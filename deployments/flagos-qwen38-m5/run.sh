#!/usr/bin/env bash
# FlagOS Qwen3.8-27B launcher for Mac M5 Pro
set -euo pipefail

eval "$(~/.homebrew/bin/brew shellenv)"
export PATH="$HOME/.local/bin:$PATH"
export SSL_CERT_FILE="$HOME/.homebrew/etc/ca-certificates/cert.pem"
export REQUESTS_CA_BUNDLE="$SSL_CERT_FILE"
export CURL_CA_BUNDLE="$SSL_CERT_FILE"
export KMP_DUPLICATE_LIB_OK=TRUE
export VLLM_HOST_IP=127.0.0.1
export MASTER_ADDR=127.0.0.1
export MASTER_PORT="${MASTER_PORT:-29500}"
export ALLOW_OTHER_APPLE_HOST=1

script_dir="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=_env.sh
source "$script_dir/_env.sh"

cd "$script_dir"

case "${1:-}" in
  run-nospec)
    shift
    exec ./infer.sh nospec "$@"
    ;;
  run-dflash2|run)
    shift
    exec ./infer.sh dflash2 "$@"
    ;;
  serve|serve-nospec)
    shift
    exec ./serve.sh nospec "$@"
    ;;
  serve-dflash2)
    shift
    exec ./serve.sh dflash2 "$@"
    ;;
esac

exec ./setup_and_run_qwen38_m5.sh "$@"
