import socket
import concurrent.futures

class NetworkDeviceScanner:
    def __init__(self, subnet_prefix="192.168.1"):
        self.subnet_prefix = subnet_prefix
        self.port_signatures = {7345: "vizio_tv", 8002: "samsung_tv", 3001: "lg_tv", 7000: "sony_tv"}

    def _check_host(self, ip):
        for port, device_type in self.port_signatures.items():
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(0.3)
                    if s.connect_ex((ip, port)) == 0:
                        return {"ip": ip, "port": port, "device_type": device_type}
            except Exception:
                continue
        return None

    def scan_subnet(self):
        discovered = []
        ips = [f"{self.subnet_prefix}.{i}" for i in range(1, 255)]
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = {executor.submit(self._check_host, ip): ip for ip in ips}
            for f in concurrent.futures.as_completed(futures):
                res = f.result()
                if res:
                    discovered.append(res)
        return discovered
