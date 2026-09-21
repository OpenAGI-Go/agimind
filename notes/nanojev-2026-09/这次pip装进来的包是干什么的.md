# 这次 pip 装进来的包是干什么的

2026-09-21。跟主笔记同一天。主笔记：[搞懂 NanoJev 并把训练跑通](搞懂NanoJev并把训练跑通.md)

我主动点名的只有配方四个包，外加 `huggingface_hub`。终端里却刷出几十个名字。原因很简单：`pip` 会把依赖的依赖也装上。这篇只记这次装进 `$STUDY/.venv` 的东西，不讲没装的。

命令是：

```bash
python -m pip install -i https://mirrors.ustc.edu.cn/pypi/simple \
  --trusted-host mirrors.ustc.edu.cn \
  -r "$NJ/requirements-toy.txt" huggingface_hub
```

最后一行 `Successfully installed` 里的名字，下面都有。

---

## 先看依赖怎么长出来的

```text
我点名
├── torch 2.14.0
│     ├── 算图、张量、反向传播（Python 层）
│     └── 为了在 A800 上干活，再拖 CUDA 13 全家桶 + Triton
├── transformers 5.17.0
│     ├── 读 Qwen3 的结构、分词、权重
│     └── 命令行、进度条、YAML、正则……
├── safetensors 0.8.0     权重文件格式
├── numpy 2.5.3           数组，torch / 数据处理都用
└── huggingface_hub 1.32.0
      └── 从 Hugging Face 下模型和数据集（httpx 那一串）
```

下面按这五棵树讲。名字后面的版本就是这次装上的。

---

## 一、我点名的五个

### torch 2.14.0

PyTorch。张量、自动求导、`nn.Module`、优化器、GPU 调度，全在这儿。NanoJev 的决策头、前向、反向、`train_unified_games.py` 都站在它上面。

Linux 默认这个 wheel 绑的是 **CUDA 13.0**，所以会再拉 `cuda-toolkit==13.0.3` 和一堆 `nvidia-*`。这不是我另装的 CUDA 发行版，是 PyPI 上的 Python 包，给这台机的驱动当用户态库用。

### transformers 5.17.0

Hugging Face 的模型库。NanoJev 用它加载 **Qwen3-0.6B** 的配置、分词器、骨干权重。没有它，本地脚本读不了官方那种 `config.json` + tokenizer 目录。

### safetensors 0.8.0

一种存权重的格式（`.safetensors`）。比老的 `pickle` 安全：只存数组，不执行代码。官方 checkpoint `best.safetensors`、初始化权重都是这个。

### numpy 2.5.3

多维数组。torch 能跟它互转；读数据、拼 batch、看形状时经常碰到。配方钉死版本，避免和官方实验对不齐。

### huggingface_hub 1.32.0

跟 Hugging Face Hub 说话的客户端。后面下载 `C-Tianyu/NanoJev` 权重、`NanoJev-Data` 数据集，走的就是它的 `snapshot_download`。配方里没有，我额外点的。

---

## 二、torch 为了上 GPU 拖进来的

可以想成三层：

1. **驱动**已经在机器上了（`nvidia-smi` 能看到）。
2. 下面这些是 **用户态 CUDA 库**，装进 venv，torch 调用它们把核丢到 A800 上。
3. 再上面才是 Python 的 `import torch`。

### 总入口

| 包 | 版本 | 干什么 |
|---|---|---|
| cuda-toolkit | 13.0.3.0 | 几乎是个空壳，声明「我要 CUDA 13.0.3」，再按 extra 把 cublas、cudart 那些拉齐。 |
| cuda-bindings | 13.4.2 | CUDA 的 Python 绑定。torch 2.14 用它调驱动/运行时，不用自己搓 ctypes。 |
| cuda-pathfinder | 1.8.2 | 在磁盘上找到 `.so`。venv 里库很多，得有人指路。 |

### 真正干活的 NVIDIA 库

名字里的 `cu13` 表示给 CUDA 13 用。没有这个后缀的，版本号自己已经是 13.x。

