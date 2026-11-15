"""Export a completed PEFT run to Hugging Face format, then convert using llama.cpp."""
import argparse
import json
from pathlib import Path


def export(adapter, output, allow_smoke=False):
    adapter, output = Path(adapter), Path(output)
    run = json.loads((adapter / "run.json").read_text())
    if run["status"] not in ("training_completed", "smoke_completed"):
        raise ValueError("No successful training record")
    if run["status"] == "smoke_completed" and not allow_smoke:
        raise ValueError("Diagnostic smoke adapter cannot be exported for production")
    if output.exists() and any(output.iterdir()):
        raise ValueError("Export directory must be empty")
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer
    import torch
    config = run["config"]
    base = AutoModelForCausalLM.from_pretrained(config["base_model"], revision=config["revision"],
                                               torch_dtype=torch.float32, trust_remote_code=False)
    merged = PeftModel.from_pretrained(base, adapter).merge_and_unload()
    merged.save_pretrained(output, safe_serialization=True)
    AutoTokenizer.from_pretrained(adapter, trust_remote_code=False).save_pretrained(output)
    (output / "specialization.json").write_text(json.dumps(run, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("adapter")
    parser.add_argument("output")
    parser.add_argument("--allow-smoke", action="store_true")
    args = parser.parse_args()
    export(args.adapter, args.output, args.allow_smoke)
