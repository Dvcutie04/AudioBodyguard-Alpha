import numpy as np

class AQSSState:
    IDLE = "IDLE"
    ARMING = "ARMING"
    TRIGGERED = "TRIGGERED"

class AcousticFingerprint:
    def __init__(self, target_freq=18000.0, tolerance_hz=50.0, chunk_size=1024, sample_rate=44100, entry_snr_db=12.0, exit_snr_db=6.0, min_purity=0.40, required_hits=3):
        self.chunk_size = chunk_size
        self.sample_rate = sample_rate
        self.entry_snr_db = entry_snr_db
        self.exit_snr_db = exit_snr_db
        self.min_purity = min_purity
        self.required_hits = required_hits
        self.state = AQSSState.IDLE
        self.accumulator = 0
        self.window = np.hanning(chunk_size).astype(np.float32)
        self._windowed_buffer = np.zeros(chunk_size, dtype=np.float32)
        freqs = np.fft.rfftfreq(chunk_size, 1.0 / sample_rate)
        self.target_indices = np.where((freqs >= target_freq - tolerance_hz) & (freqs <= target_freq + tolerance_hz))[0].astype(np.intp)
        self.core_index = np.argmin(np.abs(freqs - target_freq))
        noise_mask = ((freqs >= target_freq - 1000.0) & (freqs < target_freq - 200.0)) | ((freqs > target_freq + 200.0) & (freqs <= target_freq + 1000.0))
        self.noise_indices = np.where(noise_mask)[0].astype(np.intp)

    def process_chunk(self, audio_chunk):
        if audio_chunk.dtype != np.float32:
            audio_chunk = audio_chunk.astype(np.float32, copy=False)
        if len(audio_chunk) != self.chunk_size:
            return {"triggered": False, "state": "INVALID_CHUNK_SIZE"}
        np.multiply(audio_chunk, self.window, out=self._windowed_buffer)
        fft_complex = np.fft.rfft(self._windowed_buffer)
        psd = fft_complex.real**2 + fft_complex.imag**2
        target_power = np.mean(psd[self.target_indices]) if len(self.target_indices) > 0 else 1e-10
        noise_power = np.mean(psd[self.noise_indices]) if len(self.noise_indices) > 0 else 1e-10
        total_target_energy = np.sum(psd[self.target_indices])
        purity = (psd[self.core_index] / total_target_energy) if total_target_energy > 0 else 0.0
        tnr_db = 10.0 * np.log10(max(target_power, 1e-10) / max(noise_power, 1e-10))
        frame_valid = (tnr_db >= self.entry_snr_db) and (purity >= self.min_purity)
        if self.state in (AQSSState.IDLE, AQSSState.ARMING):
            if frame_valid:
                self.accumulator += 1
                self.state = AQSSState.TRIGGERED if self.accumulator >= self.required_hits else AQSSState.ARMING
            else:
                self.accumulator = max(0, self.accumulator - 1)
                if self.accumulator == 0:
                    self.state = AQSSState.IDLE
        elif self.state == AQSSState.TRIGGERED:
            if tnr_db < self.exit_snr_db:
                self.accumulator = max(0, self.accumulator - 1)
                if self.accumulator == 0:
                    self.state = AQSSState.IDLE
            else:
                self.accumulator = self.required_hits
        return {"triggered": self.state == AQSSState.TRIGGERED, "state": self.state, "tnr_db": round(float(tnr_db), 2), "purity": round(float(purity), 3), "persistence": self.accumulator}
