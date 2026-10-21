# agimind

自己学 AGI / AI 系统时写的笔记与可复现脚本。权重不进仓库；脚本在 `deployments/`，文章在 `notes/`（思路在 `thoughts/`）。

工作区五方向和代码位置见 [根目录 README](../README.md)。仓库内部怎么分区，见 [README.structure.md](./README.structure.md)。

| 代码 | 现路径 |
|---|---|
| NanoJev | [`../models/NanoJev/`](../models/NanoJev/) |
| 训练 infra | [`../infra/train/`](../infra/train/) |
| 推理 infra | [`../infra/infer/`](../infra/infer/)（DeepInfer / Phoenix 等） |
| 芯片栈 | [`../infra/chips/`](../infra/chips/) |
| RISC-V 专区 | [`../riscv/`](../riscv/) |
| 小鸭子 | [`../robot/`](../robot/) |

---

## 按 AI 技术主题

### 推理部署

本地 / 端侧把模型跑起来、测吞吐、开 API。

| 文章 | 说明 |
|------|------|
| [DeepInfer vs vLLM / SGLang](./notes/2026-10-20-deepinfer-vs-vllm-sglang.md) | 2026-10-20：DeepSeek 开源生产推理栈的定位与边界 |
| [FlagOS + Qwen3.8-27B 部署实践](./notes/2026-09-01-flagos-qwen38-deployment-practice.md) | Mac M5 Pro，FlagOS CPU Runtime，W4A8，OpenAI 兼容服务与压测 |
| [FlagOS Qwen3.8 M5 CPU 摘录](./notes/2026-08-31-flagos-qwen38-m5-cpu.md) | 相关文章摘录与注释 |
| [部署脚本：flagos-qwen38-m5](./deployments/flagos-qwen38-m5/) | 与上面实践配套的脚本 |
| [cn-net 国内加速](./deployments/cn-net/) | AutoDL 等：GitHub / HF / pip 一键镜像 |

### 预训练

从词表 / 空权重或开源配方，把训练链路自己跑通。

| 文章 | 说明 |
|------|------|
| [Qwen 0.5B 从零预训练（H800）](./notes/2026-09-19-h800-qwen-0.5b-pretrain.md) | AutoDL H800，手写训练循环，数据→切词→打包→训→试生成 |
| [部署脚本：h800-qwen-0.5b-pretrain](./deployments/h800-qwen-0.5b-pretrain/) | 配套脚本 |
| [nanochat 8 卡：从组机到能对话](./notes/2026-09-04-nanochat-8xh100.md) | tokenizer→预训练→CORE→SFT→对话，对照 GPT-2 CORE |

### 决策模型 / 游戏 Agent

Qwen 骨干 + 决策头，专家动作上的交叉熵 SFT，以及复现与评测。

| 文章 | 说明 |
|------|------|
| [搞懂 NanoJev 并把训练跑通](./notes/nanojev-2026-09/搞懂NanoJev并把训练跑通.md) | 主线阶段 0～7（数据、官方权重、smoke、600 步 repro、serve 对比） |
| [搞懂 NanoJev 的 548 局大评测](./notes/nanojev-2026-09/搞懂NanoJev的548局大评测.md) | 下一档闭环评测结构稿 |
| [这次 pip 装进来的包是干什么的](./notes/nanojev-2026-09/这次pip装进来的包是干什么的.md) | 环境依赖说明 |
| [把自训权重传到 Hugging Face 和 ModelScope](./notes/nanojev-2026-09/把自训权重传到HuggingFace和ModelScope.md) | 上传流程与 AutoDL 镜像踩坑 |
| [NanoJev 笔记目录](./notes/nanojev-2026-09/README.md) | 截图、runs-meta、stage7 对照 |

公开权重（不在本仓）：

- Hugging Face：[maxonxie/nanojev-hard-lr1e5-repro](https://huggingface.co/maxonxie/nanojev-hard-lr1e5-repro)
- ModelScope：[maxonxie/nanojev-hard-lr1e5-repro](https://www.modelscope.cn/models/maxonxie/nanojev-hard-lr1e5-repro)

### KV Cache / 推理存储

长上下文、Agent 多轮下 KV 落盘与主机路径。

| 文章 | 说明 |
|------|------|
| [LMCache × Phoenix](./notes/2026-09-03-lmcache-phoenix-xpuiio.md) | KV 打到 SSD 后瓶颈在主机内存跳板（摘录 + 笔记） |
| [LMCache #5344 cross-TP](./notes/2026-10-12-lmcache-5344-cross-tp.md) | torn store：复现与贡献过程（进行中） |

### RISC-V 向量与推理栈

从 RVV / 矩阵扩展的判断，落到现在能跟的 vLLM、SGLang。

| 文章 | 说明 |
|------|------|
| [RISC-V 向量与矩阵扩展](./notes/2026-09-08-riscv-vector-matrix-edge-ai.md) | 2026-09-08：V → Zvbdot → IME/VME/AME，SiFive XM 等产业对照 |
| [V、vLLM、SGLang 跟进](./notes/2026-09-27-riscv-v-vllm-sglang.md) | 2026-09-27：ISA 有没有翻面，加上两家框架的主干 / PR |

### 端侧 AI 系统

约束换成延迟、内存、功耗、离线之后，Runtime / 量化怎么判断。

| 文章 | 说明 |
|------|------|
| [端侧 AI 系统：补齐与判断](./thoughts/edge-ai-systems.md) | 端侧 vs 云侧的几条硬判断 |

### 小鸭子 · Microduck 复刻

代码与总文档在 [`../robot/`](../robot/)。agimind 只收进度摘录与指针。

| 文章 | 说明 |
|------|------|
| [复刻笔记目录](./notes/microduck-2026-10/README.md) | 索引 |
| [已完成复刻摘要](./notes/microduck-2026-10/已完成复刻摘要.md) | 装机 / 上板 / 首走 / 手柄（2026-10） |
| [真机软件栈（指针）](./notes/2026-09-11-microduck-project-analysis.md) | → `robot/microduck.md` §四 |
| [训练仓（指针）](./notes/2026-09-12-microduck-rl.md) | → `robot/microduck.md` §五 |
| [复刻路线（指针）](./notes/2026-09-13-microduck-routes.md) | → `robot/microduck.md` §六 |

### 其它

| 文章 | 说明 |
|------|------|
| [智能是如何产生的？](./notes/intelligence-come.md) | 提纲占位 |
