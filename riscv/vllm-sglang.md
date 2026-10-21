# RISC-V V、vLLM、SGLang：接 09-08 长文的跟进

> **日期**：2026-09-27  
> **背景**：接着 [向量与矩阵扩展](./vector-matrix-edge-ai.md) 往下看。那篇把 **V / RVV → Zvbdot → IME / VME / AME** 和公开 IP 叙事讲清楚了，但推理框架只写到 IREE / Triton，没有落到现在在跟的 **vLLM、SGLang 上游**。  
> **性质**：状态复核，不是重写长文。ISA 判断纪律仍用长文 §8：计划日期 ≠ 已 ratified。  
> **目录**：[`agimind/riscv/`](./README.md)（只跟开源上游；不含公司产品）。

---

## 1. 长文里已经有的，和这次要跟的

| 长文位置 | 已经写了什么 | 这次补什么 |
|---|---|---|
| §3、§8 | V 是底座；Zvbdot / IME / VME / AME 怎么分层、怎么措辞 | 09-27 仪表盘有没有翻面 |
| §7.3 | SiFive XM Gen 2 是 VME-like IP，不是零售硅片 | 没有新产品页级变化，判断保持 |
| §5、§9.3 | 软件入口写 LLVM / IREE / TVM / Triton | **vLLM 主干已有 RVV；SGLang 还在三件套 PR** |

一句话：长文回答「算力梯度是什么」；这篇回答「推理栈现在跟到哪」。

---

## 2. V 这一线：09-08 的判断还站得住

对照长文 §8，今天只核「有没有从计划变成事实」。

| 项目 | 09-08 长文 | 09-27 | 改口没有 |
|---|---|---|---|
| RVV 1.0 | 已 ratified | 仍在 Ratified Library `v20260120`；RVA23 强制带 V | 不用改 |
| BF16 三件套 | 已 ratified | 仍是 `Zfbfmin / Zvfbfmin / Zvfbfwma` | 不用改 |
| Zvldot / Zvbdot | 后期标准化中，别把计划当完成 | 仪表盘仍标 **Exposed**（最近更新 07-09） | 不用改；仍不能说已批准 |
| IME | 08-24 Release 还是 v0.9，未 ratified | 仪表盘 **On Track**（09-21 动过），窗口写到 27Q1 | **不要**因为计划写过 08-27 就改成已批准 |
| VME | 计划 09-25 Freeze、11-18 BoD | 仪表盘仍 **On Track**（07-29） | Freeze 是否完成，等正式公告，不靠计划表 |
| SiFive XM | VME-like 可授权 IP | 官方页仍是向量源 + 独立累加器、Fat Outer Product | 不用改 |

仪表盘入口：[riscv.github.io/adm-spec-dashboard](https://riscv.github.io/adm-spec-dashboard/)。它只用来看进度条，**不替代**长文里的 Ratified Library / Release tag 核对。

对推理栈的含义没变：vLLM / SGLang 现在吃的是 **RVV 1.0 + 可选 zvfh / zvfbfmin**，不是 IME/VME。SiFive XM 那套矩阵指令，这两家框架都还没接。

---

## 3. vLLM：主干能跑，官方仍不当发行目标

09-16 报告的结论今天还成立。本地 HEAD 已到 `7bbce752`，但 09-16 之后**没有新的 RISC-V 合入**；最近一条仍是 08-14 的 `#51099`。

**能用**：CPU 后端 + RVV kernel，VLEN 128/256，fp32 / fp16 / bf16，部分 W4A16 / W4A8 / W8A8。

**不能用**：FP8 KV、chunked prefill、prefix caching、`torch.compile`。官方安装文档、wheel、CI、Docker 都还没有 RISC-V。

在途（都还 open，不要平行再写一条）：

| PR | 谁 | 做什么 | 备注 |
|---|---|---|---|
| [#51132](https://github.com/vllm-project/vllm/pull/51132) | velonica0 | FP32 `exp`/`er` 和 INT4 GEMM 改 RVV FMA | 作者测 INT4 约 1.23–1.27×；08-06 后无新推 |
| [#52933](https://github.com/vllm-project/vllm/pull/52933) | HakureiPOI | 交叉编译不再读宿主机 cpuinfo | 09-17 已留言 |
| [#58257](https://github.com/vllm-project/vllm/pull/58257) | 6eanut | decode/GQA 窄 M 用 16 列双累加链 | **09-23 新开**；作者测 M=1 约 1.5× |
| `#52858` `#52934` `#53069` `#48487` | HakureiPOI | oneDNN 门控、FP16 舍入、exp clamp、运行时探测 | 工作队列已列，不重叠 |

`#58257` 和长文 §2 对得上：Decode 是窄 M，收益来自两条独立累加链，不是把 LMUL 加宽。这是 RVV 上的事，还没碰到 VME。

---

## 4. SGLang：主干仍是零，三件套 09-24 又推过

长文没写 SGLang，是因为当时软件节看的是编译器 / IREE。框架侧现状：

- 主干 `CpuArchEnum` 仍只有 X86 / ARM / UNSPECIFIED。
- 官方 CPU 路线绑 Intel AMX。
- ChenTim1011（nthu-pllab × Andes）三件套都还 open，测在 BPI-F3 / SpacemiT K1（VLEN=256）：
  - [#22193](https://github.com/sgl-project/sglang/pull/22193) kernel
  - [#22219](https://github.com/sgl-project/sglang/pull/22219) `--attention-backend rvv`
  - [#22220](https://github.com/sgl-project/sglang/pull/22220) Dockerfile / 文档
- [#18072](https://github.com/sgl-project/sglang/issues/18072) 上 09-17 的协作评论还没有回复。作者 09-24 又 force-push 过。CI 红，是因为没有 riscv runner。

选型：要在 RISC-V 上跑，仍选 **vLLM 源码构建**。SGLang 要等三件套进主干，并自己用 RVV 编 `sgl-kernel`。

---

## 5. 我们这边

物理 riscv64 还没通，这是复现和贡献的硬阻塞。通机之前只跟状态，不提重叠 PR。

通机后的顺序仍按 `riscv-inference/riscv-maintainer/`：采集硬件/工具链 → 填 support-matrix → 原生编 vLLM 标量/RVV → **原样复现** SGLang 三件套 → 再谈文档或包装。

---

## 关联

- 长文：[向量与矩阵扩展](./vector-matrix-edge-ai.md)
- 固件 / BRS：[firmware-brs.md](./firmware-brs.md)
- 组织与项目清单：[orgs.md](./orgs.md) · [projects.md](./projects.md)
