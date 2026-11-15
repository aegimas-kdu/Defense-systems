
try:
    from simulator.participants.warehouse import (
        get_warehouse_registry,
        get_distance_km,
        get_medicine_stock,
    )
    from simulator.participants.hospital import find_camp
except ModuleNotFoundError:  # pragma: no cover
    from participants.warehouse import (
        get_warehouse_registry,
        get_distance_km,
        get_medicine_stock,
    )
    from participants.hospital import find_camp


class WarehouseAgent:
    def __init__(self):
        self.name = "Warehouse Agent"

    def evaluate_order(self, proposal):
        medicine_name = proposal["medicine_name"]
        requested_quantity = proposal["requested_quantity"]
        camp_name = proposal["clinic_name"]

        if requested_quantity <= 0:
            return {
                "agent": self.name,
                "medicine_name": medicine_name,
                "decision": "Rejected",
                "reason": "Invalid requested quantity.",
            }

        camp = find_camp(camp_name)
        if camp is None:
            return {
                "agent": self.name,
                "medicine_name": medicine_name,
                "decision": "Rejected",
                "reason": "Clinic is not registered in the system.",
            }

        candidates = []
        for warehouse in get_warehouse_registry():
            stock = get_medicine_stock(warehouse["warehouse_name"], medicine_name)
            if stock is None:
                continue
            if stock["quantity"] < requested_quantity:
                continue

            distance_km = get_distance_km(camp["location"], warehouse["location"])
            transport_cost = distance_km * warehouse["cost_per_km"] + warehouse["handling_fee"]

            if transport_cost > warehouse["budget_limit"]:
                continue

            candidates.append(
                {
                    "warehouse_name": warehouse["warehouse_name"],
                    "medicine_name": medicine_name,
                    "available_stock": stock["quantity"],
                    "distance_km": round(distance_km, 2),
                    "transport_cost": round(transport_cost, 2),
                    "budget_limit": warehouse["budget_limit"],
                }
            )

        if not candidates:
            return {
                "agent": self.name,
                "medicine_name": medicine_name,
                "clinic_name": camp_name,
                "requested_quantity": requested_quantity,
                "decision": "Rejected",
                "reason": "No warehouse has enough stock within the current budget.",
            }

        best = min(candidates, key=lambda item: (item["transport_cost"], item["distance_km"]))
        return {
            "agent": self.name,
            "medicine_name": medicine_name,
            "clinic_name": camp_name,
            "requested_quantity": requested_quantity,
            "available_stock": best["available_stock"],
            "warehouse_name": best["warehouse_name"],
            "distance_km": best["distance_km"],
            "transport_cost": best["transport_cost"],
            "decision": "Approved",
            "reason": "Nearest warehouse with sufficient stock and budget feasibility was selected.",
        }
