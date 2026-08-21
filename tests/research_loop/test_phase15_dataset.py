import pytest
import json
import numpy as np
import pandas as pd
from src.research_loop.phase15.dataset import HardCaseDatasetFirewall

@pytest.fixture
def sample_manifest(tmp_path):
    manifest_content = {
        "experiment_id": "TEST-P15-001",
        "dataset": {
            "source": "hard_cases.py",
            "hard_case_lower": 0.40,
            "hard_case_upper": 0.90,
            "fingerprint": "TEST_FINGERPRINT"
        },
        "features": {
            "columns": ["f1", "f2"],
            "normalization": "train_only_standard_scaler",
            "dimension": 2
        },
        "split": {
            "method": "stratified",
            "seed": 42,
            "test_fraction": 0.5
        }
    }
    p = tmp_path / "manifest.json"
    with open(p, "w") as f:
        json.dump(manifest_content, f)
    return str(p)

@pytest.fixture
def sample_raw_data():
    return pd.DataFrame({
        "f1": [1.0, 2.0, 3.0, 4.0],
        "f2": [2.0, 3.0, 4.0, 5.0],
        "confidence": [0.5, 0.6, 0.7, 0.95],
        "label": [0, 1, 0, 1]
    })

def test_dataset_firewall_filtering_and_fingerprint(sample_manifest, sample_raw_data, tmp_path):
    firewall = HardCaseDatasetFirewall(sample_manifest)
    X_tr, X_te, y_tr, y_te, fp = firewall.prepare_and_freeze(sample_raw_data, str(tmp_path))
    assert fp["row_count"] == 3
    assert fp["dataset_id"] == "TEST-P15-001"
    assert (tmp_path / "dataset_fingerprint.json").exists()
