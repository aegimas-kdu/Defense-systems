from defense.settings import load_settings
from defense.trust import TrustMemory


def test_new_entity_starts_with_trust_half():
    memory = TrustMemory(load_settings())

    assert memory.agent_trust('A') == 0.5
    assert memory.tool_trust('T1') == 0.5


def test_after_ten_good_observations_trust_is_11_over_12():
    memory = TrustMemory(load_settings())

    for _ in range(10):
        memory.record({'agents': {'A': 'good'}, 'tools': {}})

    assert memory.agent_trust('A') == 11 / 12


def test_agent_with_rate_above_threshold_is_quarantined():
    memory = TrustMemory(load_settings())

    for _ in range(10):
        memory.record({'agents': {'A': 'bad'}, 'tools': {}})

    assert memory.is_quarantined('A') is True
    assert memory.agent_trust('A') == (10 - 10 + 1) / (10 + 2)


def test_after_nine_all_bad_observations_it_is_not_quarantined_yet():
    memory = TrustMemory(load_settings())

    for _ in range(9):
        memory.record({'agents': {'A': 'bad'}, 'tools': {}})

    assert memory.is_quarantined('A') is False


def test_exactly_ten_observations_with_three_bad_is_not_quarantined():
    memory = TrustMemory(load_settings())

    for _ in range(7):
        memory.record({'agents': {'A': 'good'}, 'tools': {}})
    for _ in range(3):
        memory.record({'agents': {'A': 'bad'}, 'tools': {}})

    assert memory.is_quarantined('A') is False


def test_tool_is_quarantined_when_wrong_rate_exceeds_threshold_and_not_when_one_wrong():
    memory = TrustMemory(load_settings())

    for _ in range(10):
        memory.record({'agents': {}, 'tools': {'T1': 'wrong'}})
    assert memory.is_quarantined('T1') is True

    memory = TrustMemory(load_settings())
    for _ in range(9):
        memory.record({'agents': {}, 'tools': {'T1': 'right'}})
    memory.record({'agents': {}, 'tools': {'T1': 'wrong'}})
    assert memory.is_quarantined('T1') is False


def test_counters_stay_separate_and_empty_evidence_is_a_noop():
    memory = TrustMemory(load_settings())

    memory.record({'agents': {}, 'tools': {}})
    assert memory.agent_seen == {}
    assert memory.tool_seen == {}
    assert memory.q_agents == set()
    assert memory.q_tools == set()

    for _ in range(10):
        memory.record({'agents': {'A': 'good'}, 'tools': {'T2': 'wrong'}})
    assert memory.is_quarantined('A') is False
    assert memory.is_quarantined('T2') is True
