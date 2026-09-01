# FlagOS + Qwen3.8-27B 部署实践总结

> **日期**：2026-09-01  
> **环境**：Mac M5 Pro / 64GB 统一内存 / macOS arm64  
> **部署目录**：`~/qwen38-m5`（脚本版本控在 [`deployments/flagos-qwen38-m5/`](../deployments/flagos-qwen38-m5/)）  
> **关联笔记**：[FlagOS 文章摘录](./2026-08-31-flagos-qwen38-m5-cpu.md)

**核心实测结论（一句话）：** DFlash2 + 常驻 Server 下，decode **~23 tok/s**，约为官方 nospec baseline（12.73 tok/s）的 **1.8 倍**；prefill **~73 tok/s**，与官方基本一致。

---

## 1. 这次做了什么

在 Mac M5 Pro 上，用 FlagOS 官方 macOS CPU Runtime，完整走通了 **Qwen3.8-27B W4A8** 的本地推理部署，包括：

1. 下载模型权重、构建 FlagOS 推理环境
2. 修复分布式初始化卡死等问题，跑通单次推理（`infer.sh`）
3. 启动 OpenAI 兼容 API 服务（`serve.sh`）
4. 用官方 pp512/tg128 协议做 HTTP 性能测试（`vllm_bench_serve.sh`）

整条链路是 **纯 CPU 推理**，没有使用 M5 Pro 的 GPU / Metal。

---

## 2. 硬件与方案选择

| 项目 | 配置 |
|------|------|
| 机器 | Mac M5 Pro（Mac17,8/17,9），64GB 统一内存 |
| 推理设备 | **18 核 ARM CPU**，不用 GPU |
| 主模型 | Qwen3.8-27B W4A8 G128（GPTQ 量化，约 22GB） |
| Draft 模型 | Qwen3.8-27B-DFlash2（投机解码用） |
| 推理框架 | vLLM 0.24 + vLLM-Plugin-FL + FlagGems + flagtree-cpu |

**为什么能跑 27B？** 原始 BF16 权重约 54GB，W4A8 量化后约 22GB，加上运行时开销，64GB 统一内存刚好够用。

**为什么不用 GPU？** FlagOS macOS Runtime 从设计目标就是 Arm CPU 专精路径，官方明确写了 *"Arm CPU only; Metal is not used"*。这不是改个参数就能切 GPU 的。

---

## 3. 目录结构

```
~/qwen38-m5/
├── setup_and_run_qwen38_m5.sh   # 官方入口：models / env / benchmark
├── infer.sh                     # 单次推理（每次冷启动加载模型）
├── serve.sh                     # OpenAI API 服务（模型常驻内存）
├── run.sh                       # 快捷封装
├── vllm_bench_serve.sh          # HTTP 性能测试
└── .flagos-qwen38-runtime/
    ├── models/
    │   ├── Qwen3.8-27B-W4A8-GPTQ-G128-packed/   # 主模型
    │   └── Qwen3.8-27B-DFlash2/                  # DFlash2 drafter
    ├── bootstrap/runtime-assets-20260829/        # Python 启动脚本
    └── sources/                                  # vLLM、FlagGems 等源码与 venv
```

磁盘占用约 **模型 22GB + 环境 14GB**。

---

## 4. 部署步骤回顾

### 4.1 下载模型

```bash
cd ~/qwen38-m5
./setup_and_run_qwen38_m5.sh models
```

从 ModelScope 拉取：
- `FlagRelease/Qwen3.8-27B-W4A8-arm-FlagOS-Express`（主模型）
- `incoai/Qwen3.8-27B-DFlash2`（drafter）

### 4.2 构建推理环境

```bash
./setup_and_run_qwen38_m5.sh env
```

首次构建约 15 分钟，安装 Python 3.11、PyTorch、vLLM、FlagGems、Triton CPU 等。本机 Mac 型号为 Mac17,8，需设置：

```bash
export ALLOW_OTHER_APPLE_HOST=1
```

