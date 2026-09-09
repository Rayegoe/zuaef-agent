from __future__ import annotations

from enum import StrEnum


class EffectClass(StrEnum):
    """Small policy vocabulary for native PydanticAI tool approval.

    This does not implement an approval runtime. It only gives business toolsets
    a shared way to classify effects before passing `requires_approval=` to
    PydanticAI's native tool registration API.
    """

    OBSERVE = "observe"
    LOCAL_WRITE = "local_write"
    EXTERNAL_WRITE = "external_write"
    DESTRUCTIVE = "destructive"


def requires_approval(effect: EffectClass | str) -> bool:
    """Return whether the effect should require native human approval by default.

    Unknown values raise ``ValueError`` instead of silently returning False:
    this function is the approval gate for external writes, so a typo'd effect
    (e.g. "destructiv") must fail loudly rather than downgrade a tool to
    approval-free.
    """
    try:
        cls = EffectClass(effect)
    except ValueError as exc:
        raise ValueError(f"unknown effect class: {effect!r}") from exc
    return cls in {EffectClass.EXTERNAL_WRITE, EffectClass.DESTRUCTIVE}
