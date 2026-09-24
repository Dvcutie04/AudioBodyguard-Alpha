class Hypothesis:
    def __init__(self, hid: str, description: str, probability: float = 0.0):
        if probability != probability or not (0.0 <= probability <= 1.0):
            raise ValueError("Out of bounds")
        self.hid, self.description, self.probability = hid, description, probability
