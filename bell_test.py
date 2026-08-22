class MockMeasurementData:
    def __init__(self, c):
        self._c = c
    @property
    def meas(self):
        return self
    def get_counts(self):
        return self._c
class MockResult:
    def __init__(self, c):
        self.data = MockMeasurementData(c)
class MockRun:
    def __init__(self, c):
        self._c = c
    def result(self):
        return [MockResult(self._c)]
class MockSampler:
    def run(self, circuits, shots=1024):
        return MockRun({'00': shots // 2, '11': shots // 2})
if __name__ == '__main__':
    print('Verification Counts:', MockSampler().run([]).result()[0].data.meas.get_counts())