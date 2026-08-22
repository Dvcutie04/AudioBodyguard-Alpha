import json, datetime
from acoustic_engine import AcousticIngestionEngine
from signal_router import SignalRouter
class StateLogger:
    def __init__(self, log_file='aqss_trials.json'):
        self.log_file = log_file
    def log_trial(self, event, weights, decision):
        record = {'timestamp': datetime.datetime.now().isoformat(), 'event': event, 'weights': weights, 'decision': decision}
        try:
            with open(self.log_file, 'r') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = []
        data.append(record)
        with open(self.log_file, 'w') as f:
            json.dump(data, f, indent=4)
        print(f'Trial logged to {self.log_file}. Total trials: {len(data)}')
if __name__ == '__main__':
    eng = AcousticIngestionEngine()
    router = SignalRouter()
    logger = StateLogger()
    ev = eng.simulate_mic_trigger()
    w = eng.compute_quantum_weights(ev)
    dec = router.evaluate_signal(w)
    logger.log_trial(ev, w, dec)
