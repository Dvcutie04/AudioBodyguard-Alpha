import pytest
from src.inference.bayesian_adapter import BayesianAdapter, ChangePointEvidence

def test_bayesian_adapter_init():
    adapter = BayesianAdapter()
    assert adapter is not None
