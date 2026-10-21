# RISC-V 向量与矩阵扩展：端侧 AI 系统工程师的技术与产业判断

> **日期**：2026-09-08  
> **视角**：端侧 LLM / VLM / VLA 部署、编译器、Runtime、Linux 与异构芯片适配  
> **结论先行**：RISC-V AI 加速不是“加一条矩阵乘指令”这么简单，而是负载、数据类型、寄存器状态、数据移动、编译器、算子库和 OS 共同决定的系统问题。  
> **后续**：V / vLLM / SGLang 的 09-27 复核见 [接 09-08 长文的跟进](./2026-09-27-riscv-v-vllm-sglang.md)。本文 §8 的截止日期不变，不把后来的计划节点回写成当时事实。

## 摘要

RISC-V 的 AI 能力正在形成一条从成熟到前沿的能力梯度：

1. **RVV 1.0** 提供通用、向量长度无关（VLA）的向量计算，是激活、归一化、Softmax、数据重排和普通矩阵实现的基础。
2. **BF16 等向量扩展**补齐 AI 常用数据类型；`Zfbfmin`、`Zvfbfmin`、`Zvfbfwma` 已正式 ratified。
3. **Zvldot / Zvbdot** 用更轻量的长点积和批量点积服务 GEMV、小矩阵与 batch=1 Decode；截至本文日期，仍应按标准化中表述，不能只根据计划日期宣称已经 ratified。
4. **IME** 复用 RVV 寄存器保存 A/B/C，不增加矩阵数据的独立体系结构状态，面积、功耗和 OS 成本较低。
5. **VME** 用 RVV 提供 A/B，新增矩阵累加器保存 C，以 Outer Product 获得更高 MAC 密度。
6. **AME** 为 A/B/C 引入独立 Tile/Matrix State 和矩阵 Load/Store，性能上限最高，软件和系统复杂度也最高。

对端侧 AI，不能以“峰值 TOPS 最大”直接选择 AME。LLM Prefill、视觉编码器等大 GEMM 容易利用矩阵引擎；batch=1 Decode 更接近 GEMV，常被权重和 KV Cache 的带宽限制，轻量 Dot Product、IME 或高带宽内存可能更有价值。机器人还要满足 20–50 ms 级控制周期，平均吞吐并不是首要指标。

产业已经出现多种先行实现，但大多数是**私有扩展、草案实现或可授权 IP**，不能等同于最终标准兼容硅片。当前最重要的工程问题，是如何在这些不同 ISA 之上形成统一的软件兼容层和可验证的性能基线。

---

## 1. 为什么端侧 AI 开始关注 RISC-V Matrix

传统端侧 RISC-V 的优势是开放 ISA、可裁剪和低功耗；不足是面对大模型和多模态模型时，单靠标量核或普通 RVV 很难同时满足：

- 大矩阵计算吞吐；
- INT8、INT4、BF16、FP8 等低精度计算；
- 权重、激活和 KV Cache 的数据移动效率；
- 端侧 batch=1 的低延迟；
- CPU、Vector、Matrix/NPU 之间的统一编程；
- Linux、Android、RTOS 和裸机部署；
- 不同芯片间的软件可迁移性。

矩阵扩展的价值不是替代 RVV，而是把高复用、高算术强度的矩阵核心交给更密集的 MAC 单元，同时让 RVV 继续处理：

- Activation；
- LayerNorm / RMSNorm；
- Softmax；
- RoPE；
- Reduce；
- Gather / Scatter；
- Layout Transform；
- 量化与反量化；
- 矩阵计算前后的 Element-wise Fusion。

因此合理的端侧 AI 核通常不是“只有 Matrix Engine”，而是：

```text
Scalar Control
    + RVV Vector
    + Dot/Matrix Engine
    + Cache/Scratchpad/Memory
    + Compiler/Runtime
```

## 2. 先从负载出发：Prefill 与 Decode 是两种机器

### 2.1 Prefill：大 GEMM，容易吃到矩阵计算

Prefill 一次处理整段 Prompt，权重可以在多个 Token 之间复用，典型计算形态接近：

```text
[tokens, hidden] × [hidden, output]
```

Prompt 较长时，这是大 GEMM，算术强度较高：

```text
Arithmetic Intensity = FLOPs / Bytes Accessed
```

它更容易进入 Compute-bound 区域，因此：

- 更宽的矩阵 MAC 阵列；
- BF16 / INT8 / FP8；
- 矩阵分块；
- Scratchpad 数据复用；
- VME/AME 级矩阵累加状态

都可能显著提升 TTFT。

### 2.2 Decode：batch=1 GEMV，通常先撞带宽

无投机解码时，每一步只生成一个 Token：

```text
[1, hidden] × [hidden, output]
```

矩阵乘退化为 GEMV。每生成一个 Token，模型仍要读取大量权重；权重使用次数低，算术强度可能接近 1–2 FLOPs/Byte。长上下文下还要读取不断增长的 KV Cache。

因此 batch=1 Decode 常近似：

```text
Token Latency ≈ (Weight Bytes + KV Bytes) / Effective Memory Bandwidth
```

