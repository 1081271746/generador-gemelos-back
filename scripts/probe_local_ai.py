"""Readiness probe, never infer availability from settings or health alone."""
import argparse
import asyncio
import json

import httpx

from app.ai.inference.config import InferenceConfig


async def probe(base_url):
    config = InferenceConfig(base_url=base_url)
    async with httpx.AsyncClient(timeout=5, follow_redirects=False, trust_env=False) as client:
        response = await client.get(config.base_url.rstrip("/") + "/models")
        response.raise_for_status()
        models = response.json()["data"]
        if not models:
            raise RuntimeError("No model loaded")
        return {"reachable": True, "loaded_models": [item["id"] for item in models],
                "generation_verified": False, "fine_tuning_verified": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=InferenceConfig.from_env().base_url)
    args = parser.parse_args()
    print(json.dumps(asyncio.run(probe(args.base_url)), indent=2))
