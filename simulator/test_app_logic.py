from simulator.participants.hospital import get_camp_registry
from simulator.agents.coordinator import AgentCoordinator


def test_registered_camps_are_available():
    names = {camp["name"] for camp in get_camp_registry()}
    assert len(names) >= 5
    assert names >= {"Muyinga Health Centre", "Rutana Refugee Camp", "Cankuzo Clinic",
                     "Bubanza Community Clinic", "Gitega Health Post"}


def test_simulation_picks_cheapest_feasible_option_within_budget():
    result = AgentCoordinator().run_simulation("Malaria Treatment", 50, "Muyinga Health Centre")
    assert result["warehouse"]["decision"] == "Approved"
    assert result["warehouse"]["warehouse_name"] == "Gitega Regional Warehouse"  # W2 is nearest to C1
    assert result["transportation"]["vehicle"] == "Van"


def test_unregistered_clinic_is_rejected():
    result = AgentCoordinator().run_simulation("Malaria Treatment", 50, "Nowhere Camp")
    assert result["warehouse"]["decision"] == "Rejected"