这说明：

- 峰值 TOPS 不等于 Decode tok/s；
- 大矩阵引擎可能利用率很低；
- INT4 的价值不仅是增加 TOPS，更是减少每 Token 的权重读取字节数；
- `Zvbdot`、较小的 IME Tile 或专门 GEMV Micro-kernel 可能比超大 AME 更合适；
- 投机解码通过一次验证多个候选 Token，把小 M 变大，才更容易利用矩阵单元。

一个定量直觉：8B 模型的 INT4 权重约 4 GB。若持续可用内存带宽是 100 GB/s，仅把权重读一遍就至少约 40 ms，对应理想上限约 25 tok/s；实际还要加 KV、激活、反量化和调度。BF16 权重约 16 GB，仅权重读取下界就约 160 ms。因此“Decode 慢就加矩阵阵列”并不完整，应该先回答 batch、权重精度、持续带宽、KV 长度和矩阵利用率。

### 2.3 KV Cache：容量和带宽同时增长

标准 MHA/GQA 的 KV Cache 可粗略计算为：

```text
KV Bytes = 2 × Layers × Batch × Tokens × KV Heads × Head Dim × Bytes per Element
```

以 Llama 3.1 8B 的 32 层、8 个 KV Head、Head Dim 128、BF16 为例，每个 Token 约 128 KiB：

- 4K Context 约 512 MiB；
- 32K Context 约 4 GiB。

Decode Attention 每一步还要扫描历史 KV。GQA/MQA、KV 量化、滑动窗口和片上缓存优化的价值，本质上都是降低这部分容量或访问字节数。提高 batch 可以让 GEMV 更像 GEMM，但 KV 容量和流量也近似随 batch 增长，端侧不能无限组批。

### 2.4 与本机 FlagOS 实验的对应

Mac M5 Pro 上的 FlagOS 实验虽不是 RISC-V，但展示了相同的软件链和负载差异：

```text
FlagGems Triton tl.dot
  → TTIR / TritonCPU IR
  → LLVM IR
  → ARM SDOT / SMMLA
  → JIT Cache / Shared Object
```

实测 PP512/TG128：

- Prefill 74.32 tok/s，基本复现官方 74.93 tok/s；
- No-spec Decode 10.30 tok/s，低于官方 12.73 tok/s；
- DFlash2 Decode 约 22.8 tok/s。

它说明两点：

1. 编译出高效矩阵指令可以直接改善 Prefill；
2. Decode 仍对 Micro-kernel、线程调度和内存带宽高度敏感，投机解码通过改变计算形态获得更大收益。

迁移到 RISC-V 后，需要回答的也是同一组问题：一个 `matmul` 最终降到 RVV、Zvbdot、IME、VME、AME，还是厂商 NPU SDK？

---

## 3. 能力梯度：RVV、Dot Product、IME、VME、AME

## 3.1 RVV：所有路线的通用底座

RVV 1.0 的关键不是某个固定的 128/256/512-bit SIMD 宽度，而是 Vector Length Agnostic：

```text
同一份二进制
  → 查询实现支持的 VL
  → 用 vsetvl/vsetvli 分段处理
  → 在不同 VLEN 的芯片上保持正确
```

RVV 有 32 个向量寄存器，`VLEN` 由实现决定。软件使用 `SEW`、`LMUL`、Tail/Mask Policy 描述数据组织。

对 AI 而言，RVV 的价值包括：

- 覆盖非矩阵算子，避免所有工作都绕到 NPU；
- 提供矩阵扩展的输入、数据重排和后处理；
- 让一个算子库在不同实现宽度上保持二进制可移植；
- 为编译器自动向量化和 C Intrinsics 提供标准入口。

它的限制是：普通 RVV 实现 GEMM 时，需要大量指令维持矩阵分块和累加；Vector Register File 的容量、端口和数据搬运会限制 MAC 密度。

## 3.2 AI 数据类型扩展

已正式 ratified 的 BF16 v1.0 包括：

- `Zfbfmin`：标量 BF16 转换；
- `Zvfbfmin`：向量 BF16 转换；
- `Zvfbfwma`：BF16 × BF16，FP32 累加的 widening multiply-add。

端侧芯片评估不能只问“支持 BF16/INT8 吗”，还要问：

- 输入、权重、累加、输出分别是什么类型；
- 是否支持混合精度；
- Scale/Zero Point 是 per-tensor、per-channel 还是 per-group；
- INT4 是原生计算还是先 unpack 到 INT8；
- 是否支持结构化稀疏；
- 转换和 Layout 指令的开销；
- 精度对齐使用什么模型与数据集。

FP8、FP4、Block/Microscaling 等能力仍在持续演进。产品宣称支持某种类型，不代表编译器、算子库和模型格式已经可用。

## 3.3 Zvldot / Zvbdot：轻量点积路线

Dot Product 是 RVV 到完整 Matrix Extension 之间的重要层：

- `Zvldot`：两个长向量点积，结果累加到向量寄存器中的标量；
- `Zvbdot`：一个向量与八个向量做批量点积，生成八个累加结果。

