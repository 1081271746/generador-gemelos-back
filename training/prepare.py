import argparse
import hashlib
import json
from pathlib import Path

from training.data import load_examples, split_examples


def prepare(source, output, allow_unreviewed=False, seed=42):
    examples = load_examples(source, allow_unreviewed)
    groups = split_examples(examples, seed)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    manifest = {"seed": seed, "source_sha256": hashlib.sha256(Path(source).read_bytes()).hexdigest(),
                "unreviewed_allowed": allow_unreviewed, "splits": {}}
    for split, records in groups.items():
        text = "".join(json.dumps(item.model_dump(), ensure_ascii=False) + "\n" for item in records)
        (output / f"{split}.jsonl").write_text(text, encoding="utf8")
        manifest["splits"][split] = {"count": len(records), "sha256": hashlib.sha256(text.encode()).hexdigest()}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("--output", default="training/prepared")
    parser.add_argument("--allow-unreviewed-synthetic", action="store_true",
                        help="Diagnostic smoke only; does not approve the dataset for production")
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.output, args.allow_unreviewed_synthetic), indent=2))
