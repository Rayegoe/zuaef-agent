"""FDE Decision Loop — event-seeded case run (SPEC v0.3 §7.1).

STATUS: HISTORICAL / DIAGNOSTIC — NOT the product authority (SPEC v1.0 §9.1).

Phase 2 moved the real FDE product proof onto the production seam:
`tools/fde_two_turn_proof.py` now runs GatewayService + `profile="stillevo-fde"`
+ a deterministically bound real Case + the real model + real StepPersistence,
with both literal golden turns and the shared approval seam. This CLI runner
(surface = console) kept its custom composition (conversation_id == case_id =
case_directory memory) from the pre-Phase-2 Field Interface contract. It is
retained here as historical/diagnostic field evidence only. It is NOT the
product authority — do not maintain or extend two FDE architectures. New FDE
proof work goes through the Gateway/stillevo-fde seam above.

The FDE agent is the product; writing/receipts are its capabilities and
evidence. This runner is the loop itself:

    inbound event (role-tagged, mechanical binding)
        -> host appends event to trajectory
        -> seed context projection (goal + situation + policy + trajectory
           tail + event) — deterministic, no LLM guessing
        -> FDE agent (case tools + field-material tools + article capability)
           runs Observe -> Diagnose -> Decide -> Act -> Verify -> Continue
        -> send_to_customer pauses for human approval (PausedRun -> resume)
        -> terminal -> host settles, Field Interface performs the send

Cross-run continuity: conversation_id == case_id; the case directory
(case.md / situation.json / trajectory.jsonl / drafts/) is the memory —
never a second message-history database.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(REPO),
    str(REPO / "examples"),
    str(REPO / "src"),
    str(REPO / "plugins" / "zuaef-case"),
    str(REPO / "plugins" / "zuaef-ace-writing"),
]

from pydantic_ai import FunctionToolset, RunContext
from zuaef_case.models import CaseDoc, Situation, TrajectoryEntry
from zuaef_case.store import CaseStore
from zuaef_case.toolset import build_case_toolset

from examples.host_runner import json_default
from examples.writing_toolset import DEFAULT_ACE_ROOT, ace_prepare, save_artifact_impl
from zuaef_agent.config import AgentSettings
from zuaef_agent.core import build_agent
from zuaef_agent.models import CoreDeps
from zuaef_agent.runtime import PausedRun, TerminalRun, decide, execute_run

CASES_ROOT = REPO / "workspace" / "cases"
DEFAULT_CASE_ID = "stillevo-beauty"
FDE_ARTICLE = "fde-case-stillevo-beauty"  # ACE workspace for case materials
MATERIAL_READ_LIMIT = 12_000  # bounded read: never the whole corpus

FDE_LOOP_INSTRUCTIONS = """\
You are the ZUAEF FDE agent deployed to this business case. You are not a
per-message reply generator: the case GOAL drives every run.

Loop discipline (one run per inbound event):
1. OBSERVE — load_case_context first: goal, situation, policy, trajectory.
2. DIAGNOSE — decide what this event means for the goal. If you now believe
   a substantive fact, update_situation with evidence_ids (e.g. the event
   seq or an artifact ref); never assert a fact you cannot source.
3. DECIDE — record_case_step (kind=decision) naming the chosen move and why.
4. ACT — use the capability tools:
     - read_case_material / list_case_materials: field materials ONLY (each
       returns the real M id and source_ref);
     - save_article: write the article with its ledgers (see rules below);
     - save_draft: hold customer-facing text (nothing is sent by saving);
     - send_to_customer: the ONLY path to the customer; it always pauses for
       human approval.
5. VERIFY — record_case_step (kind=action) with refs to the artifact/draft.
6. CONTINUE/STOP — finish with a RunSummary stating what changed in the
   situation and what the next step is.

save_article ledgers:
- sources: one row per material used, e.g.
  {"id":"S1","kind":"material","label":"<name>","material_ids":["M001"],
   "source_ref":"<ref>","sha256":"<hash>","rights":"<rights>"} — use the
  values returned by read_case_material, never invent M ids.