它适合：

- batch=1 LLM Decode；
- GEMV；
- 小矩阵；
- 卷积内核；
- 不值得启动大型矩阵引擎的短计算。

优势是新增状态少、编译器和 OS 成本较低；不足是大 GEMM 的峰值和数据复用能力有限。

截至 2026-09-08，官方页面中的里程碑日期存在“计划”和“实际进度”不一致的信息。稳妥表述是：**Zvldot/Zvbdot 已进入较后期标准化阶段，但在 ratified extension 清单得到明确确认前，不把计划批准日期当作已完成事实。**

## 3.4 IME：Matrix-in-Vector

IME（Integrated Matrix Extension）的定义特征是：矩阵数据不增加新的体系结构状态，A、B、C 都使用现有 RVV 寄存器。

```text
A Tile → Vector Registers
B Tile → Vector Registers
C Tile → Vector Registers
```

优点：

- 复用 RVV Register File 和控制语义；
- 芯片面积和功耗相对可控；
- OS、Hypervisor 和 ABI 改动较小；
- 适合 Embedded、Edge、Application Processor；
- 不同 VLEN 之间仍追求二进制可移植。

代价：

- A/B/C 争抢有限的 Vector Register；
- Register File 容量与读写端口限制吞吐；
- 很宽的 VLEN 会增加物理实现、旁路和时序压力；
- 编译器必须处理 Tile Layout、Packing 和 LMUL 压力。

标准 IME 的目标包含 INT8、BF16、FP8 以及传统 FP32/FP64，并将 OpenBLAS/oneDNN 类库视为早期软件验证对象。

## 3.5 VME：Vector 喂数，Matrix Accumulator 累加

VME（Vector-Matrix Extension）读取两个向量，计算 Outer Product，并累加到新增的 Matrix Accumulator：

```text
A/B → RVV Vector Registers
C   → Dedicated Matrix Accumulator
```

它的设计取舍是：

- RVV 继续承担 Load/Store、激活、归一化和数据重排；
- C 累加状态靠近 MAC 阵列，减少 Vector Register File 压力；
- 不要求 AME 那样的完整二维 Matrix Load/Store；
- 可从较小端侧单元扩到高吞吐矩阵引擎；
- 需要新增 Accumulator 的生命周期、Move、Spill 和上下文管理。

VME 与 Arm SME 的“Vector + Matrix Accumulator”思路较接近。它是端侧高性能实现中很有吸引力的折中：比 IME 更容易扩吞吐，比 AME 更紧密复用 RVV 软件生态。

## 3.6 AME：独立 Matrix/Tile State

AME（Attached Matrix Extension）引入独立的矩阵状态，可包含：

- A/B/C Tile Registers；
- Matrix Load/Store；
- Matrix-Matrix、Vector-Matrix、Scalar-Matrix；
- Permutation、Convolution、Reduction；
- 稀疏压缩/解压；
- Mask；
- 自己的内存模型约束。

优点：

- 最大的数据复用空间；
- 矩阵计算峰值最高；
- 可以不依赖 RVV；
- 可以扩展为较独立的 Tensor Accelerator。

代价：

- 新体系结构状态最大；
- 指令编码、内存一致性和异常精确性更复杂；
- 编译器需要独立 Tile Register Allocation；
- Linux、KVM、Debugger、Signal ABI 都要理解新状态；
- 小 batch 或小矩阵可能吃不满；
- 产品间实现差异如果过大，会重新制造软件碎片。

AME 更像“由 CPU 指令流控制的紧耦合 Tensor Engine”，不是普通 RVV 上再加几个 MAC。

## 3.7 四条路线放在一起

| 路线 | A/B 来源 | C 累加位置 | 新增状态 | 性能上限 | 系统复杂度 | 典型适配 |
|---|---|---|---:|---:|---:|---|
| RVV + Zvbdot | RVV | RVV | 很少 | 低–中 | 低 | Decode/GEMV、小矩阵 |
| IME | RVV | RVV | 少量 CSR | 中 | 低–中 | 面积/功耗敏感端侧 |
| VME | RVV | Matrix Accumulator | 中 | 中–高 | 中 | 高性能 Edge / AI CPU |
| AME | Matrix State | Matrix State | 大 | 最高 | 高 | 大 GEMM、HPC、独立 AI Engine |

这四条路线不是简单替代关系。一个 SoC 可能同时有 RVV、Dot Product 和 Matrix Engine，由 Runtime 按 Shape、Datatype 和延迟选择。

---

## 4. LLM、VLM、VLA 分别需要什么

## 4.1 LLM

LLM 主要算子：

- Q/K/V/O Projection；
- Attention；
- MLP Gate/Up/Down；
- RMSNorm；
- RoPE；
- Softmax；
- KV Cache 读写；
- Sampling。

合理映射：

```text
大 GEMM / Prefill       → VME/AME/高吞吐 IME
batch=1 Decode GEMV    → Zvbdot/IME/专用 INT4 GEMV
Norm/Softmax/RoPE      → RVV
KV Cache               → Memory System，而非 Matrix TOPS
Sampling/控制逻辑       → Scalar/RVV
```

