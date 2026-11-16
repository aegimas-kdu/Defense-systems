import copy
import pytest

from simulator import registry as R
from simulator import truth as T
from simulator.agents.coordinator import AgentCoordinator
from simulator.defense import MajorityVoteDefense
from simulator.world_ids import WAREHOUSE_IDS, MEDICINES

W = R.get_world()
AGENTS = lambda domain: [a['agent_id'] for a in W['agents'] if a['domain'] == domain]


def route_keys():
    return [{'warehouse': w, 'hospital': h, 'vehicle': v} for w, h, v in T.all_routes()]


def truth_for(question, key, inputs=None):
    w, h, v = key.get('warehouse'), key.get('hospital'), key.get('vehicle')
    return {'Q1': lambda: T.truth_stock(w, key.get('medicine')), 'Q2': lambda: T.truth_capacity(v),
            'Q3': lambda: T.truth_distance(w, h), 'Q4': lambda: T.truth_time_minutes(w, h, v),
            'Q5': lambda: T.truth_cost(w, h, v)}[question]()


def all_cases():
    for w in WAREHOUSE_IDS.values():
        for m in MEDICINES:
            yield 'Q1', {'warehouse': w, 'medicine': m}, None
    for key in route_keys():
        d = T.truth_distance(key['warehouse'], key['hospital'])
        yield 'Q2', key, None
        yield 'Q3', key, None
        yield 'Q4', key, {'resolved_distance_km': d}
        yield 'Q5', key, None


def test_key_test_different_routes_give_different_values():
    eta = {w: R.get_claim('T_Agent_3', 'Q4', {'warehouse': w, 'hospital': 'C4', 'vehicle': 'Truck'},
                          {'resolved_distance_km': 1})['answer'] for w in ('W1', 'W2', 'W3')}
    assert eta == {'W1': 186, 'W2': 143, 'W3': 157} or len(set(eta.values())) == 3
    bill = {w: R.get_claim('L_Agent_3', 'Q5', {'warehouse': w, 'hospital': 'C4', 'vehicle': 'Truck'})['answer']
            for w in ('W1', 'W2', 'W3')}
    assert bill == {'W1': 520, 'W2': 400, 'W3': 440}


def test_backup_reading_uses_the_same_key():
    claim = R.get_claim('W_Agent_1', 'Q1', {'warehouse': 'W3', 'medicine': 'Malaria Treatment'})
    assert [r['value'] for r in claim['readings']] == [470, 470]


def test_all_three_agents_of_a_domain_get_the_same_question():
    coord = AgentCoordinator()
    for q, domain in (('Q3', 'Logistics'), ('Q5', 'Logistics'), ('Q2', 'Transportation')):
        _, claims = coord.ask(q, {'warehouse': 'W2', 'hospital': 'C2', 'vehicle': 'Truck'})
        assert sorted(c['agent_id'] for c in claims) == sorted(AGENTS(domain))
        assert {c['question'] for c in claims} == {q}


def test_consistency_clean_world_all_routes_equal_truth():
    for q, key, inputs in all_cases():
        domain = R.QUESTIONS[q]['domain']
        for agent_id in AGENTS(domain):
            claim = R.get_claim(agent_id, q, key, inputs)
            expected = truth_for(q, key)
            assert [r['value'] for r in claim['readings']] == [expected, expected], (q, key, agent_id)
            assert claim['answer'] == expected


def test_no_fallback_missing_key_raises():
    with pytest.raises(LookupError):
        R.get_claim('L_Agent_2', 'Q3', {'warehouse': 'W9', 'hospital': 'C2', 'vehicle': 'Truck'})
    with pytest.raises(ValueError):
        R.get_claim('W_Agent_1', 'Q3', {'warehouse': 'W1', 'hospital': 'C2', 'vehicle': 'Truck'})  # wrong domain
    with pytest.raises(ValueError):
        R.get_claim('T_Agent_1', 'Q4', {'warehouse': 'W1', 'hospital': 'C2', 'vehicle': 'Truck'})  # no distance


