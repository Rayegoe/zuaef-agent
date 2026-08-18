"""Production writing driver — Agent-owned writing, thin mechanical host.

Writing SPEC v0.2 (§1, §5, §6, §21, §22):

- The host performs ONLY the mechanical half of a writing run:
  accept assignment -> read raw file bytes -> compute sha256 -> validate
  rights -> create the ACE workspace -> ingest raw materials -> bind M ids
  -> freeze the thin task contract.
- Everything editorial belongs to the ONE writing agent: what to read, what
  to ignore, angle, questions, outline, techniques, exemplars, knowledge,
  drafting and revision.
- The ONLY production composition path is the ace-writing profile:

      build_profile_agent("ace-writing") -> execute_run

  There is no hand-built writing agent (no build_agent + extra_toolsets),
  no host writing_plan, no selected techniques / editorial memory / examples
  projection, and no one-pass-only contract.

The pre-v0.2 host-projected machinery (prepare_writing_context,
render_writing_context, run_production_article, build_production_agent,
ProductionWritingToolset) is retired from the production authority and lives
in ``benchmarks/editorial-learning/scripts/host_projection_legacy.py`` for
the sequential/compare experiments only (SPEC §22 "删除/废弃").
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass, replace
from decimal import Decimal
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai.messages import ModelResponse, ToolCallPart

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(REPO),
    str(REPO / "examples"),
    str(REPO / "src"),
    str(REPO / "plugins" / "zuaef-ace-writing"),
]

from zuaef_ace_writing.writing_toolset import (
    DEFAULT_ACE_ROOT,
    ace_prepare,
    list_materials_impl,
)

from zuaef_agent.composition import build_profile_agent
from zuaef_agent.config import AgentSettings
from zuaef_agent.models import CoreDeps
from zuaef_agent.runtime import PausedRun, execute_run

RIGHTS_STATUSES = ("study-only", "licensed", "user-provided", "unknown")

PRODUCTION_PROFILE = "ace-writing"


# --- production input contract (SPEC §6) ---------------------------------------
# The task carries ONLY the user's declared intent plus hard constraints.
# It must NOT carry a writing_plan, angle, questions, outline, selected
# techniques, selected editorial memory, selected examples, material ids, or
# any preassembled context pack — the WritingAgent owns all of that.


class WritingTask(BaseModel):
    """The thin production input contract for one article."""

    model_config = ConfigDict(extra="forbid")  # WRITE-2: host plan fields are rejected

    article_id: str = Field(min_length=1)
    assignment: str = Field(min_length=1)
    audience: str | None = None
    constraints: list[str] = Field(default_factory=list)


@dataclass(frozen=True)
class PreparedFile:
    """One ingested material as mechanical metadata (identity, never content)."""

    source_ref: str
    path: Path
    sha256: str
    byte_length: int
    rights: str
    material_id: str | None = None


@dataclass(frozen=True)
class PrepResult:
    """What the host knows after mechanical preparation.

    ``run_id`` doubles as the ACE workspace id for the article: receipts are
    stamped with it and ``save_artifact`` writes into it. The model is told
    this id so its saves land in the right workspace.
    """

    task: WritingTask
    run_id: str
    ace_root: Path
    title: str
    files: list[PreparedFile]

    def record(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "title": self.title,
            "files": [
                {
                    "source_ref": f.source_ref,
                    "sha256": f.sha256,
                    "bytes": f.byte_length,
                    "rights": f.rights,
                    "material_id": f.material_id,
                }
                for f in self.files
            ],
        }


# --- mechanical preparation (SPEC §5.1 Host MAY) --------------------------------


def resolve_ace_root(ace_root: str | Path | None = None) -> Path:
    """Explicit arg wins, then ACE_ROOT env, then the compiled default."""
    raw = str(ace_root or os.environ.get("ACE_ROOT") or DEFAULT_ACE_ROOT)
    root = Path(raw).expanduser().resolve()
    if not (root / "tools" / "ctx.py").is_file():
        raise FileNotFoundError(f"ACE tools/ctx.py not found at {root}")
    return root


def mechanical_prepare(
    task: WritingTask,
    *,
    material_paths: list[str | Path],
    rights: str = "user-provided",
    ace_root: str | Path | None = None,
    title: str = "",
    run_id: str | None = None,
    clean_workspace: bool = True,
) -> PrepResult:
    """Bytes -> sha256 -> rights -> ACE workspace -> ingest -> M-id binding.

    The host does not read for meaning here: it only hashes exact bytes,
    validates the declared rights status and lets ACE assign material ids
    from its own index. Nothing about importance, angle or structure is
    computed — those are writing judgments (SPEC §5.2, §16).
    """
    if rights not in RIGHTS_STATUSES:
        raise ValueError(
            f"rights must be one of {RIGHTS_STATUSES}, got {rights!r}"
        )
    if not material_paths:
        raise ValueError("at least one material file is required")
    ace_root_path = resolve_ace_root(ace_root)
    run_id = run_id or task.article_id
    prepared: list[PreparedFile] = []
    for raw in material_paths:
        path = Path(raw).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"material file missing: {path}")
        data = path.read_bytes()
        prepared.append(
            PreparedFile(
                source_ref=path.name,
                path=path,
                sha256=hashlib.sha256(data).hexdigest(),
                byte_length=len(data),
                rights=rights,
            )
        )
    if not prepared:
        raise ValueError("at least one material file is required")

    workspace = ace_root_path / "workspaces" / run_id
    if clean_workspace and workspace.is_dir():
        import shutil

        shutil.rmtree(workspace)
    ace_prepare(
        run_id,
        title=title or task.article_id,
        materials=[str(f.path) for f in prepared],
        ace_root=ace_root_path,
    )

    # Bind real M ids from ACE's own material index (SPEC §15.2: ids preserved).
    index = list_materials_impl(run_id, run_id=run_id, ace_root=ace_root_path)
    by_name: dict[str, str] = {}
    for line in index.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(rec, dict) and rec.get("id") and rec.get("filename"):
            by_name[str(rec["filename"])] = str(rec["id"])
    bound = [
        replace(f, material_id=by_name.get(f.source_ref)) for f in prepared
    ]
    return PrepResult(
        task=task,
        run_id=run_id,
        ace_root=ace_root_path,
        title=title or task.article_id,
        files=bound,
    )


# --- thin prompt: task + mechanical facts only (SPEC §5.2, WRITE-2) --------------


def render_agent_prompt(prep: PrepResult, *, feedback: str | None = None) -> str:
    """The first model request.

    Carries the user's declared task and the mechanical facts the model needs
    to act (workspace id, materials available). It does NOT carry any host
    decision: no angle, no questions, no outline, no selected techniques, no
    selected memory, no selected examples, no material text.
    """
    task = prep.task
    lines = [
        (
            "Write the article for the task below. You own the entire writing "
            "trajectory: the host ingested the raw materials and nothing else "
            "was decided for you. Decide what to read, what to retrieve, what "
            "to check, how to structure and how to write."
        ),
        "",
        f"article_id (ACE article workspace id): {task.article_id}",
        f"assignment: {task.assignment}",
    ]
    if task.audience:
        lines.append(f"audience: {task.audience}")
    if task.constraints:
        lines.append("constraints:")
        for c in task.constraints:
            lines.append(f"- {c}")
    lines.append(
        "materials: already ingested into the ACE workspace above. Run "
        "list_materials to see the index, then read the materials the article "
        "actually needs (skip the rest)."
    )
    lines.append(
        "Submission: the ONLY way to submit the article is save_artifact "
        "(with the claim and source ledgers). Writing the article into a file "
        "with generic file tools does NOT submit it — it only wastes the "
        "request budget and artifacts/** is protected from generic writes "
        "anyway. Do not write draft copies to the filesystem at all."
    )
    if feedback:
        lines.extend(
            [
                "",
                "Editorial feedback from the human editor:",
                "---",
                feedback,
                "---",
                (
                    "Revise the article in the same ACE workspace to respond "
                    "to this feedback, then submit the revised article with "
                    "save_artifact."
                ),
            ]
        )
    lines.extend(
        [
            "",
            (
                "When the article is complete, submit it with save_artifact "
                f"(article_id = `{task.article_id}`) together with the claim "
                "and source ledgers, then return your RunSummary."
            ),
        ]
    )
    lines.append(
        "RunSummary format: artifacts=[\"artifacts/\" + your run_id + "
        "\"/final.md\"] (the full workspace-relative path INCLUDING the "
        "artifacts/ prefix, e.g. artifacts/wcase-1/final.md) and in evidence "
        "use ONLY artifact:... refs — never tool-effect refs (the host settles "
        "tool effects itself, and an invented or malformed ref downgrades "
        "the run)."
    )
    return "\n".join(lines)


# --- run through the profile (SPEC §21: one production composition path) ---------


def composition_settings(
    settings: AgentSettings, *, request_limit: int | None = None
) -> AgentSettings:
    """The effective settings used to compose the writing agent.

    Writing v0.2 (MEASURED, see report): the generic FileSystem and Knowledge
    capabilities are OFF for the writing profile. Their functions are fully
    covered by the ACE toolset (materials/exemplars/knowledge/claims), and
    field runs with them ON wasted the request budget: FileSystem-on runs
    wandered into workspace exploration (WCASE-2: 21 file calls, no artifact)
    or wrote drafts directly instead of saving through ACE (WCASE-1 run 1);
    Knowledge-on runs explored the workspace knowledge corpus before writing
    (WCASE-4 revision: ~12 knowledge calls, budget exhausted before save).
    Planning, Skills, ToolOutputLimits and StepPersistence stay ON (SPEC §4).
    """
    return settings.with_overrides(
        **({"request_limit": request_limit} if request_limit is not None else {}),
        enable_filesystem=False,
        enable_knowledge=False,
    )


def run_production_task(
    settings: AgentSettings,
    *,
    task: WritingTask,
    material_paths: list[str | Path],
    title: str = "",
    rights: str = "user-provided",
    ace_root: str | Path | None = None,
    run_id: str | None = None,
    feedback: str | None = None,
    clean_workspace: bool = True,
    request_limit: int | None = None,
    prompt: str | None = None,
    config_root: Path = REPO,
    profile: str = PRODUCTION_PROFILE,
) -> dict:
    """One production article: mechanical prep -> profile agent -> execute_run.

    Composition is always ``build_profile_agent(profile)``; the driver never
    hand-builds a writing agent (WRITE-1). The snapshot is passed to
    ``execute_run`` so the receipt freezes the exact composed plugins for this
    run. ``profile`` defaults to the production ace-writing profile; pass
    "ace-writing-codemode" for the experimental CodeMode side of the A/B.
    """
    run_id = run_id or task.article_id
    if not material_paths:
        raise ValueError("at least one material file is required")
    # Writing v0.2 composition decision (MEASURED, recorded in the v0.2 report):
    # the generic FileSystem and Knowledge capabilities are OFF for the writing
    # profile. Their file/knowledge access is fully covered by the ACE toolset
    # (list/read materials, retrieve exemplars/knowledge), and field runs with
    # them ON wasted the budget (WCASE-2: 21 filesystem calls with no artifact;
    # WCASE-4 revision: ~12 knowledge calls before save; WCASE-1 run 1 wrote
    # the draft directly instead of saving through ACE). Planning, Skills,
    # ToolOutputLimits and StepPersistence stay ON (SPEC §4).
    run_settings = composition_settings(settings, request_limit=request_limit)
    # Re-runnable: clear this run_id's receipts/steps/stale snapshots (and the
    # ACE workspace for a fresh run) BEFORE preparation so the execution starts
    # empty. A revision pass (clean_workspace=False) keeps the ACE workspace —
    # materials stay ingested and the previous draft stays in place.
    ace_root_path = resolve_ace_root(ace_root)
    reset_run_state(
        run_settings,
        run_id,
        ace_root=ace_root_path,
        clean_ace=clean_workspace,
    )
    prep = mechanical_prepare(
        task,
        material_paths=material_paths,
        rights=rights,
        ace_root=ace_root_path,
        title=title,
        run_id=run_id,
        clean_workspace=clean_workspace,
    )
    agent, snapshot = build_profile_agent(
        run_settings,
        run_id=run_id,
        profile=profile,
        config_root=config_root,
    )
    if prompt is None:
        prompt = render_agent_prompt(prep, feedback=feedback)
    outcome = execute_run(
        agent,
        CoreDeps(workspace_root=run_settings.workspace_root.resolve(), run_id=run_id),
        prompt=prompt,
        settings=run_settings,
        run_id=run_id,
        retries={"tools": 5},
        composition=snapshot,
    )
    if isinstance(outcome, PausedRun):
        return {
            "run_id": run_id,
            "task_id": task.article_id,
            "status": "paused",
            "pending_approvals": [c.tool_name for c in outcome.requests.approvals],
        }
    receipt = outcome.receipt
    text, path = final_artifact_text(settings.workspace_root, run_id)
    record: dict[str, Any] = {
        "run_id": run_id,
        "task_id": task.article_id,
        "status": receipt.status,
        "summary_outcome": receipt.summary.outcome,
        "model_requests": receipt.usage.get("requests"),
        "usage": receipt.usage,
        "verified_artifacts": [v.path for v in receipt.verified_artifacts],
        "verified_tool_effects": [
            (v.tool_name, v.status) for v in receipt.verified_tool_effects
        ],
        "unresolved_effects": [
            (v.tool_name, v.status) for v in receipt.unresolved_effects
        ],
        "artifact_path": path,
        "artifact_exists": bool(text),
        "artifact_chars": len(text),
        "artifact_sha256": (
            hashlib.sha256(text.encode("utf-8")).hexdigest() if text else None
        ),
        "prep": prep.record(),
    }
    return plain_jsonable(record)


def plain_jsonable(value: Any) -> Any:
    """Recursively convert a run record into JSON-safe primitives.

    Receipt usage carries pydantic ``Decimal`` cost values and the record
    carries ``Path`` objects; the CLI/runner renders it to JSON."""
    if isinstance(value, dict):
        return {key: plain_jsonable(v) for key, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain_jsonable(v) for v in value]
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, Path):
        return str(value)
    return value


# --- mechanical helpers ----------------------------------------------------------


def metrics_from_messages(messages) -> dict:
    """Model-request and tool-call counts from real run history."""
    requests = 0
    tool_calls: list[str] = []
    for message in messages:
        if isinstance(message, ModelResponse):
            requests += 1
        for part in getattr(message, "parts", []):
            if isinstance(part, ToolCallPart):
                tool_calls.append(getattr(part, "tool_name", "?"))
    return {
        "model_requests": requests,
        "tool_calls": len(tool_calls),
        "tool_names": tool_calls,
    }


def final_artifact_text(workspace_root: Path, run_id: str) -> tuple[str, str]:
    """The saved article (snapshot final.md), not the run summary."""
    path = Path(workspace_root) / "artifacts" / run_id / "final.md"
    if not path.is_file():
        return "", str(path)
    return path.read_text(encoding="utf-8"), str(path)


def reset_run_state(
    settings: AgentSettings,
    run_id: str,
    *,
    ace_root: str | Path | None = None,
    clean_ace: bool = True,
) -> None:
    """Re-runnable: drop this run_id's step-store dirs, settlement receipts,
    the ACE workspace and stale snapshots so budgets/receipts start empty.

    ``clean_ace=False`` keeps the ACE workspace (revision pass against the
    same article)."""
    import shutil

    for child in (
        settings.step_store_dir.glob(f"{run_id}*")
        if settings.step_store_dir.is_dir()
        else []
    ):
        if child.is_dir() and (
            child.name == run_id or child.name.startswith(f"{run_id}-")
        ):
            shutil.rmtree(child, ignore_errors=True)
    for root in (settings.receipt_dir, settings.state_root / "settlements"):
        for child in root.glob(f"{run_id}*") if root.is_dir() else []:
            if child.is_file():
                child.unlink()
    if clean_ace:
        ace_workspace = resolve_ace_root(ace_root) / "workspaces" / run_id
        if ace_workspace.is_dir():
            shutil.rmtree(ace_workspace)
    artifact_dir = settings.workspace_root / "artifacts" / run_id
    if artifact_dir.is_dir():
        shutil.rmtree(artifact_dir, ignore_errors=True)


# --- CLI: thin driver (SPEC §22: CLI ok, but only mechanical prep + profile) -----


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--task", required=True, help="article_id (ACE workspace id)")
    ap.add_argument("--assignment", required=True)
    ap.add_argument("--audience", default=None)
    ap.add_argument(
        "--material",
        action="append",
        required=True,
        help="path to one raw material file (repeatable)",
    )
    ap.add_argument("--title", default="")
    ap.add_argument("--rights", default="user-provided", choices=RIGHTS_STATUSES)
    ap.add_argument("--constraints", action="append", default=[])
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--request-limit", type=int, default=None)
    ap.add_argument("--feedback", default=None, help="natural-language editorial feedback (revision pass)")
    ap.add_argument("--ace-root", default=None)
    ap.add_argument(
        "--keep-workspace",
        action="store_true",
        help="do not clean the ACE workspace before running (revision flow)",
    )
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    task = WritingTask(
        article_id=args.task,
        assignment=args.assignment,
        audience=args.audience,
        constraints=list(args.constraints),
    )
    settings = AgentSettings.from_env().with_overrides(
        workspace_root=REPO / "workspace",
        runtime_state_root=REPO / ".zuaef-state",
    )
    # Generic Harness capabilities stay ON (planning/skills/filesystem/
    # knowledge/tool output limits/step persistence) — writing v0.2 restores
    # them instead of switching them off (SPEC §4).
    record = run_production_task(
        settings,
        task=task,
        material_paths=args.material,
        title=args.title,
        rights=args.rights,
        ace_root=args.ace_root,
        run_id=args.run_id,
        feedback=args.feedback,
        clean_workspace=not args.keep_workspace,
        request_limit=args.request_limit,
    )
    print(json.dumps(record, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()