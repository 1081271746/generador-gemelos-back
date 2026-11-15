"""Same held-out examples, base vs adapter, no model as a hidden judge."""
import argparse
import asyncio
import json
import resource
import time
from pathlib import Path

from app.ai.analysis_engine import AnalysisEngine
from app.ai.inference.config import InferenceConfig
from app.ai.inference.local import LocalInference
from app.ai.twin_engine import TwinEngine
from app.schemas.analysis import DIMENSION_NAMES
from training.data import load_examples


async def evaluate(examples, endpoints, max_tokens=2048, timeout=300):
    reports = {}
    for label, endpoint in endpoints.items():
        measurements = []
        provider = LocalInference(InferenceConfig(base_url=endpoint, timeout=timeout, max_tokens=max_tokens),
                                  observer=measurements.append)
        rows = []
        try:
            for example in examples:
                started = time.monotonic()
                try:
                    context = example.context.model_dump()
                    output = await (TwinEngine(provider).reply(context) if example.task == "twin"
                                    else AnalysisEngine(provider).analyze(context))
                    row = {"id": example.id, "task": example.task, "valid_schema_and_evidence": True,
                           "output": output.model_dump(), "human_review_required": True}
                    if example.task == "analysis":
                        row["score_mae_vs_provisional_label"] = sum(
                            abs(getattr(output.dimensions, key).score - example.expected["dimensions"][key]["score"])
                            for key in DIMENSION_NAMES) / len(DIMENSION_NAMES)
                except Exception as error:
                    row = {"id": example.id, "task": example.task, "valid_schema_and_evidence": False,
                           "error_type": type(error).__name__,
                           "error_code": getattr(error, "code", "domain_or_input_validation")}
                row["inference_metrics"] = measurements[-1] if measurements else None
                measurements.clear()
                row["seconds"] = round(time.monotonic() - started, 3)
                rows.append(row)
        finally:
            await provider.close()
        reports[label] = {"samples": rows, "schema_evidence_passes": sum(row["valid_schema_and_evidence"] for row in rows),
                          "client_peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                          "server_memory": "measure llama-server separately; client RSS is not model RSS"}
    return {"reports": reports, "quality_claim": "No expert claim; manual rubric required"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", help="Use prepared/test.jsonl for a held-out comparison")
    parser.add_argument("--base-url", default="http://127.0.0.1:8090/v1")
    parser.add_argument("--adapter-url", help="Separately loaded specialized model; omit if no trained adapter exists")
    parser.add_argument("--output", default="generated-artifacts/evaluation.json")
    parser.add_argument("--allow-unreviewed-synthetic", action="store_true")
    args = parser.parse_args()
    endpoints = {"base": args.base_url}
    if args.adapter_url:
        endpoints["specialized"] = args.adapter_url
    examples = load_examples(args.dataset, args.allow_unreviewed_synthetic)
    result = asyncio.run(evaluate(examples, endpoints))
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"Saved {len(examples)} examples for {len(endpoints)} model(s).")
