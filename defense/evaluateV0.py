import statistics

from defense.fake_claims import DOMAIN_AGENTS, World, scenario_runs


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
    n = len(world.sequence)

    for m in range(n):
        result = run_mission(world, defense, m, tally)
        dist_acc += result['dist']
        time_acc += result['time']
        mission_acc += result['mission']

    report = defense.report()
    quarantined_agents = set(report.get('quarantined_agents', []))
    liar_quarantined = None
    if world.liar is not None:
        liar_quarantined = 1 if world.liar in quarantined_agents else 0
        quarantined_agents -= {world.liar}
    bad_tools = {world.poison_tool} if world.poison_keys else set()
    quarantined_tools = set(report.get('quarantined_tools', [])) - bad_tools

    # False punishments count the innocent agents and clean tools that were flagged.
    return {
        'mission_success': mission_acc / n,
        'dist_acc': dist_acc / n,
        'time_acc': time_acc / n,
        'calls_per_mission': tally['calls'] / n,
        'honest_agents_quarantined': len(quarantined_agents),
        'clean_tools_quarantined': len(quarantined_tools),
        'liar_quarantined': liar_quarantined,
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


def results_table(factories, scenario_names, seeds, settings):
    rows = []
    for scenario_name in scenario_names:
        for method_name, factory in factories.items():
            run_results = []
            liar_hits = 0
            liar_runs = 0
            for seed in seeds:
                for poison_mode, liar in scenario_runs(scenario_name):
                    # A fresh defense per run avoids trust leakage between runs.
                    world = World(seed, poison_mode, liar, settings=settings)
                    defense = factory(settings, seed)
                    result = run_world(world, defense)
                    run_results.append(result)
                    if liar is not None:
                        liar_runs += 1
                        liar_hits += result['liar_quarantined'] or 0

            summary = summarize(run_results)
            liar_label = 'n/a' if liar_runs == 0 else f'{liar_hits}/{liar_runs}'
            rows.append({
                'method': method_name,
                'scenario': scenario_name,
                'mission_success': summary['mission_success'],
                'calls_per_mission': summary['calls_per_mission'],
                'honest_agents_quarantined': summary['honest_agents_quarantined'],
                'clean_tools_quarantined': summary['clean_tools_quarantined'],
                'liar_quarantined': liar_label,
            })

    return rows


if __name__ == '__main__':
    from pathlib import Path

    from defense.baselines import MajorityVote, ReadingVote
    from defense.defense import D4Base
    from defense.settings import load_settings

    factories = {
        'D1 answer vote': lambda settings, seed: MajorityVote(settings=settings, seed=seed),
        'D1b reading vote': lambda settings, seed: ReadingVote(settings=settings, seed=seed),
        'D4 base': lambda settings, seed: D4Base(settings=settings, seed=seed),
    }
    settings = load_settings()
    scenario_names = ['S0', 'S1', 'S2s', 'S2a', 'S3']
    seeds = range(1, 21)

    rows = results_table(factories, scenario_names, seeds, settings)
    results_dir = Path(__file__).resolve().parent.parent / 'results'
    results_dir.mkdir(parents=True, exist_ok=True)
    output_path = results_dir / 'phase_c.txt'

    with output_path.open('w', encoding='utf-8') as fh:
        fh.write('method\tscenario\tmission_success\tcalls_per_mission\thonest_agents_quarantined\tclean_tools_quarantined\tliar_quarantined\n')
        for row in rows:
            fh.write(
                f"{row['method']}\t{row['scenario']}\t"
                f"{row['mission_success']['mean']:.6f}\t{row['calls_per_mission']['mean']:.6f}\t"
                f"{row['honest_agents_quarantined']['mean']:.6f}\t{row['clean_tools_quarantined']['mean']:.6f}\t"
                f"{row['liar_quarantined']}\n"
            )
        fh.write('\n')
        fh.write(
            'Phase C compares D1, D1b and D4-Base across the five core scenarios. '
            'The liar-quarantine column records the number of liar runs caught over all liar-bearing runs for that scenario.'
        )

    print(f'Wrote {output_path}')
