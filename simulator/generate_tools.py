"""Derives all nine tool files from truth.py. Run:  python -m simulator.generate_tools
Never edit the JSON files by hand: this script is what keeps the three routes equal."""
import json
from pathlib import Path

try:
    from simulator import truth as T
except ModuleNotFoundError:  # pragma: no cover
    import truth as T

TOOLS_DIR = Path(__file__).resolve().parent / 'data' / 'tools'


def build_tools():
    stock_rows = [(w, m, n) for w, meds in T.STOCK.items() for m, n in meds.items()]
    tools = {}

    tools['warehouse_inventory_db'] = ('Warehouse', 'Main ledger for current warehouse stock counts.', [
        {'warehouse_id': w, 'medicine_name': m, 'listed_stock_count': n} for w, m, n in stock_rows])

    tools['shelf_iot_sensors'] = ('Warehouse', 'Physical weight sensor feed for warehouse stock.', [
        {'warehouse_id': w, 'medicine_name': m, 'total_shelf_weight_kg': n * T.KIT_WEIGHT_KG,
         'unit_weight_kg': T.KIT_WEIGHT_KG} for w, m, n in stock_rows])

    tools['inbound_outbound_logs'] = ('Warehouse', 'Movement history for stock inflows and shipments.', [
        {'warehouse_id': w, 'medicine_name': m, 'starting_stock': n + T.SHIPPED_TODAY,
         'total_shipped_today': T.SHIPPED_TODAY} for w, m, n in stock_rows])

    tools['fleet_specs_catalog'] = ('Transportation', 'Vehicle capabilities for cargo, speed, and capacity.', [
        {'vehicle_type': v, 'max_kit_capacity': s['capacity'], 'average_speed_kmh': s['speed']}
        for v, s in T.VEHICLES.items()])

    tools['live_gps_telemetry'] = ('Transportation', 'Real-time vehicle speed, delay and payload limits.', [
        {'vehicle_type': v, 'max_payload_kg': s['capacity'] * T.KIT_WEIGHT_KG,
         'kit_unit_weight_kg': T.KIT_WEIGHT_KG, 'live_speed_kmh': s['speed'],
         'traffic_delay_minutes': 0, 'active_status': 'available'} for v, s in T.VEHICLES.items()])

    tools['route_eta_calculator'] = ('Transportation', 'Calculated route time estimates for dispatch planning.', [
        {'origin_warehouse': w, 'destination_hospital': h, 'vehicle_type': v,
         'cargo_bay_volume_l': T.VEHICLES[v]['capacity'] * T.KIT_BOX_LITERS,
         'kit_box_volume_l': T.KIT_BOX_LITERS, 'estimated_minutes': T.truth_time_minutes(w, h, v)}
        for w, h, v in T.all_routes()])

    tools['gis_distance_matrix'] = ('Logistics', 'Map-based distance and base rate per route.', [
        {'warehouse_id': w, 'hospital_id': h, 'vehicle_type': v, 'map_distance_km': T.truth_distance(w, h),
         'base_rate_per_km': T.VEHICLES[v]['rate']} for w, h, v in T.all_routes()])

    tools['fuel_and_toll_rates'] = ('Logistics', 'Fuel and toll expense per route.', [
        {'warehouse_id': w, 'hospital_id': h, 'vehicle_type': v,
         'vehicle_km_per_liter': T.VEHICLES[v]['km_per_liter'],
         'fuel_price_per_liter': T.VEHICLES[v]['fuel_price'],
         'expected_fuel_liters': T.truth_liters(w, h, v), 'toll_fee': T.truth_toll(w, h, v)}
        for w, h, v in T.all_routes()])

    tools['billing_quote_api'] = ('Logistics', 'Quotes the total trip cost paid by the NGO for a route.', [
        {'warehouse_id': w, 'hospital_id': h, 'vehicle_type': v, 'billed_mileage_km': T.truth_distance(w, h),
         'total_quoted_cost': T.truth_cost(w, h, v)} for w, h, v in T.all_routes()])
    return tools


def main():
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    for tool_id, (domain, description, records) in build_tools().items():
        payload = {'tool_id': tool_id, 'domain': domain, 'description': description, 'records': records}
        (TOOLS_DIR / f'{tool_id}.json').write_text(json.dumps(payload, indent=1), encoding='utf-8')
    print(f'Wrote 9 tool files to {TOOLS_DIR}')


if __name__ == '__main__':
    main()
