"""Extrapolate measured decoding cost. Does not change quality, timeouts or tokens."""
import argparse
import json
import math
from pathlib import Path


def estimate(report, output_tokens, target_seconds):
    if type(output_tokens) is not int or not 1 <= output_tokens <= 8192:
        raise ValueError("output_tokens must be 1..8192")
    if not math.isfinite(target_seconds) or target_seconds <= 0:
        raise ValueError("target_seconds must be positive and finite")
    rows = [row for row in report["runs"]
            if row.get("http_status") == 200 and row.get("approx_decode_tokens_per_second", 0) > 0
            and row.get("first_content_seconds") is not None]
    if not rows:
        raise ValueError("No usable decoding measurement; cannot estimate from a timeout or HTTP error")
    # Conservative within available observations, not a statistical p95.
    rate = min(row["approx_decode_tokens_per_second"] for row in rows)
    first = max(row["first_content_seconds"] for row in rows)
    remaining = target_seconds - first
    return {"estimate_only": True, "quality_verified": False, "p95_measured": False,
            "output_token_budget": output_tokens, "observed_decode_tokens_per_second": rate,
            "observed_first_content_seconds": first,
            "estimated_budget_seconds": round(first + max(0, output_tokens - 1) / rate, 2),
            "target_seconds": target_seconds,
            "required_decode_tokens_per_second": round(max(0, output_tokens - 1) / remaining, 2)
            if remaining > 0 else None}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("report")
    parser.add_argument("--output-tokens", type=int, default=2048)
    parser.add_argument("--target-seconds", type=float, default=120)
    args = parser.parse_args()
    print(json.dumps(estimate(json.loads(Path(args.report).read_text()),
                              args.output_tokens, args.target_seconds), indent=2))
