# LMCache × Phoenix：Agent 把 KV 打到 SSD 之后，瓶颈在主机内存跳板

## 来源

- **标题**：LMCache&xPU.IO：当 LMCache 遇上直通存储
- **作者**：陈宸；仇实（LMCache / xPU.IO）
- **机构**：腾讯 DCPD 发起 xPU.IO；Phoenix 为社区子项目
- **链接**：https://mp.weixin.qq.com/s/zgbhdjKZlH4gvLI22kKoGg
- **日期**：2026-09-01
- **论文**：Phoenix: A Refactored I/O Stack for GPU Direct Storage without Phony Buffers（SC'25）
- **代码**：https://github.com/xPU-IO/Phoenix ；LMCache PR #4673

## 摘录

### 负载变了

Agent 把推理从 chatbot 换成多轮 loop。Codex / SWE-bench Pro trace：第 30 轮上下文常到 ~80K（最长 >180K），每轮新增只有几百到几千 token，input/output ≈ 131:1，前缀缓存命中率 94.2%。前缀命中则 prefill 几乎免费。

两个硬约束：

1. **容量**：100K 级上下文是几十 GB KV；一台实例挂大量长会话，HBM/DRAM 会淘汰，淘汰 = 整段前缀重算。SSD 单机 100TB 级才接得住。
2. **速度**：轮间间隔中位数只有几秒。几十 GB KV 必须在这个窗口回到显存。取回若慢于重算，命中率再高也换不来 TTFT。

### 现有路径为什么反了

LMCache 的 fs_native L2：盘 → 主机内存 → `cudaMemcpy` H2D。容量最大的那层离 GPU 最远，数据两次穿 PCIe，CPU 全程陪跑。

4× PCIe 4.0 NVMe RAID0：iostat 裸盘 25 GB/s，LMCache retrieve 端到端只剩 10.2 GB/s。Codex 回放（8 卡 Prefill）：TTFT 均值 1101 ms，其中 SSD→GPU 约 600 ms，真正 GPU prefill 只有 313 ms。

### Phoenix 做什么

让 NVMe DMA 直达 GPU 显存，去掉伪缓冲区。不绑 NVIDIA GDS / cuFile：用 Linux 标准 I/O（pread / io_uring），`ZONE_DEVICE` 给显存建 `struct page`，显存指针变成内核认识的合法地址。同一套注册还可当 GPUDirect RDMA 的 MR。已在 NVIDIA、沐曦上验证。

LMCache 侧走开放的 GDS L1：小 staging buffer → D2D copy 进 Prefix Cache；Phoenix 用 `LaunchHostFunc` 把 Host DMA 挂到 CUDA stream，获得和 kernel 一样的顺序语义。

### 数字（他们给的）

8×H20 + 4× NVMe Gen4，~3.5 TB KV，平均 prompt 70K / 最大 256K：

- 高压区 TTFT：Phoenix 相对纯 DRAM 5.6×、相对 SSD 中转 2.2×
- TTFT 5s 红线：dram_only 7 并发、SSD 中转 13、Phoenix 37（相对中转 2.9×、相对 DRAM 5.6×）

加载快了，vLLM/LMCache 才能把 KV 加载和前一批推理 overlap 起来。

## 我的想法

这不是微架构文章。核心是 **OS 把 GPU 显存登记成内核可 DMA 的内存**，加上推理框架把 KV 当成可分层的前缀缓存。和 RTL 无关，和发行版、驱动、ZONE_DEVICE、厂商 BAR 映射、多卡互连验收直接有关。

接到三件事：

1. **3FS + RDMA 故事要升级**：训练侧是参数/checkpoint 吞吐；Agent 推理侧是「前缀 KV 能否在轮间几秒内回到卡上」。同一类规格：介质、路径是否经主机、PCIe 几次、驱动是否暴露计数器。不要只讲「跑慢 20G」。
2. **KV 容量账不能只算 HBM**：周 1 的 27B KV vs 22GB 权重，是单会话、端侧视角。云上 Agent 是「大量长会话 × 94% 前缀可缓存」——淘汰策略和存储路径决定 TTFT，不是 TOPS。
3. **国产卡验收多一条**：NVIDIA GDS 是私有路径。Phoenix 的卖点是新卡只补「BAR 映射 + 拷贝原语」两个实现文件。沐曦已经验证。这正是「软件栈接口规格 + 供应商里程碑」：显存能否成为合法 I/O buffer、能否和 RDMA 一次注册两用。

暂不自己装内核模块。先把规格语言写进 thoughts：Agent 的第一堵墙仍是内存，但云侧解法是 **KV 分层 + GPU 直通存储**，不是把 HBM 买到无限大。
