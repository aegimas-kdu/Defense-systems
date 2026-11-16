import argparse
import statistics
import subprocess

from defense.fake_claims import DOMAIN_AGENTS, World, SCENARIO_WINDOWS, scenario_runs
from defense.settings import load_settings


def make_ask(world, key, m, qtype, dres, tally):
    # The defense only chooses agent ids; the evaluator fills in the claims and counts tool use.
    def ask(agent_ids):
        claims = [world.read(a, key, m, qtype, dres) for a in agent_ids]
        tally['calls'] += 2 * len(agent_ids)
        return claims

    return ask


def run_mission(world, defense, m, tally):
    key = world.sequence[m]

    # Distance question first; the coordinator resolves a single distance value.
    ask_dist = make_ask(world, key, m, 'dist', None, tally)
    dec_d = defense.decide('dist', key, DOMAIN_AGENTS['dist'], ask_dist)

    # Then the time question uses the distance decision as an input to the evaluator.
    ask_time = make_ask(world, key, m, 'time', dec_d['value'], tally)
    dec_t = defense.decide('time', key, DOMAIN_AGENTS['time'], ask_time, parent=dec_d)

    defense.end_mission([dec_d, dec_t])

    # The evaluator compares the final outcomes to the hidden truth, without exposing it to the defense.
    final_d = dec_t['revised_parent'] if dec_t.get('revised_parent') is not None else dec_d['value']
    ok_d = final_d == world.true_value('dist', key)
    ok_t = dec_t['value'] == world.true_value('time', key)
    return {'dist': ok_d, 'time': ok_t, 'mission': ok_d and ok_t}


def run_world(world, defense):
    tally = {'calls': 0}
    dist_acc = 0
    time_acc = 0
    mission_acc = 0
    success_second_half = 0
    n = len(world.sequence)
    half = n // 2

    for m in range(n):
        result = run_mission(world, defense, m, tally)
        dist_acc += result['dist']
        time_acc += result['time']
        mission_acc += result['mission']
        if m >= half:
            success_second_half += result['mission']

    report = defense.report()
    quarantined_agents = set(report.get('quarantined_agents', []))
    liar_quarantined = None
    if world.liar is not None:
        if world.liar_live_at_end():
            liar_quarantined = 1 if world.liar in quarantined_agents else 0
        else:
            liar_quarantined = 0
        quarantined_agents -= {world.liar}
    if world.liar is not None and not world.liar_live_at_end():
        quarantined_agents.discard(world.liar)
    bad_tools = {world.poison_tool} if world.poison_keys and world.poison_live_at_end() else set()
    quarantined_tools = set(report.get('quarantined_tools', [])) - bad_tools

    flags = set(report.get('flags', set()))
    false_flags = 0
    for flag in flags:
        if flag[0] != 'fact':
            continue
        _, tool, key = flag
        if tool != world.poison_tool or key not in world.poison_keys:
            false_flags += 1

    slice_waste = 0
    for flag in flags:
        if flag[0] != 'slice':
            continue
        _, tool, warehouse = flag
        keys_in_slice = [key for key in world.truth if key[0] == warehouse]
        if tool == world.poison_tool:
            slice_waste += sum(1 for key in keys_in_slice if key not in world.poison_keys)
        else:
            slice_waste += len(keys_in_slice)

    # False punishments count the innocent agents and clean tools that were flagged.
    return {
        'mission_success': mission_acc / n,
        'dist_acc': dist_acc / n,
        'time_acc': time_acc / n,
        'calls_per_mission': tally['calls'] / n,
        'honest_agents_quarantined': len(quarantined_agents),
        'clean_tools_quarantined': len(quarantined_tools),
        'liar_quarantined': liar_quarantined,
        'false_flags': false_flags,
        'slice_waste': slice_waste,
        'flaps': report.get('flaps', 0),
        'success_second_half': success_second_half / max(1, n - half),
    }