## 4.2 VLM

VLM 增加：

- Vision Encoder；
- Patch Embedding；
- 多模态 Projector；
- 图像/视频 Token；
- 更长 Prompt 和更大 KV。

Vision Encoder 的卷积和大矩阵较容易利用 Matrix Engine，但端侧还要关注：

- 图像分辨率与 Patch 数；
- 首帧 TTFT；
- 摄像头到内存的零拷贝；
- NPU/CPU 切图造成的数据搬运；
- Vision Encoder 与 LLM 是否共享量化格式；
- 多模态模型未使用时能否不加载 Vision 权重。

## 4.3 VLA 与具身智能

VLA 在 VLM 后增加动作 Token 或动作头。关键指标从“回答速度”变成“控制回路能否闭合”：

```text
Camera → Encode → Fuse → Reason → Action → Actuator
```

如果控制周期要求 20 ms，而完整 VLA 推理是 80 ms，仅提高矩阵 TOPS 不一定能解决。系统可能需要：

- Action Chunking；
- Fast Policy + Slow VLM 双系统；
- 异步感知；
- 降低视觉帧率或分辨率；
- 小模型处理高频控制，大模型处理低频规划；
- 预取、流水化和跨帧状态复用。

端侧矩阵扩展必须放进完整 Sensor-to-Action 延迟中评估。

---

## 5. 编译器与 Runtime：真正决定 ISA 能否被模型使用

一颗支持 Matrix ISA 的芯片，并不会自动让 PyTorch/ONNX 模型变快。完整链路是：

```text
PyTorch / ONNX / JAX
  → Graph Capture / Export
  → Operator Decomposition & Fusion
  → Tiling / Layout / Quantization
  → RVV / Dot / IME / VME / AME Lowering
  → LLVM/GCC Codegen 或 Vendor Library
  → Runtime Dispatch
  → Kernel Cache / Profiling / Fallback
```

## 5.1 编译器必须解决的问题

### Shape 与 Tiling

同一个 MatMul 要根据 M/N/K 选择不同路径：

- Prefill 大 M；
- Decode M≈1；
- 投机验证 M≈K+1；
- Vision Encoder Shape 相对稳定；
- Dynamic Shape 需要运行时选择。

固定一个“大矩阵核”无法覆盖全部 Shape。

### Register Allocation

- RVV：分配 Vector Register、SEW、LMUL；
- IME：A/B/C Tile 都压在 Vector Register 中；
- VME：管理 Vector Operand 与 Matrix Accumulator 生命周期；
- AME：增加独立 Tile Register Allocation、Spill 和 Reload。

### Layout 与 Packing

低精度性能往往取决于物理布局：

- INT4 如何 Pack；
- Group Scale 放在哪里；
- K/N 维如何分块；
- Row-major/Column-major；
- Matrix Accumulator 如何 Move；
- 是否为结构化稀疏重新排布。

如果每次调用都重新 Pack，理论 TOPS 很容易被预处理吃掉。

### Fusion

典型融合包括：

- MatMul + Bias；
- Gate + Up + SiLU；
- Norm + Quant；
- Dequant + MatMul；
- QKV Projection；
- KV 写入。

Fusion 的目标不仅是少发一个 Kernel，更是减少内存往返。

## 5.2 LLVM/GCC、MLIR/IREE/TVM、Triton 的分工

- **LLVM/GCC**：ISA、Intrinsics、Register Allocation、Machine Code；
- **MLIR/IREE**：多层 IR、图到 Loop/Vector/LLVM 的系统化 Lowering，适合异构端侧和静态部署；
- **TVM**：计算与 Schedule 分离、Auto-tuning、多后端；
- **Triton/FlagTree**：以 Kernel DSL 表达 Tile 和数据布局，再降到芯片后端；
- **Vendor SDK**：提供已手调 Kernel、图编译器和 NPU Runtime；
- **llama.cpp/ggml**：很多核心算子自带模板和手写 Micro-kernel，不一定经过通用图编译器。

需要区分：上游 Triton 官方定位仍以 GPU Kernel DSL 为主，截至本文日期没有正式 RISC-V CPU Backend；FlagTree/Triton-CPU 是独立扩展路线，不能把“会写 Triton”直接等同于“已有 RISC-V Matrix 后端”。IREE 则已经展示了较完整的 RISC-V 路径，包括模型导入、Data Tiling、`mmt4d` Micro-kernel、LLVM Bitcode 和 RVV Codegen，但当前矩阵扩展仍主要依赖 Target-specific Micro-kernel/Intrinsic。

对于 RISC-V Matrix，短期最现实的路径通常不是依赖“自动矩阵化”，而是：

1. LLVM/GCC 支持汇编和 Intrinsics；
2. 算子库提供手调 GEMM/GEMV；
3. Runtime 按 Shape/Datatype Dispatch；
4. IREE/TVM/FlagTree 等逐步建立自动 Lowering。

## 5.3 为什么需要统一软件接口

