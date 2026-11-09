import asyncio
import os
from pathlib import Path
from secrets import token_urlsafe
import socket
import subprocess
import sys

import grpc
import httpx

from tests.test_grpc_events import redis_url


def free_port():
    with socket.socket() as handle:
        handle.bind(("127.0.0.1", 0))
        return handle.getsockname()[1]


async def test_four_processes_start_and_missing_gemini_is_controlled(tmp_path, redis_url):
    ports = [free_port() for _ in range(4)]
    root = Path(__file__).resolve().parents[1]
    env = {
        **os.environ,
        "DATABASE_URL": f"sqlite:///{tmp_path / 'processes.db'}",
        "SECRET_KEY": token_urlsafe(48), "SERVICE_SECRET": token_urlsafe(48),
        "GEMINI_API_KEY": "", "REDIS_URL": redis_url,
        "TWIN_GRPC_TARGET": f"127.0.0.1:{ports[0]}",
        "ANALYSIS_GRPC_TARGET": f"127.0.0.1:{ports[1]}",
        "EVENT_GRPC_TARGET": f"127.0.0.1:{ports[2]}",
    }
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=root, env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    commands = [
        ["-m", "app.rpc.ai_server", "twin"],
        ["-m", "app.rpc.ai_server", "analysis"],
        ["-m", "app.rpc.event_server"],
        ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(ports[3])],
    ]
    processes = []
    try:
        for command in commands:
            processes.append(subprocess.Popen([sys.executable, *command], cwd=root, env=env,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        for port in ports[:3]:
            async with grpc.aio.insecure_channel(f"127.0.0.1:{port}") as channel:
                await asyncio.wait_for(channel.channel_ready(), timeout=10)
        async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{ports[3]}", timeout=5) as client:
            for _ in range(100):
                try:
                    if (await client.get("/health")).status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                await asyncio.sleep(0.1)
            else:
                raise AssertionError("FastAPI subprocess did not become healthy")
            account = {"username": "process_test", "email": "process@example.com", "password": "test-password-long"}
            assert (await client.post("/auth/register", json=account)).status_code == 201
            token = (await client.post("/auth/login", json=account)).json()["access_token"]
            client.headers["Authorization"] = f"Bearer {token}"
            scenario = {"title": "Supply", "description": "Annual supplies", "context": "Renewal",
                "objective": "Lower cost", "counterpart_role": "Supplier",
                "counterpart_goal": "Protect margin", "counterpart_limits": "Minimum 100"}
            scenario_id = (await client.post("/scenarios/", json=scenario)).json()["id"]
            negotiation_id = (await client.post("/negotiations/", json={"scenario_id": scenario_id})).json()["id"]
            response = await client.post("/messages/", json={"negotiation_id": negotiation_id, "content": "I offer 100"})
            assert response.status_code == 503
            assert len((await client.get(f"/messages/{negotiation_id}")).json()) == 1
            assert (await client.patch(f"/negotiations/{negotiation_id}", json={
                "status": "completed", "result": "No agreement; AI unavailable"})).status_code == 200
            assert (await client.post(f"/negotiations/{negotiation_id}/analysis")).status_code == 503
            assert (await client.get("/resources/exercises")).status_code == 200
            assert all(process.poll() is None for process in processes)
    finally:
        for process in reversed(processes):
            process.terminate()
        for process in reversed(processes):
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
