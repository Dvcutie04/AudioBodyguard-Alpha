from dataclasses import replace

import pytest

from src.device_fabric.endpoint_transaction_finality_protocol import EndpointFinalityAcceptedResult,EndpointFinalityAssertionClaims,EndpointFinalityDecision,EndpointFinalityReplayClassification,EndpointTransactionState,classify_endpoint_finality_replay,endpoint_finality_proof_identity,endpoint_finality_replay_result,transition_endpoint_transaction_state,transition_endpoint_transaction_state_from_finality_assertion,validate_endpoint_finality_binding,validate_endpoint_finality_chain,validate_endpoint_finality_freshness


def test_not_applied_is_terminal_and_cannot_become_execution_claimed():
    with pytest.raises(ValueError,match="terminal endpoint transaction state"):
        transition_endpoint_transaction_state(EndpointTransactionState.NOT_APPLIED,EndpointTransactionState.EXECUTION_CLAIMED)


def test_finality_assertion_for_wrong_device_is_rejected():
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-1",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-other",transaction_id="tx-1",intent_id="intent-1",capability_digest="cap-1",authorization_digest="auth-1",controller_id="controller-1",controller_fencing_token=7,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=11,issued_at=100.0,not_before=99.0,expires_at=130.0,previous_proof_digest=None)
    with pytest.raises(ValueError,match="finality assertion device_id mismatch"):
        validate_endpoint_finality_binding(claims,device_id="tv-expected",transaction_id="tx-1",intent_id="intent-1",capability_digest="cap-1",authorization_digest="auth-1",controller_id="controller-1",controller_fencing_token=7,audience="aqss-endpoint",issuer_id="finality-authority-1",authority_epoch=11)


def test_finality_assertion_rejects_unknown_profile_version():
    with pytest.raises(ValueError,match="profile_version is invalid"):
        EndpointFinalityAssertionClaims(profile_version=3,proof_id="proof-2",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-2",intent_id="intent-2",capability_digest="cap-2",authorization_digest="auth-2",controller_id="controller-1",controller_fencing_token=8,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=12,issued_at=200.0,not_before=199.0,expires_at=230.0,previous_proof_digest=None)


def test_finality_assertion_rejects_boolean_controller_fencing_token():
    with pytest.raises(ValueError,match="controller_fencing_token is invalid"):
        EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-3",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-3",intent_id="intent-3",capability_digest="cap-3",authorization_digest="auth-3",controller_id="controller-1",controller_fencing_token=True,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=13,issued_at=300.0,not_before=299.0,expires_at=330.0,previous_proof_digest=None)


def test_finality_assertion_rejects_boolean_authority_epoch():
    with pytest.raises(ValueError,match="authority_epoch is invalid"):
        EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-4",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-4",intent_id="intent-4",capability_digest="cap-4",authorization_digest="auth-4",controller_id="controller-1",controller_fencing_token=9,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=True,issued_at=400.0,not_before=399.0,expires_at=430.0,previous_proof_digest=None)


def test_finality_assertion_rejects_blank_proof_id():
    with pytest.raises(ValueError,match="proof_id is invalid"):
        EndpointFinalityAssertionClaims(profile_version=1,proof_id=" ",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-5",intent_id="intent-5",capability_digest="cap-5",authorization_digest="auth-5",controller_id="controller-1",controller_fencing_token=10,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=14,issued_at=500.0,not_before=499.0,expires_at=530.0,previous_proof_digest=None)


def test_finality_assertion_rejects_untrimmed_issuer_id():
    with pytest.raises(ValueError,match="issuer_id is invalid"):
        EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-6",issuer_id=" finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-6",intent_id="intent-6",capability_digest="cap-6",authorization_digest="auth-6",controller_id="controller-1",controller_fencing_token=11,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=15,issued_at=600.0,not_before=599.0,expires_at=630.0,previous_proof_digest=None)


def test_finality_assertion_rejects_blank_audience():
    with pytest.raises(ValueError,match="audience is invalid"):
        EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-7",issuer_id="finality-authority-1",audience="",device_id="tv-expected",transaction_id="tx-7",intent_id="intent-7",capability_digest="cap-7",authorization_digest="auth-7",controller_id="controller-1",controller_fencing_token=12,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=16,issued_at=700.0,not_before=699.0,expires_at=730.0,previous_proof_digest=None)


def test_finality_assertion_rejects_blank_device_id():
    with pytest.raises(ValueError,match="device_id is invalid"):
        EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-8",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id=" ",transaction_id="tx-8",intent_id="intent-8",capability_digest="cap-8",authorization_digest="auth-8",controller_id="controller-1",controller_fencing_token=13,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=17,issued_at=800.0,not_before=799.0,expires_at=830.0,previous_proof_digest=None)


def test_finality_assertion_rejects_untrimmed_transaction_id():
    with pytest.raises(ValueError,match="transaction_id is invalid"):
        EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-9",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-9 ",intent_id="intent-9",capability_digest="cap-9",authorization_digest="auth-9",controller_id="controller-1",controller_fencing_token=14,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=18,issued_at=900.0,not_before=899.0,expires_at=930.0,previous_proof_digest=None)


