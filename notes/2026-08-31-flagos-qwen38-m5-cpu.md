# FlagOS 实战：Mac M5 Pro 纯 CPU 跑 Qwen3.8-27B

## 来源

- **标题**：FlagOS 实战｜Mac M5 Pro 纯 CPU 跑 Qwen3.8-27B，输出吞吐达到 27.65 tok/s
- **作者/机构**：智源 FlagOpen
- **链接**：https://mp.weixin.qq.com/s/hANzM9uw2suTMWB8uXzIog
- **日期**：2026-08-31

## 摘录

### 核心结论

在 Mac M5 Pro、纯 CPU、Batch=1 条件下：

| 场景 | Prefill | Decode | 完整请求吞吐 |
|------|---------|--------|-------------|
| 基础推理（no-spec，PP512/TG128） | 74.93 tok/s | 12.73 tok/s | 38.07 tok/s |
| DFlash2 投机解码（PP85/TG325） | — | — | **27.654 tok/s**（2.22× no-spec） |

对比参考：vLLM CPU 参考路线 Decode 6.44 tok/s；llama.cpp Q4_K_M Decode 11.68 tok/s。

### 模型特点

Qwen3.8-27B 语言模型主干 64 层混合网络：
- 16 层全注意力
- 48 层 Gated DeltaNet（GDN）线性注意力，需维护循环状态
- 使用 packed W4A8 checkpoint

### FlagOS 技术栈

```
vllm-plugin-FL  → 模型接入 vLLM、ARM CPU 平台适配、W4A8 算子
FlagGems         → 量化 Linear、MLP 融合、GDN 优化算子（Triton）
flagtree-cpu     → Triton 算子编译为 ARM 指令（NEON SDOT / SMMLA）
libtriton_jit    → 内核 JIT 编译、缓存、C++ 调用
运行时           → UniProc 模式、OpenMP 并行、动态分块
```

### 关键优化点

1. **flagtree-cpu**：单 token Decode 用 NEON SDOT，多 token 块用 SMMLA
2. **FlagGems 融合**：MLP Gate/Up 共享量化；GDN qkvz/BA 投影复用输入，串成连续路径
3. **DFlash2 投机解码**：轻量 drafter 一次并行准备 7 个候选，完整模型统一验证（M=8 block）
4. **三阶段 DFlash2 优化**（PP85/TG256）：累计提升 29.59%
   - M=8 验证路径微内核（+17.07%）
   - M5 Pro 并行策略调优（+7.67%）
   - GDN 投机解码路径合并（+2.81%）

### 快速上手

```bash
# 下载模型
./setup_and_run_qwen38_m5.sh models

# 构建环境（约 15 分钟，14 GB）
./setup_and_run_qwen38_m5.sh env

# 基础推理
./setup_and_run_qwen38_m5.sh run-nospec "你的 prompt"

# DFlash2 加速
./setup_and_run_qwen38_m5.sh run-dflash2 "你的 prompt"
```

- 目标设备：Mac17,9（M5 Pro），需 Xcode CLT + Homebrew
- 模型：`FlagRelease/Qwen3.8-27B-W4A8-arm-FlagOS-Express`（ModelScope）
- GitHub：https://github.com/flagos-ai/flagtree-cpu

### 关于 FlagOS

北京智源研究院发起的异构 AI 芯片开源软件栈，目标「一次开发、跨芯迁移」。包含算子库、跨芯编译器、并行训推框架等。

- 官网：https://flagos.io
- GitHub：https://github.com/flagos-ai

## 我的想法

<!-- 待补充：与 AGI 学习思路的关联 -->
