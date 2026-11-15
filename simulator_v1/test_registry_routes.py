from simulator.registry import get_tool_read


def test_route_specific_eta_is_not_stuck_on_first_truck_record():
    read = get_tool_read('T_Agent_3', 'vehicle', warehouse='W2', hospital='C4', vehicle='Truck')
    assert read['time_hours'] == 2.17
    assert read['answer'] == 2.17


def test_route_specific_cost_is_not_stuck_on_first_truck_record():
    read = get_tool_read('L_Agent_3', 'cost', warehouse='W2', hospital='C4', vehicle='Truck')
    assert read['cost'] == 440.0
    assert read['answer'] == 440.0