def test_finality_assertion_rejects_invalid_remaining_identifiers():
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-10",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-10",intent_id="intent-10",capability_digest="cap-10",authorization_digest="auth-10",controller_id="controller-1",controller_fencing_token=15,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=19,issued_at=1000.0,not_before=999.0,expires_at=1030.0,previous_proof_digest=None)
    for field,value in (("intent_id",""),("capability_digest"," cap-10"),("authorization_digest","auth-10 "),("controller_id"," "),("reason_code",""),("previous_proof_digest"," digest-9")):
        with pytest.raises(ValueError,match=field+" is invalid"):
            replace(claims,**{field:value})


def test_finality_assertion_rejects_untyped_decision():
    with pytest.raises(ValueError,match="decision is invalid"):
        EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-11",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-11",intent_id="intent-11",capability_digest="cap-11",authorization_digest="auth-11",controller_id="controller-1",controller_fencing_token=16,decision="NOT_APPLIED",reason_code="POLICY_ABORT",authority_epoch=20,issued_at=1100.0,not_before=1099.0,expires_at=1130.0,previous_proof_digest=None)


def test_finality_assertion_rejects_boolean_timestamps():
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-12",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-12",intent_id="intent-12",capability_digest="cap-12",authorization_digest="auth-12",controller_id="controller-1",controller_fencing_token=17,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=21,issued_at=1200.0,not_before=1199.0,expires_at=1230.0,previous_proof_digest=None)
    for field in ("issued_at","not_before","expires_at"):
        with pytest.raises(ValueError,match=field+" is invalid"):
            replace(claims,**{field:True})


def test_finality_assertion_rejects_non_finite_timestamps():
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-13",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-13",intent_id="intent-13",capability_digest="cap-13",authorization_digest="auth-13",controller_id="controller-1",controller_fencing_token=18,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=22,issued_at=1300.0,not_before=1299.0,expires_at=1330.0,previous_proof_digest=None)
    for field,value in (("issued_at",float("nan")),("not_before",float("inf")),("expires_at",float("-inf"))):
        with pytest.raises(ValueError,match=field+" is invalid"):
            replace(claims,**{field:value})


def test_finality_assertion_rejects_invalid_time_window():
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-14",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-14",intent_id="intent-14",capability_digest="cap-14",authorization_digest="auth-14",controller_id="controller-1",controller_fencing_token=19,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=23,issued_at=1400.0,not_before=1399.0,expires_at=1430.0,previous_proof_digest=None)
    for changes in ({"not_before":1400.1},{"expires_at":1400.0}):
        with pytest.raises(ValueError,match="finality assertion time window is invalid"):
            replace(claims,**changes)


def test_finality_assertion_freshness_rejects_inactive_or_expired_claims():
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-15",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-15",intent_id="intent-15",capability_digest="cap-15",authorization_digest="auth-15",controller_id="controller-1",controller_fencing_token=20,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=24,issued_at=1500.0,not_before=1499.0,expires_at=1530.0,previous_proof_digest=None)
    with pytest.raises(ValueError,match="finality assertion is not yet valid"):
        validate_endpoint_finality_freshness(claims,now=1498.9)
    with pytest.raises(ValueError,match="finality assertion is expired"):
        validate_endpoint_finality_freshness(claims,now=1530.0)
    assert validate_endpoint_finality_freshness(claims,now=1500.0) is claims


def test_finality_assertion_for_wrong_authority_is_rejected():
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-16",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-16",intent_id="intent-16",capability_digest="cap-16",authorization_digest="auth-16",controller_id="controller-1",controller_fencing_token=21,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=25,issued_at=1600.0,not_before=1599.0,expires_at=1630.0,previous_proof_digest=None)
    expected=dict(device_id="tv-expected",transaction_id="tx-16",intent_id="intent-16",capability_digest="cap-16",authorization_digest="auth-16",controller_id="controller-1",controller_fencing_token=21,audience="aqss-endpoint",issuer_id="finality-authority-1",authority_epoch=25)
    for field,value in (("issuer_id","finality-authority-other"),("authority_epoch",26)):
        mismatched=dict(expected);mismatched[field]=value
        with pytest.raises(ValueError,match="finality assertion "+field+" mismatch"):
            validate_endpoint_finality_binding(claims,**mismatched)


