"""Production writing driver — a small environment around one writer model.

The host ingests sources, builds one bounded Markdown desk pack, persists the
article and records runtime facts. The model owns meaning, selection,
viewpoint, narrative, factual restraint and language.
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
    DEFAULT_CORPUS_ROOT,
    ace_prepare,
    build_writer_context,
    list_materials_impl,
)

from zuaef_agent.composition import build_profile_agent
from zuaef_agent.config import AgentSettings
from zuaef_agent.integrity import read_run_timings
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
        raise ValueError(f"rights must be one of {RIGHTS_STATUSES}, got {rights!r}")
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
    bound = [replace(f, material_id=by_name.get(f.source_ref)) for f in prepared]
    return PrepResult(
        task=task,
        run_id=run_id,
        ace_root=ace_root_path,
        title=title or task.article_id,
        files=bound,
    )


# --- thin prompt: task + mechanical facts only (SPEC §5.2, WRITE-2) --------------


def render_agent_prompt(
    prep: PrepResult,
    writer_context: str,
    *,
    feedback: str | None = None,
    previous_article: str | None = None,
    synthesis_boundary_instruction: str | None = None,
) -> str:
    """Render the normal or deliberately narrow revision entry.

    ``synthesis_boundary_instruction`` is the T006-B5 benchmark-only seam: one
    optional compact writer instruction appended to the writer instructions
    without touching the evidence desk pack (``writer_context`` stays
    byte-identical). Default ``None`` keeps production writer behavior
    unchanged.
    """
    task = prep.task
    revision = feedback is not None
    if revision and not previous_article:
        raise ValueError("revision requires the previous article")
    lines = [
        "Revise the article." if revision else "Write the article.",
        "",
        "# Task",
        "",
        f"Article ID: {task.article_id}",
        "",
        task.assignment,
    ]
    if task.audience:
        lines.extend(["", f"Audience: {task.audience}"])
    if task.constraints:
        lines.extend(["", "Constraints:"])
        for c in task.constraints:
            lines.append(f"- {c}")
    if revision:
        lines.extend(
            [
                "",
                "# Current article",
                "",
                previous_article or "",
                "",
                "# Human feedback",
                "",
                feedback or "",
            ]
        )
    lines.extend(["", writer_context])
    if synthesis_boundary_instruction:
        lines.extend(
            [
                "",
                "# Evidence-boundary synthesis rule",
                "",
                synthesis_boundary_instruction,
            ]
        )
    lines.extend(
        [
            "",
            (
                "Write or revise the complete article now. Use pull_context only if "
                "a specific question remains unanswered. Save the result once with "
                "save_article(markdown), then respond naturally. Do not create "
                "plans, task state, claim rows, source ledgers or receipt fields."
            ),
        ]
    )
    return "\n".join(lines)


# --- run through the profile (SPEC §21: one production composition path) ---------


def composition_settings(
    settings: AgentSettings, *, request_limit: int | None = None
) -> AgentSettings:
    """Compose the writer with StepPersistence as host-only evidence.

    Persistence is not context; history is not working memory; the workspace
    is not the prompt.
    """
    return settings.with_overrides(
        **({"request_limit": request_limit} if request_limit is not None else {}),
        enable_filesystem=False,
        enable_knowledge=False,
        enable_planning=False,
        enable_skills=False,
        enable_tool_output_limits=False,
        enable_shell=False,
        enable_repo_context=False,
        enable_web_search=False,
        enable_web_fetch=False,
        enable_tool_search=False,
        enable_memory=False,
        enable_conversation_search=False,
        enable_subagents=False,
        enable_context_controls=False,
    )


def _elapsed_ms(started_at: Any, finished_at: Any) -> float | None:
    """Return a persisted receipt duration without estimating missing facts."""
    try:
        duration = (finished_at - started_at).total_seconds() * 1000
    except (AttributeError, TypeError, ValueError, OverflowError):
        return None
    if duration < 0:
        return None
    return round(duration, 3)


def _timing_fields(
    settings: AgentSettings,
    *,
    run_id: str,
    started_at: Any,
    finished_at: Any,
    usage: dict[str, Any],
) -> dict[str, Any]:
    """Project existing receipt/StepStore facts into a WCASE record."""
    timings = (
        read_run_timings(settings.step_store_dir, run_id)
        if settings.enable_step_persistence
        else {"request_latencies_ms": None, "tool_latencies_ms": None}
    )
    return {
        "wall_clock_ms": _elapsed_ms(started_at, finished_at),
        "request_latencies_ms": timings["request_latencies_ms"],
        "tool_latencies_ms": timings["tool_latencies_ms"],
        "largest_input_tokens": usage.get("largest_input_tokens"),
        "runtime_timestamps": {
            "started_at": started_at.isoformat()
            if hasattr(started_at, "isoformat")
            else None,
            "finished_at": finished_at.isoformat()
            if hasattr(finished_at, "isoformat")
            else None,
        },
    }


def run_production_task(
    settings: AgentSettings,
    *,
    task: WritingTask,
    material_paths: list[str | Path],
    title: str = "",
    rights: str = "user-provided",
    ace_root: str | Path | None = None,
    corpus_root: str | Path | None = None,
    run_id: str | None = None,
    feedback: str | None = None,
    previous_article: str | None = None,
    clean_workspace: bool = True,
    request_limit: int | None = None,
    prompt: str | None = None,
    config_root: Path = REPO,
    profile: str = PRODUCTION_PROFILE,
    include_technique_guidance: bool = True,
    technique_selection_mode: str = "host",
    synthesis_boundary_instruction: str | None = None,
) -> dict:
    """One production article: mechanical prep -> profile agent -> execute_run.

    Composition is always ``build_profile_agent(profile)``; the driver never
    hand-builds a writing agent (WRITE-1). The snapshot is passed to
    ``execute_run`` so the receipt freezes the exact composed plugins for this
    run. ``profile`` defaults to the production ace-writing profile.
    """
    run_id = run_id or task.article_id
    if not material_paths:
        raise ValueError("at least one material file is required")
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
    if feedback and previous_article is None:
        previous_article, _ = final_artifact_text(
            settings.workspace_root, task.article_id
        )
    context_query = "\n".join(
        part
        for part in (
            task.assignment,
            task.audience or "",
            "\n".join(task.constraints),
            feedback or "",
        )
        if part
    )
    corpus_root_path = (
        Path(corpus_root).expanduser().resolve()
        if corpus_root is not None
        else DEFAULT_CORPUS_ROOT
    )
    writer_context = build_writer_context(
        prep.run_id,
        context_query,
        run_id=run_id,
        ace_root=ace_root_path,
        learning_root=REPO / "learning",
        corpus_root=corpus_root_path,
        include_technique_guidance=include_technique_guidance,
        technique_selection_mode=technique_selection_mode,
    )
    agent, snapshot = build_profile_agent(
        run_settings,
        run_id=run_id,
        profile=profile,
        config_root=config_root,
    )
    if prompt is None:
        prompt = render_agent_prompt(
            prep,
            writer_context,
            feedback=feedback,
            previous_article=previous_article,
            synthesis_boundary_instruction=synthesis_boundary_instruction,
        )
    outcome = execute_run(
        agent,
        CoreDeps(
            workspace_root=run_settings.workspace_root.resolve(),
            run_id=run_id,
            bindings={
                "writing_article_id": prep.run_id,
                "writing_corpus_root": str(corpus_root_path),
            },
        ),
        prompt=prompt,
        settings=run_settings,
        run_id=run_id,
        composition=snapshot,
    )
    if isinstance(outcome, PausedRun):
        pause_receipt = outcome.pause_receipt
        return {
            "run_id": run_id,
            "task_id": task.article_id,
            "status": "paused",
            "pending_approvals": [c.tool_name for c in outcome.requests.approvals],
            **_timing_fields(
                run_settings,
                run_id=run_id,
                started_at=pause_receipt.started_at,
                finished_at=pause_receipt.finished_at,
                usage=pause_receipt.usage,
            ),
        }
    receipt = outcome.receipt
    text, path = final_artifact_text(settings.workspace_root, run_id)
    record: dict[str, Any] = {
        "run_id": run_id,
        "task_id": task.article_id,
        "status": receipt.execution_state,
        "outcome": receipt.outcome,
        "model_requests": receipt.usage.get("requests"),
        "usage": receipt.usage,
        "artifact_facts": [v.path for v in receipt.artifact_facts],
        "tool_effect_facts": [
            (v.tool_name, v.status) for v in receipt.tool_effect_facts
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
        **_timing_fields(
            run_settings,
            run_id=run_id,
            started_at=receipt.started_at,
            finished_at=receipt.finished_at,
            usage=receipt.usage,
        ),
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
    ap.add_argument(
        "--feedback",
        default=None,
        help="natural-language editorial feedback (revision pass)",
    )
    ap.add_argument("--ace-root", default=None)
    ap.add_argument("--corpus-root", default=None)
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
    record = run_production_task(
        settings,
        task=task,
        material_paths=args.material,
        title=args.title,
        rights=args.rights,
        ace_root=args.ace_root,
        corpus_root=args.corpus_root,
        run_id=args.run_id,
        feedback=args.feedback,
        clean_workspace=not args.keep_workspace,
        request_limit=args.request_limit,
    )
    print(json.dumps(record, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
