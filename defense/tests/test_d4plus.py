from collections import Counter

from defense.defense import D4Base, D4Plus
from defense.evaluate import run_world
from defense.fake_claims import AGENT_TOOLS, World, scenario_runs
from defense.settings import load_settings
from defense.blame import question_evidence


def _parent_decision(value=140):
    return {
        'decision_id': 'dist:0',
        'question': 'dist',
        'key': ('W1', 'H1'),
        'value': value,
        'support': 2,
        'tied': True,
        'candidates': {140: 2, 100: 2},
        'claims': [],
        'revised_parent': None,
    }


def test_d4plus_matches_d4base_when_cascade_is_disabled_in_s3():
    settings = load_settings(use_cascade_revision=False, use_fact_quarantine=False, use_fast_path=False)

    for seed in range(1, 6):
        for _, liar in scenario_runs('S3'):
            world = World(seed, poison_mode='scattered', liar=liar, settings=settings)
            base = D4Base(settings=settings, seed=seed)
            plus = D4Plus(settings=settings, seed=seed, agent_tools=AGENT_TOOLS, dependent_tools={'T1', 'T2'})

            base_result = run_world(world, base)
            plus_result = run_world(World(seed, poison_mode='scattered', liar=liar, settings=settings), plus)

            assert base_result['mission_success'] == plus_result['mission_success']
            assert base_result['honest_agents_quarantined'] == plus_result['honest_agents_quarantined']
            assert base_result['clean_tools_quarantined'] == plus_result['clean_tools_quarantined']


def test_learning_is_deferred_until_end_mission():
    settings = load_settings()
    defense = D4Plus(settings=settings, seed=1, agent_tools=AGENT_TOOLS, dependent_tools={'T1', 'T2'})

    claims = [
        {'mission_id': 0, 'question': 'time', 'key': ('W1', 'H1'), 'agent_id': 'TA1', 'domain': 'transportation',
         'answer': 100, 'readings': [{'tool_id': 'T3', 'value': 100}, {'tool_id': 'T1', 'value': 140}], 'inputs': {'resolved_distance_km': 140}},
        {'mission_id': 0, 'question': 'time', 'key': ('W1', 'H1'), 'agent_id': 'TA2', 'domain': 'transportation',
         'answer': 100, 'readings': [{'tool_id': 'T3', 'value': 100}, {'tool_id': 'T1', 'value': 140}], 'inputs': {'resolved_distance_km': 140}},
    ]

    decision = defense.decide('time', ('W1', 'H1'), ['TA1', 'TA2'], lambda _: claims, parent=_parent_decision())
    assert defense.memory.agent_seen == Counter()
    assert decision['revised_parent'] == 100

    defense.end_mission([_parent_decision(), decision])
    assert defense.memory.agent_seen


def test_time_tie_revises_parent_and_sets_revised_parent_to_100():
    settings = load_settings()
    defense = D4Plus(settings=settings, seed=2, agent_tools=AGENT_TOOLS, dependent_tools={'T1', 'T2'})
    parent = _parent_decision()
    claims = [
        {'mission_id': 0, 'question': 'time', 'key': ('W1', 'H1'), 'agent_id': 'TA1', 'domain': 'transportation',
         'answer': 100, 'readings': [{'tool_id': 'T3', 'value': 100}, {'tool_id': 'T1', 'value': 140}], 'inputs': {'resolved_distance_km': 140}},
        {'mission_id': 0, 'question': 'time', 'key': ('W1', 'H1'), 'agent_id': 'TA2', 'domain': 'transportation',
         'answer': 100, 'readings': [{'tool_id': 'T3', 'value': 100}, {'tool_id': 'T1', 'value': 140}], 'inputs': {'resolved_distance_km': 140}},
    ]

    decision = defense.decide('time', ('W1', 'H1'), ['TA1', 'TA2'], lambda _: claims, parent=parent)

    assert decision['value'] == 100
    assert decision['support'] == 4
    assert decision['revised_parent'] == 100


def test_revision_ignores_excused_tools_and_marks_wrong_evidence_for_the_old_parent():
    settings = load_settings()
    defense = D4Plus(settings=settings, seed=3, agent_tools=AGENT_TOOLS, dependent_tools={'T1', 'T2'})
    parent = _parent_decision()
    claims = [
        {'mission_id': 0, 'question': 'time', 'key': ('W1', 'H1'), 'agent_id': 'TA1', 'domain': 'transportation',
         'answer': 100, 'readings': [{'tool_id': 'T3', 'value': 100}, {'tool_id': 'T1', 'value': 140}], 'inputs': {'resolved_distance_km': 140}},
        {'mission_id': 0, 'question': 'time', 'key': ('W1', 'H1'), 'agent_id': 'TA2', 'domain': 'transportation',
         'answer': 100, 'readings': [{'tool_id': 'T3', 'value': 100}, {'tool_id': 'T1', 'value': 140}], 'inputs': {'resolved_distance_km': 140}},
    ]

    decision = defense.decide('time', ('W1', 'H1'), ['TA1', 'TA2'], lambda _: claims, parent=parent)
    defense.end_mission([parent, decision])

    evidence = question_evidence(claims, 100, {'T1', 'T2'})
    assert 'T1' not in evidence['tools']
    assert 'T2' not in evidence['tools']
    assert evidence['tools']['T3'] == 'right'
    assert all(entry['agreed_with_verdict'] is False for entry in defense.ledger.entries if entry['tool_id'] in {'T1', 'T2'})