def test_finality_assertion_rejects_all_bound_field_mismatches():
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-17",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-17",intent_id="intent-17",capability_digest="cap-17",authorization_digest="auth-17",controller_id="controller-1",controller_fencing_token=22,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=26,issued_at=1700.0,not_before=1699.0,expires_at=1730.0,previous_proof_digest=None)
    expected=dict(device_id="tv-expected",transaction_id="tx-17",intent_id="intent-17",capability_digest="cap-17",authorization_digest="auth-17",controller_id="controller-1",controller_fencing_token=22,audience="aqss-endpoint",issuer_id="finality-authority-1",authority_epoch=26)
    for field,value in (("transaction_id","tx-other"),("intent_id","intent-other"),("capability_digest","cap-other"),("authorization_digest","auth-other"),("controller_id","controller-other"),("controller_fencing_token",23),("audience","other-audience")):
        mismatched=dict(expected);mismatched[field]=value
        with pytest.raises(ValueError,match="finality assertion "+field+" mismatch"):
            validate_endpoint_finality_binding(claims,**mismatched)


def test_finality_assertion_freshness_rejects_invalid_now():
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-18",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-18",intent_id="intent-18",capability_digest="cap-18",authorization_digest="auth-18",controller_id="controller-1",controller_fencing_token=23,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=27,issued_at=1800.0,not_before=1799.0,expires_at=1830.0,previous_proof_digest=None)
    for now in (True,float("nan"),float("inf"),float("-inf"),"1800"):
        with pytest.raises(ValueError,match="now is invalid"):
            validate_endpoint_finality_freshness(claims,now=now)


def test_finality_assertion_freshness_rejects_untyped_claims():
    for claims in (None,object(),{}):
        with pytest.raises(ValueError,match="finality assertion claims are invalid"):
            validate_endpoint_finality_freshness(claims,now=1900.0)


def test_finality_assertion_freshness_accepts_not_before_boundary():
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-19",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-19",intent_id="intent-19",capability_digest="cap-19",authorization_digest="auth-19",controller_id="controller-1",controller_fencing_token=24,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=28,issued_at=1900.0,not_before=1899.0,expires_at=1930.0,previous_proof_digest=None)
    assert validate_endpoint_finality_freshness(claims,now=claims.not_before) is claims


def test_not_applied_finality_assertion_resolves_indeterminate_transaction():
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-20",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-20",intent_id="intent-20",capability_digest="cap-20",authorization_digest="auth-20",controller_id="controller-1",controller_fencing_token=25,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=29,issued_at=2000.0,not_before=1999.0,expires_at=2030.0,previous_proof_digest=None)
    assert transition_endpoint_transaction_state_from_finality_assertion(EndpointTransactionState.INDETERMINATE,claims) is EndpointTransactionState.NOT_APPLIED


def test_not_applied_finality_assertion_cannot_clear_execution_claim():
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-21",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-21",intent_id="intent-21",capability_digest="cap-21",authorization_digest="auth-21",controller_id="controller-1",controller_fencing_token=26,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=30,issued_at=2100.0,not_before=2099.0,expires_at=2130.0,previous_proof_digest=None)
    with pytest.raises(ValueError):
        transition_endpoint_transaction_state_from_finality_assertion(EndpointTransactionState.EXECUTION_CLAIMED,claims)


def test_not_applied_finality_assertion_cannot_overwrite_terminal_truth():
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-22",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-22",intent_id="intent-22",capability_digest="cap-22",authorization_digest="auth-22",controller_id="controller-1",controller_fencing_token=27,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=31,issued_at=2200.0,not_before=2199.0,expires_at=2230.0,previous_proof_digest=None)
    for state in (EndpointTransactionState.APPLIED,EndpointTransactionState.CONFLICT):
        with pytest.raises(ValueError,match="terminal endpoint transaction state"):
            transition_endpoint_transaction_state_from_finality_assertion(state,claims)


def test_not_applied_finality_assertion_resolves_unknown_transaction():
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-23",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-23",intent_id="intent-23",capability_digest="cap-23",authorization_digest="auth-23",controller_id="controller-1",controller_fencing_token=28,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=32,issued_at=2300.0,not_before=2299.0,expires_at=2330.0,previous_proof_digest=None)
    assert transition_endpoint_transaction_state_from_finality_assertion(EndpointTransactionState.UNKNOWN,claims) is EndpointTransactionState.NOT_APPLIED


