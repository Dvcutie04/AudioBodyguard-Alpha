from src.control.media_control_prior_state import MediaControlPriorState
from src.device_fabric.contracts import AuthorizedActionIntent, DeviceState, PhysicalSnapshot


def test_prior_state_capture_preserves_observation_and_transaction():
    state=DeviceState(volume=21)
    prior_digest=state.state_digest
    snapshot=PhysicalSnapshot(device_id="living-room-tv",state=state,epoch=7,observed_at=100.0,evidence_digest="prior-observation-evidence")
    authorized=AuthorizedActionIntent(intent_id="intent-volume-1",lease_id="lease-1",action="set_volume",device_id="living-room-tv",operation="set_volume",target_state=DeviceState(volume=37),expected_pre_state=DeviceState(volume=21),authorization_digest="authorization-1",deadline_at=120.0,transaction_id="transaction-1",capability_digest="capability-1")
    captured=MediaControlPriorState.from_authorized_snapshot(snapshot,authorized)
    state.volume=37
    snapshot.evidence_digest="changed-evidence"
    authorized.transaction_id="changed-transaction"
    assert captured.volume_percent==21
    assert captured.prior_state_digest==prior_digest
    assert captured.prior_state_evidence_digest=="prior-observation-evidence"
    assert captured.prior_state_epoch==7
    assert captured.device_id=="living-room-tv"
    assert captured.intent_id=="intent-volume-1"
    assert captured.transaction_id=="transaction-1"
    assert captured.authorization_digest=="authorization-1"
    assert captured.capability_digest=="capability-1"
    from dataclasses import FrozenInstanceError
    import pytest

    with pytest.raises(TypeError):
        MediaControlPriorState()
    for field,value in (("volume_percent",99),("transaction_id","replacement"),("prior_state_digest","replacement")):
        with pytest.raises(FrozenInstanceError):
            setattr(captured,field,value)


def test_prior_state_capture_rejects_pre_state_mismatch():
    import pytest

    snapshot=PhysicalSnapshot(device_id="living-room-tv",state=DeviceState(volume=22),epoch=7,observed_at=100.0,evidence_digest="prior-observation-evidence")
    authorized=AuthorizedActionIntent(intent_id="intent-volume-1",lease_id="lease-1",action="set_volume",device_id="living-room-tv",operation="set_volume",target_state=DeviceState(volume=37),expected_pre_state=DeviceState(volume=21),authorization_digest="authorization-1",deadline_at=120.0,transaction_id="transaction-1",capability_digest="capability-1")
    with pytest.raises(ValueError,match="prior capture pre-state mismatch"):
        MediaControlPriorState.from_authorized_snapshot(snapshot,authorized)


def test_prior_state_capture_rejects_incomplete_lineage():
    from dataclasses import replace
    import pytest

    snapshot=PhysicalSnapshot(device_id="living-room-tv",state=DeviceState(volume=21),epoch=7,observed_at=100.0,evidence_digest="prior-observation-evidence")
    authorized=AuthorizedActionIntent(intent_id="intent-volume-1",lease_id="lease-1",action="set_volume",device_id="living-room-tv",operation="set_volume",target_state=DeviceState(volume=37),expected_pre_state=DeviceState(volume=21),authorization_digest="authorization-1",deadline_at=120.0,transaction_id="transaction-1",capability_digest="capability-1")
    for invalid in (None,"","   ",True):
        for field in ("device_id","evidence_digest"):
            with pytest.raises(ValueError,match="incomplete prior capture lineage"):
                MediaControlPriorState.from_authorized_snapshot(replace(snapshot,**{field:invalid}),authorized)
        for field in ("device_id","intent_id","transaction_id","authorization_digest","capability_digest","operation"):
            with pytest.raises(ValueError,match="incomplete prior capture lineage"):
                MediaControlPriorState.from_authorized_snapshot(snapshot,replace(authorized,**{field:invalid}))


