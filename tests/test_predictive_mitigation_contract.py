import importlib
from dataclasses import fields

def test_predictive_mitigation_canonical_contract_is_importable():
    module=importlib.import_module("src.mitigation.predictive_mitigation")
    prediction=module.BoundedPrediction
    assert [f.name for f in fields(prediction)] == ["horizon_ms","probability","lower_bound","upper_bound","uncertainty","source_sequence"]
