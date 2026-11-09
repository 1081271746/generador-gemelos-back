from pathlib import Path
import subprocess
import sys


root = Path(__file__).resolve().parents[1]
subprocess.run([
    sys.executable, "-m", "grpc_tools.protoc", f"-I{root}",
    f"--python_out={root}", f"--grpc_python_out={root}",
    str(root / "app/rpc/negotiation.proto"),
], check=True)