def test_prior_state_capture_rejects_invalid_observation_inputs():
    from dataclasses import replace
    import pytest

    snapshot=PhysicalSnapshot(device_id="living-room-tv",state=DeviceState(volume=21),epoch=7,observed_at=100.0,evidence_digest="prior-observation-evidence")
    authorized=AuthorizedActionIntent(intent_id="intent-volume-1",device_id="living-room-tv",operation="set_volume",target_state=DeviceState(volume=37),expected_pre_state=DeviceState(volume=21),authorization_digest="authorization-1",transaction_id="transaction-1",capability_digest="capability-1")
    for bad_snapshot,bad_authorized in ((object(),authorized),(snapshot,object()),(replace(snapshot,device_id="bedroom-tv"),authorized),(replace(snapshot,state=None),authorized),(snapshot,replace(authorized,expected_pre_state=None)),(snapshot,replace(authorized,target_state=None))):
        with pytest.raises(ValueError):
            MediaControlPriorState.from_authorized_snapshot(bad_snapshot,bad_authorized)
    for epoch in (True,-1,7.0,"7",None):
        with pytest.raises(ValueError,match="invalid prior capture epoch"):
            MediaControlPriorState.from_authorized_snapshot(replace(snapshot,epoch=epoch),authorized)
    for observed_at in (True,-1.0,float("nan"),float("inf"),float("-inf"),"100",None):
        with pytest.raises(ValueError,match="invalid prior capture observation time"):
            MediaControlPriorState.from_authorized_snapshot(replace(snapshot,observed_at=observed_at),authorized)
    for volume in (True,-1,101,21.0,None):
        with pytest.raises(ValueError,match="invalid prior capture volume"):
            MediaControlPriorState.from_authorized_snapshot(replace(snapshot,state=DeviceState(volume=volume)),authorized)


def test_prior_state_capture_preserves_captions():
    state=DeviceState(volume=21,custom_state={"captions_enabled":False})
    snapshot=PhysicalSnapshot(device_id="living-room-tv",state=state,epoch=7,observed_at=100.0,evidence_digest="prior-observation-evidence")
    authorized=AuthorizedActionIntent(intent_id="intent-captions-1",device_id="living-room-tv",operation="set_captions_enabled",target_state=DeviceState(volume=21,custom_state={"captions_enabled":True}),expected_pre_state=DeviceState(volume=21,custom_state={"captions_enabled":False}),authorization_digest="authorization-1",transaction_id="transaction-1",capability_digest="capability-1")
    captured=MediaControlPriorState.from_authorized_snapshot(snapshot,authorized)
    state.custom_state["captions_enabled"]=True
    assert captured.captions_enabled is False


def test_prior_state_capture_validates_captions():
    from dataclasses import replace
    import pytest

    snapshot=PhysicalSnapshot(device_id="living-room-tv",state=DeviceState(volume=21),epoch=7,observed_at=100.0,evidence_digest="prior-observation-evidence")
    authorized=AuthorizedActionIntent(intent_id="intent-volume-1",device_id="living-room-tv",operation="set_volume",target_state=DeviceState(volume=37),expected_pre_state=DeviceState(volume=21),authorization_digest="authorization-1",transaction_id="transaction-1",capability_digest="capability-1")
    assert MediaControlPriorState.from_authorized_snapshot(snapshot,authorized).captions_enabled is None
    for invalid in (None,0,1,"false",[],{}):
        state=DeviceState(volume=21,custom_state={"captions_enabled":invalid})
        with pytest.raises(ValueError,match="invalid prior capture captions"):
            MediaControlPriorState.from_authorized_snapshot(replace(snapshot,state=state),replace(authorized,expected_pre_state=state))
    for invalid in (None,[],"captions_enabled"):
        state=DeviceState(volume=21,custom_state=invalid)
        with pytest.raises(ValueError,match="invalid prior capture custom state"):
            MediaControlPriorState.from_authorized_snapshot(replace(snapshot,state=state),replace(authorized,expected_pre_state=state))


def test_prior_state_capture_preserves_eq_preset():
    from src.control.media_control_capabilities import EqPreset

    state=DeviceState(volume=21,custom_state={"eq_preset":"FLAT"})
    snapshot=PhysicalSnapshot(device_id="living-room-tv",state=state,epoch=7,observed_at=100.0,evidence_digest="prior-observation-evidence")
    authorized=AuthorizedActionIntent(intent_id="intent-eq-1",device_id="living-room-tv",operation="set_eq_preset",target_state=DeviceState(volume=21,custom_state={"eq_preset":"NIGHT"}),expected_pre_state=DeviceState(volume=21,custom_state={"eq_preset":"FLAT"}),authorization_digest="authorization-1",transaction_id="transaction-1",capability_digest="capability-1")
    captured=MediaControlPriorState.from_authorized_snapshot(snapshot,authorized)
    state.custom_state["eq_preset"]="NIGHT"
    assert captured.eq_preset is EqPreset.FLAT
    assert captured.eq_bands is None