如果 IME、VME、AME 和厂商私有 NPU 都要求模型框架直接适配，RISC-V 的开放会变成新的碎片化。

理想层次是：

```text
Framework / Operator API
        ↓
统一 Matrix / AI Compatibility Layer
        ↓
RVV | Zvbdot | IME | VME | AME | Vendor NPU
```

上层应表达：

- MatMul Shape；
- Datatype；
- Layout；
- Quantization Scheme；
- Sparsity；
- Epilogue/Fusion；
- Latency/Workspace 约束。

底层再选择 ISA。用户不应在模型代码里硬编码某一家 Matrix Instruction。

---

## 6. OS、ABI 与虚拟化：矩阵状态越大，系统成本越高

这是端侧 AI 系统岗位容易被忽视、但很适合 OS 背景展开的部分。

## 6.1 RVV 已经带来的问题

RVV 的寄存器状态随 VLEN 增长。Linux 需要处理：

- Context Switch；
- Signal Frame / `ucontext`；
- `ptrace` / GDB；
- Core Dump；
- Syscall 边界；
- Kernel-mode Vector；
- KVM Guest State；
- 跨任务数据泄漏。

仅 32 个向量寄存器的数据区就有 `32 × VLEN / 8` Byte；VLEN 越大，Signal Frame、Context Save 和 VM Migration 的数据量越高。

Linux 使用 Vector State 的 Off/Initial/Clean/Dirty 等状态，避免未使用 RVV 的线程每次都保存大寄存器文件。只有脏状态才需要实际 Save/Restore。

## 6.2 IME/VME/AME 的增量成本

### IME

- 复用 RVV 状态；
- 只可能增加少量 CSR；
- psABI 和 Context Switch 改动相对小；
- 对容器几乎透明，对 VM 仍需暴露能力位。

### VME

- 新增 Matrix Accumulator；
- Signal、ptrace、core dump 要定义可见状态；
- KVM 需要 Save/Restore 和 Migration ABI；
- 可考虑 Lazy Context；
- 需要防止上一个租户的 Accumulator 数据泄漏。

### AME

- 独立 A/B/C Tile State 可能很大；
- Context Switch 成本最高；
- Lazy Save/Restore、禁用/启用策略更重要；
- 可能涉及二维 Load/Store 和内存模型；
- VM Live Migration 必须处理实现大小、版本和兼容；
- Debugger、Crash Dump 和性能计数器都要扩展；
- 多核共享 Matrix Engine 时还要定义调度、QoS 和故障域。

## 6.3 端侧不等于不需要虚拟化

AI PC、车载和机器人同样可能同时运行：

- Host OS；
- Android/Linux Guest；
- 安全域；
- 多个容器；
- 第三方模型应用；
- 实时控制任务。

因此芯片评审不能只看单进程 Benchmark，还要问：

- Matrix State 是否可抢占；
- 抢占延迟；
- 多进程公平性；
- VM 是否可用；
- 是否支持性能隔离；
- Driver/Runtime 崩溃是否影响整机；
- 固件是否可升级和回滚。

---

## 7. 产业现状：标准、私有扩展、IP 和硅片要分开

## 7.1 SpacemiT K1 / K3：IME-like 私有实现

### K1 / X60 + A60

公开文档列出：

- `Xsmti8i32mm`；
- `Xsmti8i32mm_slide`；
- INT8 × INT8 → INT32 Matrix Multiply。

K1 资料存在两种命名口径：早期 Datasheet 把八核处理器统称为 X60，较新的 AI 架构文档则区分 4 个普通 X60 与 4 个带矩阵能力的 A60 智算核。上述矩阵扩展只在带 AI 能力的 Cluster 上提供，四核合计约 2 TOPS。K1 已有可购买芯片和开发板，是适合动手研究的 Matrix-in-Vector 案例。

### K3 / A100

公开资料显示其扩展到：

- INT4 / INT8；
- FP16 / BF16；
- FP32 累加；
- 4:2 结构化稀疏；
- 更宽的 Matrix Datapath；
- 宣称最高约 60 TOPS（INT4 Sparse）。

K3 已有 2026-04-30 量产交付公告和可购买的平台/模块证据；它是当前观察“CPU、RVV 与专用矩阵数据通路融合”的重要商品案例，但其 SpacemiT-IME 仍是厂商私有扩展。

必须使用的准确措辞：

> SpacemiT-IME 是厂商扩展，复用 RVV Register File，技术路线与标准 IME 接近；它不因此自动成为最终 RISC-V IME 兼容实现。

其工具链和优化库的开放程度，也是评估生态成熟度的重要指标。

## 7.2 XuanTie C907 / C950 + TPE：MME/AME-like

玄铁较早在 C907 上实现自有 Matrix-Multiply Extension（MME），并配套：

- Matrix ISA；
- GNU/LLVM/QEMU；
- HHB 模型部署工具；
- SHL/csi-nn 类算子支持。

C950 则公布了与 TPE（Tensor Processing Engine）连接的 XuanTie AME v0.5 路线，支持 INT4、FP8、BF16 等 AI 类型。

准确判断：

