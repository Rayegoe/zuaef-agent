from zuaef_agent.effects import EffectClass, requires_approval


def test_native_approval_policy_is_small_and_conservative():
    assert requires_approval(EffectClass.OBSERVE) is False
    assert requires_approval(EffectClass.LOCAL_WRITE) is False
    assert requires_approval(EffectClass.EXTERNAL_WRITE) is True
    assert requires_approval(EffectClass.DESTRUCTIVE) is True
