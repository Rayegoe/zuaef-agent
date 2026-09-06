"""Host-grounded interaction projection (P3B-3 T001/T002).

Identity is environment state, not LLM cognition: the host knows which
surface the agent is talking on and which role the current interlocutor
plays, so the model never has to infer who it is replying to. This module
renders those deterministic facts as one tiny model-visible block.

It describes the environment ONLY — it is not a workflow, carries no task
sequence, and never suggests business actions. Four concepts stay distinct
by construction:

- the CURRENT INTERLOCUTOR (who talks to the agent now);
- the BOUND CASE CUSTOMER (the business party a bound Case is about);
- a NORMAL REPLY (the agent's final response, returned to the current
  interlocutor through the current surface by the host);
- EXTERNAL DELIVERY (a separate side effect through approval-gated tools).

The Gateway/bridge calls ``project_interaction_context`` before the model
request; actor identity is supplied by the surface adapter (an authorized
Telegram operator is a supervisor), never inferred from a Case binding.

The ACTIVE COMPOSITION PROFILE is projected alongside the actor role as a
separate fact (Feishu v0.1 live finding): a model that only sees "actor
role: supervisor" tends to answer "my profile is supervisor" when asked
about itself — conflating the speaker's role with its own composition.
Stating both facts adjacently keeps them distinct. This is model-visible
environment context ONLY: it never participates in authorization or any
policy decision.
"""

from __future__ import annotations

from typing import Literal

ActorRole = Literal["supervisor", "customer", "unknown"]

# A normal reply needs no channel tool on any gateway surface: the host
# delivers the terminal presentation to the current conversation itself.
_REPLY_TRANSPORT_FACT = (
    "the host delivers your normal final response to the current "
    "conversation by itself; no channel tool is needed to reply here"
)


def project_interaction_context(
    surface: str | None,
    actor_role: ActorRole | None,
    *,
    case_id: str | None = None,
    active_profile: str | None = None,
) -> str | None:
    """Project one bounded block of host-grounded interaction facts.

    ``active_profile`` is the run's EFFECTIVE composition profile (already
    resolved by the caller through the binding precedence — thread binding >
    chat binding > group default > gateway default), never the raw session
    persistence value. ``None`` means the core agent composition.

    Returns ``None`` when the host knows no interaction facts at all (e.g. a
    headless one-shot run with no surface), so nothing is injected.
    """
    if surface is None and actor_role is None and active_profile is None:
        return None

    lines = ["Current interaction (host-grounded):"]
    if surface is not None:
        lines.append(f"- surface: {surface}")
    role = actor_role or "unknown"
    lines.append(f"- current actor role: {role} (the speaker's role, not this agent's profile)")
    if active_profile is not None:
        lines.append(f"- active composition profile: {active_profile}")
    else:
        lines.append(
            "- active composition profile: (none — core agent composition, "
            "no business profile)"
        )
    if role == "supervisor":
        lines.append(
            "- a normal reply returns to this supervisor in the current "
            "conversation"
        )
    elif role == "customer":
        lines.append(
            "- a normal reply returns to this customer in the current "
            "conversation"
        )
    else:
        lines.append(
            "- the current actor role is unknown; never assume the current "
            "speaker is the Case customer"
        )
    lines.append(f"- {_REPLY_TRANSPORT_FACT}")
    if case_id is not None:
        lines.append(
            f"- the bound Case customer ({case_id}) is a different business "
            "party from the current actor"
        )
        lines.append(
            "- replying normally in this conversation is NOT customer delivery"
        )
        lines.append(
            "- delivering to the Case customer is a separate external action "
            "with its own approval-gated delivery tools; the absence of a "
            "channel tool for replies never means customer delivery is "
            "impossible"
        )
    else:
        lines.append("- no Case is bound to this conversation")
    return "\n".join(lines)
