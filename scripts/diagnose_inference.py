"""Bounded synthetic streaming diagnostic, not a quality/production benchmark."""
import argparse
import asyncio
import json
import platform
import re
import time
from collections import Counter
from pathlib import Path

import httpx

from app.ai.inference.config import InferenceConfig
from app.ai.inference.schema import structural_schema
from app.ai.prompts import ANALYSIS_INSTRUCTIONS
from app.schemas.analysis import AnalysisResult
from training.seed import examples


async def measure(client, endpoint, mode, context, token_cap, deadline):
    body = {"model": "negotiation-local", "seed": 42, "temperature": 0.2,
            "max_tokens": token_cap, "stream": True, "stream_options": {"include_usage": True},
            "messages": [{"role": "system", "content": ANALYSIS_INSTRUCTIONS},
                         {"role": "user", "content": json.dumps(context, ensure_ascii=False)}]}
    schema = AnalysisResult.model_json_schema()
    if mode != "none":
        if mode == "structural":
            schema = structural_schema(schema)
        body["response_format"] = {"type": "json_schema", "json_schema": {
            "name": "AnalysisResult", "strict": True, "schema": schema}}
    started = time.monotonic()
    row = {"mode": mode, "token_cap": token_cap, "deadline_seconds": deadline,
           "first_content_seconds": None, "content_chunks": 0, "content_chars": 0,
           "finish_reason": None, "usage": None, "quality_evaluated": False}
    fragments = []
    try:
        async with asyncio.timeout(deadline):
            async with client.stream("POST", endpoint.rstrip("/") + "/chat/completions", json=body) as response:
                row["http_status"] = response.status_code
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: ") or line == "data: [DONE]":
                        continue
                    data = json.loads(line[6:])
                    if data.get("usage"):
                        row["usage"] = {key: data["usage"].get(key) for key in
                                        ("prompt_tokens", "completion_tokens", "total_tokens")}
                    for choice in data.get("choices", []):
                        content = choice.get("delta", {}).get("content", "")
                        if content:
                            if row["first_content_seconds"] is None:
                                row["first_content_seconds"] = round(time.monotonic() - started, 4)
                            row["content_chunks"] += 1
                            row["content_chars"] += len(content)
                            if row["content_chars"] <= 65536:
                                fragments.append(content)
                        if choice.get("finish_reason"):
                            row["finish_reason"] = choice["finish_reason"]
        row["status"] = "completed" if row["finish_reason"] == "stop" else "incomplete"
    except TimeoutError:
        row["status"] = "deadline"
    except httpx.HTTPStatusError:
        row["status"] = "http_error"
    except (httpx.HTTPError, ValueError, TypeError, KeyError):
        row["status"] = "protocol_error"
    row["seconds"] = round(time.monotonic() - started, 4)
    usage = row["usage"] or {}
    text = "".join(fragments)
    allowed_keys = set(AnalysisResult.model_fields) | {
        "assertiveness", "cooperation", "flexibility", "argumentation", "conflict_management"}
    row["known_fields_observed"] = sorted(set(re.findall(r'"([^"]+)"\s*:', text)) & allowed_keys)
    words = re.findall(r"\w+", text.lower())
    grams = Counter(tuple(words[index:index + 4]) for index in range(max(0, len(words) - 3)))
    row["repeated_4gram_fraction"] = round(
        sum(count - 1 for count in grams.values()) / max(1, sum(grams.values())), 4)
    if usage.get("completion_tokens") and row["first_content_seconds"] is not None:
        elapsed = row["seconds"] - row["first_content_seconds"]
        row["approx_decode_tokens_per_second"] = round(max(0, usage["completion_tokens"] - 1) / max(elapsed, 0.001), 3)
    return row


async def diagnose(endpoint, modes, token_cap, deadline, case_id="comercial-analysis"):
    InferenceConfig(base_url=endpoint)
    # Only bundled synthetic data. No database/account/prompt from a user.
    example = next((item for item in examples() if item.id == case_id and item.task == "analysis"), None)
    if example is None:
        raise ValueError("Select an analysis example from the bundled synthetic corpus")
    context = example.context.model_dump()
    async with httpx.AsyncClient(timeout=deadline, trust_env=False, follow_redirects=False) as client:
        # A loading model returns 503. Do not mistake startup for inference cost.
        ready_by = time.monotonic() + 30
        while True:
            try:
                response = await client.get(endpoint.rstrip("/") + "/models", timeout=3)
                if response.status_code == 200 and response.json().get("data"):
                    break
            except (httpx.HTTPError, ValueError):
                pass
            if time.monotonic() >= ready_by:
                raise RuntimeError("Inference server not ready within 30 seconds")
            await asyncio.sleep(0.5)
        rows = []
        for mode in modes:
            row = await measure(client, endpoint, mode, context, token_cap, deadline)
            rows.append(row)
            print(json.dumps(row), flush=True)
            if row["status"] == "deadline":
                # Older llama.cpp may continue generation after disconnect. Do
                # not contaminate the next run with an unknown busy server.
                break
    return {"purpose": "performance diagnostic only; no quality or training claim",
            "platform": platform.machine(), "synthetic_case": case_id,
            "warmup_order_recorded": modes, "runs": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8090/v1")
    parser.add_argument("--modes", nargs="+", choices=("none", "structural", "full"),
                        default=["none", "structural", "full"])
    parser.add_argument("--tokens", type=int, choices=range(16, 513), default=64)
    parser.add_argument("--case-id", default="comercial-analysis")
    parser.add_argument("--deadline", type=float, default=60)
    parser.add_argument("--output", default="generated-artifacts/diagnostic.json")
    args = parser.parse_args()
    if not 1 <= args.deadline <= 120:
        parser.error("deadline must be 1..120 seconds")
    result = asyncio.run(diagnose(args.base_url, args.modes, args.tokens, args.deadline, args.case_id))
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2))
