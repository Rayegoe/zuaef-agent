#!/usr/bin/env bash
# ZUAEF-ASHARE-001 · 一键每日决策 (P5.5 观察模式) — 唯一日常动作。
# 交易时段内从仓库根执行:  bash tools/quant_daily.sh
# 自动完成: 实时扫描 → Agent 决策(产 Decision Brief) → 观察日志追加 → 重新渲染看板 → 复制到 docs/quant/
# 可选: 之后 git add docs/quant/dashboard.html && git commit && git push 发布快照。
set -euo pipefail
cd "$(dirname "$0")/.."
export ZUAEF_QUANT_PYTHON="${ZUAEF_QUANT_PYTHON:-$PWD/.venv-quant/bin/python}"
export ZUAEF_QUANT_REPO_ROOT="${ZUAEF_QUANT_REPO_ROOT:-$PWD}"
OBS_LOG="benchmarks/quant/gen1/OBSERVATION_LOG.md"
SCAN_TMP="$(mktemp /tmp/quant_scan_XXXXXX.json)"

echo "== [1/3] 实时扫描 =="
uv run --group quant python tools/quant_live_scan.py >"$SCAN_TMP"
python3 -c "import json;d=json.load(open('$SCAN_TMP'));print(f\"universe={d['universe_size']} 触发={len(d['triggers'])} scan={d['scan_ms']}ms 报价源={d['quote_source']}\")"

echo "== [2/3] Agent 决策 (产 Decision Brief + 观测延迟) =="
.venv/bin/zuaef-agent run --profile quant-decision --request-limit 10 --tool-calls-limit 12 \
	"Live decision check for the A-share active strategy. FIRST tool call: get_live_signals(). Then: (1) decide the verdict NO_TRADE or ENTER_CANDIDATE strictly from the returned trigger evidence (empty trigger list means NO_TRADE — do not force a candidate); (2) call record_decision_brief once with decision_id 'brief-live-<unixseconds>', the signal timestamp and strategy name from the scan output, your why/invalidation/expected_holding, and the raw trigger facts (or 'none'); (3) stop. No other tools, no file writes."

echo "== [3/3] 观察日志追加 + 渲染看板 =="
python3 - "$SCAN_TMP" "$OBS_LOG" <<'PY'
import json, sys
from datetime import datetime, timezone, timedelta
scan = json.load(open(sys.argv[1]))
obs_log = sys.argv[2]
TZ = timezone(timedelta(hours=8))
brief_dir = __import__("pathlib").Path("workspace/artifacts/quant/briefs")
briefs = sorted(brief_dir.glob("brief-live-*.json"), key=lambda p: p.stat().st_mtime) if brief_dir.is_dir() else []
latest = None
if briefs:
    for p in reversed(briefs):
        try:
            latest = json.load(open(p)); break
        except Exception:
            continue
action = (latest or {}).get("action", "ERROR")
brief_id = (latest or {}).get("decision_id", "none")
lat = (latest or {}).get("brief_latency_seconds")
lat_s = f"{lat:.0f}s" if isinstance(lat, (int, float)) else "—"
now = datetime.now(TZ)
today = now.strftime("%Y-%m-%d")
line = (f"| {today} | {now.strftime('%H:%M')} | {scan['universe_size']} | {len(scan['triggers'])} "
        f"| {action} | {scan['scan_ms']/1000:.1f}s | {lat_s} | auto;{brief_id}.json |")
lines = open(obs_log, encoding="utf-8").read().splitlines()
if any(l.startswith(f"| {today} ") for l in lines):
    print(f"OBSERVATION_LOG 今天已有记录, 跳过追加 (防重复): {line}")
else:
    with open(obs_log, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print("已追加:", line)
PY
python3 workspace/artifacts/quant/render_dashboard.py
cp workspace/artifacts/quant/dashboard.html docs/quant/dashboard.html
echo "完成 → docs/quant/dashboard.html  (如需发布: git add docs/quant/dashboard.html && git commit -m 'docs(quant): refresh dashboard' && git push)"
rm -f "$SCAN_TMP"
