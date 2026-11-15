# **Simulator Audit and Correction Guide** 

Project: Trust-Ledgered Resilience of Multi-Agent AI Systems Against Combined Byzantine and ToolPoisoning Attacks 

For: Ted and Bessie (simulator), with Crispin, John and Precieuse. This guide checks the built simulator against the structure the team approved (Defense System Structure v2 and the Data Spec), explains why the agents return different readings, and gives the steps to correct everything. 

**How I checked.** I rebuilt the package from the uploaded files ( <mark>registry.py</mark> , <mark>coordinator.py</mark> , <mark>app.py</mark> , <mark>agents.json</mark> , the nine tool files, and the participants files) and ran it. My run **reproduced your screenshot exactly** (Warehouse 40, Transportation 2.62, 2.39 and 2.33, Logistics 1.83, 156 and 500). Everything below comes from that run or from reading the code. **Files I did not have:** the <mark>participants</mark> and <mark>agents __init__</mark> files, the exact folder layout, and any attack, defense or evaluator code, if it exists. If something is missing from my picture, tell me. 

## **1. The verdict in short** 

- **The skeleton matches.** There are 3 domains, 9 agents and 9 tools, and <mark>agents.json</mark> has exactly the agreed primary and backup triangle in all three domains. 

- **The rest does not match yet.** The questions are not asked the agreed way, the tool data are not keyed or derived the agreed way, the three routes disagree even in a clean world, two lookup bugs return the wrong records, and the readings are not connected to the plan. 

- **So the readings differ for concrete, fixable reasons** (Section 4), not because of randomness or attacks. 

- **No attack or defense can affect the outcome today,** because the plan is built from <mark>warehouse.py</mark> and the agent readings are only displayed. 

## **2. What matches the approved structure** 

- Three domains with three agents each, and nine tools with the agreed names. 

- **The triangle in** **<mark>agents.json</mark> :** Agent 1 reads tool 1 then tool 3, Agent 2 reads tool 2 then tool 1, Agent 3 reads tool 3 then tool 2, with the tools numbered as in the Data Spec. This is correct for Warehouse, Transportation and Logistics. 

- Every agent has a primary and a backup tool, and <mark>test_structure.py</mark> checks the counts and the domains. 

- The Warehouse data for W2 and W3 are consistent across the three tools (64 and 40). 

- The team ran the system end to end and has a working interface, which is a good base. 

## **3. What does not match, with severity** 

|#|Approved rule|What the code does|Severity|
|---|---|---|---|
|1|All 3 agents of a|Logistics Agent 1 answers distance, Agents 2 and 3|High|
||domain answer the|answer cost(<br>endswith('_1')in<br>coordinator.py)||



|#|Approved rule|What the code does|Severity|
|---|---|---|---|
||**same**question|||
|2|Five questions,<br>including capacity|No capacity question is ever asked. The time<br>question is named<br>vehicle|High|
|3|Three independent<br>routes per question|Capacity has one route (fleet only). Distance has<br>one route (GIS only)|High|
|4|In a clean world, the<br>three routes are<br>exactly equal|Stock W1: 50, 52, 50. Time W3: 2.62, 2.39, 2.33 h.<br>Cost W3: 121, 156, 500|High|
|5|A tool is read for the<br>**requested key**|The match uses<br>or, so the first record wins: ETA and<br>billing always return W1's value|High, a bug|
|6|The backup reading<br>is for the same key|Backups use<br>records[0], so they are always for W1<br>or the first vehicle|High, a bug|
|7|No hidden coupling<br>between tools|Time and cost call<br>_distance_for_route(the GIS<br>tool) and use a constant rate of 1.1 written in the<br>code|High|
|8|Whole numbers and<br>one unit per<br>question|Values rounded to 2 decimals, time in hours (the<br>design says minutes), and a distance read carries a<br>made-up<br>time_hoursof km divided by 60|Medium|
|9|No silent fallbacks|fallback_valueis returned when no record matches.<br>Asking Logistics Agent 2 for a distance returns 420<br>(a cost number), and Agent 3 returns 0|High|
|10|A claim has the<br>answer and**two**<br>**readings**with tool<br>ids and values|A read has<br>answer,<br>backup_answer, and separate<br>quantity,<br>time_hours,<br>costfields. No<br>readings,<br>question,<br>keyor<br>mission_id|Medium|
|11|The Coordinator<br>resolves the<br>distance, then<br>passes it to<br>Transportation|Transportation agents read the GIS tool themselves|High|
|12|The defense sits<br>between the agents<br>and the plan|Readings are collected only for display. The plan<br>comes from<br>warehouse.py(haversine distance,<br>handling fee, fleet speeds)|High|
|13|A hidden ground<br>truth, graded by an|There is no separate truth. The decision logic acts as<br>the truth|High|



