"""Baseline defense: majority vote over the three answers. Sits between the agents and the plan.
Replace with the trust-ledger defense later; keep the same decide(...) contract."""
from collections import Counter


class NoConsensus(Exception):
    pass


class MajorityVoteDefense:
    def decide(self, question, key, claims):
        votes = Counter(c['answer'] for c in claims)
        value, count = votes.most_common(1)[0]
        if count * 2 > len(claims):
            return value
        raise NoConsensus(f'{question} {key}: no majority among {dict(votes)}')
