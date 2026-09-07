"""Research artifacts, market intelligence and skill wiring
(quant research service v0.2: T006 / T008 / T011 / T012).

Pins the business-artifact contract: bounded packets with read-back
verification, UNVERIFIED customer evidence that can never look like
strategy state, a bounded structured intel adapter (not a crawler), and
plugin skill delivery through the existing Skills primitive.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "tools"))
sys.path.insert(0, str(Path(__file__).parents[1] / "plugins" / "zuaef-quant"))

import quant_market_intel as intel
from zuaef_quant import research as research_store


def _root(tmp_path: Path) -> Path:
    return tmp_path / "workspace" / "artifacts" / "quant" / "research"


# ---------------------------------------------------------------------------
# research packets (T011)
# ---------------------------------------------------------------------------


class TestResearchPackets:
    def test_save_and_read_back(self, tmp_path):
        out = research_store.save_packet(
            _root(tmp_path), "oc_group_a", "600550",
            research_status="PARTIAL",
            thesis="结构性看多，但受输电投资节奏约束。",
            supporting_facts=["quote 10.97 from current-run symbol context"],
            counter_evidence=["web: 中报毛利率下滑 (url, observed 2026-09-07)"],
            scenarios=["Bull: 条件…；依据…；失效…", "Base: …", "Bear: …"],
            unknowns=["行业投资节奏"],
            source_references=["akshare.stock_news_em", "https://example.com/a"],
        )
        assert out["saved"] is True
        assert out["file"].startswith("artifacts/quant/research/oc_group_a/600550/")
        packet = research_store.latest_packet(_root(tmp_path), "oc_group_a", "600550")
        assert packet["research_status"] == "PARTIAL"
        assert len(packet["scenarios"]) == 3
        assert packet["note"].startswith("prior hypothesis")

    def test_invalid_status_and_symbol_rejected(self, tmp_path):
        with pytest.raises(research_store.ResearchError):
            research_store.save_packet(
                _root(tmp_path), "oc_group_a", "600550",
                research_status="SURE_THING", thesis="x",
            )
        with pytest.raises(ValueError):  # shared 6-digit symbol rule
            research_store.save_packet(
                _root(tmp_path), "oc_group_a", "ABC",
                research_status="COMPLETE", thesis="x",
            )

    def test_bounded_fields_are_capped_not_trusted(self, tmp_path):
        out = research_store.save_packet(
            _root(tmp_path), "oc_group_a", "600550",
            research_status="COMPLETE",
            thesis="长" * 5000,
            supporting_facts=[f"fact {i}" for i in range(40)],
            unknowns=[],
        )
        assert out["saved"] is True
        packet = research_store.latest_packet(_root(tmp_path), "oc_group_a", "600550")
        assert len(packet["thesis"]) <= research_store.THESIS_MAX_CHARS
        assert len(packet["supporting_facts"]) == research_store.PACKET_MAX_ITEMS

    def test_latest_packet_absent_is_none_and_scopes_are_isolated(self, tmp_path):
        assert research_store.latest_packet(_root(tmp_path), "oc_group_a", "600550") is None
        research_store.save_packet(
            _root(tmp_path), "oc_group_a", "600550",
            research_status="COMPLETE", thesis="a",
        )
        assert research_store.latest_packet(_root(tmp_path), "oc_group_b", "600550") is None

    def test_two_packets_latest_wins(self, tmp_path):
        research_store.save_packet(_root(tmp_path), "s", "600550", research_status="COMPLETE", thesis="v1")
        research_store.save_packet(_root(tmp_path), "s", "600550", research_status="PARTIAL", thesis="v2")
        packet = research_store.latest_packet(_root(tmp_path), "s", "600550")
        assert packet["thesis"] == "v2"


# ---------------------------------------------------------------------------
# customer evidence (T012)
# ---------------------------------------------------------------------------


class TestCustomerEvidence:
    def test_recorded_as_unverified_with_provenance(self, tmp_path):
        out = research_store.record_customer_evidence(
            _root(tmp_path), "oc_group_a", "600550",
            claim="供应商说订单很满", source_hint="客户微信", run_id="run-1",
        )
        assert out["recorded"] is True
        assert out["verification"] == "UNVERIFIED"
        rows = research_store.read_customer_evidence(_root(tmp_path), "oc_group_a", "600550")
        assert rows[0]["kind"] == "CUSTOMER_REPORTED"
        assert rows[0]["verification"] == "UNVERIFIED"
        assert rows[0]["recorded_by_run"] == "run-1"

    def test_empty_claim_rejected(self, tmp_path):
        with pytest.raises(research_store.ResearchError):
            research_store.record_customer_evidence(
                _root(tmp_path), "oc_group_a", "600550", claim="  ",
            )

    def test_tail_is_bounded(self, tmp_path):
        for i in range(14):
            research_store.record_customer_evidence(
                _root(tmp_path), "s", "600550", claim=f"claim {i}",
            )
        rows = research_store.read_customer_evidence(_root(tmp_path), "s", "600550")
        assert len(rows) == research_store.EVIDENCE_TAIL_LIMIT
        assert rows[-1]["claim"] == "claim 13"


# ---------------------------------------------------------------------------
# market intelligence adapter (T008)
# ---------------------------------------------------------------------------


class TestMarketIntelAdapter:
    def _feed(self):
        import pandas as pd

        return pd.DataFrame(
            {
                "关键词": ["600550"] * 3,
                "新闻标题": [f"标题 {i}" for i in range(3)],
                "新闻内容": [f"内容 {i}" for i in range(3)],
                "发布时间": ["2026-09-07 10:00:00"] * 3,
                "文章来源": ["界面新闻"] * 3,
                "新闻链接": [f"https://example.com/{i}" for i in range(3)],
            }
        )

    def test_bounded_items_with_source_and_time(self, tmp_path, monkeypatch):
        monkeypatch.setitem(
            sys.modules, "akshare", SimpleNamespace(stock_news_em=lambda symbol: self._feed())
        )
        out = intel.collect("600550", limit=2)
        assert out["count"] == 2
        assert out["items"][0]["source"] == "界面新闻"
        assert out["items"][0]["published_at"] == "2026-09-07 10:00:00"
        assert out["items"][0]["url"].startswith("https://")
        assert "not exhaustive" in out["limitations"][0]

    def test_failure_is_structured_evidence(self, tmp_path, monkeypatch):
        def failing(symbol):
            raise RuntimeError("feed down")

        monkeypatch.setitem(sys.modules, "akshare", SimpleNamespace(stock_news_em=failing))
        out = intel.collect("600550")
        assert "error" in out and "feed down" in out["error"]

    def test_main_rejects_bad_symbol(self, capsys):
        sys.argv = ["quant_market_intel.py", "--symbol", "ABC"]
        assert intel.main() == 2
        assert "6-digit" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# toolset wiring + plugin skill delivery (T006/T008/T011/T012)
# ---------------------------------------------------------------------------


def _deps(tmp_path: Path, bindings: dict) -> SimpleNamespace:
    from zuaef_agent.models import CoreDeps

    return SimpleNamespace(deps=CoreDeps(
        workspace_root=tmp_path / "workspace",
        run_id="run-research-1",
        bindings=bindings,
    ))


def _toolset(tmp_path: Path):
    from zuaef_quant.toolset import make_toolset

    return make_toolset(quant_python=tmp_path / "quant-python", workspace_root=tmp_path / "workspace")


class TestResearchTools:
    def test_save_and_get_packet_roundtrip(self, tmp_path):
        toolset = _toolset(tmp_path)
        ctx = _deps(tmp_path, {"analysis_scope": "oc_group_a"})
        saved = json.loads(toolset.tools["save_research_packet"].function(
            ctx, "600550", "PARTIAL", thesis="t", scenarios=["Bull: …"],
        ))
        assert saved["saved"] is True
        got = json.loads(toolset.tools["get_research_packet"].function(ctx, "600550"))
        assert got["packet"]["thesis"] == "t"
        assert got["packet"]["research_status"] == "PARTIAL"

    def test_absent_packet_is_reported_not_fabricated(self, tmp_path):
        toolset = _toolset(tmp_path)
        ctx = _deps(tmp_path, {"analysis_scope": "oc_group_a"})
        got = json.loads(toolset.tools["get_research_packet"].function(ctx, "600550"))
        assert got["packet"] is None
        assert "no prior research packet" in got["note"]

    def test_tools_fail_closed_without_scope(self, tmp_path):
        toolset = _toolset(tmp_path)
        ctx = _deps(tmp_path, {})
        out = json.loads(toolset.tools["save_research_packet"].function(
            ctx, "600550", "COMPLETE", thesis="t"))
        assert "analysis_scope" in out["error"]
        out = json.loads(toolset.tools["record_customer_evidence"].function(
            ctx, "600550", "claim"))
        assert "analysis_scope" in out["error"]

    def test_customer_evidence_roundtrip(self, tmp_path):
        toolset = _toolset(tmp_path)
        ctx = _deps(tmp_path, {"analysis_scope": "oc_group_a"})
        out = json.loads(toolset.tools["record_customer_evidence"].function(
            ctx, "600550", "供应商说订单很满", source_hint="客户微信"))
        assert out["recorded"] is True
        got = json.loads(toolset.tools["get_research_packet"].function(ctx, "600550"))
        assert got["recent_customer_evidence"][0]["claim"] == "供应商说订单很满"

    def test_market_intelligence_routes_to_side_env(self, tmp_path, monkeypatch):
        import zuaef_quant.toolset as toolset_module

        captured: dict = {}

        def fake_run(script, args, quant_python, timeout):
            captured["script"], captured["args"] = script, args
            return json.dumps({"symbol": "600550", "count": 0, "items": []})

        monkeypatch.setattr(toolset_module, "_run", fake_run)
        toolset = _toolset(tmp_path)
        out = json.loads(toolset.tools["get_market_intelligence"].function("600550", 5))
        assert out["count"] == 0
        script, args = captured["script"], captured["args"]
        assert script.name == "quant_market_intel.py"
        assert args[args.index("--symbol") + 1] == "600550"
        assert args[args.index("--limit") + 1] == "5"

    def test_market_intelligence_failure_is_evidence(self, tmp_path, monkeypatch):
        import zuaef_quant.toolset as toolset_module

        monkeypatch.setattr(
            toolset_module, "_run",
            lambda *a: (_ for _ in ()).throw(RuntimeError("side env exploded")),
        )
        toolset = _toolset(tmp_path)
        out = json.loads(toolset.tools["get_market_intelligence"].function("600550"))
        assert "error" in out


class TestPluginSkillDelivery:
    def test_bundle_ships_quant_research_skill_dir(self, tmp_path, monkeypatch):
        from zuaef_quant.plugin import create_plugin, SKILLS_DIR

        monkeypatch.setenv("ZUAEF_QUANT_PYTHON", sys.executable)
        bundle = create_plugin(
            SimpleNamespace(workspace_root=tmp_path), {"code_mode": False}
        )
        assert bundle.skill_dirs == [SKILLS_DIR]
        skill = SKILLS_DIR / "quant-research" / "SKILL.md"
        assert skill.is_file()
        text = skill.read_text(encoding="utf-8")
        # deferred methodology the agent needs for full analysis
        for marker in (
            "name: quant-research",
            "Bull / Base / Bear",
            "Evidence hierarchy",
            "save_research_packet",
            "record_customer_evidence",
            "WebSearch",
        ):
            assert marker in text, f"skill missing {marker!r}"
