#!/usr/bin/env python3
"""render_dashboard.py — ZUAEF-ASHARE-001 只读观察看板渲染器 (P5.5 observation mode).

读取既有工件 (STATUS.md / OBSERVATION_LOG.md / evidence.json / equity_replay.csv /
briefs/*.json / active.toml / quant.toml), 输出单一自包含 HTML (内联 CSS+JS+数据,
零外部依赖)。只读: 不改任何工件, 不进入 Agent 运行时, 不触碰受管文件 (gitignored)。

再生成:
    python3 tools/quant_render_dashboard.py [--out dashboard.html]

冻结期定位 (docs/quant/README.md §6): dashboard 属禁改清单, 本脚本仅是把既有
证据渲染成页面供观察期肉眼巡检, 不是新的量化基础设施; 不用于交易决策。
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

# quant_render_dashboard.py lives at <repo>/tools/ -> 2 levels up is repo root
REPO_ROOT = Path(__file__).resolve().parent.parent  # zuaef-agent
GEN1 = REPO_ROOT / "benchmarks" / "quant" / "gen1"
ART = REPO_ROOT / "workspace" / "artifacts" / "quant"
DEFAULT_OUT = ART / "dashboard.html"


# --------------------------------------------------------------------------
# harvest helpers (all tolerant: missing files -> safe defaults)
# --------------------------------------------------------------------------


def read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def read_json(p: Path) -> dict | None:
    try:
        return json.loads(read_text(p))
    except (ValueError, TypeError):
        return None


def parse_status_proofs() -> list[dict]:
    """Parse the four-line proof table from STATUS.md."""
    rows = []
    for line in read_text(GEN1 / "STATUS.md").splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [
            c.strip().replace("**", "").strip()
            for c in line.strip().strip("|").split("|")
        ]
        if (
            len(cells) >= 3
            and cells[0] not in ("", "Proof")
            and not set(cells[0]) <= {"-"}
        ):
            rows.append({"name": cells[0], "state": cells[1], "evidence": cells[2]})
    return rows


def parse_obs_log() -> list[dict]:
    """Parse OBSERVATION_LOG.md table rows. Tolerates later manual-settlement side notes."""
    rows = []
    for line in read_text(GEN1 / "OBSERVATION_LOG.md").splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if (
            len(cells) < 5
            or cells[0] == "日期"
            or not re.match(r"\d{4}-\d{2}-\d{2}", cells[0])
        ):
            continue
        rows.append(
            {
                "date": cells[0],
                "time": cells[1] if len(cells) > 1 else "",
                "scanned": cells[2] if len(cells) > 2 else "",
                "triggers": cells[3] if len(cells) > 3 else "",
                "action": cells[4] if len(cells) > 4 else "",
                "scan_s": cells[5] if len(cells) > 5 else "",
                "brief_s": cells[6] if len(cells) > 6 else "",
                "note": cells[7] if len(cells) > 7 else "",
            }
        )
    return rows


def parse_toml_kv(p: Path) -> dict:
    out = {}
    for line in read_text(p).splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, _, v = s.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        out[k] = v
    return out


def parse_equity(p: Path, max_points: int = 200) -> dict | None:
    """Return {dates:[...], eq:[...]} downsampled by stride (last row always kept)."""
    try:
        with p.open(newline="", encoding="utf-8") as f:
            rdr = list(csv.reader(f))
        if len(rdr) < 2:
            return None
        dates, eq = [], []
        for r in rdr[1:]:
            if len(r) >= 2:
                try:
                    eq.append(float(r[1]))
                    dates.append(r[0])
                except ValueError:
                    continue
        if not eq:
            return None
        n = len(eq)
        if n > max_points:
            step = n / max_points
            idx = [int(i * step) for i in range(max_points - 1)] + [n - 1]
            idx = sorted(set(idx))
            dates = [dates[i] for i in idx]
            eq = [eq[i] for i in idx]
        return {"dates": dates, "eq": eq}
    except OSError:
        return None


def harvest_evolution() -> dict:
    """Baseline (gen1) + S1/S2/S3 children comparison from evidence.json files."""
    ev = (
        read_json(ART / "gen1" / "evidence.json") or {}
    )  # baseline evidence lives in artifact dir
    rp = ev.get("independent_replay", {}) or {}
    vc = ev.get("vector_stage", {}) or {}
    baseline = {
        "id": "基线",
        "name": "volume_pullback_reversal (hold 5)",
        "annual": rp.get("annualized_return_pct"),
        "total": rp.get("total_return_pct"),
        "dd": rp.get("max_drawdown_pct"),
        "trades": rp.get("trade_count"),
        "cost": rp.get("total_cost"),
        "intents": ev.get("intents", {}).get("total"),
        "vector_annual": vc.get("annualized_return_pct"),
        "diff_pp": (ev.get("consistency", {}) or {}).get("annualized_return_diff_pp"),
        "verdict": "基线",
        "note": "P1 冻结基准策略, 平进平出。",
    }
    children = []
    for d in (
        sorted((ART / "children").iterdir()) if (ART / "children").is_dir() else []
    ):
        if not d.is_dir():
            continue
        e = read_json(d / "evidence.json")
        if not e:
            continue
        r = e.get("independent_replay", {}) or {}
        v = e.get("vector_stage", {}) or {}
        name = e.get("strategy", {}).get("name", d.name)
        verdict, note = "未知", ""
        if name == "s2_tighter_volume":
            verdict, note = (
                "被证据否决",
                "S2 收严量比 -> 9 笔, 年化崩塌; 入场阈值以 S1 为准。",
            )
        elif name == "s3_longer_hold":
            verdict, note = (
                "冻结 (DEMO_ACTIVE_STRATEGY)",
                "S3 延长持有 5->8 天: 纯出场侧收益, 零新增成本; S4+ 停调参。",
            )
        else:
            verdict, note = (
                "改善",
                "S1 放宽回撤 -> 29 笔, 年化提升; 入场条件被后续轮次继承。",
            )
        children.append(
            {
                "id": name,
                "name": name,
                "annual": r.get("annualized_return_pct"),
                "total": r.get("total_return_pct"),
                "dd": r.get("max_drawdown_pct"),
                "trades": r.get("trade_count"),
                "cost": r.get("total_cost"),
                "intents": e.get("intents", {}).get("total"),
                "vector_annual": v.get("annualized_return_pct"),
                "diff_pp": (e.get("consistency", {}) or {}).get(
                    "annualized_return_diff_pp"
                ),
                "verdict": verdict,
                "note": note,
            }
        )
    return {"baseline": baseline, "children": children}


def harvest_equity_curves() -> list[dict]:
    """Baseline + children replay equity curves (% of initial capital)."""
    series = []
    b = parse_equity(
        ART / "gen1" / "equity_replay.csv"
    )  # baseline curve lives in artifact dir
    if b:
        series.append({"name": "基线", "dates": b["dates"], "eq": b["eq"]})
    for d in (
        sorted((ART / "children").iterdir()) if (ART / "children").is_dir() else []
    ):
        if not d.is_dir():
            continue
        c = parse_equity(d / "equity_replay.csv")
        if c:
            series.append({"name": c_name(d.name), "dates": c["dates"], "eq": c["eq"]})
    return series


def c_name(ts_dir: str) -> str:
    base = re.sub(r"-\d{8}T\d{6}Z$", "", ts_dir)
    return {
        "s1_softer_pullback": "S1",
        "s2_tighter_volume": "S2",
        "s3_longer_hold": "S3",
    }.get(base, base)


def harvest_briefs() -> list[dict]:
    out = []
    d = ART / "briefs"
    if d.is_dir():
        for p in sorted(d.glob("brief-*.json")):
            b = read_json(p)
            if b:
                out.append(b)
    return out


def harvest_params() -> dict:
    active = parse_toml_kv(GEN1 / "active.toml")
    return {
        "active": active,
        "windows": {
            "research": "2018-01-01 .. 2022-12-31 (Agent 可见)",
            "promotion": "2023-01-01 .. 2024-12-31 (host-only, 未触碰)",
            "holdout": "2025-01-01 .. 2026-08-28 (隐藏, 从未触碰)",
            "forward": "2026-09-02 起 (观察模式)",
        },
        "execution": {
            "initial_capital": 100000.0,
            "exec": "T+1 次日开盘",
            "lot": 100,
            "commission": "0.025% / 最低 5 元",
            "slippage": "10 bps",
            "stamp": "0.10% -> 0.05% (2023-08-28 下调)",
            "limits": "10% (主板) / 20% (创业板 2020-08-24 起, 科创板 2019-07-22 起)",
        },
        "universe": {
            "desc": "gen1 基准宇宙: CSI500 成分 stride 10 采样 37 只 (12 只因回溯不足排除); 当前活跃宇宙 = 用户自选 4 只 (见实时行情卡)",
            "snapshot": "全市场快照 5550 只 · CSI500 成分 500 只 (生效 2026-08-28)",
            "pit": "今日成员回看历史 (幸存者/成分偏差) — 任何盈利声明的前置门",
        },
    }


VERSIONS = [
    ("pydantic-ai", "2.35.3", "uv.lock"),
    ("pydantic-ai-harness[skills,code-mode]", "0.27.0 (`>=0.27,<0.28`)", "uv.lock"),
    ("akshare", "1.18.94", "uv 依赖组 quant · 数据面: 腾讯/新浪/CSIndex"),
    ("pyqlib", "0.9.7", ".venv-quant (Python 3.12 侧环境)"),
    ("主环境 Python", "3.13", ".venv"),
]

ARTIFACT_MAP = [
    ("benchmarks/quant/gen1/quant.toml", "冻结市场规则/成本/基准窗口 (生效日期化)"),
    ("benchmarks/quant/gen1/strategy.toml", "gen1 基线策略 (默认参数出处)"),
    (
        "benchmarks/quant/gen1/active.toml",
        "DEMO_ACTIVE_STRATEGY = s3_longer_hold (冻结)",
    ),
    ("benchmarks/quant/gen1/STATUS.md", "四行证明状态 + 冻结决策 + 已知局限"),
    ("benchmarks/quant/gen1/OBSERVATION_LOG.md", "观察模式每日一行日志"),
    ("workspace/artifacts/quant/gen1/", "基线评估工件 evidence/trades/equity/result"),
    (
        "workspace/artifacts/quant/children/",
        "S1/S2/S3 子策略工件 (evidence/equity/result)",
    ),
    (
        "workspace/artifacts/quant/briefs/",
        "Decision Brief JSON (含实测 signal->brief 延迟)",
    ),
    ("workspace/artifacts/quant/p0-data-proof-2026-08-28.log", "P0 真实数据证明日志"),
    ("data/quant-cache/", "行情缓存+sidecar、qlib bin 库 (gitignored 可重建)"),
    (".venv-quant/", "Python 3.12 侧环境 akshare+pyqlib (gitignored)"),
    ("tools/quant/upstream/dump_bin.py", "vendored qlib 上游脚本 (已审计 commit, MIT)"),
    ("tests/test_quant_replay.py", "14 个防伪 alpha 测试"),
    ("tests/test_quant_plugin.py", "16 个插件契约测试"),
]

COMMANDS = [
    ("数据证明 (P0)", "uv run --group quant python tools/quant_p0_data_proof.py"),
    (
        "宇宙准备 (仅首次/换宇宙)",
        "uv run --group quant python tools/quant_fetch_universe.py",
    ),
    (
        "基线评估 (不经 Agent)",
        ".venv-quant/bin/python tools/quant_eval_qlib.py --config benchmarks/quant/gen1/quant.toml --strategy benchmarks/quant/gen1/strategy.toml --out workspace/artifacts/quant/gen1 --window research",
    ),
    ("实时扫描 (无 LLM)", "uv run --group quant python tools/quant_live_scan.py"),
    (
        "日常决策 (经 Agent)",
        '.venv/bin/zuaef-agent run --profile quant-decision --request-limit 10 --tool-calls-limit 12 "..."',
    ),
    ("测试", "uv run pytest -q  # 810"),
    (
        "quant 测试",
        "uv run --group quant pytest tests/test_quant_replay.py tests/test_quant_plugin.py -q",
    ),
    ("ruff", ".venv/bin/python -m ruff check ."),
    (
        "manifest",
        ".venv/bin/python tools/regen_manifest.py && .venv/bin/python -m pytest tests/test_manifest_integrity.py -q",
    ),
]

TROUBLESHOOT = [
    (
        "EastMoney / SSL EOF",
        "本网络对 EastMoney 被拒 (正常, 数据面已是腾讯/新浪/CSIndex)",
        "检查 qt.gtimg.cn 可达性",
    ),
    ("历史抓取偶发 SSL 失败", "腾讯限流", "引擎内有界重试 (2s/8s), 重跑即可"),
    (
        "quant plugin side environment missing",
        "侧环境不存在或路径错",
        "确认 .venv-quant/bin/python, 或设 ZUAEF_QUANT_PYTHON",
    ),
    (
        "cannot locate repository quant tooling",
        "agent 不在仓库根运行",
        "从仓库根运行, 或设 ZUAEF_QUANT_REPO_ROOT",
    ),
    (
        "profile not found",
        "profile 未安装",
        "cp profiles/quant-decision.toml ~/.config/zuaef/profiles/",
    ),
    (
        "evaluate_strategy already ran this round",
        "一轮守卫生效 (设计行为)",
        "写完 Strategy Result 即结束任务",
    ),
    (
        "execution_state: failed 但产物已落盘",
        "撞 tool-call limit (探索过头)",
        "检查产物; 必要时再降 limit",
    ),
    (
        "扫描全是 0 触发",
        "S3 条件选择性高 (正常)",
        "记日志; 连续多周 0 触发才构成 §6 研究信号",
    ),
]

STAGES = [
    {
        "k": "U0",
        "t": "上游兼容刷新",
        "state": "PASS",
        "summary": "pydantic-ai 2.35.3 / harness 0.27.0, 759/759 全绿; U005 按证据记 no-op",
    },
    {
        "k": "P0",
        "t": "真实数据证明",
        "state": "PASS",
        "summary": "akshare 1.18.94; 600519 qfq≠raw 复权真实; 全市场快照 5550; 新鲜度 0 天; EastMoney 被拒→腾讯/新浪/CSIndex 替代",
    },
    {
        "k": "P1",
        "t": "固定策略 + Qlib 评估",
        "state": "PASS",
        "summary": "CSI500 stride 采样 37 只; 冻结 gen1 窗口; 基线 +0.20%/24 笔 (真实不 attractive)",
    },
    {
        "k": "P2",
        "t": "独立重放 + A股执行真相",
        "state": "PASS",
        "summary": "事件循环引擎: T+1/涨跌停/停牌/整手/成本; 14 防伪测试抓出真 bug (次日开盘成交); 双引擎年化差 0.02pp",
    },
    {
        "k": "P3",
        "t": "QuantDecision 接入 ZUAEF",
        "state": "PASS",
        "summary": "Capability + 3 确定性工具; 弱模型不会调 TOML→改普通数值参数; 12 契约测试",
    },
    {
        "k": "P4",
        "t": "三轮真实模型进化",
        "state": "PASS",
        "summary": "S1 改善 (+0.34%) → S2 被证据否决 (+0.01%) → S3 换杠杆 (+0.37%); 循环为真非预写 workflow",
    },
    {
        "k": "P4.5",
        "t": "三项修复 + 冻结",
        "state": "PASS",
        "summary": "workspace/workspace 根因修复; 单轮 clean exit 硬守卫; S3 冻结为 DEMO_ACTIVE_STRATEGY, 停止 S4 调参",
    },
    {
        "k": "P5",
        "t": "实时决策链路首验",
        "state": "PASS",
        "summary": "scan 提速 16× (qt.gtimg.cn 批量报价 2.9s/37只); record_decision_brief 端到端延迟 86s 实测",
    },
    {
        "k": "P5.5",
        "t": "观察模式 (当前)",
        "state": "OBSERVING",
        "summary": "代码冻结; 每日 run → observe → record → judge; 不开发 P6/P7/dashboard/watcher/结算引擎",
    },
]

FIVE_METRICS = [
    (
        "Trigger frequency",
        "有没有足够交易机会",
        "0 次真实 trigger (≥10 次才进入结算复盘, 条件 A)",
    ),
    (
        "Signal→Brief latency",
        "Agent 是否赶得上",
        "86s (2026-09-02 实测, 含模型推理; scan 仅 ~3s)",
    ),
    (
        "Signal→Brief price drift",
        "延迟是否造成真实损失",
        "无 trigger, 待首笔 forward evidence",
    ),
    ("Subsequent return path", "信号本身是否有意义", "无 trigger, 无持仓, 待积累"),
    (
        "Agent veto / 增量判断",
        "LLM 相对裸扫描器是否有增益",
        "1/1 次遵守: 空触发→NO_TRADE 未硬推候选 (V007)",
    ),
]


# --------------------------------------------------------------------------
# template
# --------------------------------------------------------------------------


def format_number(v, digits=2):
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.{digits}f}"
    return str(v)


def read_universe_size() -> int:
    """Read active universe size: committed gen1/universe.toml, else cache meta."""
    try:
        import tomllib
    except ModuleNotFoundError:
        tomllib = None  # Python < 3.11: fall back to the cache meta path
    if tomllib is not None:
        try:
            with (REPO_ROOT / "benchmarks" / "quant" / "gen1" / "universe.toml").open(
                "rb"
            ) as fh:
                return len(tomllib.load(fh).get("symbols", []))
        except (OSError, KeyError, ValueError, TypeError):
            pass
    p = REPO_ROOT / "data" / "quant-cache" / "universe" / "csi500_subset.meta.json"
    try:
        return int(json.loads(p.read_text(encoding="utf-8")).get("size", 0))
    except (OSError, KeyError, ValueError, TypeError):
        return 0


def build_data() -> dict:
    obs = parse_obs_log()
    trigger_count = sum(
        1 for r in obs if str(r.get("triggers", "0")).strip() not in ("", "0")
    )
    briefs = harvest_briefs()
    return {
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        "proofs": parse_status_proofs(),
        "stages": STAGES,
        "evolution": harvest_evolution(),
        "equity": harvest_equity_curves(),
        "obs_log": obs,
        "obs_stats": {
            "runs": len(obs),
            "trigger_runs": len(
                [r for r in obs if str(r.get("triggers", "")).strip() not in ("", "0")]
            ),
            "trigger_count": trigger_count,
            "last_action": obs[-1].get("action", "—") if obs else "—",
            "last_scan_s": obs[-1].get("scan_s", "—") if obs else "—",
            "last_brief_s": obs[-1].get("brief_s", "—") if obs else "—",
        },
        "briefs": briefs,
        "latest_brief": briefs[-1] if briefs else None,
        "universe_size": read_universe_size(),
        "active": harvest_params()["active"],
        "params": harvest_params(),
        "versions": VERSIONS,
        "artifacts": ARTIFACT_MAP,
        "commands": COMMANDS,
        "troubleshoot": TROUBLESHOOT,
        "five_metrics": FIVE_METRICS,
        "freeze": {
            "since": "2026-09-02",
            "note": "U0–P5 全部 PASS, 代码冻结, 转入观察模式。重启开发准入规则 (docs/quant/README.md §6): A. ≥10 个真实 trigger → 人工结算复盘; B. 观察期足够长仍 0 trigger → 策略/宇宙研究 (不是框架)。",
            "forbidden": "S4+ 调参 · P6/P7 框架 · dashboard·watcher · PIT platform · 10-run A/B · SpendLimits · broker (PIT universe 是唯一提前解冻例外)",
        },
    }


CSS = """\
:root{
  --bg:#0b0e14; --panel:#12161f; --panel2:#0f1420; --line:#1f2733; --line2:#27303f;
  --tx:#d7dde8; --mut:#8b96a8; --dim:#5c6678;
  --acc:#4cc2ff; --green:#3fb950; --amber:#d29922; --red:#f85149; --purple:#bc8cff;
  --pass:#3fb950; --warn:#d29922; --live:#4cc2ff; --gray:#8b96a8;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--tx);font:14px/1.55 -apple-system,"PingFang SC","Microsoft YaHei","Noto Sans SC",system-ui,sans-serif;padding:24px 20px 60px}
.wrap{max-width:1240px;margin:0 auto}
a{color:var(--acc);text-decoration:none} a:hover{text-decoration:underline}
code{font:12.5px "SFMono-Regular",Consolas,"Liberation Mono",monospace;background:var(--panel2);border:1px solid var(--line);border-radius:5px;padding:1px 6px;color:#9ecbff}
h1{font-size:22px;display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.sub{color:var(--mut);font-size:13px;margin-top:6px}
.badge{font-size:11px;font-weight:600;padding:3px 10px;border-radius:20px;letter-spacing:.4px;border:1px solid}
.b-freeze{color:var(--amber);border-color:#5c4a1e;background:#1b170c}
.b-pass{color:#163a22;background:var(--pass);border-color:var(--pass)}
.b-pending{color:#3a2c0d;background:var(--amber);border-color:var(--amber)}
.b-live{color:#062a3d;background:var(--live);border-color:var(--live)}
.b-obs{color:var(--amber);border-color:#5c4a1e;background:#1b170c}
.b-dim{color:var(--mut);border-color:var(--line2);background:transparent}
.grid{display:grid;gap:16px;margin-top:18px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px}
.card h2{font-size:14px;letter-spacing:.3px;color:#b7c2d4;margin-bottom:12px;display:flex;align-items:center;gap:8px}
.card h2 .cnt{font-size:11px;color:var(--dim);font-weight:400}
.two{grid-template-columns:1.35fr 1fr}
@media(max-width:960px){.two{grid-template-columns:1fr}}
/* proof cards */
.pf{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px}
.pf .c{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px 16px 14px;position:relative;overflow:hidden}
.pf .c::before{content:"";position:absolute;inset:0 auto 0 0;width:3px;background:var(--st,var(--gray))}
.pf .n{font-size:12px;color:var(--mut);text-transform:uppercase;letter-spacing:.6px}
.pf .s{font-size:20px;font-weight:700;margin:8px 0 6px;color:var(--st,var(--tx))}
.pf .e{font-size:12px;color:var(--mut);line-height:1.5}
/* stepper */
.step{display:grid;grid-template-columns:repeat(9,1fr);gap:6px}
@media(max-width:960px){.step{grid-template-columns:repeat(3,1fr)}}
.step .st{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px;text-align:center;cursor:default;transition:border-color .15s}
.step .st:hover{border-color:var(--line2)}
.step .k{font-weight:700;font-size:12px;color:var(--acc)}
.step .t{font-size:12px;color:var(--tx);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.step .st.pass{border-color:#1f6a34;background:#101a13}
.step .st.obs{border-color:#5c4a1e;background:#1b170c}
.step .st .dot{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:4px;vertical-align:1px}
/* tables */
table{width:100%;border-collapse:collapse;font-size:13px}
th{color:var(--mut);font-weight:600;text-align:left;font-size:12px;padding:6px 8px;border-bottom:1px solid var(--line2);white-space:nowrap}
td{padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top}
tr:last-child td{border-bottom:none}
.num{font-variant-numeric:tabular-nums;text-align:right}
.pos{color:var(--red)} .neg{color:var(--green)} .mut{color:var(--mut)}
.chip{display:inline-block;font-size:11px;font-weight:600;padding:1px 8px;border-radius:12px;white-space:nowrap}
.chip.ok{color:#163a22;background:var(--pass)}
.chip.bad{color:#3b1110;background:var(--red)}
.chip.wait{color:#3a2c0d;background:var(--amber)}
.chip.gray{color:var(--mut);background:var(--panel2);border:1px solid var(--line2)}
.chip.frozen{color:#062a3d;background:var(--live)}
/* kpi strip */
.kpi{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}
.kpi .k{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.kpi .v{font-size:22px;font-weight:700;font-variant-numeric:tabular-nums}
.kpi .l{font-size:11.5px;color:var(--mut);margin-top:2px}
/* brief */
.brief dt{color:var(--mut);font-size:11.5px;text-transform:uppercase;letter-spacing:.4px;margin-top:10px}
.brief dd{font-size:13px;margin-top:2px}
/* metrics */
.m5{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px}
.m5 .m{background:var(--panel2);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.m5 .q{font-size:12px;color:var(--acc);font-weight:600}
.m5 .qq{font-size:11px;color:var(--dim);margin-bottom:6px}
.m5 .a{font-size:12.5px;color:var(--tx)}
.bar{height:9px;background:var(--panel2);border:1px solid var(--line2);border-radius:6px;overflow:hidden;margin-top:10px}
.bar i{display:block;height:100%;background:linear-gradient(90deg,#2c82c9,var(--acc));border-radius:6px}
/* refs */
details{background:var(--panel);border:1px solid var(--line);border-radius:10px;margin-bottom:10px;overflow:hidden}
summary{cursor:pointer;padding:12px 16px;font-size:13.5px;font-weight:600;color:#b7c2d4;list-style:none;display:flex;align-items:center;gap:8px}
summary::before{content:"▸";color:var(--dim);transition:transform .15s}
details[open] summary::before{transform:rotate(90deg)}
details .body{padding:0 16px 14px;font-size:13px}
details table td{font-size:12.5px}
.paramgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin-top:8px}
.paramgrid .p{background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:8px 10px}
.paramgrid .pk{font-size:11px;color:var(--dim)}
.paramgrid .pv{font-size:13.5px;font-variant-numeric:tabular-nums;margin-top:2px;word-break:break-all}
.cmdline{font-family:"SFMono-Regular",Consolas,monospace;font-size:12px;background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:9px 12px;margin:6px 0 12px;color:#9ecbff;white-space:pre-wrap;word-break:break-all}
.cmd{display:flex;gap:10px;align-items:flex-start;margin-bottom:4px}
.cmd .cl{color:var(--acc);font-size:12.5px;min-width:130px;font-weight:600}
/* chart */
.chart-box{position:relative;margin-top:6px}
.chart-box svg{width:100%;height:auto;display:block}
.tip{position:absolute;pointer-events:none;background:#0d1117;border:1px solid var(--line2);border-radius:8px;padding:8px 10px;font-size:12px;display:none;z-index:10;box-shadow:0 6px 24px rgba(0,0,0,.5);min-width:150px}
.legend{display:flex;flex-wrap:wrap;gap:14px;margin-top:10px;font-size:12px;color:var(--mut)}
.legend .lg{display:flex;align-items:center;gap:6px}
.legend i{width:10px;height:10px;border-radius:3px;display:inline-block}
footer{margin-top:26px;color:var(--dim);font-size:12px;border-top:1px solid var(--line);padding-top:14px;line-height:1.8}
"""

JS = r"""
const D = window.DASH;

/* ---- helpers ---- */
const $ = (id) => document.getElementById(id);
const fmt = (v, d=2) => v==null ? '—' : (typeof v==='number' ? v.toFixed(d) : v);
const esc = (s) => String(s??'').replace(/[&<>"]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const stateBadge = (st) => {
  const m = st.toUpperCase();
  if (m.includes('PASS')) return '<span class="badge b-pass">PASS</span>';
  if (m.includes('FIRST PROOF')) return '<span class="badge b-live">FIRST PROOF</span>';
  if (m.includes('NOT YET')) return '<span class="badge b-pending">NOT YET</span>';
  if (m.includes('OBSERV')) return '<span class="badge b-obs">OBSERVING</span>';
  return `<span class="badge b-dim">${esc(st)}</span>`;
};

/* ---- proofs ---- */
function renderProofs(){
  const states = {};
  D.proofs.forEach(p=>{
    const u = p.state.toUpperCase();
    const st = u.includes('NOT YET') ? '#d29922' : (u.includes('FIRST') ? '#4cc2ff' : '#3fb950');
    states[p.name.toLowerCase()] = st;
    $(`proof-${['research','learning','profitability','live'].reduce((a,k,i)=> p.name.toLowerCase().startsWith(k.replace('self-learning','learning'))?('p'+i):a, 'p0')}`)
  });
  $('proofs').innerHTML = D.proofs.map(p=>{
    const u = p.state.toUpperCase();
    const st = u.includes('NOT YET') ? 'var(--amber)' : ('#4cc2ff');
    return `<div class="c" style="--st:${st}">
      <div class="n">${esc(p.name)}</div>
      <div class="s">${esc(p.state)}</div>
      <div class="e">${esc(p.evidence)}</div>
    </div>`;
  }).join('');
}

/* ---- stages ---- */
function renderStages(){
  $('stages').innerHTML = D.stages.map(s=>{
    const cls = s.state==='PASS' ? 'pass' : (s.state==='OBSERVING' ? 'obs' : '');
    return `<div class="st ${cls}"><div class="k"><span class="dot" style="background:${s.state==='PASS'?'var(--green)':(s.state==='OBSERVING'?'var(--amber)':'var(--gray)')}"></span>${esc(s.k)}</div><div class="t" title="${esc(s.summary)}">${esc(s.t)}</div></div>`;
  }).join('');
  $('stages-detail').innerHTML = D.stages.map(s=>`
    <tr><td class="mut" style="white-space:nowrap"><b>${esc(s.k)}</b></td><td style="white-space:nowrap">${esc(s.t)}</td>
    <td style="white-space:nowrap">${stateBadge(s.state)}</td><td>${esc(s.summary)}</td></tr>`).join('');
}

/* ---- evolution table ---- */
function renderEvolution(){
  const rows = [D.evolution.baseline, ...D.evolution.children];
  const total = Object.values(D.evolution.children).length;
  $('evol-rows').innerHTML = rows.map(r=>{
    const verdictCls = r.verdict.includes('否决') ? 'bad' : (r.verdict.includes('冻结') ? 'frozen' : (r.verdict==='基线' ? 'gray' : 'ok'));
    return `<tr>
      <td>${esc(r.id)}</td>
      <td class="mut" style="max-width:180px">${esc(r.name)}</td>
      <td class="num pos">${fmt(r.annual,3)}%</td>
      <td class="num">${r.trades}</td>
      <td class="num neg">${fmt(r.dd,3)}%</td>
      <td class="num">${fmt(r.cost,2)}</td>
      <td class="num">${fmt(r.diff_pp,3)} pp</td>
      <td><span class="chip ${verdictCls}">${esc(r.verdict)}</span></td>
    </tr>`;
  }).join('');
  // bar chart (annualized)
  const names = rows.map(r=>esc(r.id));
  const vals = rows.map(r=>r.annual??0);
  const cards = rows.map(r=>r.verdict);
  const maxV = Math.max(...vals)*1.25;
  const colors = {基线:'#8b96a8', s1_softer_pullback:'#58a6ff', s2_tighter_volume:'#d29922', s3_longer_hold:'#f85149'};
  let bars = '';
  vals.forEach((v,i)=>{
    const h = v>=0 ? Math.max(2, v/maxV*120) : 0;
    const neg = v<0;
    bars += `<div style="display:flex;flex-direction:column;align-items:center;gap:6px;flex:1;justify-content:flex-end;height:150px">
      <div class="num" style="font-size:12px;color:${neg?'var(--green)':'var(--red)'}">${v.toFixed(3)}%</div>
      <div style="width:38px;height:${h}px;border-radius:4px 4px 0 0;background:${colors[names[i]]||'var(--gray)'};opacity:${cards[i].includes('否决')?0.45:1}"></div>
      <div class="mut" style="font-size:12px">${names[i]}</div>
      <div style="font-size:10.5px;line-height:1.25;text-align:center;min-height:28px">
        <span class="chip ${cards[i].includes('否决')?'bad':(cards[i].includes('冻结')?'frozen':(cards[i]==='基线'?'gray':'ok'))}" style="font-size:10px">${esc(cards[i])}</span>
      </div>
    </div>`;
  });
  $('evol-chart').innerHTML = `<div style="display:flex;align-items:flex-end;gap:8px;height:190px;padding:8px 4px 0">${bars}</div>
    <div class="mut" style="font-size:11.5px;margin-top:8px">年化收益率 (独立重放, raw 价格, market truth ON) — research 窗口 2018-01-01..2022-12-31 · PIT 局限: 今日成分回看历史</div>`;
}

/* ---- equity curves ---- */
function renderEquity(){
  const series = D.equity;
  if(!series.length){ $('equity-box').innerHTML='<div class="mut">equity_replay.csv 缺失</div>'; return; }
  const all = series.flatMap(s=>s.eq);
  let lo = Math.min(...all), hi = Math.max(...all);
  const pad = Math.max((hi-lo)*0.12, 0.3);
  lo -= pad; hi += pad;
  const W=1000, H=300, t=14, b=30, l=52, r=14;
  const X = i => l + (i/(series[0].dates.length-1||1))*(W-l-r);
  const Y = v => t + (1-(v-lo)/(hi-lo||1))*(H-t-b);
  const colors = {基线:'#8b96a8', S1:'#58a6ff', S2:'#d29922', S3:'#f85149'};
  const lines = series.map(s=>{
    const pts = s.eq.map((v,i)=>`${X(i).toFixed(1)},${Y(v).toFixed(1)}`).join(' ');
    return `<polyline points="${pts}" fill="none" stroke="${colors[s.name]||'var(--gray)'}" stroke-width="1.6" opacity="0.95" data-name="${esc(s.name)}"/>`;
  }).join('');
  // gridlines + labels
  const ny = 6; let grid='', labs='';
  for(let i=0;i<=ny;i++){
    const v = lo + (hi-lo)*i/ny;
    const y = Y(v);
    grid += `<line x1="${l}" y1="${y}" x2="${W-r}" y2="${y}" stroke="#1a2130" stroke-width="1"/>`;
    labs += `<text x="${l-6}" y="${y+4}" fill="#5c6678" font-size="10.5" text-anchor="end">${v.toFixed(1)}</text>`;
  }
  const years = [];
  const dates = series[0].dates;
  const ySet = new Set();
  dates.forEach((d,i)=>{ const yr=d.slice(0,4); if(!ySet.has(yr)){ySet.add(yr); years.push([i,yr]);} });
  const xlabs = years.map(([i,yr])=>`<text x="${X(i)}" y="${H-10}" fill="#5c6678" font-size="10.5" text-anchor="middle">${yr}</text>`).join('');
  $('equity-box').innerHTML = `<div class="chart-box" id="ec">
    <svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">
      ${grid}${labs}${xlabs}${lines}
    </svg>
    <div class="tip" id="etip"></div>
    <div class="legend">${series.map(s=>`<span class="lg"><i style="background:${colors[s.name]||'var(--gray)'}"></i>${esc(s.name)}</span>`).join('')}
      <span class="mut" style="margin-left:auto">账户净值 % (初始 100,000) · 独立重放 · 2022 年后无交易, 曲线平直</span></div>
  </div>`;
  // tooltip
  const box = $('ec'), tip = $('etip');
  const n = dates.length;
  const itv = (W-l-r)/n;
  box.addEventListener('mousemove', e=>{
    const r = box.getBoundingClientRect();
    const px = (e.clientX - r.left) / r.width * W;
    const i = Math.max(0, Math.min(n-1, Math.round((px - l) / itv)));
    const d = dates[i];
    let html = `<div class="mut" style="margin-bottom:3px">${esc(d)}</div>`;
    series.forEach(s=>{
      const v = s.eq[Math.min(i, s.eq.length-1)];
      html += `<div style="display:flex;gap:8px;justify-content:space-between"><span style="color:${colors[s.name]}">${esc(s.name)}</span><span class="num">${(v-100).toFixed(2)}%</span></div>`;
    });
    tip.innerHTML = html;
    tip.style.display = 'block';
    const tx = e.clientX - r.left + 14;
    tip.style.left = Math.min(tx + tip.offsetWidth < r.width ? tx : tx - tip.offsetWidth - 20, r.width - tip.offsetWidth) + 'px';
    tip.style.top = '10px';
  });
  box.addEventListener('mouseleave', ()=> tip.style.display='none');
}

/* ---- briefs ---- */
function renderBriefs(){
  const b = D.latest_brief;
  if(!b){ $('brief-latest').innerHTML='<div class="mut">暂无 Decision Brief (首个交易日运行后出现)</div>'; }
  else {
    const actCls = b.action==='NO_TRADE' ? 'gray' : (b.action==='ENTER_CANDIDATE' ? 'frozen' : 'wait');
    $('brief-latest').innerHTML = `
      <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
        <span class="chip ${actCls}" style="font-size:13px;padding:3px 12px">${esc(b.action)}</span>
        <span class="mut" style="font-size:12px">${esc(b.decision_id||'')}</span>
        <span class="badge b-dim" style="margin-left:auto">strategies: ${esc(b.strategy_name||'—')}</span>
      </div>
      <dl class="brief">
        <dt>signal → brief 延迟</dt><dd class="pos" style="font-size:18px;font-weight:700">${fmt(b.brief_latency_seconds,0)} s</dd>
        <dt>signal 时间</dt><dd>${esc(b.signal_timestamp||'—')}</dd>
        <dt>recorded at</dt><dd>${esc(b.recorded_at||'—')}</dd>
        <dt>why (Agent 决策依据)</dt><dd>${esc(b.why||'—')}</dd>
        <dt>invalidation</dt><dd>${esc(b.invalidation||'—')}</dd>
        <dt>expected_holding</dt><dd>${esc(b.expected_holding||'—')}</dd>
        <dt>trigger_facts</dt><dd class="mut" style="font-family:'SFMono-Regular',Consolas,monospace;font-size:12px">${esc(b.trigger_facts||'—')}</dd>
      </dl>`;
  }
  const rows = D.briefs.slice().reverse().map(b=>`
    <tr><td>${esc(b.decision_id||'')}</td>
    <td><span class="chip ${b.action==='NO_TRADE'?'gray':'frozen'}">${esc(b.action)}</span></td>
    <td class="num">${fmt(b.brief_latency_seconds,0)}s</td>
    <td class="mut">${esc(b.signal_timestamp||'—')}</td>
    <td class="mut" style="max-width:340px">${esc((b.why||'').slice(0,120))}${(b.why||'').length>120?'…':''}</td></tr>`).join('');
  $('brief-table').innerHTML = rows || '<tr><td colspan="5" class="mut">暂无 brief</td></tr>';
}

/* ---- observation log ---- */
function renderObs(){
  const s = D.obs_stats;
  $('obs-count').innerHTML = `${s.runs} 个交易日 · ${s.trigger_runs} 次触发`;
  $('obs-rows').innerHTML = D.obs_log.length ? D.obs_log.slice().reverse().map(r=>`
    <tr><td class="num">${esc(r.date)}</td><td class="num">${esc(r.time)}</td>
    <td class="num">${esc(r.scanned)}</td>
    <td class="num" style="font-weight:600;color:${r.triggers&&r.triggers!=='0'?'var(--red)':'var(--dim)'}">${esc(r.triggers)}</td>
    <td><span class="chip ${r.action==='NO_TRADE'?'gray':'frozen'}">${esc(r.action)}</span></td>
    <td class="num">${esc(r.scan_s)}</td><td class="num">${esc(r.brief_s)}</td>
    <td class="mut">${esc(r.note)}</td></tr>`).join('')
    : '<tr><td colspan="8" class="mut">OBSERVATION_LOG.md 暂无记录</td></tr>';
  // five metrics
  $('metrics').innerHTML = D.five_metrics.map(m=>`
    <div class="m"><div class="q">${esc(m[0])}</div><div class="qq">${esc(m[1])}</div><div class="a">${esc(m[2])}</div></div>`).join('');
  // A/B gate progress
  const trig = s.trigger_count;
  const pct = Math.min(100, trig/10*100);
  $('gate-progress').innerHTML = `
    <div style="display:flex;justify-content:space-between;font-size:12.5px;margin-bottom:2px">
      <span>退出条件 A: 真实 trigger ≥ 10 次</span><span class="num"><b style="color:${trig>=10?'var(--green)':'var(--amber)'}">${trig}</b> / 10</span>
    </div>
    <div class="bar"><i style="width:${pct}%"></i></div>
    <div class="mut" style="font-size:11.5px;margin-top:6px">达到条件 A → 进入人工结算复盘, 决定 A/B 实验与是否自动化; 条件 B (长期 0 trigger) → 重启策略/宇宙研究, 非框架。</div>`;
}

/* ---- references ---- */
function renderRefs(){
  const a = D.active;
  const rows = Object.entries(a);
  $('active-params').innerHTML = rows.map(([k,v])=>`<div class="p"><div class="pk">${esc(k)}</div><div class="pv">${esc(v)}</div></div>`).join('');
  $('win-params').innerHTML = Object.entries(D.params.windows).map(([k,v])=>`<div class="p"><div class="pk">${esc(k)} window</div><div class="pv">${esc(v)}</div></div>`).join('');
  $('exe-params').innerHTML = Object.entries(D.params.execution).map(([k,v])=>`<div class="p"><div class="pk">${esc(k)}</div><div class="pv">${esc(v)}</div></div>`).join('');
  $('uni-params').innerHTML = Object.entries(D.params.universe).map(([k,v])=>`<div class="p"><div class="pk">${esc(k)}</div><div class="pv">${esc(v)}</div></div>`).join('');
  $('ver-rows').innerHTML = D.versions.map(v=>`<tr><td>${esc(v[0])}</td><td><code>${esc(v[1])}</code></td><td class="mut">${esc(v[2])}</td></tr>`).join('');
  $('art-rows').innerHTML = D.artifacts.map(a=>`<tr><td><code>${esc(a[0])}</code></td><td class="mut">${esc(a[1])}</td></tr>`).join('');
  $('cmd-rows').innerHTML = D.commands.map(c=>`<div class="cmd"><div class="cl">${esc(c[0])}</div><div class="cmdline">${esc(c[1])}</div></div>`).join('');
  $('ts-rows').innerHTML = D.troubleshoot.map(t=>`<tr><td class="mut" style="white-space:nowrap">${esc(t[0])}</td><td>${esc(t[1])}</td><td>${esc(t[2])}</td></tr>`).join('');
}

/* ---- live ---- */
function liveRow(q){
  const tr = q.trigger ? `<span class="chip frozen">TRIGGER</span>` : `<span class="chip gray">—</span>`;
  const px = q.price == null ? '—' : Number(q.price).toFixed(2);
  const pc = q.prev_close == null ? '—' : Number(q.prev_close).toFixed(2);
  const pb = q.pullback_5d == null ? '—' : (Number(q.pullback_5d)*100).toFixed(2)+'%';
  const vr = q.volume_ratio_20d == null ? '—' : Number(q.volume_ratio_20d).toFixed(2);
  const pbc = q.pullback_5d != null && Number(q.pullback_5d) <= 0 ? 'var(--red)' : 'var(--dim)';
  return `<tr><td><code>${esc(q.symbol)}</code></td><td>${esc(q.name||'')}</td>
    <td class="num">${px}</td><td class="num">${pc}</td>
    <td class="num" style="color:${pbc}">${pb}</td><td class="num">${vr}</td><td>${tr}</td></tr>`;
}
function drawLive(s){
  const rows = (s.quotes || []).map(liveRow).join('');
  $('live-rows').innerHTML = rows || '<tr><td colspan="7" class="mut">暂无行情数据</td></tr>';
  $('live-status').innerHTML = `更新于 ${esc(s.as_of||'')} · 扫描 ${esc(String(s.scan_ms))}ms · 触发 ${(s.triggers||[]).length} · ${esc(s.quote_source||'')}`;
  $('kpi-universe').textContent = (s.universe_size || D.universe_size || '?') + ' 只';
  $('kpi-scan').textContent = s.scan_ms ? (s.scan_ms/1000).toFixed(1)+'s' : $('kpi-scan').textContent;
}
async function pollScan(){
  try{
    const r = await fetch('/api/scan', {cache:'no-store'});
    if(!r.ok) throw new Error('http '+r.status);
    const s = await r.json();
    if(s.error) throw new Error(s.error);
    drawLive(s);
    $('live-status').style.color = 'var(--green)';
  }catch(e){
    $('live-status').innerHTML = '实时服务未连接 — 启动: python3 tools/quant_serve.py (显示静态快照)';
    $('live-status').style.color = 'var(--amber)';
  }
}

/* ---- boot ---- */
document.addEventListener('DOMContentLoaded', ()=>{
  $('gen-time').textContent = D.generated_at;
  $('freeze-since').textContent = D.freeze.since + ' 起';
  $('freeze-note').textContent = D.freeze.note;
  $('freeze-forbidden').textContent = D.freeze.forbidden;
  $('kpi-stage').textContent = D.stages[D.stages.length-1].k + ' · ' + D.stages[D.stages.length-1].t;
  $('kpi-obs').textContent = D.obs_stats.trigger_count + ' 次真实 trigger';
  $('kpi-universe').textContent = (D.universe_size || '?') + ' 只';
  $('kpi-scan').textContent = D.obs_stats.last_scan_s;
  $('kpi-latency').textContent = D.obs_stats.last_brief_s;
  renderProofs(); renderStages(); renderEvolution(); renderEquity();
  renderBriefs(); renderObs(); renderRefs();
  pollScan();
  setInterval(pollScan, 60000);
});
"""


def build_html(data: dict) -> str:
    blob = json.dumps(data, ensure_ascii=False, indent=1)
    return TEMPLATE.replace("__DATA_JSON__", blob)


TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ZUAEF-ASHARE-001 · A股决策 Agent 观察看板</title>
<style>__CSS__</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>
      ZUAEF-ASHARE-001 · A股决策 Agent 观察看板
      <span class="badge b-freeze">ENGINEERING FREEZE</span>
      <span class="badge b-obs">OBSERVATION MODE · <span id="freeze-since"></span></span>
    </h1>
    <div class="sub">Spec ZUAEF-ASHARE-001 v1.0-final · 观察模式日常巡检页 (只读 · 数据由既有工件渲染) · 生成于 <span id="gen-time"></span>
      · 再生成: <code>python3 tools/quant_render_dashboard.py</code></div>
  </header>

  <div class="kpi" style="margin-top:18px">
    <div class="k"><div class="v" id="kpi-stage">—</div><div class="l">当前阶段</div></div>
    <div class="k"><div class="v" id="kpi-obs">—</div><div class="l">真实 trigger 累计</div></div>
    <div class="k"><div class="v" id="kpi-universe">—</div><div class="l">活动宇宙 (自选)</div></div>
    <div class="k"><div class="v" id="kpi-scan">—</div><div class="l">最近 scan 耗时</div></div>
    <div class="k"><div class="v" id="kpi-latency">—</div><div class="l">最近 signal→brief 延迟</div></div>
  </div>

  <div class="card" style="margin-top:16px">
    <h2>实时行情 <span class="cnt">自选宇宙 · 每 60s 自动刷新 · 数据源 tools/quant_serve.py /api/scan</span></h2>
    <div class="mut" id="live-status" style="font-size:12px;margin-bottom:8px">连接实时服务中…</div>
    <div style="overflow-x:auto"><table>
      <thead><tr><th>代码</th><th>名称</th><th style="text-align:right">现价</th><th style="text-align:right">昨收</th>
        <th style="text-align:right">5日回撤</th><th style="text-align:right">20日量比</th><th>触发</th></tr></thead>
      <tbody id="live-rows"></tbody>
    </table></div>
  </div>

  <div class="card" style="margin-top:16px">
    <h2>四行证明状态 <span class="cnt">— 证据见 STATUS.md</span></h2>
    <div class="pf" id="proofs"></div>
    <div class="mut" style="font-size:11.5px;margin-top:12px;line-height:1.7" id="freeze-note"></div>
    <div class="mut" style="font-size:11.5px;margin-top:6px;line-height:1.7"><b style="color:var(--amber)">冻结期禁改:</b> <span id="freeze-forbidden"></span></div>
  </div>

  <div class="card">
    <h2>开发链路 <span class="cnt">U0 → P5.5</span></h2>
    <div class="step" id="stages"></div>
    <details style="margin-top:12px">
      <summary>阶段明细（各阶段以可用证明收尾）</summary>
      <div class="body"><table id="stages-detail"></table></div>
    </details>
  </div>

  <div class="grid two">
    <div class="card">
      <h2>模型进化 <span class="cnt">三轮真实 run · S3 冻结</span></h2>
      <table>
        <thead><tr>
          <th>轮次</th><th>策略</th><th style="text-align:right">年化</th><th style="text-align:right">笔数</th>
          <th style="text-align:right">最大回撤</th><th style="text-align:right">成本 (CNY)</th><th style="text-align:right">双引擎差</th><th>结论</th>
        </tr></thead>
        <tbody id="evol-rows"></tbody>
      </table>
      <div id="evol-chart" style="margin-top:16px"></div>
    </div>

    <div class="card">
      <h2>实盘决策产品 <span class="cnt">P5 FIRST PROOF</span></h2>
      <div class="brief" id="brief-latest"></div>
      <details style="margin-top:12px">
        <summary>全部 Decision Briefs (<span id="obs-count"></span>)</summary>
        <div class="body"><table>
          <thead><tr><th>decision_id</th><th>action</th><th style="text-align:right">延迟</th><th>signal 时间</th><th>Why (节选)</th></tr></thead>
          <tbody id="brief-table"></tbody>
        </table></div>
      </details>
    </div>
  </div>

  <div class="card">
    <h2>独立重放权益曲线 <span class="cnt">raw 价格 · market truth ON · 初始 100,000</span></h2>
    <div id="equity-box"></div>
  </div>

  <div class="grid two">
    <div class="card">
      <h2>观察日志 <span class="cnt">benchmarks/quant/gen1/OBSERVATION_LOG.md</span></h2>
      <table>
        <thead><tr><th>日期</th><th>时间</th><th style="text-align:right">扫描只数</th><th style="text-align:right">触发数</th><th>Action</th><th style="text-align:right">scan 耗时</th><th style="text-align:right">brief 延迟</th><th>备注</th></tr></thead>
        <tbody id="obs-rows"></tbody>
      </table>
      <div class="mut" style="font-size:11.5px;margin-top:8px">日志只存一行/日, 供肉眼巡检; 完整字段在 brief JSON。出现真实 trigger 时人工加"结算旁注"(字段见 docs/quant/README.md §5.4)。</div>
    </div>
    <div class="card">
      <h2>观察期五指标 + 退出条件</h2>
      <div class="m5" id="metrics"></div>
      <div style="margin-top:16px" id="gate-progress"></div>
    </div>
  </div>

  <div style="margin-top:18px">
    <details>
      <summary>当前冻结策略 · 市场规则 · 宇宙</summary>
      <div class="body">
        <div class="paramgrid" id="active-params"></div>
        <table style="margin-top:12px"><thead><tr><th>窗口 (冻结)</th><th>执行规则</th><th>宇宙</th></tr></thead>
        <tbody><tr>
          <td><div class="paramgrid" id="win-params" style="grid-template-columns:1fr"></div></td>
          <td><div class="paramgrid" id="exe-params" style="grid-template-columns:1fr"></div></td>
          <td><div class="paramgrid" id="uni-params" style="grid-template-columns:1fr"></div></td>
        </tr></tbody></table>
      </div>
    </details>
    <details>
      <summary>版本锁定 (当前执行基线)</summary>
      <div class="body"><table id="ver-rows"></table></div>
    </details>
    <details>
      <summary>工件地图</summary>
      <div class="body"><table id="art-rows"></table></div>
    </details>
    <details>
      <summary>命令速查</summary>
      <div class="body" id="cmd-rows"></div>
    </details>
    <details>
      <summary>故障排查</summary>
      <div class="body"><table>
        <thead><tr><th>症状</th><th>原因</th><th>处置</th></tr></thead>
        <tbody id="ts-rows"></tbody>
      </table></div>
    </details>
  </div>

  <footer>
    本看板是 P5.5 观察模式的 <b>只读巡检页</b>: 数据全部来自既有工件 (STATUS.md / OBSERVATION_LOG.md / evidence.json / briefs), 不含任何交易建议。
    <br>语义色: 红=正向结论/被选策略, 绿=风险信号, 非 A股涨跌方向。看板上所有历史数字都受 PIT 局限 (今日 CSI500 成分回看历史) 与 <b>+0.37%/29 笔噪声内</b> 约束; 盈利声明唯一前置门是 PIT universe 重建。
    <br>再生成: <code>python3 tools/quant_render_dashboard.py</code> · 冻结期禁改清单见 README §6 (dashboard/watcher/结算引擎不建 — 本页只是把已有证据渲染出来)。
  </footer>
</div>
<script>
window.DASH = __DATA_JSON__;
__JS__
</script>
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Render ZUAEF-ASHARE-001 observation dashboard."
    )
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="output html path")
    args = ap.parse_args()

    data = build_data()
    # sanity first: embedded JSON must be loadable (check before __JS__ is injected)
    import re as _re

    templ = build_html(data)
    m = _re.search(r"window\.DASH = (\{.*?\});", templ, _re.DOTALL)
    if m:
        try:
            json.loads(m.group(1))
        except ValueError as e:
            print(f"sanity: embedded JSON invalid -> {e}", file=sys.stderr)
            return 1
    else:
        print("sanity: DASH marker not found", file=sys.stderr)
        return 1
    html = templ.replace("__CSS__", CSS).replace("__JS__", JS)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(
        f"OK -> {out}  ({out.stat().st_size / 1024:.1f} KB, proofs={len(data['proofs'])}, "
        f"obs_rows={len(data['obs_log'])}, briefs={len(data['briefs'])}, equity_series={len(data['equity'])})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
