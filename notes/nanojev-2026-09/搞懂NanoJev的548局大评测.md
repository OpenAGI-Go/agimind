# 搞懂 NanoJev 的 548 局大评测

（结构稿 · 2026-09-21 起笔，明天接着填。）

上一篇：[搞懂 NanoJev 并把训练跑通](搞懂NanoJev并把训练跑通.md)（阶段 0～7：环境、数据、hard CE SFT、玩具推理收口）。

**我怎么跟助手配合：** 跟上一篇一样——命令我自己敲；一次只做当前阶段；输出贴回来，一起改这篇、填「我看到的」。截图存 `screenshots/`，扩展名用真正的 PNG。

这台机器：还是那张 A800；代码 `$NJ=/root/autodl-tmp/NanoJev`；自训权重 `$RUNS/hard_lr1e5_repro`；官方包 `$CKPT/NanoJev-unified`。

当前我在做：**结构已搭好 · 阶段尚未开跑**

---

## 我到底要搞明白什么

读完这篇，我希望能讲清：

1. 548 局量的是什么：不是单题 CE，是**整局是否成功**（迷宫到终点、蛇活够久/吃够、射击真打中）。
2. 548 从哪来：固定 case 表，大约 **274 test + 274 ood**；构成大致是迷宫 20 + 蛇 16 + Basic 256 + 打移动靶 256。
3. 跟上一篇玩具请求差在哪：玩具是两段客服 JSON；这里是闭环对局，控制器吃概率、环境走步。
4. 我自己的 `hard_lr1e5_repro` 在这把尺子上大概什么水平；和官方 `NanoJev-unified`（以及文档里的 Jev / 未调 Qwen 对照）怎么比。

---

## 进度（先占位）


| 阶段 | 状态 |
|---|---|
| 0 对齐上一篇 | 待做：路径、权重 sha、磁盘 |
| 1 读懂 548 | 待做：case 表、任务拆分、加权成功率 |
| 2 依赖与环境 | 待做：ViZDoom 等是否要装 |
| 3 拿到冻结 case | 待做：test_cases / dev_cases 从哪来 |
| 4 冒烟一小撮 | 待做：先跑几局确认管线 |
| 5 正式 548 | 待做：自训权重闭环 |
| 6 对照官方 | 待做：同一 case 上 NanoJev-unified |
| 7 读结果 | 待做：weighted_success、分任务、test vs ood |
| 8 小结 | 待做 |

---

## 阶段 0 · 对齐上一篇的产物

确认上一篇留下的东西还在，磁盘够跑对局输出。

- [ ] `$NJ`、venv、`$CKPT`、`$RUNS/hard_lr1e5_repro`、`best.safetensors` sha
- [ ] 数据盘空闲（对局日志可能比训练 summary 大，先估再跑）

命令 / 我看到的：

```
（待填）
```

---

## 阶段 1 · 读懂「548 局」在量什么

材料入口（仓库里）：

- `docs/SONIC_PREDICT_POSITION.md`、`docs/SONIC_PREDICT_POSITION_RESULTS.md`
- `configs/sonic_unified_sft_v1.json` 里的 `evaluation` / `population_weights`
- `results/sonic_sft_v1_summary.json`（别人已经跑过的数字，当对照，不是我的结果）

我想自己写清：

| 问题 | 我的理解（待填） |
|---|---|
| 一局 success 怎么定义？迷宫 / 蛇 / Basic / 打移动靶 | |
| 为什么是 548？test / ood 各多少？ | |
| `weighted_success` 四个池子各多少权？ | |
| 控制器 greedy + epsilon 0.1 是什么意思？ | |
| 和上一篇 `selection_ce` 为什么不能互相替代？ | |

我看到的：

```
（待填）
```

---

## 阶段 2 · 评测依赖还要不要再装

上一篇只装了 `requirements-toy.txt`。548 里射击要真环境的话，可能碰到：