def test_prior_state_capture_validates_eq_preset():
    from dataclasses import replace
    import pytest

    snapshot=PhysicalSnapshot(device_id="living-room-tv",state=DeviceState(volume=21),epoch=7,observed_at=100.0,evidence_digest="prior-observation-evidence")
    authorized=AuthorizedActionIntent(intent_id="intent-volume-1",device_id="living-room-tv",operation="set_volume",target_state=DeviceState(volume=37),expected_pre_state=DeviceState(volume=21),authorization_digest="authorization-1",transaction_id="transaction-1",capability_digest="capability-1")
    captured=MediaControlPriorState.from_authorized_snapshot(snapshot,authorized)
    assert captured.eq_preset is None
    assert captured.eq_bands is None
    for invalid in (None,0,True,"UNKNOWN",[],{}):
        state=DeviceState(volume=21,custom_state={"eq_preset":invalid})
        with pytest.raises(ValueError,match="invalid prior capture EQ preset"):
            MediaControlPriorState.from_authorized_snapshot(replace(snapshot,state=state),replace(authorized,expected_pre_state=state))


def test_prior_state_capture_preserves_eq_bands():
    from src.control.media_control_capabilities import EqBandGain

    raw_bands=[{"frequency_hz":100,"gain_db":-2},{"frequency_hz":1000,"gain_db":1.5}]
    state=DeviceState(volume=21,custom_state={"eq_bands":raw_bands})
    snapshot=PhysicalSnapshot(device_id="living-room-tv",state=state,epoch=7,observed_at=100.0,evidence_digest="prior-observation-evidence")
    authorized=AuthorizedActionIntent(intent_id="intent-eq-bands-1",device_id="living-room-tv",operation="set_eq_bands",target_state=DeviceState(volume=21,custom_state={"eq_bands":[{"frequency_hz":100,"gain_db":0},{"frequency_hz":1000,"gain_db":0}]}),expected_pre_state=DeviceState(volume=21,custom_state={"eq_bands":[{"frequency_hz":100,"gain_db":-2},{"frequency_hz":1000,"gain_db":1.5}]}),authorization_digest="authorization-1",transaction_id="transaction-1",capability_digest="capability-1")
    captured=MediaControlPriorState.from_authorized_snapshot(snapshot,authorized)
    raw_bands[0]["gain_db"]=12
    raw_bands.append({"frequency_hz":10000,"gain_db":4})
    assert captured.eq_preset is None
    assert captured.eq_bands==(EqBandGain(100,-2),EqBandGain(1000,1.5))


def test_prior_state_capture_validates_eq_bands():
    from dataclasses import replace
    import pytest

    snapshot=PhysicalSnapshot(device_id="living-room-tv",state=DeviceState(volume=21),epoch=7,observed_at=100.0,evidence_digest="prior-observation-evidence")
    authorized=AuthorizedActionIntent(intent_id="intent-eq-bands-1",device_id="living-room-tv",operation="set_eq_bands",target_state=DeviceState(volume=21,custom_state={"eq_bands":[{"frequency_hz":100,"gain_db":0}]}),expected_pre_state=DeviceState(volume=21),authorization_digest="authorization-1",transaction_id="transaction-1",capability_digest="capability-1")
    def capture(custom):
        state=DeviceState(volume=21,custom_state=custom)
        return MediaControlPriorState.from_authorized_snapshot(replace(snapshot,state=state),replace(authorized,expected_pre_state=state))
    for invalid in (None,(),[],[{"frequency_hz":100+i,"gain_db":0} for i in range(11)]):
        with pytest.raises(ValueError,match="invalid prior capture EQ bands"):
            capture({"eq_bands":invalid})
    for invalid in ([None],[{}],[{"frequency_hz":100}],[{"frequency_hz":100,"gain_db":0,"extra":1}]):
        with pytest.raises(ValueError,match="invalid prior capture EQ band"):
            capture({"eq_bands":invalid})
    for invalid in ([{"frequency_hz":True,"gain_db":0}],[{"frequency_hz":10,"gain_db":0}],[{"frequency_hz":100,"gain_db":13}],[{"frequency_hz":100,"gain_db":float("nan")}]):
        with pytest.raises(ValueError):
            capture({"eq_bands":invalid})
    for invalid in ([{"frequency_hz":100,"gain_db":0},{"frequency_hz":100,"gain_db":1}],[{"frequency_hz":1000,"gain_db":0},{"frequency_hz":100,"gain_db":1}]):
        with pytest.raises(ValueError,match="prior capture EQ bands must increase"):
            capture({"eq_bands":invalid})
    with pytest.raises(ValueError,match="prior capture combines EQ preset and bands"):
        capture({"eq_preset":"FLAT","eq_bands":[{"frequency_hz":100,"gain_db":0}]})


