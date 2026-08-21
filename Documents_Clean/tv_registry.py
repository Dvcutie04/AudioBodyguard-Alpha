from bridges.tv_controller import TVControllerFactory

# Multi-target configuration registry
TV_REGISTRY = {
    "tcl_roku_local": {"brand": "tcl", "ip": "192.168.1.50"}, # Update with your local IP if needed
}

def execute_test(name):
    if name not in TV_REGISTRY:
        return {"status": "error", "message": f"Target {name} not found."}
    cfg = TV_REGISTRY[name]
    controller = TVControllerFactory.get_controller(cfg["brand"], cfg["ip"]);
    # Attempt a safe non-destructive query/ping or check instance state
    return {"target": name, "brand": cfg["brand"], "ip": cfg["ip"], "controller": type(controller).__name__, "status": "verified_instantiated"}

if __name__ == "__main__":
    print(execute_test("tcl_roku_local"))

