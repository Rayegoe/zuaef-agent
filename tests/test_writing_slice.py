"""Deterministic branches of the Harness-neutral Context Engine proof.

These tests exercise the ZUAEF adapter and host settlement against the real
article-context-engine repo. Real-model execution is tested by
``examples/writing_case.py`` itself, never faked with TestModel.

Run isolation is a first-class contract here: receipts are only accepted when
stamped with the current run_id, and budgets are per (run_id, tool). The
regression tests below assert both properties explicitly.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest import mock

from pydantic_ai import RunContext, RunUsage
from pydantic_ai.models.test import TestModel

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from examples.writing_case import build_prompt, context_usage, settle_run
from examples.writing_toolset import (
    DEFAULT_ACE_ROOT,
    MAX_CLAIM_CHECKS,
    ace_prepare,
    build_writing_toolset,
    check_claim_impl,
    list_materials_impl,
    machine_ready_or_complete,
    read_material_impl,
    retrieve_exemplars_impl,
    retrieve_knowledge_impl,
    save_artifact_impl,
)
from zuaef_agent.models import CoreDeps

ACE = Path(str(DEFAULT_ACE_ROOT))

VALID_CLAIM = {
    "id": "C001",
    "text": "机器运行四十天。",
    "type": "FACT",
    "source_ids": ["S001"],
    "status": "resolved",
}


def _invoke_tool(tool: object, args: dict[str, Any], ctx: Any) -> Any:
    """Call a registered tool's function directly, bypassing the Agent loop.

    ``toolset.tools`` holds ``pydantic_ai.tools.Tool`` objects whose
    ``.function`` is the original sync function with ``RunContext`` first.
    """
    fn = cast(Any, tool).function
    return fn(ctx, **args)


def _receipt_run(article_id: str, run_id: str, execution_id: str, n: int) -> None:
    """Synthesize n durable ACE retrieval receipts for one run (resume sim)."""
    path = ACE / "workspaces" / article_id / "_state" / "retrieval-receipts.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "receipt_id": f"rr-synth-{execution_id}",
        "article_id": article_id,
        "run_id": run_id,
        "execution_id": execution_id,
        "query": "synth",
        "selected_refs": ["ref"],
        "hashes": {"ref": "abc"},
    }
    with path.open("a", encoding="utf-8") as f:
        for _ in range(n):
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


@unittest.skipUnless(
    (ACE / "tools" / "ctx.py").is_file(), f"ACE repo not found at {ACE}"
)
class WritingContextCapabilityTests(unittest.TestCase):
    def setUp(self):
        self.article_id = f"test-context-{uuid.uuid4().hex[:8]}"
        self.run_id = uuid.uuid4().hex
        self.ws = ACE / "workspaces" / self.article_id
        self.snap_root = Path(tempfile.mkdtemp(prefix="zuaef-context-test-"))
        self.material = Path(tempfile.mkstemp(suffix=".md")[1])
        self.material.write_text(
            "# 素材\n\n受访者说：这台机器连续跑了四十天，中间只停过一次电。\n"
            "数字是客户自报的 42。\n",
            encoding="utf-8",
        )
        ace_prepare(
            self.article_id,
            title="context capability test",
            materials=[str(self.material)],
            ace_root=ACE,
        )

    def tearDown(self):
        shutil.rmtree(self.ws, ignore_errors=True)
        shutil.rmtree(self.snap_root, ignore_errors=True)
        self.material.unlink(missing_ok=True)

    def _fake_ctx(self, run_id: str) -> SimpleNamespace:
        return SimpleNamespace(
            deps=SimpleNamespace(run_id=run_id, workspace_root=self.snap_root)
        )

    def _real_ctx(self, run_id: str) -> RunContext[CoreDeps]:
        return RunContext(
            deps=CoreDeps(workspace_root=self.snap_root.resolve(), run_id=run_id),
            model=TestModel(),
            usage=RunUsage(),
        )

    def _save_valid_article(self, run_id: str):
        final_md = "# 测试成稿\n\n" + "正文内容。" * 60
        claims = [
            {
                "id": "C001",
                "text": "受访者报告机器连续运行四十天。",
                "type": "FACT",
                "source_ids": ["S001"],
                "status": "resolved",
            },
            {
                "id": "C002",
                "text": "这个数字值得继续追问。",
                "type": "AUTHOR_INFERENCE",
                "status": "resolved",
            },
        ]
        sources = [
            {
                "id": "S001",
                "kind": "material",
                "label": "ingested material",
                "origin": "test",
                "material_ids": ["M001"],
            },
        ]
        return save_artifact_impl(
            self.article_id,
            final_md,
            claims,
            sources,
            snapshot_dir=self.snap_root / "artifacts" / run_id,
            run_id=run_id,
            ace_root=ACE,
        )

    def test_material_list_and_read_are_receipted(self):
        listing = list_materials_impl(self.article_id, run_id=self.run_id, ace_root=ACE)
        self.assertIn('"id": "M001"', listing)
        read = read_material_impl(
            self.article_id, "M001", run_id=self.run_id, ace_root=ACE
        )
        self.assertIn("MATERIAL M001", read)
        self.assertIn("RECEIPT", read)
        receipts = context_usage(self.ws, self.run_id)["by_execution_id"]
        self.assertIn("list-materials", receipts)
        self.assertIn("read-material", receipts)
        read_rec = receipts["read-material"][0]
        self.assertEqual(read_rec["selected_refs"], ["M001"])
        self.assertIn("material_sha256", read_rec)
        for rec in [*receipts["list-materials"], read_rec]:
            self.assertEqual(rec["run_id"], self.run_id)
            self.assertEqual(rec["article_id"], self.article_id)
            self.assertTrue(rec["timestamp"])

    def test_exemplar_retrieval_supports_query_function_and_tags(self):
        out = retrieve_exemplars_impl(
            self.article_id,
            query=["原话"],
            functions=["QUOTE"],
            tags=["quote_without_explanation"],
            budget=2,
            run_id=self.run_id,
            ace_root=ACE,
        )
        lines = [line for line in out.splitlines() if line.strip()]
        records = [json.loads(line) for line in lines if line.startswith("{")]
        self.assertTrue(records)
        for rec in records:
            funcs = {rec["primary_function"], *rec.get("secondary_functions", [])}
            tags = {
                str(rec.get("primary_function", "")).lower(),
                *[str(t).lower() for t in rec.get("effect_tags") or []],
                *[str(t).lower() for t in rec.get("use_when") or []],
            }
            self.assertIn("QUOTE", funcs)
            self.assertIn("quote_without_explanation", tags)
        pull = context_usage(self.ws, self.run_id)["receipts"][-1]
        self.assertEqual(pull["execution_id"], "pull-exemplars")
        self.assertEqual(pull["requested_tags"], ["quote_without_explanation"])
        self.assertTrue(pull["hashes"])
        self.assertEqual(pull["run_id"], self.run_id)

    def test_knowledge_retrieval_returns_hashed_assets(self):
        out = retrieve_knowledge_impl(
            self.article_id, ["证据"], budget=2, run_id=self.run_id, ace_root=ACE
        )
        self.assertIn("KNOWLEDGE", out)
        self.assertIn("RECEIPT", out)
        rec = context_usage(self.ws, self.run_id)["receipts"][-1]
        self.assertEqual(rec["execution_id"], "retrieve-knowledge")
        self.assertTrue(rec["hashes"])
        self.assertTrue(rec["selected_refs"])
        self.assertEqual(rec["run_id"], self.run_id)

    def test_save_artifact_settlement_and_claim_check(self):
        run_id = uuid.uuid4().hex
        result, snapshot_path = self._save_valid_article(run_id)
        self.assertTrue(result["ok"], result)
        self.assertTrue(result["fact_check_passed"])
        self.assertTrue(result["claims_resolved"])
        self.assertIsNotNone(snapshot_path)
        assert snapshot_path is not None
        sha = result["sha256"]
        self.assertEqual(hashlib.sha256(snapshot_path.read_bytes()).hexdigest(), sha)
        canonical = self.ws / "article" / "final.md"
        self.assertEqual(hashlib.sha256(canonical.read_bytes()).hexdigest(), sha)

        gate_ok, gate_detail = machine_ready_or_complete(self.article_id, ACE)
        self.assertTrue(gate_ok, gate_detail)

        settlement = settle_run(
            self.article_id,
            run_id,
            self.snap_root,
            self.snap_root / ".state",
            [(f"artifacts/{run_id}/final.md", sha)],
            ace_root=ACE,
        )
        self.assertTrue(settlement["ok"], settlement["problems"])

        check = check_claim_impl(
            self.article_id,
            dict(VALID_CLAIM),
            run_id=run_id,
            ace_root=ACE,
        )
        self.assertTrue(json.loads(check)["ok"], check)

        canonical.write_text(canonical.read_text() + "\n被篡改", encoding="utf-8")
        broken = settle_run(
            self.article_id,
            run_id,
            self.snap_root,
            self.snap_root / ".state",
            [(f"artifacts/{run_id}/final.md", sha)],
            ace_root=ACE,
        )
        self.assertFalse(broken["ok"])
        self.assertTrue(any("hash mismatch" in p for p in broken["problems"]))

    def test_save_artifact_rejects_placeholder_material_ids(self):
        final_md = "# 成稿\n\n" + "正文。" * 80
        result, _ = save_artifact_impl(
            self.article_id,
            final_md,
            claims=[
                {
                    "id": "C001",
                    "text": "素材事实。",
                    "type": "FACT",
                    "source_ids": ["S001"],
                    "status": "resolved",
                }
            ],
            sources=[
                {
                    "id": "S001",
                    "kind": "material",
                    "label": "test",
                    "origin": "test",
                    "material_ids": ["M00x-placeholder"],
                }
            ],
            snapshot_dir=None,
            run_id=self.run_id,
            ace_root=ACE,
        )
        self.assertTrue(result["ok"])
        self.assertFalse(result["fact_check_passed"])
        self.assertTrue(
            any("M00x placeholders" in e for e in result["material_errors"])
        )

    def test_toolset_builds_with_context_capabilities(self):
        toolset = build_writing_toolset(ACE)
        names = (
            {t.name for t in toolset.tools.values()}
            if hasattr(toolset, "tools")
            else set()
        )
        for expected in (
            "list_materials",
            "read_material",
            "retrieve_exemplars",
            "retrieve_knowledge",
            "check_claim",
            "save_artifact",
        ):
            self.assertIn(expected, names)

    def test_prompt_does_not_hardcode_a_tool_sequence(self):
        prompt = build_prompt("article-x", ["硬件", "CH340"], "shizuoweilai")
        self.assertIn("read_material", prompt)
        self.assertIn("retrieve_exemplars", prompt)
        self.assertIn("retrieve_knowledge", prompt)
        self.assertIn("check_claim", prompt)
        self.assertIn("integration_probe", prompt)
        self.assertNotIn("先调用 get_task_context", prompt)
        self.assertNotIn("pull_exemplars 最多 2 次", prompt)

    # ---- P0 regression: run isolation ------------------------------------

    def test_run_isolation_no_historical_contamination(self):
        """A prior run's receipts must never satisfy a later run's acceptance."""
        run_a = uuid.uuid4().hex
        run_b = uuid.uuid4().hex
        list_materials_impl(self.article_id, run_id=run_a, ace_root=ACE)
        read_material_impl(self.article_id, "M001", run_id=run_a, ace_root=ACE)
        check_claim_impl(
            self.article_id,
            dict(VALID_CLAIM),
            run_id=run_a,
            ace_root=ACE,
        )

        usage_a = context_usage(self.ws, run_a)
        self.assertTrue(usage_a["by_execution_id"].get("read-material"))
        self.assertEqual(len(usage_a["claim_checks"]), 1)

        usage_b = context_usage(self.ws, run_b)
        self.assertEqual(usage_b["receipts"], [])
        self.assertEqual(usage_b["by_execution_id"], {})
        self.assertEqual(usage_b["claim_checks"], [])

    def test_claim_probe_purpose_is_recorded(self):
        check_claim_impl(
            self.article_id,
            dict(VALID_CLAIM),
            run_id=self.run_id,
            purpose="integration_probe",
            ace_root=ACE,
        )
        recs = context_usage(self.ws, self.run_id)["claim_checks"]
        self.assertEqual([r.get("purpose") for r in recs], ["integration_probe"])
        self.assertEqual([r.get("run_id") for r in recs], [self.run_id])

    # ---- P0 regression: budgets are run-scoped, single authority ----------

    def test_budget_is_run_scoped(self):
        """The adapter's per-(run_id, tool) budget blocks the 9th claim check
        without consulting any receipt history, and a new run starts fresh."""
        toolset = build_writing_toolset(ACE)
        tool = toolset.tools["check_claim"]
        args = {"article_id": self.article_id, "claim": dict(VALID_CLAIM)}
        with mock.patch(
            "examples.writing_toolset.check_claim_impl", return_value="stub"
        ) as impl:
            for _ in range(MAX_CLAIM_CHECKS):
                _invoke_tool(tool, args, self._fake_ctx(self.run_id))
            self.assertEqual(impl.call_count, MAX_CLAIM_CHECKS)
            skipped = json.loads(_invoke_tool(tool, args, self._fake_ctx(self.run_id)))
            self.assertTrue(skipped["budget_exhausted"])
            self.assertEqual(impl.call_count, MAX_CLAIM_CHECKS)  # no new impl call

        fresh_run = uuid.uuid4().hex
        with mock.patch(
            "examples.writing_toolset.check_claim_impl", return_value="stub"
        ) as impl2:
            out = _invoke_tool(tool, args, self._fake_ctx(fresh_run))
            self.assertEqual(out, "stub")
            self.assertEqual(impl2.call_count, 1)

    def test_exemplar_budget_refuses_without_hidden_delivery(self):
        """Exhausted exemplar budget returns guidance and writes NO receipt."""
        toolset = build_writing_toolset(ACE)
        tool = toolset.tools["retrieve_exemplars"]
        args = {"article_id": self.article_id, "query": "开场"}
        with mock.patch(
            "examples.writing_toolset.retrieve_exemplars_impl",
            return_value="stub",
        ) as impl:
            for _ in range(6):
                _invoke_tool(tool, args, self._fake_ctx(self.run_id))
            self.assertEqual(impl.call_count, 6)
            out = _invoke_tool(tool, args, self._fake_ctx(self.run_id))
            self.assertIn("EXEMPLAR BUDGET EXHAUSTED", out)
            self.assertEqual(impl.call_count, 6)  # no hidden fallback delivery
        self.assertEqual(
            context_usage(self.ws, self.run_id)["receipts"],
            [],
            "budget-exhausted refusals must not fabricate receipts",
        )

    def test_durable_quota_survives_toolset_rebuild(self):
        """Resume sim: receipts written by an earlier process of the SAME run_id
        count against the budget in a freshly built toolset."""
        _receipt_run(self.article_id, self.run_id, "retrieve-knowledge", 3)
        toolset = build_writing_toolset(ACE)
        ctx = self._real_ctx(self.run_id)
        tool = toolset.tools["retrieve_knowledge"]
        args = {"article_id": self.article_id, "query": "证据"}

        # 3 durable + 0 local: one more delivery is allowed (cap 4), and it is
        # the FINAL delivery — the toolset must warn the model about withdrawal.
        with mock.patch(
            "examples.writing_toolset.retrieve_knowledge_impl", return_value="stub"
        ) as impl:
            out = _invoke_tool(tool, args, ctx)
        self.assertIn("stub", out)
        self.assertIn("final delivery", out)
        self.assertEqual(impl.call_count, 1)

        # 3 durable + 1 local == cap: next call refused, tool withdrawn.
        tools = asyncio.run(toolset.get_tools(ctx))
        self.assertNotIn("retrieve_knowledge", tools)
        self.assertIn("retrieve_exemplars", tools)
        with mock.patch(
            "examples.writing_toolset.retrieve_knowledge_impl", return_value="stub"
        ) as impl2:
            out = _invoke_tool(tool, args, ctx)
        self.assertIn("KNOWLEDGE BUDGET EXHAUSTED", out)
        self.assertEqual(impl2.call_count, 0)

        # A DIFFERENT run's receipts never leak into this one (and vice
        # versa): other_run has its own 3 durable receipts and still allows
        # one more delivery — it does NOT inherit self.run_id's 3.
        other_run = uuid.uuid4().hex
        _receipt_run(self.article_id, other_run, "retrieve-knowledge", 3)
        toolset2 = build_writing_toolset(ACE)
        ctx2 = self._real_ctx(other_run)
        with mock.patch(
            "examples.writing_toolset.retrieve_knowledge_impl", return_value="stub"
        ) as impl3:
            out = _invoke_tool(toolset2.tools["retrieve_knowledge"], args, ctx2)
        self.assertIn("stub", out)
        self.assertEqual(impl3.call_count, 1)
        tools2 = asyncio.run(toolset2.get_tools(ctx2))
        self.assertNotIn("retrieve_knowledge", tools2)  # 3 durable + 1 local == cap

    def test_exhausted_tool_withdrawn_from_action_space(self):
        """After the cap is hit, the tool disappears from the next step's
        action space (get_tools) — the model is no longer offered it."""
        toolset = build_writing_toolset(ACE)
        ctx = self._real_ctx(self.run_id)
        args = {"article_id": self.article_id, "query": "开场"}
        with mock.patch(
            "examples.writing_toolset.retrieve_exemplars_impl", return_value="stub"
        ):
            for _ in range(6):
                _invoke_tool(toolset.tools["retrieve_exemplars"], args, ctx)
        tools = asyncio.run(toolset.get_tools(ctx))
        self.assertNotIn("retrieve_exemplars", tools)
        for name in (
            "list_materials",
            "read_material",
            "retrieve_knowledge",
            "check_claim",
            "save_artifact",
        ):
            self.assertIn(name, tools)

    # ---- P1 regression: adapter must not overwrite ACE's semantic ok ------

    def test_save_artifact_preserves_ace_semantic_ok(self):
        """A future ACE verdict of ok=false (exit 0) must survive the adapter."""
        fake_stdout = json.dumps(
            {"ok": False, "fact_check_passed": False, "problems": ["unresolved claim"]}
        )
        fake_proc = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=fake_stdout + "\n", stderr=""
        )
        with mock.patch("examples.writing_toolset._ace", return_value=fake_proc):
            result, snapshot_path = save_artifact_impl(
                self.article_id,
                "# 成稿\n\n" + "正文。" * 60,
                [],
                [],
                snapshot_dir=None,
                run_id=self.run_id,
                ace_root=ACE,
            )
        self.assertFalse(result["ok"])  # ACE's verdict preserved
        self.assertTrue(result["transport_ok"])  # transport layer still recorded
        self.assertFalse(result["fact_check_passed"])
        self.assertIsNone(snapshot_path)

    # ---- P0 regression: gate accepts machine-ready OR fully-reviewed ------

    def test_machine_ready_or_complete_accepts_both_success_states(self):
        run_id = uuid.uuid4().hex
        self._save_valid_article(run_id)
        ok, detail = machine_ready_or_complete(self.article_id, ACE)
        self.assertTrue(ok, detail)  # machine-ready, only human_final_reviewed left

        release = json.loads((self.ws / "release.json").read_text(encoding="utf-8"))
        release["human_final_reviewed"] = True
        (self.ws / "release.json").write_text(
            json.dumps(release, ensure_ascii=False), encoding="utf-8"
        )
        ok, detail = machine_ready_or_complete(self.article_id, ACE)
        self.assertTrue(ok, detail)  # fully reviewed gate also passes
        self.assertEqual(detail, "gate fully passed")

        other = f"test-empty-{uuid.uuid4().hex[:8]}"
        try:
            ace_prepare(other, title="empty", ace_root=ACE)
            ok, detail = machine_ready_or_complete(other, ACE)
            self.assertFalse(ok, detail)  # no artifact: not machine-ready
        finally:
            shutil.rmtree(ACE / "workspaces" / other, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
