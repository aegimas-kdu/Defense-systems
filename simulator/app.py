
import pandas as pd
import streamlit as st

try:
    from simulator.registry import get_agent_registry, get_tool_registry, QUESTIONS
    from simulator.participants.hospital import get_camp_registry
    from simulator.agents.coordinator import AgentCoordinator
except ModuleNotFoundError:  # pragma: no cover
    from registry import get_agent_registry, get_tool_registry, QUESTIONS
    from participants.hospital import get_camp_registry
    from agents.coordinator import AgentCoordinator


MEDICINE_CATALOG = [
    {"name": "Malaria Treatment", "category": "medicine"},
    {"name": "Tuberculosis Treatment", "category": "medicine"},
    {"name": "Kwashiorkor Nutrition Support", "category": "nutrition"},
    {"name": "Paracetamol", "category": "medicine"},
    {"name": "Antibiotics", "category": "medicine"},
]


def get_camps():
    return get_camp_registry()


def get_medicine_catalog():
    return MEDICINE_CATALOG


def get_tools():
    return get_tool_registry()


def get_agents():
    return get_agent_registry()


st.set_page_config(
    page_title='Burundi Humanitarian Logistics',
    page_icon='🏥',
    layout='wide',
)

st.markdown(
    """
    <style>
    .main .block-container { padding-top: 1rem; }
    div[data-testid="stForm"] { background: linear-gradient(135deg, #16a34a 0%, #22c55e 100%); border-radius: 20px; padding: 2rem; box-shadow: 0 8px 20px rgba(22, 163, 74, 0.18); }
    div[data-testid="stForm"] label, div[data-testid="stForm"] .st-emotion-cache-10trblm { color: white !important; }
    div[data-testid="stForm"] .stButton > button { background: #14532d; color: white; border: none; border-radius: 12px; height: 3rem; font-weight: 700; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title('🏥 Burundi Humanitarian Relief')
st.caption('Submit a medical supply request for a registered clinic or refugee camp.')

st.markdown('<div>', unsafe_allow_html=True)
with st.form('relief_request_form', clear_on_submit=False):
    st.markdown('<h3 style="color: white; margin: 0 0 1rem;">Submit a relief request</h3>', unsafe_allow_html=True)
    camp_names = [camp['name'] for camp in get_camps()]
    medicine_names = [item['name'] for item in MEDICINE_CATALOG]

    camp_name = st.selectbox('Clinic or camp', camp_names, key='camp_name_form')
    medicine_name = st.selectbox('Item requested', medicine_names, key='medicine_name_form')
    quantity = st.number_input('Quantity', min_value=1, value=50, step=10, key='quantity_form')
    submit = st.form_submit_button('Process request', use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

if submit:
    coordinator = AgentCoordinator()
    result = coordinator.run_simulation(medicine_name=medicine_name, quantity=quantity, camp_name=camp_name)

    if result['warehouse']['decision'] == 'Approved' and result['transportation']['decision'] == 'Approved':
        delivery_hours = float(result['transportation']['delivery_time_hours'])

        st.markdown(
            f"""
            <div style="background: #f0fdf4; border-left: 8px solid #16a34a; border-radius: 14px; padding: 1.25rem; margin: 1rem 0 1.5rem;">
            <div style="font-size: 0.9rem; color: #166534; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em;">Order approved</div>
            <div style="font-size: 2rem; color: #166534; font-weight: 700; margin-top: 0.3rem;">{medicine_name}</div>
            <div style="font-size: 1.2rem; color: #14532d; margin-top: 0.35rem;">Expected delivery in {delivery_hours:.2f} hours</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col1, col2, col3 = st.columns(3)
        col1.metric('Clinic', camp_name)
        col2.metric('Warehouse', result['warehouse']['warehouse_name'])
        col3.metric('Vehicle', result['transportation']['vehicle'])

        col4, col5, col6 = st.columns(3)
        col4.metric('Distance', f"{result['transportation']['distance_km']} km")
        col5.metric('ETA', f"{result['transportation']['delivery_time_hours']} hrs")
        col6.metric('Cost', f"${result['transportation']['transportation_cost']:,.0f}")
    else:
        st.warning(result['warehouse'].get('reason') or result['transportation'].get('reason') or 'Request could not be fulfilled.')

    with st.expander('Technical details', expanded=False):
        st.markdown('### Operation result')
        st.write(result['warehouse'])
        st.write(result['transportation'])

        if result.get('agents'):
            st.markdown('### Agent readings')
            st.caption('All three agents of a domain answer the same question. Each claim shows the answer '
                       '(primary tool) and both tool readings.')
            rows = []
            for c in result['agents']:
                spec = QUESTIONS[c['question']]
                primary, backup = c['readings']
                rows.append({
                    'Question': f"{c['question']} {spec['name']} ({spec['unit']})",
                    'Key': ' / '.join(c['key']),
                    'Agent': c['agent_id'],
                    'Answer': c['answer'],
                    'Primary tool': f"{primary['tool_id']} = {primary['value']}",
                    'Backup tool': f"{backup['tool_id']} = {backup['value']}",
                    'Routes agree': primary['value'] == backup['value'],
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        st.markdown('### Decision log')
        for log in result.get('logs', []):
            st.write('•', log)

st.caption('Prototype scope: no login, registered refugee camps, and internal route and cost calculations handled by the system.')
