class LegacyPhysicalIOQuarantined(RuntimeError):
    pass


class BaseTVController:
    def __init__(self, ip, **kwargs):
        self.ip = ip

    def _reject(self, operation):
        raise LegacyPhysicalIOQuarantined(
            f"{operation} requires an authorized Device Fabric intent"
        )

    def power_on(self):
        return self._reject("power_on")

    def power_off(self):
        return self._reject("power_off")


class VizioTVController(BaseTVController):
    def __init__(self, ip, token=""):
        super().__init__(ip)
        self.token = token


class SamsungTVController(BaseTVController):
    pass


class LGWebOSTVController(BaseTVController):
    pass


class SonyBraviaTVController(BaseTVController):
    pass


class TCLRokuTVController(BaseTVController):
    pass


class AmazonFireTVController(BaseTVController):
    pass


class RokuTVController(TCLRokuTVController):
    pass


class TVControllerFactory:
    @staticmethod
    def get_controller(device_type, ip, **kwargs):
        normalized = device_type.casefold()
        if "vizio" in normalized:
            return VizioTVController(ip, kwargs.get("token", ""))
        if "samsung" in normalized:
            return SamsungTVController(ip)
        if "lg" in normalized:
            return LGWebOSTVController(ip)
        if "sony" in normalized:
            return SonyBraviaTVController(ip)
        if "tcl" in normalized or "roku" in normalized:
            return TCLRokuTVController(ip)
        if "fire" in normalized or "amazon" in normalized:
            return AmazonFireTVController(ip)
        raise ValueError(f"Unsupported brand: {device_type}")
