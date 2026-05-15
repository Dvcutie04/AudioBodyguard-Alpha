import numpy as np; import time
T, SR, BS = 0.35, 48000, 4800; n = np.random.normal(0, 0.1, BS); t = np.zeros(BS); t[2000:2500] = np.linspace(0, 0.15, 500); s = n + t; hf, hs, tau = 0.0, 0.0, 0.0; trig = []
for i, x in enumerate(s): eg = abs(x); tau += 1.2 if eg < 0.05 else 0.8; hf = (hf * 0.7) + (eg * 0.3); hs = (hs * 0.98) + (eg * 0.02); ht = (hf * 0.6) + (hs * 0.4);  if ht > T: trig.append(i) if trig: print(f'✅ THREAT DETECTED | Latency: {((trig[0]-2000)/SR)*1000:.2f} ms') else: print('❌ THREAT MISSED') print(f'⏱️ Tau: {tau:.2f}')