官方性能 profile 针对 Mac17,9（M5 Pro），Mac17,8 可运行但不保证复现官方 benchmark 数字。

### 4.3 单次推理验证

```bash
MAX_TOKENS=128 ENABLE_THINKING=0 ./infer.sh dflash2 "你的问题"
# 或
./run.sh run-dflash2 "你的问题"
```

首次冷启动约 2–3 分钟（加载 ~22GB 权重 + Triton JIT 编译 + warmup）。

### 4.4 启动 API 服务

```bash
./serve.sh dflash2    # DFlash2 加速
# 或
./serve.sh nospec     # 基础推理，可对比官方 baseline
```

服务地址：`http://127.0.0.1:8000`，模型名 `qwen38`。

### 4.5 性能测试

```bash
./vllm_bench_serve.sh
```

对齐官方 **pp512/tg128** 协议（512 token 输入 + 128 token 输出，batch=1，greedy）。

---

## 5. 踩坑与修复

### 5.1 TCPStore 卡死（连 172.19.0.1）

**现象**：`./infer.sh` 启动后长时间无输出，日志里 `TCPStore` 不断 retry `172.19.0.1`。

**原因**：vLLM 分布式初始化自动选了虚拟网卡地址（常见于 Docker/代理环境），而非 localhost。

**修复**：在 `infer.sh` / `serve.sh` 中加入：

```bash
export VLLM_HOST_IP=127.0.0.1
export MASTER_ADDR=127.0.0.1
export MASTER_PORT=29500
```

修复后日志应出现：`distributed_init_method=tcp://127.0.0.1:*`

### 5.2 Ctrl+C 无法停止进程

**现象**：卡住的推理进程 SIGINT 无效。

**处理**：

```bash
pkill -9 -f qwen38_dflash2_generate
# 或
pkill -9 -f "vllm.entrypoints.cli.main serve"
```

### 5.3 Gloo 初始化慢（~60 秒）

**现象**：serve 启动时在 Gloo 阶段空等约 1 分钟。

**修复**：在 `serve.sh` 中加入：

```bash
export GLOO_SOCKET_IFNAME=lo0
```

### 5.4 serve.sh CLI 参数错误

**现象**：`--enable-prefix-caching=false` 不被 vLLM 接受。

**修复**：改为 `--no-enable-prefix-caching`。

### 5.5 OpenMP 库冲突

**修复**：

```bash
export KMP_DUPLICATE_LIB_OK=TRUE
```

---

## 6. 实践结果（实测数据）

本节记录 2026-09-01 当天实际跑出来的数字，含命令、条件和原始输出。

### 6.1 部署与功能验证

| 验证项 | 结果 | 备注 |
|--------|------|------|
| 模型下载 | ✅ 成功 | 主模型 + DFlash2 drafter 均完整 |
| 环境构建（`env`） | ✅ 成功 | 约 15 分钟，~14GB |
| 分布式初始化 | ✅ 修复后正常 | `tcp://127.0.0.1:*`，不再连 `172.19.0.1` |
| 单次推理（`infer.sh dflash2`） | ✅ 成功 | 中文回复正常，模型自识别为 Qwen |
| API 服务（`serve.sh dflash2`） | ✅ 成功 | `http://127.0.0.1:8000/health` → 200 |
| HTTP benchmark | ✅ 成功 | 4/4 请求成功，0 失败 |

**功能测试命令：**

```bash
MAX_TOKENS=128 ENABLE_THINKING=0 ./infer.sh dflash2 "你的问题"
```

**第一次成功推理（2026-09-01 11:10，修复 TCPStore 后）：**

| 阶段 | 耗时（约） |
|------|-----------|
| 主模型 27B 加载 | ~7 s |
| DFlash2 drafter 加载 | ~3 s |
| Warmup | ~12 s |
| 生成 52 token | **11.6 s** |

- Prompt token 数：14（短 prompt）
- 输出 token 数：52
- 生成阶段吞吐：**4.5 tok/s**
- 输出内容：模型正确用中文自我介绍，内容为 Qwen 系列大语言模型
- 分布式日志：`distributed_init_method=tcp://127.0.0.1:63990 backend=gloo` ✓

