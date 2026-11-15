"""Reading logic. Every agent answers the SAME question through its own tool route.

Rules enforced here (Simulator Audit Guide, Phase 1 and 3):
  * a record must match ALL key fields, otherwise an error is raised (no first-record bug, no fallback);
  * the backup reading uses the same key and the same question as the primary reading;
  * no tool reads another tool; time derivations receive the resolved distance as an input;
  * answers are whole numbers in the question's unit (kits, km, minutes, cost units);
  * a claim has the agreed shape: mission_id, question, key, agent_id, domain, answer, readings, inputs.
"""
import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / 'data'
TOOLS_DIR = DATA_DIR / 'tools'

ROUTE_KEY = ('warehouse', 'hospital', 'vehicle')
QUESTIONS = {
    'Q1': {'name': 'stock',    'domain': 'Warehouse',      'unit': 'kits',       'key': ('warehouse', 'medicine')},
    'Q2': {'name': 'capacity', 'domain': 'Transportation', 'unit': 'kits',       'key': ROUTE_KEY},
    'Q3': {'name': 'distance', 'domain': 'Logistics',      'unit': 'km',         'key': ROUTE_KEY},
    'Q4': {'name': 'time',     'domain': 'Transportation', 'unit': 'minutes',    'key': ROUTE_KEY},
    'Q5': {'name': 'cost',     'domain': 'Logistics',      'unit': 'cost units', 'key': ROUTE_KEY},
}

# Which record fields identify a row in each tool, and which mission-key field fills them.
TOOL_KEYS = {
    'warehouse_inventory_db': {'warehouse_id': 'warehouse', 'medicine_name': 'medicine'},
    'shelf_iot_sensors':      {'warehouse_id': 'warehouse', 'medicine_name': 'medicine'},
    'inbound_outbound_logs':  {'warehouse_id': 'warehouse', 'medicine_name': 'medicine'},
    'fleet_specs_catalog':    {'vehicle_type': 'vehicle'},
    'live_gps_telemetry':     {'vehicle_type': 'vehicle'},
    'route_eta_calculator':   {'origin_warehouse': 'warehouse', 'destination_hospital': 'hospital',
                               'vehicle_type': 'vehicle'},
    'gis_distance_matrix':    {'warehouse_id': 'warehouse', 'hospital_id': 'hospital', 'vehicle_type': 'vehicle'},
    'fuel_and_toll_rates':    {'warehouse_id': 'warehouse', 'hospital_id': 'hospital', 'vehicle_type': 'vehicle'},
    'billing_quote_api':      {'warehouse_id': 'warehouse', 'hospital_id': 'hospital', 'vehicle_type': 'vehicle'},
}


def _distance_input(inputs):
    if not inputs or 'resolved_distance_km' not in inputs:
        raise ValueError("Q4 needs inputs['resolved_distance_km'] (the Coordinator resolves Q3 first)")
    return inputs['resolved_distance_km']