- 它们证明 AME-like 独立矩阵状态可以形成完整软硬件栈；
- XuanTie MME/AME 是私有提案或标准化输入；
- C950/TPE 更应视为可授权 IP/公布设计，不能直接描述为已经大规模可购买的标准 AME 芯片。

## 7.3 SiFive Intelligence XM Gen 2：VME-like IP

SiFive XM Gen 2 的公开架构是：

- 4 个 X300 Core；
- Vector Unit 处理非矩阵层；
- Fat Outer Product Matrix Engine；
- Source 来自 Vector Register；
- Destination 为 Matrix Accumulator；
- 每 Cluster 宣称 16 TOPS INT8/GHz、8 TFLOPS BF16/GHz；
- 每 Cluster 宣称 1 TB/s Sustained Bandwidth。

这与 VME 的架构定义高度一致。它是可授权 IP，而不是普通零售芯片；客户 SoC 的具体 ISA 版本和量产状态需要单独确认。

## 7.4 Epic Semi Contrail AIX：宣称 VME 的平台

Contrail AIX 公布：

- 32 个 RISC-V CPU Core；
- 16 个 AI Acceleration Core；
- RVV 1.0；
- VME Matrix Acceleration；
- 最高约 75 TOPS INT8；
- DDR5、PCIe 5.0、CXL 和虚拟化。

2026 年已有平台发布和公开演示，但大规模商用供货与正式 VME 版本兼容性仍需厂商证据。

## 7.5 Stream Computing：开放规范与 PoC

Stream Computing 提供过自己的 Matrix ISA v0.5 及配套：

- LLVM-based Compiler；
- Spike Simulator；
- GDB/OpenOCD；
- Chipyard/SCOOP PoC Core。

它的意义是展示“ISA 之外至少还要交付编译器、模拟器、Debugger、Kernel Library”。它属于标准化输入和 PoC，不应等同于正式标准量产芯片。

## 7.6 其他值得关注的厂商 IP

- **Andes AX46MPV + AMM**：2048-bit RVV 核加厂商 Matrix Multiplication Extension，支持 INT8 和二维 Load/Store；属于已走到客户流片阶段的私有 Matrix IP，不是正式 IME。
- **Semidynamics Tensor Unit / Cervell**：Vector Unit 连接 Cache-coherent Tensor Unit，使用私有 Matrix 指令；Cervell 整体更适合称为可编程 RISC-V NPU IP。

这类产品说明私有矩阵 IP 的商业进度可能领先于标准，但也进一步强化了统一 Compiler/Runtime Compatibility Layer 的必要性。

## 7.7 哪些不能算标准 Matrix Extension

以下情况不能因为“有 RISC-V + 有矩阵计算”就称为 IME/VME/AME：

- RISC-V 只负责控制，独立 NPU 使用自己的 Command Queue；
- Tenstorrent Tensix 内部用 RISC-V 小核控制矩阵单元，但编程模型是 TT-Metalium；
- 仅支持 RVV 的 CPU；
- 通过 PCIe/MMIO 外挂的 AI 加速器；
- 厂商文档只写 TOPS，没有 ISA、寄存器或工具链说明。

---

## 8. 标准化状态：截至 2026-09-08 应如何准确表述

| 项目 | 稳妥状态 |
|---|---|
| RVV 1.0 | 已 ratified，通用基础 |
| BF16 v1.0 | 已 ratified：Zfbfmin、Zvfbfmin、Zvfbfwma |
| Zvldot / Zvbdot | 后期标准化中；不要把计划日期直接当成完成证明 |
| IME / Zvvm family | 2026-08-24 官方 Release 仍标为 v0.9 ARC Review Candidate，并明确未 ratified |
| VME | Task Group 推进；计划 2026-09-25 Freeze、2026-11-18 BoD 批准，这些是未来计划节点 |
| AME | Task Group 推进；计划 2027-02-07 Freeze、2027-04-29 BoD 批准，范围和交付周期最大 |

一个重要方法论：

> `Ratification Plan` 页面写的是计划，不是事实日志。是否已经 ratified，应交叉检查 RISC-V Ratified Extensions 清单、正式 Specification Library、BoD/TSC 公告和版本 Tag。

---

## 9. 如何评估一颗 RISC-V 端侧 AI 芯片

## 9.1 不要先问 TOPS，先问负载

固定：

- 模型：LLM/VLM/VLA 名称和版本；
- Weight/Activation/KV 精度；
- Prompt 长度；
- Output 长度；
- batch=1 或并发；
- 图像分辨率、帧率；
- 控制周期；
- 功耗和温度边界。

## 9.2 芯片指标

- Sustained Memory Bandwidth，而非理论峰值；
- Cache/Scratchpad 容量；
- RVV VLEN、Lane 和 Register Port；
- Matrix Tile/Accumulator 大小；
- 支持的数据类型和累加精度；
- INT4 Packing/Unpacking；
- 稀疏是否要求固定 Pattern；
- Matrix Engine 启动和同步延迟；
- CPU/Matrix/NPU 数据是否零拷贝；
- DMA/IOMMU/一致性；
- 热设计下的持续频率。

