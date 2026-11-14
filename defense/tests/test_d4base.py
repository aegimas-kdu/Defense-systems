from collections import Counter

from defense.defense import D4Base
from defense.fake_claims import World
from defense.settings import load_settings


def make_claims(agent_values):
    claims = []
    for agent_id, value in agent_values:
        claims.append({
            'mission_id': 0,
            'question': 'dist',
            'key': ('W1', 'H1'),
            'agent_id': agent_id,
            'domain': 'logistics',
            'answer': value,
            'readings': [{'tool_id': f'T{agent_id[-1]}', 'value': value}],
            'inputs': {},
        })
    return claims


def test_full_s0_run_makes_one_ledger_entry_per_reading():
    settings = load_settings()
    world = World(3, poison_mode='none', liar=None, settings=settings)
    defense = D4Base(settings=settings, seed=3)

    ask = lambda agent_ids: [world.read(agent_id, world.sequence[0], 0, 'dist') for agent_id in agent_ids]
    decision = defense.decide('dist', world.sequence[0], ['LA1', 'LA2', 'LA3'], ask)

    assert decision['value'] is not None
    assert len(defense.ledger.entries) == 2 * len(['LA1', 'LA2', 'LA3'])


def test_learned_decision_marks_every_ledger_entry_as_agreed_or_disagreed():
    settings = load_settings()
    defense = D4Base(settings=settings, seed=5)
    claims = make_claims([('A1', 10), ('A2', 10), ('A3', 10)])

    decision = defense.decide('dist', ('W1', 'H1'), ['A1', 'A2', 'A3'], lambda _: claims)

    assert decision['support'] >= settings.support_needed
    assert all(entry['agreed_with_verdict'] in (True, False) for entry in defense.ledger.entries)


def test_quarantined_agent_reads_do_not_vote():
    settings = load_settings()
    defense = D4Base(settings=settings, seed=7)
    defense.memory.q_agents.add('A1')
    claims = [
        {
            'mission_id': 0,
            'question': 'dist',
            'key': ('W1', 'H1'),
            'agent_id': 'A1',
            'domain': 'logistics',
            'answer': 0,
            'readings': [{'tool_id': 'L1', 'value': 0}, {'tool_id': 'L2', 'value': 0}],
            'inputs': {},
        },
        {
            'mission_id': 0,
            'question': 'dist',
            'key': ('W1', 'H1'),
            'agent_id': 'A2',
            'domain': 'logistics',
            'answer': 5,
            'readings': [{'tool_id': 'L3', 'value': 5}, {'tool_id': 'L4', 'value': 5}],
            'inputs': {},
        },
    ]

    decision = defense.decide('dist', ('W1', 'H1'), ['A1', 'A2'], lambda _: claims)

    assert decision['value'] == 5
    assert decision['support'] == 2


def test_every_agent_quarantined_falls_back_to_all_readings():
    settings = load_settings()
    defense = D4Base(settings=settings, seed=11)
    defense.memory.q_agents.update({'A1', 'A2'})
    claims = [
        {'mission_id': 0, 'question': 'dist', 'key': ('W1', 'H1'), 'agent_id': 'A1', 'domain': 'logistics', 'answer': 3,
         'readings': [{'tool_id': 'T1', 'value': 3}], 'inputs': {}},
        {'mission_id': 0, 'question': 'dist', 'key': ('W1', 'H1'), 'agent_id': 'A2', 'domain': 'logistics', 'answer': 7,
         'readings': [{'tool_id': 'T2', 'value': 7}], 'inputs': {}},
    ]

    decision = defense.decide('dist', ('W1', 'H1'), ['A1', 'A2'], lambda _: claims)

    assert decision['value'] in {3, 7}
    assert decision['support'] == 1


def test_low_support_does_not_learn_or_mark_entries_as_agreed():
    settings = load_settings()
    defense = D4Base(settings=settings, seed=13)
    claims = [
        {'mission_id': 0, 'question': 'dist', 'key': ('W1', 'H1'), 'agent_id': 'A1', 'domain': 'logistics', 'answer': 10,
         'readings': [{'tool_id': 'T1', 'value': 10}], 'inputs': {}},
        {'mission_id': 0, 'question': 'dist', 'key': ('W1', 'H1'), 'agent_id': 'A2', 'domain': 'logistics', 'answer': 20,
         'readings': [{'tool_id': 'T2', 'value': 20}], 'inputs': {}},
        {'mission_id': 0, 'question': 'dist', 'key': ('W1', 'H1'), 'agent_id': 'A3', 'domain': 'logistics', 'answer': 30,
         'readings': [{'tool_id': 'T3', 'value': 30}], 'inputs': {}},
    ]

    decision = defense.decide('dist', ('W1', 'H1'), ['A1', 'A2', 'A3'], lambda _: claims)

    assert decision['support'] < settings.support_needed
    assert defense.memory.agent_seen == Counter()
    assert defense.memory.tool_seen == Counter()
    assert all(entry['agreed_with_verdict'] is None for entry in defense.ledger.entries)


def test_get_trust_of_unseen_entity_is_0_5():
    settings = load_settings()
    defense = D4Base(settings=settings, seed=17)

    assert defense.get_trust('MYSTERY_ID') == 0.5
