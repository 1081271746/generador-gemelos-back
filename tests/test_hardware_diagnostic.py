import json
import subprocess
from types import SimpleNamespace

import pytest

from scripts import diagnose_local_hardware as diagnostic


def test_inventory_does_not_initialize_torch_or_run_runtime_check(monkeypatch):
    monkeypatch.setattr(diagnostic, "installed_libraries", lambda: {"torch": "2.10.0"})
    monkeypatch.setattr(diagnostic, "gpu_info", lambda: {"status": "not_found", "gpus": []})
    monkeypatch.setattr(diagnostic, "memory_info", lambda: {"total_bytes": 16 * 1024**3})
    monkeypatch.setattr(diagnostic, "check_cuda", lambda: pytest.fail("CUDA was not requested"))
    report = diagnostic.collect()
    assert report["cuda_runtime_check"]["status"] == "not_requested"
    assert report["training_readiness"] == "not_verified"
    assert not report["nf4_backward_check"]["verified"]
    assert not any(report["actions_performed"].values())
    assert not {"hostname", "username", "environment", "python_path"} & report.keys()


def test_gpu_inventory_parses_multiple_devices_and_driver_not_toolkit(monkeypatch):
    responses = iter([
        ("ok", "NVIDIA GeForce RTX 4050 Laptop GPU, 6141, 5920, 610.74\nSecond GPU, 8192, 4096, 610.74\n"),
        ("ok", "CUDA UMD Version : 13.3\n"),
    ])
    monkeypatch.setattr(diagnostic, "run_command", lambda *a, **k: next(responses))
    result = diagnostic.gpu_info()
    assert result["status"] == "ok"
    assert result["gpus"][0]["vram_total_mib"] == 6141
    assert len(result["gpus"]) == 2
    assert result["driver_cuda_version"] == "13.3"
    assert "cuda_available" not in result


@pytest.mark.parametrize("output", [
    "", "GPU, N/A, 0, 610.74", "GPU, 6141, 7000, 610.74",
    "GPU, -1, 0, 610.74", "GPU, 6141, 5000, secret-path", "unexpected",
])
def test_invalid_gpu_output_is_not_reported_as_success(monkeypatch, output):
    monkeypatch.setattr(diagnostic, "run_command", lambda *a, **k: ("ok", output))
    result = diagnostic.gpu_info()
    assert result["status"] == "invalid_output"
    assert result["gpus"] == []


@pytest.mark.parametrize("error,status", [
    (FileNotFoundError(), "not_found"),
    (subprocess.TimeoutExpired("nvidia-smi", 10), "timeout"),
    (PermissionError("private-path"), "command_failed"),
])
def test_command_failures_are_bounded_and_sanitized(monkeypatch, error, status):
    def fail(*a, **k):
        assert k["shell"] is False
        assert k["timeout"] == 10
        raise error
    monkeypatch.setattr(diagnostic.subprocess, "run", fail)
    assert diagnostic.run_command(["nvidia-smi"]) == (status, "")


def test_failed_command_does_not_disclose_output(monkeypatch):
    monkeypatch.setattr(diagnostic.subprocess, "run", lambda *a, **k:
                        SimpleNamespace(returncode=1, stdout="private", stderr="private"))
    assert diagnostic.run_command(["anything"]) == ("command_failed", "")


def test_dependency_inventory_only_reads_metadata(monkeypatch):
    def version(name):
        if name == "torch":
            return "2.10.0+cu126"
        raise diagnostic.importlib.metadata.PackageNotFoundError(name)
    monkeypatch.setattr(diagnostic.importlib.metadata, "version", version)
    result = diagnostic.installed_libraries()
    assert result["torch"] == "2.10.0+cu126"
    assert result["bitsandbytes"] is None


def test_optional_cuda_check_is_isolated_and_cannot_approve_training(monkeypatch):
    def worker(args, timeout):
        assert args[-1] == "--cuda-worker"
        assert timeout == 60
        return "ok", 'extra library output\n{"status":"ok","operation_verified":true}\n'
    monkeypatch.setattr(diagnostic, "run_command", worker)
    monkeypatch.setattr(diagnostic, "installed_libraries", lambda: {})
    monkeypatch.setattr(diagnostic, "memory_info", lambda: {})
    monkeypatch.setattr(diagnostic, "gpu_info", lambda: {})
    report = diagnostic.collect(True)
    assert report["cuda_runtime_check"]["operation_verified"]
    assert report["training_readiness"] == "not_verified"


@pytest.mark.parametrize("status,output", [
    ("timeout", ""), ("ok", "not json"), ("ok", '{"environment":"private"}'),
    ("ok", '{"status":"ok","operation_verified":"yes"}'), ("ok", "[]"),
])
def test_bad_cuda_worker_results_do_not_pass(monkeypatch, status, output):
    monkeypatch.setattr(diagnostic, "run_command", lambda *a, **k: (status, output))
    assert not diagnostic.check_cuda()["operation_verified"]


def test_windows_memory_uses_native_api_without_powershell(monkeypatch):
    def fill(pointer):
        pointer._obj.total_phys = 16 * 1024**3
        pointer._obj.avail_phys = 8 * 1024**3
        return 1
    monkeypatch.setattr(diagnostic.ctypes, "windll", SimpleNamespace(
        kernel32=SimpleNamespace(GlobalMemoryStatusEx=fill)), raising=False)
    result = diagnostic.windows_memory()
    assert result["total_bytes"] == 16 * 1024**3
    assert result["available_bytes"] == 8 * 1024**3


def test_windows_memory_failure_is_explicit(monkeypatch):
    monkeypatch.setattr(diagnostic.ctypes, "windll", SimpleNamespace(
        kernel32=SimpleNamespace(GlobalMemoryStatusEx=lambda p: 0)), raising=False)
    assert diagnostic.windows_memory()["total_bytes"] is None


def test_cli_never_overwrites_existing_report(monkeypatch, tmp_path):
    target = tmp_path / "report.json"
    target.write_text("keep")
    monkeypatch.setattr(diagnostic.sys, "argv", ["diagnostic", "--output", str(target)])
    with pytest.raises(SystemExit) as error:
        diagnostic.main()
    assert error.value.code == 2
    assert target.read_text() == "keep"


def test_cli_creates_explicit_new_report(monkeypatch, tmp_path, capsys):
    target = tmp_path / "reports" / "report.json"
    monkeypatch.setattr(diagnostic, "collect", lambda flag: {"training_readiness": "not_verified"})
    monkeypatch.setattr(diagnostic.sys, "argv", ["diagnostic", "--output", str(target)])
    diagnostic.main()
    assert json.loads(target.read_text()) == json.loads(capsys.readouterr().out)
