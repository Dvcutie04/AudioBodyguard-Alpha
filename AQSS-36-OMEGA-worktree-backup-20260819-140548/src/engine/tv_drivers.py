class TVDriver:
    @staticmethod
    def dispatch(p, ip, c):
        print(f"[{p.upper()}] Dispatched {c} to {ip}")
        return True
