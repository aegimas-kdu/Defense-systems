from defense.defense import D4Base
from defense.evaluate import make_ask, run_mission, run_world, summarize
from defense.fake_claims import World, scenario_runs
from defense.settings import load_settings


class DummyDefense:
    def __init__(self):
        self.claims = []

    def decide(self, question, key, agents, ask, parent=None):
        claims = ask(agents)
        self.claims.extend(claims)
        if not claims:
            value = 0
        else:
            value = claims[0]['answer']
        return {
            'question': question,
            'key': key,
            'value': value,
            'support': len(claims),
            'tied': False,
            'candidates': {value: len(claims)},
            'claims': claims,
            'revised_parent': None,
        }

    def end_mission(self, decisions):
        return None

    def report(self):
        return {'quarantined_agents': [], 'quarantined_tools': []}


class AllAgentsDefense(DummyDefense):
    def decide(self, question, key, agents, ask, parent=None):
        claims = ask(agents)
        self.claims.extend(claims)
        value = claims[0]['answer'] if claims else 0
        return {
            'question': question,
            'key': key,
            'value': value,
            'support': len(claims),
            'tied': False,
            'candidates': {value: len(claims)},
            'claims': claims,
            'revised_parent': None,
        }


class WrongDistanceDefense(DummyDefense):
    def decide(self, question, key, agents, ask, parent=None):
        claims = ask(agents)
        self.claims.extend(claims)
        if question == 'dist':
            value = -999
        else:
            value = claims[0]['answer'] if claims else 0
        return {
            'question': question,
            'key': key,
            'value': value,
            'support': len(claims),
            'tied': False,
            'candidates': {value: len(claims)},
            'claims': claims,
            'revised_parent': None,
        }


def test_run_world_metrics_are_between_zero_and_one():
    world = World(13, poison_mode='none', liar=None)
    result = run_world(world, DummyDefense())

    assert 0.0 <= result['mission_success'] <= 1.0
    assert 0.0 <= result['dist_acc'] <= 1.0
    assert 0.0 <= result['time_acc'] <= 1.0


def test_all_agents_calls_are_exactly_twelve_per_mission():
    world = World(17, poison_mode='none', liar=None)
    defense = AllAgentsDefense()
    tally = {'calls': 0}

    for m in range(len(world.sequence)):
        run_mission(world, defense, m, tally)

    assert tally['calls'] == len(world.sequence) * 12


def test_spy_defense_receives_only_claims_and_no_true_value_key():
    world = World(19, poison_mode='none', liar=None)
    defense = DummyDefense()
    run_world(world, defense)

    assert defense.claims
    assert all(set(claim) == {'mission_id', 'question', 'key', 'agent_id', 'domain', 'answer', 'readings', 'inputs'}
               for claim in defense.claims)
    assert all('true_value' not in claim for claim in defense.claims)


def test_same_seed_gives_identical_run_world_results():
    world_a = World(23, poison_mode='none', liar=None)
    world_b = World(23, poison_mode='none', liar=None)

    result_a = run_world(world_a, DummyDefense())
    result_b = run_world(world_b, DummyDefense())

    assert result_a == result_b


def test_time_inputs_propagate_the_wrong_distance_from_dist_decision():
    world = World(29, poison_mode='none', liar=None)
    defense = WrongDistanceDefense()
    tally = {'calls': 0}
    key = world.sequence[0]

    run_mission(world, defense, 0, tally)

    wrong_distance = -999
    time_claims = [
        claim for claim in defense.claims
        if claim['question'] == 'time' and claim['key'] == key
    ]
    assert time_claims
    assert all(claim['inputs']['resolved_distance_km'] == wrong_distance for claim in time_claims)


def test_summarize_uses_mean_and_standard_error():
    values = [
        {'mission_success': 0.2, 'dist_acc': 0.5, 'time_acc': 0.4, 'calls_per_mission': 10},
        {'mission_success': 0.4, 'dist_acc': 0.7, 'time_acc': 0.6, 'calls_per_mission': 12},
    ]
    summary = summarize(values)

    assert round(summary['mission_success']['mean'], 12) == 0.3
    assert round(summary['calls_per_mission']['mean'], 12) == 11
    assert summary['time_acc']['stderr'] >= 0.0
    assert summary['time_acc']['stderr'] == 0.1


def test_d4base_liar_is_quarantined_in_at_least_90_percent_of_s1_runs():
    settings = load_settings()
    liar_hits = 0
    total = 0
    for seed in range(5):
        for _, liar in scenario_runs('S1'):
            world = World(seed, poison_mode='none', liar=liar, settings=settings)
            defense = D4Base(settings=settings, seed=seed)
            result = run_world(world, defense)
            liar_hits += result['liar_quarantined'] or 0
            total += 1 if liar is not None else 0

    ratio = liar_hits / total
    print(f"S1 liar quarantine rate: {ratio:.2%} ({liar_hits}/{total})")
    assert ratio >= 0.90


def test_d4base_has_no_false_alarms_in_clean_worlds():
    settings = load_settings()
    honest_agents_quarantined = 0
    clean_tools_quarantined = 0
    for seed in range(20):
        world = World(seed, poison_mode='none', liar=None, settings=settings)
        defense = D4Base(settings=settings, seed=seed)
        result = run_world(world, defense)
        honest_agents_quarantined += result['honest_agents_quarantined']
        clean_tools_quarantined += result['clean_tools_quarantined']

    print(f"S0 false alarms: honest={honest_agents_quarantined}, clean_tools={clean_tools_quarantined}")
    assert honest_agents_quarantined == 0
    assert clean_tools_quarantined == 0


def test_d4base_poison_only_runs_keep_honest_quarantine_counts_low():
    settings = load_settings()
    honest_agents_quarantined = 0
    for seed in range(20):
        for poison_mode in ['scattered', 'aligned']:
            world = World(seed, poison_mode=poison_mode, liar=None, settings=settings)
            defense = D4Base(settings=settings, seed=seed)
            result = run_world(world, defense)
            honest_agents_quarantined += result['honest_agents_quarantined']

    print(f"S2 poison-only honest quarantine total: {honest_agents_quarantined}")
    assert honest_agents_quarantined <= 5


def test_d4base_combined_runs_have_low_false_punishment_counts():
    settings = load_settings()
    honest_agents_quarantined = 0
    clean_tools_quarantined = 0
    for seed in range(20):
        for _, liar in scenario_runs('S3'):
            world = World(seed, poison_mode='scattered', liar=liar, settings=settings)
            defense = D4Base(settings=settings, seed=seed)
            result = run_world(world, defense)
            honest_agents_quarantined += result['honest_agents_quarantined']
            clean_tools_quarantined += result['clean_tools_quarantined']

    print(f"S3 false punishments: honest={honest_agents_quarantined}, clean_tools={clean_tools_quarantined}")
    assert honest_agents_quarantined <= 20
    assert clean_tools_quarantined <= 20