| 包 | 版本 | 人话 |
|---|---|---|
| nvidia-cuda-runtime | 13.0.96 | CUDA Runtime（cudart）。分配显存、拷数据、启动 kernel。没有它 torch 上不了 GPU。 |
| nvidia-cublas | 13.1.1.3 | GPU 上的矩阵乘。Transformer 里几乎所有线性层最后都是 GEMM，训练时最吃这个。 |
| nvidia-cudnn-cu13 | 9.24.0.43 | 深度学习原语：卷积、归一化、一部分注意力实现。体积大（这次约 553 MB），但训练会用到。 |
| nvidia-nccl-cu13 | 2.30.7 | 多卡通信（AllReduce 等）。我这台只有 1 张 A800，现在用不上，wheel 还是绑着。 |
| nvidia-nvshmem-cu13 | 3.4.5 | GPU 之间的共享内存通信。同样偏多卡/高性能，单卡先当陪绑。 |
| nvidia-cusparselt-cu13 | 0.8.1 | 结构化稀疏矩阵乘。有的加速路径会用，不是我每天直接 import 的。 |
| nvidia-cusparse | 12.6.3.3 | 普通稀疏矩阵。 |
| nvidia-cusolver | 12.0.4.66 | 解线性方程组、分解。个别算子会碰到。 |
| nvidia-cufft | 12.0.0.61 | GPU 上做 FFT。语音/部分卷积会用；这条训练主路径不太吃它。 |
| nvidia-curand | 10.4.0.35 | GPU 随机数。dropout、采样、初始化会间接用到。 |
| nvidia-cuda-nvrtc | 13.0.88 | 运行时把 CUDA C++ 编译成 GPU 码。动态编译 kernel 时需要。 |
| nvidia-nvjitlink | 13.4.92 | 把即时编译出来的码链成能跑的东西。和 nvrtc 搭档。 |
| nvidia-cufile | 1.15.1.6 | GPUDirect Storage：磁盘数据尽量少绕 CPU，直达 GPU。大 checkpoint 时可能受益。 |
| nvidia-cuda-cupti | 13.0.85 | 给 profiler 用的接口。`nsys` / PyTorch profiler 靠它看 kernel。训练本身不强制。 |
| nvidia-nvtx | 13.0.85 | 在时间线上打标注，方便 profiler 看出「这段是前向、那段是反向」。 |

### Triton 和 torch 自己的小配件

| 包 | 版本 | 干什么 |
|---|---|---|
| triton | 3.8.0 | 用 Python 写 GPU kernel。PyTorch 的 `torch.compile`、一部分 SDPA/融合算子走它。官方推理脚本里有 `--disable-native-triton`，是因为有的环境 Triton 会闹脾气；库还是装上了。 |
| filelock | 4.0.1 | 文件锁。多进程同时写同一份缓存/权重时，别互相踩。 |
| typing-extensions | 4.16.0 | 给类型标注补新语法。torch / transformers 都依赖。 |
| setuptools | 84.0.0 | 打包工具。部分包安装和入口脚本还靠它。 |
| sympy | 1.14.0 | 符号计算。`torch.compile` 化简表达式时用。 |
| mpmath | 1.3.0 | 高精度算术。sympy 的依赖。 |
| networkx | 3.6.1 | 图。FX / Dynamo 把计算图画出来分析时用。 |
| jinja2 | 3.1.6 | 模板。torch 生成代码、报错页会用。 |
| MarkupSafe | 3.0.3 | jinja2 的依赖，做字符串转义。 |
| fsspec | 2026.9.0 | 把本地盘、HTTP、Hugging Face 都当成「文件系统」来读。下模型、读 parquet 常经过它。 |

---

## 三、transformers 拖进来的

| 包 | 版本 | 干什么 |
|---|---|---|
| tokenizers | 0.23.2 | 快速分词（Rust 实现）。Qwen3 的 tokenizer 实际跑的是它，transformers 是上层 API。 |
| packaging | 26.3 | 解析版本号：`>=4.10.0` 这种比较。 |
| pyyaml | 6.0.3 | 读 YAML。不少配置、Hub 元数据是 YAML。 |
| regex | 2026.9.10 | 比标准库 `re` 更强的正则。分词预处理会用。 |
| tqdm | 4.70.1 | 进度条。下载、训练 step 那条会动的条。 |
| typer | 0.27.2 | 用 Python 函数生成命令行。`transformers` 自带的 CLI 走它。 |

typer 自己又拖了一串，我训练脚本一般不直接碰，但装进来了：

| 包 | 版本 | 干什么 |
|---|---|---|
| click | 8.5.0 | 更老牌的命令行库。typer 底下是它；huggingface_hub 的 CLI 也用。 |
| shellingham | 1.5.4 | 探测当前 shell，好给 CLI 做自动补全。 |
| rich | 15.0.0 | 终端里彩色、表格、漂亮报错。 |
| annotated-doc | 0.0.5 | 给 typer 的文档注解用。 |
| pygments | 2.21.0 | 代码高亮。rich 用。 |
| markdown-it-py | 4.2.0 | 把 Markdown 解析成 token。rich 渲染 Markdown 用。 |
| mdurl | 0.1.2 | markdown-it-py 处理 URL 的小库。 |