def test_liar_who_reads_depended_tool_is_not_excused_and_is_blamed():
    settings = load_settings()
    defense = D4Plus(settings=settings, seed=4, agent_tools=AGENT_TOOLS, dependent_tools={'T1', 'T2'})
    parent = _parent_decision()
    claims = [
        {'mission_id': 0, 'question': 'time', 'key': ('W1', 'H1'), 'agent_id': 'TA1', 'domain': 'transportation',
         'answer': 90, 'readings': [{'tool_id': 'T1', 'value': 90}, {'tool_id': 'T3', 'value': 105}], 'inputs': {'resolved_distance_km': 140}},
        {'mission_id': 0, 'question': 'time', 'key': ('W1', 'H1'), 'agent_id': 'TA2', 'domain': 'transportation',
         'answer': 90, 'readings': [{'tool_id': 'T1', 'value': 90}, {'tool_id': 'T3', 'value': 110}], 'inputs': {'resolved_distance_km': 140}},
    ]

    decision = defense.decide('time', ('W1', 'H1'), ['TA1', 'TA2'], lambda _: claims, parent=parent)
    evidence = question_evidence(claims, 140, frozenset())

    assert decision['revised_parent'] is None
    assert evidence['agents']['TA1'] == 'bad'
    assert evidence['agents']['TA2'] == 'bad'


def test_decision_without_parent_never_revises():
    settings = load_settings()
    defense = D4Plus(settings=settings, seed=5, agent_tools=AGENT_TOOLS, dependent_tools={'T1', 'T2'})
    claims = [
        {'mission_id': 0, 'question': 'time', 'key': ('W1', 'H1'), 'agent_id': 'TA1', 'domain': 'transportation',
         'answer': 100, 'readings': [{'tool_id': 'T3', 'value': 100}, {'tool_id': 'T1', 'value': 100}], 'inputs': {'resolved_distance_km': 140}},
        {'mission_id': 0, 'question': 'time', 'key': ('W1', 'H1'), 'agent_id': 'TA2', 'domain': 'transportation',
         'answer': 100, 'readings': [{'tool_id': 'T3', 'value': 100}, {'tool_id': 'T1', 'value': 100}], 'inputs': {'resolved_distance_km': 140}},
    ]

    decision = defense.decide('time', ('W1', 'H1'), ['TA1', 'TA2'], lambda _: claims)
    assert decision['revised_parent'] is None
    assert decision['value'] == 100


def _claim(agent, readings):
    return {
        'mission_id': 0,
        'question': 'time',
        'key': ('W1', 'H1'),
        'agent_id': agent,
        'domain': 'transportation',
        'answer': readings[0][1],
        'readings': [{'tool_id': tool_id, 'value': value} for tool_id, value in readings],
        'inputs': {'resolved_distance_km': 140},
    }


def test_fast_path_accepts_trusted_agent_with_matching_readings():
    settings = load_settings(use_fast_path=True)
    defense = D4Plus(settings=settings, seed=1, agent_tools=AGENT_TOOLS, dependent_tools={'T1', 'T2'})
    defense.memory.agent_seen['TA1'] = 100
    defense.memory.agent_bad['TA1'] = 0
    defense.memory.q_agents.add('TA2')

    seen = []

    def ask(agent_ids):
        seen.extend(agent_ids)
        return [
            _claim('TA1', [('T1', 100), ('T3', 100)]),
            _claim('TA2', [('T2', 100), ('T1', 100)]),
        ] if 'TA2' in agent_ids else [_claim('TA1', [('T1', 100), ('T3', 100)])]

    decision = defense.decide('time', ('W1', 'H1'), ['TA1', 'TA2', 'TA3'], ask)

    assert decision['fast'] is True
    assert decision['value'] == 100
    assert decision['support'] == 2
    assert seen == ['TA1', 'TA2']


