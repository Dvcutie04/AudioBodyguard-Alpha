class MeshClock:
    def __init__(self, t=0, d=0.0):
        self.t, self.d, self.o = int(t), float(d), 0
    def advance(self, dt):
        if dt < 0: raise ValueError()
        self.t += int(dt * (1.0 + self.d / 1e6))
    def now_ms(self): return self.t + self.o
    def calibrate(self, rt): self.o = rt - self.t
    def measure_skew(self, o): return abs(self.now_ms() - o.now_ms())
