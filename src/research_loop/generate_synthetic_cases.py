import numpy as np
from src.research_loop.hard_cases import HardCaseExtractor

def generate_synthetic_cases(n_samples: int = 100):
    np.random.seed(42)
    features = np.random.rand(n_samples, 4)
    y_true = np.random.randint(0, 2, n_samples)
    probs = np.random.uniform(0.35, 0.95, n_samples)
    return features, y_true, probs

if __name__ == "__main__":
    features, ytrue, probs = generate_synthetic_cases()
    extractor = HardCaseExtractor(lo_bound=0.40, hi_bound=0.90)
    hard_set = extractor.extract_ambiguous(features, ytrue, probs)
    print(f"[SESSION 1 COMPLETE] Isolated {len(hard_set.indices)}/100 ambiguous samples.")
    print(f"Sample Ratio: {hard_set.sample_ratio * 100:.1f}%")
