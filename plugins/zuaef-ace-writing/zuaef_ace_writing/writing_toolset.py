# Provenance: byte-identical copy of examples/writing_toolset.py (proof evidence,
# per SPEC §33 the original stays untouched). Keep both in sync; do not fork
# domain logic here — the Context Engine (ACE) remains the owner.
"""Thin ZUAEF adapter over article-context-engine (ACE) context capabilities.

The ACE engine owns materials, knowledge/evidence assets, corpus retrieval,
claim validation, and artifact saving. This module only calls
``tools/ctx.py`` and returns its receipts/text; no corpus selection, evidence
logic, or canonical workspace writing is duplicated here.

Agent-facing capabilities:

  list_materials      observe
  read_material       observe
  retrieve_exemplars  observe
  retrieve_knowledge  observe
  check_claim         observe
  save_artifact       local_write (snapshot under ZUAEF workspace only)

Exemplars are language/technique references. They are never factual evidence
for the current HW-951-style material set.

Run isolation: every ACE call is stamped with the current run_id (from
RunContext.deps), so receipts are attributable to the run that caused them.

Budget authority: per-run delivery caps are seeded from THIS run's ACE
receipts (durable truth, survives resume) plus this process's delivery
counter (fast path). Exhausted tools are withdrawn from the next model step's
action space via ``get_tools``; a refusal is a normal terminal return, so it
settles as a completed effect in the step ledger.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from pydantic_ai import FunctionToolset, RunContext

from zuaef_agent.models import CoreDeps

DEFAULT_ACE_ROOT = Path(
    os.environ.get(
        "ACE_ROOT",
        Path.home() / "projects/article-context-engine/article-context-engine",
    )
)

MAX_EXEMPLAR_PULLS = 6
MAX_KNOWLEDGE_PULLS = 4
MAX_CLAIM_CHECKS = 8

WRITING_RULES = (
    "ACE context capabilities are pull-based. Choose which material to read, which "
    "exemplar technique to retrieve, which knowledge/evidence asset to consult, and "
    "which claim to check; the Context Engine does not prescribe a workflow. "
    "Exemplars are language/technique references only, never factual sources. "
    "There is no quality/style scoring tool; the human editor owns taste. "
    "Budgets are per-run, seeded from this run's ACE receipts (resume-safe) and "
    "counted in-process; an exhausted tool is withdrawn from the next step's "
    "action space."
)


def _ace(
    ace_root: Path,
    *args: str,
    input_text: str | None = None,
    timeout: int = 120,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(ace_root / "tools" / "ctx.py"), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        input=input_text,
    )


def ace_prepare(
    article_id: str,
    *,
    title: str = "",
    account: str = "",
    materials: list[str] | None = None,
    ace_root: Path = DEFAULT_ACE_ROOT,
) -> dict:
    """Host-side prep: create the ACE workspace and ingest raw materials."""
    if not (ace_root / "workspaces" / article_id).exists():
        r = _ace(
            ace_root,
            "new",
            article_id,
            "--title",
            title,
            *(["--account", account] if account else []),
        )
        if r.returncode != 0:
            raise RuntimeError(f"ctx.py new failed: {r.stderr or r.stdout}")
    if materials:
        r = _ace(ace_root, "ingest", article_id, *materials)
        if r.returncode != 0:
            raise RuntimeError(f"ctx.py ingest failed: {r.stderr or r.stdout}")
    return {"article_id": article_id, "materials": materials or []}


def check_gate_impl(article_id: str, ace_root: Path = DEFAULT_ACE_ROOT) -> str:
    r = _ace(ace_root, "gate", article_id)
    return f"exit={r.returncode}\n{r.stdout}"


def machine_ready_or_complete(
    article_id: str, ace_root: Path = DEFAULT_ACE_ROOT
) -> tuple[bool, str]:
    """Gate predicate: machine gate fully green, or only human_final_reviewed pending.

    Both are success states for the Harness Integration Test: (a) the gate passed
    completely (human review already done), or (b) the machine gate has exactly one
    remaining blocker, human_final_reviewed — human review is an optional post-test
    observation, not a blocking condition."""
    output = check_gate_impl(article_id, ace_root)
    lines = output.strip().splitlines()
    try:
        exit_code = int(lines[0].removeprefix("exit="))
    except (ValueError, IndexError):
        return False, f"unparseable gate output: {output!r}"
    errors = [
        line.removeprefix("- ").strip() for line in lines[1:] if line.startswith("- ")
    ]
    if exit_code == 0:
        return True, "gate fully passed"
    only_human = len(errors) == 1 and "human_final_reviewed" in errors[0]
    if only_human:
        return True, errors[0]
    detail = "; ".join(errors) or output.strip()
    return False, detail


def list_materials_impl(
    article_id: str, run_id: str = "", ace_root: Path = DEFAULT_ACE_ROOT
) -> str:
    r = _ace(ace_root, "materials", article_id, "--run-id", run_id)
    return (
        r.stdout if r.returncode == 0 else f"MATERIALS FAILED: {r.stderr or r.stdout}"
    )


def read_material_impl(
    article_id: str,
    material_id: str,
    run_id: str = "",
    ace_root: Path = DEFAULT_ACE_ROOT,
) -> str:
    r = _ace(ace_root, "material", article_id, material_id, "--run-id", run_id)
    return (
        r.stdout
        if r.returncode == 0
        else f"MATERIAL READ FAILED: {r.stderr or r.stdout}"
    )


def _terms(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [t for t in value.replace("，", ",").replace(",", " ").split() if t]
    return [str(t) for t in value if str(t).strip()]


def retrieve_exemplars_impl(
    article_id: str,
    query: str | list[str],
    functions: str | list[str] | None = None,
    tags: str | list[str] | None = None,
    budget: int = 3,
    execution_id: str = "pull-exemplars",
    run_id: str = "",
    ace_root: Path = DEFAULT_ACE_ROOT,
) -> str:
    query_terms = _terms(query)
    args = [
        "exemplars",
        article_id,
        "--query",
        *query_terms,
        "--budget",
        str(budget),
        "--execution-id",
        execution_id,
        "--run-id",
        run_id,
    ]
    if functions:
        args += ["--functions", *_terms(functions)]
    if tags:
        args += ["--tags", *_terms(tags)]
    r = _ace(ace_root, *args)
    return (
        r.stdout if r.returncode == 0 else f"EXEMPLARS FAILED: {r.stderr or r.stdout}"
    )


def retrieve_knowledge_impl(
    article_id: str,
    query: str | list[str],
    budget: int = 3,
    run_id: str = "",
    ace_root: Path = DEFAULT_ACE_ROOT,
) -> str:
    r = _ace(
        ace_root,
        "knowledge",
        article_id,
        "--query",
        *_terms(query),
        "--budget",
        str(budget),
        "--run-id",
        run_id,
    )
    return (
        r.stdout if r.returncode == 0 else f"KNOWLEDGE FAILED: {r.stderr or r.stdout}"
    )


def check_claim_impl(
    article_id: str,
    claim: dict,
    run_id: str = "",
    purpose: str = "validation",
    ace_root: Path = DEFAULT_ACE_ROOT,
) -> str:
    """Ask ACE to validate one claim; a serialization problem is a returned
    failure string, never a raised exception (tool errors must not block a
    run through the retry loop)."""
    try:
        payload = json.dumps(claim, ensure_ascii=False, default=str)
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
        return json.dumps(
            {
                "ok": False,
                "error": f"claim is not JSON-serializable: {type(exc).__name__}",
                "hint": "pass plain JSON values in the claim object.",
            },
            ensure_ascii=False,
        )
    r = _ace(
        ace_root,
        "claim-check",
        article_id,
        "--run-id",
        run_id,
        "--purpose",
        purpose,
        input_text=payload,
    )
    return (
        r.stdout if r.returncode == 0 else f"CLAIM CHECK FAILED: {r.stderr or r.stdout}"
    )


def save_artifact_impl(
    article_id: str,
    final_markdown: str,
    claims: list[dict],
    sources: list[dict],
    snapshot_dir: Path | None = None,
    run_id: str = "",
    ace_root: Path = DEFAULT_ACE_ROOT,
) -> tuple[dict, Path | None]:
    """Ask ACE to validate and write the canonical artifact, then snapshot it.

    ``transport_ok`` records that the CLI executed and returned parseable JSON.
    The semantic verdict is ACE's own (``ok`` / ``fact_check_passed``) and is
    never overwritten here.
    """
    payload = json.dumps(
        {
            "final_markdown": final_markdown,
            "claims": claims,
            "sources": sources,
        },
        ensure_ascii=False,
    )
    r = _ace(ace_root, "save", article_id, "--run-id", run_id, input_text=payload)
    if r.returncode != 0:
        result = {
            "article_id": article_id,
            "ok": False,
            "transport_ok": False,
            "error": (r.stderr or r.stdout).strip()[:2000],
        }
        return result, None
    try:
        result = json.loads(r.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        result = {
            "article_id": article_id,
            "ok": False,
            "transport_ok": False,
            "error": r.stdout.strip()[:2000],
        }
        return result, None
    # Transport succeeded. Trust ACE's semantic verdict: only default ok=True
    # when ACE itself did not declare one.
    result["transport_ok"] = True
    result.setdefault("ok", True)

    snapshot_path: Path | None = None
    if snapshot_dir is not None:
        snapshot_path = snapshot_dir / "final.md"
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text(final_markdown, encoding="utf-8")
        result["snapshot_rel_path"] = None
        result["snapshot_sha256"] = hashlib.sha256(
            final_markdown.encode("utf-8")
        ).hexdigest()
    return result, snapshot_path


class BudgetedWritingToolset(FunctionToolset[CoreDeps]):
    """Run-scoped, resume-safe delivery budgets + action-space withdrawal.

    Budget authority is the ACE receipt ledger filtered by ``run_id`` (durable
    truth) plus this process's delivery counter (fast path). A tool whose
    budget is exhausted is refused at call time (a normal terminal return that
    settles as a completed effect) AND withdrawn from the next model step's
    action space by ``get_tools``, so the model stops being offered it.
    """

    _BUDGETED: tuple[tuple[str, str, int], ...] = (
        ("retrieve_exemplars", "pull-exemplars", MAX_EXEMPLAR_PULLS),
        ("retrieve_knowledge", "retrieve-knowledge", MAX_KNOWLEDGE_PULLS),
        ("check_claim", "check-claim", MAX_CLAIM_CHECKS),
    )

    def __init__(self, *, ace_root: Path, instructions: str = WRITING_RULES) -> None:
        super().__init__(instructions=instructions)
        self._ace_root = ace_root
        # Durable counts per (article_id, run_id, execution_id), read once per
        # process from ACE receipts; survives resume because receipts persist.
        self._durable: dict[tuple[str, str, str], int] = {}
        # This-process deliveries per (article_id, run_id, tool).
        self._local: dict[tuple[str, str, str], int] = {}
        # First article_id seen per run (one run == one article in this proof).
        self._run_article: dict[str, str] = {}

    # -- durable counting ----------------------------------------------------

    def _note_article(self, run_id: str, article_id: str) -> None:
        self._run_article.setdefault(run_id, article_id)

    def _receipt_count(self, article_id: str, run_id: str, execution_id: str) -> int:
        key = (article_id, run_id, execution_id)
        if key in self._durable:
            return self._durable[key]
        if execution_id == "check-claim":
            path = (
                self._ace_root
                / "workspaces"
                / article_id
                / "_state"
                / "claim-checks.jsonl"
            )
        else:
            path = (
                self._ace_root
                / "workspaces"
                / article_id
                / "_state"
                / "retrieval-receipts.jsonl"
            )
        count = 0
        if path.is_file():
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if (
                    record.get("execution_id") == execution_id
                    and str(record.get("run_id")) == run_id
                ):
                    count += 1
        self._durable[key] = count
        return count

    def _remaining(
        self, article_id: str, run_id: str, tool: str, execution_id: str, cap: int
    ) -> int:
        delivered = self._receipt_count(
            article_id, run_id, execution_id
        ) + self._local.get((article_id, run_id, tool), 0)
        return cap - delivered

    def _mark_delivered(self, article_id: str, run_id: str, tool: str) -> None:
        key = (article_id, run_id, tool)
        self._local[key] = self._local.get(key, 0) + 1

    def _final_delivery_note(
        self, article_id: str, run_id: str, tool: str, execution_id: str, cap: int
    ) -> str:
        """Warn the model when this was the last allowed delivery, so the
        upcoming withdrawal is not a surprise."""
        if self._remaining(article_id, run_id, tool, execution_id, cap) <= 0:
            return (
                "\n[NOTE] This was the final delivery of this tool for the run "
                f"(per-run cap {cap}). It will no longer be available from the next "
                "step — do not call it again. Draft and save with what you have."
            )
        return ""

    # -- action-space withdrawal ---------------------------------------------

    async def get_tools(self, ctx: RunContext[CoreDeps]) -> dict[str, Any]:
        """Per-step action space: budget-exhausted tools are not offered."""
        tools = await super().get_tools(ctx)
        run_id = ctx.deps.run_id
        article_id = self._run_article.get(run_id)
        if article_id is None:
            return tools  # nothing delivered yet, nothing exhausted
        for tool_name, execution_id, cap in self._BUDGETED:
            if tool_name not in tools:
                continue
            if self._remaining(article_id, run_id, tool_name, execution_id, cap) <= 0:
                del tools[tool_name]
        return tools


def build_writing_toolset(
    ace_root: Path = DEFAULT_ACE_ROOT,
) -> BudgetedWritingToolset:
    toolset = BudgetedWritingToolset(ace_root=ace_root)

    @toolset.tool(metadata={"code_mode": True})
    def list_materials(ctx: RunContext[CoreDeps], article_id: str) -> str:
        """List ACE ingested material index rows (ids, hashes, stored paths)."""
        return list_materials_impl(article_id, ctx.deps.run_id, ace_root)

    @toolset.tool(metadata={"code_mode": True})
    def read_material(
        ctx: RunContext[CoreDeps], article_id: str, material_id: str
    ) -> str:
        """Read one ingested raw material by id (e.g. M001). Use this instead of
        a pre-built context pack; each read is receipted by ACE."""
        return read_material_impl(article_id, material_id, ctx.deps.run_id, ace_root)

    @toolset.tool(retries=3, metadata={"code_mode": True})
    def retrieve_exemplars(
        ctx: RunContext[CoreDeps],
        article_id: str,
        query: str,
        functions: str | None = None,
        tags: str | None = None,
        budget: int = 3,
    ) -> str:
        """Pull writing-technique exemplars for the current drafting need.

        `query` is one string of lexical terms (space/comma separated) over
        exemplar text/metadata; `functions` e.g. "QUOTE TRANSITION"; `tags`
        e.g. "low_author_intrusion scene_preserving". Returned fragments are
        language references only, never factual sources. Per-run cap: 6 pulls;
        once exhausted the tool is withdrawn from your action space."""
        toolset._note_article(ctx.deps.run_id, article_id)
        if (
            toolset._remaining(
                article_id,
                ctx.deps.run_id,
                "retrieve_exemplars",
                "pull-exemplars",
                MAX_EXEMPLAR_PULLS,
            )
            <= 0
        ):
            return (
                f"EXEMPLAR BUDGET EXHAUSTED (per-run cap {MAX_EXEMPLAR_PULLS}). "
                "Draft with the technique references already pulled; this tool "
                "is no longer available this run."
            )
        out = retrieve_exemplars_impl(
            article_id,
            query,
            functions,
            tags,
            budget,
            run_id=ctx.deps.run_id,
            ace_root=ace_root,
        )
        toolset._mark_delivered(article_id, ctx.deps.run_id, "retrieve_exemplars")
        note = toolset._final_delivery_note(
            article_id,
            ctx.deps.run_id,
            "retrieve_exemplars",
            "pull-exemplars",
            MAX_EXEMPLAR_PULLS,
        )
        return note + out

    @toolset.tool(retries=3, metadata={"code_mode": True})
    def retrieve_knowledge(
        ctx: RunContext[CoreDeps],
        article_id: str,
        query: str,
        budget: int = 3,
    ) -> str:
        """Retrieve ACE knowledge/evidence policy assets relevant to `query`.

        Use this for claim taxonomy, evidence policy, or knowledge-braid rules
        while drafting. Each retrieval is receipted with selected refs and hashes.
        Per-run cap: 4 pulls; once exhausted the tool is withdrawn."""
        toolset._note_article(ctx.deps.run_id, article_id)
        if (
            toolset._remaining(
                article_id,
                ctx.deps.run_id,
                "retrieve_knowledge",
                "retrieve-knowledge",
                MAX_KNOWLEDGE_PULLS,
            )
            <= 0
        ):
            return (
                f"KNOWLEDGE BUDGET EXHAUSTED (per-run cap {MAX_KNOWLEDGE_PULLS}). "
                "Continue drafting with the policy assets already retrieved; this "
                "tool is no longer available this run."
            )
        out = retrieve_knowledge_impl(
            article_id, query, budget, run_id=ctx.deps.run_id, ace_root=ace_root
        )
        toolset._mark_delivered(article_id, ctx.deps.run_id, "retrieve_knowledge")
        note = toolset._final_delivery_note(
            article_id,
            ctx.deps.run_id,
            "retrieve_knowledge",
            "retrieve-knowledge",
            MAX_KNOWLEDGE_PULLS,
        )
        return note + out

    @toolset.tool(retries=3, metadata={"code_mode": True})
    def check_claim(
        ctx: RunContext[CoreDeps],
        article_id: str,
        claim: Any = None,
        purpose: str = "validation",
    ) -> str:
        """Validate one claim JSON against ACE source ledger rules.

        claim shape: {id,text,type,status,source_ids,qualifier?}. FACT and
        SUPPORTED_INTERPRETATION need existing source_ids. `purpose` labels why
        the check runs: "validation" for claims flagged by save_artifact, or
        "integration_probe" for the explicit end-of-run capability canary
        (non-authoritative for the saved artifact: its output must not trigger
        another save). The check is logged by ACE; fix failures before
        save_artifact. Per-run cap: 8 checks; once exhausted the tool is withdrawn.

        A malformed claim returns a normal error string, never a raised
        exception: a bad argument must not exhaust tool retries and block the
        run (Writing v0.2 field hardening)."""
        toolset._note_article(ctx.deps.run_id, article_id)
        if (
            toolset._remaining(
                article_id,
                ctx.deps.run_id,
                "check_claim",
                "check-claim",
                MAX_CLAIM_CHECKS,
            )
            <= 0
        ):
            return json.dumps(
                {
                    "ok": True,
                    "skipped": True,
                    "budget_exhausted": True,
                    "hint": "check_claim budget exhausted; batch validation is in "
                    "save_artifact. Call save_artifact now, then return RunSummary.",
                },
                ensure_ascii=False,
            )
        if isinstance(claim, str):
            try:
                claim = json.loads(claim)
            except json.JSONDecodeError:
                return json.dumps(
                    {
                        "ok": False,
                        "error": f"claim is not valid JSON: {claim[:200]!r}",
                        "hint": "pass the claim as a JSON object, e.g. "
                        '{"id":"C1","text":"...","type":"FACT","source_ids":["S1"],"status":"resolved"}',
                    },
                    ensure_ascii=False,
                )
        if not isinstance(claim, dict):
            return json.dumps(
                {
                    "ok": False,
                    "error": f"claim must be a JSON object, got {type(claim).__name__}",
                    "hint": "pass the claim as a JSON object with id/text/type/source_ids/status.",
                },
                ensure_ascii=False,
            )
        out = check_claim_impl(
            article_id,
            claim,
            run_id=ctx.deps.run_id,
            purpose=purpose,
            ace_root=ace_root,
        )
        toolset._mark_delivered(article_id, ctx.deps.run_id, "check_claim")
        note = toolset._final_delivery_note(
            article_id,
            ctx.deps.run_id,
            "check_claim",
            "check-claim",
            MAX_CLAIM_CHECKS,
        )
        return note + out

    @toolset.tool
    def save_artifact(
        ctx: RunContext[CoreDeps],
        article_id: str,
        final_markdown: str,
        claims: list[dict],
        sources: list[dict],
    ) -> dict:
        """Submit the complete article and evidence ledgers to ACE.

        sources entries: {"id":"S1","kind":"material","label":"...","material_ids":["M001"]}.
        claims entries: {"id":"C1","text":"...","type":"FACT","source_ids":["S1"],"status":"resolved"}.
        source_ids reference S ids; material_ids reference M ids. ACE validates
        links, writes canonical final.md/release.json, runs the gate, and returns
        hashes. A run snapshot is also written under the ZUAEF workspace and is
        verified by the runtime. Never use M00x placeholders."""
        result, snapshot_path = save_artifact_impl(
            article_id,
            final_markdown,
            claims,
            sources,
            snapshot_dir=ctx.deps.workspace_root / "artifacts" / ctx.deps.run_id,
            run_id=ctx.deps.run_id,
            ace_root=ace_root,
        )
        if snapshot_path is not None:
            result["snapshot_rel_path"] = snapshot_path.relative_to(
                ctx.deps.workspace_root
            ).as_posix()
        return result

    return toolset
