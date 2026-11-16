from collections import Counter


class TrustMemory:
    def __init__(self, settings, whole_tool_quarantine=True):
        self.settings = settings
        self.whole_tool_quarantine = whole_tool_quarantine
        self.agent_seen = Counter()
        self.agent_bad = Counter()
        self.tool_seen = Counter()
        self.tool_wrong = Counter()
        self.q_agents = set()
        self.q_tools = set()
        self.fact_flags = set()
        # Each warehouse is key[0], so a slice flag is for all keys in one warehouse.
        self.flagged_by_slice = {}
        self.streak = Counter()
        self.released = set()
        self.flaps = 0

    def flag_fact(self, tool, key):
        self.fact_flags.add((tool, key))
        warehouse = key[0]
        self.flagged_by_slice.setdefault((tool, warehouse), set()).add(key)

    def unflag_fact(self, tool, key):
        self.fact_flags.discard((tool, key))
        warehouse = key[0]
        bucket = self.flagged_by_slice.get((tool, warehouse))
        if bucket is None:
            return
        bucket.discard(key)
        if not bucket:
            self.flagged_by_slice.pop((tool, warehouse), None)

    def slice_flagged(self, tool, warehouse):
        return len(self.flagged_by_slice.get((tool, warehouse), set())) >= self.settings.slice_flag_after

    def usable_tool(self, tool, key):
        if self.whole_tool_quarantine and tool in self.q_tools:
            return False
        if key is not None and (tool, key) in self.fact_flags:
            return False
        if key is not None and self.slice_flagged(tool, key[0]):
            return False
        return True

    def flags(self):
        out = set()
        for tool, key in self.fact_flags:
            out.add(('fact', tool, key))
        for (tool, warehouse), keys in self.flagged_by_slice.items():
            if len(keys) >= self.settings.slice_flag_after:
                out.add(('slice', tool, warehouse))
        return out

    def observe_agent(self, agent, good):
        if agent not in self.q_agents:
            return
        if good:
            self.streak[agent] += 1
            if self.streak[agent] >= self.settings.n_probation:
                self.release_agent(agent)
        else:
            self.streak[agent] = 0

    def release_agent(self, agent):
        if agent in self.q_agents:
            self.q_agents.remove(agent)
            self.agent_seen[agent] = 0
            self.agent_bad[agent] = 0
            self.streak[agent] = 0
            self.released.add(agent)

    def observe_tool_reading(self, tool, key, good):
        if self.usable_tool(tool, key):
            return
        if good:
            self.streak[tool] += 1
            if self.streak[tool] >= self.settings.n_probation:
                for flagged_tool, flagged_key in list(self.fact_flags):
                    if flagged_tool == tool:
                        self.unflag_fact(flagged_tool, flagged_key)
                self.streak[tool] = 0
        else:
            self.streak[tool] = 0

    def record(self, evidence, key=None):
        for agent, verdict in evidence.get('agents', {}).items():
            self.agent_seen[agent] += 1
            if verdict == 'bad':
                self.agent_bad[agent] += 1

        for tool, verdict in evidence.get('tools', {}).items():
            self.tool_seen[tool] += 1
            if verdict == 'wrong':
                self.tool_wrong[tool] += 1

        if not self.whole_tool_quarantine and key is not None:
            for tool, verdict in evidence.get('tools', {}).items():
                if verdict == 'wrong':
                    self.flag_fact(tool, key)

        self._update_quarantine()

    def _update_quarantine(self):
        for agent, n in list(self.agent_seen.items()):
            if n >= self.settings.min_claims and self.agent_bad[agent] / n > self.settings.t_agent:
                if agent in self.released:
                    self.flaps += 1
                self.q_agents.add(agent)

        if self.whole_tool_quarantine:
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
