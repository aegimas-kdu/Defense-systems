import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / 'data'
TOOLS_DIR = DATA_DIR / 'tools'


def _round_metric(value, digits=2):
    if value is None:
        return None
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return value


def load_json(path):
    with open(path, 'r', encoding='utf-8') as fh:
        return json.load(fh)


def get_agent_registry():
    return load_json(DATA_DIR / 'agents.json')


def get_tool_registry():
    tools = {}
    for tool_path in sorted(TOOLS_DIR.glob('*.json')):
        payload = load_json(tool_path)
        tools[payload['tool_id']] = payload
    return tools


def get_tool_by_id(tool_id):
    return get_tool_registry().get(tool_id)


def _distance_for_route(warehouse_id, hospital_id):
    gis_tool = get_tool_by_id('gis_distance_matrix')
    for record in gis_tool.get('records', []):
        if record.get('warehouse_id') == warehouse_id and record.get('hospital_id') == hospital_id:
            return float(record.get('distance_km', 100.0))
    return 100.0


def _compute_stock_value(tool_id, record):
    if tool_id == 'warehouse_inventory_db':
        return record.get('listed_stock_count')
    if tool_id == 'shelf_iot_sensors':
        weight = record.get('total_shelf_weight_kg', 0)
        unit_weight = record.get('unit_weight_kg', 1)
        return weight / unit_weight if unit_weight else weight
    if tool_id == 'inbound_outbound_logs':
        return record.get('remaining_stock', record.get('starting_stock', 0) - record.get('total_shipped_today', 0))
    return None


def _compute_time_hours(tool_id, record, warehouse_id=None, hospital_id=None, vehicle_type=None):
    if tool_id == 'route_eta_calculator':
        minutes = record.get('estimated_minutes', 0)
        return minutes / 60.0
    if tool_id == 'fleet_specs_catalog':
        distance_km = _distance_for_route(warehouse_id, hospital_id)
        speed = record.get('average_speed_kmh')
        return distance_km / speed if speed else None
    if tool_id == 'live_gps_telemetry':
        distance_km = _distance_for_route(warehouse_id, hospital_id)
        speed = record.get('live_speed_kmh')
        delay_minutes = record.get('traffic_delay_minutes', 0)
        if speed:
            return (distance_km / speed) + (delay_minutes / 60.0)
        return (delay_minutes / 60.0)
    return None


def _compute_cost_value(tool_id, record, warehouse_id=None, hospital_id=None, vehicle_type=None):
    if tool_id == 'billing_quote_api':
        return record.get('total_quoted_cost')
    if tool_id == 'fuel_and_toll_rates':
        distance_km = _distance_for_route(warehouse_id, hospital_id)
        base_rate = record.get('cost_per_km', 0)
        toll = record.get('highway_toll_fee', 0)
        return (distance_km * base_rate) + toll
    if tool_id == 'gis_distance_matrix':
        distance_km = record.get('distance_km', 0)
        rate = 1.1
        return distance_km * rate
    return None


def _build_comparable_read(agent, primary_tool, backup_tool, source, raw_value, quantity=None, time_hours=None, cost=None, backup_value=None):
    rounded_raw = _round_metric(raw_value)
    return {
        'agent_id': agent['agent_id'],
        'domain': agent['domain'],
        'tool_id': primary_tool.get('tool_id'),
        'source': source,
        'backup_tool': agent.get('backup_tool'),
        'backup_answer': _round_metric(backup_value),
        'answer': rounded_raw,
        'quantity': _round_metric(quantity),
        'time_hours': _round_metric(time_hours),
        'cost': _round_metric(cost),
    }


