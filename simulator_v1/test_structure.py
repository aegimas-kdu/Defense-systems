import json
from pathlib import Path


def test_simulator_has_nine_agents_and_nine_tools():
    root = Path(__file__).resolve().parent
    agents = json.loads((root / 'data' / 'agents.json').read_text())
    tool_files = sorted((root / 'data' / 'tools').glob('*.json'))

    assert len(agents) == 9
    assert len(tool_files) == 9

    domains = {agent['domain'] for agent in agents}
    assert domains == {'Warehouse', 'Transportation', 'Logistics'}

    domain_counts = {domain: 0 for domain in domains}
    for agent in agents:
        domain_counts[agent['domain']] += 1
        assert agent['primary_tool']
        assert agent['backup_tool']

    assert domain_counts == {'Warehouse': 3, 'Transportation': 3, 'Logistics': 3}
