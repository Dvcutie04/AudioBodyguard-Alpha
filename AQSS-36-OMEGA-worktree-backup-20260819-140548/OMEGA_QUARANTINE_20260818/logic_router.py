import os

ALPHA_LOG = "alpha_current.txt"
V2_BACKLOG = "version_2_roadmap.txt"
V2_KEYWORDS = ["quantum", "bayesian", "qubit", "non-stationary state estimation"]

def router_agent(input_data):
    print(f"Analyzing incoming data: '{input_data}'...")
    is_v2_feature = any(keyword in input_data.lower() for keyword in V2_KEYWORDS)
    
    if is_v2_feature:
        print(">> LOGIC TRIGGER: Advanced feature detected.")
        trigger_v2_handoff(input_data)
    else:
        print(">> LOGIC TRIGGER: Core feature detected.")
        route_to_alpha(input_data)

def trigger_v2_handoff(data):
    with open(V2_BACKLOG, "a") as f:
        f.write(f"- {data}\n")
    print(f"[HANDOFF] Successfully routed to {V2_BACKLOG}. Staying focused on Alpha.\n")

def route_to_alpha(data):
    with open(ALPHA_LOG, "a") as f:
        f.write(f"- {data}\n")
    print(f"[ROUTED] Successfully added to {ALPHA_LOG}.\n")

if __name__ == "__main__":
    print("=== STARTING AGENT HANDOFF TEST ===\n")
    
    test_input_1 = "Adjust BAMBOO haptic pulse duration for better acoustic matching."
    router_agent(test_input_1)
    
    test_input_2 = "Integrate variational quantum Bayesian persistence for predictive volume spikes."
    router_agent(test_input_2)
    
    print("=== ROUTING COMPLETE ===")
