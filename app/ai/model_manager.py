"""Explicit provider choice. No automatic commercial fallback."""
import os

from app.ai.inference.local import LocalInference


def provider_name():
    name = os.getenv("AI_PROVIDER", "groq")
    if name not in ("local", "groq"):
        raise ValueError("AI_PROVIDER must be groq or local")
    return name


def create_provider():
    if provider_name() == "local":
        return LocalInference()
    from app.ai.groq import GroqService
    return GroqService()