- claims: every claim MUST carry "status":"resolved" and source_ids that
  reference ONLY the S ids you passed. ACE rejects unresolved claims.

Hard rules:
- Facts, numbers, quotes and product claims come ONLY from the case
  materials. Never invent customer facts, prices, guarantees, cases,
  sales figures, efficacy claims or commitments.
- Policy overrides (policy.md) outrank everything except a Barry override.
- The customer sees nothing except through an approved send_to_customer.
- RunSummary discipline: reference ONLY verifiable refs —
  artifacts=["artifacts/<run_id>/final.md"] for ACE-saved articles, and
  tool-effect:<call_id> for executed tools. Case drafts (drafts/msg-*.md)
  are case files, NOT summary artifacts — name them in trajectory refs
  only. Open questions belong in the situation (update_situation
  open_questions), never in summary unknowns.
"""


# --- case fixture (host-authored onboarding, deterministic) ----------------------


def setup_case(case_dir: Path, store: CaseStore, case_id: str) -> dict[str, str]:
    """Create the case fixture once: case.md, policy, situation, materials,
    ACE workspace ingest -> filename-to-M-id map. Idempotent per file."""
    directory = store.case_dir(case_id)
    directory.mkdir(parents=True, exist_ok=True)

    case_path = directory / "case.md"
    if not case_path.exists():
        store.create_case(
            CaseDoc(
                case_id=case_id,
                goal=(
                    "把云朵美妆（平价美妆电商，李姐主理）从“方案讨论”推进到 Pilot："
                    "本周完成一次 bounded live demo——用客户自有素材现场写一篇"
                    "公众号文章，外发前经 Barry 审批。"
                ),
                status="active",
                stakeholders={"customer": "wechat-li", "barry": "supervisor-chat"},
                customer_chat_id="wechat-li",
                supervisor_chat_id="supervisor-chat",
                notes=(
                    "客户背景、预算与承诺记录见 materials/chat-history.md；"
                    "决策人：李姐（创始人）。"
                ),
            )
        )

    policy_path = directory / "policy.md"
    if not policy_path.exists():
        policy_path.write_text(
            "# Case Policy — stillevo-beauty\n"
            "- 外发：任何客户可见内容必须先 save_draft，再 send_to_customer（人工审批）。\n"
            "- 价格/折扣/承诺：一律不写；客户问价只能答复“需要确认后答复”，由 Barry 批准后外发。\n"
            "- 事实边界：只使用 materials/ 中客户提供的素材；数字、引语、产品表述必须来自素材。\n"
            "- 不编造：销量、成分功效、用户评价数量、案例、人名。\n"
            "- demo 目标：证明“用客户素材现场成稿”，文章要能直接给老板看，但外发必须审批。\n",
            encoding="utf-8",
        )

    situation_path = directory / "situation.json"
    if not situation_path.exists():
        store.write_situation(
            Situation(
                case_id=case_id,
                updated_by="barry-onboard",
                state={
                    "customer": {
                        "company": "云朵美妆",
                        "contact": "李姐",
                        "stage": "方案讨论",
                    },
                    "budget": {
                        "monthly_range": "3000-5000 元（客户原话，见 chat-history）"
                    },
                    "demo": {
                        "status": "not_started",
                        "promise": "本周内给一篇现场写的 demo（我方承诺，见 chat-history）",
                    },
                },
                open_questions=["demo 文章的用途：公众号还是朋友圈？"],
                evidence_ids=[],
                barry_override="barry-onboard",
            )
        )

    materials = {
        "client-background.md": (
            "# 客户背景（客户提供）\n\n"
            "云朵美妆：平价美妆电商，客单价 50-100 元，主打眼影与唇釉。\n"
            "创始人李姐，团队 8 人。公众号现有粉丝约 2 万，最近阅读量下滑"
            "（客户原话：“以前一篇还能有几百阅读，现在几十”）。\n"
            "找过代运营，效果不好（客户原话：“发的东西我自己都不想转”）。\n"
        ),
        "chat-history.md": (
            "# 聊天记录摘录（客户原话）\n\n"
            "- “公众号现在没人看了。”\n"
            "- “之前找的代运营，发的东西我自己都不想转。”\n"
            "- “预算一个月三四千吧，先看效果。”\n"
            "- “你们能先写一篇给我看看吗——就用我们自己的东西写，别编。”\n"
            "- 我方承诺：“下周给你看一篇用你们素材写的 demo，你先看效果再决定。”\n"
        ),
        "product-notes.md": (
            "# 产品资料（客户提供）\n\n"
            "云朵盘眼影：六色，主打色“豆沙奶咖”。\n"
            "两条用户评价（客户提供原话）：\n"
            "- “显色度刚好，通勤能用。”\n"
            "- “壳子好看，自留了一盘。”\n"
            "活动：三八节满 99 减 20（客户原话）。\n"
        ),
    }
    material_paths: list[Path] = []
    for name, text in materials.items():
        path = directory / "materials" / name
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        material_paths.append(path)

    ace_prepare(
        FDE_ARTICLE,
        title=f"FDE case {case_id}",
        materials=[str(p) for p in material_paths],
        ace_root=DEFAULT_ACE_ROOT,
    )
    ids = _material_id_map(material_paths)
    ids_path = directory / "material-ids.json"
    if not ids_path.exists():
        ids_path.write_text(
            json.dumps(ids, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return ids


def _material_id_map(paths: list[Path]) -> dict[str, dict[str, str]]:
    """filename -> {material_id, source_ref} from the ACE workspace index."""
    index = DEFAULT_ACE_ROOT / "workspaces" / FDE_ARTICLE / "materials.jsonl"
    rows = [
        json.loads(line)
        for line in index.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    by_sha = {row["sha256"]: row for row in rows}
    mapping: dict[str, dict[str, str]] = {}
    for path in paths:
        import hashlib

        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        row = by_sha.get(sha)
        if row is None:
            raise RuntimeError(f"material not in ACE index: {path.name}")
        mapping[path.name] = {
            "material_id": str(row["id"]),
            "source_ref": f"cases/{path.parent.parent.name}/materials/{path.name}",
            "sha256": sha,
            "rights": "user-provided",
        }
    return mapping


# --- FDE field-material + article capability tools -------------------------------


def build_fde_toolset(
    store: CaseStore,
    case_id: str,
    material_ids: dict[str, dict[str, str]],
) -> FunctionToolset[CoreDeps]:
    toolset: FunctionToolset[CoreDeps] = FunctionToolset()

    @toolset.tool
    def list_case_materials(ctx: RunContext[CoreDeps]) -> list[dict]:
        """List the case's field materials (names + real M ids), bounded."""
        return [{"name": name, **meta} for name, meta in sorted(material_ids.items())]

    @toolset.tool
    def read_case_material(ctx: RunContext[CoreDeps], name: str) -> dict:
        """Read ONE field material (bounded). Returns the real M id and
        source_ref so save_article ledgers can reference it."""
        meta = material_ids.get(name)
        if meta is None:
            raise FileNotFoundError(
                f"unknown material {name!r}; use list_case_materials"
            )
        path = store.case_dir(case_id) / "materials" / name
        text = path.read_text(encoding="utf-8")
        if len(text) > MATERIAL_READ_LIMIT:
            text = text[:MATERIAL_READ_LIMIT] + "\n…(truncated)"
        return {"name": name, **meta, "text": text}

    @toolset.tool
    def save_article(
        ctx: RunContext[CoreDeps],
        article_id: str,
        final_markdown: str,
        claims: list[dict] | None = None,
        sources: list[dict] | None = None,
    ) -> dict:
        """Write the article through ACE: claims/sources are validated
        against the real ingested materials (never M00x placeholders)."""
        result, _snapshot = save_artifact_impl(
            article_id,
            final_markdown,
            claims or [],
            sources or [],
            snapshot_dir=ctx.deps.workspace_root / "artifacts" / ctx.deps.run_id,
            run_id=ctx.deps.run_id,
            ace_root=DEFAULT_ACE_ROOT,
        )
        return result

    return toolset


