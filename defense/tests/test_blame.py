from defense.blame import is_right, question_evidence, tool_agreed_values


def claim(agent, first, second):
    return {
        'agent_id': agent,
        'readings': [
            {'tool_id': first[0], 'value': first[1]},
            {'tool_id': second[0], 'value': second[1]},
        ],
    }


def test_clean_case_all_agents_and_tools_are_right():
    claims = [
        claim('A', ('X', 100), ('Z', 100)),
        claim('B', ('Y', 100), ('X', 100)),
        claim('C', ('Z', 100), ('Y', 100)),
    ]

    evidence = question_evidence(claims, 100)

    assert evidence['agents'] == {'A': 'good', 'B': 'good', 'C': 'good'}
    assert evidence['tools'] == {'X': 'right', 'Y': 'right', 'Z': 'right'}


def test_one_liar_has_bad_agent_and_no_tool_evidence_for_his_tools():
    claims = [
        claim('A', ('X', 100), ('Z', 100)),
        claim('B', ('Y', 70), ('X', 130)),
        claim('C', ('Z', 100), ('Y', 100)),
    ]

    evidence = question_evidence(claims, 100)

    assert evidence['agents'] == {'A': 'good', 'B': 'bad', 'C': 'good'}
    assert evidence['tools'] == {'Z': 'right'}


def test_poisoned_tool_marks_tool_wrong_but_keeps_agents_good():
    claims = [
        claim('A', ('X', 100), ('Z', 100)),
        claim('B', ('Y', 140), ('X', 100)),
        claim('C', ('Z', 100), ('Y', 140)),
    ]

    evidence = question_evidence(claims, 100)

    assert evidence['agents'] == {'A': 'good', 'B': 'good', 'C': 'good'}
    assert evidence['tools'] == {'X': 'right', 'Y': 'wrong', 'Z': 'right'}


def test_poisoned_tool_shared_with_liar_gives_no_tool_evidence_and_blames_liar():
    claims = [
        claim('A', ('Y', 140), ('Z', 100)),
        claim('B', ('Y', 60), ('X', 130)),
        claim('C', ('Z', 100), ('X', 100)),
    ]

    evidence = question_evidence(claims, 100)

    assert evidence['agents'] == {'A': 'good', 'B': 'bad', 'C': 'good'}
    assert evidence['tools'] == {'Z': 'right'}


def test_honest_single_slip_keeps_everyone_good_and_no_tool_evidence_for_slipped_tool():
    claims = [
        claim('A', ('X', 103), ('Z', 100)),
        claim('B', ('Y', 100), ('X', 100)),
        claim('C', ('Z', 100), ('Y', 100)),
    ]

    evidence = question_evidence(claims, 100)

    assert evidence['agents'] == {'A': 'good', 'B': 'good', 'C': 'good'}
    assert evidence['tools'] == {'Y': 'right', 'Z': 'right'}


def test_two_poisoned_tools_leave_agent_good_when_both_wrong_readings_are_explained():
    claims = [
        claim('A', ('Y', 140), ('Z', 140)),
        claim('B', ('Y', 140), ('X', 100)),
        claim('C', ('Z', 140), ('X', 100)),
    ]

    evidence = question_evidence(claims, 100)

    assert evidence['agents'] == {'A': 'good', 'B': 'good', 'C': 'good'}
    assert evidence['tools'] == {'Y': 'wrong', 'Z': 'wrong', 'X': 'right'}


def test_echo_and_garbage_reading_makes_agent_bad_when_only_one_reading_is_explained():
    claims = [
        claim('A', ('Y', 140), ('Z', 55)),
        claim('B', ('X', 100), ('Y', 140)),
        claim('C', ('Z', 100), ('X', 100)),
    ]

    evidence = question_evidence(claims, 100)

    assert evidence['agents'] == {'A': 'bad', 'B': 'good', 'C': 'good'}
    assert evidence['tools'] == {'X': 'right', 'Y': 'wrong'}


def test_excused_tool_counts_as_right_and_no_tool_evidence_is_recorded():
    claims = [
        claim('A', ('Y', 140), ('Z', 100)),
        claim('B', ('Y', 140), ('X', 100)),
        claim('C', ('Z', 100), ('X', 100)),
    ]

    evidence = question_evidence(claims, 100, excused={'Y'})

    assert evidence['agents'] == {'A': 'good', 'B': 'good', 'C': 'good'}
    assert evidence['tools'] == {'X': 'right', 'Z': 'right'}


def test_tool_agreed_values_and_is_right_match_rule():
    claims = [
        claim('A', ('X', 100), ('Z', 100)),
        claim('B', ('Y', 100), ('X', 100)),
        claim('C', ('Z', 100), ('Y', 100)),
    ]

    assert tool_agreed_values(claims) == {'X': 100, 'Y': 100, 'Z': 100}
    assert is_right({'tool_id': 'X', 'value': 100}, 100, frozenset()) is True
    assert is_right({'tool_id': 'Y', 'value': 90}, 100, frozenset()) is False
    assert is_right({'tool_id': 'Y', 'value': 90}, 100, {'Y'}) is True
