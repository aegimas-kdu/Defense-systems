from defense.fake_claims import (
    ALL_AGENTS,
    KEYS,
    SCENARIOS,
    World,
    make_noise,
    make_sequence,
    make_truth,
    pick_poison_keys,
    poison_value,
    scenario_runs,
)
from defense.settings import Settings


def test_same_seed_gives_same_truth_poison_keys_and_sequence():
    truth_a = make_truth(7)
    truth_b = make_truth(7)
    poison_a = pick_poison_keys(7, 'scattered', 3)
    poison_b = pick_poison_keys(7, 'scattered', 3)
    seq_a = make_sequence(7, 12)
    seq_b = make_sequence(7, 12)

    assert truth_a == truth_b
    assert poison_a == poison_b
    assert seq_a == seq_b


def test_all_distances_are_multiples_of_20_from_20_to_300():
    values = list(make_truth(5).values())

    assert len(values) == 15
    assert all(20 <= value <= 300 and value % 20 == 0 for value in values)


def test_three_poison_modes_have_expected_sizes_and_alignment():
    assert len(pick_poison_keys(9, 'none', 3)) == 0
    assert len(pick_poison_keys(9, 'scattered', 3)) == 3

    aligned = pick_poison_keys(9, 'aligned', 3)
    assert len(aligned) == 3
    assert len({key[0] for key in aligned}) == 1


def test_poison_value_is_never_the_original_number():
    for value in range(2000):
        assert poison_value(value) != value


def test_poison_tool_only_returns_poison_value_on_poison_keys():
    world = World(11, poison_mode='scattered', poison_tool='L1')
    for key in KEYS:
        expected = poison_value(world.truth[key]) if key in world.poison_keys else world.truth[key]
        assert world.tool_value('L1', key, 0) == expected
        assert world.tool_value('L2', key, 0) == world.truth[key]


def test_make_noise_is_identical_for_the_same_seed_and_different_for_other_seeds():
    noise_a = make_noise(13, 10)
    noise_b = make_noise(13, 10)
    noise_c = make_noise(17, 10)

    assert noise_a == noise_b
    assert noise_a != noise_c
    assert all(len(values) == 2 for values in noise_a.values())
    assert all(len(tuple_value) == 3 for values in noise_a.values() for tuple_value in values)


def test_reading_the_same_agent_twice_gives_the_identical_claim():
    world = World(3, poison_mode='none', liar=None)

    claim_a = world.read('LA1', ('W1', 'H1'), 7, 'dist')
    claim_b = world.read('LA1', ('W1', 'H1'), 7, 'dist')

    assert claim_a == claim_b


def test_liar_readings_never_equal_the_truth():
    world = World(4, poison_mode='none', liar='TA2')
    claim = world.read('TA2', ('W2', 'H3'), 5, 'time', dres=120)

    assert claim['answer'] != world.true_value('time', ('W2', 'H3'))
    assert all(reading['value'] != world.true_value('time', ('W2', 'H3')) for reading in claim['readings'])


def test_honest_agent_reading_matches_tool_value_except_for_about_2_5_percent_slips():
    world = World(5, poison_mode='none', liar=None)
    total = 0
    wrong = 0

    for m in range(200):
        claim = world.read('LA1', ('W1', 'H1'), m, 'dist')
        total += 1
        if claim['answer'] != world.tool_value(claim['readings'][0]['tool_id'], ('W1', 'H1'), None):
            wrong += 1

    assert 0.01 <= wrong / total <= 0.04


def test_every_claim_has_the_agreed_keys_and_two_readings():
    world = World(6, poison_mode='none', liar='LA2')
    claim = world.read('LA2', ('W3', 'H2'), 11, 'dist')

    assert set(claim) == {'mission_id', 'question', 'key', 'agent_id', 'domain', 'answer', 'readings', 'inputs'}
    assert len(claim['readings']) == 2
    assert set(claim['readings'][0]) == {'tool_id', 'value'}
    assert set(claim['readings'][1]) == {'tool_id', 'value'}


def test_poisoned_tool_reading_matches_the_poisoned_value_for_the_first_tool():
    settings = Settings(slip_rate=0.0)
    world = World(7, poison_mode='scattered', poison_tool='L1', liar=None, settings=settings)
    key = next(iter(world.poison_keys))
    claim = world.read('LA1', key, 1, 'dist')

    assert claim['readings'][0]['tool_id'] == 'L1'
    assert claim['readings'][0]['value'] == poison_value(world.true_value('dist', key))


def test_scenario_runs_match_expected_lengths():
    assert len(scenario_runs('S0')) == 1
    assert len(scenario_runs('S1')) == len(ALL_AGENTS)
    assert len(scenario_runs('S2s')) == 1
    assert len(scenario_runs('S2a')) == 1
    assert len(scenario_runs('S3')) == len(ALL_AGENTS)
    assert SCENARIOS['S0'] == 'clean'


def test_every_scenario_for_one_seed_builds_a_world_without_error():
    for name in SCENARIOS:
        for poison_mode, liar in scenario_runs(name):
            world = World(12, poison_mode=poison_mode, liar=liar)
            assert world.sequence


def test_same_pair_and_seed_give_identical_sequences():
    pair = ('scattered', 'LA2')
    world_a = World(9, poison_mode=pair[0], liar=pair[1])
    world_b = World(9, poison_mode=pair[0], liar=pair[1])
    assert world_a.sequence == world_b.sequence


def test_s3_liar_is_not_the_poison_tool():
    poison_tool = 'L1'
    for _, liar in scenario_runs('S3'):
        assert liar != poison_tool