def test_finality_chain_requires_exact_previous_proof_digest():
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-24",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-24",intent_id="intent-24",capability_digest="cap-24",authorization_digest="auth-24",controller_id="controller-1",controller_fencing_token=29,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=33,issued_at=2400.0,not_before=2399.0,expires_at=2430.0,previous_proof_digest="proof-digest-23")
    assert validate_endpoint_finality_chain(claims,previous_proof_digest="proof-digest-23") is claims
    with pytest.raises(ValueError,match="finality assertion previous_proof_digest mismatch"):
        validate_endpoint_finality_chain(claims,previous_proof_digest="proof-digest-other")


def test_finality_chain_enforces_explicit_root_semantics():
    root=EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-25",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-25",intent_id="intent-25",capability_digest="cap-25",authorization_digest="auth-25",controller_id="controller-1",controller_fencing_token=30,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=34,issued_at=2500.0,not_before=2499.0,expires_at=2530.0,previous_proof_digest=None)
    assert validate_endpoint_finality_chain(root,previous_proof_digest=None) is root
    with pytest.raises(ValueError,match="finality assertion previous_proof_digest mismatch"):
        validate_endpoint_finality_chain(root,previous_proof_digest="unexpected-predecessor")
    chained=replace(root,proof_id="proof-26",previous_proof_digest="proof-digest-25")
    with pytest.raises(ValueError,match="finality assertion previous_proof_digest mismatch"):
        validate_endpoint_finality_chain(chained,previous_proof_digest=None)


def test_finality_chain_rejects_untyped_claims():
    for claims in (None,object(),{}):
        with pytest.raises(ValueError,match="finality assertion claims are invalid"):
            validate_endpoint_finality_chain(claims,previous_proof_digest=None)


def test_finality_chain_rejects_invalid_expected_previous_digest():
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-27",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-27",intent_id="intent-27",capability_digest="cap-27",authorization_digest="auth-27",controller_id="controller-1",controller_fencing_token=31,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=35,issued_at=2700.0,not_before=2699.0,expires_at=2730.0,previous_proof_digest=None)
    for previous_proof_digest in (True,1,b"digest",""," "," padded","padded "):
        with pytest.raises(ValueError,match="previous_proof_digest is invalid"):
            validate_endpoint_finality_chain(claims,previous_proof_digest=previous_proof_digest)


def test_endpoint_finality_proof_identity_uses_issuer_and_proof_id():
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-28",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-28",intent_id="intent-28",capability_digest="cap-28",authorization_digest="auth-28",controller_id="controller-1",controller_fencing_token=32,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=36,issued_at=2800.0,not_before=2799.0,expires_at=2830.0,previous_proof_digest=None)
    assert endpoint_finality_proof_identity(claims)==("finality-authority-1","proof-28")


def test_endpoint_finality_proof_identity_ignores_transaction_and_epoch():
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-29",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-29",intent_id="intent-29",capability_digest="cap-29",authorization_digest="auth-29",controller_id="controller-1",controller_fencing_token=33,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=37,issued_at=2900.0,not_before=2899.0,expires_at=2930.0,previous_proof_digest=None)
    expected=("finality-authority-1","proof-29")
    assert endpoint_finality_proof_identity(replace(claims,transaction_id="tx-other"))==expected
    assert endpoint_finality_proof_identity(replace(claims,authority_epoch=38))==expected


def test_endpoint_finality_proof_identity_distinguishes_issuers():
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-30",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-30",intent_id="intent-30",capability_digest="cap-30",authorization_digest="auth-30",controller_id="controller-1",controller_fencing_token=34,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=38,issued_at=3000.0,not_before=2999.0,expires_at=3030.0,previous_proof_digest=None)
    other_issuer=replace(claims,issuer_id="finality-authority-2")
    assert endpoint_finality_proof_identity(claims)!=(endpoint_finality_proof_identity(other_issuer))


def test_endpoint_finality_proof_identity_rejects_untyped_claims():
    for claims in (None,object(),{}):
        with pytest.raises(ValueError,match="finality assertion claims are invalid"):
            endpoint_finality_proof_identity(claims)


def test_endpoint_finality_proof_identity_rejects_claims_subclass():
    class ClaimsSubclass(EndpointFinalityAssertionClaims):
        pass
    claims=ClaimsSubclass(profile_version=1,proof_id="proof-31",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-31",intent_id="intent-31",capability_digest="cap-31",authorization_digest="auth-31",controller_id="controller-1",controller_fencing_token=35,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=39,issued_at=3100.0,not_before=3099.0,expires_at=3130.0,previous_proof_digest=None)
    with pytest.raises(ValueError,match="finality assertion claims are invalid"):
        endpoint_finality_proof_identity(claims)


def test_finality_replay_classifies_absent_accepted_entry_as_unseen():
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-32",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-32",intent_id="intent-32",capability_digest="cap-32",authorization_digest="auth-32",controller_id="controller-1",controller_fencing_token=36,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=40,issued_at=3200.0,not_before=3199.0,expires_at=3230.0,previous_proof_digest=None)
    assert classify_endpoint_finality_replay(claims,accepted_claims=None) is EndpointFinalityReplayClassification.UNSEEN


