# 推到 OpenAGI-Go/agimind

AutoDL 这台容器 **连不上 github.com**（TCP 超时），所以 push 需要在你本机（能开 GitHub 的环境）做。

## 已整理好的内容（轻量，约 7MB）

目录：`/root/autodl-tmp/agimind-staging/notes/nanojev-2026-09/`

或打包：`/root/autodl-tmp/agimind-nanojev-notes.tar.gz`

```text
notes/nanojev-2026-09/
  README.md
  搞懂NanoJev并把训练跑通.md
  搞懂NanoJev的548局大评测.md
  这次pip装进来的包是干什么的.md
  screenshots/          # 各阶段 PNG
  stage7/               # 玩具推理对比 JSON
  runs-meta/            # summary / train_log（无 2.3G 权重）
```

**故意没带：** `.venv`、`ckpts/`、`data/`、`runs/*/best.safetensors`、上游 `NanoJev/` 整仓。

## 本机推送示例

```bash
# 1) 从 AutoDL 拷下来（按你平时的 scp / Cursor 下载）
#    例如拿到 agimind-nanojev-notes.tar.gz

# 2) 解压并放进 agimind
git clone git@github.com:OpenAGI-Go/agimind.git
cd agimind
tar -xzf /path/to/agimind-nanojev-notes.tar.gz
# 得到 notes/nanojev-2026-09/

# 3) 若仓里已有别的 notes 结构，把 nanojev-2026-09 挪到对应位置后：
git add notes/nanojev-2026-09
git status
git commit -m "$(cat <<'EOF'
Add NanoJev study notes (SFT repro + 548 eval outline).

EOF
)"
git push
```
