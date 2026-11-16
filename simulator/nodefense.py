"""No defense: the Coordinator trusts ONE randomly chosen agent per question and uses its answer as-is.

This is the experimental baseline. It shows what happens when nobody checks the readings.
The choice is seeded, so the same seed + mission + question always picks the same agent
(repeatable, and independent of the order in which questions are asked).
"""
import random


class NoDefense:
    def __init__(self, seed=0):
        self.seed = seed
        self.choices = []  # (mission_id, question, key, chosen agent_id), useful for experiment logs

    def decide(self, question, key, claims):
        mission_id = claims[0]['mission_id']
        rng = random.Random(f'{self.seed}|{mission_id}|{question}|{key}')
        chosen = rng.choice(sorted(claims, key=lambda c: c['agent_id']))
        self.choices.append((mission_id, question, chosen['key'], chosen['agent_id']))
        return chosen['answer']