# ---- the 15 derivations: (question, tool_id) -> whole number in the answer's unit ----
DERIVE = {
    ('Q1', 'warehouse_inventory_db'): lambda r, i: r['listed_stock_count'],
    ('Q1', 'shelf_iot_sensors'):      lambda r, i: round(r['total_shelf_weight_kg'] / r['unit_weight_kg']),
    ('Q1', 'inbound_outbound_logs'):  lambda r, i: r['starting_stock'] - r['total_shipped_today'],

    ('Q2', 'fleet_specs_catalog'):    lambda r, i: r['max_kit_capacity'],
    ('Q2', 'live_gps_telemetry'):     lambda r, i: round(r['max_payload_kg'] / r['kit_unit_weight_kg']),
    ('Q2', 'route_eta_calculator'):   lambda r, i: round(r['cargo_bay_volume_l'] / r['kit_box_volume_l']),

    ('Q3', 'gis_distance_matrix'):    lambda r, i: r['map_distance_km'],
    ('Q3', 'fuel_and_toll_rates'):    lambda r, i: round(r['expected_fuel_liters'] * r['vehicle_km_per_liter']),
    ('Q3', 'billing_quote_api'):      lambda r, i: r['billed_mileage_km'],

    ('Q4', 'fleet_specs_catalog'):    lambda r, i: round(_distance_input(i) * 60 / r['average_speed_kmh']),
    ('Q4', 'live_gps_telemetry'):     lambda r, i: round(_distance_input(i) * 60 / r['live_speed_kmh']
                                                         + r['traffic_delay_minutes']),
    ('Q4', 'route_eta_calculator'):   lambda r, i: r['estimated_minutes'],

    ('Q5', 'gis_distance_matrix'):    lambda r, i: round(r['map_distance_km'] * r['base_rate_per_km']),
    ('Q5', 'fuel_and_toll_rates'):    lambda r, i: round(r['expected_fuel_liters'] * r['fuel_price_per_liter']
                                                         + r['toll_fee']),
    ('Q5', 'billing_quote_api'):      lambda r, i: r['total_quoted_cost'],
}


# ---- loading (once) --------------------------------------------------------
def _load_json(path):
    with open(path, 'r', encoding='utf-8') as fh:
        return json.load(fh)


@lru_cache(maxsize=1)
def get_world():
    """Agents and tools, loaded once. Attacks must deepcopy this before mutating it."""
    agents = _load_json(DATA_DIR / 'agents.json')
    tools = {}
    for path in sorted(TOOLS_DIR.glob('*.json')):
        payload = _load_json(path)
        tools[payload['tool_id']] = payload
    return {'agents': agents, 'tools': tools}


def get_agent_registry():
    return get_world()['agents']


def get_tool_registry():
    return get_world()['tools']


def get_tool_by_id(tool_id):
    return get_world()['tools'].get(tool_id)


# ---- lookup and reading ----------------------------------------------------
def find_record(world, tool_id, key):
    tool = world['tools'].get(tool_id)
    if tool is None:
        raise LookupError(f'Unknown tool {tool_id}')
    wanted = {}
    for record_field, key_field in TOOL_KEYS[tool_id].items():
        if key.get(key_field) is None:
            raise ValueError(f'{tool_id} needs key field "{key_field}"')
        wanted[record_field] = key[key_field]
    matches = [r for r in tool['records'] if all(r.get(f) == v for f, v in wanted.items())]
    if len(matches) != 1:
        raise LookupError(f'{tool_id}: {len(matches)} records match {wanted}, expected exactly 1')
    return matches[0]


def read_tool(world, tool_id, question, key, inputs=None):
    derive = DERIVE.get((question, tool_id))
    if derive is None:
        raise ValueError(f'Tool {tool_id} cannot answer {question}')
    return derive(find_record(world, tool_id, key), inputs or {})


def get_claim(agent_id, question, key, inputs=None, mission_id=None, world=None):
    world = world or get_world()
    agent = next((a for a in world['agents'] if a['agent_id'] == agent_id), None)
    if agent is None:
        raise ValueError(f'Unknown agent {agent_id}')
    spec = QUESTIONS[question]
    if agent['domain'] != spec['domain']:
        raise ValueError(f'{agent_id} is a {agent["domain"]} agent; {question} belongs to {spec["domain"]}')
    inputs = dict(inputs or {})
    readings = [
        {'tool_id': tool_id, 'value': read_tool(world, tool_id, question, key, inputs)}
        for tool_id in (agent['primary_tool'], agent['backup_tool'])
    ]
    return {
        'mission_id': mission_id,
        'question': question,
        'key': [key[f] for f in spec['key']],
        'agent_id': agent_id,
        'domain': agent['domain'],
        'answer': readings[0]['value'],   # the agent's own (primary) reading
        'readings': readings,             # primary first, backup second
        'inputs': inputs,
    }
