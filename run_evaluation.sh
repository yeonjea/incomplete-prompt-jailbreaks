#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

MODEL_NAMES=(
  # "meta-llama/Llama-3.1-70B-Instruct"
  # "meta-llama/Llama-3.1-8B-Instruct"
  # "Qwen/Qwen3-4B-Instruct-2507"
  # "Qwen/Qwen2.5-7B-Instruct"
  # "Qwen/Qwen3-32B"

  "google/gemma-3-270m-it"
  "google/gemma-3-4b-it"
  "google/gemma-3-12b-it"
  "google/gemma-3-27b-it"
)

JUDGE_MODEL_NAME="${JUDGE_MODEL_NAME:-google/gemma-3-12b-it}"

for model_name in "${MODEL_NAMES[@]}"; do
  python "${SCRIPT_DIR}/main_evaluation.py" \
    --model-name "${model_name}" \
    --setting all \
    --evaluator judge_model \
    --judge-model-name "${JUDGE_MODEL_NAME}" \
    --output-dir "${SCRIPT_DIR}/outputs"
done

if [[ -n "${OPENAI_API_KEY:-}" ]]; then
  for model_name in "${MODEL_NAMES[@]}"; do
    python "${SCRIPT_DIR}/main_evaluation.py" \
      --model-name "${model_name}" \
      --setting all \
      --evaluator openai_moderation_api \
      --openai-api-key "${OPENAI_API_KEY}" \
      --output-dir "${SCRIPT_DIR}/outputs"
  done
fi
