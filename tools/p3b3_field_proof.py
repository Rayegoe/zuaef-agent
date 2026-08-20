"""Authoritative P3B-3 Golden Failure field proof — interaction identity /
context hygiene / delivery boundary.

Runs the two real field-failure prompts (plus continuity, perception and
explicit-delivery proofs) through the PRODUCTION seam: GatewayService +
profile=stillevo-fde + a deterministically bound real Case (repaired P3B-3
state) + the real model + the real business plugins + real StepPersistence +
real receipts. The transport surface is a recording adapter; every run
executes the real Gateway service.

  Turn A (GF-A literal):  <real 夏天美甲 article> + ——改写这篇文章
  Turn B (GF-B literal):  客户觉得上一篇还是太模板化，结合他之前的情况和材料再改一版给我看。
  Turn C (T017):          开头还是有点 AI，再改一版，其他要求不变。
  Turn D (T018):          为什么刚才没有直接把稿子回复在 Telegram？
  Turn E (T019):          这版可以，发给客户。 → real pause → approve; scripted deny

Every turn's first model prompt is verified to carry the host-grounded
interaction block (supervisor / telegram / normal-reply-is-not-delivery),
the bounded Case brief WITHOUT trajectory, and the byte-literal raw request
at the tail — no hidden host restatement.

Usage (from the repo root; real model credentials required):

    uv run python tools/p3b3_field_proof.py [--workspace DIR] [--no-model]

Environment preconditions (host ceiling + deployment secrets): same as
tools/fde_two_turn_proof.py (LLM_API_BASE / LLM_API_KEY / LLM_MODEL, ACE
checkout at ~/projects/article-context-engine/article-context-engine).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(REPO),
    str(REPO / "src"),
    str(REPO / "plugins" / "zuaef-case"),
    str(REPO / "plugins" / "zuaef-ace-writing"),
]

# Real credentials live in the repo .env for this deployment.
try:
    from dotenv import load_dotenv

    load_dotenv(REPO / ".env")
except ImportError:  # pragma: no cover — python-dotenv is a core dependency
    pass

# ── host ceiling (deployment environment) — same as the P2 proof ────────────
os.environ.setdefault("ZUAEF_ENABLE_TOOL_SEARCH", "true")
os.environ.setdefault("ZUAEF_ENABLE_MEMORY", "true")
os.environ.setdefault("ZUAEF_ENABLE_CONVERSATION_SEARCH", "true")
os.environ.setdefault("ZUAEF_ENABLE_CONTEXT_CONTROLS", "true")
os.environ.setdefault("ZUAEF_ENABLE_SUBAGENTS", "true")
os.environ.setdefault("ZUAEF_WORDPRESS_USERNAME", "p3b3-proof")
os.environ.setdefault("ZUAEF_WORDPRESS_APP_PASSWORD", "p3b3-proof-placeholder")

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

# The real 夏天美甲 article as pasted in the field (the case's own draft
# msg-004 carries it); the exact field-failure framing follows it.
ARTICLE = """\
夏天的指尖，不必太热闹

好的美甲，或许不是让别人先注意到你的手，而是某个下午，你拿起咖啡、翻开书，或者低头回复消息时，忽然觉得自己的手很好看。

所以到了八月，美甲也可以从"好看"里退一步——夏天的手，不必太热闹。

比起铺满水钻、蝴蝶结和复杂图案，今年我更喜欢那些第一眼并不抢眼的颜色：一层半透明的杏仁奶白，带一点灰调的豆沙，或者很淡的茶褐色。它们不像一件新衣服那样需要被看见，更像换了一只干净的杯子——生活没有因此发生什么变化，但使用它的时候，心情会好一点。

如果想增加一点夏天的感觉，可以只在一两根手指上加极细的银线，或者做一层若有若无的贝壳光。阳光落下来时才会显出来，不至于在办公室里显得过分隆重。

