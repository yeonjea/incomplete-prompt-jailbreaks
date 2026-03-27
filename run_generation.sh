#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

MODEL_NAMES=(
  # "meta-llama/Llama-3.1-8B-Instruct"
  # "meta-llama/Llama-3.1-70B-Instruct"
  # "Qwen/Qwen3-4B-Instruct-2507"
  "Qwen/Qwen2.5-7B-Instruct"
  "Qwen/Qwen3-32B"

  # "google/gemma-3-4b-it"
  
  "google/gemma-3-270m-it"
  "google/gemma-3-12b-it"
  "google/gemma-3-27b-it"
)

for model_name in "${MODEL_NAMES[@]}"; do
  python "${SCRIPT_DIR}/main_generation.py" \
    --model-name "${model_name}" \
    --setting all \
    --output-dir "${SCRIPT_DIR}/outputs"
done