|#|Approved rule|What the code does|Severity|
|---|---|---|---|
||evaluator|||
|14|Truth and tools<br>come from one<br>world|Two worlds:<br>warehouse.py(5 medicines, real<br>coordinates) and the tool files (kit K1, hospital C2,<br>distances 120, 90, 110)|High|
|15|Keys: warehouse,<br>hospital, vehicle|The hospital is always C2 and the six camps are<br>ignored. The kit is always K1. An unknown<br>warehouse maps to W1|Medium|
|16|Seeds, a liar, poison,<br>slips|Not present yet|Expected, listed<br>for<br>completeness|
|17|A clean repository|__innit__.pytypo.<br>.gitignore.txtand<br>requirements.txt.txt.<br>medical_supply.dbis<br>committed although<br>*.dbis ignored.<br>database.py,<br>transport.py,<br>agent_test.pyand<br>agents_test.py<br>belong to an older design, and<br>run_simulation(...,<br>distance=50)fails now|Low|



## **4. Why the agents return different readings** 

This is your screenshot, explained. The request selected W3 (Bujumbura Supply Hub), a Truck, and the data in the tool files. 

|Agent|Reading|What it really is|Why it differs|
|---|---|---|---|
|W_Agent_1<br>(inventory)|40|W3 stock|Correct|
|W_Agent_2 (IoT)|40|200 kg divided by 5|Correct for W3 (W1 would give 52, not<br>50)|
|W_Agent_3 (logs)|40|60 minus 20|Correct|
|T_Agent_1 (fleet)|2.62 h|110 km divided by 42<br>km/h|The transport agent read the**GIS**<br>**distance**by itself|
|T_Agent_2 (GPS)|2.39 h|110 divided by 48,<br>plus 6 minutes|Different speed and a delay, so a<br>different formula|
|T_Agent_3 (ETA)|2.33 h|140 minutes|**Bug 5:**that is W1's record. W3's is 130<br>minutes, which is 2.17 h|
|L_Agent_1 (GIS)|110 and<br>time_hours|The distance, and 110<br>divided by 60|The 1.83 is invented, and does not<br>belong in a distance read|



|Agent|Reading|What it really is|Why it differs|
|---|---|---|---|
||1.83|||
|L_Agent_2 (fuel)|156|110 times 1.1, plus a<br>35 toll|Another question (cost), and a distance<br>borrowed from the GIS tool|
|L_Agent_3<br>(billing)|500|W1's quote|**Bug 5:**W3's quote is 480|



The causes, from most to least important: 

1. **The agents are not asked the same question.** Logistics splits into distance and cost, so the answers cannot be compared. 

2. **The tool data are not generated from one truth.** The fleet speed (42), the GPS speed (48 plus a delay) and the ETA (130 minutes) describe three different trips, so they cannot agree. 

3. **The first-record bug (Bug 5).** The match is <mark>matches_route or matches_vehicle</mark> . Every record is a Truck, so the first record always matches. I confirmed it: asking for W1, W2 and W3 returns 500 for billing and 2.33 h for the ETA every time. 

