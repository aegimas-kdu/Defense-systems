"""Coordinator: asks the five questions in order, lets the defense decide, then builds the plan from
the DECIDED values only. It never reads warehouse.py or truth.py for stock, distance, time or cost."""
import itertools

try:
    from simulator import registry
    from simulator.defense import NoConsensus
    from simulator.nodefense import NoDefense
    from simulator.participants.hospital import find_camp
    from simulator.world_ids import WAREHOUSE_IDS, VEHICLE_TYPES
except ModuleNotFoundError:  # pragma: no cover
    import registry
    from defense import NoConsensus
    from nodefense import NoDefense
    from participants.hospital import find_camp
    from world_ids import WAREHOUSE_IDS, VEHICLE_TYPES

DEFAULT_NGO_BUDGET = 50000  # cost units, as in the system description


class AgentCoordinator:
    def __init__(self, defense=None, world=None):
        self.world = world or registry.get_world()
        self.defense = defense or NoDefense()
        self._mission_ids = itertools.count(1)

    def ask(self, question, key, inputs=None, mission_id=None):
        """Send ONE question to ALL three agents of its domain. Returns (decided value, claims)."""
        domain = registry.QUESTIONS[question]['domain']
        claims = [
            registry.get_claim(a['agent_id'], question, key, inputs, mission_id, world=self.world)
            for a in self.world['agents'] if a['domain'] == domain
        ]
        return self.defense.decide(question, key, claims), claims

    def run_simulation(self, medicine_name, quantity, camp_name, budget=DEFAULT_NGO_BUDGET,
                       deadline_minutes=None):
        camp = find_camp(camp_name)
        if camp is None:
            return self._rejected(camp_name, medicine_name, quantity, 'Clinic is not registered.',
                                  ['Clinic not registered in the system.'], [])
        hospital_id = camp['camp_id']
        mission_id = next(self._mission_ids)
        all_claims, notes, candidates = [], [], []

        for warehouse_name, wid in WAREHOUSE_IDS.items():
            # Q1 stock
            try:
                stock, claims = self.ask('Q1', {'warehouse': wid, 'medicine': medicine_name}, mission_id=mission_id)
            except NoConsensus as exc:
                notes.append(str(exc)); continue
            all_claims += claims
            if stock < quantity:
                notes.append(f'{warehouse_name}: stock {stock} < requested {quantity}.')
                continue

            for vehicle in VEHICLE_TYPES:
                key = {'warehouse': wid, 'hospital': hospital_id, 'vehicle': vehicle}
                try:
                    capacity, c2 = self.ask('Q2', key, mission_id=mission_id)
                    all_claims += c2
                    if capacity < quantity:
                        notes.append(f'{warehouse_name}/{vehicle}: capacity {capacity} < {quantity}.')
                        continue
                    distance, c3 = self.ask('Q3', key, mission_id=mission_id)
                    minutes, c4 = self.ask('Q4', key, {'resolved_distance_km': distance}, mission_id)
                    cost, c5 = self.ask('Q5', key, mission_id=mission_id)
                except NoConsensus as exc:
                    notes.append(str(exc)); continue
                all_claims += c3 + c4 + c5
                if cost > budget:
                    notes.append(f'{warehouse_name}/{vehicle}: cost {cost} exceeds budget {budget}.')
                    continue
                if deadline_minutes is not None and minutes > deadline_minutes:
                    notes.append(f'{warehouse_name}/{vehicle}: {minutes} min misses deadline {deadline_minutes}.')
                    continue
                candidates.append({'warehouse_name': warehouse_name, 'vehicle': vehicle, 'stock': stock,
                                   'distance_km': distance, 'minutes': minutes, 'cost': cost,
                                   'claims': claims + c2 + c3 + c4 + c5})

        if not candidates:
            return self._rejected(camp_name, medicine_name, quantity,
                                  'No warehouse and vehicle can satisfy the request within stock, capacity, budget and deadline.',
                                  notes or ['No feasible plan.'], all_claims)

        best = min(candidates, key=lambda c: (c['cost'], c['minutes']))
        logs = [
            f'Clinic {camp_name} requested {quantity} units of {medicine_name}.',
            f"Warehouse domain agreed on stock {best['stock']} at {best['warehouse_name']}.",
            f"Transportation domain agreed {best['vehicle']} can carry the load; ETA {best['minutes']} min.",
            f"Logistics domain agreed on {best['distance_km']} km and a cost of {best['cost']}.",
        ]
        return {
            'hospital': {'clinic_name': camp_name, 'medicine_name': medicine_name, 'quantity': quantity},
            'warehouse': {'decision': 'Approved',
                          'reason': 'Cheapest feasible warehouse and vehicle chosen from defense-decided values.',
                          'warehouse_name': best['warehouse_name'], 'distance_km': best['distance_km'],
                          'transport_cost': best['cost']},
            'transportation': {'decision': 'Approved', 'reason': 'Route approved by the transportation domain agents.',
                               'vehicle': best['vehicle'], 'distance_km': best['distance_km'],
                               'delivery_time_minutes': best['minutes'],
                               'delivery_time_hours': round(best['minutes'] / 60, 2),
                               'transportation_cost': best['cost']},
            'logs': logs,
            'agents': best['claims'],
            'mission_id': mission_id,
        }

    @staticmethod
    def _rejected(camp_name, medicine_name, quantity, reason, logs, claims):
        return {
            'hospital': {'clinic_name': camp_name, 'medicine_name': medicine_name, 'quantity': quantity},
            'warehouse': {'decision': 'Rejected', 'reason': reason},
            'transportation': None,
            'logs': logs,
            'agents': claims,
        }