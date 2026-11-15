import json

import pytest

from training.config import TrainingConfig
from training.data import load_examples, split_examples
from training.prepare import prepare
from training.seed import examples
from training.tokenization import tokenize_example
from training.train import train
from training.privacy import check_privacy


def source(tmp_path):
    path = tmp_path / "dataset.jsonl"
    path.write_text("".join(item.model_dump_json() + "\n" for item in examples()))
    return path


def test_seed_has_ten_domains_and_validated_targets():
    rows = list(examples())
    assert len(rows) == 20
    assert len({item.domain for item in rows}) == 10
    assert all(item.synthetic and not item.reviewed and item.authorized for item in rows)


def test_human_review_is_default_gate(tmp_path):
    with pytest.raises(ValueError, match="Unreviewed"):
        load_examples(source(tmp_path))


def test_group_split_reproducible_and_disjoint():
    rows = list(examples())
    first = split_examples(rows)
    assert first == split_examples(rows)
    groups = [{item.family for item in first[name]} for name in ("train", "validation", "test")]
    assert all(groups)
    assert not groups[0] & groups[1] and not groups[1] & groups[2] and not groups[0] & groups[2]
    assert sum(map(len, first.values())) == 20


def test_preparation_hashes_and_counts(tmp_path):
    target = tmp_path / "prepared"
    manifest = prepare(source(tmp_path), target, allow_unreviewed=True)
    assert sum(item["count"] for item in manifest["splits"].values()) == 20
    assert manifest["unreviewed_allowed"]
    assert len(manifest["source_sha256"]) == 64


def test_duplicate_and_unauthorized_rejected(tmp_path):
    path = source(tmp_path)
    first = path.read_text().splitlines()[0]
    path.write_text(first + "\n" + first)
    with pytest.raises(ValueError, match="Duplicate"):
        load_examples(path, allow_unreviewed=True)
    record = json.loads(first)
    record["authorized"] = False
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError, match="Invalid dataset"):
        load_examples(path, allow_unreviewed=True)


def test_changed_ids_do_not_hide_duplicate_conversations(tmp_path):
    example = next(examples()).model_dump()
    changed = json.loads(json.dumps(example))
    changed["id"] += "-different-id"
    changed["context"]["negotiation_id"] += 100
    changed["context"]["messages"][0]["message_id"] += 100
    path = tmp_path / "duplicates.jsonl"
    path.write_text(json.dumps(example) + "\n" + json.dumps(changed))
    with pytest.raises(ValueError, match="Duplicate"):
        load_examples(path, allow_unreviewed=True)


def test_training_preflight_blocks_full_run_without_gpu(monkeypatch):
    monkeypatch.setattr("training.train.inspect_hardware", lambda: {"cuda_training_candidate": False})
    config = TrainingConfig(revision="a" * 40)
    with pytest.raises(RuntimeError, match="No NVIDIA GPU"):
        train(config)


class CharacterTokenizer:
    def apply_chat_template(self, messages, tokenize, add_generation_prompt):
        value = "".join(f'{item["role"]}:{item["content"]};' for item in messages)
        return value + "assistant:" if add_generation_prompt else value

    def __call__(self, text, add_special_tokens):
        return {"input_ids": [ord(char) for char in text]}


def test_assistant_only_labels_and_no_silent_truncation():
    item = next(examples())
    encoded = tokenize_example(CharacterTokenizer(), item, 10000)
    assert -100 in encoded["labels"] and encoded["labels"][-1] != -100
    assert len(encoded["input_ids"]) == len(encoded["labels"])
    with pytest.raises(ValueError, match="never truncate"):
        tokenize_example(CharacterTokenizer(), item, 10)


@pytest.mark.parametrize("value", [
    "Contacta persona@example.org",
    "password=not-a-real-password",
    "-----BEGIN PRIVATE KEY-----",
])
def test_private_information_is_rejected(value):
    with pytest.raises(ValueError):
        check_privacy(value)
