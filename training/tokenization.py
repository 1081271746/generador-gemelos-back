import json

from app.ai.prompts import TWIN_INSTRUCTIONS, ANALYSIS_INSTRUCTIONS


def chat_messages(example):
    return [
        {"role": "system", "content": TWIN_INSTRUCTIONS if example.task == "twin" else ANALYSIS_INSTRUCTIONS},
        {"role": "user", "content": json.dumps(example.context.model_dump(), ensure_ascii=False)},
        {"role": "assistant", "content": json.dumps(example.expected, ensure_ascii=False)},
    ]


def tokenize_example(tokenizer, example, max_length):
    messages = chat_messages(example)
    prefix = tokenizer.apply_chat_template(messages[:-1], tokenize=False, add_generation_prompt=True)
    full = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
    if not full.startswith(prefix):
        raise ValueError("Tokenizer chat template does not support assistant-only loss safely")
    prefix_ids = tokenizer(prefix, add_special_tokens=False)["input_ids"]
    full_ids = tokenizer(full, add_special_tokens=False)["input_ids"]
    if len(full_ids) > max_length or len(full_ids) <= len(prefix_ids):
        raise ValueError("Example exceeds max_length or has no supervised target; never truncate silently")
    if full_ids[:len(prefix_ids)] != prefix_ids:
        raise ValueError("Tokenizer boundary mismatch")
    return {"input_ids": full_ids, "attention_mask": [1] * len(full_ids),
            "labels": [-100] * len(prefix_ids) + full_ids[len(prefix_ids):]}


def pad_batch(features, pad_token_id):
    import torch
    length = max(len(row["input_ids"]) for row in features)
    return {key: torch.tensor([
        row[key] + [pad_token_id if key == "input_ids" else -100 if key == "labels" else 0] * (length - len(row[key]))
        for row in features], dtype=torch.long)
        for key in ("input_ids", "attention_mask", "labels")}