- `requirements-vizdoom.txt` / 射击相关依赖
- 是否必须 GPU；一批环境 `env_batch` 多大

先查清「最小能跑通」再装，能不装就不装。

我看到的：

```
（待填：装了什么 / 故意没装什么）
```

---

## 阶段 3 · 冻结 case 表从哪来

官方流程里有 `test_cases.jsonl`、`dev_cases.jsonl`（见 `run_sonic_supervision.py`、summarize 脚本）。

我要搞清：

- 公开释放里有没有现成 case 文件可下
- 还是要从某个 `runs/sonic_unified_sft_v1/` 产物里拷
- case 的 sha / 条数是不是 548

命令 / 我看到的：

```
（待填）
```

---

## 阶段 4 · 冒烟：先跑几局

目标：确认「权重 → 概率 → 控制器 → 环境」闭环通，再开全量。

- [ ] 指定 checkpoint = `$RUNS/hard_lr1e5_repro`
- [ ] 只跑 1～几局（迷宫或 Basic 先）
- [ ] 看输出：`success`、轨迹是否写盘、有没有立刻炸依赖

命令 / 我看到的：

```
（待填）
```

---

## 阶段 5 · 正式跑：自训权重上的 548

- checkpoint：`hard_lr1e5_repro`（best_step=300 那份）
- case：冻结的 548
- 控制器：跟协议对齐（greedy / ε=0.1 / seed 等，以当时读到的协议为准）
- 输出目录：例如 `$RUNS/eval_548_repro/`（名字待定）
- 日志：`tee` 留一份

时间预期、显存、磁盘：（跑之前估，跑完改）

我看到的：

```
（待填：总成功率、分任务、分 split）
```

---

## 阶段 6 · 同一把尺子对照官方 unified

同一套 case、同一控制器设定，把 checkpoint 换成 `$CKPT/NanoJev-unified` 再跑（或对照已发布的 summary 数字——先分清「我复跑的」和「文档里印好的」）。

对比表（占位）：

| 池子 | 我的 repro | 官方 unified | 备注 |
|---|---|---|---|
| maze/policy | | | |
| snake/policy | | | |
| shooting/basic | | | |
| shooting/predict_position | | | |
| weighted_success | | | |

我看到的：

```
（待填）
```

---

## 阶段 7 · 怎么读结果

想记清这些词（跑完用自己的数字填）：

| 词 | 人话 |
|---|---|
| `success` | 这一局任务有没有完成 |
| `weighted_success` | 四个任务池按协议加权后的成功率 |
| test vs ood | 同分布 / 偏分布，分开报 |
| 专家动作一致率 / CE | 贴专家；**不等于**整局成功 |
| replay | 独立模拟器重放轨迹，核对有没有记错 |

可选：跟发布文里的 Jev / Untuned Qwen 表肩并肩看一眼（若本机不复跑那两条，就只引用公开数字并标明来源）。

---

## 阶段 8 · 小结

四句（待填）：

1. 548 量的是 _____  
2. 我的 repro 加权成功率大约 _____  
3. 和官方 unified 差在 _____  
4. 跟上一篇玩具请求比，多证明了 _____  

---

## 附录（先占位）

| 编号 | 内容 |
|---|---|
| A | 548 case 表字段怎么读 |
| B | 一局 episode JSON 里我该看哪些键 |
| C | 和上一篇 CE / 玩具请求指标对照 |

---

## 先不做什么（这轮边界）

- 不重录 896 专家局、不重跑四条臂训练
- 不调 TypeSafe Jev 直播 API（除非我后来改主意并写进阶段）
- 不把 RLCD 当这轮目标

---

## 和上一篇的衔接

| 上一篇 | 这一篇 |
|---|---|
| hard CE SFT 600 步，best=300 | 用那份权重打封闭对局 |
| 玩具请求 decode 0、argmax 对齐官方 | 548 局 success，看会不会玩游戏 |
| `selection_ce` 选 checkpoint | `weighted_success` 谈发布尺子 |
