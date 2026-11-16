"""Cascade revision helpers for the D1 child-parent evidence rule.

THE CASCADE RULE (version 1)

Input: a child decision, its parent decision (value, support, candidates), and the child's readings.
Rule 1: Independent route. Take the readings of tools that do NOT depend on the parent.
        If there are at least 2 and they all agree on a value v, that is the independent value.
Rule 2: Implied parent. implied = distance_from_time(v). If implied equals the parent's value,
        nothing is wrong. Stop.
Rule 3: Revise only if implied is one of the parent's earlier candidates AND candidate_support[implied]
        + number of independent readings is greater than the parent's support.
Rule 4: If revised: the parent's final value is implied, the child's value is v, and the dependent
        tools whose readings ALL equal time_from_distance(old parent value) are excused.
Known limits: a liar who reads the independent tool breaks Rule 1's agreement, so no revision.
A parent that was accepted on the fast path has no rival candidates, so Rule 3 cannot fire.
"""


def time_from_distance(d):
    """In this toy world, time in minutes equals distance in km for the Van at 60 km/h.
    The functions are kept separate so a real-world formula can replace them later.
    """
    return d


def distance_from_time(t):
    """In this toy world, distance in km equals time in minutes for the Van at 60 km/h."""
    return t


def cascade_check(parent, independent_values):
    """Return a revision payload if the independent child readings justify revising the parent."""
    if len(independent_values) < 2 or len(set(independent_values)) != 1:
        return None

    v = independent_values[0]
    implied = distance_from_time(v)

    if implied == parent['value']:
        return None

    if implied not in parent['candidates']:
        return None

    support = parent['candidates'][implied] + len(independent_values)
    if support <= parent['support']:
        return None

    return {'revised_parent': implied, 'value': v, 'support': support}


def excused_tools(claims, dependent_tools, old_parent_value):
    """Return the tools whose readings all equal the old parent time, across every claim."""
    excused = set()
    for tool in dependent_tools:
        readings = []
        for claim in claims:
            for reading in claim['readings']:
                if reading['tool_id'] == tool:
                    readings.append(reading['value'])
        if readings and all(value == time_from_distance(old_parent_value) for value in readings):
            excused.add(tool)
    return excused
