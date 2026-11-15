
try:
    from simulator.participants.warehouse import get_warehouse_registry, get_distance_km
    from simulator.participants.hospital import find_camp
except ModuleNotFoundError:  # pragma: no cover
    from participants.warehouse import get_warehouse_registry, get_distance_km
    from participants.hospital import find_camp


class TransportationAgent:
    def __init__(self):
        self.name = "Transport Agent"

    def arrange_delivery(self, medicine_name, quantity, camp_name, warehouse_name, warehouse_distance_km):
        camp = find_camp(camp_name)
        if camp is None:
            return {
                "agent": self.name,
                "decision": "Rejected",
                "reason": "Clinic route could not be calculated.",
            }

        warehouse = next((item for item in get_warehouse_registry() if item["warehouse_name"] == warehouse_name), None)
        if warehouse is None:
            return {
                "agent": self.name,
                "decision": "Rejected",
                "reason": "Warehouse record not found.",
            }

        vehicle = warehouse["fleet"][0]
        speed_kmh = vehicle["speed_kmh"]
        cost_per_km = vehicle["cost_per_km"]
        distance_km = warehouse_distance_km
        delivery_time_hours = distance_km / speed_kmh
        transport_cost = distance_km * cost_per_km

        return {
            "agent": self.name,
            "decision": "Approved",
            "reason": "Route approved within the operating budget.",
            "vehicle": vehicle["name"],
            "distance_km": round(distance_km, 2),
            "delivery_time_hours": round(delivery_time_hours, 2),
            "transportation_cost": round(transport_cost, 2),
            "medicine_name": medicine_name,
            "quantity": quantity,
            "clinic_name": camp_name,
            "warehouse_name": warehouse_name,
        }
