"""Explicit offline specialization. GPU preflight precedes model downloads."""
import argparse
import hashlib
import json
from pathlib import Path

from training.config import TrainingConfig
from training.data import load_examples
from training.hardware import inspect_hardware
from training.tokenization import tokenize_example, pad_batch
from training.provenance import software_manifest


def train(config, resume=None):
    facts = inspect_hardware()
    if not facts["cuda_training_candidate"] and not (config.smoke and config.cpu_smoke):
        raise RuntimeError("No NVIDIA GPU detected. Use a compatible GPU host; CPU is allowed only for explicit smoke.")
    if config.smoke and not 1 <= config.max_steps <= 5:
        raise ValueError("Smoke must specify 1..5 optimizer steps")
    if config.cpu_smoke and (not config.smoke or config.max_length > 1024):
        raise ValueError("CPU smoke requires smoke=true and max_length<=1024")
    if config.mode == "qlora" and not facts["cuda_training_candidate"]:
        raise RuntimeError("QLoRA requires a supported CUDA GPU and bitsandbytes")
    output = Path(config.output_dir)
    if output.exists() and any(output.iterdir()) and not resume:
        raise ValueError("Output is nonempty; choose a new run directory or --resume checkpoint")
    data = Path(config.data_dir)
    manifest = json.loads((data / "manifest.json").read_text())
    examples = {}
    for name in ("train", "validation", "test"):
        path = data / f"{name}.jsonl"
        if hashlib.sha256(path.read_bytes()).hexdigest() != manifest["splits"][name]["sha256"]:
            raise ValueError(f"{name} dataset differs from its preparation manifest")
        examples[name] = load_examples(path, allow_unreviewed=config.smoke)
    families = [{item.family for item in examples[name]} for name in examples]
    if any(families[i] & families[j] for i in range(3) for j in range(i)):
        raise ValueError("Scenario leakage between train, validation and test")
    # Heavy packages are optional and never imported by FastAPI or gRPC.
    import torch
    from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments, set_seed
    from peft import LoraConfig, TaskType, get_peft_model, prepare_model_for_kbit_training
    set_seed(config.seed)
    model_config = AutoConfig.from_pretrained(config.base_model, revision=config.revision, trust_remote_code=False)
    if config.cpu_smoke and (getattr(model_config, "hidden_size", 0) > 1024
                             or getattr(model_config, "num_hidden_layers", 0) > 24):
        raise ValueError("CPU smoke requires a small diagnostic model; do not load the 1.5B target on this host")
    tokenizer = AutoTokenizer.from_pretrained(config.base_model, revision=config.revision, trust_remote_code=False)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    dtype = torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else torch.float32
    kwargs = {"revision": config.revision, "trust_remote_code": False, "torch_dtype": dtype}
    if config.mode == "qlora":
        from transformers import BitsAndBytesConfig
        kwargs.update(device_map={"": torch.cuda.current_device()}, quantization_config=BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=dtype,
            bnb_4bit_use_double_quant=True))
    model = AutoModelForCausalLM.from_pretrained(config.base_model, **kwargs)
    if config.mode == "qlora":
        model = prepare_model_for_kbit_training(model)
    model.config.use_cache = False
    model = get_peft_model(model, LoraConfig(task_type=TaskType.CAUSAL_LM, r=config.rank,
                                           lora_alpha=config.alpha, lora_dropout=0.05,
                                           target_modules=["q_proj", "v_proj"]))
    encoded = {name: [tokenize_example(tokenizer, item, config.max_length) for item in rows]
               for name, rows in examples.items() if name != "test"}
    args = TrainingArguments(
        output_dir=str(output), per_device_train_batch_size=1, per_device_eval_batch_size=1,
        gradient_accumulation_steps=1 if config.smoke else 8, learning_rate=config.learning_rate,
        num_train_epochs=config.epochs, max_steps=config.max_steps, seed=config.seed,
        eval_strategy="steps", eval_steps=1 if config.smoke else 25, save_strategy="steps",
        save_steps=1 if config.smoke else 25, save_total_limit=2, logging_steps=1,
        bf16=dtype == torch.bfloat16, fp16=False, report_to="none", save_safetensors=True,
        gradient_checkpointing=True, gradient_checkpointing_kwargs={"use_reentrant": False},
        use_cpu=config.cpu_smoke, dataloader_num_workers=0)
    trainer = Trainer(model=model, args=args, train_dataset=encoded["train"],
                      eval_dataset=encoded["validation"],
                      data_collator=lambda rows: pad_batch(rows, tokenizer.pad_token_id))
    result = trainer.train(resume_from_checkpoint=resume)
    metrics = trainer.evaluate()
    # Actual adapter saved only after train() returns successfully.
    trainer.save_model(str(output))
    tokenizer.save_pretrained(output)
    trainable, total = model.get_nb_trainable_parameters()
    (output / "training-history.json").write_text(json.dumps(trainer.state.log_history, indent=2, default=str) + "\n")
    run = {"status": "smoke_completed" if config.smoke else "training_completed",
           "expert_model": False, "config": config.model_dump(), "hardware": facts,
           "software": software_manifest(), "cuda_runtime": torch.version.cuda,
           "trainable_parameters": trainable, "total_parameters": total,
           "global_step": trainer.state.global_step,
           "checkpoints": sorted(path.name for path in output.glob("checkpoint-*") if path.is_dir()),
           "dataset_manifest": manifest, "train_metrics": result.metrics, "validation_metrics": metrics}
    (output / "run.json").write_text(json.dumps(run, indent=2, default=str) + "\n")
    return run


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("config")
    parser.add_argument("--resume")
    args = parser.parse_args()
    print(json.dumps(train(TrainingConfig.load(args.config), args.resume), indent=2, default=str))
