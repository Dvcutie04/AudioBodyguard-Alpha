python3 -c '
path = "tests/inference/test_change_point_bayesian_adapter.py"
content = """import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.inference.bayesian_adapter import BayesianAdapter, ChangePointEvidence
""" + open(path).read().split("\n", 2)[-1]
open(path, "w").write(content)
'
