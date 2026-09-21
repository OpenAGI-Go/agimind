# 把自训权重传到 Hugging Face 和 ModelScope

AutoDL A800 上 `hard_lr1e5` 复现训完之后，我想把 checkpoint 挂到网上，方便关机后还能拉下来续训 / serve。两边都传了一份。

| 平台 | 仓库 |
|------|------|
| ModelScope | [maxonxie/nanojev-hard-lr1e5-repro](https://www.modelscope.cn/models/maxonxie/nanojev-hard-lr1e5-repro) |
| Hugging Face | [maxonxie/nanojev-hard-lr1e5-repro](https://huggingface.co/maxonxie/nanojev-hard-lr1e5-repro) |

对照官方发布：[C-Tianyu/NanoJev](https://huggingface.co/C-Tianyu/NanoJev) 根目录那一套 checkpoint 布局。

---

## 1. 本地先整理一份「能公开的包」

原始训练目录：

```text
/root/autodl-tmp/nanojev-study/runs/hard_lr1e5_repro
```

上传用目录（和原始硬链接同一份 `best.safetensors`，不占双倍盘）：

```text
/root/autodl-tmp/nanojev-study/hf-upload/nanojev-hard-lr1e5-repro
```

一开始我只想传「最小能 serve」的几样；后来想对齐程天宇仓库根目录、而且以后可能还要从网上下来续训，就把 **predictions / audit 也带上了**：

| 文件 | 作用 |
|------|------|
| `best.safetensors` | best_step=300，约 2.3G |
| `config.json` | 本机跑出来的配置（里头可能有 AutoDL 绝对路径） |
| `training_config.json` | 同超参，绝对路径已抹掉，换机续训时改路径用 |
| `tokenizer/`、`backbone_config/` | serve / 续训都要 |
| `summary.json`、`train_log.json` | 指标和步日志 |
| `predictions_{dev,test,ood,calibration}.jsonl` | 各 split 预测 |
| `initial_dev.jsonl`、`initial_dev_metrics.json` | 开训前后对照 |
| `target_audit.json` | 目标审计 |
| `README.md` | 模型卡（配方、SHA、怎么 serve） |

官方仓里还有 `variants/`、`stage1/`、`source/`——那是整仓发布；我这份只是 **一次 run 的完整产物**。

---

## 2. ModelScope（这台 AutoDL 上最顺）

### 账号与 CLI

```bash
source /root/autodl-tmp/nanojev-study/.venv/bin/activate
pip install -U modelscope   # 当时装的是 1.40.x，带 modelscope_hub

# Token：https://www.modelscope.cn/my/myaccesstoken
modelscope login --token <TOKEN>
modelscope whoami   # → maxonxie
```

### 建库 + 上传

网页「创建模型」或 CLI：

```bash
modelscope create maxonxie/nanojev-hard-lr1e5-repro \
  --repo-type model \
  --visibility private \
  --license MIT \
  --chinese-name "NanoJev hard CE 复现权重" \
  --exist-ok

modelscope upload maxonxie/nanojev-hard-lr1e5-repro \
  /root/autodl-tmp/nanojev-study/hf-upload/nanojev-hard-lr1e5-repro \
  --repo-type model \
  --commit-message "Add hard_lr1e5 repro checkpoint (full run artifacts)"
```

第一次真正传完大约几十秒量级（大 blob 可复用）；再跑同一条会显示：

```text
17 file(s) already committed, skipping.
✓ All files already committed, nothing to upload.
```

这是正常的，不是没传上去。

### 核对

仓库页能看到 `best.safetensors` ≈ 2385039280 字节；CLI `get_model_files` 递归列表里 config / tokenizer / predictions / README 都在。后来把可见性改成了公开（visibility=5）。

---

## 3. Hugging Face（AutoDL 上坑最多）

### 网页先建空库

账号 `maxonxie` → New Model → `nanojev-hard-lr1e5-repro`。  
仓库建好后是空的；**别在网页拖 2.3G**，用 CLI。

### 正路命令（理想情况）

```bash
source /root/autodl-tmp/nanojev-study/.venv/bin/activate
hf auth login

hf upload-large-folder maxonxie/nanojev-hard-lr1e5-repro \
  /root/autodl-tmp/nanojev-study/hf-upload/nanojev-hard-lr1e5-repro \
  --repo-type model --num-workers 4
```

`upload-large-folder` 自带断点：断了重跑同一条，已传完的不重传。新版 CLI 会提示它 deprecated、让改用 `hf upload`；这台机器上我仍用 large-folder，续传行为符合预期。

---

## 4. 踩坑记录

### 坑 1：`HF_ENDPOINT=hf-mirror` 是下载用的，上传别瞎套

学习笔记里下数据/权重一直写：

```bash
export HF_ENDPOINT=https://hf-mirror.com
```

第一次 `hf upload` 时环境里却走到了 **`hf-mirror.org`**（注意 `.org`）。  
分片都能往 LFS 里灌，收尾 `complete_multipart` / `lfs/objects/verify` 报：

```text
[Errno -5] No address associated with hostname
... hf-mirror.org/api/complete_multipart ...
```

`hf-mirror.org` 在这台机上 **DNS 直接 NXDOMAIN**。镜像域名要用 **`.com`**。

### 坑 2：`unset HF_ENDPOINT` 直连官方也不通

关掉镜像后：

```text
httpx.ConnectError: [Errno 101] Network is unreachable
```

测过：`huggingface.co`（IPv4/IPv6）和 `cdn-lfs.huggingface.co` 都连不上；`hf-mirror.com`、`modelscope.cn` 正常。  
**AutoDL 这台机出不去官方 HF，上传只能走镜像。**

### 坑 3：设了 `HF_ENDPOINT=https://hf-mirror.com`，LFS 仍会请求 `.org`

`batch` 打 `.com` 成功，`verify` 却被指到 `https://hf-mirror.org/...`。  
把 `.org` 写进 `/etc/hosts` 指到 `.com` 的 IP 也不行——TLS 证书对不上，握手直接挂。

做法：上传脚本里把 httpx 请求 URL 里的 `hf-mirror.org` **改写成** `hf-mirror.com`，再调 `HfApi(endpoint="https://hf-mirror.com").upload_large_folder(...)`。  
小文件（README）先试通，再传整包。

### 坑 4：上传和下载的环境变量要分开想

| 场景 | 建议 |
|------|------|
| 这台机 **下载** HF 数据/权重 | `export HF_ENDPOINT=https://hf-mirror.com` |
| 这台机 **上传** 到 HF | 同样走 `hf-mirror.com`，并防住 `.org` 回跳 |
| 有外网的机器（Mac / 家里）上传 | 可以 `unset HF_ENDPOINT`，直连 `huggingface.co` |
| ModelScope | 不依赖 HF 镜像，AutoDL 上最省心 |

### 坑 5：别把本地上传缓存目录一并推上去

HF 仓库文件列表里一度出现过 `.ms_upload_cache`（ModelScope 上传元数据）。  
整理上传包时尽量不要把 `.cache/`、`.ms_upload_cache` 放进要传的根目录；已经误传的话可以以后再从网页删。

---

## 5. 传完怎么用

### 从 ModelScope 拉

```bash
modelscope download maxonxie/nanojev-hard-lr1e5-repro \
  --local_dir ./nanojev-hard-lr1e5-repro
```

### 从 Hugging Face 拉（国内机继续走镜像）

```bash
export HF_ENDPOINT=https://hf-mirror.com
hf download maxonxie/nanojev-hard-lr1e5-repro \
  --local-dir ./nanojev-hard-lr1e5-repro
```

### serve / 续训

目录形状对齐官方 unified 根目录：把 `--checkpoint-dir` / init checkpoint 指到解压后的文件夹即可（具体 flag 跟 NanoJev 当前脚本一致）。  
`config.json` 里若还有 AutoDL 路径，换机时改数据路径或看 `training_config.json`。

权重 SHA256（summary 里）：

```text
f53eadbd34eb5a1040d9d579c64bebde45a7180fa3b012d187e64c118c09022f
```

---

## 6. 一句话对照

- **ModelScope**：建库 → `modelscope upload` → 完事；再跑同一条会 skip。  
- **Hugging Face（AutoDL）**：必须 `hf-mirror.com`；躲开 `.org`；大文件用 `upload-large-folder`（或等价 API）续传。  
- **关机前**：权重已在两个平台，AutoDL 数据盘释放也不怕丢这份 repro。
