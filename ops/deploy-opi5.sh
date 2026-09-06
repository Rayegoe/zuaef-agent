#!/usr/bin/env bash
# opi5 production deploy: fast-forward canonical main from GitHub, then restart
# the long-running user units so the editable (src/) install picks up new code.
#
# 用法（在 opi5 上，orangepi 用户）：
#   cd ~/zuaef-agent && bash ops/deploy-opi5.sh
# 开发机流程：本机改代码 -> commit + push origin main -> 在 opi5 跑本脚本。
#
# 说明：
#   - .venv 是 editable 安装（zuaef_agent 直接从 ~/zuaef-agent/src/ import），
#     pull 后只需重启，不需要重装。
#   - 定时器驱动的一次性服务（quant-bridge / quant-monitor）在下一个 tick
#     自动取新代码，无需手动重启；这里只重启三个常驻进程。
#   - .env 是 gitignored，pull 永不触碰；凭据/模型/开关变更需手动改 .env。
set -euo pipefail
cd "$HOME/zuaef-agent"

echo "== fast-forward pull =="
git pull --ff-only origin main

echo "== restart long-running units =="
systemctl --user restart \
  zuaef-gateway.service \
  zuaef-console.service \
  zuaef-quant-dashboard.service
# Feishu surface (v0.1): restart only when the unit is installed; older nodes
# without it must not fail the deploy.
if systemctl --user list-unit-files zuaef-feishu-gateway.service --no-legend 2>/dev/null | grep -q feishu; then
  systemctl --user restart zuaef-feishu-gateway.service
else
  echo "  (zuaef-feishu-gateway not installed, skipping)"
fi

sleep 6

echo "== status =="
for s in zuaef-gateway.service zuaef-console.service zuaef-quant-dashboard.service; do
  printf "  %-30s %s\n" "$s" "$(systemctl --user is-active "$s")"
done
if systemctl --user list-unit-files zuaef-feishu-gateway.service --no-legend 2>/dev/null | grep -q feishu; then
  printf "  %-30s %s\n" "zuaef-feishu-gateway.service" "$(systemctl --user is-active zuaef-feishu-gateway.service)"
fi
echo "== git head =="
git log --oneline -1