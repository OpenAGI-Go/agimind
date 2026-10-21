#!/usr/bin/env bash
# 国内云主机（AutoDL 等）一键加速：GitHub / Hugging Face / pip(uv)
#
# 用法（必须 source，export 才进当前 shell）：
#   source /path/to/cn_net.sh          # 开启
#   source /path/to/cn_net.sh on
#   source /path/to/cn_net.sh off      # 关闭
#   source /path/to/cn_net.sh status
#   source /path/to/cn_net.sh probe    # 测各镜像是否通
#
# 经验（本仓 AutoDL 踩过的坑）：
# - 清华 PyPI 在部分 AutoDL 区会 HTTP 403 → 默认优先中科大
# - HF 下载用 hf-mirror.com；上传权重请 cn_net off 或 unset HF_ENDPOINT
# - hf_xet 可能绕过镜像直连官方 → 默认关掉
# - AutoDL: source /etc/network_turbo 只加速 github/hf，且部分地区不可用

_CN_NET_CMD="${1:-on}"

_cn_net_is_sourced() {
  # shellcheck disable=SC3028
  [[ "${BASH_SOURCE[0]}" != "${0}" ]]
}

_cn_net_say() { printf '[cn-net] %s\n' "$*"; }

# ---------- 候选镜像（按优先序）----------
# PyPI：中科大 > 阿里云 > 豆瓣；清华作 probe 备用（部分机房 403）
_CN_PIP_CANDIDATES=(
  "https://mirrors.ustc.edu.cn/pypi/simple"
  "https://mirrors.aliyun.com/pypi/simple"
  "https://pypi.douban.com/simple"
  "https://pypi.tuna.tsinghua.edu.cn/simple"
)
_CN_HF_MIRROR="https://hf-mirror.com"
# git clone 包装用的 GitHub 前缀（不稳定，失败会回退直连 / turbo）
_CN_GH_PREFIXES=(
  "https://ghfast.top/https://github.com/"
  "https://mirror.ghproxy.com/https://github.com/"
  "https://gitclone.com/github.com/"
)

_cn_net_http_ok() {
  local url="$1"
  curl -fsSIL --connect-timeout 3 --max-time 8 "$url" >/dev/null 2>&1
}

_cn_net_pick_pip() {
  local u
  for u in "${_CN_PIP_CANDIDATES[@]}"; do
    if _cn_net_http_ok "$u"; then
      printf '%s\n' "$u"
      return 0
    fi
  done
  # 全挂则仍返回中科大，让 pip 自己报错
  printf '%s\n' "${_CN_PIP_CANDIDATES[0]}"
  return 1
}

_cn_net_try_autodl_turbo() {
  if [[ -f /etc/network_turbo ]]; then
    # shellcheck disable=SC1091
    source /etc/network_turbo
    if [[ -n "${http_proxy:-}${https_proxy:-}${HTTP_PROXY:-}${HTTPS_PROXY:-}" ]]; then
      _cn_net_say "已 source /etc/network_turbo（GitHub/HF 学术加速）"
      return 0
    fi
    _cn_net_say "/etc/network_turbo 存在但未设置 proxy（该地区可能不支持）"
  fi
  return 1
}

cn_net_off() {
  unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY all_proxy ALL_PROXY no_proxy NO_PROXY
  unset HF_ENDPOINT HF_HUB_DISABLE_XET
  unset PIP_INDEX_URL PIP_TRUSTED_HOST UV_INDEX_URL UV_DEFAULT_INDEX
  unset GIT_CONFIG_COUNT GIT_CONFIG_KEY_0 GIT_CONFIG_VALUE_0
  # 清掉本脚本加的 insteadOf（只清我们打过标记的）
  if git config --global --get-regexp '^url\..*\.insteadof$' >/dev/null 2>&1; then
    git config --global --unset-all "url.https://ghfast.top/https://github.com/.insteadOf" 2>/dev/null || true
  fi
  _cn_net_say "已关闭代理 / HF 镜像 / pip 索引环境变量"
}

cn_net_on() {
  local pip_idx pip_host

  _cn_net_try_autodl_turbo || true

  export HF_ENDPOINT="${HF_ENDPOINT:-$_CN_HF_MIRROR}"
  export HF_HUB_DISABLE_XET="${HF_HUB_DISABLE_XET:-1}"
  _cn_net_say "HF_ENDPOINT=$HF_ENDPOINT  HF_HUB_DISABLE_XET=$HF_HUB_DISABLE_XET"
  _cn_net_say "注意：上传 Hugging Face 前请 source cn_net.sh off（或 unset HF_ENDPOINT）"

  pip_idx="$(_cn_net_pick_pip)"
  pip_host="${pip_idx#https://}"
  pip_host="${pip_host#http://}"
  pip_host="${pip_host%%/*}"
  export PIP_INDEX_URL="$pip_idx"
  export PIP_TRUSTED_HOST="$pip_host"
  # uv 读这些
  export UV_DEFAULT_INDEX="$pip_idx"
  export UV_INDEX_URL="$pip_idx"
  _cn_net_say "PIP_INDEX_URL=$PIP_INDEX_URL"

  # git：不强制改 global insteadOf（镜像域名常挂）；提供函数 cn_git_clone
  _cn_net_say "GitHub: 用 cn_git_clone <github-url> [dir]；或先依赖 network_turbo"
  _cn_net_say "就绪。验证: cn_net_status"
}

