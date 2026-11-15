"""Explicit provider choice. No automatic commercial fallback."""
import os

from app.ai.inference.local import LocalInference


def provider_name():
    name = os.getenv("AI_PROVIDER", "local")
    if name not in ("local", "gemini"):
        raise ValueError("AI_PROVIDER must be local or gemini")
    return name


def create_provider():
    if provider_name() == "local":
        return LocalInference()
    # Legacy rollback is opt-in; the normal runtime never imports Gemini.
    from app.ai.gemini import GeminiService
    return GeminiService()