## 9.3 软件指标

- GCC/LLVM 是否 Upstream；
- 是否只有 Intrinsics，还是可自动 Lower；
- PyTorch/ONNX/IREE/TVM/Triton 后端；
- llama.cpp/ggml 是否有 Kernel；
- 模型支持是“跑通”还是“性能优化”；
- Unsupported Op 如何 Fallback；
- Fallback 是否导致频繁数据搬运；
- Profiler 能否看到每个 Op 的时间、带宽和命中路径；
- Kernel Cache 和版本兼容；
- Quantization Tool 是否开放；
- 精度回归和性能基线是否可复现。

## 9.4 系统指标

- Linux Kernel 支持；
- Signal/ptrace/core dump；
- KVM/虚拟化；
- Context Switch 开销；
- 多进程和多租户；
- 电源管理、DVFS、Thermal Throttling；
- Firmware/Driver/Runtime 的升级和回滚；
- 安全隔离和故障恢复。

## 9.5 推荐基准

至少拆成：

```text
Micro-kernel:
  GEMM / GEMV / Dot / Norm / Softmax / Layout / Quant

Model Stage:
  Prefill TTFT
  Decode TPOT
  Vision Encoder latency
  Projector latency
  Action head latency

System:
  Peak RSS / KV growth
  Sustained power
  Thermal steady state
  Context switch / multi-process interference
  CPU↔NPU transfer
```

只报端到端 tok/s 会掩盖问题所在。

---

## 10. 对端侧 AI 行业的几个判断

### 判断一：未来不是 IME/VME/AME 三选一，而是软件统一、硬件分层

不同功耗和性能点不会只剩一种 ISA。更可能是：

```text
低功耗端：RVV + Dot / IME
高性能端：RVV + VME
大型加速：AME / 独立 NPU
```

竞争焦点将从“谁定义了最多指令”转到“谁能被同一个模型编译栈稳定使用”。

### 判断二：Decode 会迫使架构回到内存系统

Matrix TOPS 会改善 Prefill 和视觉编码器，但 batch=1 Decode 仍会把权重和 KV 流过内存。端侧更需要：

- 低比特权重；
- 高有效带宽；
- 大容量统一内存；
- KV 压缩；
- GQA/MLA；
- 投机解码；
- Shape-aware Micro-kernel。

### 判断三：编译器不是“支持一条指令”就完成

真正的支持至少包括：

- Intrinsics；
- Tiling；
- Layout；
- Register Allocation；
- Quantization；
- Fusion；
- Runtime Dispatch；
- Profiler；
- 模型级精度和性能验证。

### 判断四：端侧异构最大的隐性成本是搬运

一个算子在 NPU 上快 2 倍，但 CPU↔NPU 拷贝、Layout 转换和同步花了更多时间，端到端仍会变慢。评审必须看完整 Subgraph，而不是单算子峰值。

### 判断五：OS 是 Matrix ISA 商业化的必要部分

AME/VME 新增的状态如果没有 Linux、KVM、Debugger 和安全隔离，芯片只能跑 Demo，难以进入 AI PC、机器人和多应用智能终端。

---

## 11. 面试时可以怎么聊

## 11.1 两分钟版本

> 我把 RISC-V AI 加速看成一条从 RVV、Dot Product 到 IME、VME、AME 的能力梯度。RVV 负责通用向量和非矩阵算子；Zvbdot 更适合 batch=1 Decode/GEMV；IME 复用 Vector Register，适合面积和功耗敏感端侧；VME 用 Vector 喂 A/B、专用 Accumulator 保存 C，是性能与复杂度的折中；AME 有完整独立 Tile State，吞吐最高，但编译器、OS 和虚拟化成本也最高。
>
> 对端侧不能只比较 TOPS。Prefill 和 Vision Encoder 是大 GEMM，矩阵引擎收益明显；Decode 往往被权重和 KV 带宽限制。评估时我会固定模型、精度、PP/TG 和功耗，分别测 TTFT、TPOT、内存、数据搬运和热稳态。
>
> 产业上已经有 SpacemiT、玄铁、SiFive、Epic Semi 等先行实现，但要区分厂商私有扩展、草案 IP 和正式标准兼容硅片。真正决定生态的是 LLVM/IREE/TVM/算子库能否在不同 ISA 下面形成统一接口，以及 Linux/KVM 是否能管理新增 Matrix State。

## 11.2 可以主动问对方

1. 你们关注的是 RVV 上的 Dot/IME，还是带独立 Accumulator/Tile State 的 VME/AME？
2. 目标负载是 LLM batch=1 Decode、VLM Vision Encoder，还是 VLA 控制闭环？
3. 现在的软件入口是 LLVM Intrinsics、IREE/MLIR、TVM、Triton，还是厂商算子库？
4. 模型不支持的算子如何 Fallback？CPU/NPU 切换的数据搬运占比是多少？
5. Matrix State 是否进入 Linux Context Switch、Signal ABI 和 KVM？
6. 性能数据是 Micro-kernel TOPS，还是热稳态下的模型 TTFT/TPOT？
7. 私有扩展将来如何兼容标准 IME/VME/AME？是编译器重定向，还是硬件同时兼容？

