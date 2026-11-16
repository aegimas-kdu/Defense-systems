from defense.cascade import cascade_check, excused_tools, time_from_distance, distance_from_time


def test_time_and_distance_are_identity_in_this_world():
    assert time_from_distance(140) == 140
    assert distance_from_time(140) == 140


def test_cascade_revises_parent_when_independent_values_agree_on_a_candidate():
    parent = {'value': 140, 'support': 2, 'candidates': {140: 2, 100: 2}}
    assert cascade_check(parent, [100, 100]) == {'revised_parent': 100, 'value': 100, 'support': 4}


def test_cascade_returns_none_when_independent_values_match_parent():
    parent = {'value': 140, 'support': 2, 'candidates': {140: 2, 100: 2}}
    assert cascade_check(parent, [140, 140]) is None


def test_cascade_returns_none_when_independent_values_disagree():
    parent = {'value': 140, 'support': 2, 'candidates': {140: 2, 100: 2}}
    assert cascade_check(parent, [100, 103]) is None


def test_cascade_returns_none_when_implied_value_is_not_a_candidate():
    parent = {'value': 140, 'support': 2, 'candidates': {140: 2, 120: 2}}
    assert cascade_check(parent, [55, 55]) is None


def test_cascade_returns_none_when_revision_would_not_exceed_parent_support():
    parent = {'value': 140, 'support': 4, 'candidates': {140: 4, 100: 1}}
    assert cascade_check(parent, [100, 100]) is None


def test_cascade_returns_none_for_a_single_independent_value():
    parent = {'value': 140, 'support': 2, 'candidates': {140: 2, 100: 2}}
    assert cascade_check(parent, [100]) is None


def test_excused_tools_only_returns_tools_whose_readings_all_equal_old_parent_time():
    claims = [
        {'agent_id': 'A1', 'readings': [{'tool_id': 'T1', 'value': 140}, {'tool_id': 'T2', 'value': 140}]},
        {'agent_id': 'A2', 'readings': [{'tool_id': 'T1', 'value': 140}, {'tool_id': 'T2', 'value': 140}]},
        {'agent_id': 'A3', 'readings': [{'tool_id': 'T1', 'value': 90}, {'tool_id': 'T2', 'value': 140}]},
    ]
    assert excused_tools(claims, {'T1', 'T2'}, 140) == {'T2'}
