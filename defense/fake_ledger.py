class FakeLedger:
    """A stand-in for the real ledger. Same functions, but it is just a list."""

    def __init__(self):
        self.entries = []

    def append(self, entry):
        stored = dict(entry)
        stored.setdefault('parent_decision_ids', [])
        stored.setdefault('agreed_with_verdict', None)
        stored.setdefault('audit_correct', None)
        stored.setdefault('excused_by_parent', False)
        stored['entry_id'] = len(self.entries)
        self.entries.append(stored)
        return stored['entry_id']

    def query(self, agent_id):
        return [e for e in self.entries if e['agent_id'] == agent_id]

    def query_decision(self, decision_id):
        return [e for e in self.entries if e['decision_id'] == decision_id]

    def set_outcome(self, entry_id, agreed=None, audit_correct=None, excused=None):
        entry = self.entries[entry_id]
        if agreed is not None:
            entry['agreed_with_verdict'] = agreed
        if audit_correct is not None:
            entry['audit_correct'] = audit_correct
        if excused is not None:
            entry['excused_by_parent'] = excused

    def verify_chain(self):
        return True # the fake never checks anything


    

    