def get_tool_read(agent_id, question, warehouse=None, hospital=None, vehicle=None):
    agents = get_agent_registry()
    agent = next(item for item in agents if item['agent_id'] == agent_id)
    primary_tool = get_tool_by_id(agent['primary_tool'])
    backup_tool = get_tool_by_id(agent['backup_tool'])

    if not primary_tool:
        raise ValueError(f'Unknown primary tool for {agent_id}')

    if question == 'stock':
        for record in primary_tool.get('records', []):
            if record.get('warehouse_id') == warehouse and record.get('kit_type') == 'K1':
                quantity = _compute_stock_value(primary_tool.get('tool_id'), record)
                return _build_comparable_read(
                    agent,
                    primary_tool,
                    backup_tool,
                    'primary',
                    quantity,
                    quantity=quantity,
                    backup_value=(
                        _compute_stock_value(backup_tool.get('tool_id'), backup_tool.get('records', [{}])[0])
                        if backup_tool and backup_tool.get('records') else backup_tool.get('fallback_value')
                    ),
                )
        quantity = primary_tool.get('fallback_value')
        return _build_comparable_read(
            agent,
            primary_tool,
            backup_tool,
            'primary',
            quantity,
            quantity=quantity,
            backup_value=(backup_tool.get('fallback_value') if backup_tool else None),
        )

    if question == 'distance':
        for record in primary_tool.get('records', []):
            if record.get('warehouse_id') == warehouse and record.get('hospital_id') == hospital:
                distance_km = record.get('distance_km', 0)
                rounded_distance_km = _round_metric(distance_km)
                return _build_comparable_read(
                    agent,
                    primary_tool,
                    backup_tool,
                    'primary',
                    rounded_distance_km,
                    time_hours=(_round_metric((distance_km / 60.0)) if distance_km else None),
                    backup_value=(
                        _round_metric(backup_tool.get('records', [{}])[0].get('distance_km'))
                        if backup_tool and backup_tool.get('records') else _round_metric(backup_tool.get('fallback_value'))
                    ),
                )

    if question == 'cost':
        for record in primary_tool.get('records', []):
            matches_route = record.get('warehouse_id') == warehouse and record.get('hospital_id') == hospital
            matches_vehicle = record.get('vehicle_type') == vehicle
            if matches_route or matches_vehicle:
                cost_value = _compute_cost_value(primary_tool.get('tool_id'), record, warehouse, hospital, vehicle)
                resolved_cost = cost_value if cost_value is not None else record.get('total_quoted_cost', primary_tool.get('fallback_value'))
                return _build_comparable_read(
                    agent,
                    primary_tool,
                    backup_tool,
                    'primary',
                    resolved_cost,
                    cost=resolved_cost,
                    backup_value=(
                        _compute_cost_value(backup_tool.get('tool_id'), backup_tool.get('records', [{}])[0], warehouse, hospital, vehicle)
                        if backup_tool and backup_tool.get('records') else backup_tool.get('fallback_value')
                    ),
                )

    if question == 'vehicle':
        for record in primary_tool.get('records', []):
            matches_vehicle = record.get('vehicle_type') == vehicle
            matches_origin = record.get('current_location') == warehouse or record.get('origin_warehouse') == warehouse
            if matches_vehicle or matches_origin:
                time_hours = _compute_time_hours(primary_tool.get('tool_id'), record, warehouse, hospital, vehicle)
                raw_value = time_hours if time_hours is not None else record.get('estimated_minutes', record.get('average_speed_kmh', record.get('live_speed_kmh', primary_tool.get('fallback_value'))))
                return _build_comparable_read(
                    agent,
                    primary_tool,
                    backup_tool,
                    'primary',
                    raw_value,
                    time_hours=time_hours,
                    backup_value=(
                        _compute_time_hours(backup_tool.get('tool_id'), backup_tool.get('records', [{}])[0], warehouse, hospital, vehicle)
                        if backup_tool and backup_tool.get('records') else backup_tool.get('fallback_value')
                    ),
                )

    return _build_comparable_read(
        agent,
        primary_tool,
        backup_tool,
        'primary',
        primary_tool.get('fallback_value'),
    )
