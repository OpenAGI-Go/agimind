# Mac 上大模型训推开源地图

> **日期**：2026-09-22（上午对话整理）  
> **背景**：梳理 Apple Silicon 上能训、能推的开源栈，以及和 System One / Jev 类项目的衔接。  
> **性质**：选型备忘，不是性能 benchmark。  
> **关联**：[开源 Jev 模型梳理](./2026-09-22-open-jev-models-nanojev-nimble-laya.md) · [FlagOS + Qwen3.8 M5 实践](./2026-09-01-flagos-qwen38-deployment-practice.md)

---

## 1. Mac 能训也能推，但分工不同

Mac 不是「只能看文档」——**推理、LoRA 微调、小编码器训练**都可以在本机做。但和 Linux + A100/A800 比，分工应明确：

| 适合在 Mac 做 | 更适合放到 Linux GPU |
|---|---|
| MLX **LoRA / QLoRA**（3B–8B 4bit） | 大规模预训练 |
| 小编码器 / 决策头（Laya 量级） | NanoJev 级 unified 全量训练（已在 A800 完成，见 [nanojev-2026-09](./nanojev-2026-09/README.md)） |
| 本地推理 demo、Ollama、mlx_lm.server | 长上下文 + 大 batch 生产训练 |
| 读代码、写笔记、SSH 到远程 GPU | 指望 Mac 复现 H100 级吞吐 |

---

## 2. MLX 与 MPS：不是一回事

| | **MPS** | **MLX** |
|---|---|---|
| 层级 | PyTorch 的 **Mac GPU 后端** | Apple **独立 ML 框架** |
| 用法 | `device="mps"` | `mlx` / `mlx-lm` |
| 生态 | 挂 PyTorch 全栈 | Mac 原生；大量 `mlx-community` 模型 |
| 训练 | 通用，大模型常不如 MLX 省心 | **Mac 上训推首选** |
| 推理 | ✅ | ✅ |

**Metal** 是底层 GPU API；**MPS** 是 PyTorch 走 Metal；**MLX** 是另一套完整栈。日常说「Mac GPU 训模型」，多数场景指 **MLX**，不是 PyTorch MPS。

---

## 3. 原生训推栈（精选）

