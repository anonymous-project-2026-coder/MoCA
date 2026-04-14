from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from .pipeline import ConflictReasoningPipeline
from .schemas import FinalReasoningResult, ReasoningCase


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Appendix 5-step conflict reasoner")
    parser.add_argument("--input-file", type=Path, required=True)
    parser.add_argument("--output-file", type=Path)
    parser.add_argument("--max-revision-rounds", type=int, default=0)
    parser.add_argument(
        "--stop-after",
        choices=["stage1", "stage2", "stage3", "stage4", "stage5"],
        default="stage5",
    )
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


def _load_cases(path: Path) -> list[ReasoningCase]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [ReasoningCase.model_validate(item) for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        return [ReasoningCase.model_validate(payload)]
    raise SystemExit("Input JSON must be a dict or list of dicts.")


def _serialize_final(result: FinalReasoningResult) -> dict[str, Any]:
    return {
        "id": result.case.case_id,
        "prediction": {
            "subject": result.mechanism_decision.subject,
            "target": result.mechanism_decision.target,
            "mechanism": result.mechanism_decision.mechanism,
            "label": result.mechanism_decision.label,
        },
        "accepted": result.accepted,
    }


async def _run(args: argparse.Namespace) -> list[dict[str, Any]]:
    pipeline = ConflictReasoningPipeline(max_revision_rounds=args.max_revision_rounds)
    outputs: list[dict[str, Any]] = []
    for case in _load_cases(args.input_file):
        artifacts = await pipeline.run_stages(case=case, stop_after=args.stop_after)
        if args.stop_after == "stage5":
            outputs.append(_serialize_final(artifacts["final_result"]))
        else:
            outputs.append(
                {
                    "id": case.case_id,
                    "artifacts": {
                        key: (value.model_dump() if hasattr(value, "model_dump") else value)
                        for key, value in artifacts.items()
                    },
                }
            )
    return outputs


def main() -> None:
    args = parse_args()
    outputs = asyncio.run(_run(args))
    text = json.dumps(outputs, ensure_ascii=False, indent=2 if args.pretty else None)
    if args.output_file:
        args.output_file.write_text(text, encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
