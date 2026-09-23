# 开源 Jev / System One 模型梳理：NanoJev、Nimble、Laya

> **日期**：2026-09-22（上午对话整理）  
> **背景**：对比社区三条主流「开源 Jev」复现线，弄清它们是不是同一种模型、各自适合什么场景。  
> **性质**：学习笔记 + 选型备忘，不是论文结论。  
> **关联**：[Mac 训推地图](./2026-09-22-mac-train-infer-landscape.md) · [为什么底座都用 Qwen](../sparks/2026-09-22-为什么底座都用Qwen.md) · [NanoJev 训练实录（2026-09-21）](./nanojev-2026-09/README.md)

---

## 1. 这条线在回答什么

1. **Jev / System One 到底在卖什么？** 和聊天 LLM 有什么不同？  
2. **NanoJev、Nimble、Laya 是不是同一模型的不同尺寸？**  
3. **为什么很多开源决策模型底座都选 Qwen？**

一句话结论：**三者形态完全不同**——不是 S/M/L，而是同一接口方向上的不同工程选择。底座（Qwen、ModernBERT 等）只是成本项；**怎么读出概率、评测在什么场景**才决定是不是同一条路。

---

## 2. Jev / System One 在干什么

材料主要来自 [TypeSafe 的 Jev 介绍](https://typesafe.ai/blog/introducing-system-one-models-and-jev)。

聊天 LLM 对人友好：能写、能解释、很灵活。嵌进无人值守的软件里，字符串输出会变成负担——格式不稳、逐 token 生成慢、置信度常过自信。

**System One / Jev** 换了一个接口：

```text
程序给：状态 + 若干问题（boolean / choice / score）
模型回：每个问题上的概率分布
推理：一次前向，不生成答案 token
```

和「猜下一个字」的 SFT 相比，损失往往仍是交叉熵，但 softmax **只对这道题给的候选**做，不是对整个词表。

---

## 3. NanoJev：游戏闭环 + 小 LM 决策头

### 3.1 定位

[NanoJev](https://github.com/OpenAGI-Go/NanoJev) 是 [TypeSafe Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev) 的 **nano 复现**：0.6B 并行决策模型，输入 state + question + candidates，**一次前向出完整概率分布**。

当前统一发布 **`unified-games-v1`**：一个 checkpoint 覆盖 Maze、Snake、ViZDoom Basic、ViZDoom Predict Position。

### 3.2 架构（和「普通 LLM」不同）

逻辑在 `scripts/train_toy_decisions.py` 的 `DecisionModel`：

- 底座：**Qwen3-0.6B** backbone（不是完整 Causal LM 自回归生成链路）
- 每个候选编码成独立 **leaf path**（state + question + candidate 文本）
- 共享 **scalar head**；Choice 可选 **set-attention head**
- 题内 softmax / boolean sigmoid → 直接概率

常用入口：

| 用途 | 入口 | 默认端口 |
|---|---|---|
| 批量推理 | `predict_toy_decisions.py` → `DecisionPredictor` | — |
| HTTP 服务 | `serve_decisions.py` | **8765** |
| 静态回放 | `python3 -m http.server 8080 --directory web` | **8080**（无需 GPU） |

### 3.3 开源边界

**已公开：**

- 完整代码、数据生成、训练/推理/评测脚本
- Hugging Face 模型 **`C-Tianyu/NanoJev`**、数据 **`C-Tianyu/NanoJev-Data`**（revision `unified-games-v1`）
- 初始化 checkpoint、训练配置与日志、固定评测 cases

**未公开 / 不能等同官方 Jev：**

- Jev API 私有教师标签全集、`.env` 密钥、完整供应商 journal
- TypeSafe 内部架构与官方 RLCD 配方
- 部分早期私有 run 目录

因此：**可以学习和复现 NanoJev 公开主实验，不能声称复刻了 TypeSafe Jev 本体。**

### 3.4 亲手训练

**已在 2026-09-21 于 AutoDL A800 完成 `hard_lr1e5` 复现**（阶段 0～7 收口）。过程、命令、指标与自训 vs 官方对比见：

- [搞懂 NanoJev 并把训练跑通](./nanojev-2026-09/搞懂NanoJev并把训练跑通.md)
- [548 局大评测结构稿](./nanojev-2026-09/搞懂NanoJev的548局大评测.md)
- `nanojev-2026-09/stage7/` — 玩具推理 JSON 对比

本文不再重复训练步骤与环境细节。

---

## 4. Nimble：9B 生成式 LM + 答案 token 打分

[Bespoke-Nimble-9B](https://github.com/bespokelabsai/nimble)（Apache 2.0）走另一条路：保留 **Qwen3.5-9B** 生成式 LM，对**允许答案 token** 的 logits 打分，而不是自定义决策头。

| 项 | 内容 |
|---|---|
| HF | [bespokelabs/Bespoke-Nimble-9B](https://huggingface.co/bespokelabs/Bespoke-Nimble-9B) |
| 规模 | 9B base + LoRA adapter（~165MB） |
| 训练数据 | ~2676 对比合成对 |
| 任务 | 文本 schema 决策（boolean / choice / score） |
| 限制 | prompt ≤ **2048** tokens；enum ≤ **26** 选项；flat schema |
| 与 Jev | 作者称**未蒸馏 Jev**；324 例 holdout **90.12%** vs Jev **93.21%** |
| Mac | **官方 MLX 推理**；holdout 中位延迟 ~**444 ms**（M5 Pro 64GB，每样本一次打分） |
| Linux GPU | CUDA **BF16**；需 Qwen3.5-9B base + adapter |

**适合**：需要 LLM 世界知识、能接受 9B 延迟、想在 Mac 上 MLX 试 System One 接口。

---

## 5. Laya：轻量编码器 + 决策头

[Laya](https://github.com/NandhaKishorM/laya)（Apache 2.0）用 **双向编码器**（ModernBERT / mmBERT）+ 决策头，偏生产文本决策。

| 项 | 内容 |
|---|---|
| 安装 | `pip install laya`；Python ≥ **3.10** |
| 规模 | **300–420M**（英文 ModernBERT-large 421M / 多语言 mmBERT 322M） |
| 路由 | 三个 checkpoint + **`Router`** 按语言分流 |
| 任务 | 工单/邮件/路由/安全等 typed decisions |
| 测速 | T4 GPU 单题 ~**33 ms**；CPU preload 后 ~193–464 ms/题 |
| Mac | **CPU 可跑**；官方**未写** Mac GPU / MLX / MPS |
| 注意 | 高基数 choice（如 Banking77）默认 token 预算不够，需调 `head_max_len` 或 shortlist |
| 注意 | typed-decisions 上 **0.766** 来自**该 benchmark 微调 checkpoint**，零样本 base 很弱 |
| 与 Jev | 第三方 Jev 数字对比；**作者未实测 Jev API** |

**适合**：要最快、最轻、CPU 就能试 System One 接口；严肃吞吐看 CUDA。

---

## 6. 三者对照

| | **NanoJev** | **Nimble** | **Laya** |
|---|---|---|---|
| 仓库 | [OpenAGI-Go/NanoJev](https://github.com/OpenAGI-Go/NanoJev) | [bespokelabsai/nimble](https://github.com/bespokelabsai/nimble) | [NandhaKishorM/laya](https://github.com/NandhaKishorM/laya) |
| 许可 | 项目 MIT + HF 发布 | Apache 2.0 | Apache 2.0 |
| 规模 | **0.6B** + 决策头 | **9B** Qwen3.5 + LoRA | **300–420M** 编码器 + 决策头 |
| 形态 | 候选路径并行 + 自定义 head | 生成式 LM，答案 token 打分 | 双向编码器 + 决策头 |
| 训练数据 | 游戏决策 + 专家轨迹 | ~2676 对比合成对 | RLCD + 领域微调 |
| 任务重心 | Maze / Snake / ViZDoom 闭环 | 文本 schema 决策 | 工单/邮件/路由/安全 |
| Mac | 静态 web 回放；训练需 CUDA | **官方 MLX 推理** | **CPU** 可跑 |
| 公开训练管线 | **最完整**（数据+脚本+评测） | 有，偏 GPU | 有，偏 CPU/CUDA |

**怎么选（概念层）：**

- **Laya**：快、轻、编码器，偏生产文本决策  
- **Nimble**：继承 LLM 世界知识，9B token-scoring  
- **NanoJev**：小 LM + 游戏闭环 + 完整公开训练与评测管线  

---

## 7. 社区里常见的「模型形态」

没有官方「一共 N 种」分类；开源实践里大约 **5–7 类**：

| 形态 | 代表 | 怎么出概率 |
|---|---|---|
| 编码器 + 决策头 | Laya、Verdict/GLiClass | 双向编码，头直接出分布 |
| 生成式 LM + 答案 token 打分 | Nimble | 只读允许答案的 logits |
| 生成式 LM + 自定义决策头 | **NanoJev** | 候选路径并行，scalar/set head |
| 共享前缀 / 树注意力 | openjev 等实验 | 共用 state 前缀，分支打分 |
| 约束解码 / 掩码生成 | 部分「伪 System One」 | 仍生成，mask 非法 token |
| 冻结 LM + 提示 | 未微调 Qwen baseline | 提示或词表头凑决策 |
| 固定标签分类器 | 传统 BERT 路由 | 非通用 schema |

形态一般由 **延迟预算 × 候选复杂度 × 数据从哪来 × 是否复用 LLM 能力 × 开源/许可** 共同决定，不是审美问题。

---

## 8. 为什么很多底座选 Qwen？

已单独写成随笔：[为什么底座都用 Qwen](../sparks/2026-09-22-为什么底座都用Qwen.md)。

摘要：

1. 许可与权重分发相对友好  
2. 0.6B–9B 对决策任务 often 够用  
3. Transformers / LoRA / BF16 工具链成熟  
4. 中英文与指令跟随稳定  
5. 单卡可训，成本低  
6. **路径依赖**：NanoJev、Nimble 等已用 Qwen，后来者便于对照配方  

这不是「System One 必须用 Qwen」，而是**开源复现实验的默认性价比选择**。Laya 选 ModernBERT/mmBERT 是同一逻辑在「更小、更快、编码器」侧的变体。

---

## 9. 参考链接

| 资源 | URL |
|---|---|
| NanoJev | https://github.com/OpenAGI-Go/NanoJev |
| NanoJev 模型 HF | https://huggingface.co/C-Tianyu/NanoJev |
| Nimble | https://github.com/bespokelabsai/nimble |
| Nimble 模型 HF | https://huggingface.co/bespokelabs/Bespoke-Nimble-9B |
| Laya | https://github.com/NandhaKishorM/laya |
| Laya 模型 HF | https://huggingface.co/convaiinnovations/laya |
| TypeSafe Jev 介绍 | https://typesafe.ai/blog/introducing-system-one-models-and-jev |
| System One 替代品综述 | https://systemonemodels.org/examples/alternatives/ |

---

## 10. 一句话收束

**NanoJev 是游戏闭环 + 小 LM 决策头的公开复现线；Nimble 是 9B token-scoring 配方；Laya 是轻量编码器决策引擎。** 别用「又一个 Qwen 底座」掩盖结构差异——读出方式与评测场景才决定是不是同一条路。训练实操见 [nanojev-2026-09](./nanojev-2026-09/README.md)；Mac 上怎么训、怎么推见 [Mac 训推地图](./2026-09-22-mac-train-infer-landscape.md)。