def test_fast_path_escalates_when_best_agent_readings_disagree():
    settings = load_settings(use_fast_path=True)
    defense = D4Plus(settings=settings, seed=2, agent_tools=AGENT_TOOLS, dependent_tools={'T1', 'T2'})
    defense.memory.agent_seen['TA1'] = 100
    defense.memory.agent_bad['TA1'] = 0
    defense.memory.q_agents.add('TA2')

    seen = []

    def ask(agent_ids):
        seen.extend(agent_ids)
        claims = []
        if 'TA1' in agent_ids:
            claims.append(_claim('TA1', [('T1', 100), ('T3', 120)]))
        if 'TA2' in agent_ids:
            claims.append(_claim('TA2', [('T2', 120), ('T1', 120)]))
        if 'TA3' in agent_ids:
            claims.append(_claim('TA3', [('T3', 100), ('T2', 100)]))
        return claims

    decision = defense.decide('time', ('W1', 'H1'), ['TA1', 'TA2', 'TA3'], ask)

    assert decision['fast'] is False
    assert len(seen) == 3
    assert len({x for x in seen}) == 3


def test_fast_path_rejects_agents_without_independent_tools_when_parent_exists():
    settings = load_settings(use_fast_path=True)
    defense = D4Plus(settings=settings, seed=3, agent_tools=AGENT_TOOLS, dependent_tools={'T1', 'T2'})
    defense.memory.agent_seen['TA1'] = 100
    defense.memory.agent_bad['TA1'] = 0
    defense.memory.agent_seen['TA2'] = 100
    defense.memory.agent_bad['TA2'] = 0

    def ask(agent_ids):
        return [_claim('TA1', [('T3', 100), ('T1', 100)])]

    parent = _parent_decision()
    decision = defense.decide('time', ('W1', 'H1'), ['TA1', 'TA2'], ask, parent=parent)

    assert decision['fast'] is True
    assert decision['fast_agent'] == 'TA1'


def test_fast_path_is_disabled_when_key_is_flagged():
    settings = load_settings(use_fast_path=True)
    defense = D4Plus(settings=settings, seed=4, agent_tools=AGENT_TOOLS, dependent_tools={'T1', 'T2'})
    defense.memory.agent_seen['TA1'] = 100
    defense.memory.agent_bad['TA1'] = 0
    defense.memory.flag_fact('T1', ('W1', 'H1'))

    def ask(agent_ids):
        return [_claim('TA1', [('T1', 100), ('T3', 100)])]

    decision = defense.decide('time', ('W1', 'H1'), ['TA1', 'TA2', 'TA3'], ask)

    assert decision['fast'] is False


def test_fast_path_asks_quarantined_agent_but_does_not_count_its_vote():
    settings = load_settings(use_fast_path=True)
    defense = D4Plus(settings=settings, seed=5, agent_tools=AGENT_TOOLS, dependent_tools={'T1', 'T2'})
    defense.memory.agent_seen['TA1'] = 100
    defense.memory.agent_bad['TA1'] = 0
    defense.memory.q_agents.add('TA2')

    def ask(agent_ids):
        claims = []
        for agent in agent_ids:
            if agent == 'TA1':
                claims.append(_claim('TA1', [('T1', 84), ('T3', 84)]))
            if agent == 'TA2':
                claims.append(_claim('TA2', [('T2', 84), ('T1', 84)]))
        return claims

    decision = defense.decide('time', ('W1', 'H1'), ['TA1', 'TA2', 'TA3'], ask)

    assert decision['fast'] is True
    assert decision['value'] == 84
    assert decision['support'] == 2
    assert any(claim['agent_id'] == 'TA2' for claim in decision['claims'])


def test_fast_path_switch_off_uses_the_full_call_count():
    settings = load_settings(use_fast_path=False)
    defense = D4Plus(settings=settings, seed=6, agent_tools=AGENT_TOOLS, dependent_tools={'T1', 'T2'})
    total = {'calls': 0}

    def ask(agent_ids):
        total['calls'] += 2 * len(agent_ids)
        return [
            _claim(agent, [('T1', 100), ('T3', 100)]) if agent == 'TA1' else
            _claim(agent, [('T2', 100), ('T1', 100)]) if agent == 'TA2' else
            _claim(agent, [('T3', 100), ('T2', 100)])
            for agent in agent_ids
        ]

    defense.decide('time', ('W1', 'H1'), ['TA1', 'TA2', 'TA3'], ask)

    assert total['calls'] == 6


def test_d4plus_cascade_only_outperforms_d4base_on_s3_with_liar_fixed_la3():
    settings = load_settings(use_fact_quarantine=False, use_fast_path=False)
    base_scores = []
    plus_scores = []

    for seed in range(1, 21):
        world_base = World(seed, poison_mode='scattered', liar='LA3', settings=settings)
        world_plus = World(seed, poison_mode='scattered', liar='LA3', settings=settings)

        base = D4Base(settings=settings, seed=seed)
        plus = D4Plus(settings=settings, seed=seed, agent_tools=AGENT_TOOLS, dependent_tools={'T1', 'T2'})

        base_scores.append(run_world(world_base, base)['mission_success'])
        plus_scores.append(run_world(world_plus, plus)['mission_success'])

    assert sum(plus_scores) > sum(base_scores)
