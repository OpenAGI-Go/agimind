#!/usr/bin/env bash
# OpenAI-compatible vLLM server (model stays loaded between requests)
set -euo pipefail

eval "$(~/.homebrew/bin/brew shellenv)"
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin:$PATH"
export SSL_CERT_FILE="$HOME/.homebrew/etc/ca-certificates/cert.pem"
export REQUESTS_CA_BUNDLE="$SSL_CERT_FILE"
export CURL_CA_BUNDLE="$SSL_CERT_FILE"
export KMP_DUPLICATE_LIB_OK=TRUE
export ALLOW_OTHER_APPLE_HOST=1
export VLLM_HOST_IP=127.0.0.1
export MASTER_ADDR=127.0.0.1
export MASTER_PORT="${MASTER_PORT:-29500}"
export GLOO_SOCKET_IFNAME=lo0

script_dir="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=_env.sh
source "$script_dir/_env.sh"

SERVER_MODE="${1:-dflash2}"
shift || true

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
SERVED_NAME="${SERVED_NAME:-qwen38}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-1024}"
MAX_NUM_BATCHED_TOKENS="${MAX_NUM_BATCHED_TOKENS:-1024}"

source "$PAYLOAD/portable_env.sh"
ulimit -n 4096

ARGS=(
  serve "$MODEL_DIR"
  --host "$HOST"
  --port "$PORT"
  --served-model-name "$SERVED_NAME"
  --trust-remote-code
  --dtype bfloat16
  --max-model-len "$MAX_MODEL_LEN"
  --max-num-batched-tokens "$MAX_NUM_BATCHED_TOKENS"
  --max-num-seqs 1
  --enforce-eager
  --language-model-only
  --no-enable-prefix-caching
  --distributed-executor-backend uni
  --disable-log-stats
  --generation-config vllm
  --reasoning-parser qwen3
  --limit-mm-per-prompt '{"image":0,"video":0}'
)

if [[ "$SERVER_MODE" == "dflash2" ]]; then
  ARGS+=(
    --speculative-config "{\"method\":\"dflash\",\"model\":\"$DFLASH2_DIR\",\"num_speculative_tokens\":7}"
  )
elif [[ "$SERVER_MODE" == "nospec" ]]; then
  :
else
  echo "Unknown server mode: $SERVER_MODE (use nospec or dflash2)" >&2
  exit 1
fi

echo "Starting vLLM server ($SERVER_MODE) at http://$HOST:$PORT (model: $SERVED_NAME)"
echo "First startup loads ~22GB weights; expect 2-3 minutes before /health is ready."
exec "$PYTHON_BIN" -m vllm.entrypoints.cli.main "${ARGS[@]}" "$@"
