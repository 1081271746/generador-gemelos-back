import asyncio
import os
import signal
import sys
from dataclasses import dataclass
from pathlib import Path

# Add the project root to Python's import path.
ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import httpx
from redis.asyncio import Redis

from app.core.config import settings
from app.rpc.transport import create_channel, local_target


STARTUP_TIMEOUT = int(os.getenv("SERVICE_STARTUP_TIMEOUT_SECONDS", "60"))
SHUTDOWN_TIMEOUT = 10


@dataclass
class ManagedProcess:
    name: str
    process: asyncio.subprocess.Process


def install_shutdown_handlers(stopping: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()

    def request_shutdown(_signum, _frame):
        loop.call_soon_threadsafe(stopping.set)

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stopping.set)
        except NotImplementedError:
            signal.signal(sig, request_shutdown)


def validate_targets() -> None:
    targets = {
        "Twin": settings.TWIN_GRPC_TARGET,
        "Analysis": settings.ANALYSIS_GRPC_TARGET,
        "Events": settings.EVENT_GRPC_TARGET,
    }

    for name, target in targets.items():
        if not local_target(target):
            raise RuntimeError(
                f"{name} must use a loopback address in the single-service deployment"
            )


def get_port() -> int:
    value = os.getenv("PORT", "8000")

    try:
        port = int(value)
    except ValueError:
        raise RuntimeError("PORT must be a valid integer") from None

    if not 1 <= port <= 65535:
        raise RuntimeError("PORT must be between 1 and 65535")

    return port


async def check_redis() -> None:
    print("Checking Redis connection...", flush=True)

    client = Redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=3,
    )

    try:
        for attempt in range(20):
            try:
                await client.ping()
                print("Redis connection successful.", flush=True)
                return
            except Exception as error:
                if attempt == 19:
                    raise RuntimeError(
                        f"Redis did not become available: {type(error).__name__}"
                    ) from None

                await asyncio.sleep(1)

    finally:
        await client.aclose()


async def run_migrations() -> None:
    print("Running database migrations...", flush=True)

    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "alembic",
        "upgrade",
        "head",
        cwd=ROOT,
    )

    code = await process.wait()

    if code != 0:
        raise RuntimeError(f"Alembic migrations failed with exit code {code}")

    print("Database migrations completed.", flush=True)


async def start_process(name: str, *command: str) -> ManagedProcess:
    print(f"Starting {name}...", flush=True)

    process = await asyncio.create_subprocess_exec(
        sys.executable,
        *command,
        cwd=ROOT,
    )

    managed = ManagedProcess(name=name, process=process)

    print(f"{name} started with PID {process.pid}.", flush=True)

    return managed


async def wait_for_grpc(managed: ManagedProcess, target: str) -> None:
    print(f"Waiting for {managed.name}...", flush=True)

    channel = create_channel(target)

    try:
        await asyncio.wait_for(
            channel.channel_ready(),
            timeout=STARTUP_TIMEOUT,
        )

        print(f"{managed.name} is ready.", flush=True)

        if managed.process.returncode is not None:
            raise RuntimeError(
                f"{managed.name} exited during startup"
            )

    except asyncio.TimeoutError:
        raise RuntimeError(
            f"{managed.name} did not become ready within {STARTUP_TIMEOUT} seconds"
        ) from None

    finally:
        await channel.close()


async def wait_for_http(port: int) -> None:
    url = f"http://127.0.0.1:{port}/health"

    print(f"Waiting for FastAPI at {url}...", flush=True)

    async with httpx.AsyncClient(timeout=3) as client:
        for attempt in range(STARTUP_TIMEOUT):
            try:
                response = await client.get(url)

                if response.status_code == 200:
                    print("FastAPI is healthy.", flush=True)
                    return

            except httpx.HTTPError:
                pass

            await asyncio.sleep(1)

    raise RuntimeError("FastAPI did not become healthy before the startup timeout")


async def stop_processes(processes: list[ManagedProcess]) -> None:
    if not processes:
        return

    print("Stopping application processes...", flush=True)

    for managed in reversed(processes):
        process = managed.process

        if process.returncode is None:
            try:
                process.terminate()
            except ProcessLookupError:
                pass

    for managed in reversed(processes):
        process = managed.process

        try:
            await asyncio.wait_for(
                process.wait(),
                timeout=SHUTDOWN_TIMEOUT,
            )
        except asyncio.TimeoutError:
            print(f"Force stopping {managed.name}.", flush=True)
            process.kill()
            await process.wait()

    print("All application processes stopped.", flush=True)


async def monitor_processes(
    processes: list[ManagedProcess],
    stopping: asyncio.Event,
) -> None:
    waiters = {
        asyncio.create_task(managed.process.wait()): managed
        for managed in processes
    }

    stop_waiter = asyncio.create_task(stopping.wait())

    try:
        done, _ = await asyncio.wait(
            [*waiters, stop_waiter],
            return_when=asyncio.FIRST_COMPLETED,
        )

        if stop_waiter in done:
            print("Shutdown signal received.", flush=True)
            return

        for task in done:
            managed = waiters.get(task)

            if managed is not None:
                code = task.result()

                raise RuntimeError(
                    f"{managed.name} exited unexpectedly with code {code}"
                )

    finally:
        stop_waiter.cancel()

        for task in waiters:
            task.cancel()

        await asyncio.gather(
            stop_waiter,
            *waiters,
            return_exceptions=True,
        )


async def main() -> int:
    stopping = asyncio.Event()
    install_shutdown_handlers(stopping)

    processes: list[ManagedProcess] = []

    try:
        settings.validate_security()
        validate_targets()

        port = get_port()

        print("Starting Negotiation Twin Generator in production mode.", flush=True)

        await check_redis()
        await run_migrations()

        if stopping.is_set():
            return 0

        services = [
            (
                "gRPC Twin",
                ("-m", "app.rpc.ai_server", "twin"),
                settings.TWIN_GRPC_TARGET,
            ),
            (
                "gRPC Analysis",
                ("-m", "app.rpc.ai_server", "analysis"),
                settings.ANALYSIS_GRPC_TARGET,
            ),
            (
                "gRPC Events",
                ("-m", "app.rpc.event_server"),
                settings.EVENT_GRPC_TARGET,
            ),
        ]

        for name, command, target in services:
            managed = await start_process(name, *command)
            processes.append(managed)

            await wait_for_grpc(managed, target)

        api = await start_process(
            "FastAPI",
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            str(port),
        )

        processes.append(api)

        await wait_for_http(port)

        print("All backend services are online.", flush=True)

        await monitor_processes(processes, stopping)

        return 0

    except Exception as error:
        print(
            f"Production startup failed: {type(error).__name__}: {error}",
            file=sys.stderr,
            flush=True,
        )

        return 1

    finally:
        await stop_processes(processes)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
