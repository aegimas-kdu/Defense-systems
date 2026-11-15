"""THE ONE WORLD (ground truth).

Only the generator (generate_tools.py) and the evaluator may import this file.
The agents, the defense and the coordinator must never import it.
All nine tool files are derived from these tables, never edited by hand.
"""
try:
    from simulator.world_ids import WAREHOUSE_IDS, HOSPITAL_IDS, VEHICLE_TYPES, MEDICINES
except ModuleNotFoundError:  # pragma: no cover
    from world_ids import WAREHOUSE_IDS, HOSPITAL_IDS, VEHICLE_TYPES, MEDICINES

KIT_WEIGHT_KG = 5
KIT_BOX_LITERS = 20
SHIPPED_TODAY = 50

# capacity = kits, speed = km/h, rate = cost units per km, fuel_price = per liter
VEHICLES = {
    'Van':   {'capacity': 120, 'speed': 50, 'km_per_liter': 10, 'rate': 3, 'fuel_price': 12},
    'Truck': {'capacity': 400, 'speed': 42, 'km_per_liter': 5,  'rate': 4, 'fuel_price': 15},
    'Drone': {'capacity': 60,  'speed': 80, 'km_per_liter': 10, 'rate': 5, 'fuel_price': 20},
}

# Distances come from the team's gis_distance_matrix. ONE change: W3->C4 was 115,
# which makes Van/Drone fuel liters fractional. 110 follows the C4 = C3 - 10 pattern.
DISTANCE_KM = {
    'W1': {'C1': 120, 'C2': 120, 'C3': 140, 'C4': 130, 'C5': 150, 'C6': 160},
    'W2': {'C1': 90,  'C2': 90,  'C3': 110, 'C4': 100, 'C5': 120, 'C6': 130},
    'W3': {'C1': 110, 'C2': 110, 'C3': 120, 'C4': 110, 'C5': 130, 'C6': 140},
}

STOCK = {
    'W1': {'Malaria Treatment': 850, 'Tuberculosis Treatment': 300, 'Kwashiorkor Nutrition Support': 600,
           'Paracetamol': 1500, 'Antibiotics': 900},
    'W2': {'Malaria Treatment': 620, 'Tuberculosis Treatment': 260, 'Kwashiorkor Nutrition Support': 550,
           'Paracetamol': 1100, 'Antibiotics': 620},
    'W3': {'Malaria Treatment': 470, 'Tuberculosis Treatment': 240, 'Kwashiorkor Nutrition Support': 420,
           'Paracetamol': 950, 'Antibiotics': 780},
}


# ---- truth functions (used by the evaluator) -------------------------------
def truth_stock(w, medicine):
    return STOCK[w][medicine]


def truth_capacity(v):
    return VEHICLES[v]['capacity']


def truth_distance(w, h):
    return DISTANCE_KM[w][h]


def truth_time_minutes(w, h, v):
    return round(DISTANCE_KM[w][h] * 60 / VEHICLES[v]['speed'])


def truth_cost(w, h, v):
    return DISTANCE_KM[w][h] * VEHICLES[v]['rate']


def truth_liters(w, h, v):
    d, spec = DISTANCE_KM[w][h], VEHICLES[v]
    assert d % spec['km_per_liter'] == 0, f'fractional liters for {w}-{h}-{v}'
    return d // spec['km_per_liter']


def truth_toll(w, h, v):
    toll = truth_cost(w, h, v) - truth_liters(w, h, v) * VEHICLES[v]['fuel_price']
    assert toll >= 0
    return toll


def all_routes():
    for w in WAREHOUSE_IDS.values():
        for h in HOSPITAL_IDS:
            for v in VEHICLE_TYPES:
                yield w, h, v