# --- seed projection (deterministic, no LLM guessing) ----------------------------


def seed_case_context(
    store: CaseStore, case_id: str, event: dict, *, tail: int = 20
) -> str:
    doc = store.load_case(case_id)
    situation = store.read_situation(case_id)
    trajectory = store.read_trajectory(case_id, tail=tail)
    policy_path = store.case_dir(case_id) / "policy.md"
    policy = (
        policy_path.read_text(encoding="utf-8")[:4000] if policy_path.is_file() else ""
    )
    return (
        f"## Case: {case_id}\n\n"
        f"### goal\n{doc.goal}\n\n"
        f"### stakeholders\n{json.dumps(doc.stakeholders, ensure_ascii=False)}\n\n"
        f"### policy\n{policy}\n"
        f"### situation\n{json.dumps(situation.state, ensure_ascii=False, indent=2)}\n"
        f"### open questions\n{json.dumps(situation.open_questions, ensure_ascii=False)}\n"
        f"### trajectory (tail)\n"
        f"{json.dumps([e.model_dump() for e in trajectory], ensure_ascii=False, indent=2)}\n"
        f"### inbound event\nrole={event['role']}: {event['text']}\n"
    )


def bind_event_role(store: CaseStore, case_id: str, role: str) -> str:
    """Mechanical role derivation: the role must be a declared stakeholder."""
    doc = store.load_case(case_id)
    if role not in doc.stakeholders:
        raise SystemExit(
            f"role {role!r} not in stakeholders {sorted(doc.stakeholders)}"
        )
    return role


