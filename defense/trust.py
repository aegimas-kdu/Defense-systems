from collections import Counter


class TrustMemory:
    def __init__(self, settings):
        self.settings = settings
        self.agent_seen = Counter()
        self.agent_bad = Counter()
        self.tool_seen = Counter()
        self.tool_wrong = Counter()
        self.q_agents = set()
        self.q_tools = set()

    def record(self, evidence):
        for agent, verdict in evidence.get('agents', {}).items():
            self.agent_seen[agent] += 1
            if verdict == 'bad':
                self.agent_bad[agent] += 1

        for tool, verdict in evidence.get('tools', {}).items():
            self.tool_seen[tool] += 1
            if verdict == 'wrong':
                self.tool_wrong[tool] += 1

        self._update_quarantine()

    def _update_quarantine(self):
        for agent, n in list(self.agent_seen.items()):
            if n >= self.settings.min_claims and self.agent_bad[agent] / n > self.settings.t_agent:
                self.q_agents.add(agent)

        for tool, n in list(self.tool_seen.items()):
            if n >= self.settings.min_claims and self.tool_wrong[tool] / n > self.settings.t_tool:
                self.q_tools.add(tool)

    def agent_trust(self, agent):
        seen = self.agent_seen[agent]
        bad = self.agent_bad[agent]
        return (seen - bad + 1) / (seen + 2) if seen else 0.5

    def tool_trust(self, tool):
        seen = self.tool_seen[tool]
        wrong = self.tool_wrong[tool]
        return (seen - wrong + 1) / (seen + 2) if seen else 0.5

    def is_quarantined(self, entity_id):
        return entity_id in self.q_agents or entity_id in self.q_tools

    def quarantined_agents(self):
        return set(self.q_agents)

    def quarantined_tools(self):
        return set(self.q_tools)
