
try:
    from simulator.participants.hospital import get_camp_registry
except ModuleNotFoundError:  # pragma: no cover
    from participants.hospital import get_camp_registry


class HospitalAgent:
    def __init__(self):
        self.name = "Clinic Coordinator"

    def analyze_needs(self):
        return get_camp_registry()

    def create_order_proposal(self, medicine_name, quantity, camp_name):
        camp = None
        for entry in get_camp_registry():
            if entry["name"].lower() == camp_name.lower():
                camp = entry
                break

        return {
            "agent": self.name,
            "clinic_name": camp_name,
            "location": camp["location"] if camp else None,
            "medicine_name": medicine_name,
            "requested_quantity": quantity,
            "decision": "Order Required",
            "reason": "Clinic request submitted for internal logistics review.",
        }
