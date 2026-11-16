import random

from defense.settings import load_settings

# Fixed world dimensions: five warehouses, three hospitals, and 15 fact keys.
WAREHOUSES = ['W1', 'W2', 'W3', 'W4', 'W5']
HOSPITALS = ['H1', 'H2', 'H3']
KEYS = [(warehouse, hospital) for warehouse in WAREHOUSES for hospital in HOSPITALS]

LOGISTICS_AGENTS = ['LA1', 'LA2', 'LA3']
TRANSPORT_AGENTS = ['TA1', 'TA2', 'TA3']

# Each agent has a primary tool and a backup tool used for the two readings.
AGENT_TOOLS = {
    'LA1': ('L1', 'L3'),
    'LA2': ('L2', 'L1'),
    'LA3': ('L3', 'L2'),
    'TA1': ('T1', 'T3'),
    'TA2': ('T2', 'T1'),
    'TA3': ('T3', 'T2'),
}
DOMAIN_AGENTS = {'dist': LOGISTICS_AGENTS, 'time': TRANSPORT_AGENTS}
ALL_AGENTS = LOGISTICS_AGENTS + TRANSPORT_AGENTS
SCENARIOS = {
    'S0': 'clean',
    'S1': 'one liar',
    'S2s': 'scattered poison',
    'S2a': 'aligned poison',
    'S3': 'a liar and scattered poison',
    'S5': 'poison repaired',
    'S6': 'liar reforms',
    'S7': 'late attack',
}

SCENARIO_WINDOWS = {
    'S0': {'poison_window': (0, None), 'liar_window': (0, None)},
    'S1': {'poison_window': (0, None), 'liar_window': (0, None)},
    'S2s': {'poison_window': (0, None), 'liar_window': (0, None)},
    'S2a': {'poison_window': (0, None), 'liar_window': (0, None)},
    'S3': {'poison_window': (0, None), 'liar_window': (0, None)},
    'S5': {'poison_window': (0, None), 'liar_window': (0, None)},
    'S6': {'poison_window': (0, None), 'liar_window': (0, None)},
    'S7': {'poison_window': (0, None), 'liar_window': (0, None)},
}


def scenario_runs(name):
    # One run is a pair: a poison pattern and an optional liar agent.
    if name == 'S0':
        return [('none', None)]
    if name == 'S1':
        return [('none', agent) for agent in ALL_AGENTS]
    if name == 'S2s':
        return [('scattered', None)]
    if name == 'S2a':
        return [('aligned', None)]
    if name == 'S3':
        return [('scattered', agent) for agent in ALL_AGENTS]
    if name == 'S5':
        return [('scattered', None)]
    if name == 'S6':
        return [('none', agent) for agent in ALL_AGENTS]
    if name == 'S7':
        return [('scattered', agent) for agent in ALL_AGENTS]
    raise ValueError(f'Unknown scenario: {name}')


def poison_value(value):
    # Poison always changes the value by at least 10, with no randomness.
    return value + max(10, value // 2)


def make_truth(seed):
    rng = random.Random(f'truth-{seed}')
    truth = {}
    for key in KEYS:
        truth[key] = 20 * rng.randint(1, 15)
    # The true time in minutes equals the true distance, because every vehicle is the Van at 60 km/h.
    return truth


def pick_poison_keys(seed, mode, n_scattered):
    rng = random.Random(f'poison-{seed}')

    if mode == 'none':
        return set()
    if mode == 'scattered':
        # Choose a few keys spread around the map, not one warehouse slice.
        return set(rng.sample(KEYS, n_scattered))
    if mode == 'aligned':
        # A single warehouse gets poisoned together, which creates a slice-wide effect.
        warehouse = rng.choice(WAREHOUSES)
        return {key for key in KEYS if key[0] == warehouse}
    raise ValueError(f'Unknown poison mode: {mode}')


def make_sequence(seed, n):
    # Fixed mission order: each defense sees the same sequence for a given seed.
    rng = random.Random(f'sequence-{seed}')
    return [rng.choice(KEYS) for _ in range(n)]


def make_noise(seed, n_missions):
    rng = random.Random(f'noise-{seed}')
    noise = {}

    # Precompute the random slip and lie draws once so every defense uses the same stream.
    for m in range(n_missions):
        for qtype in ['dist', 'time']:
            for agent in AGENT_TOOLS:
                noise[(m, qtype, agent)] = [
                    (
                        rng.random(),
                        rng.randint(1, 5) * rng.choice([-1, 1]),
                        rng.randint(5, 50) * rng.choice([-1, 1]),
                    )
                    for _ in range(2)
                ]

    return noise


class World:
    def __init__(self, seed, poison_mode='none', liar=None, poison_tool='L1', settings=None,
                 poison_window=(0, None), liar_window=(0, None)):
        if settings is None:
            settings = load_settings()
        if liar is not None and liar not in AGENT_TOOLS:
            raise ValueError(f'Unknown liar: {liar}')
        self.settings = settings
        self.truth = make_truth(seed)
        self.poison_keys = pick_poison_keys(seed, poison_mode, self.settings.n_scattered_poison_keys)
        self.poison_tool = poison_tool
        self.liar = liar
        self.poison_window = poison_window
        self.liar_window = liar_window
        self.sequence = make_sequence(seed, self.settings.n_missions)
        self.noise = make_noise(seed, self.settings.n_missions)

    def _in(self, window, m):
        if m is None:
            return True
        start, end = window
        return m >= start and (end is None or m < end)

    def true_value(self, qtype, key):
        # Both question types use the same hidden truth table in this toy world.
        return self.truth[key]

    def read(self, agent, key, m, qtype, dres=None):
        truth = self.true_value(qtype, key)
        readings = []

        # Each agent reads the two tools in its personal order; the per-read noise is fixed by seed.
        for tool, (slip_roll, slip_size, lie_offset) in zip(AGENT_TOOLS[agent], self.noise[(m, qtype, agent)]):
            value = self.tool_value(tool, key, dres, m)

            if agent == self.liar and self._in(self.liar_window, m):
                value = truth + lie_offset
            elif slip_roll < self.settings.slip_rate / 2:
                value += slip_size

            readings.append({'tool_id': tool, 'value': value})

        domain = 'logistics' if agent in LOGISTICS_AGENTS else 'transportation'
        inputs = {'resolved_distance_km': dres} if qtype == 'time' else {}

        # The claim contract is the same format used by the defense and the evaluator.
        return {
            'mission_id': m,
            'question': qtype,
            'key': key,
            'agent_id': agent,
            'domain': domain,
            'answer': readings[0]['value'],
            'readings': readings,
            'inputs': inputs,
        }

    def tool_value(self, tool, key, dres, m=None):
        if tool in {'T1', 'T2'}:
            # Distance-derived tools need the resolved distance from the earlier decision.
            if dres is None:
                raise ValueError(f'dres is required for tool {tool} when resolving a distance-based reading')
            base = dres
        else:
            base = self.truth[key]

        if tool == self.poison_tool and key in self.poison_keys and self._in(self.poison_window, m):
            return poison_value(base)
        return base

    def poison_live_at_end(self):
        return self._in(self.poison_window, self.settings.n_missions - 1)

    def liar_live_at_end(self):
        return self._in(self.liar_window, self.settings.n_missions - 1)
