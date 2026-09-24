from dataclasses import dataclass
from typing import List, Dict, Any
import math

@dataclass(frozen=True)
class CalibrationMetrics:
    window_days: int
    total_decisions: int
    mean_confidence: float
    mean_accuracy: float
    calibration_error: float
    cumulative_regret: float
    drift_score: float
    status: str

class CalibrationAnalyticsEngine:
    def __init__(self, window_days: int = 7):
        self.window_days = window_days

    def evaluate_window(self, audit_records: List[Dict[str, Any]]) -> CalibrationMetrics:
        if not audit_records:
            return CalibrationMetrics(
                window_days=self.window_days,
                total_decisions=0,
                mean_confidence=0.0,
                mean_accuracy=0.0,
                calibration_error=0.0,
                cumulative_regret=0.0,
                drift_score=0.0,
                status="INSUFFICIENT_DATA"
            )

        total = len(audit_records)
        confidences = [r.get("confidence_weight", 0.5) for r in audit_records]
        mean_conf = sum(confidences) / total

        # Derive accuracy from feedback agreement (AGREE = 1.0, DISAGREE = 0.0)
        accuracies = [1.0 if r.get("feedback_type") == "AGREE" else 0.0 for r in audit_records]
        mean_acc = sum(accuracies) / total

        # Expected Calibration Error (ECE proxy)
        ece = abs(mean_conf - mean_acc)

        # Cumulative Regret: sum of missed optimal value or penalty for disagreement
        regret = sum(1.0 - acc for acc in accuracies)

        # Policy drift score based on version variance or parameter deltas
        deltas = [abs(r.get("bounded_delta", 0.0)) for r in audit_records]
        drift = sum(deltas) / total if total > 0 else 0.0

        status = "WELL_CALIBRATED" if ece < 0.15 else "RECALIBRATION_RECOMMENDED"

        return CalibrationMetrics(
            window_days=self.window_days,
            total_decisions=total,
            mean_confidence=mean_conf,
            mean_accuracy=mean_acc,
            calibration_error=ece,
            cumulative_regret=regret,
            drift_score=drift,
            status=status
        )
