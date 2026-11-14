
from math import atan2, cos, radians, sin, sqrt

WAREHOUSE_REGISTRY = [
    {
        "warehouse_name": "Kigali Central Warehouse",
        "location": {"latitude": -1.9441, "longitude": 30.0619},
        "budget_limit": 12000,
        "cost_per_km": 8,
        "handling_fee": 150,
        "fleet": [{"name": "Truck 12", "speed_kmh": 45, "cost_per_km": 8}],
        "stock": {
            "Malaria Treatment": 850,
            "Tuberculosis Treatment": 300,
            "Kwashiorkor Nutrition Support": 600,
            "Paracetamol": 1500,
            "Antibiotics": 900,
        },
    },
    {
        "warehouse_name": "Gitega Regional Warehouse",
        "location": {"latitude": -3.4296, "longitude": 29.9308},
        "budget_limit": 12000,
        "cost_per_km": 7,
        "handling_fee": 120,
        "fleet": [{"name": "Truck 7", "speed_kmh": 42, "cost_per_km": 7}],
        "stock": {
            "Malaria Treatment": 620,
            "Tuberculosis Treatment": 260,
            "Kwashiorkor Nutrition Support": 550,
            "Paracetamol": 1100,
            "Antibiotics": 620,
        },
    },
    {
        "warehouse_name": "Bujumbura Supply Hub",
        "location": {"latitude": -3.3764, "longitude": 29.3604},
        "budget_limit": 13000,
        "cost_per_km": 9,
        "handling_fee": 160,
        "fleet": [{"name": "Truck 18", "speed_kmh": 40, "cost_per_km": 9}],
        "stock": {
            "Malaria Treatment": 470,
            "Tuberculosis Treatment": 240,
            "Kwashiorkor Nutrition Support": 420,
            "Paracetamol": 950,
            "Antibiotics": 780,
        },
    },
]


def get_warehouse_registry():
    return WAREHOUSE_REGISTRY


def get_warehouse_stock():
    stock = []
    for warehouse in WAREHOUSE_REGISTRY:
        for medicine_name, quantity in warehouse["stock"].items():
            stock.append(
                {
                    "warehouse_name": warehouse["warehouse_name"],
                    "medicine_name": medicine_name,
                    "quantity": quantity,
                    "location": warehouse["location"],
                }
            )
    return stock


def get_medicine_stock(warehouse_name, medicine_name):
    for warehouse in WAREHOUSE_REGISTRY:
        if warehouse["warehouse_name"].lower() == warehouse_name.lower():
            quantity = warehouse["stock"].get(medicine_name)
            if quantity is None:
                return None
            return {"warehouse_name": warehouse_name, "medicine_name": medicine_name, "quantity": quantity}
    return None


def get_distance_km(loc_a, loc_b):
    lat1, lon1 = radians(loc_a["latitude"]), radians(loc_a["longitude"])
    lat2, lon2 = radians(loc_b["latitude"]), radians(loc_b["longitude"])

    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    earth_radius_km = 6371
    return earth_radius_km * c


def check_stock(medicine_name):
    for warehouse in WAREHOUSE_REGISTRY:
        if medicine_name in warehouse["stock"]:
            return {
                "warehouse_name": warehouse["warehouse_name"],
                "medicine_name": medicine_name,
                "quantity": warehouse["stock"][medicine_name],
            }
    return None
