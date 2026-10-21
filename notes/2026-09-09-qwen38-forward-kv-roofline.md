# Qwen3.8-27B：前向、KV 账、Roofline（叠在已有部署上）

> **日期**：2026-09-09  
> **对应路线**：周 1–2（模型内核 + 用已有数字画墙）  
> **叠在哪**：[FlagOS 部署实践](./2026-09-01-flagos-qwen38-deployment-practice.md)、[FlagOS 摘录](./2026-08-31-flagos-qwen38-m5-cpu.md)  
> **配置来源**：Qwen 官方卡片（Hugging Face `Qwen/Qwen3.8-27B`）；KV 元素宽度按 **BF16=2B** 估，权重按你机器上的 **W4A8 ≈ 22GB**

**一句话：** 你已经跑通的不是「一个 27B Transformer」，而是 16 次「3×线性注意力 + 1×全注意力」的混合网。全注意力的 KV 随长度涨；GDN 状态几乎不涨。nospec decode ~13 tok/s 已经贴着 M5 Pro 307 GB/s 的权重搬运上限。

---

## 1. 前向：token 在你这台 27B 里怎么走

```text
token id
  → embed（vocab 248320 → hidden 5120）
  → 重复 16 次：
        GDN → FFN
        GDN → FFN
        GDN → FFN
        Gated Attention（全注意力，GQA）→ FFN
  → lm_head（5120 → 248320）
  → （可选）MTP 头 / 你用的 DFlash2 draft
```

层数：64 = 48 GDN + 16 全注意力。官方布局是 `16 × (3× GDN + 1× Gated Attention)`，不是「先 48 层线性再 16 层全注意力」。

| 块 | 配置 | 随序列长度怎么变 |
|---|---|---|
| Gated DeltaNet ×48 | V 头 48、QK 头 16、head dim 128 | 循环状态，**每层一块固定矩阵**，不随 T 涨 |
| Gated Attention ×16 | Q 24 / KV 4，head dim 256，RoPE dim 64 | 标准 GQA：**K/V 按 token 追加** |
| FFN | intermediate 17408 | 每 token 过一遍，不存历史 |
| 权重（你的包） | W4A8 G128，约 22GB（BF16 约 54GB） | 常驻；decode 每步都要扫 |

和 FlagOS 笔记的对应：FlagGems 里 GDN 走 native/循环核，全注意力和 Linear 才是「编译出来的 GEMM」。两种层对编译器和内存的压力本来就不一样。

---

## 2. KV 账：只算会涨的那 16 层

全注意力（GQA）每个 token：

```text
bytes/token = 2 × L_full × kv_heads × head_dim × elem
            = 2 × 16 × 4 × 256 × 2
            = 64 KiB
```

| 上下文 T | 全注意力 KV | 对照 |
|---|---|---|
| 512（你 bench 的 PP） | 32 MiB | 几乎看不见 |
| 8K | 512 MiB | 仍远小于权重 |
| 32K | 2 GiB | 开始能感觉到 |
| 128K | 8 GiB | 和 22GB 权重同一量级的 1/3 |
| 256K（原生窗口） | 16 GiB | 权重 22 + KV 16，64GB 机器会挤 |

GDN 状态不按 T 涨。公开 serving 口径大约是：48 层 × 48 头 × 128 × 128，fp32 ~154MB，bf16 ~78MB（另加一点 conv state）。相对 22GB 权重可以当成常数。

**若误把 64 层都当成全注意力 GQA：** 每 token 256 KiB，256K 上下文就是 **64 GiB**，这台 64GB Mac 根本装不下。混合注意力不是论文装饰，是你能在 64GB 上开长上下文的原因。

端侧单会话：先撞的是 **22GB 权重**，KV 要到 32K+ 才跟权重抢。  
云上 Agent（见 [Phoenix 笔记](./2026-09-03-lmcache-phoenix-xpuiio.md)）：会话数 × 长前缀，KV 会先把 HBM 打满——同一公式，乘的是并发而不是一层。

---

## 3. Roofline：用你已经测过的数字

M5 Pro 统一内存峰值带宽按 Apple 口径 **307 GB/s**。权重 22GB。若 decode 每步把权重扫一遍、忽略 KV：

```text
理想上限 ≈ 307 / 22 ≈ 14 tok/s
```

| 场景 | 你的数字 | 和 14 tok/s 比 | 读法 |
|---|---|---|---|
| nospec decode | 12.73 tok/s | 约 91% 上限 | **带宽墙**（权重搬运）。再加核也抬不动，除非少读权重 |
| DFlash2 decode | ~23 tok/s | 超过「每步扫 22GB」的上限 | 投机解码让部分 token 不跑完整模型，有效搬运下降 |
| prefill | ~73 tok/s | 远高于 14 | 一段 prompt 摊还权重，算术强度上去，不再是「每 token 扫一遍 22GB」 |

所以：

- 你笔记里的「decode 慢、prefill 还行」不是玄学，是 Roofline 的两种落点。
- DFlash2 的 1.8× 改的是 **要不要每步付 22GB**，不是把 307 GB/s 变大。
- 周 5–6 可以把 KV 读字节叠进分母，把 512 / 8K 两条线分开画；本周先钉住权重这一项。

---

## 4. 这会改哪条判断

1. 讲 Qwen3.8 先画 3:1 混合，再谈 tok/s。只说「27B W4A8」会把 GDN 和 GQA 混成一种内存行为。  
2. 端侧第一堵墙仍是权重；长上下文才轮到 KV。云上 Agent 相反，KV 会先爆。  
3. 编译器作业（GEMM tile → NEON）对应的是 Linear/FFN/全注意力投影；GDN 是另一条核。对照表不要假装一种 schedule 覆盖 64 层。

---

## 5. 未核实（下一次补）

- 你这台 serve 里 KV 实际是 BF16 还是更低精度（会把 64 KiB/token 按比例缩小）。  
- DFlash2 每步接受长度、验证块 M=8 各自省掉多少权重流量。  
- GDN 状态在 FlagOS 运行时的真实 dtype 与字节数（现在用的是公开 serving 口径）。
