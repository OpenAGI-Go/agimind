# FlagOS Qwen3.8-27B on Mac M5 Pro

Mac 纯 CPU 部署脚本，配合 [实践总结](../../notes/2026-09-01-flagos-qwen38-deployment-practice.md) 使用。

**不包含模型权重和 Runtime 环境**（~36GB），需在本机另行下载构建。

## 推荐目录布局

默认假定运行时目录为 `~/qwen38-m5`：

```
~/qwen38-m5/
├── infer.sh                    # 可从本目录复制或 symlink
├── serve.sh
├── run.sh
├── vllm_bench_serve.sh
├── setup_and_run_qwen38_m5.sh
└── .flagos-qwen38-runtime/     # models + venv，由 setup 生成
    ├── models/
    └── sources/
```

也可通过环境变量改路径：

```bash
export QWEN38_ROOT="$HOME/qwen38-m5"
```

## 首次部署

```bash
# 复制脚本到运行目录（或在此目录直接跑并设置 QWEN38_ROOT）
cp -r deployments/flagos-qwen38-m5/* ~/qwen38-m5/
cd ~/qwen38-m5

# 下载模型 + 构建环境（约 15 分钟）
./setup_and_run_qwen38_m5.sh models
export DFLASH2_INSTALL_ROOT="$HOME/qwen38-m5/.flagos-qwen38-runtime"
./setup_and_run_qwen38_m5.sh env
```

非 Mac17,9 机器需：

```bash
export ALLOW_OTHER_APPLE_HOST=1
```

## 日常使用

```bash
# 单次推理
MAX_TOKENS=128 ENABLE_THINKING=0 ./infer.sh dflash2 "你的问题"

# API 服务
./serve.sh dflash2

# HTTP 性能测试（server 已启动）
./vllm_bench_serve.sh
```

## 脚本说明

| 文件 | 作用 |
|------|------|
| `_env.sh` | 路径与环境变量（被其他脚本 source） |
| `setup_and_run_qwen38_m5.sh` | 官方入口：models / env / benchmark |
| `infer.sh` | 单次推理（每次冷启动） |
| `serve.sh` | OpenAI 兼容 API（`:8000`） |
| `run.sh` | 快捷封装 |
| `vllm_bench_serve.sh` | pp512/tg128 HTTP benchmark |
| `results/` | 实测 benchmark JSON |

## 关键修复（已内置）

- `VLLM_HOST_IP=127.0.0.1` — 避免 TCPStore 连 `172.19.0.1` 卡死
- `GLOO_SOCKET_IFNAME=lo0` — 加速 Gloo 初始化
- `KMP_DUPLICATE_LIB_OK=TRUE` — OpenMP 库冲突
- `--no-enable-prefix-caching` — serve 参数兼容 vLLM 0.24
