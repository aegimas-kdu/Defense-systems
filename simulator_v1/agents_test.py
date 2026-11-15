
from database import initialize_database
from agents.coordinator import AgentCoordinator
from pprint import pprint

# Initialize the database
initialize_database()

# Create the coordinator
coordinator = AgentCoordinator()

# Run a simulation
result = coordinator.run_simulation(
    medicine_name="Paracetamol",
    quantity=100,
    distance=50
)

# Display the results
print("\n===== MULTI-AGENT SIMULATION =====")

print("\nHOSPITAL AGENT:")
pprint(result["hospital"])

print("\nWAREHOUSE AGENT:")
pprint(result["warehouse"])

print("\nTRANSPORTATION AGENT:")
pprint(result["transportation"])
