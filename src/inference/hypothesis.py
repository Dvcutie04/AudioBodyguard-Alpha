class Hypothesis:
    def __init__(self, hid: str, description: str, probability: float = 0.0):
        if probability != probability or not (0.0 <= probability <= 1.0):
            raise ValueError("Hypothesis probability must be between 0.0 and 1.0")
        self.hid = hid
        self.description = description
        self.probability = probability
