import random

# Warehouse agents and tools
AGENTS = ['WH-1', 'WH-2', 'WH-3']
TOOLS = ['WH-T1', 'WH-T2', 'WH-T3']
TOOL_WEIGHTS = [0.5, 0.3, 0.2]
N_FACTS = 40
N_QUESTIONS = 300
SLIP_RATE = 0.05
POISON_RATE = 0.20


def make_rng(seed, name):
    return random.Random(f"{seed}-{name}")


def make_true_facts(seed):
    rng = make_rng(seed, 'facts')
    facts = {}
    for i in range(N_FACTS):
        facts[f'stock|{i}'] = rng.randint(0, 200)
    return facts


def poison_value(value):
    return value + max(10, value // 2)


def liar_value(value, rng):
    return value + rng.randint(5, 50) * rng.choice([-1, 1])


def slip_value(value, rng):
    return value + rng.randint(1, 5) * rng.choice([-1, 1])


def make_poisoned_table(truth, tool_id, seed):
    rng = make_rng(seed, f'poison-{tool_id}')
    table = dict(truth)
    for key, value in truth.items():
        if rng.random() < POISON_RATE:
            table[key] = poison_value(value)
    return table


SCENARIOS = {
    'S0': {'liars': [], 'poisoned_tools': [], 'repair_at': None},
    'S1': {'liars': ['WH-2'], 'poisoned_tools': [], 'repair_at': None},
    'S2': {'liars': [], 'poisoned_tools': ['WH-T1'], 'repair_at': None},
    'S3': {'liars': ['WH-2'], 'poisoned_tools': ['WH-T1'], 'repair_at': None},
    'S4': {'liars': [], 'poisoned_tools': ['WH-T1'], 'repair_at': 150},
}


def agent_report(agent_id, true_value, tool_value, liars, rng_slip, rng_liar):
    slip_roll = rng_slip.random()
    slip_answer = slip_value(tool_value, rng_slip)
    liar_answer = liar_value(true_value, rng_liar)
    if agent_id in liars:
        return liar_answer   
    if slip_roll < SLIP_RATE:
        return slip_answer
    return tool_value


def generate_stream(scenario_name, seed):
    scenario = SCENARIOS[scenario_name]
    truth = make_true_facts(seed)
    fact_keys = list(truth)
    clean_tables = {tool_id: dict(truth) for tool_id in TOOLS}
    poisoned_tables = {
        tool_id: make_poisoned_table(truth, tool_id, seed)
        for tool_id in TOOLS
    }

    rng_questions = make_rng(seed, 'questions')
    rng_tools = make_rng(seed, 'tools')
    rng_slips = make_rng(seed, 'slips')
    rng_liars = make_rng(seed, 'liars')

    stream = []
    for q in range(N_QUESTIONS):
        fact_key = rng_questions.choice(fact_keys)
        true_value = truth[fact_key]
        claims = []

        for agent_id in AGENTS:
            tool_id = rng_tools.choices(TOOLS, weights=TOOL_WEIGHTS)[0]
            poison_active = (
                bool(scenario['poisoned_tools'])
                and tool_id in scenario['poisoned_tools']
                and (scenario['repair_at'] is None or q < scenario['repair_at'])
            )
            table = poisoned_tables[tool_id] if poison_active else clean_tables[tool_id]
            tool_value = table[fact_key]
            claim_value = agent_report(
                agent_id,
                true_value,
                tool_value,
                scenario['liars'],
                rng_slips,
                rng_liars,
            )

            claims.append({
                'mission_id': q,
                'agent_id': agent_id,
                'domain': 'warehouse',
                'tool_id': tool_id,
                'fact_key': fact_key,
                'claim': claim_value,
            })

        stream.append({
            'question_id': q,
            'domain': 'warehouse',
            'fact_key': fact_key,
            'true_value': true_value,
            'claims': claims,
        })

    return stream
