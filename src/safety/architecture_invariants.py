class ArchitectureInvariants:
    @staticmethod
    def assert_bounds(value: float, lower: float = 0.0, upper: float = 100.0) -> bool:
        return lower <= value <= upper
    @staticmethod
    def assert_safety_retention(before: float, after: float) -> bool:
        return after >= before
    @staticmethod
    def assert_monotonic_version(prev: int, nxt: int) -> bool:
        return nxt > prev
    @staticmethod
    def assert_side_effect_free(changed: bool) -> bool:
        return not changed