# --- the loop --------------------------------------------------------------------


def run_case_event(
    settings: AgentSettings,
    store: CaseStore,
    case_id: str,
    event: dict,
    *,
    approve: bool = True,
    request_limit: int = 12,
) -> dict:
    role = bind_event_role(store, case_id, event["role"])
    event_seq = (
        len([e for e in store.read_trajectory(case_id) if e.kind == "event"]) + 1
    )
    run_id = f"fde-{case_id}-e{event_seq:02d}"

    # Host-side field memory: the inbound event is recorded by the host, not
    # the model — the agent may not edit its own inputs.
    store.append_trajectory_for_case(
        case_id,
        TrajectoryEntry(kind="event", role=role, summary=event["text"], refs={}),
    )

    material_ids = json.loads(
        (store.case_dir(case_id) / "material-ids.json").read_text(encoding="utf-8")
    )
    minimal = settings.with_overrides(
        enable_filesystem=False,
        enable_knowledge=False,
        enable_planning=False,
        enable_skills=False,
        enable_tool_output_limits=False,
    )
    agent = build_agent(
        minimal,
        run_id=run_id,
        instructions=FDE_LOOP_INSTRUCTIONS,
        extra_toolsets=[
            build_case_toolset(store),
            build_fde_toolset(store, case_id, material_ids),
        ],
    )
    prompt = (
        seed_case_context(store, case_id, event)
        + "\nHandle this inbound event now. Follow the loop discipline: "
        "observe, diagnose, decide, act, verify. End with a RunSummary "
        "stating what changed and what is next."
    )
    outcome = execute_run(
        agent,
        CoreDeps(workspace_root=settings.workspace_root.resolve(), run_id=run_id),
        prompt=prompt,
        settings=minimal.with_overrides(request_limit=request_limit),
        run_id=run_id,
        conversation_id=case_id,
        retries={"tools": 5},
    )

    if isinstance(outcome, PausedRun):
        print(
            f"  PAUSED for approval: {[c.tool_name for c in outcome.requests.approvals]}"
        )
        if not approve:
            answer = input("approve? [y/n] ").strip().lower()
            if answer not in ("y", "yes"):
                print("  RESULT: approval denied")
                return {"status": "denied"}
        resume_run_id = f"{run_id}-r"
        resume_agent = build_agent(
            minimal,
            run_id=resume_run_id,
            instructions=FDE_LOOP_INSTRUCTIONS,
            extra_toolsets=[
                build_case_toolset(store),
                build_fde_toolset(store, case_id, material_ids),
            ],
        )
        outcome = execute_run(
            resume_agent,
            CoreDeps(
                workspace_root=settings.workspace_root.resolve(), run_id=resume_run_id
            ),
            settings=minimal.with_overrides(request_limit=request_limit),
            run_id=resume_run_id,
            conversation_id=outcome.conversation_id,
            message_history=outcome.message_history,
            deferred_tool_results=decide(outcome, approve=True),
            prior_pause_receipt=outcome.pause_receipt,
        )

    if not isinstance(outcome, TerminalRun):
        raise SystemExit(f"expected TerminalRun, got {type(outcome).__name__}")
    receipt = outcome.receipt
    sent_drafts: list[str] = []
    if any(
        e.tool_name == "send_to_customer" and e.status == "completed"
        for e in receipt.verified_tool_effects
    ):
        # Field Interface performs the surface send after the run settles.
        sent = store.list_drafts(case_id)[-1] if store.list_drafts(case_id) else None
        if sent is not None:
            sent_drafts.append(sent.name)
            store.append_trajectory_for_case(
                case_id,
                TrajectoryEntry(
                    kind="action",
                    role="system",
                    run_id=receipt.run_id,
                    summary=f"sent {sent.name} to customer via Field Interface",
                    refs={"draft_ref": sent.name},
                ),
            )
            print(f"  FIELD SEND: {sent.name} -> customer")
            print("  " + sent.read_text(encoding="utf-8").replace("\n", "\n  ")[:400])
    record = {
        "event_seq": event_seq,
        "run_id": receipt.run_id,
        "status": receipt.status,
        "model_requests": receipt.usage.get("requests"),
        "cost": receipt.usage.get("cost"),
        "verified_effects": [
            (e.tool_name, e.status) for e in receipt.verified_tool_effects
        ],
        "sent_drafts": sent_drafts,
    }
    print(json.dumps(record, ensure_ascii=False, indent=2, default=json_default))
    return record


