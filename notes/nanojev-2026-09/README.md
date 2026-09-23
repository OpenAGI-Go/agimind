# NanoJev 学习笔记（2026-09）

在 AutoDL A800 上亲手复现公开 hard CE SFT，并准备 548 局大评测。

## 文档

- [搞懂 NanoJev 并把训练跑通](./搞懂NanoJev并把训练跑通.md) — 主线阶段 0～7
- [搞懂 NanoJev 的 548 局大评测](./搞懂NanoJev的548局大评测.md) — 下一档结构稿
- [这次 pip 装进来的包是干什么的](./这次pip装进来的包是干什么的.md)
- [把自训权重传到 Hugging Face 和 ModelScope](./把自训权重传到HuggingFace和ModelScope.md) — 上传流程与踩坑

## 延伸（2026-09-22）

- [开源 Jev 模型梳理：NanoJev、Nimble、Laya](../2026-09-22-open-jev-models-nanojev-nimble-laya.md) — System One 接口、三者对比、模型形态
- [Mac 上大模型训推开源地图](../2026-09-22-mac-train-infer-landscape.md) — MLX vs MPS、内存选型、本地训推栈
- [为什么底座都用 Qwen](../../sparks/2026-09-22-为什么底座都用Qwen.md) — 随笔

## 其它

- `screenshots/` — 各阶段终端 / 页面截图（PNG）
- `stage7/` — 自训 vs 官方玩具推理 JSON
- `runs-meta/` — smoke / repro 的 summary、train_log（**不含** 2.3G 权重）

机器上的权重与数据仍在 AutoDL：`/root/autodl-tmp/nanojev-study/{ckpts,data,runs}`；上游代码：`/root/autodl-tmp/NanoJev`。
