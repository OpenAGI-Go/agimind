# cn-net · 国内云主机网络加速

登录 AutoDL / 同类机器后：

```bash
# 把脚本拷上去，或从本仓同步
source cn_net.sh          # 开 HF 镜像 + pip 源；有则尝试 /etc/network_turbo
cn_net_probe              # 看哪些镜像通
cn_git_clone https://github.com/LMCache/LMCache.git
cn_pip install -U pip
```

| 命令 | 作用 |
|------|------|
| `source cn_net.sh` / `on` | 开启 |
| `source cn_net.sh off` | 关闭（**上传 HF 前先 off**） |
| `cn_net_status` / `probe` | 状态 / 探测 |
| `cn_git_clone <url> [dir]` | GitHub clone（直连 → turbo → 公共前缀） |
| `cn_pip …` | 带镜像的 `python -m pip install` |

默认策略（被本仓踩坑验证过）：

- **pip / uv**：中科大优先（部分 AutoDL 上清华 403、阿里云偏慢）
- **HF 下载**：`HF_ENDPOINT=https://hf-mirror.com` + `HF_HUB_DISABLE_XET=1`
- **GitHub**：不永久改 `insteadOf`；用 `cn_git_clone` 或 AutoDL `network_turbo`