def show_case(store: CaseStore, case_id: str) -> None:
    doc = store.load_case(case_id)
    situation = store.read_situation(case_id)
    trajectory = store.read_trajectory(case_id)
    print(f"=== case {case_id} ===")
    print(doc.to_md())
    print("--- situation ---")
    print(json.dumps(situation.model_dump(), ensure_ascii=False, indent=2))
    print("--- trajectory ---")
    for entry in trajectory:
        print(
            f"{entry.seq:>3} {entry.ts[:19]} {entry.kind:<8} {entry.role:<8} "
            f"run={entry.run_id or '-':<28} {entry.summary[:80]}"
        )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case-dir", default=str(CASES_ROOT))
    ap.add_argument("--case-id", default=DEFAULT_CASE_ID)
    ap.add_argument("--setup", action="store_true", help="create the case fixture once")
    ap.add_argument("--event-role", choices=("customer", "barry"))
    ap.add_argument("--event-text", default="")
    ap.add_argument("--approve", action="store_true", help="auto-approve send pauses")
    ap.add_argument("--show", action="store_true", help="print case state + trajectory")
    args = ap.parse_args()

    store = CaseStore(Path(args.case_dir))
    if args.setup:
        ids = setup_case(Path(args.case_dir), store, args.case_id)
        print(json.dumps(ids, ensure_ascii=False, indent=2))
        print("case fixture ready; run --show to inspect")
        return
    if args.show:
        show_case(store, args.case_id)
        return
    if not args.event_role or not args.event_text:
        ap.error("--event-role and --event-text are required (or --setup / --show)")

    settings = AgentSettings.from_env().with_overrides(
        workspace_root=REPO / "workspace",
        runtime_state_root=REPO / ".zuaef-state",
        enable_planning=False,
        enable_skills=False,
    )
    run_case_event(
        settings,
        store,
        args.case_id,
        {"role": args.event_role, "text": args.event_text},
        approve=args.approve,
    )


if __name__ == "__main__":
    main()
