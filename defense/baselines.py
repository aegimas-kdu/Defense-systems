from collections import Counter

from defense.defense import Defense, make_decision, plurality


class MajorityVote(Defense):
    def decide(self, question, key, agents, ask, parent=None):
        claims = ask(agents)
        votes = Counter(claim['answer'] for claim in claims)
        value, support, tied = plurality(votes, self.rng)
        return make_decision(question, key, claims, value, support, tied, votes)


class ReadingVote(Defense):
    def decide(self, question, key, agents, ask, parent=None):
        claims = ask(agents)
        votes = Counter(reading['value'] for claim in claims for reading in claim['readings'])
        value, support, tied = plurality(votes, self.rng)
        return make_decision(question, key, claims, value, support, tied, votes)
