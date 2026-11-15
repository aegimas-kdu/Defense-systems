
CLINIC_REGISTRY = [
    {
        "camp_id": "C1",
        "name": "Muyinga Health Centre",
        "location": {"latitude": -2.8470, "longitude": 30.3278},
        "region": "Muyinga",
    },
    {
        "camp_id": "C2",
        "name": "Rutana Refugee Camp",
        "location": {"latitude": -3.9271, "longitude": 30.1189},
        "region": "Rutana",
    },
    {
        "camp_id": "C3",
        "name": "Cankuzo Clinic",
        "location": {"latitude": -3.2145, "longitude": 30.5411},
        "region": "Cankuzo",
    },
    {
        "camp_id": "C4",
        "name": "Bubanza Community Clinic",
        "location": {"latitude": -3.0831, "longitude": 29.3956},
        "region": "Bubanza",
    },
    {
        "camp_id": "C5",
        "name": "Gitega Health Post",
        "location": {"latitude": -3.4286, "longitude": 29.9253},
        "region": "Gitega",
    },
    {
        "camp_id": "C6",
        "name": "Ngozi Primary Care Centre",
        "location": {"latitude": -2.9089, "longitude": 29.8273},
        "region": "Ngozi",
    },
]


def get_camp_registry():
    return CLINIC_REGISTRY


def find_camp(camp_name):
    for camp in CLINIC_REGISTRY:
        if camp["name"].lower() == camp_name.lower():
            return camp
    return None


def get_hospital_needs():
    return [{"medicine_name": "Malaria Treatment", "required_quantity": 50}, {"medicine_name": "Tuberculosis Treatment", "required_quantity": 20}, {"medicine_name": "Kwashiorkor Nutrition Support", "required_quantity": 30}, {"medicine_name": "Paracetamol", "required_quantity": 120}, {"medicine_name": "Antibiotics", "required_quantity": 80}]


def check_hospital_need(medicine_name):
    needs = get_hospital_needs()
    for medicine in needs:
        if medicine["medicine_name"].lower() == medicine_name.lower():
            return medicine
    return None
