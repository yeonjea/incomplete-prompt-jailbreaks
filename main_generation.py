from __future__ import annotations

import argparse
import json
from typing import Any

from datasets import load_dataset

from eval import load_results, results_path, save_results
from modules import (
    generate_response,
    load_base_model,
    make_incomplete_chat_response_prompt,
)

DATASET_NAME = "leo-bjpark/incomplete-prompt-jailbreak"
SUPPORTED_SETTINGS = ("completion_benchmark", "chat_template_benchmark")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run incomplete-prompt jailbreak generation.")
    parser.add_argument("--model-name", required=True, help="HF model name used for generation.")
    parser.add_argument(
        "--setting",
        default="all",
        choices=(*SUPPORTED_SETTINGS, "all"),
        help="Benchmark split to run.",
    )
    parser.add_argument("--dataset-name", default=DATASET_NAME)
    parser.add_argument("--split", default="train")
    parser.add_argument("--output-dir", default="outputs")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-new-tokens", type=int, default=128)
    parser.add_argument(
        "--system-instruction",
        default=None,
        help="Optional system instruction injected into chat-template prompts.",
    )
    return parser.parse_args()


def iter_settings(requested: str) -> list[str]:
    return list(SUPPORTED_SETTINGS) if requested == "all" else [requested]


def _build_rows(
    setting: str,
    ds: Any,
    *,
    tokenizer: Any,
    generations: list[str],
    system_instruction: str | None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    if setting == "completion_benchmark":
        prompts = list(ds["prompt"])
        categories = list(ds["category"])
        for idx, prompt in enumerate(prompts):
            rows.append(
                {
                    "input": {
                        "setting": setting,
                        "row_index": idx,
                        "source_prompt": prompt,
                        "prompt": prompt,
                        "category": categories[idx],
                    },
                    "generation": generations[idx] if idx < len(generations) else "",
                    "evals": [],
                }
            )
        return rows

    records = list(ds)
    for idx, record in enumerate(records):
        prompt = make_incomplete_chat_response_prompt(
            tokenizer,
            record["user_request"],
            record["response_prefill"],
            system_instruction=system_instruction,
        )
        rows.append(
            {
                "input": {
                    "setting": setting,
                    "row_index": idx,
                    "source_prompt": record["user_request"],
                    "response_prefill": record["response_prefill"],
                    "prompt": prompt,
                    "category": record["category"],
                },
                "generation": generations[idx] if idx < len(generations) else "",
                "evals": [],
            }
        )
    return rows


def _merge_existing_evals(target_rows: list[dict[str, Any]], existing_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for idx, row in enumerate(target_rows):
        if idx < len(existing_rows) and isinstance(existing_rows[idx], dict):
            existing_evals = existing_rows[idx].get("evals", [])
            if isinstance(existing_evals, list):
                row["evals"] = existing_evals
    return target_rows


def run_generation(args: argparse.Namespace) -> None:
    model, tokenizer = load_base_model(args.model_name)

    for setting in iter_settings(args.setting):
        ds = load_dataset(args.dataset_name, setting, split=args.split)
        if setting == "completion_benchmark":
            prompts = list(ds["prompt"])
        else:
            prompts = [
                make_incomplete_chat_response_prompt(
                    tokenizer,
                    row["user_request"],
                    row["response_prefill"],
                    system_instruction=args.system_instruction,
                )
                for row in ds
            ]

        generations = generate_response(
            model,
            tokenizer,
            prompts,
            batch_size=args.batch_size,
            max_new_tokens=args.max_new_tokens,
        )
        rows = _build_rows(
            setting,
            ds,
            tokenizer=tokenizer,
            generations=generations,
            system_instruction=args.system_instruction,
        )
        output_path = results_path(args.output_dir, args.model_name, setting)
        if output_path.exists():
            rows = _merge_existing_evals(rows, load_results(output_path))
        save_results(output_path, rows)
        print(json.dumps({"setting": setting, "saved_to": str(output_path), "count": len(rows)}))


if __name__ == "__main__":
    run_generation(parse_args())
