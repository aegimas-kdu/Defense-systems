from defense.defense import D4Base, D4Plus
from defense.baselines import MajorityVote, ReadingVote
from defense.evaluate import (
    HEADER,
    format_row,
    make_ask,
    results_table,
    run_mission,
    run_world,
    summarize,
    write_table,
)
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
    for seed in range(1, 6):
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
    for seed in range(1, 21):
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
    for seed in range(1, 21):
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
    for seed in range(1, 21):
        for _, liar in scenario_runs('S3'):
            world = World(seed, poison_mode='scattered', liar=liar, settings=settings)
            defense = D4Base(settings=settings, seed=seed)
            result = run_world(world, defense)
            honest_agents_quarantined += result['honest_agents_quarantined']
            clean_tools_quarantined += result['clean_tools_quarantined']

    print(f"S3 false punishments: honest={honest_agents_quarantined}, clean_tools={clean_tools_quarantined}")
    assert honest_agents_quarantined <= 20
    assert clean_tools_quarantined <= 20


# ---------------------------------------------------------------------------
# Results table and file writer (standard errors in the saved files)
# ---------------------------------------------------------------------------

def make_row(method='D1 answer vote', scenario='S0', liar='n/a'):
    return {
        'method': method,
        'scenario': scenario,
        'mission_success': {'mean': 0.9825, 'stderr': 0.0034},
        'calls_per_mission': {'mean': 12.0, 'stderr': 0.0},
        'honest_agents_quarantined': {'mean': 0.0, 'stderr': 0.0},
        'clean_tools_quarantined': {'mean': 0.075, 'stderr': 0.024145},
        'liar_quarantined': liar,
    }


def small_table(scenarios=('S0', 'S1'), seeds=(1, 2)):
    factories = {
        'D1 answer vote': lambda settings, seed: MajorityVote(settings=settings, seed=seed),
        'D1b reading vote': lambda settings, seed: ReadingVote(settings=settings, seed=seed),
    }
    return results_table(factories, list(scenarios), list(seeds), load_settings())


def test_header_names_every_metric_with_its_standard_error():
    columns = HEADER.rstrip('\n').split('\t')

    assert columns == [
        'method', 'scenario',
        'mission_success', 'mission_success_se',
        'calls_per_mission', 'calls_per_mission_se',
        'honest_agents_quarantined', 'honest_agents_quarantined_se',
        'clean_tools_quarantined', 'clean_tools_quarantined_se',
        'liar_quarantined',
    ]
    assert HEADER.endswith('\n')


def test_format_row_matches_header_and_prints_six_decimals():
    line = format_row(make_row(liar='120/120'))
    fields = line.rstrip('\n').split('\t')

    assert line.endswith('\n')
    assert len(fields) == len(HEADER.rstrip('\n').split('\t'))
    assert fields[:2] == ['D1 answer vote', 'S0']
    assert fields[2:4] == ['0.982500', '0.003400']
    assert fields[8:10] == ['0.075000', '0.024145']
    assert fields[-1] == '120/120'


def test_summarize_single_run_has_zero_standard_error():
    summary = summarize([{'mission_success': 0.5, 'calls_per_mission': 12}])

    assert summary['mission_success'] == {'mean': 0.5, 'stderr': 0.0}


def test_results_table_rows_carry_mean_and_stderr_for_every_written_metric():
    rows = small_table()

    assert len(rows) == 2 * 2  # two scenarios times two methods
    for row in rows:
        for metric in ['mission_success', 'calls_per_mission', 'honest_agents_quarantined', 'clean_tools_quarantined']:
            assert set(row[metric]) == {'mean', 'stderr'}
            assert row[metric]['stderr'] >= 0.0


def test_results_table_liar_label_counts_runs_with_a_liar():
    rows = small_table(scenarios=('S0', 'S1'), seeds=(1, 2))

    s0 = [row for row in rows if row['scenario'] == 'S0']
    s1 = [row for row in rows if row['scenario'] == 'S1']
    assert all(row['liar_quarantined'] == 'n/a' for row in s0)
    # S1 has 6 liar positions per seed, so 2 seeds give 12 liar runs.
    assert all(row['liar_quarantined'].endswith('/12') for row in s1)


