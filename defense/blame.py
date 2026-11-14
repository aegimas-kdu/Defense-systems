"""Pure evidence rules for assigning blame to agents and tools on one question.

The underlying rule is intentionally conservative: an agent is bad only when both of
its readings are wrong, unless those wrong readings are explained by their tools'
agreed values. This keeps honest agents from being blamed for single slips while still
catching the liar pattern.
"""


def tool_agreed_values(claims):
    """Return the agreed value for each tool seen in the question, or None if no stable agreement exists."""
    by_tool = {}
    for claim in claims:
        for reading in claim['readings']:
            by_tool.setdefault(reading['tool_id'], []).append(reading['value'])

    agreed = {}
    for tool, values in by_tool.items():
        if len(values) >= 2 and len(set(values)) == 1:
            agreed[tool] = values[0]
        else:
            agreed[tool] = None
    return agreed


def is_right(reading, verdict, excused):
    """A reading is right if it matches the verdict or its tool is excused."""
    return reading['value'] == verdict or reading['tool_id'] in excused


def question_evidence(claims, verdict, excused=frozenset()):
    """Return evidence for one question as {'agents': ..., 'tools': ...}."""
    if verdict is None:
        return {'agents': {}, 'tools': {}}

    agreed = tool_agreed_values(claims)

    tools = {}
    for tool, value in agreed.items():
        if value is None or tool in excused:
            continue
        tools[tool] = 'right' if value == verdict else 'wrong'

    agents = {}
    for claim in claims:
        wrong = [not is_right(r, verdict, excused) for r in claim['readings']]
        explained = [
            agreed[r['tool_id']] is not None and agreed[r['tool_id']] == r['value']
            for r in claim['readings']
        ]
        bad = all(wrong) and not all(explained)
        agents[claim['agent_id']] = 'bad' if bad else 'good'

    return {'agents': agents, 'tools': tools}
