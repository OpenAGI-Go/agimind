#!/usr/bin/env bash
# Direct inference launcher (skips doctor check)
set -euo pipefail

eval "$(~/.homebrew/bin/brew shellenv)"
export PATH="$HOME/.local/bin:$PATH"
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

export INFERENCE_MODE="${1:-nospec}"
shift || true

source "$PAYLOAD/portable_env.sh"
ulimit -n 4096

if [[ "$INFERENCE_MODE" == "nospec" ]]; then
  exec "$PYTHON_BIN" "$PAYLOAD/qwen38_nospec_benchmark.py" "$@"
elif [[ "$INFERENCE_MODE" == "dflash2" ]]; then
  exec "$PYTHON_BIN" "$PAYLOAD/qwen38_dflash2_generate.py" "$@"
else
  echo "Unknown inference mode: $INFERENCE_MODE (use nospec or dflash2)" >&2
  exit 1
fi
