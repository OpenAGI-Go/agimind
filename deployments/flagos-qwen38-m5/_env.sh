# Shared paths for FlagOS Qwen3.8-27B on Mac M5.
# Override install location:
#   export QWEN38_ROOT="$HOME/qwen38-m5"

ROOT="${QWEN38_ROOT:-$HOME/qwen38-m5}"
IR="${DFLASH2_INSTALL_ROOT:-$ROOT/.flagos-qwen38-runtime}"
WS="$IR/sources"
PY="$WS/vllm-0.24.0/.venv/bin/python"
VLLM="$WS/vllm-0.24.0/.venv/bin/vllm"
PAYLOAD="$IR/bootstrap/runtime-assets-20260829"
MODEL="$IR/models/Qwen3.8-27B-W4A8-GPTQ-G128-packed"
DFLASH2="$IR/models/Qwen3.8-27B-DFlash2"

export DFLASH2_INSTALL_ROOT="$IR"
export MODEL_DIR="$MODEL"
export DFLASH2_DIR="$DFLASH2"
export WORKSPACE_ROOT="$WS"
export RUNTIME_WORKSPACE="$WS"
export FL_PLUGIN_SOURCE_ROOT="$WS/vllm-plugin-FL-vllm024"
export PYTHON_BIN="$PY"
export FLAGOS_RUNTIME_PROFILE="$WS/flagos-macos-runtime/profiles/m5-dflash2-k7.env"
export FLAGGEMS_LIBTRITON_JIT_Q4_OP="$WS/build/flaggems-arm-m5/libflag_gems_arm_ops.dylib"
export VLLM_ENABLE_V1_MULTIPROCESSING=0
export FLAGGEMS_MTP_W8=1
export TRITON_HOME="$IR/triton"
export LIBOMP_ROOT="${LIBOMP_ROOT:-$HOME/.homebrew/opt/libomp}"
