"""Safe software metadata; never dump process environment or credentials."""
from importlib.metadata import PackageNotFoundError, version
import platform


def software_manifest():
    libraries = {}
    for name in ("torch", "transformers", "peft", "accelerate", "safetensors", "bitsandbytes"):
        try:
            libraries[name] = version(name)
        except PackageNotFoundError:
            libraries[name] = None
    return {"python": platform.python_version(), "libraries": libraries}
