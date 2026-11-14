class Settings:
    def __init__(self, **overrides):
        # Centralized defaults: one place for the shared thresholds and flags.
        self.n_missions = 300
        self.slip_rate = 0.05
        self.n_scattered_poison_keys = 3
        self.min_claims = 10
        self.t_agent = 0.30
        self.t_tool = 0.15
        self.support_needed = 3
        self.audit_rate = 0.0
        self.trust_fast_path = 0.90
        self.slice_flag_after = 2
        self.n_probation = 15
        self.use_cascade_revision = True
        self.use_fact_quarantine = True
        self.use_fast_path = True

        # Reject typos in override names before they silently do nothing.
        for name, value in overrides.items():
            if not hasattr(self, name):
                raise ValueError(f"Unknown setting: {name}")
            setattr(self, name, value)


def load_settings(**overrides):
    # Single entry point for reading settings from the team's shared config later.
    return Settings(**overrides)