| 项目 | 训 | 推 | 备注 |
|---|---|---|---|
| [MLX](https://github.com/ml-explore/mlx) + [mlx-lm](https://github.com/ml-explore/mlx-lm) | ✅ | ✅ | `mlx_lm.lora` 微调；`mlx_lm.server` OpenAI 兼容 API |
| [Ollama](https://github.com/ollama/ollama) | ❌ | ✅ | 日常本地推理最省事 |
| [llama.cpp](https://github.com/ggerganov/llama.cpp) | ⚠️ LoRA | ✅ | Metal 推理成熟；GGUF 生态 |
| PyTorch **MPS** | ⚠️ | ✅ | 通用但大模型训练常不如 MLX |
| [donkeytune](https://github.com/donkey-labs/donkeytune) | ✅ | ✅ | MLX LoRA → fuse → GGUF → Ollama 一条龙示例 |

**MLX 常用命令方向：**

```bash
# 微调（示例，具体参数见 mlx-lm 文档）
mlx_lm.lora --model mlx-community/Qwen2.5-7B-Instruct-4bit ...

# 本地 OpenAI 兼容服务
mlx_lm.server --model mlx-community/Qwen2.5-7B-Instruct-4bit
```

---

## 4. 按统一内存选型（经验值）

| 统一内存 | 推理（4bit 量化） | LoRA 微调 |
|---|---|---|
| **16GB** | 3B 4bit | 3B QLoRA |
| **32GB** | 7B–8B 4bit | 7B/8B QLoRA |
| **64GB+** | 14B–27B 4bit | 8B 全参/LoRA；或 FlagOS Qwen3.8 CPU 推理 |

**MLX 友好模型（HF `mlx-community`）**：Qwen2.5/3（0.6B–7B）、Llama 3.2（1B/3B）、Gemma 2/3、Phi、Mistral 7B 等 4bit 版。

下载后本地路径即模型目录，无需再转格式（与 Ollama/GGUF 路径不同）。

---

## 5. System One / Jev 项目在 Mac 上怎么用

| 项目 | Mac 建议 | 说明 |
|---|---|---|
| **Laya** | `pip install laya`，**CPU** 试接口 | 官方未承诺 MPS/MLX；严肃延迟看 CUDA T4 |
| **Nimble** | **官方 MLX 推理** | 9B；holdout ~444 ms/样本（M5 Pro 64GB） |
| **NanoJev** | 静态 **web 回放**（8080） | 训练已在远程 A800 完成；本机可看 demo、读代码 |

详见 [开源 Jev 模型梳理](./2026-09-22-open-jev-models-nanojev-nimble-laya.md)。

---

## 6. 本仓库已有 Mac 实践

| 内容 | 路径 |
|---|---|
| FlagOS + Qwen3.8-27B M5 **CPU** 部署 | [2026-09-01-flagos-qwen38-deployment-practice.md](./2026-09-01-flagos-qwen38-deployment-practice.md) |
| 部署脚本 | [deployments/flagos-qwen38-m5/](../deployments/flagos-qwen38-m5/) |

64GB 机器上，**FlagOS W4A8 CPU 推理**与 **MLX 27B 4bit** 是两条大模型本地路线；前者偏框架实践，后者偏 Apple 原生生态。

---

## 7. 选型决策树

```
目标是什么？
├─ 本地玩 System One 接口（工单/路由/布尔/选项）
│   ├─ 要最快、最轻 → Laya（CPU，pip install laya）
│   └─ 要 MLX、可接受 9B → Nimble
├─ Mac 上 LoRA 微调聊天模型
│   └─ mlx-lm + mlx-community 3B–8B 4bit
├─ Mac 上日常本地 API（聊天/助手）
│   └─ Ollama 或 mlx_lm.server
├─ Mac 上大模型推理（64GB）
│   └─ FlagOS Qwen3.8 W4A8 或 MLX 27B 4bit
└─ NanoJev 训练 / 548 局评测
    └─ 见 nanojev-2026-09（已在 A800 完成主线）
```

---

## 8. 和「聊天 LLM 训推」的关系

上午对话里还澄清了一点：**Jev 类模型和聊天 LLM 的 Mac 栈 largely 重叠，但用途不同。**

- **聊天 LLM**：Ollama / mlx-lm 推理；mlx-lm LoRA 做指令微调。  
- **决策模型**：Laya CPU、Nimble MLX 直接走 System One 接口；NanoJev 需 CUDA 训练，Mac 侧主要是学习与静态 demo。  

若目标是「在 Mac 上练手 ML 工程」，**MLX LoRA + Ollama** 是性价比最高的入门组合；若目标是「理解决策接口」，**Laya + Nimble MLX** 比从零训 NanoJev 更贴 Mac。

---

## 9. 参考链接

| 资源 | URL |
|---|---|
| MLX | https://github.com/ml-explore/mlx |
| mlx-lm | https://github.com/ml-explore/mlx-lm |
| mlx-community 模型 | https://huggingface.co/mlx-community |
| Ollama | https://github.com/ollama/ollama |
| llama.cpp | https://github.com/ggerganov/llama.cpp |
| donkeytune | https://github.com/donkey-labs/donkeytune |

---

## 10. 一句话收束

**Mac 训推首选 MLX（微调 + 本地 API），日常推理用 Ollama 最省事；大内存机器可看 FlagOS 或 MLX 27B 4bit。** System One 在 Mac 上：Laya 走 CPU，Nimble 走 MLX，NanoJev 训练放远程 GPU——本机负责轻量实验与文档，别和 Linux 单卡全量训练抢活。
