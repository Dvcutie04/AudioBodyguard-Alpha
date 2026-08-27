import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.inference.bayesian_adapter import BayesianAdapter, ChangePointEvidence


def test_bayesian_adapter_initialization():
    adapter = BayesianAdapter()
    assert adapter is not None
