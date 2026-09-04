"""P0.3 PIT correctness audit for ZUAEF quant (spec v2.0 03_DATA_EXECUTION_TRUTH.md).

Deterministically audits the point-in-time semantics of the data actually
consumed by this repo, across the five aspects the spec names:

  1. index membership as-of (historical research universe vs live pool)
  2. financial report period
  3. announcement / effective date availability
  4. historical valuation as-of
  5. price adjustment semantics

Verdict (spec-mandated vocabulary): PIT_CLEAN / PIT_PARTIAL / PIT_CONTAMINATED.
Per-aspect statuses may be UNKNOWN; unknowns without contamination resolve to
PIT_PARTIAL (partial alignment) — never fabricated as clean. The verdict is a
recorded fact, not a tool failure: exit 0 whenever a verdict was recorded,
2 only when evidence is insufficient to audit at all.

The audit reads existing artifacts and configs only. It never mutates data.

    python3 tools/quant_pit_audit.py

Evidence: workspace/artifacts/quant/semantic/pit_audit_<UTC>.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GEN1 = REPO_ROOT / "benchmarks" / "quant" / "gen1"
CACHE = REPO_ROOT / "data" / "quant-cache"
SNAPSHOT_PATH = REPO_ROOT / "workspace" / "artifacts" / "quant" / "business" / "candidate_snapshot.json"
EVIDENCE_DIR = REPO_ROOT / "workspace" / "artifacts" / "quant" / "semantic"

QUANT_TOML = GEN1 / "quant.toml"
SUBSET_META = CACHE / "universe" / "csi500_subset.meta.json"

PIT_RANK = {"CONTAMINATED": 0, "PARTIAL": 1, "UNKNOWN": 2, "CLEAN": 3}
ANNOUNCEMENT_KEYS = {"announcement_date", "announce_date", "公告日期", "公告日"}


def worst_pit(statuses: list[str]) -> str:
    return min(statuses, key=lambda s: PIT_RANK.get(s, 2))


def membership_historical_aspect(subset_meta: dict | None, window: tuple[str, str]) -> dict:
    """Historical research universe vs its membership as-of date.

    A universe built from CURRENT index membership and evaluated over a
    window that ends before/around that basis date carries survivorship and
    lookahead contamination by construction (spec: PIT_CONTAMINATED).
    """
    if not subset_meta:
        return {"status": "UNKNOWN", "finding": "universe subset meta 缺失", "evidence": [str(SUBSET_META)]}
    limitation = str(subset_meta.get("pit_limitation", ""))
    window_start, window_end = window
    contaminated = "current membership" in limitation.lower()
    return {
        "status": "CONTAMINATED" if contaminated else "PARTIAL",
        "finding": (
            f"研究宇宙为当前成分股回溯应用至历史窗口 {window_start}..{window_end}"
            f"（meta 自述: {limitation or '未声明'}; basis: {subset_meta.get('basis', '?')}）"
            " — 幸存者/前视偏差，历史收益不可作为盈利证明"
            if contaminated
            else f"研究宇宙 membership as-of 未完全对齐窗口 {window_start}..{window_end}"
        ),
        "evidence": [str(SUBSET_META), str(QUANT_TOML)],
    }


def membership_live_aspect(snapshot: dict | None) -> dict:
    """Live candidate pool: current membership is the correct as-of for today."""
    membership = ((snapshot or {}).get("sources") or {}).get("membership") or {}
    entries = [
        {"index": label, **(info or {})}
        for label, info in membership.items()
        if isinstance(info, dict)
    ]
    dated = [e for e in entries if e.get("effective_date")]
    if not entries:
        return {"status": "UNKNOWN", "finding": "候选快照缺失或无 membership 来源", "evidence": [str(SNAPSHOT_PATH)]}
    if len(dated) < len(entries):
        return {
            "status": "PARTIAL",
            "finding": f"部分指数 membership 缺 effective_date ({[e['index'] for e in entries if not e.get('effective_date')]})",
            "evidence": [str(SNAPSHOT_PATH)],
        }
    return {
        "status": "CLEAN",
        "finding": "live 候选池即当前成分（effective_date 在案），对今日决策 membership as-of 正确",
        "evidence": [
            str(SNAPSHOT_PATH),
            *[f"{e['index']} effective {e['effective_date']}" for e in dated],
        ],
    }


def financial_announcement_aspect(metas: list[dict]) -> dict:
    """Report period vs announcement date (spec: 没有 announcement date 不能把 report period 当可用日)."""
    if not metas:
        return {"status": "UNKNOWN", "finding": "无 fundamentals 缓存可审", "evidence": [str(CACHE / "fundamentals")]}
    with_announcement = [m for m in metas if ANNOUNCEMENT_KEYS & set(m)]
    have_report = [m for m in metas if m.get("report_date")]
    if len(with_announcement) == len(metas):
        return {
            "status": "CLEAN",
            "finding": f"{len(with_announcement)}/{len(metas)} 条 fundamentals 缓存带公告日期",
            "evidence": [str(CACHE / "fundamentals")],
        }
    return {
        "status": "PARTIAL",
        "finding": (
            f"公告日期覆盖 {len(with_announcement)}/{len(metas)}；"
            f"{len(have_report)}/{len(metas)} 条带报告期。未覆盖记录不能用于历史 PIT 证明。"
            "今日打分安全（数据源仅返回已公告报告，不构成前视）；"
            "但任何历史研究若把报告期当作可用日即为污染 — 在引入公告日期前禁止该用法"
        ),
        "evidence": [str(CACHE / "fundamentals")],
    }


def valuation_asof_aspect(metas: list[dict]) -> dict:
    """Valuation series used only for current-value-vs-own-past percentile."""
    if not metas:
        return {"status": "UNKNOWN", "finding": "无 valuation3y 缓存可审", "evidence": [str(CACHE / "valuation3y")]}
    complete = [m for m in metas if m.get("series_last_date") and m.get("retrieved_at")]
    if len(complete) < len(metas):
        return {
            "status": "PARTIAL",
            "finding": f"{len(metas) - len(complete)} 条估值缓存缺 series_last_date/retrieved_at",
            "evidence": [str(CACHE / "valuation3y")],
        }
    return {
        "status": "CLEAN",
        "finding": "估值序列仅用于当前值对自身 3 年历史的后视分位（不含未来）；序列带 as-of 溯源",
        "evidence": [str(CACHE / "valuation3y")],
    }


def adjustment_semantics_aspect(
    daily_metas: list[dict],
    has_execution_rules: bool,
    symbols: list[str] | None = None,
    window: tuple[str, str] | None = None,
) -> dict:
    """qfq research face vs raw execution face, both recorded per cache."""
    if not daily_metas:
        return {"status": "UNKNOWN", "finding": "无 daily 缓存可审", "evidence": [str(CACHE / "daily")]}
    symbols = symbols or []
    if symbols:
        by_symbol: dict[str, dict[str, dict]] = {}
        for meta in daily_metas:
            by_symbol.setdefault(str(meta.get("symbol", "")), {})[str(meta.get("adjust"))] = meta
        missing: list[str] = []
        short: list[str] = []
        for symbol in symbols:
            faces = by_symbol.get(symbol, {})
            if not {"qfq", "raw"} <= set(faces):
                missing.append(symbol)
                continue
            if window:
                for adjust in ("qfq", "raw"):
                    span = faces[adjust].get("date_range") or []
                    if len(span) != 2 or str(span[0]) > window[0] or str(span[1]) < window[1]:
                        short.append(f"{symbol}:{adjust}")
        if missing or short or not has_execution_rules:
            return {
                "status": "PARTIAL",
                "finding": (
                    f"逐标的 raw/qfq 不完整: missing={len(missing)}, short_range={len(short)}, "
                    f"execution={has_execution_rules}"
                ),
                "missing_symbols": missing,
                "short_ranges": short,
                "evidence": [str(CACHE / "daily"), str(QUANT_TOML)],
            }
        return {
            "status": "CLEAN",
            "finding": f"研究宇宙 {len(symbols)} 只逐标的具备 raw/qfq 且覆盖实验窗口",
            "evidence": [str(CACHE / "daily"), str(QUANT_TOML)],
        }
    adjusts = {str(m.get("adjust")) for m in daily_metas}
    if {"qfq", "raw"} <= adjusts and has_execution_rules:
        return {
            "status": "CLEAN",
            "finding": "研究面 qfq / 执行面 raw 分离且逐缓存记录；qfq 比值型信号对再锚定不变",
            "evidence": [str(CACHE / "daily"), str(QUANT_TOML)],
        }
    return {
        "status": "PARTIAL",
        "finding": f"adjust 记录不全（observed: {sorted(adjusts)}）或执行规则缺失 (execution={has_execution_rules})",
        "evidence": [str(CACHE / "daily"), str(QUANT_TOML)],
    }


def _load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def audit(snapshot_path: Path = SNAPSHOT_PATH, cache: Path = CACHE, gen1: Path = GEN1) -> dict:
    subset_meta = _load_json(cache / "universe" / "csi500_subset.meta.json")
    quant_toml = _load_toml(gen1 / "quant.toml")
    research = (quant_toml or {}).get("research") or {}
    window = (str(research.get("research_start", "")), str(research.get("research_end", "")))
    has_execution_rules = bool((quant_toml or {}).get("execution"))

    fundamentals = [m for m in _sidecar_metas(cache / "fundamentals") if m]
    valuation = [m for m in _sidecar_metas(cache / "valuation3y") if m]
    daily = [m for m in _sidecar_metas(cache / "daily") if m]

    aspects = {
        "membership_historical": membership_historical_aspect(subset_meta, window),
        "membership_live": membership_live_aspect(_load_json(snapshot_path)),
        "financial_announcement": financial_announcement_aspect(fundamentals),
        "valuation_asof": valuation_asof_aspect(valuation),
        "adjustment_semantics": adjustment_semantics_aspect(
            daily,
            has_execution_rules,
            [str(s) for s in (subset_meta or {}).get("symbols", [])],
            window,
        ),
    }
    statuses = [a["status"] for a in aspects.values()]
    if all(s == "UNKNOWN" for s in statuses):
        return {"verdict": None, "aspects": aspects, "implication": "证据不足，无法审计"}
    if "CONTAMINATED" in statuses:
        verdict = "PIT_CONTAMINATED"
        implication = "历史回测宇宙带幸存者/前视污染：不得宣称 proven profitability；live 决策不受该宇宙偏差影响"
    elif "PARTIAL" in statuses or "UNKNOWN" in statuses:
        verdict = "PIT_PARTIAL"
        implication = "PIT 对齐部分成立；未决方面在解决前不得作为 green"
    else:
        verdict = "PIT_CLEAN"
        implication = "五个方面均与 as-of 语义对齐"
    return {"verdict": verdict, "aspects": aspects, "implication": implication}


def _sidecar_metas(dir_path: Path) -> list[dict]:
    return [m for m in (_load_json(p) for p in sorted(dir_path.glob("*.meta.json"))) if m]


def _load_toml(path: Path) -> dict | None:
    import tomllib

    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=EVIDENCE_DIR)
    args = parser.parse_args()

    result = audit()
    if result["verdict"] is None:
        print(json.dumps({"verdict": None, "reason": "insufficient evidence"}, ensure_ascii=False))
        return 2
    evidence = {
        "spec": "zuaef-quant-final-spec-v2.0 P0.3",
        "verdict": result["verdict"],
        "implication": result["implication"],
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "aspects": result["aspects"],
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = args.out_dir / f"pit_audit_{stamp}.json"
    out.write_text(json.dumps(evidence, ensure_ascii=False, indent=1), encoding="utf-8")
    print(
        json.dumps(
            {
                "verdict": result["verdict"],
                "aspects": {k: v["status"] for k, v in result["aspects"].items()},
                "implication": result["implication"],
                "evidence": str(out),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
