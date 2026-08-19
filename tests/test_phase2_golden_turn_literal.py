"""Golden Outcome literal turns — SPEC v1.0 §7 (P2-5).

The authoritative proof ships the EXACT golden texts; Turn 2 receives NO
hidden host restatement (in particular no re-stated no-price reminder). The
Gateway projects the inbound text verbatim; continuity (Turn 2 seeing Turn 1)
comes only from public StepStore history + Case state.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO), str(REPO / "src"), str(REPO / "tools")]

import fde_two_turn_proof as proof

from zuaef_agent.gateway.bridge import project_prompt
from zuaef_agent.gateway.models import InboundEnvelope

GOLDEN_TURN1 = (
    "客户觉得上一篇 demo 太模板化。"
    "结合他之前给的背景和材料重写一篇。"
    "价格先不要写，我看完再决定要不要发。"
)
GOLDEN_TURN2 = "开头还是太像 AI，保留刚才客户背景，再改一版；其他要求不变。"


def test_turn_constants_are_the_exact_golden_texts():
    assert proof.TURN1 == GOLDEN_TURN1
    assert proof.TURN2 == GOLDEN_TURN2


def test_turn2_contains_no_hidden_constraint_restatement():
    # The forbidden host addition: 上一轮客户说过不要价格… or equivalent.
    assert "价格" not in proof.TURN2
    assert "上一轮" not in proof.TURN2
    assert "不要写" not in proof.TURN2
    assert "审批" not in proof.TURN2


def test_gateway_projects_turn2_literally():
    envelope = InboundEnvelope(
        surface="telegram",
        user_id="42",
        channel_id="42",
        message_id="m-2",
        text=proof.TURN2,
    )
    # Mechanical projection: the prompt the model receives IS the literal text.
    assert project_prompt(envelope) == proof.TURN2


def test_proof_passes_turn_texts_unchanged_to_the_gateway():
    for message_id, turn in (("m-1", proof.TURN1), ("m-2", proof.TURN2)):
        envelope = proof._envelope(message_id, turn)
        assert envelope.text == turn


def test_turn1_turn2_share_conversation_and_case_by_session_binding():
    """The proof binds ONE session to ONE Case; both turns flow through the
    same channel/thread, so the same conversation_id is implied by the
    Gateway's session store — never by prompt text."""
    env1 = proof._envelope("m-1", proof.TURN1)
    env2 = proof._envelope("m-2", proof.TURN2)
    key1 = (
        env1.surface,
        env1.tenant_id,
        env1.user_id,
        env1.channel_id,
        env1.thread_id,
    )
    key2 = (
        env2.surface,
        env2.tenant_id,
        env2.user_id,
        env2.channel_id,
        env2.thread_id,
    )
    assert key1 == key2