def test_finality_replay_classifies_identical_accepted_claims():
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-33",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-33",intent_id="intent-33",capability_digest="cap-33",authorization_digest="auth-33",controller_id="controller-1",controller_fencing_token=37,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=41,issued_at=3300.0,not_before=3299.0,expires_at=3330.0,previous_proof_digest="proof-digest-32")
    assert classify_endpoint_finality_replay(claims,accepted_claims=replace(claims)) is EndpointFinalityReplayClassification.IDENTICAL_REPLAY


def test_finality_replay_classifies_changed_content_under_same_identity_as_conflict():
    accepted=EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-34",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-34",intent_id="intent-34",capability_digest="cap-34",authorization_digest="auth-34",controller_id="controller-1",controller_fencing_token=38,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=42,issued_at=3400.0,not_before=3399.0,expires_at=3430.0,previous_proof_digest="proof-digest-33")
    submitted=replace(accepted,transaction_id="tx-other")
    assert classify_endpoint_finality_replay(submitted,accepted_claims=accepted) is EndpointFinalityReplayClassification.ID_CONFLICT


def test_finality_replay_rejects_mismatched_accepted_identity():
    accepted=EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-35",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-35",intent_id="intent-35",capability_digest="cap-35",authorization_digest="auth-35",controller_id="controller-1",controller_fencing_token=39,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=43,issued_at=3500.0,not_before=3499.0,expires_at=3530.0,previous_proof_digest="proof-digest-34")
    for submitted in (replace(accepted,proof_id="proof-other"),replace(accepted,issuer_id="finality-authority-2")):
        with pytest.raises(ValueError,match="accepted finality assertion identity mismatch"):
            classify_endpoint_finality_replay(submitted,accepted_claims=accepted)


def test_finality_replay_treats_equal_numeric_values_with_different_types_as_conflict():
    accepted=EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-36",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-36",intent_id="intent-36",capability_digest="cap-36",authorization_digest="auth-36",controller_id="controller-1",controller_fencing_token=40,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=44,issued_at=3600.0,not_before=3599.0,expires_at=3630.0,previous_proof_digest="proof-digest-35")
    submitted=replace(accepted,issued_at=3600)
    assert classify_endpoint_finality_replay(submitted,accepted_claims=accepted) is EndpointFinalityReplayClassification.ID_CONFLICT


def test_finality_replay_treats_opposite_signed_zero_as_conflict():
    accepted=EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-37",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-37",intent_id="intent-37",capability_digest="cap-37",authorization_digest="auth-37",controller_id="controller-1",controller_fencing_token=41,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=45,issued_at=0.0,not_before=0.0,expires_at=30.0,previous_proof_digest="proof-digest-36")
    submitted=replace(accepted,issued_at=-0.0)
    assert classify_endpoint_finality_replay(submitted,accepted_claims=accepted) is EndpointFinalityReplayClassification.ID_CONFLICT


def test_finality_replay_classifies_nonidentity_claim_mutations_as_conflicts():
    accepted=EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-38",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-38",intent_id="intent-38",capability_digest="cap-38",authorization_digest="auth-38",controller_id="controller-1",controller_fencing_token=42,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=46,issued_at=3800.0,not_before=3799.0,expires_at=3830.0,previous_proof_digest="proof-digest-37")
    changes=({"audience":"other-audience"},{"device_id":"tv-other"},{"transaction_id":"tx-other"},{"intent_id":"intent-other"},{"capability_digest":"cap-other"},{"authorization_digest":"auth-other"},{"controller_id":"controller-2"},{"controller_fencing_token":43},{"reason_code":"OTHER_REASON"},{"authority_epoch":47},{"issued_at":3801.0},{"not_before":3798.0},{"expires_at":3831.0},{"previous_proof_digest":None})
    for change in changes:
        assert classify_endpoint_finality_replay(replace(accepted,**change),accepted_claims=accepted) is EndpointFinalityReplayClassification.ID_CONFLICT,change


def test_finality_replay_rejects_untyped_accepted_claims():
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-39",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-39",intent_id="intent-39",capability_digest="cap-39",authorization_digest="auth-39",controller_id="controller-1",controller_fencing_token=43,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=47,issued_at=3900.0,not_before=3899.0,expires_at=3930.0,previous_proof_digest="proof-digest-38")
    for accepted_claims in (object(),{}):
        with pytest.raises(ValueError,match="accepted finality assertion claims are invalid"):
            classify_endpoint_finality_replay(claims,accepted_claims=accepted_claims)


