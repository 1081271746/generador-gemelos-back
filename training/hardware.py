"""Read hardware facts without CUDA/PyTorch dependencies or environment dumps."""
import json
import os
import platform
import shutil
import subprocess
from pathlib import Path


def _integer(path):
    try:
        return int(Path(path).read_text().strip())
    except (OSError, ValueError):
        return None


def inspect_hardware():
    memory = {}
    try:
        memory = {line.split(":")[0]: int(line.split()[1]) * 1024
                  for line in Path("/proc/meminfo").read_text().splitlines() if ":" in line}
    except OSError:
        pass
    limit = _integer("/sys/fs/cgroup/memory.max")
    total = memory.get("MemTotal")
    effective = min(total, limit) if total and limit else total or limit
    used = _integer("/sys/fs/cgroup/memory.current")
    available = min(memory.get("MemAvailable", effective or 0), max(0, effective - used)) if effective and used else memory.get("MemAvailable")
    gpu = []
    if shutil.which("nvidia-smi"):
        result = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version",
                                 "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            gpu = [row.strip() for row in result.stdout.splitlines()]
    return {"os": platform.system(), "architecture": platform.machine(),
            "cpu_count": os.cpu_count(), "ram_limit_bytes": effective,
            "ram_available_bytes": available, "disk_free_bytes": shutil.disk_usage(".").free,
            "nvidia_gpus": gpu, "cuda_training_candidate": bool(gpu)}


if __name__ == "__main__":
    print(json.dumps(inspect_hardware(), indent=2))
