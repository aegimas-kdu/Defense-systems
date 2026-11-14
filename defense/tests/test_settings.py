import pytest

from defense.settings import Settings, load_settings


def test_defaults_are_right():
    settings = Settings()

    assert settings.n_missions == 300
    assert settings.slip_rate == 0.05
    assert settings.n_scattered_poison_keys == 3
    assert settings.min_claims == 10
    assert settings.t_agent == 0.3
    assert settings.t_tool == 15 / 100
    assert settings.support_needed == 3
    assert settings.audit_rate == 0.0
    assert settings.trust_fast_path == 0.90
    assert settings.slice_flag_after == 2
    assert settings.n_probation == 15
    assert settings.use_cascade_revision is True
    assert settings.use_fact_quarantine is True
    assert settings.use_fast_path is True


def test_override_changes_value():
    settings = Settings(min_claims=20)

    assert settings.min_claims == 20


def test_unknown_name_raises_value_error():
    with pytest.raises(ValueError, match='t_agnet'):
        Settings(t_agnet=0.5)


def test_changing_one_object_does_not_change_another():
    a = Settings()
    b = Settings()

    a.min_claims = 42

    assert a.min_claims == 42
    assert b.min_claims == 10
