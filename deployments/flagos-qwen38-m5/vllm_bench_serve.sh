#!/usr/bin/env bash
# HTTP benchmark: pp512/tg128 against a running vLLM server
set -euo pipefail

eval "$(~/.homebrew/bin/brew shellenv)"
export KMP_DUPLICATE_LIB_OK=TRUE

script_dir="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=_env.sh
source "$script_dir/_env.sh"

HOST="${BENCH_HOST:-127.0.0.1}"
PORT="${BENCH_PORT:-8000}"
NUM_PROMPTS="${BENCH_NUM_PROMPTS:-4}"

"$VLLM" bench serve \
  --backend vllm \
  --host "$HOST" \
  --port "$PORT" \
  --endpoint /v1/completions \
  --model qwen38 \
  --tokenizer "$MODEL_DIR" \
  --dataset-name random \
  --random-input-len 512 \
  --random-output-len 128 \
  --num-prompts "$NUM_PROMPTS" \
  --max-concurrency 1 \
  --temperature 0 \
  --seed 42 \
  --ignore-eos \
  --save-result
