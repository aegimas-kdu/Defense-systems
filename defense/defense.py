import random
from collections import Counter

from defense.blame import is_right, question_evidence
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
                ids.append((entry_id, reading['value'], reading['tool_id']))
        return ids

    def _set_agreement(self, ids, verdict):
        for entry_id, value, _ in ids:
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
            'flaps': self.memory.flaps,
        }


class D4Plus(D4Base):
    def __init__(self, settings, seed, ledger=None, agent_tools=None, dependent_tools=frozenset()):
        super().__init__(settings=settings, seed=seed, ledger=ledger)
        self.memory = TrustMemory(settings, whole_tool_quarantine=not settings.use_fact_quarantine)
        self.agent_tools = {} if agent_tools is None else dict(agent_tools)
        self.dependent_tools = frozenset(dependent_tools)
        self.pending = {}
        self.revisions = {}
        self.excused = {}

    def _usable_votes(self, claims, key):
        votes = Counter()
        for claim in claims:
            if self.memory.is_quarantined(claim['agent_id']):
                continue
            for reading in claim['readings']:
                if not self.memory.usable_tool(reading['tool_id'], key):
                    continue
                votes[reading['value']] += 1
        return votes

    def _fast_path_candidate(self, key, agents, parent=None):
        if not self.settings.use_fast_path:
            return None

        domain_tools = {tool for agent in agents for tool in self.agent_tools.get(agent, ())}
        if any(not self.memory.usable_tool(tool, key) for tool in domain_tools):
            return None

        candidates = []
        for agent in agents:
            if self.memory.is_quarantined(agent):
                continue
            tools = tuple(self.agent_tools.get(agent, ()))
            if len(tools) < 2:
                continue
            if not all(self.memory.usable_tool(tool, key) for tool in tools):
                continue
            if parent is not None and not any(tool not in self.dependent_tools for tool in tools):
                continue
            candidates.append(agent)

        if not candidates:
            return None

        best = sorted(candidates, key=lambda agent: (-self.get_trust(agent), agent))[0]
        if self.get_trust(best) < self.settings.trust_fast_path:
            return None
        return best

    def _fast_ids_for_agent(self, agent, claims, ids):
        fast_ids = []
        for claim in claims:
            if claim['agent_id'] != agent:
                continue
            for reading in claim['readings']:
                for entry_id, value, tool_id in ids:
                    if tool_id == reading['tool_id'] and value == reading['value']:
                        fast_ids.append(entry_id)
                        break
        return fast_ids

    def decide(self, question, key, agents, ask, parent=None):
        claims = None
        if self.settings.use_fast_path:
            best_agent = self._fast_path_candidate(key, agents, parent=parent)
            if best_agent is not None:
                quarantined = sorted(
                    agent for agent in agents if self.memory.is_quarantined(agent) and agent != best_agent
                )
                selected = [best_agent] + quarantined
                claims = ask(selected)
                best_claim = next(claim for claim in claims if claim['agent_id'] == best_agent)
                values = {reading['value'] for reading in best_claim['readings']}
                if len(values) == 1:
                    value = next(iter(values))
                    decision = make_decision(question, key, claims, value, 2, False, {value: 2})
                    decision['fast'] = True
                    decision['fast_agent'] = best_agent
                    ids = self._write_ledger(decision, claims, parent)
                    fast_ids = self._fast_ids_for_agent(best_agent, claims, ids)
                    self.pending[decision['decision_id']] = {
                        'claims': claims,
                        'ids': ids,
                        'fast': True,
                        'fast_agent': best_agent,
                        'fast_ids': fast_ids,
                    }
                    return decision

                remaining = [agent for agent in agents if agent not in selected]
                if remaining:
                    claims.extend(ask(remaining))

        if claims is None:
            claims = ask(agents)
        votes = self._usable_votes(claims, key)

        if not votes:
            votes = Counter(r['value'] for c in claims for r in c['readings'])

        value, support, tied = plurality(votes, self.rng)
        decision = make_decision(question, key, claims, value, support, tied, votes)
        decision['fast'] = False
        decision['fast_agent'] = None
        ids = self._write_ledger(decision, claims, parent)
        self.pending[decision['decision_id']] = (claims, ids)

        if self.settings.use_cascade_revision and parent is not None:
            independent = []
            for claim in claims:
                if self.memory.is_quarantined(claim['agent_id']):
                    continue
                for reading in claim['readings']:
                    if reading['tool_id'] in self.dependent_tools:
                        continue
                    if not self.memory.usable_tool(reading['tool_id'], key):
                        continue
                    independent.append(reading['value'])

            result = cascade_check(parent, independent)
            if result is not None:
                decision['value'] = result['value']
                decision['support'] = result['support']
                decision['tied'] = False
                decision['revised_parent'] = result['revised_parent']
                self.revisions[parent['decision_id']] = result['revised_parent']
                self.excused[decision['decision_id']] = excused_tools(
                    claims, self.dependent_tools, parent['value']
                )

        return decision

    def end_mission(self, decisions):
        for decision in decisions:
            decision_id = decision['decision_id']
            pending = self.pending.pop(decision_id, None)
            if isinstance(pending, dict):
                claims = pending.get('claims', decision['claims'])
                ids = pending.get('ids', [])
                fast = pending.get('fast', decision.get('fast', False))
                fast_agent = pending.get('fast_agent')
                fast_ids = pending.get('fast_ids', [])
            elif pending is not None:
                claims, ids = pending
                fast = False
                fast_agent = None
                fast_ids = []
            else:
                claims = decision['claims']
                ids = []
                fast = decision.get('fast', False)
                fast_agent = decision.get('fast_agent')
                fast_ids = []

            verdict = self.revisions.get(decision_id, decision['value'])
            excused = self.excused.get(decision_id, frozenset())

            if fast:
                evidence = {'agents': {fast_agent: 'good'}, 'tools': {}}
                self.memory.record(evidence, key=decision['key'])
                for entry_id in fast_ids:
                    self.ledger.set_outcome(entry_id, agreed=True)
                for claim in claims:
                    if claim['agent_id'] in self.memory.q_agents and claim['agent_id'] != fast_agent:
                        good = any(reading['value'] == verdict for reading in claim['readings'])
                        self.memory.observe_agent(claim['agent_id'], good)
                continue

            learn = decision['support'] >= self.settings.support_needed or decision_id in self.revisions
            if learn:
                evidence = question_evidence(claims, verdict, excused)
                self.memory.record(evidence, key=decision['key'])
                for entry_id, value, tool_id in ids:
                    self.ledger.set_outcome(
                        entry_id,
                        agreed=(value == verdict),
                        excused=(tool_id in excused),
                    )

                for claim in claims:
                    if claim['agent_id'] in self.memory.q_agents:
                        good = any(is_right(reading, verdict, excused) for reading in claim['readings'])
                        self.memory.observe_agent(claim['agent_id'], good)

                    for reading in claim['readings']:
                        if not self.memory.usable_tool(reading['tool_id'], decision['key']):
                            good = reading['value'] == verdict
                            self.memory.observe_tool_reading(reading['tool_id'], decision['key'], good)

        self.pending.clear()
        self.revisions.clear()
        self.excused.clear()

    def report(self):
        flags_on = self.settings.use_fact_quarantine
        return {
            'quarantined_agents': self.memory.quarantined_agents(),
            'quarantined_tools': set() if flags_on else self.memory.quarantined_tools(),
            'flags': self.memory.flags() if flags_on else set(),
            'flaps': self.memory.flaps,
        }


from defense.cascade import cascade_check, excused_tools
