from defense.fake_ledger import FakeLedger


def make_entry(agent_id, tool_id, value, decision_id='1:dist', **extra):
    entry = {'decision_id': decision_id, 'agent_id': agent_id, 'tool_id': tool_id,
             'key': ('W1', 'H1'), 'value': value}
    entry.update(extra)
    return entry


def check_ledger(ledger):
    """Works for ANY ledger: the fake now, the real one in Phase E."""
    id_a = ledger.append(make_entry('LA1', 'L1', 120))
    id_b = ledger.append(make_entry('LA2', 'L2', 140))
    id_c = ledger.append(make_entry('TA1', 'T1', 120, decision_id='1:time'))
    assert len({id_a, id_b, id_c}) == 3

    # a fresh entry has the default fields
    fresh = ledger.query('LA1')[0]
    assert fresh['parent_decision_ids'] == []
    assert fresh['agreed_with_verdict'] is None
    assert fresh['audit_correct'] is None
    assert fresh['excused_by_parent'] is False

    # query returns only that agent's entries, and keeps the tool id and value
    assert len(ledger.query('LA1')) == 1
    assert ledger.query('LA1')[0]['tool_id'] == 'L1'
    assert ledger.query('LA2')[0]['value'] == 140
    assert ledger.query('LA3') == []

    # query_decision returns every reading behind a decision
    assert len(ledger.query_decision('1:dist')) == 2
    assert len(ledger.query_decision('1:time')) == 1
    assert ledger.query_decision('9:none') == []

    # the two outcomes are independent
    ledger.set_outcome(id_a, agreed=True)
    entry = ledger.query('LA1')[0]
    assert entry['agreed_with_verdict'] is True
    assert entry['audit_correct'] is None
    ledger.set_outcome(id_a, audit_correct=False)
    entry = ledger.query('LA1')[0]
    assert entry['agreed_with_verdict'] is True
    assert entry['audit_correct'] is False

    # the order does not matter: an audit first, the agreement later
    ledger.set_outcome(id_b, audit_correct=True)
    ledger.set_outcome(id_b, agreed=False)
    entry = ledger.query('LA2')[0]
    assert entry['audit_correct'] is True
    assert entry['agreed_with_verdict'] is False

    # excused only changes the excused field, and other entries are untouched
    ledger.set_outcome(id_c, excused=True)
    assert ledger.query('TA1')[0]['excused_by_parent'] is True
    assert ledger.query('LA2')[0]['agreed_with_verdict'] is False

    # parent ids given by the caller are kept
    ledger.append(make_entry('TA2', 'T2', 120, decision_id='1:time', parent_decision_ids=['1:dist']))
    assert ledger.query('TA2')[0]['parent_decision_ids'] == ['1:dist']

    # the ledger keeps its own copy of what it was given
    original = make_entry('LA3', 'L3', 120)
    ledger.append(original)
    original['value'] = 999
    assert ledger.query('LA3')[0]['value'] == 120

    assert ledger.verify_chain() is True


def test_fake_ledger():
    check_ledger(FakeLedger())