def test_finality_replay_rejects_accepted_claims_subclass():
    class ClaimsSubclass(EndpointFinalityAssertionClaims):
        pass
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-40",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-40",intent_id="intent-40",capability_digest="cap-40",authorization_digest="auth-40",controller_id="controller-1",controller_fencing_token=44,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=48,issued_at=4000.0,not_before=3999.0,expires_at=4030.0,previous_proof_digest="proof-digest-39")
    accepted_claims=ClaimsSubclass(**{name:getattr(claims,name) for name in EndpointFinalityAssertionClaims.__slots__})
    with pytest.raises(ValueError,match="accepted finality assertion claims are invalid"):
        classify_endpoint_finality_replay(claims,accepted_claims=accepted_claims)


def test_endpoint_finality_accepted_result_preserves_original_transition_and_time():
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-41",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-41",intent_id="intent-41",capability_digest="cap-41",authorization_digest="auth-41",controller_id="controller-1",controller_fencing_token=45,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=49,issued_at=4100.0,not_before=4099.0,expires_at=4130.0,previous_proof_digest="proof-digest-40")
    result=EndpointFinalityAcceptedResult(claims=claims,prior_state=EndpointTransactionState.INDETERMINATE,result_state=EndpointTransactionState.NOT_APPLIED,accepted_at=4101.0)
    assert result.claims is claims
    assert result.prior_state is EndpointTransactionState.INDETERMINATE
    assert result.result_state is EndpointTransactionState.NOT_APPLIED
    assert result.accepted_at==4101.0


def test_endpoint_finality_accepted_result_rejects_untyped_claims():
    for claims in (None,object(),{}):
        with pytest.raises(ValueError,match="accepted finality result claims are invalid"):
            EndpointFinalityAcceptedResult(claims=claims,prior_state=EndpointTransactionState.INDETERMINATE,result_state=EndpointTransactionState.NOT_APPLIED,accepted_at=4201.0)


def test_endpoint_finality_accepted_result_rejects_claims_subclass():
    class ClaimsSubclass(EndpointFinalityAssertionClaims):
        pass
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-43",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-43",intent_id="intent-43",capability_digest="cap-43",authorization_digest="auth-43",controller_id="controller-1",controller_fencing_token=46,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=50,issued_at=4300.0,not_before=4299.0,expires_at=4330.0,previous_proof_digest="proof-digest-42")
    subclass_claims=ClaimsSubclass(**{field:getattr(claims,field) for field in EndpointFinalityAssertionClaims.__slots__})
    with pytest.raises(ValueError,match="accepted finality result claims are invalid"):
        EndpointFinalityAcceptedResult(claims=subclass_claims,prior_state=EndpointTransactionState.INDETERMINATE,result_state=EndpointTransactionState.NOT_APPLIED,accepted_at=4301.0)


def test_endpoint_finality_accepted_result_rejects_untyped_prior_state():
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-44",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-44",intent_id="intent-44",capability_digest="cap-44",authorization_digest="auth-44",controller_id="controller-1",controller_fencing_token=47,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=51,issued_at=4400.0,not_before=4399.0,expires_at=4430.0,previous_proof_digest="proof-digest-43")
    for prior_state in (None,object(),"INDETERMINATE"):
        with pytest.raises(ValueError,match="accepted finality result prior_state is invalid"):
            EndpointFinalityAcceptedResult(claims=claims,prior_state=prior_state,result_state=EndpointTransactionState.NOT_APPLIED,accepted_at=4401.0)


def test_endpoint_finality_accepted_result_rejects_untyped_result_state():
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-45",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-45",intent_id="intent-45",capability_digest="cap-45",authorization_digest="auth-45",controller_id="controller-1",controller_fencing_token=48,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=52,issued_at=4500.0,not_before=4499.0,expires_at=4530.0,previous_proof_digest="proof-digest-44")
    for result_state in (None,object(),"NOT_APPLIED"):
        with pytest.raises(ValueError,match="accepted finality result result_state is invalid"):
            EndpointFinalityAcceptedResult(claims=claims,prior_state=EndpointTransactionState.INDETERMINATE,result_state=result_state,accepted_at=4501.0)