4. **The backup bug (Bug 6).** The backup reading is taken from <mark>records[0]</mark> . For W3 stock, the three backups show 50, 50 and 52, but the true stock is 40. The Transportation backups show 2.33, 2.20 and 2.61 for the same reason (W1's ETA record, the Van, and vehicle V1). 

5. **Missing fields replaced by constants.** The GIS tool has no <mark>base_rate_per_km</mark> , so the code uses 1.1. The fuel tool has no efficiency or fuel price, so the code multiplies a distance it borrows from GIS. 

6. **A data error.** The IoT record for W1 says 260 kg at 5 kg per kit, which is 52. The other two tools say 50. 

7. **Rounding and units.** Everything is rounded to 2 decimals and time is in hours, so exact equality cannot hold. 

**What a clean world should give for W3, Truck, using the team's own distances** (the corrected values are in Section 7): stock 40, capacity 400, distance 110, time 157 minutes, cost 440. All three routes for each question return the same number. 

## **5. What each agent should return** 

**One question at a time, all three agents of the domain answer it. Each claim holds the agent's answer (its primary reading) and both readings, already in the answer's unit.** 

|Question|Domain|Agent 1 reads|Agent 2 reads|Agent 3 reads|Unit|
|---|---|---|---|---|---|
|Q1 Stock|Warehouse|inventory, logs|sensors,<br>inventory|logs, sensors|kits|
|Q2 Capacity|Transportation|fleet, ETA|GPS, fleet|ETA, GPS|kits|
|Q3 Distance|Logistics|GIS, billing|fuel, GIS|billing, fuel|km|
|Q4 Time|Transportation|fleet, ETA|GPS, fleet|ETA, GPS|minutes|



|Question|Domain|Agent 1 reads|Agent 2 reads|Agent 3 reads|Unit|
|---|---|---|---|---|---|
|Q5 Cost|Logistics|GIS, billing|fuel, GIS|billing, fuel|cost units|



Order per mission: Q1, Q2, Q3, then Q4 (which receives the resolved distance from Q3), then Q5. 

#### **The claim format (matches the interface the defense expects):** 

{'mission_id': 17, 'question': 'Q4', 'key': ['W3', 'C2', 'Truck'], 'agent_id': 'T_Agent_1', 'domain': 'Transportation', 'answer': 157, 'readings': [ {'tool_id': 'fleet_specs_catalog', 'value': 157}, {'tool_id': 'route_eta_calculator', 'value': 157}], 'inputs': {'resolved_distance_km': 110}} **Where the built version differs:** it returns <mark>answer</mark> , <mark>backup_answer</mark> and loose <mark>quantity</mark> , <mark>time_hours</mark> and <mark>cost</mark> fields, and no <mark>question</mark> , <mark>key</mark> or <mark>readings</mark> . The defense needs the structure above, so the adapter in Phase E would otherwise have to guess. 

## **6. The correction plan** 

Do the phases in this order. The hours are my rough estimates, for the whole team together (about 22 to 25 hours in total). 

### **Phase 1: Stop the wrong readings (about 3 to 4 hours, do this first)** 

These fixes are small, and until they are done every other reading is misleading. 

#### **Step 1.1. Fix the lookup (Bug 5).** 

- In <mark>get_tool_read</mark> , a record must match on **all** the key fields of the question, joined with <mark>and</mark> , never or. The key fields are: stock (warehouse, kit), capacity (vehicle), distance (warehouse, hospital), time (warehouse, hospital, vehicle for the ETA tool; vehicle for the fleet and GPS tools), cost (warehouse, hospital, vehicle). 

- If no record matches, **raise an error** . Do not return a default. 

- **Done when:** asking for W1, W2 and W3 returns three different ETA and billing values, equal to what the files hold. 

#### **Step 1.2. Fix the backup reading (Bug 6).** 

- Take the backup reading with the **same lookup function and the same key** as the primary reading. Never use <mark>records[0]</mark> . 

- Return it as a second reading, with the backup tool's id and value. 

- **Done when:** the backup readings for W3 stock show 40, not 50 or 52. 

#### **Step 1.3. Remove the silent fallbacks and the hidden constants.** 

- Delete every <mark>fallback_value</mark> (in the tool files and in <mark>registry.py</mark> ), the constant rate <mark>1.1</mark> in the GIS cost derivation, and the <mark>/ 60.0</mark> that turns a distance into <mark>time_hours</mark> . 

- A missing field is an error to fix in the data, not a number to invent. 

- **Done when:** a search finds none of them, and asking a tool for a question it cannot answer raises a clear error (today, asking Logistics Agent 2 for a distance returns 420). 

#### **Step 1.4. Ask the same question to all three agents.** 

- Remove the <mark>endswith('_1')</mark> logic in <mark>collect_agent_reads</mark> . Loop over the five questions, and send each one to all three agents of its domain. 

- **Done when:** the distance question returns three claims, and so does the cost question. 

### **Phase 2: One truth, with the tools generated from it** 

**Step 2.1. Choose one world.** Today there are two: <mark>warehouse.py</mark> (five medicines, real coordinates, distances measured by haversine) and the tool files (kit K1, hospital C2, distances 120, 90 and 110). Choose one source for the distances, delete the other, and put the truth in one module (a truth table for each warehouse, hospital and vehicle: stock, capacity, distance, time, cost). The evaluator reads this table, and the defense never does. 

**Step 2.2. Generate the tool files from the truth.** Write a small script that derives every raw field of every tool from the truth, using the formulas in Section 7, and writes the nine JSON files. Stop editing the tool files by hand. This is what keeps the three routes equal. 

**Step 2.3. Fix the fields of each tool.** 

|Tool|Add|Remove or change|
|---|---|---|
|warehouse_inventory_db|more kit types if wanted|nothing|
|shelf_iot_sensors|nothing|remove<br>physical_count(a stored<br>answer). Fix W1: 250 kg, not 260|
|inbound_outbound_logs|nothing|remove<br>remaining_stock(a stored<br>answer), so the stock is computed from<br>the raw fields|
|fleet_specs_catalog|nothing|keep|
|live_gps_telemetry|vehicle_type,<br>max_payload_kg,<br>kit_unit_weight_kg|in the clean world,<br>live_speed_kmh<br>equals the average speed and<br>traffic_delay_minutesis 0|
|route_eta_calculator|cargo_bay_volume_l,<br>kit_box_volume_l, rows for<br>all vehicle types|store<br>estimated_minutesas a whole<br>number|
|gis_distance_matrix|base_rate_per_kmper<br>vehicle|rename to<br>map_distance_km.<br>road_typecan go|
|fuel_and_toll_rates|vehicle_km_per_liter,<br>fuel_price_per_liter|make<br>expected_fuel_litersand<br>toll_fee<br>per route (warehouse, hospital,<br>vehicle). Remove the duplicate fields|



|Tool|Add|Remove or change|
|---|---|---|
|billing_quote_api|billed_mileage_km, rows|drop<br>base_dispatch_fee, or add the|
||for all vehicle types|same fee to all three cost routes|



**Step 2.4. Prove the world is consistent.** Write the consistency test of Section 8. **Done when:** for every question and key, the three routes return exactly the same number. 

### **Phase 3: Rewrite the reading logic in** **<mark>registry.py</mark>** 

**Step 3.1. One derivation function for each question and tool.** Keep a table, for example <mark>DERIVE[('time', 'route_eta_calculator')]</mark> , that points to a small function. The function takes the tool's record and the inputs, and returns a **whole number in the answer's unit** . There are 15 of them (5 questions times 3 routes), and Section 5 and Section 7 give the formulas. 

**Step 3.2. Replace** **<mark>get_tool_read</mark> with one function that returns the agreed claim** (Section 5): <mark>mission_id</mark> , <mark>question</mark> , <mark>key</mark> , <mark>agent_id</mark> , <mark>domain</mark> , <mark>answer</mark> (the primary reading), <mark>readings</mark> (two entries with <mark>tool_id</mark> and <mark>value</mark> ), and <mark>inputs</mark> . No <mark>quantity</mark> , <mark>time_hours</mark> or <mark>cost</mark> fields. No rounding to decimals. 

**Step 3.3. No tool reads another tool.** The time derivations use <mark>resolved_distance_km</mark> from the inputs. The cost route of the GIS tool uses the GIS tool's own distance. Delete <mark>_distance_for_route</mark> , because it creates hidden dependencies: today, poisoning the GIS tool silently changes the fleet, GPS and fuel readings too. 

**Step 3.4. Load the tool files once** and keep them in memory, instead of reading nine files every time an agent asks. 

**Done when:** the tests of Section 8 pass. 

### **Phase 4: Rewrite the Coordinator** 

**Step 4.1. The five questions, in order.** Q1 stock, Q2 capacity, Q3 distance, then Q4 time (the Coordinator passes the resolved distance to the Transportation agents), then Q5 cost. Each question goes to all three agents of its domain. 

**Step 4.2. Remove the hard-coded keys.** The hospital is always <mark>'C2'</mark> , the kit is always K1, and an unknown warehouse falls back to <mark>'W1'</mark> . Either map the six camps to hospital ids with tool rows for each, or reduce the demo to the camps that have data. Either map the five medicines to kit types, or take medicine names out of the agent layer. 

**Step 4.3. Decide, then plan.** The Coordinator receives decided values from a defense object, <mark>decide(question, key, agents, ask, parent)</mark> , and builds the plan from those values. It must not read <mark>warehouse.py</mark> for stock, distance, time or cost any more. **Test:** feed the Coordinator a wrong decision, and the plan must change. 

**Step 4.4. Choose the vehicle from the capacity answer (Q2),** not from <mark>warehouse['feet'][0]</mark> l . 

**Step 4.5. A headless mission function.** Create <mark>run_mission(world, defense, mission)</mark> that works without Streamlit. The Streamlit page calls the same function, so the experiments and the demo run the same code. 

### **Phase 5: Evaluator, attacks and the defense hook** 

- **Evaluator (John, with Ted):** holds the truth, compares each decision with it, computes mission success, and counts tool calls. 

- **Seeds and noise (Ted):** precompute the slips and lies for every mission, question, agent and reading, so every defense faces the same noise. 

- **Attack switches (Crispin):** a liar (an agent id), a poisoned tool, and the poison keys (scattered or aligned), applied in the world and never inside the agents. 

- **Baseline defenses (Precieuse):** majority vote over answers and over readings, so the app works with no attack. 

- **The hook:** <mark>ask(agent_ids)</mark> returns the claims and counts 2 tool calls per agent. 

### **Phase 6: Repository cleanup (about 1 hour)** 

- Rename <mark>__innit__.py</mark> to <mark>__init__.py</mark> , and remove the duplicate <mark>__init___13da57.py</mark> . 

- Rename <mark>.gitignore.txt</mark> to <mark>.gitignore</mark> and <mark>requirements.txt.txt</mark> to <mark>requirements.txt</mark> (add <mark>pytest</mark> ). 

- • <mark>medical_supply.db</mark> is committed although <mark>*.db</mark> is ignored: run <mark>git rm --cached medical_supply.db</mark> . 

- Move <mark>database.py</mark> , <mark>transport.py</mark> , <mark>agent_test.py</mark> and <mark>agents_test.py</mark> to a <mark>legacy/</mark> folder, or delete them. The two test scripts call <mark>run_simulation(..., distance=50)</mark> , which no longer exists. 

- Check that <mark>test_app_logic.py</mark> and <mark>test_structure.py</mark> still pass after the changes. 

## **7. Corrected data for your current keys (verified)** 

I built a consistent dataset from your own numbers (distances 120, 90 and 110 km, your vehicle speeds and capacities), and checked that **every route agrees exactly for all 9 combinations of warehouse and vehicle** . 

#### **The rules** 

- **Minutes** are <mark>round(distance times 60 divided by speed)</mark> , used in every time route, including the ETA tool. In the clean world, the GPS live speed equals the average speed and the delay is 0. 

- • **Liters** are <mark>distance divided by km per liter</mark> . Your distances are multiples of 10, so liters are whole for efficiencies of 5 and 10. 

- **Cost** is <mark>distance times base rate</mark> . The fuel route reaches the same number because <mark>toll_fee</mark> is derived: <mark>cost minus liters times fuel price</mark> . 

#### **Constants** 

|Vehicle|Capacity|Speed (km/h)|Km per liter|Base rate per km|Fuel price per liter|
|---|---|---|---|---|---|
|Van|120|50|10|3|12|
|Truck|400|42|5|4|15|
|Drone|60|80|10|5|20|



Kit weight is 5 kg and kit box volume is 20 liters. Stock: W1 50, W2 64, W3 40. IoT weights: 250, 320 and 200 kg. Logs: start 70, 80, 60, shipped 20, 16, 20. 

#### **Results for each route (all three routes give the same number)** 

|Route|Vehicle|Distance|Time (min)|Cost|Liters|Toll|
|---|---|---|---|---|---|---|
|W1 to C2|Van|120|144|360|12|216|
|W1 to C2|Truck|120|171|480|24|120|
|W1 to C2|Drone|120|90|600|12|360|
|W2 to C2|Van|90|108|270|9|162|
|W2 to C2|Truck|90|129|360|18|90|
|W2 to C2|Drone|90|68|450|9|270|
|W3 to C2|Van|110|132|330|11|198|
|W3 to C2|Truck|110|157|440|22|110|
|W3 to C2|Drone|110|82|550|11|330|



#### **Example: the raw records for W3 to C2 with the Truck** 

- GIS: <mark>map_distance_km</mark> 110, <mark>base_rate_per_km</mark> 4. 

- Fuel: <mark>vehicle_km_per_liter</mark> 5, <mark>fuel_price_per_liter</mark> 15, and for the route <mark>expected_fuel_liters</mark> 22, <mark>toll_fee</mark> 110. 

- Billing: <mark>billed_mileage_km</mark> 110, <mark>total_quoted_cost</mark> 440. 

- Fleet: <mark>max_kit_capacity</mark> 400, <mark>average_speed_kmh</mark> 42. 

- GPS: <mark>max_payload_kg</mark> 2000, <mark>kit_unit_weight_kg</mark> 5, <mark>live_speed_kmh</mark> 42, <mark>trafc_delay_minutes</mark> fi 0. 

- ETA: <mark>cargo_bay_volume_l</mark> 8000, <mark>kit_box_volume_l</mark> 20, <mark>estimated_minutes</mark> 157. 

The three routes then give: distance 110, 22 times 5 = 110, 110. Time 157, 157, 157. Cost 440, 22 times 15 plus 110 = 440, 440. Capacity 400, 2000 divided by 5 = 400, 8000 divided by 20 = 400. 

**Simplifications to state in the paper:** live speed equals average speed and the delay is 0, capacity is the same by weight and by volume, the Drone is given fuel-equivalent liters, and the fixed handling fee is left out. 

## **8. Tests that would have caught each problem** 

1. **Key test:** for every tool and key, the claim is for the requested key. W1, W2 and W3 give different ETA and billing values. _Catches Bug 5. It fails today._ 

2. **Backup test:** the backup reading equals the backup tool's value for the same key. _Catches Bug 6. It fails today._ 

3. **Same-question test:** the Coordinator sends the same question to all three agents of a domain. _Catches finding 1._ 

4. **Consistency test:** in a clean world, the three routes return the same whole number for every question and key. _Catches findings 3, 4 and 7, and the IoT data error._ 

5. **No-fallback test:** a missing key raises an error. _Catches finding 9._ 

6. **Independence test:** poison one tool, and exactly one route changes. _Catches the hidden dependency on the GIS tool._ 

7. **Format test:** a claim has exactly the agreed keys, two readings and whole-number values. 

8. **Cascade test:** a wrong resolved distance changes only Q4 routes 1 and 2. 

9. **Truth separation test:** the defense never receives a true value, and a wrong decision changes the plan. 

10. **Repeatability test:** the same seed gives the same results. 

## **9. What I could not check, and questions for the team** 

- **The folder layout.** I assumed <mark>simulator/</mark> with <mark>data/</mark> , <mark>participants/</mark> and <mark>agents/</mark> . 

- **One truth.** Do you keep the haversine distances from <mark>warehouse.py</mark> (rounded to multiples of 10 km), or the distances in the tool files (120, 90, 110)? 

- **The six camps.** Do they all get tool rows (C1 to C6), or does the demo use only the camps with data? 

- **Medicines against kits.** The app orders five medicines, and the tools know only kit K1. 

- **The handling fee, the Drone's fuel, and the live speed with the delay set to 0.** Confirm these simplifications. 

- **The Streamlit page.** It works as a demo, so keep it, but make it call the headless mission function. 

