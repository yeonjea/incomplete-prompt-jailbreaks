from __future__ import annotations

import argparse
import json

from tqdm import tqdm

from eval import (
    DEFAULT_JUDGE_PROMPT,
    evaluate_with_judge_model,
    evaluate_with_openai_moderation,
    load_results,
    replace_or_append_eval,
    results_path,
    save_results,
)


SUPPORTED_SETTINGS = ("completion_benchmark", "chat_template_benchmark")
SUPPORTED_EVALUATORS = ("openai_moderation_api", "judge_model")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate incomplete-prompt jailbreak generations.")
    parser.add_argument("--model-name", required=True, help="Target model whose generations are being evaluated.")
    parser.add_argument(
        "--setting",
        default="all",
        choices=(*SUPPORTED_SETTINGS, "all"),
        help="Which benchmark output(s) to evaluate.",
    )
    parser.add_argument("--output-dir", default="outputs")
    parser.add_argument(
        "--evaluator",
        required=True,
        choices=SUPPORTED_EVALUATORS,
        help="Evaluation backend.",
    )
    parser.add_argument("--openai-api-key", default="")
    parser.add_argument("--judge-model-name", default="google/gemma-3-4b-it")
    parser.add_argument("--judge-batch-size", type=int, default=8)
    parser.add_argument("--judge-max-new-tokens", type=int, default=256)
    parser.add_argument("--judge-system-prompt", default=DEFAULT_JUDGE_PROMPT)
    return parser.parse_args()


def iter_settings(requested: str) -> list[str]:
    return list(SUPPORTED_SETTINGS) if requested == "all" else [requested]


def evaluate_setting(args: argparse.Namespace, setting: str) -> None:
    path = results_path(args.output_dir, args.model_name, setting)
    rows = load_results(path)

    if args.evaluator == "openai_moderation_api":
        if not args.openai_api_key.strip():
            raise ValueError("--openai-api-key is required for openai_moderation_api evaluation.")
        for row in tqdm(rows, desc=f"Moderating {setting}"):
            payload = evaluate_with_openai_moderation(row.get("generation", ""), api_key=args.openai_api_key)
            replace_or_append_eval(row, args.evaluator, payload)
    else:
        payloads = evaluate_with_judge_model(
            rows,
            judge_model_name=args.judge_model_name,
            batch_size=args.judge_batch_size,
            max_new_tokens=args.judge_max_new_tokens,
            system_prompt=args.judge_system_prompt,
        )
        evaluator_name = args.judge_model_name
        for row, payload in zip(rows, payloads):
            replace_or_append_eval(row, evaluator_name, payload)

    save_results(path, rows)
    print(json.dumps({"setting": setting, "saved_to": str(path), "count": len(rows), "evaluator": args.evaluator}))


def main() -> None:
    args = parse_args()
    for setting in iter_settings(args.setting):
        evaluate_setting(args, setting)


if __name__ == "__main__":
    main()
