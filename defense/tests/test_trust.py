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


def test_flag_fact_makes_usable_tool_false_for_that_key_only():
    memory = TrustMemory(load_settings(use_fact_quarantine=True), whole_tool_quarantine=False)
    memory.flag_fact('T1', ('W1', 'H1'))

    assert memory.usable_tool('T1', ('W1', 'H1')) is False
    assert memory.usable_tool('T1', ('W1', 'H2')) is True


def test_two_flagged_keys_in_one_warehouse_flag_the_slice():
    settings = load_settings(use_fact_quarantine=True, slice_flag_after=2)
    memory = TrustMemory(settings, whole_tool_quarantine=False)
    memory.flag_fact('T1', ('W1', 'H1'))
    memory.flag_fact('T1', ('W1', 'H2'))

    assert memory.slice_flagged('T1', 'W1') is True
    assert memory.usable_tool('T1', ('W1', 'H3')) is False


def test_two_flagged_keys_in_different_warehouses_do_not_flag_a_slice():
    settings = load_settings(use_fact_quarantine=True, slice_flag_after=2)
    memory = TrustMemory(settings, whole_tool_quarantine=False)
    memory.flag_fact('T1', ('W1', 'H1'))
    memory.flag_fact('T1', ('W2', 'H1'))

    assert memory.slice_flagged('T1', 'W1') is False
    assert memory.slice_flagged('T1', 'W2') is False
    assert memory.usable_tool('T1', ('W1', 'H2')) is True


def test_flagging_the_same_key_twice_does_not_create_a_second_slice_marker():
    settings = load_settings(use_fact_quarantine=True, slice_flag_after=2)
    memory = TrustMemory(settings, whole_tool_quarantine=False)
    memory.flag_fact('T1', ('W1', 'H1'))
    memory.flag_fact('T1', ('W1', 'H1'))

    assert len(memory.flagged_by_slice[('T1', 'W1')]) == 1
    assert memory.slice_flagged('T1', 'W1') is False


def test_flags_mode_keeps_a_wrong_tool_visible_without_whole_tool_quarantine():
    settings = load_settings(use_fact_quarantine=True, min_claims=10)
    memory = TrustMemory(settings, whole_tool_quarantine=False)

    for _ in range(10):
        memory.record({'agents': {}, 'tools': {'T1': 'wrong'}})

    assert memory.is_quarantined('T1') is False

    whole_memory = TrustMemory(load_settings(min_claims=10), whole_tool_quarantine=True)
    for _ in range(10):
        whole_memory.record({'agents': {}, 'tools': {'T1': 'wrong'}})
    assert whole_memory.is_quarantined('T1') is True


def test_flagged_reading_gets_no_vote_in_d4plus_usable_votes():
    from defense.defense import D4Plus
    from defense.fake_claims import AGENT_TOOLS

    defense = D4Plus(
        settings=load_settings(use_fact_quarantine=True),
        seed=11,
        agent_tools=AGENT_TOOLS,
        dependent_tools={'T1', 'T2'},
    )
    defense.memory.flag_fact('T1', ('W1', 'H1'))
    claims = [{
        'mission_id': 0,
        'question': 'time',
        'key': ('W1', 'H1'),
        'agent_id': 'TA1',
        'domain': 'transportation',
        'answer': 17,
        'readings': [{'tool_id': 'T1', 'value': 17}, {'tool_id': 'T3', 'value': 17}],
        'inputs': {'resolved_distance_km': 17},
    }]

    assert defense._usable_votes(claims, ('W1', 'H1')) == {17: 1}


def test_report_flags_returns_fact_and_slice_tuples_in_the_expected_format():
    from defense.defense import D4Plus
    from defense.fake_claims import AGENT_TOOLS

    defense = D4Plus(
        settings=load_settings(use_fact_quarantine=True, slice_flag_after=2),
        seed=12,
        agent_tools=AGENT_TOOLS,
        dependent_tools={'T1', 'T2'},
    )
    defense.memory.flag_fact('T1', ('W1', 'H1'))
    defense.memory.flag_fact('T1', ('W1', 'H2'))

    flags = defense.report()['flags']
    assert ('fact', 'T1', ('W1', 'H1')) in flags
    assert ('slice', 'T1', 'W1') in flags
