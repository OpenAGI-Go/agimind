# 端侧 AI 系统：补齐与判断

> 为「端侧 AI 系统工程师」岗位建立认知。自学实验（FlagOS / llama.cpp）记在开源实践，不写进腾讯经历。

## 一句话

云侧优化吞吐和利用率；端侧优化延迟、内存、功耗和离线。同一模型换约束，Runtime、量化和算子来源都要换。

## 五条判断

1. **第一堵墙是内存**（权重 + KV + 激活），然后才是带宽，很少是峰值 TOPS。
2. **端侧几乎 batch=1**。Decode 吃不满算力；组批是云的武器。
3. **Runtime 分家**：vLLM/SGLang 是云；llama.cpp / ORT / ExecuTorch 是端。FlagGems/FlagTree 是给它们供核的编译层，不是第四个聊天 Runtime。
4. **算子来源**：有厂商 SDK 先用；没有再 Triton/TVM/MLIR 编；有的循环手写 C++ 更快（FlagGems 的 GDN 就是这样）。
5. **具身成功标准是控制频率**。模型 80ms、控制 20ms 时，要动作块或双系统，不能指望 decode 跟环。

## 我已有的锚点

- 腾讯：跨芯片 Driver/SDK + vLLM/SGLang/KsanaLLM 发行版闭环。
- M5 FlagOS：Qwen3.8-27B W4A8，Triton `tl.dot` → TTIR/LLIR → `smmla`；GDN 留在 native。
- Packages-Agent：Local Agent 需要 OS 环境、权限和可复现运行时。

## 补齐顺序

0. FlagOS 编译链（已完成，整理话术）
1. 端侧物理 + llama.cpp（本周）
2. 量化与 KV 容量
3. ORT / ExecuTorch 最小跑通（认知，不装专家）
4. VLM/VLA 模块图与延迟预算

## 过关标准（第一课）

能不看稿说出：为什么 27B 必须量化才能进 64GB；为什么端侧不该用 vLLM 当默认 Runtime；为什么矩阵核可以编译、循环核可能手写。
