from typing import Protocol, TypeVar

from pydantic import BaseModel

Result = TypeVar("Result", bound=BaseModel)


class InferenceProvider(Protocol):
    async def generate(self, instructions: str, context: dict, schema: type[Result]) -> Result: ...
    async def close(self) -> None: ...
