#!/usr/bin/env bash
# ZUAEF-ASHARE-001 · 一键每日决策 (观察模式) — 唯一日常动作。
# 交易时段内从仓库根执行:  bash tools/quant_daily.sh
# 流程: 校验活跃候选宇宙(非空) → 实时扫描(存业务页快照) → Agent 决策(产 Decision Brief)
#       → 观察日志追加 → 渲染业务页 + 工程/审计页。
# 候选池刷新是独立的盘后/手动动作 (uv run --group quant python tools/quant_build_candidates.py),
# 本脚本不重建候选基本面数据。
# 可选: 之后 git add docs/quant/ && git commit && git push 发布页面快照。
set -euo pipefail
cd "$(dirname "$0")/.."
export ZUAEF_QUANT_PYTHON="${ZUAEF_QUANT_PYTHON:-$PWD/.venv-quant/bin/python}"
export ZUAEF_QUANT_REPO_ROOT="${ZUAEF_QUANT_REPO_ROOT:-$PWD}"
OBS_LOG="benchmarks/quant/gen1/OBSERVATION_LOG.md"
ACTIVE_SYMBOLS="data/quant-cache/candidates/active_symbols.json"
SCAN_TMP="$(mktemp /tmp/quant_scan_XXXXXX.json)"

echo "== [0/3] 活跃候选宇宙校验 (fail closed) =="
if [ ! -s "$ACTIVE_SYMBOLS" ]; then
	echo "FATAL: 活跃候选宇宙缺失/为空 ($ACTIVE_SYMBOLS)。" >&2
	echo "       空宇宙不能当作合法 NO_TRADE 市场结论。先运行候选刷新:" >&2
	echo "       uv run --group quant python tools/quant_build_candidates.py" >&2
	exit 2
fi
python3 - "$ACTIVE_SYMBOLS" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
symbols = d.get("symbols") or []
if not symbols:
    sys.exit("FATAL: active_symbols.json has no symbols — rerun tools/quant_build_candidates.py (fail closed)")
print(f"active candidate universe: {len(symbols)} 只 (as_of {d.get('as_of','?')})")
PY

echo "== [1/3] 实时扫描 (活跃候选宇宙) =="
uv run --group quant python tools/quant_live_scan.py >"$SCAN_TMP"
mkdir -p workspace/artifacts/quant/business
cp "$SCAN_TMP" workspace/artifacts/quant/business/last_scan.json
python3 -c "import json;d=json.load(open('$SCAN_TMP'));print(f\"universe={d['universe_size']}({d['universe']}) 触发={len(d['triggers'])} scan={d['scan_ms']}ms 报价源={d['quote_source']}\")"

echo "== [2/3] Agent 决策 (产 Decision Brief + 观测延迟) =="
.venv/bin/zuaef-agent run --profile quant-decision --request-limit 10 --tool-calls-limit 12 \
	"Live decision check for the A-share active strategy. FIRST tool call: get_live_signals(). Then: (1) decide the verdict NO_TRADE or ENTER_CANDIDATE strictly from the returned trigger evidence (empty trigger list means NO_TRADE — do not force a candidate); (2) call record_decision_brief once with decision_id 'brief-live-<unixseconds>', the signal timestamp and strategy name from the scan output, your why/invalidation/expected_holding, and the raw trigger facts (or 'none'); (3) stop. No other tools, no file writes."

echo "== [3/3] 观察日志追加 + 渲染业务页/工程页 =="
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
python3 tools/quant_render_business_dashboard.py
python3 tools/quant_render_dashboard.py
cp workspace/artifacts/quant/dashboard.html docs/quant/dashboard.html
echo "完成 → docs/quant/business.html (业务页) + docs/quant/dashboard.html (工程/审计页)"
echo "(如需发布: git add docs/quant/ && git commit -m 'docs(quant): refresh dashboards' && git push)"
rm -f "$SCAN_TMP"
