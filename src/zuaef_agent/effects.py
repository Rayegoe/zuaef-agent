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


def requires_approval(effect: EffectClass) -> bool:
    """Return whether the effect should require native human approval by default."""
    return effect in {EffectClass.EXTERNAL_WRITE, EffectClass.DESTRUCTIVE}