### 6.2 单次推理对比（infer.sh，每次冷启动）

同一 prompt `"你的问题"`，连续两次 `./infer.sh dflash2`（每次均重新加载模型）：

| 次数 | 时间 | 输出 token | 生成耗时 | 吞吐 | 相对第 1 次 |
|------|------|-----------|---------|------|------------|
| 第 1 次 | 11:10 | 52 | 11.6 s | **4.5 tok/s** | — |
| 第 2 次 | 11:43 | 52 | 7.5 s | **6.9 tok/s** | **+53%** |

说明：
- 两次输出内容一致（`seed=0`，确定性生成）
- 第 2 次更快，主要因为 Triton kernel JIT 缓存已写入 `~/.flagos-qwen38-runtime/triton/.triton/cache/`
- 第 2 次日志中 Gloo 初始化仍约 **60 s**（`11:43:51` → `11:44:56`），后续已在 `serve.sh` 用 `GLOO_SOCKET_IFNAME=lo0` 优化
- 此模式 **不适合** 作为稳态性能参考：每次冷启动 ~2–3 分钟，短 prompt（14 token）+ 短输出（52 token），prefill 占比大

### 6.3 API 服务启动（serve.sh dflash2）

**启动时间：** 2026-09-01 14:24 左右

| 项目 | 值 |
|------|-----|
| 地址 | `http://127.0.0.1:8000` |
| 模型名 | `qwen38` |
| 模式 | dflash2（`num_speculative_tokens=7`） |
| 进程 PID | 2924 |
| 健康检查 | `GET /health` → 200 OK |
| 聊天接口 | `POST /v1/chat/completions` → 200 OK（实测 2 次） |

Server 启动后模型常驻内存，后续请求 **无需重新加载 22GB 权重**，这是 benchmark 能测出 ~23 tok/s 的前提。

### 6.4 HTTP 性能测试（vllm_bench_serve.sh）

**测试时间：** 2026-09-01 14:36  
**前置条件：** `./serve.sh dflash2` 已在运行  
**协议：** pp512 / tg128，batch=1，`temperature=0`，`seed=42`，`ignore_eos`  
**请求数：** 4（连续，无 90s 冷却）  
**结果文件：** `~/qwen38-m5/vllm-infqps-concurrency1-qwen38-20260901-143723.json`

#### 汇总指标

| 指标 | 实测值 | 换算 |
|------|--------|------|
| 成功 / 失败 | **4 / 0** | — |
| 总输入 token | 2048（512×4） | — |
| 总输出 token | 512（128×4） | — |
| Benchmark 总耗时 | **50.29 s** | 4 次连续 |
| 单次平均耗时 | ~12.6 s | 50.29 ÷ 4 |

#### 延迟与吞吐

| 指标 | Mean | Median | P99 |
|------|------|--------|-----|
| **TTFT**（首 token，ms） | 7008 | 7021 | 7476 |
| **TPOT**（每输出 token，ms） | 43.8 | 42.6 | 56.8 |
| **ITL**（流式 chunk 间隔，ms） | 211.9 | 210.6 | 244.3 |

#### 速度换算（重点）

| 阶段 | 计算公式 | 实测速度 |
|------|---------|---------|
| Prefill | 512 ÷ 7.008 s | **~73.1 tok/s** |
| Decode | 1000 ÷ 43.8 ms | **~22.8 tok/s** |
| Decode（median） | 1000 ÷ 42.6 ms | **~23.5 tok/s** |
| 单次端到端估算 | 7.0 s + 127×0.044 s | **~12.6 s** |

#### 其他 benchmark 输出（仅供参考，非 decode 速度）

| 指标 | 值 | 说明 |
|------|-----|------|
| Output token throughput | 10.18 tok/s | 含 prefill，**不能当 decode 速度** |
| Total token throughput | 50.91 tok/s | 输入+输出合计 |
| Request throughput | 0.08 req/s | — |
| Peak output throughput | 5.0 tok/s | 瞬态峰值 |

