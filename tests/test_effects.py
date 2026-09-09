import pytest

from zuaef_agent.effects import EffectClass, requires_approval


def test_native_approval_policy_is_small_and_conservative():
    assert requires_approval(EffectClass.OBSERVE) is False
    assert requires_approval(EffectClass.LOCAL_WRITE) is False
    assert requires_approval(EffectClass.EXTERNAL_WRITE) is True
    assert requires_approval(EffectClass.DESTRUCTIVE) is True


def test_effects_accept_raw_string_values():
    assert requires_approval("external_write") is True
    assert requires_approval("destructive") is True
    assert requires_approval("local_write") is False


def test_unknown_effect_raises_instead_of_silently_passing():
    # A typo must not silently downgrade an external write to approval-free.
    with pytest.raises(ValueError, match="unknown effect class"):
        requires_approval("destructiv")
    with pytest.raises(ValueError):
        requires_approval("banana")
