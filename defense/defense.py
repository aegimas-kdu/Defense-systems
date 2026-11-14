import random
from collections import Counter

from defense.blame import question_evidence
from defense.fake_ledger import FakeLedger
from defense.settings import load_settings
from defense.trust import TrustMemory


def plurality(votes, rng):
    if not votes:
        return (None, 0, False)

    top = max(votes.values())
    leaders = sorted(value for value, count in votes.items() if count == top)
    tied = len(leaders) > 1
    value = rng.choice(leaders) if tied else leaders[0]
    return (value, top, tied)


def make_decision(question, key, claims, value, support, tied, candidates):
    mission = claims[0]['mission_id'] if claims else None
    decision_id = f'{mission}:{question}' if mission is not None else f'None:{question}'
    return {
        'decision_id': decision_id,
        'question': question,
        'key': key,
        'value': value,
        'support': support,
        'tied': tied,
        'candidates': dict(candidates),
        'claims': claims,
        'revised_parent': None,
    }


class Defense:
    def __init__(self, settings=None, seed=0):
        self.settings = load_settings() if settings is None else settings
        self.rng = random.Random(f'ties-{seed}')

    def decide(self, question, key, agents, ask, parent=None):
        raise NotImplementedError

    def end_mission(self, decisions):
        pass

    def learn_audit(self, decision_id, true_value):
        pass

    def get_trust(self, entity_id):
        return None

    def is_quarantined(self, entity_id, key=None):
        return False

    def report(self):
        return {'quarantined_agents': set(), 'quarantined_tools': set(), 'flags': set()}


class D4Base(Defense):
    def __init__(self, settings, seed, ledger=None):
        super().__init__(settings=settings, seed=seed)
        self.memory = TrustMemory(settings)
        self.ledger = ledger if ledger is not None else FakeLedger()

    def _usable_votes(self, claims):
        votes = Counter()
        for claim in claims:
            if self.memory.is_quarantined(claim['agent_id']):
                continue
            for reading in claim['readings']:
                if self.memory.is_quarantined(reading['tool_id']):
                    continue
                votes[reading['value']] += 1
        return votes

    def _write_ledger(self, decision, claims, parent):
        parents = [parent['decision_id']] if parent else []
        ids = []
        for claim in claims:
            for reading in claim['readings']:
                entry_id = self.ledger.append({
                    'decision_id': decision['decision_id'],
                    'agent_id': claim['agent_id'],
                    'tool_id': reading['tool_id'],
                    'key': claim['key'],
                    'value': reading['value'],
                    'parent_decision_ids': parents,
                })
                ids.append((entry_id, reading['value']))
        return ids

    def _set_agreement(self, ids, verdict):
        for entry_id, value in ids:
            self.ledger.set_outcome(entry_id, agreed=(value == verdict))

    def decide(self, question, key, agents, ask, parent=None):
        claims = ask(agents)
        votes = self._usable_votes(claims)

        if not votes:
            votes = Counter(r['value'] for c in claims for r in c['readings'])

        value, support, tied = plurality(votes, self.rng)
        decision = make_decision(question, key, claims, value, support, tied, votes)
        ids = self._write_ledger(decision, claims, parent)

        if support >= self.settings.support_needed:
            evidence = question_evidence(claims, value)
            self.memory.record(evidence)
            self._set_agreement(ids, value)

        return decision

    def end_mission(self, decisions):
        pass

    def learn_audit(self, decision_id, true_value):
        pass

    def get_trust(self, entity_id):
        if entity_id in self.memory.agent_seen:
            return self.memory.agent_trust(entity_id)
        if entity_id in self.memory.tool_seen:
            return self.memory.tool_trust(entity_id)
        return 0.5

    def is_quarantined(self, entity_id, key=None):
        return self.memory.is_quarantined(entity_id)

    def report(self):
        return {
            'quarantined_agents': self.memory.quarantined_agents(),
            'quarantined_tools': self.memory.quarantined_tools(),
            'flags': set(),
        }