def test_prior_state_capture_rejects_unsupported_operation():
    from dataclasses import replace
    import pytest

    snapshot=PhysicalSnapshot(device_id="living-room-tv",state=DeviceState(volume=21),epoch=7,observed_at=100.0,evidence_digest="prior-observation-evidence")
    authorized=AuthorizedActionIntent(intent_id="intent-volume-1",device_id="living-room-tv",operation="set_volume",target_state=DeviceState(volume=37),expected_pre_state=DeviceState(volume=21),authorization_digest="authorization-1",transaction_id="transaction-1",capability_digest="capability-1")
    for operation in ("play","pause","seek","SET_VOLUME"):
        with pytest.raises(ValueError,match="unsupported prior capture operation"):
            MediaControlPriorState.from_authorized_snapshot(snapshot,replace(authorized,operation=operation))


def test_prior_state_capture_rejects_target_outside_operation_scope():
    import pytest

    prior=DeviceState(volume=21,muted=False,custom_state={"captions_enabled":False})
    snapshot=PhysicalSnapshot(device_id="living-room-tv",state=prior,epoch=7,observed_at=100.0,evidence_digest="prior-observation-evidence")
    authorized=AuthorizedActionIntent(intent_id="intent-volume-1",device_id="living-room-tv",operation="set_volume",target_state=DeviceState(volume=37,muted=True,custom_state={"captions_enabled":False}),expected_pre_state=DeviceState(volume=21,muted=False,custom_state={"captions_enabled":False}),authorization_digest="authorization-1",transaction_id="transaction-1",capability_digest="capability-1")
    with pytest.raises(ValueError,match="prior capture target does not match operation"):
        MediaControlPriorState.from_authorized_snapshot(snapshot,authorized)


def test_prior_state_capture_scopes_captions_target():
    import pytest

    prior=DeviceState(volume=21,muted=False,custom_state={"captions_enabled":False})
    snapshot=PhysicalSnapshot(device_id="living-room-tv",state=prior,epoch=7,observed_at=100.0,evidence_digest="prior-observation-evidence")
    authorized=AuthorizedActionIntent(intent_id="intent-captions-1",device_id="living-room-tv",operation="set_captions_enabled",target_state=DeviceState(volume=21,muted=True,custom_state={"captions_enabled":True}),expected_pre_state=DeviceState(volume=21,muted=False,custom_state={"captions_enabled":False}),authorization_digest="authorization-1",transaction_id="transaction-1",capability_digest="capability-1")
    with pytest.raises(ValueError,match="prior capture target does not match operation"):
        MediaControlPriorState.from_authorized_snapshot(snapshot,authorized)


def test_prior_state_capture_scopes_eq_preset_target():
    import pytest

    prior=DeviceState(volume=21,muted=False,custom_state={"eq_bands":[{"frequency_hz":100.0,"gain_db":-2.0}]})
    snapshot=PhysicalSnapshot(device_id="living-room-tv",state=prior,epoch=7,observed_at=100.0,evidence_digest="prior-observation-evidence")
    authorized=AuthorizedActionIntent(intent_id="intent-eq-preset-1",device_id="living-room-tv",operation="set_eq_preset",target_state=DeviceState(volume=21,muted=True,custom_state={"eq_preset":"NIGHT"}),expected_pre_state=DeviceState(volume=21,muted=False,custom_state={"eq_bands":[{"frequency_hz":100.0,"gain_db":-2.0}]}),authorization_digest="authorization-1",transaction_id="transaction-1",capability_digest="capability-1")
    with pytest.raises(ValueError,match="prior capture target does not match operation"):
        MediaControlPriorState.from_authorized_snapshot(snapshot,authorized)


def test_prior_state_capture_scopes_eq_bands_target():
    import pytest

    prior=DeviceState(volume=21,muted=False,custom_state={"eq_preset":"FLAT"})
    snapshot=PhysicalSnapshot(device_id="living-room-tv",state=prior,epoch=7,observed_at=100.0,evidence_digest="prior-observation-evidence")
    authorized=AuthorizedActionIntent(intent_id="intent-eq-bands-1",device_id="living-room-tv",operation="set_eq_bands",target_state=DeviceState(volume=21,muted=True,custom_state={"eq_bands":[{"frequency_hz":100.0,"gain_db":-2.0},{"frequency_hz":1000.0,"gain_db":1.5}]}),expected_pre_state=DeviceState(volume=21,muted=False,custom_state={"eq_preset":"FLAT"}),authorization_digest="authorization-1",transaction_id="transaction-1",capability_digest="capability-1")
    with pytest.raises(ValueError,match="prior capture target does not match operation"):
        MediaControlPriorState.from_authorized_snapshot(snapshot,authorized)