def test_endpoint_finality_accepted_result_rejects_invalid_accepted_at():
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-46",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-46",intent_id="intent-46",capability_digest="cap-46",authorization_digest="auth-46",controller_id="controller-1",controller_fencing_token=49,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=53,issued_at=4600.0,not_before=4599.0,expires_at=4630.0,previous_proof_digest="proof-digest-45")
    for accepted_at in (None,True,"4601",float("nan"),float("inf"),float("-inf")):
        with pytest.raises(ValueError,match="accepted finality result accepted_at is invalid"):
            EndpointFinalityAcceptedResult(claims=claims,prior_state=EndpointTransactionState.INDETERMINATE,result_state=EndpointTransactionState.NOT_APPLIED,accepted_at=accepted_at)


def test_endpoint_finality_accepted_result_rejects_transition_mismatch():
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-47",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-47",intent_id="intent-47",capability_digest="cap-47",authorization_digest="auth-47",controller_id="controller-1",controller_fencing_token=50,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=54,issued_at=4700.0,not_before=4699.0,expires_at=4730.0,previous_proof_digest="proof-digest-46")
    with pytest.raises(ValueError,match="accepted finality result transition mismatch"):
        EndpointFinalityAcceptedResult(claims=claims,prior_state=EndpointTransactionState.INDETERMINATE,result_state=EndpointTransactionState.APPLIED,accepted_at=4701.0)


def test_endpoint_finality_replay_result_returns_original_accepted_result():
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-48",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-48",intent_id="intent-48",capability_digest="cap-48",authorization_digest="auth-48",controller_id="controller-1",controller_fencing_token=51,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=55,issued_at=4800.0,not_before=4799.0,expires_at=4830.0,previous_proof_digest="proof-digest-47")
    accepted_result=EndpointFinalityAcceptedResult(claims=claims,prior_state=EndpointTransactionState.INDETERMINATE,result_state=EndpointTransactionState.NOT_APPLIED,accepted_at=4801.0)
    replay_result=endpoint_finality_replay_result(replace(claims),accepted_result=accepted_result)
    assert replay_result is accepted_result
    assert replay_result.accepted_at==4801.0


def test_endpoint_finality_replay_result_rejects_identity_conflict():
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-49",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-49",intent_id="intent-49",capability_digest="cap-49",authorization_digest="auth-49",controller_id="controller-1",controller_fencing_token=52,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=56,issued_at=4900.0,not_before=4899.0,expires_at=4930.0,previous_proof_digest="proof-digest-48")
    accepted_result=EndpointFinalityAcceptedResult(claims=claims,prior_state=EndpointTransactionState.INDETERMINATE,result_state=EndpointTransactionState.NOT_APPLIED,accepted_at=4901.0)
    with pytest.raises(ValueError,match="accepted finality proof identity conflict"):
        endpoint_finality_replay_result(replace(claims,transaction_id="tx-other"),accepted_result=accepted_result)
    assert accepted_result.claims is claims
    assert accepted_result.accepted_at==4901.0


def test_endpoint_finality_replay_result_rejects_invalid_accepted_result():
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-50",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-50",intent_id="intent-50",capability_digest="cap-50",authorization_digest="auth-50",controller_id="controller-1",controller_fencing_token=53,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=57,issued_at=5000.0,not_before=4999.0,expires_at=5030.0,previous_proof_digest="proof-digest-49")
    for accepted_result in (None,object(),{}):
        with pytest.raises(ValueError,match="accepted finality result is invalid"):
            endpoint_finality_replay_result(claims,accepted_result=accepted_result)


def test_endpoint_finality_replay_result_rejects_accepted_result_subclass():
    class AcceptedResultSubclass(EndpointFinalityAcceptedResult):
        pass
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-51",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-51",intent_id="intent-51",capability_digest="cap-51",authorization_digest="auth-51",controller_id="controller-1",controller_fencing_token=54,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=58,issued_at=5100.0,not_before=5099.0,expires_at=5130.0,previous_proof_digest="proof-digest-50")
    accepted_result=AcceptedResultSubclass(claims=claims,prior_state=EndpointTransactionState.INDETERMINATE,result_state=EndpointTransactionState.NOT_APPLIED,accepted_at=5101.0)
    with pytest.raises(ValueError,match="accepted finality result is invalid"):
        endpoint_finality_replay_result(replace(claims),accepted_result=accepted_result)


def test_endpoint_finality_replay_result_rejects_invalid_claims():
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-52",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-52",intent_id="intent-52",capability_digest="cap-52",authorization_digest="auth-52",controller_id="controller-1",controller_fencing_token=55,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=59,issued_at=5200.0,not_before=5199.0,expires_at=5230.0,previous_proof_digest="proof-digest-51")
    accepted_result=EndpointFinalityAcceptedResult(claims=claims,prior_state=EndpointTransactionState.INDETERMINATE,result_state=EndpointTransactionState.NOT_APPLIED,accepted_at=5201.0)
    for replay_claims in (None,object(),{}):
        with pytest.raises(ValueError,match="finality assertion claims are invalid"):
            endpoint_finality_replay_result(replay_claims,accepted_result=accepted_result)


