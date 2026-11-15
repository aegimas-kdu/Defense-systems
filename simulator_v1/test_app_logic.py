from simulator.app import choose_warehouse_for_order, get_camps, get_medicine_catalog


def test_registered_camps_are_available():
    camps = get_camps()
    assert len(camps) >= 5
    assert {camp["name"] for camp in camps} >= {
        "Muyinga Health Centre",
        "Rutana Refugee Camp",
        "Cankuzo Clinic",
        "Bubanza Community Clinic",
        "Gitega Health Post",
    }


def test_warehouse_selection_favors_nearest_stocked_option_within_budget():
    catalog = get_medicine_catalog()
    medicine = next(m for m in catalog if m["name"] == "Malaria Treatment")
    order = {
        "medicine": medicine,
        "quantity": 50,
        "camp_name": "Muyinga Health Centre",
        "budget_limit": 5000,
    }

    choice = choose_warehouse_for_order(order)
    assert choice["warehouse_name"] in {"Kigali Central Warehouse", "Gitega Regional Warehouse"}
    assert choice["status"] == "approved"
