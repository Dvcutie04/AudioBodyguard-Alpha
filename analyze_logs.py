import json
def analyze():
    try:
        with open('aqss_trials.json', 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print('No logs found yet. Run state_logger.py first!')
        return
    total = len(data)
    if total == 0:
        print('Log file is empty.')
        return
    counts = {}
    for item in data:
        dec = item['decision']
        counts[dec] = counts.get(dec, 0) + 1
    print(f'=== AQSS-36-OMEGA TRIAL METRICS (Total Trials: {total}) ===')
    for dec, count in counts.items():
        pct = (count / total) * 100
        print(f'- {dec}: {count} ({pct:.1f}%)')
if __name__ == '__main__':
    analyze()
