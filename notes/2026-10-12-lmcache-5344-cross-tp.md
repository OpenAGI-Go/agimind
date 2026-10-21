# LMCache #5344：我跟 cross-TP torn store 这件事

写在本机。远端 AutoDL 关机就没了，过程记这儿。

## 我想干什么

Slack 里被拉进 [#5344](https://github.com/LMCache/LMCache/issues/5344)。ppilgrim 单 rank 的 fail-closed 已经有 [#5349](https://github.com/LMCache/LMCache/pull/5349)，还差 **跨 TP** 怎么一起提交。我想先复现、再跟设计、再提 PR；顺带把 LMCache 这条线做深一点。

我对 LMCache 还在上手，对外不说死。

## 我对 LMCache 的基础认知（第一次上手）

**它是什么**  
推理引擎（vLLM 等）算完的 **KV cache** 本来只活在 GPU 里、请求结束就没了。LMCache 把它变成可管理的一层：能 **存、取、跨请求/跨实例复用**，用来砍长前缀的 prefill（降 TTFT、提吞吐）。自己不算注意力，是 **KV 的缓存/搬运层**。

**为什么需要**  
Agent / 多轮 / RAG：上下文很长，但每轮新增不多，前缀命中率很高。HBM 装不下就淘汰 = 整段重算。把 KV 放到 CPU / 盘 / 远端，下次命中直接灌回 GPU。

**我脑子里的分层**

| 层 | 我怎么记 |
|---|---|
| 引擎 | vLLM 负责算；通过 **Connector**（如 `LMCacheMPConnector`）跟 LMCache 说话 |
| MP server | 常是独立进程，管存储，引擎挂了缓存还能在（不 fate-share） |
| L1 | 快层，多半是主机大内存池；#5344 的 `batched_allocate` 就在这 |
| L2 | 更慢更大（盘、对象存储等）；L1 不够再往下落 |
| 索引 / 事件 | 用 token（或 hash）登记「这段前缀有没有」；`MP_TOKENS` 就是在报这个 |

**和 APC 的差别**  
vLLM 自带前缀缓存多半还在引擎进程/GPU 语义里。LMCache 把 KV **挪出引擎生命周期**，还能跨实例、分层。

**TP 为什么特别麻烦**  
一张逻辑前缀在 TP=N 时是 **N 个 shard**。目录说「有了」必须 N 份都有。只成功一部分 = torn。#5344 / 我要跟的 cross-TP，就是卡在「谁有权宣布有了」。

**我跟这条线相关的调用直觉**

```
请求前缀 → connector store
  → 各 TP rank 各自 reserve L1、拷 KV
  →（今天）worker0 可能已发 MP_TOKENS
  → finish_write 提交
之后请求 → lookup / retrieve → 命中则少算 prefill
```

本地代码：`infra/infer/LMCache`。我 dig 的文件主要是 `lmcache_driven_transfer.py`。

## 我目前怎么理解 #5344

TP 多卡时，每个 rank 各自往 L1 里 reserve / 写 KV。有人 OOM、有人写成功，worker 0 却可能已经发了 `MP_TOKENS`，目录以为前缀齐了——其实 shard 没齐。这叫 torn prefix。

乱码那条 retrieve 链路社区有争议；**store 侧跨 rank 不一致** 这一点我先当真的。

关键点：`lmcache_driven_transfer.py` 里 worker 0 在 `finish_write` 之前就会 `_publish_token_bindings`。

## 版本我怎么选

- 对齐原文报告：`0.5.4rc5`
- 提 PR：跟上游 **`dev`**
- 稳定包：`0.5.5`；较新 rc：`0.5.6rc4`

## 复现我怎么拆

本机 Mac 没 CUDA，E2E 只能上云。

- **先**：TP=2、L1 故意设很小，盯日志里「有的 rank Stored、有的 Failed to batched allocate」
- **本机还能**：跟 #5349 一样用 mock/pytest 盯单 rank abort
- **原报告**：TP=4 + hybrid Mamba/GDN + 大 L1，有卡再对齐

## 远端我做过什么

1. 租 AutoDL 多卡（要过 2 张同型号；1 张做不了 cross-TP）
2. Cursor Remote-SSH 连上去；下载慢就本机 `localServerDownload`，server 装到 `/root/autodl-tmp`
3. 旧机没续费关机后，SSH Host 名还在 Cursor 最近列表里会连飞；新机还把地区域名写错过——**端口对、域名错会直接被对端掐掉**（`weste`/`westd`/`westb` 都要跟控制台一致）
4. **2026-10-12**：新实例上 `nvidia-smi` 看到 **2× RTX PRO 6000**（约 96GB/卡），驱动 580.95.05，**CUDA 13.0**。显存空闲、无进程。够跑 TP=2。
5. **2026-10-13**：克隆实例重启后端口变 `31374`；HostName 需为 `connect.westb.seetacloud.com`（不是旧的 `westd`）
6. （待写）装 vLLM / LMCache、打复现日志……
7. 国内网络统一用本仓脚本：[`../deployments/cn-net/`](../deployments/cn-net/) → 远端 `source cn_net.sh`

SSH 别名：`autodl-RTX-Pro-6000-gpu-lmcache`（以 AutoDL 控制台最新命令为准）。

## Slack

我回的大意：还在读 #5344 / #5349；单 rank 像是对的第一步；我先把路径看清，再回来问问题和粗方案。

## 下一步

- [x] 新机器上 `nvidia-smi` 确认 2 卡
- [ ] `/root/autodl-tmp` 装环境（尽量 editable 跟 `dev`；注意镜像 CUDA 13）
- [ ] 打出跨 rank 半成功 store 日志，贴到这篇后面
- [ ] 英文短设计发 issue / Slack
- [ ] 开 PR（有了再填链接）

## 代码走读：问题出在哪几站（修前 `dev` / `160b6de`）

文件主线：`lmcache/v1/multiprocess/modules/lmcache_driven_transfer.py` 的 `store()`。  
rank = TP 里的一张 GPU（`key.worker_id`）。两边都进**同一个** LMCache server。

```
vLLM rank0 / rank1
    │  LMCacheMPConnector
    ▼
LMCache server · store()
    ├─① MP_STORE_SUBMITTED
    ├─② worker0 发 MP_TOKENS          ← 问题点 A（太早）
    ├─③ 各 rank 自己 reserve_write    ← 问题点 B（互不知晓）
    ├─④ D2H 拷 KV 进暂存
    ├─⑤ 成功则 finish_write_by_owner  ← 问题点 C（只看本 rank）
    └─⑥ 打 "Stored …" / 或 allocate 失败日志
```

### ① 入口

两边各自带着同一段 `request_id` + token range 进 `store()`。  
到这儿还没撕开。

### ② 问题点 A — `MP_TOKENS` 发太早

修前大约在 723–730 行：

- 条件：`key.worker_id == 0` 且有人订阅 `MP_TOKENS`
- 时机：**还没** `reserve_write` / **还没** `finish_write`
- 注释大意：token 内容各 rank 一样，worker0 报一次就行

所以索引侧可能已经听到「这段前缀有了」，后面的 GPU 还没申请成功。

（我复现时没开订阅，日志里看不到 `MP_TOKENS`；撕裂照样发生在 ③⑤。）

### ③ 问题点 B — 各 rank 自己 `reserve_write`

循环 object group → `storage_manager.reserve_write(...)`。

- 成功：key 进 `reserved_dict` / `all_dict`
- OOM：`batched_allocate` 打 `Failed to batched allocate …`，这张卡这批没进 `all_dict`
- **另一张卡不知道**

共享 L1 + 小池子时：一边装得下整批，一边装不下 → 日志一边 `Stored`、一边失败。

### ④ 拷贝

`transfer_kv_per_object_group(... D2H ...)`：把本卡 KV 拷进刚 reserve 的缓冲区。  
还是本卡自己的事。

### ⑤ 问题点 C — `finish_write` 只看本 rank

`finally` 里修前逻辑大意：

- `store_succeeded` 且本卡 `all_dict` 非空 → `finish_write_by_owner` → 对象对查找可见
- 本卡失败 → 本卡不 commit

所以：**成功的那张卡照样把残缺前缀的半边写进 L1**；失败的那张卡什么都没有。  
#5349 只加强「本卡半路 OOM 时 abort 自己的暂存」，**碰不到已经成功的那张卡**。

### ⑥ 日志你看到的样子

- 成功卡：`Stored 3840 tokens …`
- 失败卡：`Failed to batched allocate 15 memory blocks … (short by 10 blocks)`

lookup 用 fold：缺任一 rank 的 shard → chunk 不算命中 → 我复现时二次请求没有 `Retrieved`（撕裂占空间，不一定读出乱码）。

---

### 修后对照（分支 `issue-5344-cross-rank-store`）

同一文件，多卡时：

| 站 | 变化 |
|---|---|
| ② | `world_size > 1` **先不发** `MP_TOKENS` |
| ③ | `reserve_write_with_status`，把 OOM / 已存在等状态留下 |
| ⑤ | **不立刻** `finish_write`；`_handoff_cross_rank_store` → `CrossRankStoreGate` |
| 新 | `cross_rank_store.py`：各 rank 报到 + 拷贝完成 → 按 chunk 投票 → 同意的 commit，不同意的 abort；worker0 再发同意的 `MP_TOKENS` |

走读顺序建议：修前 `store()` ②③⑤ → 再打开 `cross_rank_store.py` 的 `submit` / `_decide`。

远端完整笔记：fork 上 `docs/issue-5344-笔记.md`。  
分支：https://github.com/OpenAGI-Go/LMCache/tree/issue-5344-cross-rank-store

## 链接

- https://github.com/LMCache/LMCache/issues/5344  
- https://github.com/LMCache/LMCache/pull/5349  
- 旧笔记：[LMCache × Phoenix](./2026-09-03-lmcache-phoenix-xpuiio.md)  
