
from database import get_data


# Retrieve all registered vehicles
def get_vehicles():

    return get_data("vehicles")


# Find vehicles that can transport the requested quantity
def get_available_vehicles(quantity):

    vehicles = get_vehicles()

    suitable_vehicles = []

    for vehicle in vehicles:

        if (
            vehicle["available"] == 1
            and vehicle["capacity_units"] >= quantity
        ):

            suitable_vehicles.append(vehicle)

    return suitable_vehicles


# Select the smallest suitable vehicle
def select_vehicle(quantity):

    vehicles = get_available_vehicles(quantity)

    if not vehicles:
        return None

    vehicles.sort(
        key=lambda vehicle: vehicle["capacity_units"]
    )

    return vehicles[0]


# Calculate delivery information
def calculate_delivery(vehicle, distance):

    speed = vehicle["average_speed_kmh"]
    cost_per_km = vehicle["cost_per_km"]

    delivery_time = distance / speed

    transportation_cost = distance * cost_per_km

    return {
        "vehicle": vehicle["vehicle_name"],
        "distance_km": distance,
        "delivery_time_hours": round(delivery_time, 2),
        "transportation_cost": transportation_cost
    }