def test_independence_poisoning_one_tool_changes_only_its_readings():
    key = {'warehouse': 'W3', 'hospital': 'C2', 'vehicle': 'Truck'}
    poisoned = copy.deepcopy(W)
    rec = R.find_record(poisoned, 'gis_distance_matrix', key)
    rec['map_distance_km'] = 999
    clean = {c['agent_id']: c for c in (R.get_claim(a, 'Q3', key) for a in AGENTS('Logistics'))}
    dirty = {c['agent_id']: c for c in (R.get_claim(a, 'Q3', key, world=poisoned) for a in AGENTS('Logistics'))}
    for agent_id in clean:
        for r_clean, r_dirty in zip(clean[agent_id]['readings'], dirty[agent_id]['readings']):
            if r_clean['tool_id'] == 'gis_distance_matrix':
                assert r_dirty['value'] == 999
            else:
                assert r_dirty['value'] == r_clean['value']
    # the fleet/GPS/fuel readings must not change (no hidden dependency on GIS)
    t_clean = R.get_claim('T_Agent_1', 'Q4', key, {'resolved_distance_km': 110})
    t_dirty = R.get_claim('T_Agent_1', 'Q4', key, {'resolved_distance_km': 110}, world=poisoned)
    assert t_clean['readings'] == t_dirty['readings']


def test_format_test_claim_shape_and_whole_numbers():
    claim = R.get_claim('T_Agent_1', 'Q4', {'warehouse': 'W3', 'hospital': 'C2', 'vehicle': 'Truck'},
                        {'resolved_distance_km': 110}, mission_id=17)
    assert set(claim) == {'mission_id', 'question', 'key', 'agent_id', 'domain', 'answer', 'readings', 'inputs'}
    assert claim['key'] == ['W3', 'C2', 'Truck'] and claim['answer'] == 157 and len(claim['readings']) == 2
    assert all(isinstance(r['value'], int) for r in claim['readings'])


def test_cascade_wrong_distance_changes_only_q4_routes_1_and_2():
    key = {'warehouse': 'W3', 'hospital': 'C2', 'vehicle': 'Truck'}
    vals = {a: R.get_claim(a, 'Q4', key, {'resolved_distance_km': 500})['answer'] for a in AGENTS('Transportation')}
    assert vals['T_Agent_3'] == 157          # ETA tool ignores the distance input
    assert vals['T_Agent_1'] != 157 and vals['T_Agent_2'] != 157


def test_truth_separation_wrong_decision_changes_the_plan():
    class LyingDefense:
        def decide(self, question, key, claims):
            return 0 if question == 'Q1' else MajorityVoteDefense().decide(question, key, claims)
    honest = AgentCoordinator().run_simulation('Malaria Treatment', 50, 'Rutana Refugee Camp')
    wrong = AgentCoordinator(defense=LyingDefense()).run_simulation('Malaria Treatment', 50, 'Rutana Refugee Camp')
    assert honest['warehouse']['decision'] == 'Approved' and wrong['warehouse']['decision'] == 'Rejected'


def test_screenshot_case_is_now_consistent():
    result = AgentCoordinator().run_simulation('Malaria Treatment', 50, 'Rutana Refugee Camp')
    by_q = {}
    for c in result['agents']:
        by_q.setdefault(c['question'], set()).add(c['answer'])
    assert all(len(v) == 1 for v in by_q.values()), by_q


def test_nodefense_is_repeatable_and_picks_one_agents_answer():
    from simulator.nodefense import NoDefense
    key = {'warehouse': 'W2', 'hospital': 'C1', 'vehicle': 'Van'}
    claims = [R.get_claim(a, 'Q2', key, mission_id=5) for a in AGENTS('Transportation')]
    first = NoDefense(seed=1).decide('Q2', key, claims)
    again = NoDefense(seed=1).decide('Q2', key, claims)
    assert first == again == 120
    liar = [dict(c) for c in claims]
    liar[0]['answer'] = 9999
    picks = {NoDefense(seed=s).decide('Q2', key, liar) for s in range(40)}
    assert picks == {120, 9999}   # with no defense, a lying agent's answer can be chosen