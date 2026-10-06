#!/usr/bin/env bash
#
# deploy.sh — 构建并推送（第二站 Real Pay Tools）
#
# 这是完全独立于第一站的项目：独立仓库、独立 Cloudflare Pages 项目、独立域名。
# 运行它不会影响第一站（Small Profit Tools）的任何文件或部署。
#
# 用法：
#   ./deploy.sh "本次改了什么"    # 构建 + 提交 + 推送
#   ./deploy.sh --preview         # 只本地构建，不推送
#
# 首次使用需要先关联远程仓库：
#   git remote add origin https://github.com/<你的账号>/<仓库名>.git

set -euo pipefail
cd "$(dirname "$0")"

PY="/Users/linluo2012/.workbuddy/binaries/python/versions/3.13.12/bin/python3"
[ -x "$PY" ] || PY="$(command -v python3)"

if [ -f .env ]; then
  DOMAIN="$(grep -E '^SITE_DOMAIN=' .env | cut -d= -f2- | tr -d ' "' || true)"
fi
if [ -z "${DOMAIN:-}" ] && [ -f domain.txt ]; then
  DOMAIN="$(tr -d ' \n' < domain.txt)"
fi
if [ -z "${DOMAIN:-}" ]; then
  echo "错误：找不到域名。在 domain.txt 里写入 career.linwt.top 即可。"
  exit 1
fi

echo "域名: $DOMAIN"
echo

echo "[1/4] 本地构建检查…"
"$PY" build.py "$DOMAIN"
echo

if [ "${1:-}" = "--preview" ]; then
  echo "预览构建完成，未推送。产物在 site/。"
  exit 0
fi

MSG="${1:-}"
if [ -z "$MSG" ]; then
  read -r -p "请输入本次改动说明: " MSG
  [ -n "$MSG" ] || { echo "已取消"; exit 0; }
fi

echo "[2/4] 检查改动…"
if [ -z "$(git status --porcelain)" ]; then
  echo "没有检测到任何改动，无需推送。"
  exit 0
fi

if ! git remote get-url origin >/dev/null 2>&1; then
  echo "尚未关联远程仓库。先执行一次："
  echo "  git remote add origin https://github.com/<你的账号>/<仓库名>.git"
  exit 1
fi

echo "[3/4] 提交改动…"
git add -A
git commit -q -m "$MSG"

echo "[4/4] 推送到 GitHub…"
BRANCH="$(git branch --show-current)"
push_ok=0
for attempt in 1 2 3; do
  if [ "$attempt" -gt 1 ]; then
    echo "      重试（第 $attempt 次）…"
    sleep 4
  fi
  if git push origin "$BRANCH" 2>&1; then
    push_ok=1
    break
  fi
done

if [ "$push_ok" -ne 1 ]; then
  echo
  echo "推送失败。代码已安全提交在本地，不会丢失。"
  echo "检查网络或 GitHub 权限后重试： git push origin $BRANCH"
  exit 1
fi

echo
echo "已推送。Cloudflare Pages 将在约 30 秒内自动部署。"
echo "线上地址：https://$DOMAIN/"
echo "想撤销：git revert HEAD --no-edit && git push origin $BRANCH"
