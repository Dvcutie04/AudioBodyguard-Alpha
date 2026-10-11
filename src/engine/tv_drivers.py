class TVDriver:
    """Reference stub with no physical transport or execution authority."""

    @staticmethod
    def dispatch(p, ip, c):
        print(f"[NOT_EXECUTED] Legacy TV proposal: {c} ({p}, {ip})")
        return False
