# DeepInfer 开源：和 vLLM / SGLang 怎么摆

> **日期**：2026-10-20  
> **来源**：DeepSeek 公众号公告 · [微信](https://mp.weixin.qq.com/s/5MEu2eeqNfBWXlkCKTd6sg) · [DeepInfer README](https://github.com/deepseek-ai/DeepInfer)  
> **上游**： [DeepInfer](https://github.com/deepseek-ai/DeepInfer) · [deepseek-recipe](https://github.com/deepseek-ai/deepseek-recipe)  
> **性质**：定位备忘，不是性能对照。本地若有浅克隆，在工作区推理 infra 目录，不在本 Git 仓库。

---

## 1. 公告在开什么

| 仓库 | 角色 | 本机 HEAD（浅克隆） |
|---|---|---|
| [DeepInfer](https://github.com/deepseek-ai/DeepInfer) | 生产推理引擎；Apache-2.0 | `8b16149`（2026-10-20） |
| [deepseek-recipe](https://github.com/deepseek-ai/deepseek-recipe) | API 请求 ↔ Conversation ↔ prompt / token；MIT | `935817c`（2026-10-20） |

线上 **DeepSeek V4.1 Flash** 的高吞吐服务基于 DeepInfer；后续新模型推理代码也会往这里更。

`deepseek-recipe` **不做推理**：调用方自己接 backend、工具执行和 HTTP。它保证社区 API 体验和官方编解码一致。

---

## 2. DeepInfer 自己划的边界

**已开源（offline 为主）**

- 模型：DeepSeek-V4.1-Flash（默认 HF：`deepseek-ai/DeepSeek-V4.1-Flash-1017`）
- 硬件：NVIDIA **SM100**；华为 **Ascend 950**（`DEEPINFER_ACCELERATOR=nvidia|ascend`）
- 能力：FlashMLA / DeepGEMM / DeepEP 等算子；Attention DP / CP；MoE EP + EPLB；DSpark + confidence 调度验证；SWA bounded replay；异步调度；batch-invariant / 确定性采样（NVIDIA）；结构化输出

**本 release 明确不含**

- KV cache 系统  
- VE / Prefill–Decode 解耦（引擎侧功能大多已实现，编排未打包）  
- Prefill / Decode 的 DP 副本负载均衡  

构建：Linux、GCC ≥ 13、Python 3.12；NVIDIA 要 CUDA 13；Ascend 要 CANN 9.2。`./build.sh`，再 `python examples/offline_inference.py`。

官方致谢：主体基于 **vLLM**，并吸收 **SGLang**、**TensorRT-LLM**。

---

## 3. 和 vLLM / SGLang 怎么分

| 维度 | DeepInfer | vLLM | SGLang |
|---|---|---|---|
| 定位 | DeepSeek 自家生产栈开源 | 通用开源引擎 | 通用开源引擎（偏结构化 / 多轮） |
| 模型面 | 先保 V4.1-Flash Day-0 体验 | 宽模型面 | 宽模型面 |
| 硬件 | SM100 + Ascend 950 一等公民 | CUDA 主线；Ascend 走 vLLM-Ascend 等插件 | CUDA 主线；NPU 另有适配 |
| 完整服务 | 缺 KV 系统与 PD 编排 | 自带服务与生态连接器 | 自带服务与路由 |
| API 对齐 | 靠 `deepseek-recipe` 对齐官方 | OpenAI 兼容为主 | OpenAI / 自有协议 |

一句话：

- **要跟官方 DeepSeek API 行为、吃透 V4.1 Flash 生产路径** → DeepInfer + deepseek-recipe  
- **要通用多模型、多厂家后端、社区插件（含 RISC-V RVV）** → 仍看 vLLM / SGLang  
- DeepInfer **不是**「又一个通用引擎替代品」；README 自己承认从 vLLM 长出来，且完整 serving 还缺几块

对应本工作区（均在本仓之外的本地目录）：

- 框架本体 → 推理 infra  
- Ascend / NVIDIA Runtime 竖切 → 芯片栈  
- RISC-V 上的 vLLM / SGLang → RISC-V 专区（不复制进 DeepInfer）

---

## 4. 和早先「不开整仓」的关系

Open Source Week 时他们写过：内部引擎是老版 vLLM fork，耦合集群工具，带宽不够维护整仓，改成分模块贡献。这次是**整框架开源**，但边界仍克制（offline 优先、KV / PD 编排未打包）。当作策略升级，不要和旧文混成同一承诺。

---

## 5. 本机下一步（未做）

1. 有 SM100 或 Ascend 950 再跑 `build.sh` + `examples/offline_inference.py`  
2. Mac 上只能读代码与 recipe；不要指望本机构建 NVIDIA / CANN 路径  
3. 若要对齐官方 API：先通 `deepseek-recipe` 的 convert / render，再挂任意 backend  

---

## 关联

- KV / 落盘：[LMCache × Phoenix](./2026-09-03-lmcache-phoenix-xpuiio.md)  
- RISC-V 推理跟进：[vLLM / SGLang](../riscv/vllm-sglang.md)  
