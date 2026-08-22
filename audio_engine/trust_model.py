class TrustEngine:
    def __init__(self, alpha=0.2, initial_trust=1.0):
        self.alpha = alpha
        self.instant_trust = initial_trust
        self.long_term_trust = initial_trust

    def update(self, freshness_factor=1.0, noise_factor=1.0, conflict_factor=1.0, stability_factor=1.0):
        self.instant_trust = max(0.0, min(1.0, freshness_factor * noise_factor * conflict_factor * stability_factor))
        self.long_term_trust = max(0.0, min(1.0, (self.alpha * self.instant_trust) + ((1.0 - self.alpha) * self.long_term_trust)))
        return self.long_term_trust

    @property
    def effective_trust(self):
        return (self.alpha * self.instant_trust) + ((1.0 - self.alpha) * self.long_term_trust)
