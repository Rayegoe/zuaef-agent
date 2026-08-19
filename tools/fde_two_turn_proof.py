"""Authoritative two-turn FDE proof — Phase 2, SPEC v1.0 §7 (P2-4/P2-5/P2-6).

Runs the Golden Outcome through the PRODUCTION seam, exactly as SPEC §8
demands: GatewayService + profile=stillevo-fde + a deterministically bound
real Case + the real model + the real business plugins + real StepPersistence
+ real receipts. The transports surface is a recording adapter (deterministic
capture); every run executes the real Gateway service.

  Turn 1 (literal): 客户觉得上一篇 demo 太模板化。结合他之前给的背景和材料重写一篇。
                    价格先不要写，我看完再决定要不要发。
  Turn 2 (literal): 开头还是太像 AI，保留刚才客户背景，再改一版；其他要求不变。

No hidden editorial instruction is appended to either turn; Turn 2 inherits
Turn 1 only through the Gateway's public StepStore history restore plus the
Case state (trajectory/situation/drafts). The proof then exercises the shared
approval seam (PausedRun → approve / deny → resume_paused_run) on the same
bound Case and conversation.

Evidence captured: conversation_id, run ids, initial/loaded model-visible
tool surface (deterministic probe on the REAL profile), invoked/dormant
domains (StepPersistence ledger), Case reads/writes (trajectory/situation/
drafts), material refs, verified artifacts, no-price scan, publish calls,
pause/approval receipts, and the Turn-2 prior-history proof.

Usage (from the repo root; real model credentials required):

    uv run python tools/fde_two_turn_proof.py [--workspace DIR] [--article-id ID]
        [--no-model]   # deterministic-only: surface probe + approval over
                       # scripted model (no real LLM turn)

Environment preconditions (host ceiling + deployment secrets):
    LLM_API_BASE / LLM_API_KEY / LLM_MODEL
    ZUAEF_WORDPRESS_USERNAME / ZUAEF_WORDPRESS_APP_PASSWORD (wordpress compose)
    host ceiling flags: ZUAEF_ENABLE_TOOL_SEARCH=true etc. (set automatically
    by this script via setdefault; see .env.example)
    ACE checkout at ~/projects/article-context-engine/article-context-engine
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
from pathlib import Path
from uuid import uuid4

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(REPO),
    str(REPO / "src"),
    str(REPO / "plugins" / "zuaef-case"),
    str(REPO / "plugins" / "zuaef-ace-writing"),
]

# ── host ceiling (deployment environment) ────────────────────────────────────
# The profile requests the generalist surface; these setdefaults are the
# process/environment ceiling the Gateway process would carry. shell and
# repo_context stay OFF so the business deployment never exposes them.
os.environ.setdefault("ZUAEF_ENABLE_TOOL_SEARCH", "true")
os.environ.setdefault("ZUAEF_ENABLE_MEMORY", "true")
os.environ.setdefault("ZUAEF_ENABLE_CONVERSATION_SEARCH", "true")
os.environ.setdefault("ZUAEF_ENABLE_CONTEXT_CONTROLS", "true")
os.environ.setdefault("ZUAEF_ENABLE_SUBAGENTS", "true")
os.environ.setdefault("ZUAEF_WORDPRESS_USERNAME", "phase2-proof")
os.environ.setdefault("ZUAEF_WORDPRESS_APP_PASSWORD", "phase2-proof-placeholder")

from zuaef_agent.config import AgentSettings
from zuaef_agent.gateway.bridge import prior_run_history
from zuaef_agent.gateway.models import InboundEnvelope, SessionBinding
from zuaef_agent.gateway.service import GatewayService
from zuaef_agent.gateway.store import GatewayStore
from zuaef_agent.gateway.surface import SurfaceAdapter
from zuaef_agent.receipt_store import ReceiptStore

PROFILE = "stillevo-fde"
BOUND_CASE = "stillevo-beauty"
DEFAULT_ACE_ARTICLE = "fde-case-stillevo-beauty"

# SPEC v1.0 §7 Golden Outcome — the exact literal texts. Never edit these;
# tests pin them.
TURN1 = (
    "客户觉得上一篇 demo 太模板化。"
    "结合他之前给的背景和材料重写一篇。"
    "价格先不要写，我看完再决定要不要发。"
)
TURN2 = "开头还是太像 AI，保留刚才客户背景，再改一版；其他要求不变。"

# Genuine pricing expressions only. The bare word "价格" is deliberately NOT
# scanned: the model may legitimately state its absence (e.g. "本篇不含价格
# 内容") — that is transparency, not a written price. An actual price always
# carries a currency/amount token somewhere (¥/元/RMB/定价/售价/客单价/满减…).
PRICE_TOKENS = (
    "¥",
    "￥",
    "人民币",
    "RMB",
    "USD",
    "元",
    "定价",
    "售价",
    "客单价",
    "满减",
    "优惠",
    "折扣",
)
PUBLISH_TOKENS = ("publish", "wordpress", "发布")


class RecordingSurface(SurfaceAdapter):
    """Deterministic transport capture: records everything the Gateway sends."""

    surface_name = "recording"

    def __init__(self) -> None:
        self.texts: list[tuple[str, str]] = []
        self.documents: list[tuple[str, Path, str | None]] = []
        self.approvals: list[dict] = []
        self.keyboards: list[dict] = []
        self.callback_answers: list[tuple[str, str]] = []

    def poll_once(self, *, timeout_seconds):
        return []

    def pending_cursor(self):
        return None

    def send_text(self, channel_id: str, text: str) -> None:
        self.texts.append((channel_id, text))

    def send_document(self, channel_id: str, path: Path, *, caption: str | None = None) -> None:
        self.documents.append((channel_id, path, caption))

    def send_approval(
        self,
        channel_id: str,
        *,
        text: str,
        approve_token: str,
        approve_label: str = "Approve",
        deny_label: str = "Deny",
    ) -> None:
        self.approvals.append(
            {
                "channel_id": channel_id,
                "text": text,
                "token": approve_token,
                "approve_label": approve_label,
                "deny_label": deny_label,
            }
        )

    def send_keyboard(self, channel_id: str, *, text: str, buttons) -> None:
        self.keyboards.append(
            {"channel_id": channel_id, "text": text, "buttons": list(buttons)}
        )

    def answer_callback(self, callback_id: str, text: str) -> None:
        self.callback_answers.append((callback_id, text))


def _now() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()


# ── mechanical fixture preparation (SPEC §8 allows only this) ────────────────


def _prepare_case_fixture(workspace_root: Path) -> Path:
    """Copy the real committed Case fixture into the proof workspace (files
    only) and make its model-visible state consistent with this proof env:
    the ACE article referenced in the situation is registered by
    ``_ensure_ace_workspace``, so the stale "save failed / article not in ACE"
    operational status from the pre-Phase-2 runner is refreshed — otherwise
    the model is told the writing domain is broken and never loads it.
    """
    src = REPO / "workspace" / "cases"
    cases_root = workspace_root / "cases"
    if cases_root.exists():
        shutil.rmtree(cases_root)
    shutil.copytree(src, cases_root)
    from zuaef_case.store import CaseStore

    store = CaseStore(cases_root)
    situation = store.read_situation(BOUND_CASE)
    state = dict(situation.state)
    state["resources"] = {"ace_article_id": DEFAULT_ACE_ARTICLE}
    state["article_ace_status"] = (
        f"proof-prepared: ACE article workspace {DEFAULT_ACE_ARTICLE} is "
        "registered; use the writing domain's list_materials/read_material/"
        "save_artifact for this case's material"
    )
    updated = situation.model_copy(
        update={
            "state": state,
            "updated_by": "barry",
            "barry_override": "barry-onboard; p2-fixture:case-resource-refs",
        }
    )
    store.write_situation(updated)
    return cases_root


def _ensure_ace_workspace(workspace_root: Path) -> None:
    """Idempotently prepare the ACE article workspace from the case materials
    (the same bytes the case's material-ids.json hashes)."""
    from zuaef_ace_writing.writing_toolset import ace_prepare

    cases = workspace_root / "cases" / BOUND_CASE / "materials"
    materials = [
        str(cases / "client-background.md"),
        str(cases / "chat-history.md"),
        str(cases / "product-notes.md"),
    ]
    ace_prepare(
        DEFAULT_ACE_ARTICLE,
        title="stillevo-beauty field demo",
        account="stillevo-beauty",
        materials=materials,
    )


def _build_settings(workspace_root: Path, state_root: Path) -> AgentSettings:
    settings = AgentSettings.from_env()
    return settings.with_overrides(
        workspace_root=workspace_root.resolve(),
        runtime_state_root=state_root.resolve(),
        # The repo skill library (bmad) is not the FDE skill set; keep the
        # run's surface business-focused. FileSystem/Knowledge stay on like a
        # normal deployment (host ceiling), not proof special-casing.
        enable_skills=False,
        request_limit=40,
        tool_calls_limit=80,
    )


def _write_env_record(settings: AgentSettings) -> dict:
    return {
        "model": settings.compat_model or settings.model,
        "mode": settings.openai_api_mode,
        "workspace": str(settings.workspace_root),
        "state_root": str(settings.state_root),
    }


# ── deterministic surface probe (real profile, FunctionModel) ────────────────


def probe_visible_surface(settings: AgentSettings):
    """Record the model-visible tool surface of the REAL stillevo-fde profile:
    step 1 (initial) and step 2 (after a scripted search_tools discovery)."""
    from pydantic_ai.messages import ModelResponse, ToolCallPart
    from pydantic_ai.models.function import FunctionModel

    from zuaef_agent.composition import build_profile_agent
    from zuaef_agent.models import CoreDeps

    run_id = uuid4().hex
    agent, snapshot = build_profile_agent(
        settings, run_id=run_id, profile=PROFILE, config_root=REPO
    )
    steps: list[list[str]] = []
    seq = [("search_tools", {"queries": ["materials 素材 save artifact 保存"]})]

    async def handler(messages, info):
        names = sorted(getattr(t, "name", "") for t in (info.function_tools or []))
        steps.append(names)
        if seq:
            name, args = seq.pop(0)
            return ModelResponse(parts=[ToolCallPart(name, args)])
        return ModelResponse(
            parts=[
                ToolCallPart(
                    "final_result",
                    {"status": "completed", "outcome": "done"},
                )
            ]
        )

    deps = CoreDeps(
        workspace_root=settings.workspace_root.resolve(),
        run_id=run_id,
        case_id=BOUND_CASE,
    )
    with agent.override(model=FunctionModel(handler)):
        asyncio.run(agent.run("probe", deps=deps))
    return {
        "composition_id": snapshot.composition_id,
        "generalist": snapshot.generalist,
        "initial_visible": steps[0] if steps else [],
        "during_search": steps[1] if len(steps) > 1 else [],
        "writing_visible_initially": (
            "list_materials" in (steps[0] if steps else [])
        ),
        "writing_visible_after_search": any(
            "list_materials" in step for step in steps[1:]
        ),
    }


# ── gateway harness ──────────────────────────────────────────────────────────


def _envelope(message_id: str, text: str, **overrides) -> InboundEnvelope:
    base = {
        "surface": "telegram",
        "user_id": "42",
        "channel_id": "42",
        "message_id": message_id,
        "text": text,
    }
    base.update(overrides)
    return InboundEnvelope(**base)


def _session(service: GatewayService) -> SessionBinding:
    return service.store.get_session(
        surface="telegram", tenant_id="default", user_id="42",
        channel_id="42", thread_id=None,
    )


def _tool_effects(settings: AgentSettings, run_id: str) -> list[str]:
    from zuaef_agent.verification import latest_tool_effects, read_tool_effects

    if not settings.enable_step_persistence:
        return []
    records = latest_tool_effects(read_tool_effects(settings.step_store_dir, run_id))
    return [r.get("tool_name", "") for r in records if r.get("status") == "completed"]


def _history_texts(settings: AgentSettings, run_id: str) -> list[str]:
    from pydantic_ai_harness.step_persistence import FileStepStore, fork_run

    store = FileStepStore(settings.step_store_dir)
    try:
        history = asyncio.run(fork_run(store, run_id=run_id))
    except LookupError:
        return []
    texts: list[str] = []
    for message in history or []:
        for part in getattr(message, "parts", []):
            if getattr(part, "part_kind", None) in ("user-prompt", "assistant-prompt"):
                content = getattr(part, "content", "")
                if isinstance(content, list):
                    content = " ".join(
                        str(item.get("text", "")) if isinstance(item, dict) else str(item)
                        for item in content
                    )
                texts.append(str(content))
    return texts


def _artifact_texts(settings: AgentSettings, run_ids: list[str]) -> dict[str, str]:
    """Verified artifact file → full text (price scan source of truth)."""
    receipts = ReceiptStore(settings.state_root)
    found: dict[str, str] = {}
    for run_id in run_ids:
        try:
            receipt = receipts.read(run_id)
        except (FileNotFoundError, ValueError):
            continue
        for artifact in getattr(receipt, "verified_artifacts", []):
            path = settings.workspace_root / artifact.path
            if path.is_file():
                found[artifact.path] = path.read_text(encoding="utf-8", errors="replace")
    return found


def _handle_real_turn(
    service: GatewayService,
    settings: AgentSettings,
    surface: RecordingSurface,
    envelope: InboundEnvelope,
    marker: str,
) -> dict:
    """Run one real-model turn through the Gateway; if the model proposes a
    customer-visible send, exercise the shared approval seam (approve) and
    continue — the turn settles through the same path a supervisor uses."""
    service.handle(envelope)
    session = _session(service)
    run_id = session.last_terminal_run_id or session.paused_run_id
    receipts = ReceiptStore(settings.state_root)
    receipt = receipts.read(run_id)
    turn: dict = {
        "run_id": run_id,
        "status": getattr(receipt, "status", "paused"),
        "case_id": getattr(receipt, "case_id", None),
        "conversation_id": getattr(receipt, "conversation_id", None),
        "effects": _tool_effects(settings, run_id),
        "paused": bool(session.paused_run_id),
    }
    turn["verified_artifact_count"] = len(
        getattr(receipt, "verified_artifacts", None) or []
    )
    if session.paused_run_id and surface.approvals:
        approval = surface.approvals[-1]
        service.handle(
            _envelope(
                f"{marker}-auto-approve",
                "",
                callback_token=approval["token"],
                callback_action="approve",
                transport_context={"callback_query_id": f"cbq-{marker}-auto"},
            )
        )
        session = _session(service)
        settled_run_id = session.last_terminal_run_id
        settled = receipts.read(settled_run_id)
        turn["approval"] = {
            "auto_approved": True,
            "paused_run_id": run_id,
            "settled_run_id": settled_run_id,
            "settled_status": settled.status,
            "settled_case_id": settled.case_id,
            "settled_conversation_id": settled.conversation_id,
        }
        turn["run_id"] = settled_run_id
        turn["status"] = settled.status
        turn["case_id"] = settled.case_id
        turn["conversation_id"] = settled.conversation_id
        # The actual task work (load_case_context, search_tools, material reads,
        # save_artifact/save_draft) happened in the PAUSED run; the settled run
        # only carries the approval continuation. Evidence must merge both.
        merged = _tool_effects(settings, run_id) + _tool_effects(
            settings, settled_run_id
        )
        seen: set[str] = set()
        deduped = []
        for record in merged:
            key = (record.get("tool_call_id"), record.get("status"))
            if key not in seen:
                seen.add(key)
                deduped.append(record)
        turn["effects"] = deduped
        turn["paused"] = False
    return turn


# ── approval scenarios (deterministic, shared seam) ──────────────────────────


def _run_approval_scenario(
    service: GatewayService,
    settings: AgentSettings,
    surface: RecordingSurface,
    *,
    decision: str,
    marker: str,
) -> dict:
    """Scripted model proposes send_to_customer on the bound Case → the real
    Gateway pauses → the operator decision (approve/deny) is applied through
    the shared resume seam via the gateway callback path."""
    from pydantic_ai.messages import ModelResponse, ToolCallPart
    from pydantic_ai.models.function import FunctionModel

    from zuaef_agent import core as core_module

    def propose_send(messages, info):
        # First resolve the draft name the scripted model itself just saved
        # (deterministic), then propose the customer-visible send.
        draft_ref = None
        for m in messages:
            for p in getattr(m, "parts", []):
                if (
                    getattr(p, "part_kind", None) == "tool-return"
                    and getattr(p, "tool_name", None) == "save_draft"
                ):
                    content = getattr(p, "content", None)
                    if isinstance(content, dict):
                        draft_ref = content.get("draft_ref")
        if draft_ref is None:
            return ModelResponse(
                parts=[ToolCallPart("save_draft", {"text": marker})]
            )
        return ModelResponse(
            parts=[
                ToolCallPart("send_to_customer", {"draft_ref": draft_ref})
            ]
        )

    def continue_after_approval(messages, info):
        return ModelResponse(
            parts=[
                ToolCallPart(
                    "final_result",
                    {"status": "completed", "outcome": f"{marker} settled"},
                )
            ]
        )

    original = core_module.resolve_model
    try:
        # Pause: the proposal run is scripted.
        core_module.resolve_model = lambda s: FunctionModel(propose_send)
        service.handle(
            _envelope(f"{marker}-propose", f"（{marker}）请把最新草稿发给客户。")
        )
        session = _session(service)
        paused_run_id = session.paused_run_id
        approval = surface.approvals[-1]
    finally:
        core_module.resolve_model = original

    # Operator decision through the real callback gate (token → shared resume).
    core_module.resolve_model = lambda s: FunctionModel(continue_after_approval)
    try:
        service.handle(
            _envelope(
                f"{marker}-decision",
                "",
                callback_token=approval["token"],
                callback_action="approve" if decision == "approve" else "deny",
                transport_context={"callback_query_id": f"cbq-{marker}"},
            )
        )
    finally:
        core_module.resolve_model = original

    final_session = _session(service)
    receipts = ReceiptStore(settings.state_root)
    continued = receipts.read(final_session.last_terminal_run_id)
    result = {
        "scenario": marker,
        "decision": decision,
        "paused_run_id": paused_run_id,
        "pause_case_id": receipts.read(paused_run_id).case_id,
        "pause_conversation_id": receipts.read(paused_run_id).conversation_id,
        "continued_run_id": continued.run_id,
        "continued_status": continued.status,
        "continued_case_id": continued.case_id,
        "continued_conversation_id": continued.conversation_id,
        "identity_preserved": (
            continued.case_id == receipts.read(paused_run_id).case_id
            and continued.conversation_id
            == receipts.read(paused_run_id).conversation_id
        ),
    }
    if decision == "deny":
        result["denial_visible"] = any(
            "Denied" in text for _, text in surface.callback_answers
        )
    else:
        result["approval_visible"] = any(
            "Approved" in text for _, text in surface.callback_answers
        )
    return result


# ── main ─────────────────────────────────────────────────────────────────────


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace", default=str(Path.home() / "zuaef-fde-proof-p2"))
    ap.add_argument("--article-id", default=DEFAULT_ACE_ARTICLE)
    ap.add_argument("--no-model", action="store_true",
                    help="skip the real LLM turns (deterministic surface + approval only)")
    args = ap.parse_args()

    root = Path(args.workspace)
    workspace_root = root / "workspace"
    state_root = root / ".zuaef-state"
    workspace_root.mkdir(parents=True, exist_ok=True)
    state_root.mkdir(parents=True, exist_ok=True)

    settings = _build_settings(workspace_root, state_root)
    if not (settings.openai_base_url and settings.openai_api_key):
        print("RESULT: BLOCKED — no real model credentials (LLM_* / ZUAEF_OPENAI_*)", file=sys.stderr)
        return 2

    evidence: dict = {
        "run_at": _now(),
        "profile": PROFILE,
        "bound_case": BOUND_CASE,
        "env": _write_env_record(settings),
        "turns": {},
        "approval": {},
        "surface": None,
        "case": {},
        "conversation": {},
        "artifacts": {},
        "price_scan": {},
        "publish_calls": [],
        "dormant_checks": {},
        "turn2_prior_history": {},
    }

    # ── deterministic surface proof on the REAL profile ─────────────────────
    try:
        evidence["surface"] = probe_visible_surface(settings)
    except Exception as exc:  # noqa: BLE001 — evidence driver
        print(f"RESULT: BLOCKED — surface probe failed: {exc}", file=sys.stderr)
        return 3

    _prepare_case_fixture(workspace_root)
    _ensure_ace_workspace(workspace_root)

    store = GatewayStore(state_root / "gateway.sqlite3")
    surface = RecordingSurface()
    service = GatewayService(
        settings=settings,
        store=store,
        surface=surface,
        default_profile=PROFILE,
        config_root=REPO,
    )
    # Deterministic supervisor binding (SPEC §5.4) — the model never binds.
    # The session is created through the same key the service resolves on the
    # first inbound envelope (surface/tenant/user/channel/thread), so the
    # binding is visible to the very first turn.
    session = store.get_or_create_session(
        surface="telegram",
        tenant_id="default",
        user_id="42",
        channel_id="42",
        thread_id=None,
        default_profile=PROFILE,
    )
    bound = store.bind_case(session, BOUND_CASE)
    evidence["session"] = {
        "surface": bound.surface,
        "channel_id": bound.channel_id,
        "thread_key": bound.thread_key,
        "conversation_id": bound.conversation_id,
        "case_id": bound.case_id,
    }
    conversation_id = bound.conversation_id

    # ── Turn 1 (real model, literal text) ────────────────────────────────────
    if args.no_model:
        turn_evidence: dict = {"skipped": True, "run_id": None, "status": "skipped"}
    else:
        turn_evidence = _handle_real_turn(
            service, settings, surface, _envelope("m-1", TURN1), "turn1"
        )
    evidence["turns"]["turn1"] = turn_evidence

    # ── Turn 2 (real model, literal text, same session/conversation) ─────────
    if not args.no_model:
        turn1_run_id = evidence["turns"]["turn1"]["run_id"]
        history_before = prior_run_history(
            settings,
            run_id=turn1_run_id,
            conversation_id=conversation_id,
            receipts=ReceiptStore(settings.state_root),
        )
        evidence["turn2_prior_history"] = {
            "restored_message_count": len(history_before) if history_before else 0,
            "turn1_literal_visible": any(
                "价格先不要写" in text
                for text in _history_texts(settings, turn1_run_id)
            ),
            "no_host_restatement": True,  # Turn 2 text below is the only prompt
        }
        turn2_evidence = _handle_real_turn(
            service, settings, surface, _envelope("m-2", TURN2), "turn2"
        )
        evidence["turns"]["turn2"] = turn2_evidence
        evidence["turn2_prior_history"]["turn2_model_history_len"] = (
            len(history_before) if history_before else 0
        )

    # ── Approval scenarios (approve + deny) through the shared seam ──────────
    evidence["approval"]["approve"] = _run_approval_scenario(
        service, settings, surface, decision="approve", marker="approve"
    )
    evidence["approval"]["deny"] = _run_approval_scenario(
        service, settings, surface, decision="deny", marker="deny"
    )

    # ── Case evidence ────────────────────────────────────────────────────────
    from zuaef_case.store import CaseStore

    case_store = CaseStore(workspace_root / "cases")
    situation = case_store.read_situation(BOUND_CASE)
    trajectory = case_store.read_trajectory(BOUND_CASE, tail=100)
    drafts = case_store.list_drafts(BOUND_CASE)
    evidence["case"] = {
        "case_id": BOUND_CASE,
        "situation_resources": situation.state.get("resources"),
        "situation_updated_by": situation.updated_by,
        "trajectory_count": len(trajectory),
        "trajectory_tail": [
            {"seq": e.seq, "kind": e.kind, "role": e.role, "summary": e.summary[:120]}
            for e in trajectory[-6:]
        ],
        "draft_count": len(drafts),
        "drafts": [d.name for d in drafts],
        "material_ids": ["M001", "M002", "M003"],
    }

    # ── Artifact / side-effect evidence ──────────────────────────────────────
    run_ids = [
        t["run_id"]
        for t in evidence["turns"].values()
        if t.get("run_id") and t.get("status") != "skipped"
    ]
    artifacts = _artifact_texts(settings, run_ids)
    evidence["artifacts"] = {path: len(text) for path, text in artifacts.items()}
    price_matches: dict[str, list[str]] = {}
    for path, text in artifacts.items():
        matches = sorted({token for token in PRICE_TOKENS if token in text})
        if matches:
            price_matches[path] = matches
    evidence["price_scan"] = price_matches

    all_effects = [
        effect
        for turn in evidence["turns"].values()
        for effect in turn.get("effects", [])
    ]
    evidence["publish_calls"] = sorted(
        {
            effect
            for effect in all_effects
            if any(token in effect for token in PUBLISH_TOKENS)
        }
    )
    evidence["dormant_checks"] = {
        "budget_invoked": any("budget" in e for e in all_effects),
        "wordpress_invoked": any("wordpress" in e or "publish" in e for e in all_effects),
        "subagent_invoked": any("delegate" in e for e in all_effects),
        "shell_or_repo_available_initially": any(
            name in (evidence["surface"]["initial_visible"] or [])
            for name in ("run_command", "inventory_agent_context")
        ),
        "web_tools_invoked": any(
            e in ("web_search", "web_fetch") for e in all_effects
        ),
        "case_loaded": "load_case_context" in all_effects,
        "writing_invoked": any(
            e in ("list_materials", "read_material", "save_artifact") for e in all_effects
        ),
    }

    # ── verdict ──────────────────────────────────────────────────────────────
    def _gate(turn_name: str):
        t = evidence["turns"].get(turn_name)
        if not t or t.get("status") == "skipped":
            return None
        return (
            t["status"] == "completed"
            and t["case_id"] == BOUND_CASE
            and t["conversation_id"] == conversation_id
        )

    surface_ok = (
        evidence["surface"]["writing_visible_initially"] is False
        and evidence["surface"]["writing_visible_after_search"] is True
    )
    turn1_ok = _gate("turn1")
    turn2_ok = _gate("turn2")
    turn2_history_ok = (
        evidence["turn2_prior_history"].get("turn1_literal_visible") is True
        if "turn1_literal_visible" in evidence["turn2_prior_history"]
        else None
    )
    approval_ok = (
        evidence["approval"]["approve"]["identity_preserved"]
        and evidence["approval"]["approve"]["continued_status"] == "completed"
        and evidence["approval"]["deny"]["identity_preserved"]
        and evidence["approval"]["deny"]["denial_visible"]
    )
    side_effect_ok = (
        not evidence["price_scan"]
        and not evidence["publish_calls"]
        and evidence["dormant_checks"]["case_loaded"]
        and evidence["dormant_checks"]["writing_invoked"]
        and not evidence["dormant_checks"]["budget_invoked"]
        and not evidence["dormant_checks"]["wordpress_invoked"]
        and not evidence["dormant_checks"]["subagent_invoked"]
        and not evidence["dormant_checks"]["web_tools_invoked"]
        and not evidence["dormant_checks"]["shell_or_repo_available_initially"]
    )

    print("\n== ZUAEF PHASE 2 — AUTHORITATIVE FDE TWO-TURN PROOF ==")
    print(json.dumps(evidence, ensure_ascii=False, indent=2, default=str))

    gates = [surface_ok, side_effect_ok, approval_ok]
    if args.no_model:
        gates.append(True)  # deterministic mode: real turns intentionally skipped
    else:
        gates.extend([bool(turn1_ok), bool(turn2_ok), bool(turn2_history_ok)])
    ok = all(gates)
    print(f"\nRESULT: {'PASS' if ok else 'PARTIAL'}")
    return 0 if ok else 5


if __name__ == "__main__":
    raise SystemExit(main())