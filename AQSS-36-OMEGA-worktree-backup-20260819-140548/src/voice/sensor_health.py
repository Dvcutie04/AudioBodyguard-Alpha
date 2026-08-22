import math

class SensorHealthMonitor:
    def __init__(self, clip_threshold=0.99, dead_threshold=1e-7):
        self.clip_threshold = clip_threshold
        self.dead_threshold = dead_threshold

    def inspect_frame(self, frame):
        if not frame:
            return {"status": "FAULT_EMPTY_FRAME", "healthy": False}

        channels = frame if isinstance(frame[0], list) else [frame]

        for ch_idx, ch in enumerate(channels):
            if not ch:
                return {"status": f"FAULT_EMPTY_CHANNEL_{ch_idx}", "healthy": False}
            
            max_val = 0.0
            sum_val = 0.0
            for val in ch:
                if math.isnan(val) or math.isinf(val):
                    return {"status": f"FAULT_CORRUPTED_VALUE_CH_{ch_idx}", "healthy": False}
                abs_val = abs(val)
                sum_val += abs_val
                if abs_val > max_val:
                    max_val = abs_val

            if max_val >= self.clip_threshold:
                return {"status": f"FAULT_CLIPPED_SIGNAL_CH_{ch_idx}", "healthy": False}
            
            avg_val = sum_val / len(ch)
            if avg_val < self.dead_threshold:
                return {"status": f"FAULT_DEAD_CHANNEL_CH_{ch_idx}", "healthy": False}

        return {"status": "NOMINAL", "healthy": True}
