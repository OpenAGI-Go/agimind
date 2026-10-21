# cn-net · 云主机包源与模型源配置

在租用的 GPU 云主机上，给当前 shell 设好常用的 **PyPI 索引** 和 **Hugging Face Hub endpoint**，方便装依赖、拉模型。上传权重到官方 Hub 前请先关掉。

```bash
source cn_net.sh          # 设置 HF_ENDPOINT + pip/uv 索引；若存在则沿用机器自带的 /etc/network_turbo
cn_net_probe              # 检查各索引是否可达
cn_git_clone https://github.com/LMCache/LMCache.git
cn_pip install -U pip
```

| 命令 | 作用 |
|------|------|
| `source cn_net.sh` / `on` | 启用当前 shell 的源配置 |
| `source cn_net.sh off` | 恢复默认（**推送 HF 前先 off**） |
| `cn_net_status` / `probe` | 查看环境变量 / 探测可达性 |
| `cn_git_clone <url> [dir]` | clone GitHub 仓库（直连失败时再试备用入口） |
| `cn_pip …` | 使用当前 `PIP_INDEX_URL` 的 `python -m pip install` |

默认偏好（按本机实测调整过）：

- **pip / uv**：优先 USTC，其次阿里云等公开索引
- **HF 下载**：`HF_ENDPOINT=https://hf-mirror.com`，并默认 `HF_HUB_DISABLE_XET=1`（避免 xet 绕过 endpoint）
- **GitHub**：不改全局 `insteadOf`；需要时用 `cn_git_clone`，或使用云厂商提供的 `/etc/network_turbo`