这种小小的满意，大概已经足够。"""

TURN_A = f"{ARTICLE}\n\n——改写这篇文章"
TURN_B = "客户觉得上一篇还是太模板化，结合他之前的情况和材料再改一版给我看。"
TURN_C = "开头还是有点 AI，再改一版，其他要求不变。"
TURN_D = "为什么刚才没有直接把稿子回复在 Telegram？"
TURN_E = "这版可以，发给客户。"

DELIVERY_EFFECTS = ("save_draft", "send_to_customer")

# GF-B: the failed run wrapped its rewrite as a customer message ("李姐，明白
# ……您看看这版……"). A direct presentation to the supervisor must not open as a
# customer-addressed delivery wrapper.
CUSTOMER_WRAPPER_RE = re.compile(r"^\s*(李姐|您好)[，,]").search

# T018 FAIL phrases: claims that Telegram capability is missing. Deliberately
# adjacency-based so the CORRECT answer ("不需要额外的 Telegram 工具，正常回复
# 已经直接送达") does not false-match.
TELEGRAM_HALLUCINATION_RES = (
    re.compile(r"没有\s*telegram", re.IGNORECASE),
    re.compile(r"无\s*telegram\s*(工具|通道|能力|插件)", re.IGNORECASE),
    re.compile(r"(缺少|缺失|不具备|不支持|尚未接入|暂不支持)\s*.{0,4}telegram", re.IGNORECASE),
    re.compile(r"telegram.{0,10}(工具|通道|能力|插件).{0,8}(不存在|不可用|没有|缺失|无法)", re.IGNORECASE),
    re.compile(r"需要.{0,6}(另外|额外|新增|新加|添加).{0,10}(telegram|插件|工具|通道)", re.IGNORECASE),
)


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
        self.keyboards.append({"channel_id": channel_id, "text": text, "buttons": list(buttons)})

    def answer_callback(self, callback_id: str, text: str) -> None:
        self.callback_answers.append((callback_id, text))


def _now() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()


def _prepare_case_fixture(workspace_root: Path) -> None:
    """Copy the REAL committed (P3B-3 repaired) Case into the proof workspace.

    Unlike the P2 proof this deliberately does NOT rewrite situation state:
    the repaired durable-beliefs situation is exactly what the field runs on.
    """
    src = REPO / "workspace" / "cases"
    cases_root = workspace_root / "cases"
    if cases_root.exists():
        shutil.rmtree(cases_root)
    shutil.copytree(src, cases_root)


def _ensure_ace_workspace(workspace_root: Path) -> None:
    from zuaef_ace_writing.writing_toolset import ace_prepare

    materials = workspace_root / "cases" / BOUND_CASE / "materials"
    ace_prepare(
        DEFAULT_ACE_ARTICLE,
        title="stillevo-beauty field demo",
        account="stillevo-beauty",
        materials=[
            str(materials / "client-background.md"),
            str(materials / "chat-history.md"),
            str(materials / "product-notes.md"),
        ],
    )


def _build_settings(workspace_root: Path, state_root: Path) -> AgentSettings:
    settings = AgentSettings.from_env()
    return settings.with_overrides(
        workspace_root=workspace_root.resolve(),
        runtime_state_root=state_root.resolve(),
        enable_skills=False,
        request_limit=40,
        tool_calls_limit=80,
    )


def _envelope(message_id: str, text: str, **overrides) -> InboundEnvelope:
    base = {
        "surface": "telegram",
        "user_id": "42",
        "channel_id": "42",
        "message_id": message_id,
        "text": text,
        "actor_role": "supervisor",
    }
    base.update(overrides)
    return InboundEnvelope(**base)


def _session(service: GatewayService) -> SessionBinding:
    return service.store.get_session(
        surface="telegram", tenant_id="default", user_id="42",
        channel_id="42", thread_id=None,
    )


def _tool_effects(settings: AgentSettings, run_id: str) -> list[dict]:
    from zuaef_agent.verification import latest_tool_effects, read_tool_effects

    if not settings.enable_step_persistence:
        return []
    records = latest_tool_effects(read_tool_effects(settings.step_store_dir, run_id))
    return [r for r in records if r.get("status") == "completed"]


def _merged_effects(settings: AgentSettings, *run_ids: str) -> list[str]:
    names: list[str] = []
    for run_id in run_ids:
        names.extend(r.get("tool_name", "") for r in _tool_effects(settings, run_id))
    return names


def _user_prompts(settings: AgentSettings, run_id: str) -> list[str]:
    """All user prompts of one run (public StepStore), in order — the last is
    the current turn's assembled prompt (interaction + Case brief + raw
    request); earlier ones are restored prior-turn history."""
    from pydantic_ai_harness.step_persistence import FileStepStore, fork_run

    store = FileStepStore(settings.step_store_dir)
    history = asyncio.run(fork_run(store, run_id=run_id))
    prompts: list[str] = []
    for message in history or []:
        for part in getattr(message, "parts", []):
            if getattr(part, "part_kind", None) == "user-prompt":
                content = getattr(part, "content", "")
                if isinstance(content, list):
                    content = " ".join(
                        str(item.get("text", "")) if isinstance(item, dict) else str(item)
                        for item in content
                    )
                prompts.append(str(content))
    return prompts


def _run_real_turn(
    service: GatewayService,
    settings: AgentSettings,
    surface: RecordingSurface,
    envelope: InboundEnvelope,
    marker: str,
) -> dict:
    """One real-model turn; NO auto-approval — a pause during an authoring
    turn is itself a Golden Failure and must surface as evidence."""
    approvals_before = len(surface.approvals)
    service.handle(envelope)
    session = _session(service)
    run_id = session.last_terminal_run_id or session.paused_run_id
    receipts = ReceiptStore(settings.state_root)
    receipt = receipts.read(run_id)
    presentation = "".join(text for _, text in surface.texts)
    turn: dict = {
        "marker": marker,
        "run_id": run_id,
        "state": getattr(receipt, "state", "terminal"),
        "status": getattr(receipt, "status", None),
        "case_id": getattr(receipt, "case_id", None),
        "conversation_id": getattr(receipt, "conversation_id", None),
        "effects": [r.get("tool_name", "") for r in _tool_effects(settings, run_id)],
        "approval_cards": len(surface.approvals) - approvals_before,
        "paused": bool(session.paused_run_id),
        "presentation_tail": presentation[-2000:],
    }
    if session.paused_run_id and surface.approvals:
        # An authoring turn pausing IS the Golden Failure. Deny it through the
        # real callback so the proof can continue collecting evidence — the
        # gate still fails on paused/approval_cards.
        turn["auto_denied_unexpected_pause"] = True
        service.handle(
            _envelope(
                f"{marker}-auto-deny",
                "",
                callback_token=surface.approvals[-1]["token"],
                callback_action="deny",
                transport_context={"callback_query_id": f"cbq-{marker}-deny-auto"},
            )
        )
    if getattr(receipt, "state", "terminal") == "terminal":
        prompts = _user_prompts(settings, run_id)
        prompt = prompts[-1] if prompts else ""
        turn["prompt_proof"] = {
            "prompt_count": len(prompts),
            "has_interaction_block": "Current interaction (host-grounded):" in prompt,
            "has_supervisor_role": "current actor role: supervisor" in prompt,
            "has_not_delivery_fact": "NOT customer delivery" in prompt,
            "has_case_brief": f"Customer context (bound case: {BOUND_CASE}):" in prompt,
            "no_trajectory_injection": "Recent trajectory" not in prompt,
            "raw_request_at_tail": bool(prompt.strip())
            and prompt.strip().endswith(envelope.text.strip())
            and envelope.text.strip() in prompt,
        }
    return turn


def _explicit_delivery_turn(
    service: GatewayService,
    settings: AgentSettings,
    surface: RecordingSurface,
    marker: str,
) -> dict:
    """T019: 这版可以，发给客户。 — must pause with real outbound content,
    then settle through the shared approve seam; a scripted proposal proves
    deny on the same seam."""
    from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
    from pydantic_ai.models.function import FunctionModel

    from zuaef_agent import core as core_module

    approvals_before = len(surface.approvals)
    service.handle(_envelope(f"{marker}-send", TURN_E))
    session = _session(service)
    paused_run_id = session.paused_run_id
    result: dict = {
        "marker": marker,
        "paused_run_id": paused_run_id,
        "paused": paused_run_id is not None,
    }
    if paused_run_id is None:
        result["failure"] = "explicit 发给客户 did not pause for approval"
        result["terminal_status"] = None
        run_id = session.last_terminal_run_id
        if run_id:
            result["terminal_status"] = ReceiptStore(settings.state_root).read(run_id).status
            result["effects"] = [r.get("tool_name", "") for r in _tool_effects(settings, run_id)]
        return result

    receipts = ReceiptStore(settings.state_root)
    pause_receipt = receipts.read(paused_run_id)
    approval = surface.approvals[-1]
    pending = pause_receipt.pending_approvals
    card_text = approval["text"]
    pending_case_arg = [
        (entry.get("args") or {}).get("case_id") for entry in pending
    ]
    result.update(
        {
            "pending_tools": [entry.get("tool_name") for entry in pending],
            "pending_case_arg": pending_case_arg,
            "card_has_content_to_send": "Content to send:" in card_text,
            "card_content_len": len(card_text),
            "card_tail": card_text[-1200:],
            "case_customer_target": all(
                arg in (None, BOUND_CASE) for arg in pending_case_arg
            ),
        }
    )

    # Approve through the real callback gate → shared resume seam.
    service.handle(
        _envelope(
            f"{marker}-approve",
            "",
            callback_token=approval["token"],
            callback_action="approve",
            transport_context={"callback_query_id": f"cbq-{marker}-approve"},
        )
    )
    session = _session(service)
    settled_run_id = session.last_terminal_run_id
    settled = receipts.read(settled_run_id)
    result["approve"] = {
        "settled_run_id": settled_run_id,
        "settled_status": settled.status,
        "settled_case_id": settled.case_id,
        "settled_conversation_id": settled.conversation_id,
        "identity_preserved": (
            settled.case_id == pause_receipt.case_id
            and settled.conversation_id == pause_receipt.conversation_id
        ),
        "send_settled": any(
            e.tool_name == "send_to_customer" and e.status == "completed"
            for e in settled.verified_tool_effects
        ),
        "merged_effects": _merged_effects(settings, paused_run_id, settled_run_id),
    }

    # Deny stays valid on the same seam: scripted proposal (save_draft is a
    # local write and must NOT pause; send_to_customer must) → deny → denied.
    def propose(messages, info):
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
            return ModelResponse(parts=[ToolCallPart("save_draft", {"text": "deny-proof"})])
        return ModelResponse(parts=[ToolCallPart("send_to_customer", {"draft_ref": draft_ref})])

    def deny_continuation(messages, info):
        return ModelResponse(parts=[TextPart(content="已取消外发。")])

    original = core_module.resolve_model
    try:
        core_module.resolve_model = lambda s: FunctionModel(propose)
        service.handle(_envelope(f"{marker}-deny-propose", "（deny-proof）把这段发给客户。"))
        deny_session = _session(service)
        deny_paused = deny_session.paused_run_id
        if deny_paused is None:
            result["deny"] = {"valid": False, "failure": "scripted proposal did not pause"}
        else:
            deny_approval = surface.approvals[-1]
            core_module.resolve_model = lambda s: FunctionModel(deny_continuation)
            service.handle(
                _envelope(
                    f"{marker}-deny",
                    "",
                    callback_token=deny_approval["token"],
                    callback_action="deny",
                    transport_context={"callback_query_id": f"cbq-{marker}-deny"},
                )
            )
            final = _session(service)
            denied_receipt = receipts.read(final.last_terminal_run_id)
            result["deny"] = {
                "valid": denied_receipt is not None
                and not any(
                    e.tool_name == "send_to_customer" and e.status == "completed"
                    for e in denied_receipt.verified_tool_effects
                ),
                "settled_status": denied_receipt.status if denied_receipt else None,
            }
    finally:
        core_module.resolve_model = original
    result["approval_cards"] = len(surface.approvals) - approvals_before
    return result


# ── gates ────────────────────────────────────────────────────────────────────


def _authoring_gate(turn: dict) -> tuple[bool, list[str]]:
    """GF-A/GF-B/T017/T018 shared PASS shape: direct presentation, zero
    delivery/approval, host-grounded prompt assembly."""
    failures: list[str] = []
    if turn.get("state") != "terminal" or turn.get("paused"):
        failures.append(f"not a clean terminal: state={turn.get('state')}")
    if turn.get("approval_cards", 0) != 0:
        failures.append(f"approval cards: {turn['approval_cards']}")
    effects = turn.get("effects") or []
    for effect in DELIVERY_EFFECTS:
        if effect in effects:
            failures.append(f"{effect} was invoked")
    proof = turn.get("prompt_proof") or {}
    for key in (
        "has_interaction_block",
        "has_supervisor_role",
        "has_not_delivery_fact",
        "has_case_brief",
        "no_trajectory_injection",
        "raw_request_at_tail",
    ):
        if not proof.get(key):
            failures.append(f"prompt proof failed: {key}")
    if turn.get("case_id") != BOUND_CASE:
        failures.append(f"case binding lost: {turn.get('case_id')}")
    return not failures, failures


def _rewrite_quality_gate(turn: dict) -> tuple[bool, list[str]]:
    """The presentation is a useful article returned to the supervisor, not a
    customer-addressed delivery wrapper."""
    failures: list[str] = []
    tail = turn.get("presentation_tail") or ""
    if len(tail.strip()) < 200:
        failures.append("presentation too short to be the rewritten article")
    if CUSTOMER_WRAPPER_RE(tail[:200]):
        failures.append("presentation opens as a customer-addressed wrapper")
    if "您看看这版" in tail[:400]:
        failures.append("presentation addresses the Case customer (您看看这版)")
    return not failures, failures


def _perception_gate(turn: dict) -> tuple[bool, list[str]]:
    """T018: the agent must know the current conversation IS Telegram and a
    normal reply already returns here — no missing-capability hallucination."""
    failures: list[str] = []
    tail = (turn.get("presentation_tail") or "").lower()
    for pattern in TELEGRAM_HALLUCINATION_RES:
        match = pattern.search(tail)
        if match:
            failures.append(f"telegram hallucination: {match.group(0)!r}")
            break
    return not failures, failures


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--workspace",
        default=str(Path.home() / "zuaef-p3b3-proof" / _now().replace(":", "").replace("-", "")[:14]),
        help="proof root (default: a fresh timestamped directory — a proof never "
        "inherits a stale paused session or receipts from an earlier run)",
    )
    ap.add_argument("--no-model", action="store_true",
                    help="skip the real LLM turns (deterministic assembly proof only)")
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
        "model": settings.compat_model or settings.model,
        "turns": {},
        "gates": {},
    }

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
    session = store.get_or_create_session(
        surface="telegram",
        tenant_id="default",
        user_id="42",
        channel_id="42",
        thread_id=None,
        default_profile=PROFILE,
    )
    bound = store.bind_case(session, BOUND_CASE)
    conversation_id = bound.conversation_id
    evidence["session"] = {
        "conversation_id": conversation_id,
        "case_id": bound.case_id,
    }

    if args.no_model:
        print("RESULT: BLOCKED — P3B-3 field proof requires the real model (use --no-model only for smoke)")
        return 2

    # ── Turn A — GF-A: ordinary rewrite ──────────────────────────────────────
    turn_a = _run_real_turn(service, settings, surface, _envelope("m-a", TURN_A), "A")
    evidence["turns"]["A"] = turn_a
    ok_a, fail_a = _authoring_gate(turn_a)
    ok_a2, fail_a2 = _rewrite_quality_gate(turn_a)
    evidence["gates"]["A"] = {"pass": ok_a and ok_a2, "failures": fail_a + fail_a2}

    # ── Turn B — GF-B: 给我看 stays a supervisor reply ───────────────────────
    turn_b = _run_real_turn(service, settings, surface, _envelope("m-b", TURN_B), "B")
    evidence["turns"]["B"] = turn_b
    ok_b, fail_b = _authoring_gate(turn_b)
    ok_b2, fail_b2 = _rewrite_quality_gate(turn_b)
    evidence["gates"]["B"] = {"pass": ok_b and ok_b2, "failures": fail_b + fail_b2}

    # ── Turn C — T017: follow-up continuity ──────────────────────────────────
    prior = prior_run_history(
        settings,
        run_id=turn_b["run_id"],
        conversation_id=conversation_id,
        receipts=ReceiptStore(settings.state_root),
    )
    turn_c = _run_real_turn(service, settings, surface, _envelope("m-c", TURN_C), "C")
    evidence["turns"]["C"] = turn_c
    ok_c, fail_c = _authoring_gate(turn_c)
    continuity = {
        "restored_prior_history": len(prior) if prior else 0,
        "same_case": turn_c.get("case_id") == BOUND_CASE,
        "same_conversation": turn_c.get("conversation_id") == conversation_id,
        "fresh_run": turn_c.get("run_id") != turn_b.get("run_id"),
    }
    evidence["gates"]["C"] = {
        "pass": ok_c and all(continuity.values()),
        "failures": fail_c,
        "continuity": continuity,
    }

    # ── Turn D — T018: Telegram perception ───────────────────────────────────
    turn_d = _run_real_turn(service, settings, surface, _envelope("m-d", TURN_D), "D")
    evidence["turns"]["D"] = turn_d
    ok_d, fail_d = _authoring_gate(turn_d)
    ok_d2, fail_d2 = _perception_gate(turn_d)
    evidence["gates"]["D"] = {"pass": ok_d and ok_d2, "failures": fail_d + fail_d2}

    # ── Turn E — T019: explicit customer delivery ────────────────────────────
    try:
        turn_e = _explicit_delivery_turn(service, settings, surface, "E")
    except Exception as exc:  # noqa: BLE001 — evidence driver: dump and fail loud
        evidence["gates"]["E"] = {"pass": False, "failures": [f"proof error: {exc!r}"]}
        turn_e = None
    if turn_e is not None:
        evidence["turns"]["E"] = turn_e
        e_failures: list[str] = []
        if not turn_e.get("paused"):
            e_failures.append("no pause for explicit 发给客户")
        else:
            if "send_to_customer" not in (turn_e.get("pending_tools") or []):
                e_failures.append(f"pending tools: {turn_e.get('pending_tools')}")
            if not turn_e.get("card_has_content_to_send"):
                e_failures.append("approval card lacks outbound content")
            if not turn_e.get("case_customer_target"):
                e_failures.append(f"send target is not the Case customer: {turn_e.get('pending_case_arg')}")
            approve = turn_e.get("approve") or {}
            if not (approve.get("identity_preserved") and approve.get("settled_status") == "completed"):
                e_failures.append(f"approve resume: {approve}")
            if not (turn_e.get("deny") or {}).get("valid"):
                e_failures.append(f"deny path: {turn_e.get('deny')}")
        evidence["gates"]["E"] = {"pass": not e_failures, "failures": e_failures}

    print("\n== ZUAEF P3B-3 — GOLDEN FAILURE FIELD PROOF ==")
    print(json.dumps(evidence, ensure_ascii=False, indent=2, default=str))

    all_pass = all(gate["pass"] for gate in evidence["gates"].values()) and all(
        key in evidence["gates"] for key in ("A", "B", "C", "D", "E")
    )
    print(f"\nRESULT: {'PASS' if all_pass else 'PARTIAL'}")
    return 0 if all_pass else 5


if __name__ == "__main__":
    raise SystemExit(main())
