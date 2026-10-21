# 走通 pyqpanda3 / QPanda3：体会量子编程整条链

2026-09-23。这是我自己的笔记，不是本源官方文档的拷贝。

官方正典：[pyqpanda3 文档中心](https://qcloud.originqc.com.cn/document/pyqpanda3-docs/zh/docs/) · [快速入门](https://qcloud.originqc.com.cn/document/pyqpanda3-docs/zh/tutorial/getting-started)

**这台机器：** MacBook Pro · Apple M5 Pro · 64GB · macOS ARM64。  
官方对 **macOS (ARM64)** 写的是「完全支持」（Clang ≥ 15）；用 `CPUQVM` 本地模拟即可。没有 NVIDIA，不跑 `GPUQVM`。

**我怎么跟助手配合：** 命令我自己在终端里敲。助手不代装、不代跑、不改我机器上的环境。我一次只做当前阶段，做完把终端输出贴到对话里，一起改这篇文档、填「我看到的」。挂了先停。

当前我在做：**阶段 0（地图）→ 准备开阶段 1（环境）**

---

## 我到底要搞明白什么

读完这篇，希望能用自己的话讲清四句：

1. 量子程序主要是：**线路（门序列）+ 测量**；跑完得到的是概率分布（counts），不是一个确定返回值。
2. **QPanda3** 是 C++ 内核；**pyqpanda3** 是 Python SDK。我们用手写和跑的是后者。
3. 本机主路径：`写 QProg` → `CPUQVM.run` → `get_counts`。上云/真机多一层：转译、拓扑、提交任务。
4. VQE / QAOA 这类东西 = **参数化量子线路 + 经典优化循环**，不是纯量子程序一次性算完。

---

## 0. 地图：整条链长什么样

```text
你写的 Python（pyqpanda3）
        │
        ▼
   QProg / 门 / 测量          ← 逻辑线路
        │
        ├─► CPUQVM（本机模拟）──► counts / 期望值     ← 我们主线
        │
        └─► Transpiler / OriginIR / QASM
                │
                ▼
           QCloud / 真机（可选）
```

和经典程序对照（先建立感觉，不必严谨）：

| 我熟的 | 这里换成 |
| --- | --- |
| `f(x)` 算一个数 | 线路演化一个态，再测量抽样 |
| 调试打印中间变量 | 大多只能看测量统计；模拟器偶尔能看态矢量 |
| PyTorch 跑在 CPU/GPU | `CPUQVM` /（可选）云后端 |
| CUDA | **没有**行业统一版；pyqpanda3 是本源这一栈的 SDK |

**我看到的（阶段 0）：**

> （用自己的话写两句：QPanda3 和 pyqpanda3 各管什么）

---

## 1. 环境：装上并能 import

### 1.1 选对 Python

系统自带的 `python3` 若是 **3.9**，太旧（官方要 **3.10–3.14**）。本机已有 `python3.12` / `python3.11`，用它们建 venv。

```bash
python3.12 --version
# 期望类似：Python 3.12.x
```

### 1.2 建虚拟环境并安装

路径可自定，下面只是示例：

```bash
python3.12 -m venv ~/venvs/pyqpanda3
source ~/venvs/pyqpanda3/bin/activate
python -m pip install -U pip
pip install pyqpanda3
```

### 1.3 macOS 常见坑：libidn2

若 `import pyqpanda3` 报类似：

```text
Library not loaded: /opt/homebrew/opt/libidn2/lib/libidn2.0.dylib
```

按官方说明先装库：

```bash
brew install libidn2
# 或：brew reinstall libidn2
```

**本机额外注意：** Homebrew 若在 `~/.homebrew`，而报错死盯 `/opt/homebrew/...`，需要把路径对齐（例如把 `libidn2` 链到 `/opt/homebrew/opt/libidn2`）。对齐前先确认：

```bash
brew --prefix
brew --prefix libidn2
ls "$(brew --prefix libidn2)/lib"
```

把这三条输出贴回来再决定怎么链，别瞎 `sudo`。

### 1.4 验证

```bash
python - <<'PY'
import pyqpanda3
print("version:", pyqpanda3.__version__)
from pyqpanda3 import core
m = core.CPUQVM()
print("CPUQVM ok")
PY
```

**我看到的（阶段 1）：**

> version:  
> CPUQVM:  
> 若踩过 libidn2，我是怎么修的：

**本阶段完成标志：** `import pyqpanda3` 成功，且能创建 `CPUQVM()`。

---

## 2. 第一个程序：贝尔态

最小完整故事：叠加 + 纠缠 + 测量。

```bash
python - <<'PY'
from pyqpanda3 import core

prog = core.QProg()
prog << core.H(0)
prog << core.CNOT(0, 1)
prog << core.measure([0, 1], [0, 1])

machine = core.CPUQVM()
machine.run(prog, shots=1000)
print(machine.result().get_counts())
PY
```

期望直觉：大约一半 `00`、一半 `11`，几乎没有 `01` / `10`。

在线路上发生了什么（直觉版）：

1. `H(0)`：比特 0 进入叠加  
2. `CNOT(0,1)`：把相关性写到比特 1 → 纠缠  
3. `measure`：塌缩成经典比特串，重复 `shots` 次得到直方图  

**我看到的（阶段 2）：**

> counts:  
> 和预期差多少：

**本阶段完成标志：** 跑出以 `00`/`11` 为主的 counts。

---

## 3. 读结果：shots、counts、和「态」

自己改 `shots`（如 100 / 1000 / 10000）各跑一次，看分布稳不稳。

想一想（写进「我看到的」即可）：

- 为什么同线路每次 counts 不完全一样？  
- 模拟器若能给出态矢量，和 counts 是什么关系？  
- 真机上通常只能拿到哪一种？

**我看到的（阶段 3）：**

>  

---

## 4. 线路积木：组合与（可选）可视化

目标：会用 `QCircuit` 拼一块再 `append`/`<<` 进 `QProg`；知道量子比特用**整数下标**（新 API，不是旧版 `qAlloc`）。

可对照官方：[量子线路构建](https://qcloud.originqc.com.cn/document/pyqpanda3-docs/zh/tutorial/)（侧边栏「量子线路构建」）。

**我看到的（阶段 4）：**

>  

---

## 5. 稍难一点：GHZ 或 Deutsch-Jozsa（二选一）

- GHZ：三比特「全 0 / 全 1」相关  
- 或官方 how-to：Deutsch-Jozsa / Grover 任选一个最小例子  

How-to 入口：[操作指南](https://qcloud.originqc.com.cn/document/pyqpanda3-docs/zh/docs/) → Bell / GHZ / Grover / VQE / QAOA

**我看到的（阶段 5）：**

> 我选的是：  
> 结果：

---

## 6. 噪声一眼

同一条贝尔态线路，加个简单 `NoiseModel`，再看 counts 是否出现「不该有」的 `01`/`10`。

目的：体会 **理想模拟 ≠ 真机**；噪声会把理想关联糊掉。

**我看到的（阶段 6）：**

>  

---

## 7. 变分一眼（不调参到收敛）

只求建立模型：

```text
参数 θ → 参数化线路 → 测期望值 ⟨H⟩ → 经典优化器改 θ → 再跑
```

在文档里摸一下 `VQCircuit` / `Parameter` / 期望值 API 即可，不必追求 VQE 收敛。

**我看到的（阶段 7）：**

>  

---

## 8. 收口：IR / 转译 /（可选）云

把整条链说圆：

```text
逻辑线路 →（Transpiler / 拓扑）→ 可执行形式 → OriginIR 或 QASM → QCloud 任务
```

没有云账号就停在「看懂提交长什么样」；有账号再开 [量子云用户指南](https://qcloud.originqc.com.cn/document/pyqpanda3-docs/zh/tutorial/quantum-cloud-user-guide.html)。

**我看到的（阶段 8）：**

>  

---

## 附录 A · 别混版本

| | 旧 | 新（我们用这个） |
| --- | --- | --- |
| 包名 | `pyqpanda` | `pyqpanda3` |
| 内核 | QPanda2 | QPanda3 |
| 比特 | `qAlloc` 对象 | 整数下标 `H(0)` |
| 机器 | 常要 `init_qvm()` | `CPUQVM()` 直接用 |

不要两套 import 混在同一脚本里。

## 附录 B · 官方链接速查

- 文档首页：https://qcloud.originqc.com.cn/document/pyqpanda3-docs/zh/docs/  
- 快速入门：https://qcloud.originqc.com.cn/document/pyqpanda3-docs/zh/tutorial/getting-started  
- API：https://qcloud.originqc.com.cn/document/pyqpanda3-docs/zh/api/  
- AI Skill（可选）：https://github.com/OriginQ/pyqpanda3-skill  

---

## 进度

| 阶段 | 状态 | 日期 |
| --- | --- | --- |
| 0 地图 | 进行中 | |
| 1 环境 | 未开始 | |
| 2 Bell | 未开始 | |
| 3 读结果 | 未开始 | |
| 4 积木 | 未开始 | |
| 5 GHZ/DJ | 未开始 | |
| 6 噪声 | 未开始 | |
| 7 变分一眼 | 未开始 | |
| 8 IR/云收口 | 未开始 | |
