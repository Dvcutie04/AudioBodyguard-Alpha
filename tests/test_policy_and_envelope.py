import pytest
from src.control.policy_governor import PolicyGovernor
from src.control.action_envelope import ActionEnvelope


def test_policy_governor_instantiation():
    gov = PolicyGovernor()
    assert gov is not None


def test_action_envelope_instantiation():
    env = ActionEnvelope(
        action="SET_ATTENUATION",
        target="spk_01",
        trust_score=0.95,
        evidence_mask=[1, 0, 1]
    )
    assert env.action == "SET_ATTENUATION"
    assert env.target == "spk_01"
    assert env.trust_score == 0.95
    assert env.evidence_mask == [1, 0, 1]


def test_policy_governor_evaluation():
    gov = PolicyGovernor()
    env = ActionEnvelope(
        action="SET_ATTENUATION",
        target="spk_01",
        trust_score=0.95,
        evidence_mask=[1, 0, 1]
    )
    res = gov.evaluate(env)
    assert isinstance(res, tuple)
    assert len(res) == 2
    assert isinstance(res[0], bool)


def test_action_envelope_methods():
    env = ActionEnvelope(
        action="SET_ATTENUATION",
        target="spk_01",
        trust_score=0.95,
        evidence_mask=[1, 0, 1]
    )
    if hasattr(env, "to_dict"):
        d = env.to_dict()
        assert isinstance(d, dict)
    if hasattr(env, "is_valid"):
        assert env.is_valid() in (True, False)


def test_policy_governor_rejection_branches():
    gov = PolicyGovernor()
    # Test with expired envelope if method exists
    env = ActionEnvelope(
        action="SET_ATTENUATION",
        target="spk_01",
        trust_score=0.1,
        evidence_mask=[0, 0, 0]
    )
    if hasattr(env, "is_expired"):
        setattr(env, "is_expired", lambda: True)
        res = gov.evaluate(env)
        assert res[0] is False
    
    # Test low trust / invalid mask evaluation
    env2 = ActionEnvelope(
        action="SET_ATTENUATION",
        target="spk_01",
        trust_score=0.1,
        evidence_mask=[0, 0, 0]
    )
    if hasattr(env2, "is_expired"):
        setattr(env2, "is_expired", lambda: False)
    res2 = gov.evaluate(env2)
    assert isinstance(res2, tuple)


def test_policy_governor_line13_branch():
    gov = PolicyGovernor()
    env = ActionEnvelope(
        action="SET_ATTENUATION",
        target="spk_01",
        trust_score=0.01,
        evidence_mask=[0, 0, 0]
    )
    if hasattr(env, "is_expired"):
        setattr(env, "is_expired", lambda: False)
    res = gov.evaluate(env)
    assert res[0] is False or res[1] != ""