## 11.3 不要说的三句话

- “AME 一定比 IME 更适合端侧。”
- “SpacemiT-IME/XuanTie AME 已经等于 RISC-V 正式标准。”
- “芯片支持 INT4 和 60 TOPS，所以 LLM Decode 一定快。”

---

## 12. 与个人经验的连接方式

可以把已有经验连成以下主线：

1. **OpenCloudOS / 多架构适配**：证明理解 ISA、工具链、内核和发行版不是分开的。
2. **六家 GPU/NPU Driver + SDK**：说明“芯片支持”必须收敛到 Runtime、Framework 和模型验收。
3. **FlagOS M5 实验**：展示从 Triton 源算子追到 TTIR、LLVM IR 和 ARM `SMMLA` 的真实编译链观察。
4. **PP512/TG128 基准**：用 Prefill 基本复现、Decode 存在差距说明按阶段定位性能，而不是只报总 tok/s。
5. **Packages-Agent / Local Agent**：端侧 Agent 不只需要模型，还需要 OS 权限、工具调用、可复现环境和安全边界。

准确定位：

> 我不是宣称自己已经实现 RISC-V Matrix Compiler，而是能从 OS、工具链、Runtime、算子和模型负载之间建立验收闭环，并知道进入新 ISA 后应该测什么、问什么、由谁交付。

---

## 参考资料

### RISC-V 官方

- RISC-V Vector Extension：https://docs.riscv.org/reference/isa/unpriv/v-st-ext.html
- Ratified Extensions：https://lf-riscv.atlassian.net/wiki/spaces/HOME/pages/16154732/Ratified+Extensions
- BF16 v1.0：https://docs.riscv.org/reference/isa/extensions/bf16min/_attachments/riscv-bfloat16.pdf
- IME Ratification Plan：https://riscv.atlassian.net/wiki/spaces/IMEX/pages/598867969/IME+Ratification+Plan
- IME 官方 Releases：https://github.com/riscv/integrated-matrix-extension/releases
- VME Charter：https://riscv.atlassian.net/wiki/spaces/VMEX/pages/663912452
- VME Ratification Plan：https://riscv.atlassian.net/wiki/spaces/VMEX/pages/663617995/Ratification+Plan
- AME Charter：https://riscv.atlassian.net/wiki/spaces/AMEX/pages/55083388/Charter
- AME Ratification Plan：https://riscv.atlassian.net/wiki/spaces/AMEX/pages/55083420/AME+Ratification+Plan
- Zvldot/Zvbdot Ratification Plan：https://riscv.atlassian.net/wiki/spaces/USXX/pages/591233026
- RISC-V Annual Report 2025：https://riscv.org/wp-content/uploads/2026/01/RISC-V-Annual-Report-2025.pdf
- RISC-V Matrix Software Compatibility Discussion：https://lists.riscv.org/g/tech-attached-matrix-extension/message/311

### 产业与开源

- SpacemiT AI Architecture Docs：https://github.com/spacemit-com/docs-ai
- SpacemiT K3 Docs：https://github.com/spacemit-com/docs-chip
- SpacemiT K3 Product：https://spacemit.com/products/keystone/k3
- XuanTie Matrix Extension：https://github.com/XUANTIE-RV/riscv-matrix-extension-spec
- RISC-V International: XuanTie MME/C907：https://riscv.org/blog/enhancing-the-future-of-ai-ml-with-attached-matrix-extension/
- SiFive Intelligence XM：https://www.sifive.com/cores/intelligence-xm-series
- Epic Semi Contrail AIX：https://www.epicsemi.com/products/contrail/compute/contrail-aix/
- Andes Matrix AI 资料：https://www.andestech.com/en/2025/05/12/andes-technology-showcases-risc-v-ai-leadership-at-risc-v-summit-europe-2025/
- Semidynamics Tensor Unit：https://semidynamics.com/technology/tensor-unit
- Stream Computing Matrix v0.5：https://riscv.org/blog/stream-computing-risc-v-matrix-extension-open-source-project-upgrades-to-version-0-5-supporting-vector+matrix-implementation/

### 软件与负载

- RVV C Intrinsics：https://github.com/riscv-non-isa/riscv-rvv-intrinsic-doc
- IREE on RISC-V：https://riscv.org/blog/co-developing-risc-v-ai-solutions-using-vector-extensions-in-renode-with-kenning/
- IREE RISC-V 2026 实践：https://iree.dev/community/blog/2026-07-23-running-models-on-risc-v-with-iree/
- Linux RISC-V hwprobe：https://docs.kernel.org/arch/riscv/hwprobe.html
- NVIDIA Prefill/Decode Roofline：https://developer.nvidia.com/blog/co-designing-ai-model-attention-for-fast-interactive-long-context-inference/
- 本仓库 FlagOS M5 实践：[FlagOS + Qwen3.8-27B 部署实践](./2026-09-01-flagos-qwen38-deployment-practice.md)

