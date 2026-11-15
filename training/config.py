import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TrainingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base_model: str = "Qwen/Qwen2.5-1.5B-Instruct"
    revision: str = Field(pattern=r"^[a-f0-9]{40}$")
    data_dir: str = "training/prepared"
    output_dir: str = "models/negotiation_adapter"
    mode: Literal["lora", "qlora"] = "lora"
    max_length: int = Field(default=2048, ge=128, le=8192)
    rank: int = Field(default=8, ge=1, le=64)
    alpha: int = Field(default=16, ge=1, le=128)
    learning_rate: float = Field(default=0.0002, gt=0, le=0.01)
    epochs: float = Field(default=3, gt=0, le=20)
    max_steps: int = Field(default=-1, ge=-1, le=100000)
    seed: int = 42
    smoke: bool = False
    cpu_smoke: bool = False

    @classmethod
    def load(cls, path):
        return cls.model_validate(json.loads(Path(path).read_text()))