def summarize(results):
    if not results:
        return {}

    metrics = list(results[0].keys())
    summary = {}
    for metric in metrics:
        values = [item[metric] for item in results if item.get(metric) is not None]
        if not values:
            continue
        mean = round(statistics.mean(values), 12)
        stderr = 0.0 if len(values) < 2 else round(statistics.stdev(values) / len(values) ** 0.5, 12)
        summary[metric] = {'mean': mean, 'stderr': stderr}

    return summary


def results_table(factories, scenario_names, seeds, settings, metrics=None):
    if metrics is None:
        metrics = ['mission_success', 'calls_per_mission', 'honest_agents_quarantined', 'clean_tools_quarantined']

    rows = []
    for scenario_name in scenario_names:
        for method_name, factory in factories.items():
            run_results = []
            liar_hits = 0
            liar_runs = 0
            for seed in seeds:
                for poison_mode, liar in scenario_runs(scenario_name):
                    # A fresh defense per run avoids trust leakage between runs.
                    world_args = dict(SCENARIO_WINDOWS.get(scenario_name, {}))
                    if scenario_name in {'S5', 'S6', 'S7'}:
                        event_at = settings.event_at
                        if scenario_name == 'S5':
                            world_args = {'poison_window': (0, event_at), 'liar_window': (0, None)}
                        elif scenario_name == 'S6':
                            world_args = {'poison_window': (0, None), 'liar_window': (0, event_at)}
                        elif scenario_name == 'S7':
                            world_args = {'poison_window': (event_at, None), 'liar_window': (event_at, None)}
                    world = World(seed, poison_mode, liar, settings=settings, **world_args)
                    defense = factory(settings, seed)
                    result = run_world(world, defense)
                    run_results.append(result)
                    if liar is not None:
                        liar_runs += 1
                        liar_hits += result['liar_quarantined'] or 0

            summary = summarize(run_results)
            liar_label = 'n/a' if liar_runs == 0 else f'{liar_hits}/{liar_runs}'
            row = {'method': method_name, 'scenario': scenario_name, 'liar_quarantined': liar_label}
            for metric in metrics:
                row[metric] = summary[metric]
            rows.append(row)

    return rows


HEADER = (
    'method\tscenario\tmission_success\tmission_success_se\tcalls_per_mission\tcalls_per_mission_se\t'
    'honest_agents_quarantined\thonest_agents_quarantined_se\tclean_tools_quarantined\t'
    'clean_tools_quarantined_se\tliar_quarantined\n'
)

PHASE_D_HEADER = (
    'method\tscenario\tmission_success\tmission_success_se\tsuccess_second_half\t'
    'success_second_half_se\tcalls_per_mission\tcalls_per_mission_se\t'
    'honest_agents_quarantined\thonest_agents_quarantined_se\tclean_tools_quarantined\t'
    'clean_tools_quarantined_se\tfalse_flags\tfalse_flags_se\tslice_waste\t'
    'slice_waste_se\tflaps\tflaps_se\tliar_quarantined\n'
)


def format_row(row, metrics=None):
    # Every metric is written as its mean followed by its standard error.
    if metrics is None:
        metrics = ['mission_success', 'calls_per_mission', 'honest_agents_quarantined', 'clean_tools_quarantined']
    parts = [row['method'], row['scenario']]
    for metric in metrics:
        parts.append(f"{row[metric]['mean']:.6f}")
        parts.append(f"{row[metric]['stderr']:.6f}")
    parts.append(row['liar_quarantined'])
    return '\t'.join(parts) + '\n'


def format_phase_d_row(row):
    metrics = [
        'mission_success', 'success_second_half', 'calls_per_mission',
        'honest_agents_quarantined', 'clean_tools_quarantined', 'false_flags',
        'slice_waste', 'flaps',
    ]
    return format_row(row, metrics=metrics)


