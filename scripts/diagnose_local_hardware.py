"""Standalone local inventory. Standard library only; no installs or model loads."""
import argparse
import csv
import ctypes
import importlib.metadata
import json
import os
import platform
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys


LIBRARIES = ("torch", "transformers", "peft", "accelerate", "bitsandbytes", "safetensors")
RECOMMENDED = {
    "python": "3.11 (64-bit)", "torch": "2.10.0+cu126",
    "transformers": "4.57.6", "peft": "0.18.1",
    "accelerate": "1.12.0", "bitsandbytes": "0.49.2",
}


def run_command(args, timeout=10):
    """Never return command output on failure: it can contain personal paths."""
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                                encoding="utf-8", errors="replace", shell=False)
    except FileNotFoundError:
        return "not_found", ""
    except subprocess.TimeoutExpired:
        return "timeout", ""
    except OSError:
        return "command_failed", ""
    return ("ok", result.stdout) if result.returncode == 0 else ("command_failed", "")


def windows_memory():
    class MemoryStatus(ctypes.Structure):
        _fields_ = [
            ("length", ctypes.c_uint32), ("load", ctypes.c_uint32),
            ("total_phys", ctypes.c_uint64), ("avail_phys", ctypes.c_uint64),
            ("total_page", ctypes.c_uint64), ("avail_page", ctypes.c_uint64),
            ("total_virtual", ctypes.c_uint64), ("avail_virtual", ctypes.c_uint64),
            ("avail_extended", ctypes.c_uint64),
        ]
    try:
        status = MemoryStatus()
        status.length = ctypes.sizeof(status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return {"total_bytes": status.total_phys, "available_bytes": status.avail_phys,
                    "source": "GlobalMemoryStatusEx"}
    except (AttributeError, OSError):
        pass
    return {"total_bytes": None, "available_bytes": None, "source": "unavailable"}


def memory_info():
    if platform.system() == "Windows":
        return windows_memory()
    try:
        values = {}
        for line in Path("/proc/meminfo").read_text().splitlines():
            key, value = line.split(":", 1)
            values[key] = int(value.split()[0]) * 1024
        return {"total_bytes": values.get("MemTotal"),
                "available_bytes": values.get("MemAvailable"), "source": "proc_meminfo"}
    except (OSError, ValueError, IndexError):
        return {"total_bytes": None, "available_bytes": None, "source": "unavailable"}


def gpu_info():
    status, output = run_command([
        "nvidia-smi", "--query-gpu=name,memory.total,memory.free,driver_version",
        "--format=csv,noheader,nounits",
    ])
    result = {"status": status, "gpus": [], "driver_cuda_version": None}
    if status != "ok":
        return result
    try:
        for row in csv.reader(output.splitlines()):
            if len(row) != 4:
                raise ValueError("Unexpected GPU fields")
            name, total, free, driver = (item.strip() for item in row)
            total, free = int(total), int(free)
            if not name or len(name) > 200 or not 0 <= free <= total or total == 0:
                raise ValueError("Invalid GPU memory")
            if not re.fullmatch(r"[0-9.]{1,32}", driver):
                raise ValueError("Invalid driver version")
            result["gpus"].append({"name": name, "vram_total_mib": total,
                                   "vram_free_mib": free, "driver_version": driver})
        if not result["gpus"]:
            raise ValueError("Empty GPU list")
    except (ValueError, csv.Error):
        result.update(status="invalid_output", gpus=[])
        return result
    version_status, version = run_command(["nvidia-smi", "--version"])
    if version_status == "ok":
        match = re.search(r"CUDA(?:\s+UMD)?\s+Version\s*:\s*(\d+\.\d+)", version, re.I)
        if match:
            result["driver_cuda_version"] = match.group(1)
    return result


def installed_libraries():
    versions = {}
    for name in LIBRARIES:
        try:
            value = importlib.metadata.version(name)
            versions[name] = value if re.fullmatch(r"[a-zA-Z0-9.+_-]{1,80}", value) else "unknown"
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def cuda_worker():
    """Opt-in tiny tensor operation only: no model, optimizer or training."""
    try:
        import torch
        if not torch.cuda.is_available():
            return {"status": "unavailable", "operation_verified": False}
        device = 0
        capability = list(torch.cuda.get_device_capability(device))
        with torch.no_grad():
            tensor = torch.ones((8, 8), device="cuda:0", dtype=torch.float32)
            value = (tensor @ tensor)[0, 0].item()
        torch.cuda.synchronize(device)
        return {
            "status": "ok" if value == 8.0 else "unexpected_result",
            "operation_verified": value == 8.0,
            "torch_cuda_runtime": torch.version.cuda,
            "compute_capability": capability,
            "bf16_supported": bool(torch.cuda.is_bf16_supported()),
            "test_dtype": "float32",
        }
    except ImportError:
        return {"status": "dependency_missing_or_unloadable", "operation_verified": False}
    except Exception:
        # No raw exception: Windows loader errors may disclose personal paths.
        return {"status": "operation_failed", "operation_verified": False}


def check_cuda():
    status, output = run_command(
        [sys.executable, "-B", str(Path(__file__).resolve()), "--cuda-worker"], timeout=60)
    if status != "ok":
        return {"status": status, "operation_verified": False}
    try:
        data = json.loads(output.splitlines()[-1])
        allowed = {"status", "operation_verified", "torch_cuda_runtime",
                   "compute_capability", "bf16_supported", "test_dtype"}
        if not isinstance(data, dict) or not set(data) <= allowed:
            raise ValueError("Invalid worker result")
        if not isinstance(data.get("operation_verified"), bool):
            raise ValueError("Missing verification")
        return data
    except (ValueError, IndexError, TypeError):
        return {"status": "invalid_output", "operation_verified": False}


def collect(check_runtime=False):
    libraries = installed_libraries()
    try:
        free_disk = shutil.disk_usage(Path.cwd()).free
    except OSError:
        free_disk = None
    return {
        "report_version": 1,
        "execution_scope": "machine_running_this_script_not_a_remote_computer",
        "system": {"os": platform.system(), "os_release": platform.release(),
                   "architecture": platform.machine(), "process_bits": struct.calcsize("P") * 8,
                   "cpu_count": os.cpu_count()},
        "python": {"version": platform.python_version(),
                   "matches_recommended_series": sys.version_info[:2] == (3, 11)
                   and struct.calcsize("P") * 8 == 64},
        "ram": memory_info(),
        "disk_free_bytes_on_current_drive": free_disk,
        "nvidia": gpu_info(),
        "libraries_in_active_python": libraries,
        "recommended_versions_not_a_validated_lockfile": RECOMMENDED,
        "cuda_runtime_check": check_cuda() if check_runtime else
            {"status": "not_requested", "operation_verified": False},
        "nf4_backward_check": {"status": "not_performed", "verified": False},
        "training_readiness": "not_verified",
        "actions_performed": {"installed_dependencies": False, "downloaded_models": False,
                              "started_training": False},
        "notes": [
            "Inventory uses installed package metadata; it does not import ML libraries by default.",
            "Driver CUDA version is not proof of an installed Toolkit or working PyTorch.",
            "A float32 tensor check does not verify BF16 arithmetic, NF4, training or model quality.",
            "RAM/disk figures describe this machine, not a guaranteed model memory budget.",
            "Do not share environment files, credentials, personal paths or full system inventories.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optional new JSON file; never overwrites a file")
    parser.add_argument("--check-cuda", action="store_true",
                        help="Opt in to a tiny CUDA tensor check, if PyTorch is already installed")
    parser.add_argument("--cuda-worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.cuda_worker:
        print(json.dumps(cuda_worker()))
        return
    if args.output and args.output.exists():
        parser.error("The output file already exists; choose another name")
    report = json.dumps(collect(args.check_cuda), ensure_ascii=False, indent=2)
    if args.output:
        try:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x", encoding="utf-8") as handle:
                handle.write(report + "\n")
        except OSError:
            parser.exit(1, "Could not create report; choose a new writable output file.\n")
    print(report)


if __name__ == "__main__":
    main()