#### 与官方 nospec baseline 对比

| 指标 | 本次实测（dflash2 + HTTP） | 官方 nospec（README） | 差异 |
|------|--------------------------|----------------------|------|
| Prefill | ~73 tok/s | 74.93 tok/s | 基本一致（-2.6%） |
| Decode（TPOT） | ~22.8 tok/s（43.8 ms） | 12.73 tok/s（78.55 ms） | **+79%（DFlash2 加速）** |
| 端到端 | ~12.6 s | 16.81 s | 快 ~25% |

> 官方 baseline 是 **nospec + 90s 冷却 + 3 次 median**；本次是 **dflash2 + 连续 4 次**，负载和条件不完全相同，但足以说明 DFlash2 在 decode 阶段有效。

### 6.5 与 FlagOS 文章数据对比

| 场景 | 文章/官方 | 本次实测 | 说明 |
|------|----------|---------|------|
| nospec decode（PP512/TG128） | 12.73 tok/s | 未单独测 nospec HTTP | 待补测 |
| dflash2 完整请求（PP85/TG325） | **27.65 tok/s** | — | 需 `./run.sh benchmark-dflash2` |
| dflash2 decode（HTTP PP512/TG128） | — | **~23 tok/s** | 已测，接近但低于文章 |
| infer.sh 冷启动短回复 | — | 4.5 → 6.9 tok/s | 含加载，非稳态 |

### 6.6 资源占用（观察值）

| 资源 | 数值 |
|------|------|
| 磁盘（模型 + 环境） | ~22 GB + ~14 GB |
| 运行时内存 | ~25–30 GB（64 GB 机器足够） |
| 首次冷启动到可生成 | ~2–3 分钟 |
| Server 就绪（修复 Gloo 后） | ~2–3 分钟（仅首次） |
| 推理设备 | 纯 CPU，GPU/Metal 未使用 |

### 6.7 指标速查

| 缩写 | 含义 |
|------|------|
| **PP512** | Prompt Prefill 512 token |
| **TG128** | Token Generation 128 token |
| **TTFT** | 首 token 延迟，反映 prefill 速度 |
| **TPOT** | 每个输出 token 平均耗时，**decode 速度看这项** |
| **ITL** | 流式 chunk 间隔（DFlash2 下偏大，以 TPOT 为准） |
| **tok/s** | 1000 ÷ TPOT(ms)，或 token 数 ÷ 秒数 |

---

## 7. 三种使用模式对比

| 模式 | 命令 | 特点 | 适用场景 |
|------|------|------|---------|
| 单次推理 | `./infer.sh dflash2 "..."` | 每次冷启动，~3 分钟 | 偶尔问一句 |
| API 服务 | `./serve.sh dflash2` | 模型常驻，后续请求快 | AnythingLLM、curl、生产用法 |
| In-process benchmark | `./run.sh benchmark-dflash2` | 进程内测 PP85/TG325 | 复现文章数字（需先停 server） |
| HTTP benchmark | `./vllm_bench_serve.sh` | 对已运行 server 发请求 | 测真实 API 性能 |

**推荐日常使用**：`serve.sh` 常驻 + 客户端连 `http://127.0.0.1:8000`。

---

## 8. 技术栈一图流

```
用户请求
    │
    ▼
vLLM serve (:8000)          ← OpenAI 兼容 API
    │
    ├── vLLM-Plugin-FL       ← 模型接入、DFlash2 投机解码
    ├── FlagGems             ← Q4 G128 / GDN / W8 算子（Triton CPU）
    ├── flagtree-cpu         ← Triton → ARM SDOT/I8MM 指令
    └── PyTorch CPU          ← 18 核 OpenMP 并行
         │
         ├── Target: Qwen3.8-27B W4A8（主模型）
         └── Drafter: Qwen3.8-DFlash2（猜 token，可选）
```

**DFlash2 投机解码**：小 drafter 一次猜 7 个 token，主模型批量验证，猜对的直接接受，从而一步生成多个 token，加速 decode。

