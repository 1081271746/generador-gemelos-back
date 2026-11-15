"""Start an installed llama.cpp binary with bounded local-only inference."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess


def command(model, adapter=None, port=8090, threads=3, context=8192):
    binary = shutil.which("llama-server")
    if not binary:
        raise RuntimeError("Install llama.cpp with llama-server on your inference host")
    model = Path(model).resolve()
    if not model.is_file() or model.suffix != ".gguf":
        raise ValueError("Select an existing GGUF model file")
    args = [binary, "-m", str(model), "--host", "127.0.0.1", "--port", str(port),
            "--alias", "negotiation-local", "-c", str(context), "-np", "1",
            "-t", str(threads), "-ngl", os.getenv("AI_GPU_LAYERS", "0"),
            "--no-context-shift", "--no-webui", "--log-disable"]
    if adapter:
        adapter = Path(adapter).resolve()
        if not adapter.is_file() or adapter.suffix != ".gguf":
            raise ValueError("Adapter must be an existing converted GGUF LoRA adapter")
        args += ["--lora", str(adapter)]
    return args


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("model")
    parser.add_argument("--adapter")
    parser.add_argument("--port", type=int, choices=range(1024, 65536), default=8090)
    parser.add_argument("--threads", type=int, choices=range(1, 65), default=3)
    parser.add_argument("--context", type=int, choices=(4096, 8192, 16384), default=8192)
    args = parser.parse_args()
    raise SystemExit(subprocess.call(command(args.model, args.adapter, args.port, args.threads, args.context)))