---

## 四、huggingface_hub 拖进来的（联网那一层）

下载权重、数据集都要 HTTPS。这一串就是客户端：

| 包 | 版本 | 干什么 |
|---|---|---|
| httpx | 0.28.1 | 现代 HTTP 客户端。Hub 用它发请求。 |
| httpcore | 1.0.9 | httpx 底下真正说话的引擎。 |
| h11 | 0.16.0 | HTTP/1.1 状态机。httpcore 的一块积木。 |
| anyio | 4.15.1 | 异步 I/O 的统一层（asyncio 等）。httpx 依赖。 |
| certifi | 2026.7.22 | 一包根证书。HTTPS 校验服务器是不是真的 Hugging Face。 |
| idna | 3.20 | 国际域名编码。URL 里有非 ASCII 主机名时用。 |
| hf-xet | 1.6.0 | Hugging Face 的 Xet 传输。大文件分块、去重，下模型有时比纯 HTTPS 快。 |

`click` 上面已经出现过，hub 的命令行也用它。

---

## 五、按名字再扫一眼（防漏）

上面分组已经覆盖 `Successfully installed` 的全部 52 个名字。再按「跟 NanoJev 这条路的远近」收一下：

**我会在代码里直接碰到的**

- `torch`：模型、训练循环
- `transformers`：骨干和 tokenizer
- `safetensors`：读写 `.safetensors`
- `numpy`：数组
- `huggingface_hub`：`snapshot_download`

**训练时在底下转、我很少 import 的**

- CUDA 那一排：`nvidia-cublas`、`nvidia-cudnn-cu13`、`nvidia-cuda-runtime`、`triton`……没它们 GPU 跑不起来或会极慢
- `tokenizers`、`tqdm`、`fsspec`、`filelock`、`pyyaml`

**这次用不上、但是被绑来的**

- 多卡：`nvidia-nccl-cu13`、`nvidia-nvshmem-cu13`
- profiler：`nvidia-cuda-cupti`、`nvidia-nvtx`
- CLI 漂亮输出：`typer`、`rich`、`pygments` 那串
- 稀疏 / FFT / 解方程：`nvidia-cusparselt-cu13`、`nvidia-cufft`、`nvidia-cusolver` 等

删它们不安全：torch 的 Linux wheel 声明了依赖，缺了可能 `import torch` 或第一次上 GPU 就炸。单卡训练多占的是磁盘，不是显存。

---

## 六、和官方配方差在哪

对齐了：`torch==2.14.0`、`transformers==5.17.0`、`safetensors==0.8.0`、`numpy==2.5.3`。

没对齐：Python 是 **3.12.3**，上游实验机是 **3.14.4**。wheel 文件名里的 `cp312` 就是这个意思。

`huggingface_hub==1.32.0` 是当时中科大源给出的最新版，配方没钉死它。

---

## 七、后来又动过什么（对照现在的 venv）

配方那次 `Successfully installed` 记的是 **52** 个名字。今天我又扫了一眼 `$STUDY/.venv`，和当时比对：

**训练 / 推理主路径：没有再 pip 新配方。**  
中间用到的 `huggingface_hub.snapshot_download`、`hf auth login`、训练、`serve_decisions`，都还是上面那棵树。也**没**去装仓库里的 `requirements-vizdoom.txt` / `requirements-shooting-demo.txt`——那是真开 ViZDoom 录专家或射击 demo 才要的，这轮复现用不上。

**环境变量不算装包，但跟 Hub 有关：**

- `HF_ENDPOINT=https://hf-mirror.com`：走镜像下数据和权重  
- `HF_HUB_DISABLE_XET=1`：关掉 `hf-xet`，避免它绕开镜像又去撞官方网

**后来多出来的一个包：`pillow` 12.3.0**  
写笔记、处理终端截图时补进 venv 的（把扁 JPEG 垫成能预览的 PNG）。**训练脚本不依赖它**；删了也不影响 `train_unified_games` / `serve_decisions`。只是现在 `pip list` 里会多看到这一行。

**一开头还升过 pip：** 阶段 0 有 `python -m pip install -U pip`，所以列表里有 `pip 26.2.1`。那是安装器自己，不是 NanoJev 依赖。

一句话：跟 NanoJev 算账相关的，还是配方那五个 + Hub；多出来的只有笔记用的 `pillow`，以及 Hub 镜像那两行环境变量。