---

## 9. 常用命令速查

```bash
cd ~/qwen38-m5

# ── 推理 ──
MAX_TOKENS=128 ENABLE_THINKING=0 ./infer.sh dflash2 "你好"
./infer.sh nospec "你好"

# ── 服务 ──
./serve.sh dflash2          # 终端 A
curl http://127.0.0.1:8000/health   # 终端 B 检查

# ── 聊天 API 测试 ──
curl http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen38","messages":[{"role":"user","content":"你好"}],"max_tokens":128}'

# ── 性能测试 ──
./vllm_bench_serve.sh                              # HTTP pp512/tg128
./run.sh benchmark-dflash2                         # in-process PP85/TG325（先停 server）

# ── 杀进程 ──
pkill -9 -f qwen38_dflash2_generate
pkill -9 -f "vllm.entrypoints.cli.main serve"
```

---

## 10. 关键环境变量

| 变量 | 作用 |
|------|------|
| `VLLM_HOST_IP=127.0.0.1` | 避免 TCPStore 连错网卡 |
| `MASTER_ADDR=127.0.0.1` | 分布式通信用 localhost |
| `GLOO_SOCKET_IFNAME=lo0` | 加速 Gloo 初始化（serve 用） |
| `KMP_DUPLICATE_LIB_OK=TRUE` | 解决 OpenMP 库冲突 |
| `ALLOW_OTHER_APPLE_HOST=1` | 非 Mac17,9 机器兼容 |
| `MAX_TOKENS=128` | 控制最大生成长度 |
| `ENABLE_THINKING=0` | 关闭 Qwen3 思考模式 |

---

## 11. 与官方数据的差距说明

详细实测数据见 **第 6 节**。简要结论：

| 对比项 | 官方/文章 | 本次实测 | 原因 |
|--------|----------|---------|------|
| nospec decode | 12.73 tok/s | 未单独测 nospec HTTP | 待 `./serve.sh nospec` + benchmark |
| dflash2 decode（HTTP） | — | **~23 tok/s** | pp512/tg128，连续 4 次无冷却 |
| dflash2 完整请求（PP85/TG325） | ~27 tok/s | 未跑 in-process benchmark | 待 `./run.sh benchmark-dflash2` |
| infer.sh 冷启动 | — | 4.5 → 6.9 tok/s | 含模型加载 + 短输出 |

要补齐对照实验：
1. `./serve.sh nospec` + `./vllm_bench_serve.sh` → 对比官方 12.73 tok/s
2. 每次采样前 **sleep 90** → 对齐官方冷却协议
3. `./run.sh benchmark-dflash2` → 复现文章 PP85/TG325 的 27.65 tok/s

---

## 12. 收获与下一步

### 学到了什么

1. **推理分 prefill 和 decode 两阶段**，性能指标 TTFT / TPOT 各反映一段
2. **量化（W4A8）+ 专用 CPU kernel** 是让 27B 在 Mac 上可跑的关键
3. **投机解码（DFlash2）** 是推理侧加速技巧，与训练无关
4. **冷启动 vs 常驻服务** 对体感速度影响巨大；API server 模式才是正确用法
5. FlagOS 的价值在于 **跨芯片统一栈**；macOS 版走 CPU 路线，不是 GPU 路线

### 可继续探索

- [ ] 用 `./serve.sh nospec` 跑 HTTP benchmark，和官方 12.73 tok/s 做 apples-to-apples 对比
- [ ] 跑 `./run.sh benchmark-dflash2`，复现文章 PP85/TG325 数字
- [ ] 接 AnythingLLM 做本地对话 UI
- [ ] 对比 MLX / llama.cpp 在 Mac 上的 GPU 推理方案

---

## 参考链接

- FlagOS 文章：https://mp.weixin.qq.com/s/hANzM9uw2suTMWB8uXzIog
- flagtree-cpu：https://github.com/flagos-ai/flagtree-cpu
- FlagOS 官网：https://flagos.io
- 本地部署目录：`~/qwen38-m5`