def test_write_final_report_includes_seed_and_commit_metadata(tmp_path):
    from defense.evaluate import write_final_report

    output_path = tmp_path / 'final.txt'
    write_final_report(
        seeds=(101, 102),
        output_path=output_path,
        settings=load_settings(),
        git_commit='abc1234',
    )

    text = output_path.read_text(encoding='utf-8')
    assert '# defaults-frozen' in text
    assert '# seeds: 101-102' in text
    assert '# git: abc1234' in text
    assert 'method\tscenario' in text


def test_write_table_writes_header_rows_and_no_notes_when_missing(tmp_path):
    path = tmp_path / 'table.txt'
    rows = [make_row('D1 answer vote', 'S0'), make_row('D1b reading vote', 'S0')]

    write_table(rows, path, tmp_path / 'missing_notes.txt')

    lines = path.read_text(encoding='utf-8').splitlines()
    assert lines[0] == HEADER.rstrip('\n')
    assert len(lines) == 1 + len(rows)
    assert lines[1].startswith('D1 answer vote\tS0\t')


def test_write_table_without_a_notes_path_writes_only_the_table(tmp_path):
    path = tmp_path / 'table.txt'

    write_table([make_row()], path)

    assert len(path.read_text(encoding='utf-8').splitlines()) == 2


def test_write_table_appends_existing_notes_after_a_blank_line(tmp_path):
    path = tmp_path / 'table.txt'
    notes = tmp_path / 'notes.txt'
    notes.write_text('My hand-written commentary.\n', encoding='utf-8')

    write_table([make_row()], path, notes)

    lines = path.read_text(encoding='utf-8').splitlines()
    assert lines[2] == ''
    assert lines[3] == 'My hand-written commentary.'
    # the notes file itself is never modified
    assert notes.read_text(encoding='utf-8') == 'My hand-written commentary.\n'


def test_saved_table_can_be_read_back_with_the_same_means(tmp_path):
    rows = small_table()
    path = tmp_path / 'round_trip.txt'

    write_table(rows, path)

    lines = path.read_text(encoding='utf-8').splitlines()
    columns = lines[0].split('\t')
    parsed = [dict(zip(columns, line.split('\t'))) for line in lines[1:]]
    assert len(parsed) == len(rows)
    for row, record in zip(rows, parsed):
        assert record['method'] == row['method']
        assert record['scenario'] == row['scenario']
        assert float(record['mission_success']) == round(row['mission_success']['mean'], 6)
        assert float(record['mission_success_se']) == round(row['mission_success']['stderr'], 6)
        assert record['liar_quarantined'] == row['liar_quarantined']


def test_d4plus_all_off_matches_d4base_equivalence():
    settings = load_settings()
    for seed in range(1, 6):
        for _, liar in scenario_runs('S3'):
            world_base = World(seed, poison_mode='scattered', liar=liar, settings=settings)
            world_all_off = World(seed, poison_mode='scattered', liar=liar, settings=settings)
            base = D4Base(settings=settings, seed=seed)
            all_off = D4Plus(
                settings=load_settings(
                    use_cascade_revision=False,
                    use_fact_quarantine=False,
                    use_fast_path=False,
                ),
                seed=seed,
            )
            base_result = run_world(world_base, base)
            all_off_result = run_world(world_all_off, all_off)
            assert base_result == all_off_result


def test_d4plus_all_off_matches_d4base_equivalence():
    settings = load_settings()
    for seed in range(1, 6):
        for _, liar in scenario_runs('S3'):
            world_base = World(seed, poison_mode='scattered', liar=liar, settings=settings)
            world_all_off = World(seed, poison_mode='scattered', liar=liar, settings=settings)
            base = D4Base(settings=settings, seed=seed)
            all_off = D4Plus(
                settings=load_settings(
                    use_cascade_revision=False,
                    use_fact_quarantine=False,
                    use_fast_path=False,
                ),
                seed=seed,
            )
            base_result = run_world(world_base, base)
            all_off_result = run_world(world_all_off, all_off)
            assert base_result == all_off_result