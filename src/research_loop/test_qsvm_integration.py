import numpy as np
from sklearn.svm import SVC
from src.research_loop.hard_cases import HardCaseExtractor
from src.research_loop.generate_synthetic_cases import generate_synthetic_cases
from src.research_loop.qkernel import QSVMClassifier

def run_session_2():
    features, ytrue, probs = generate_synthetic_cases(100)
    extractor = HardCaseExtractor(lo_bound=0.40, hi_bound=0.90)
    hard_set = extractor.extract_ambiguous(features, ytrue, probs)
    
    X = hard_set.features
    y = hard_set.y_true
    
    split = int(len(X) * 0.7)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]
    
    # Classical SVM Baseline
    clf_classical = SVC(kernel="rbf")
    clf_classical.fit(X_train, y_train)
    acc_classical = clf_classical.score(X_test, y_test)
    
    # Quantum Kernel SVM
    qsvm = QSVMClassifier(n_qubits=4)
    qsvm.fit(X_train, y_train)
    acc_quantum = qsvm.score(X_test, y_test)
    
    print(f"[SESSION 2 COMPLETE] Processed {len(X)} hard cases.")
    print(f"Classical SVM Accuracy: {acc_classical * 100:.1f}%")
    print(f"Quantum Kernel SVM Accuracy: {acc_quantum * 100:.1f}%")

if __name__ == "__main__":
    run_session_2()
