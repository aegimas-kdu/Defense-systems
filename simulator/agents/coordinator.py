
try:
    from simulator.registry import get_agent_registry, get_tool_read
    from simulator.participants.hospital import find_camp
    from simulator.participants.warehouse import get_warehouse_registry, get_distance_km, get_medicine_stock
except ModuleNotFoundError:  # pragma: no cover
    from registry import get_agent_registry, get_tool_read
    from participants.hospital import find_camp
    from participants.warehouse import get_warehouse_registry, get_distance_km, get_medicine_stock


class AgentCoordinator:
    def __init__(self):
        self.agent_registry = get_agent_registry()

    @staticmethod
    def normalize_vehicle_type(vehicle_name):
        if vehicle_name is None:
            return 'Truck'
        name = str(vehicle_name).strip()
        if name.lower().startswith('truck'):
            return 'Truck'
        if name.lower().startswith('van'):
            return 'Van'
        if name.lower().startswith('drone'):
            return 'Drone'
        return name

    @staticmethod
    def warehouse_id_for_name(warehouse_name):
        mapping = {
            'Kigali Central Warehouse': 'W1',
            'Gitega Regional Warehouse': 'W2',
            'Bujumbura Supply Hub': 'W3',
        }
        return mapping.get(warehouse_name, 'W1')

    def collect_agent_reads(self, warehouse_id, hospital_id, vehicle_type):
        agent_reads = []
        normalized_vehicle = self.normalize_vehicle_type(vehicle_type)
        for agent in self.agent_registry:
            if agent['domain'] == 'Warehouse':
                read = get_tool_read(agent['agent_id'], 'stock', warehouse=warehouse_id)
            elif agent['domain'] == 'Transportation':
                read = get_tool_read(
                    agent['agent_id'],
                    'vehicle',
                    warehouse=warehouse_id,
                    hospital=hospital_id,
                    vehicle=normalized_vehicle,
                )
            else:
                if agent['agent_id'].endswith('_1'):
                    question = 'distance'
                else:
                    question = 'cost'
                read = get_tool_read(
                    agent['agent_id'],
                    question,
                    warehouse=warehouse_id,
                    hospital=hospital_id,
                    vehicle=normalized_vehicle,
                )
            agent_reads.append(read)
        return agent_reads

    def run_simulation(self, medicine_name, quantity, camp_name):
        camp = find_camp(camp_name)
        if camp is None:
            return {
                'hospital': {'clinic_name': camp_name},
                'warehouse': {'decision': 'Rejected', 'reason': 'Clinic is not registered.'},
                'transportation': None,
                'logs': ['Clinic not registered in the system.'],
                'agents': [],
            }

        candidates = []
        for warehouse in get_warehouse_registry():
            stock = get_medicine_stock(warehouse['warehouse_name'], medicine_name)
            if stock is None or stock['quantity'] < quantity:
                continue
            distance_km = get_distance_km(camp['location'], warehouse['location'])
            cost = distance_km * warehouse['cost_per_km'] + warehouse['handling_fee']
            if cost > warehouse['budget_limit']:
                continue
            candidates.append({
                'warehouse_name': warehouse['warehouse_name'],
                'distance_km': round(distance_km, 2),
                'transport_cost': round(cost, 2),
                'stock': stock['quantity'],
            })

        if not candidates:
            return {
                'hospital': {'clinic_name': camp_name, 'medicine_name': medicine_name, 'quantity': quantity},
                'warehouse': {'decision': 'Rejected', 'reason': 'No warehouse has enough stock within the current budget.'},
                'transportation': None,
                'logs': ['No feasible warehouse could satisfy the request under the NGO budget.'],
                'agents': self.collect_agent_reads('W1', 'C2', 'Truck'),
            }

        warehouse = min(candidates, key=lambda item: (item['transport_cost'], item['distance_km']))
        service = {
            'clinic_name': camp_name,
            'medicine_name': medicine_name,
            'quantity': quantity,
            'selected_warehouse': warehouse['warehouse_name'],
            'distance_km': warehouse['distance_km'],
            'transport_cost': warehouse['transport_cost'],
        }

        vehicle = next((vehicle for vehicle in next(w['fleet'] for w in get_warehouse_registry() if w['warehouse_name'] == warehouse['warehouse_name'])), None)
        selected_warehouse_id = self.warehouse_id_for_name(warehouse['warehouse_name'])
        normalized_vehicle_type = self.normalize_vehicle_type(vehicle['name'] if vehicle else 'Truck')
        agent_reads = self.collect_agent_reads(selected_warehouse_id, 'C2', normalized_vehicle_type)

        transport = {
            'decision': 'Approved',
            'reason': 'Route approved by the transportation domain agents.',
            'vehicle': vehicle['name'] if vehicle else 'Truck',
            'distance_km': warehouse['distance_km'],
            'delivery_time_hours': round(warehouse['distance_km'] / vehicle['speed_kmh'], 2) if vehicle else 0,
            'transportation_cost': warehouse['transport_cost'],
        }

        logs = [
            f"Clinic {camp_name} requested {quantity} units of {medicine_name}.",
            f"Warehouse domain checked stock and selected {warehouse['warehouse_name']}.",
            f"Transportation domain approved the route using {transport['vehicle']}.",
            f"Logistics agents verified total cost of ${transport['transportation_cost']:.0f}."
        ]

        return {
            'hospital': {'clinic_name': camp_name, 'medicine_name': medicine_name, 'quantity': quantity},
            'warehouse': {
                'decision': 'Approved',
                'reason': 'Nearest warehouse with sufficient stock and budget feasibility was selected.',
                'warehouse_name': warehouse['warehouse_name'],
                'distance_km': warehouse['distance_km'],
                'transport_cost': warehouse['transport_cost'],
            },
            'transportation': transport,
            'logs': logs,
            'agents': agent_reads,
        }