def test_endpoint_finality_replay_result_rejects_claims_subclass():
    class ClaimsSubclass(EndpointFinalityAssertionClaims):
        pass
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-53",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-53",intent_id="intent-53",capability_digest="cap-53",authorization_digest="auth-53",controller_id="controller-1",controller_fencing_token=56,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=60,issued_at=5300.0,not_before=5299.0,expires_at=5330.0,previous_proof_digest="proof-digest-52")
    replay_claims=ClaimsSubclass(**{field:getattr(claims,field) for field in EndpointFinalityAssertionClaims.__slots__})
    accepted_result=EndpointFinalityAcceptedResult(claims=claims,prior_state=EndpointTransactionState.INDETERMINATE,result_state=EndpointTransactionState.NOT_APPLIED,accepted_at=5301.0)
    with pytest.raises(ValueError,match="finality assertion claims are invalid"):
        endpoint_finality_replay_result(replay_claims,accepted_result=accepted_result)


def test_endpoint_finality_replay_result_rejects_mismatched_proof_identity():
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-54",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-54",intent_id="intent-54",capability_digest="cap-54",authorization_digest="auth-54",controller_id="controller-1",controller_fencing_token=57,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=61,issued_at=5400.0,not_before=5399.0,expires_at=5430.0,previous_proof_digest="proof-digest-53")
    accepted_result=EndpointFinalityAcceptedResult(claims=claims,prior_state=EndpointTransactionState.INDETERMINATE,result_state=EndpointTransactionState.NOT_APPLIED,accepted_at=5401.0)
    for replay_claims in (replace(claims,proof_id="proof-other"),replace(claims,issuer_id="finality-authority-other")):
        with pytest.raises(ValueError,match="accepted finality assertion identity mismatch"):
            endpoint_finality_replay_result(replay_claims,accepted_result=accepted_result)


import src.device_fabric.endpoint_transaction_finality_protocol as finality_protocol


def test_endpoint_finality_replay_result_does_not_recompute_transition(monkeypatch):
    claims=EndpointFinalityAssertionClaims(profile_version=1,proof_id="proof-55",issuer_id="finality-authority-1",audience="aqss-endpoint",device_id="tv-expected",transaction_id="tx-55",intent_id="intent-55",capability_digest="cap-55",authorization_digest="auth-55",controller_id="controller-1",controller_fencing_token=58,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="POLICY_ABORT",authority_epoch=62,issued_at=5500.0,not_before=5499.0,expires_at=5530.0,previous_proof_digest="proof-digest-54")
    accepted_result=EndpointFinalityAcceptedResult(claims=claims,prior_state=EndpointTransactionState.INDETERMINATE,result_state=EndpointTransactionState.NOT_APPLIED,accepted_at=5501.0)
    def fail_transition(*args,**kwargs):
        raise AssertionError("replay recomputed finality transition")
    monkeypatch.setattr(finality_protocol,"transition_endpoint_transaction_state_from_finality_assertion",fail_transition)
    replay_result=endpoint_finality_replay_result(replace(claims),accepted_result=accepted_result)
    assert replay_result is accepted_result
    assert replay_result.accepted_at==5501.0


def test_v2_finality_requires_request_binding():
    base=EndpointFinalityAssertionClaims(profile_version=1,proof_id="p",issuer_id="i",audience="a",device_id="d",transaction_id="t",intent_id="n",capability_digest="c",authorization_digest="h",controller_id="r",controller_fencing_token=1,decision=EndpointFinalityDecision.NOT_APPLIED,reason_code="x",authority_epoch=1,issued_at=1,not_before=0,expires_at=2,previous_proof_digest=None)
    with pytest.raises(ValueError,match="request_digest"):
        replace(base,profile_version=2)
    with pytest.raises(ValueError,match="request_digest"):
        replace(base,request_digest="request-one")
    claims=replace(base,profile_version=2,request_digest="request-one")
    binding=dict(device_id="d",transaction_id="t",intent_id="n",capability_digest="c",authorization_digest="h",controller_id="r",controller_fencing_token=1,audience="a",issuer_id="i",authority_epoch=1)
    with pytest.raises(ValueError,match="request_digest"):
        validate_endpoint_finality_binding(claims,**binding)
    with pytest.raises(ValueError,match="request_digest mismatch"):
        validate_endpoint_finality_binding(claims,request_digest="request-two",**binding)
    assert validate_endpoint_finality_binding(claims,request_digest="request-one",**binding) is claims
