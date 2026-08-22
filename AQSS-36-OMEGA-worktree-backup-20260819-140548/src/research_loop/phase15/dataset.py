from pathlib import Path
import json
import hashlib
import numpy as np
import pandas as pd


class HardCaseDatasetFirewall:
    def __init__(self, manifest_path):
        self.manifest_path = Path(manifest_path)
        with self.manifest_path.open('r') as f:
            self.manifest = json.load(f)

    def prepare_and_freeze(self, data, out_dir):
        dataset_cfg = self.manifest.get('dataset', {})
        lower = float(dataset_cfg.get('hard_case_lower', -float('inf')))
        upper = float(dataset_cfg.get('hard_case_upper', float('inf')))
        if 'confidence' not in data.columns:
            raise ValueError("Missing required column: confidence")
        if 'label' not in data.columns:
            raise ValueError("Missing required column: label")
        if data.duplicated().any():
            raise ValueError("Duplicate rows detected in input dataset")
        if not data.empty:
            numeric = data.select_dtypes(include=[np.number])
            if not numeric.empty and not np.isfinite(numeric.to_numpy(dtype=float)).all():
                raise ValueError("Non-finite numeric values detected in input dataset")
        filtered = data[(data['confidence'] >= lower) & (data['confidence'] < upper)].copy()
        features = self.manifest.get('features', {}).get('columns', [])
        if not features:
            features = [c for c in filtered.columns if c not in ('confidence', 'label')]
        missing = [c for c in features if c not in filtered.columns]
        if missing:
            raise ValueError(f"Missing feature columns: {missing}")
        X = filtered[features].to_numpy(dtype=float)
        y = filtered['label'].to_numpy()
        split_cfg = self.manifest.get('split', {})
        seed = int(split_cfg.get('seed', 42))
        test_fraction = float(split_cfg.get('test_fraction', 0.2))
        n = len(filtered)
        n_test = max(1, int(round(n * test_fraction))) if n > 1 else 0
        rng = np.random.default_rng(seed)
        if n > 1 and 'label' in filtered.columns:
            labels = filtered['label'].to_numpy()
            test_idx = []
            train_idx = []
            for label in np.unique(labels):
                group = np.flatnonzero(labels == label)
                rng.shuffle(group)
                k = int(round(len(group) * test_fraction))
                k = max(0, min(k, len(group)))
                test_idx.extend(group[:k].tolist())
                train_idx.extend(group[k:].tolist())
            test_idx = np.asarray(test_idx, dtype=int)
            train_idx = np.asarray(train_idx, dtype=int)
            rng.shuffle(test_idx)
            rng.shuffle(train_idx)
        else:
            indices = np.arange(n)
            rng.shuffle(indices)
            test_idx = indices[:n_test]
            train_idx = indices[n_test:]
        X_tr, X_te = X[train_idx], X[test_idx]
        y_tr, y_te = y[train_idx], y[test_idx]
        fingerprint_payload = filtered.to_csv(index=False).encode('utf-8')
        digest = hashlib.sha256(fingerprint_payload).hexdigest()
        fp = {'dataset_id': self.manifest.get('experiment_id'), 'row_count': int(len(filtered)), 'sha256': digest, 'features': features, 'hard_case_lower': lower, 'hard_case_upper': upper, 'split_seed': seed, 'test_fraction': test_fraction}
        out_path = Path(out_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        (out_path / 'dataset_fingerprint.json').write_text(json.dumps(fp, indent=2, sort_keys=True))
        return X_tr, X_te, y_tr, y_te, fp