cn_net_status() {
  _cn_net_say "http_proxy=${http_proxy:-<empty>}  https_proxy=${https_proxy:-<empty>}"
  _cn_net_say "HF_ENDPOINT=${HF_ENDPOINT:-<empty>}  HF_HUB_DISABLE_XET=${HF_HUB_DISABLE_XET:-<empty>}"
  _cn_net_say "PIP_INDEX_URL=${PIP_INDEX_URL:-<empty>}"
  _cn_net_say "UV_INDEX_URL=${UV_INDEX_URL:-<empty>}"
}

cn_net_probe() {
  local u
  _cn_net_say "探测 PyPI…"
  for u in "${_CN_PIP_CANDIDATES[@]}"; do
    if _cn_net_http_ok "$u"; then
      _cn_net_say "OK  $u"
    else
      _cn_net_say "FAIL $u"
    fi
  done
  _cn_net_say "探测 HF 镜像…"
  if _cn_net_http_ok "$_CN_HF_MIRROR"; then
    _cn_net_say "OK  $_CN_HF_MIRROR"
  else
    _cn_net_say "FAIL $_CN_HF_MIRROR"
  fi
  _cn_net_say "探测 github.com…"
  if _cn_net_http_ok "https://github.com"; then
    _cn_net_say "OK  https://github.com（直连或已有 proxy）"
  else
    _cn_net_say "FAIL https://github.com → 试 source /etc/network_turbo 或 cn_git_clone"
  fi
}

# clone GitHub：优先直连，再 turbo，再公共前缀镜像
cn_git_clone() {
  local url="$1"
  local dest="${2:-}"
  local path mirror_url

  if [[ -z "$url" ]]; then
    _cn_net_say "用法: cn_git_clone https://github.com/org/repo.git [dir]"
    return 2
  fi

  # 规范化成 https://github.com/org/repo.git
  if [[ "$url" =~ ^git@github\.com:(.+)$ ]]; then
    url="https://github.com/${BASH_REMATCH[1]}"
  fi
  if [[ "$url" =~ ^https?://github\.com/(.+)$ ]]; then
    path="${BASH_REMATCH[1]}"
  else
    _cn_net_say "只处理 github.com URL: $url"
    return 2
  fi

  _cn_net_say "尝试直连 clone…"
  if [[ -n "$dest" ]]; then
    git clone --depth 1 "$url" "$dest" && return 0
  else
    git clone --depth 1 "$url" && return 0
  fi

  _cn_net_say "直连失败，试 AutoDL turbo…"
  _cn_net_try_autodl_turbo || true
  if [[ -n "$dest" ]]; then
    git clone --depth 1 "$url" "$dest" && return 0
  else
    git clone --depth 1 "$url" && return 0
  fi

  local p
  for p in "${_CN_GH_PREFIXES[@]}"; do
    mirror_url="${p}${path}"
    _cn_net_say "试镜像: $mirror_url"
    if [[ -n "$dest" ]]; then
      git clone --depth 1 "$mirror_url" "$dest" && return 0
    else
      git clone --depth 1 "$mirror_url" && return 0
    fi
  done
  _cn_net_say "全部失败"
  return 1
}

cn_pip() {
  if [[ -z "${PIP_INDEX_URL:-}" ]]; then
    cn_net_on
  fi
  python -m pip install -i "$PIP_INDEX_URL" --trusted-host "${PIP_TRUSTED_HOST}" "$@"
}

# ---- dispatch ----
case "$_CN_NET_CMD" in
  on|enable|start|"")
    if ! _cn_net_is_sourced; then
      _cn_net_say "请用: source $0 on"
      exit 1
    fi
    cn_net_on
    ;;
  off|disable|stop)
    if ! _cn_net_is_sourced; then
      _cn_net_say "请用: source $0 off"
      exit 1
    fi
    cn_net_off
    ;;
  status)
    cn_net_status
    ;;
  probe)
    cn_net_probe
    ;;
  *)
    _cn_net_say "未知命令: $_CN_NET_CMD（on|off|status|probe）"
    if ! _cn_net_is_sourced; then
      exit 2
    fi
    ;;
esac