def write_table(rows, path, notes_path=None, header=HEADER, formatter=None):
    """Write the results table, then the hand-written notes (if the notes file exists) under it."""
    if formatter is None:
        formatter = format_row
    with path.open('w', encoding='utf-8') as fh:
        fh.write(header)
        for row in rows:
            fh.write(formatter(row))
        if notes_path is not None and notes_path.exists():
            fh.write('\n')
            fh.write(notes_path.read_text(encoding='utf-8').strip() + '\n')


def get_git_commit():
    try:
        return subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return 'unknown'


def build_phase_d_factories(settings):
    from defense.baselines import MajorityVote, ReadingVote
    from defense.defense import D4Base, D4Plus
    from defense.fake_claims import AGENT_TOOLS

    return {
        'D1 answer vote': lambda settings, seed: MajorityVote(settings=settings, seed=seed),
        'D1b reading vote': lambda settings, seed: ReadingVote(settings=settings, seed=seed),
        'D4 base': lambda settings, seed: D4Base(settings=settings, seed=seed),
        'D4+ cascade, flags, fast': lambda settings, seed: D4Plus(
            settings=load_settings(
                use_cascade_revision=True,
                use_fact_quarantine=True,
                use_fast_path=True,
            ),
            seed=seed,
            agent_tools=AGENT_TOOLS,
            dependent_tools={'T1', 'T2'},
        ),
        'D4+ cascade, flags': lambda settings, seed: D4Plus(
            settings=load_settings(use_cascade_revision=True, use_fact_quarantine=True, use_fast_path=False),
            seed=seed,
            agent_tools=AGENT_TOOLS,
            dependent_tools={'T1', 'T2'},
        ),
        'D4+ cascade, fast': lambda settings, seed: D4Plus(
            settings=load_settings(use_cascade_revision=True, use_fact_quarantine=False, use_fast_path=True),
            seed=seed,
            agent_tools=AGENT_TOOLS,
            dependent_tools={'T1', 'T2'},
        ),
        'D4+ flags, fast': lambda settings, seed: D4Plus(
            settings=load_settings(use_cascade_revision=False, use_fact_quarantine=True, use_fast_path=True),
            seed=seed,
            agent_tools=AGENT_TOOLS,
            dependent_tools={'T1', 'T2'},
        ),
        'D4+ cascade': lambda settings, seed: D4Plus(
            settings=load_settings(use_cascade_revision=True, use_fact_quarantine=False, use_fast_path=False),
            seed=seed,
            agent_tools=AGENT_TOOLS,
            dependent_tools={'T1', 'T2'},
        ),
        'D4+ flags': lambda settings, seed: D4Plus(
            settings=load_settings(use_cascade_revision=False, use_fact_quarantine=True, use_fast_path=False),
            seed=seed,
            agent_tools=AGENT_TOOLS,
            dependent_tools={'T1', 'T2'},
        ),
        'D4+ fast': lambda settings, seed: D4Plus(
            settings=load_settings(use_cascade_revision=False, use_fact_quarantine=False, use_fast_path=True),
            seed=seed,
            agent_tools=AGENT_TOOLS,
            dependent_tools={'T1', 'T2'},
        ),
        'D4+ all off': lambda settings, seed: D4Plus(
            settings=load_settings(use_cascade_revision=False, use_fact_quarantine=False, use_fast_path=False),
            seed=seed,
            agent_tools=AGENT_TOOLS,
            dependent_tools={'T1', 'T2'},
        ),
    }


