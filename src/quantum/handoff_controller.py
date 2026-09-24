class QuantumHandoffController:
    def __init__(self, enter_threshold=0.8, exit_threshold=0.5):
        self.state = "LOCAL"
        self.enter = enter_threshold
        self.exit = exit_threshold
