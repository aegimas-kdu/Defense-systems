from defense.old_fake_claims import (
    AGENTS,
    SCENARIOS,
    generate_stream,
    make_poisoned_table,
    make_true_facts,
    poison_value,
    liar_value,
    slip_value,
    SLIP_RATE
)
import random

import random


def test_repeatable_stream():
    stream_a = generate_stream('S1', 5)
    stream_b = generate_stream('S1', 5)
    assert stream_a == stream_b


def test_shape_and_claim_keys():
    stream = generate_stream('S0', 11)

    assert len(stream) == 300
    assert all(len(question['claims']) == len(AGENTS) for question in stream)
    assert all(
        set(question.keys()) == {'question_id', 'domain', 'fact_key', 'true_value', 'claims'}
        for question in stream
    )
    assert all(
        set(claim.keys()) == {'mission_id', 'agent_id', 'domain', 'tool_id', 'fact_key', 'claim'}
        for question in stream
        for claim in question['claims']
    )


def test_s0_wrong_fraction_is_about_5_percent():
    stream = generate_stream('S0', 17)
    wrong = [
        claim['claim'] != question['true_value']
        for question in stream
        for claim in question['claims']
    ]
    wrong_fraction = sum(wrong) / len(wrong)
    assert 0.02 <= wrong_fraction <= 0.09


def test_s1_liars_are_always_wrong_and_others_are_about_5_percent():
    stream = generate_stream('S1', 9)
    liar_id = SCENARIOS['S1']['liars'][0]

    liar_wrong = []
    other_wrong = []
    for question in stream:
        for claim in question['claims']:
            is_wrong = claim['claim'] != question['true_value']
            if claim['agent_id'] == liar_id:
                liar_wrong.append(is_wrong)
            else:
                other_wrong.append(is_wrong)

    assert liar_wrong and all(liar_wrong)
    assert 0.02 <= sum(other_wrong) / len(other_wrong) <= 0.09


def test_s2_poisoned_tool_has_about_20_percent_plus_slips():
    stream = generate_stream('S2', 23)
    poisoned = []
    clean = []
    for question in stream:
        for claim in question['claims']:
            is_wrong = claim['claim'] != question['true_value']
            if claim['tool_id'] == 'WH-T1':
                poisoned.append(is_wrong)
            else:
                clean.append(is_wrong)

    poisoned_fraction = sum(poisoned) / len(poisoned)
    clean_fraction = sum(clean) / len(clean)
    assert 0.08 <= poisoned_fraction <= 0.45
    assert 0.02 <= clean_fraction <= 0.09
    assert poisoned_fraction > clean_fraction + 0.10


def test_make_poisoned_table_is_repeatable_and_roughly_20_percent_changed():
    truth = make_true_facts(7)
    table_a = make_poisoned_table(truth, 'WH-T1', 7)
    table_b = make_poisoned_table(truth, 'WH-T1', 7)

    assert table_a == table_b

    changed = {key for key, value in truth.items() if table_a[key] != value}
    assert 3 <= len(changed) <= 14
    assert all(table_a[key] == value for key, value in truth.items() if key not in changed)


def test_fair_comparison_between_s0_and_s1():
    stream_0 = generate_stream('S0', 13)
    stream_1 = generate_stream('S1', 13)

    assert [question['fact_key'] for question in stream_0] == [question['fact_key'] for question in stream_1]
    assert all(
        [claim['tool_id'] for claim in q0['claims']] == [claim['tool_id'] for claim in q1['claims']]
        for q0, q1 in zip(stream_0, stream_1)
    )

def wrong_fraction(claims, true_values):
    wrong = [c['claim'] != true_values[c['mission_id']] for c in claims]
    return sum(wrong) / len(wrong)


def all_claims(stream):
    return [c for q in stream for c in q['claims']]


def truth_by_question(stream):
    return {q['question_id']: q['true_value'] for q in stream}


def test_wrong_value_helpers_never_return_original():
    rng = random.Random(0)
    for v in range(2000):
        assert poison_value(v) != v
        assert liar_value(v, rng) != v
        assert slip_value(v, rng) != v


def test_s3_liar_always_wrong_and_poisoned_tool_hurts_the_others():
    stream = generate_stream('S3', 31)
    truth = truth_by_question(stream)
    claims = all_claims(stream)

    liar_claims = [c for c in claims if c['agent_id'] == 'WH-2']
    assert liar_claims and all(c['claim'] != truth[c['mission_id']] for c in liar_claims)

    others = [c for c in claims if c['agent_id'] != 'WH-2']
    on_poisoned = [c for c in others if c['tool_id'] == 'WH-T1']
    on_clean = [c for c in others if c['tool_id'] != 'WH-T1']
    assert wrong_fraction(on_poisoned, truth) > wrong_fraction(on_clean, truth) + 0.10


def test_s4_poison_is_repaired_at_question_100():
    stream = generate_stream('S4', 41)
    truth = truth_by_question(stream)
    t1 = [c for c in all_claims(stream) if c['tool_id'] == 'WH-T1']
    before = [c for c in t1 if c['mission_id'] < 100]
    after = [c for c in t1 if c['mission_id'] >= 100]

    assert wrong_fraction(before, truth) > wrong_fraction(after, truth) + 0.10
    assert 0.01 <= wrong_fraction(after, truth) <= 0.10


def test_s2_every_reader_of_a_poisoned_fact_gets_the_same_wrong_value():
    seed = 23
    stream = generate_stream('S2', seed)
    truth = make_true_facts(seed)
    table = make_poisoned_table(truth, 'WH-T1', seed)
    poisoned_keys = {k for k, v in truth.items() if table[k] != v}
    assert poisoned_keys

    wrong_on_poisoned = [
        c for c in all_claims(stream)
        if c['tool_id'] == 'WH-T1'
        and c['fact_key'] in poisoned_keys
        and c['claim'] != truth[c['fact_key']]
    ]
    assert wrong_on_poisoned
    same_value = [
        c for c in wrong_on_poisoned
        if c['claim'] == poison_value(truth[c['fact_key']])
    ]
    assert len(same_value) / len(wrong_on_poisoned) >= 0.90


def test_honest_agents_make_identical_claims_in_s0_and_s1():
    stream_0 = generate_stream('S0', 13)
    stream_1 = generate_stream('S1', 13)

    def honest(stream):
        return [(c['mission_id'], c['agent_id'], c['claim'])
                for c in all_claims(stream) if c['agent_id'] in ('WH-1', 'WH-3')]

    assert honest(stream_0) == honest(stream_1)