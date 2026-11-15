
from database import initialize_database
from agents.coordinator import AgentCoordinator
from pprint import pprint

initialize_database()

coordinator = AgentCoordinator()

result = coordinator.run_simulation(
    medicine_name="Paracetamol",
    quantity=100,
    distance=50
)

print("\n===== MULTI-AGENT SIMULATION =====")

print("\nHOSPITAL AGENT:")
pprint(result["hospital"])

print("\nWAREHOUSE AGENT:")
pprint(result["warehouse"])

print("\nTRANSPORTATION AGENT:")
pprint(result["transportation"])

print("\n===== SIMULATION DECISION LOG =====")

for log in result["logs"]:
    print("->", log)
