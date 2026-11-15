"""Validated, provenance-aware examples and leakage-safe family splitting."""
import hashlib
import json
import random
import unicodedata
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.ai.response_validator import NegotiationInput, validate_analysis
from app.schemas.analysis import AnalysisResult, TwinResponse
from training.privacy import check_privacy


def normalize(value):
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value.replace("\r\n", "\n")).strip()
    if isinstance(value, list):
        return [normalize(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize(item) for key, item in value.items()}
    return value


class Example(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=150)
    family: str = Field(min_length=1, max_length=150)
    domain: str = Field(min_length=1, max_length=150)
    task: Literal["twin", "analysis"]
    source: str = Field(min_length=1, max_length=1000)
    license: Literal["CC0-1.0", "CC-BY-4.0", "Apache-2.0", "authorized-private"]
    authorized: bool
    synthetic: bool
    reviewed: bool
    context: NegotiationInput
    expected: dict
    rationale: str = Field(min_length=10, max_length=5000)

    @model_validator(mode="after")
    def valid_target(self):
        if not self.authorized:
            raise ValueError("Training requires explicitly authorized examples")
        context = self.context.checked()
        if self.task == "analysis":
            validate_analysis(AnalysisResult.model_validate(self.expected), context)
        else:
            TwinResponse.model_validate(self.expected)
            if context["messages"][-1]["sender_type"] != "user":
                raise ValueError("Twin training requires final user message")
        return self


def load_examples(path, allow_unreviewed=False):
    examples, ids, fingerprints = [], set(), set()
    with Path(path).open(encoding="utf8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            if len(line.encode()) > 300000:
                raise ValueError(f"Example too large at line {line_number}")
            try:
                check_privacy(line)
                example = Example.model_validate(normalize(json.loads(line)))
            except Exception:
                # Do not echo private records in validation errors.
                raise ValueError(f"Invalid dataset example at line {line_number}") from None
            if not example.reviewed and not allow_unreviewed:
                raise ValueError(f"Unreviewed example at line {line_number}")
            # IDs cannot make an otherwise identical conversation a new sample.
            context = example.context.model_dump(exclude={"negotiation_id"})
            context["messages"] = [{key: value for key, value in message.items() if key != "message_id"}
                                   for message in context["messages"]]
            canonical = json.dumps([example.task, context], sort_keys=True, ensure_ascii=False)
            fingerprint = hashlib.sha256(canonical.encode()).hexdigest()
            if example.id in ids or fingerprint in fingerprints:
                raise ValueError(f"Duplicate example at line {line_number}")
            ids.add(example.id)
            fingerprints.add(fingerprint)
            examples.append(example)
    if not examples:
        raise ValueError("Empty dataset")
    return examples


def split_examples(examples, seed=42):
    groups = sorted({item.family for item in examples})
    if len(groups) < 3:
        raise ValueError("At least three independent scenario families are required")
    random.Random(seed).shuffle(groups)
    held_out = max(1, int(len(groups) * 0.15))
    assigned = {group: "test" if index < held_out else "validation" if index < 2 * held_out else "train"
                for index, group in enumerate(groups)}
    return {name: [item for item in examples if assigned[item.family] == name]
            for name in ("train", "validation", "test")}