def write_final_report(seeds, output_path, settings, git_commit=None):
    from pathlib import Path

    if isinstance(seeds, range):
        seed_values = list(seeds)
    else:
        seed_values = list(seeds)
    if not seed_values:
        raise ValueError('At least one seed is required.')

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = results_table(
        build_phase_d_factories(settings),
        ['S0', 'S1', 'S2s', 'S2a', 'S3', 'S5', 'S6', 'S7'],
        seed_values,
        settings,
        metrics=['mission_success', 'success_second_half', 'calls_per_mission', 'honest_agents_quarantined',
                 'clean_tools_quarantined', 'false_flags', 'slice_waste', 'flaps'],
    )

    commit = git_commit or get_git_commit()
    with output_path.open('w', encoding='utf-8') as fh:
        fh.write(f'# defaults-frozen\n')
        fh.write(f'# seeds: {seed_values[0]}-{seed_values[-1]}\n')
        fh.write(f'# git: {commit}\n\n')
        fh.write(PHASE_D_HEADER)
        for row in rows:
            fh.write(format_phase_d_row(row))

    return output_path


def main():
    from pathlib import Path

    from defense.baselines import MajorityVote, ReadingVote
    from defense.defense import D4Base, D4Plus
    from defense.fake_claims import AGENT_TOOLS
    from defense.settings import load_settings

    parser = argparse.ArgumentParser(description='Generate the evaluation tables used in the defense paper.')
    parser.add_argument('--seeds', nargs=2, type=int, metavar=('START', 'END'), default=(101, 200),
                        help='Inclusive test-seed range for the final report (default: 101 200).')
    parser.add_argument('--output', default='results/final.txt', help='Path to the final report output.')
    args = parser.parse_args()

    start_seed, end_seed = args.seeds
    if start_seed > end_seed:
        raise ValueError('Seed start must be <= seed end.')

    factories = {
        'D1 answer vote': lambda settings, seed: MajorityVote(settings=settings, seed=seed),
        'D1b reading vote': lambda settings, seed: ReadingVote(settings=settings, seed=seed),
        'D4 base': lambda settings, seed: D4Base(settings=settings, seed=seed),
        'D4 plus': lambda settings, seed: D4Plus(
            settings=settings,
            seed=seed,
            agent_tools=AGENT_TOOLS,
            dependent_tools={'T1', 'T2'},
        ),
    }
    settings = load_settings()
    scenario_names = ['S0', 'S1', 'S2s', 'S2a', 'S3']
    seeds = range(start_seed, end_seed + 1)

    # One run of everything. Phase B is the baselines-only view of the same rows,
    # so the two files can never disagree.
    rows = results_table(factories, scenario_names, seeds, settings)
    baseline_methods = {'D1 answer vote', 'D1b reading vote'}
    baseline_rows = [row for row in rows if row['method'] in baseline_methods]

    results_dir = Path(__file__).resolve().parent.parent / 'results'
    results_dir.mkdir(parents=True, exist_ok=True)
    write_table(baseline_rows, results_dir / 'phase_b_baselines.txt', results_dir / 'phase_b_notes.txt')
    write_table(rows, results_dir / 'phase_c.txt', results_dir / 'phase_c_notes.txt')

    final_output = results_dir / args.output if not Path(args.output).is_absolute() else Path(args.output)
    write_final_report(seeds, final_output, settings)

    phase_d_rows = results_table(
        build_phase_d_factories(settings),
        ['S0', 'S1', 'S2s', 'S2a', 'S3', 'S5', 'S6', 'S7'],
        seeds,
        settings,
        metrics=['mission_success', 'success_second_half', 'calls_per_mission', 'honest_agents_quarantined',
                 'clean_tools_quarantined', 'false_flags', 'slice_waste', 'flaps'],
    )
    write_table(
        phase_d_rows,
        results_dir / 'phase_d.txt',
        results_dir / 'phase_d_notes.txt',
        header=PHASE_D_HEADER,
        formatter=format_phase_d_row,
    )

    print(f"Wrote {results_dir / 'phase_b_baselines.txt'}")
    print(f"Wrote {results_dir / 'phase_c.txt'}")
    print(f"Wrote {results_dir / 'phase_d.txt'}")
    print(f"Wrote {final_output}")


if __name__ == '__main__':
    main()
