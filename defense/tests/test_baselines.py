from collections import Counter

from defense.baselines import MajorityVote, ReadingVote
from defense.defense import Defense, make_decision, plurality


def test_majority_vote_reaches_50_with_support_2_and_no_tie():
    claims = [
        {'mission_id': 0, 'answer': 50},
        {'mission_id': 0, 'answer': 50},
        {'mission_id': 0, 'answer': 60},
    ]

    decision = MajorityVote(settings=None, seed=7).decide('dist', ('W1', 'H1'), [], lambda agent_ids: claims)

    assert decision['value'] == 50
    assert decision['support'] == 2
    assert decision['tied'] is False


def test_majority_vote_tie_is_seeded_and_repeatable():
    claims = [
        {'mission_id': 1, 'answer': 50},
        {'mission_id': 1, 'answer': 60},
        {'mission_id': 1, 'answer': 70},
    ]

    decision_a = MajorityVote(settings=None, seed=11).decide('dist', ('W2', 'H2'), [], lambda agent_ids: claims)
    decision_b = MajorityVote(settings=None, seed=11).decide('dist', ('W2', 'H2'), [], lambda agent_ids: claims)

    assert decision_a['tied'] is True
    assert decision_a['value'] in {50, 60, 70}
    assert decision_a['value'] == decision_b['value']


def test_d1_and_d1b_diverge_when_second_readings_agree():
    claims = [
        {'mission_id': 2, 'answer': 50, 'readings': [{'value': 50}, {'value': 60}]},
        {'mission_id': 2, 'answer': 70, 'readings': [{'value': 70}, {'value': 60}]},
        {'mission_id': 2, 'answer': 80, 'readings': [{'value': 80}, {'value': 60}]},
    ]

    d1 = MajorityVote(settings=None, seed=3).decide('dist', ('W3', 'H3'), [], lambda agent_ids: claims)
    d1b = ReadingVote(settings=None, seed=3).decide('dist', ('W3', 'H3'), [], lambda agent_ids: claims)

    assert d1['tied'] is True
    assert d1['support'] == 1
    assert d1b['value'] == 60
    assert d1b['support'] == 3
    assert d1b['tied'] is False


def test_plurality_returns_none_zero_false_for_empty_votes():
    value, support, tied = plurality(Counter(), random_seed := __import__('random').Random(42))

    assert (value, support, tied) == (None, 0, False)


def test_make_decision_returns_the_expected_contract():
    claims = [{'mission_id': 9, 'answer': 42}]
    decision = make_decision('time', ('W4', 'H1'), claims, 42, 1, False, {'42': 1})

    assert set(decision) == {'decision_id', 'question', 'key', 'value', 'support', 'tied', 'candidates', 'claims', 'revised_parent'}
    assert decision['decision_id'] == '9:time'
    assert decision['question'] == 'time'
    assert decision['key'] == ('W4', 'H1')
    assert decision['value'] == 42
    assert decision['support'] == 1
    assert decision['tied'] is False
    assert decision['candidates'] == {'42': 1}
    assert decision['claims'] == claims
    assert decision['revised_parent'] is None


def test_defense_report_has_the_three_expected_keys():
    report = Defense().report()

    assert set(report) == {'quarantined_agents', 'quarantined_tools', 'flags'}
    assert report['quarantined_agents'] == set()
    assert report['quarantined_tools'] == set()
    assert report['flags'] == set()
