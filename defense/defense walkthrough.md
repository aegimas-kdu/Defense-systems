**Defense Build Walkthrough: Phases A to C**



**Project:** Trust-Ledgered Resilience of Multi-Agent AI Systems Against Combined Byzantine and Tool-Poisoning Attacks

This guide works through Phases A, B and C of Defense Roadmap v3, one step at a time. It does not give you the finished code. For every step it says what the step does and what it delivers, then explains each file, class, function and line you need to write. After each step, run the check, and paste your code here for review. The walkthrough for Phases D and E comes later.



**Names used everywhere**



•	Test world: a small pretend system for developing the defense before the real simulator is ready. One mission asks a distance question (Logistics agents), then a time question (Transportation agents), about the same key.

•	Key: a pair like ('W1', 'H2'): a warehouse and a hospital. There are 5 warehouses and 3 hospitals, so 15 keys. A slice is all the keys of one warehouse.

•	Agents: LA1, LA2, LA3 (Logistics) and TA1, TA2, TA3 (Transportation).

•	Tools: L1 (GIS distance), L2 (fuel), L3 (billing), T1 (fleet), T2 (GPS), T3 (ETA).

•	Each agent reads two tools: LA1: L1, L3, LA2: L2, L1, LA3: L3, L2, TA1: T1, T3, TA2: T2, T1, TA3: T3, T2. The first is the primary tool and the second is the backup.

•	Reading: one tool's value for the question, already in the answer's unit. Claim: one agent's answer plus its two readings.

•	Verdict: the value the defense decides is right for a question. Decision: what the defense returns for a question.

•	Seeds: development seeds are 1 to 20. Do not tune on any others.

•	Run the tests: python -m pytest defense/tests -v from the folder that contains defense.





**Phase A: Foundations**



**Step A1. Workspace check**



What this step does: gets your folder ready for the new design and removes the old generator, so nothing old gets mixed in.

What it delivers: a clean defense/ package with the layout below, and a test run that starts without import errors.

The layout

trust-ledger-mas/

&#x20; defense/

&#x20;   \_\_init\_\_.py

&#x20;   settings.py       # every number (Step A3)

&#x20;   fake\_ledger.py    # stand-in ledger (Step A4)

&#x20;   fake\_claims.py    # the test world (Phase B)

&#x20;   evaluate.py       # runs missions, measures results (Step B4)

&#x20;   baselines.py      # D1 and D1b (Step B5)

&#x20;   blame.py          # the blame rule (Step C1)

&#x20;   trust.py          # counters, trust, quarantine (Step C2)

&#x20;   defense.py        # Defense base class and D4-Base (Steps B5, C3)

&#x20;   tests/

&#x20;     \_\_init\_\_.py

&#x20;     test\_ledger.py



**What to do, line by line**



1\.	Rename the old fake\_claims.py to old\_fake\_claims.py, and the old test\_fake\_claims.py to old\_test\_fake\_claims.py. Pytest only collects files that start with test\_, so the old tests stop running, and nothing imports the old module by accident. Delete them later.

2\.	Check that defense/\_\_init\_\_.py and defense/tests/\_\_init\_\_.py exist (empty files).

3\.	Create the empty files in the layout that do not exist yet.

4\.	Run pytest. The ledger test should still pass (it changes in Step A4).

5\.	Commit on your branch defense-precieuse.

Check: pytest starts, git status is clean after the commit.





**Step A2. Agree the interfaces**



**What this step does:** fixes the shape of the data that passes between your code and the team's code. If these shapes change later, every module breaks, so you agree them now, in writing.

What it delivers: docs/defense\_interfaces.md (about half a page) with an "OK" from Bessie, Ted and Marie Rosine.

What goes in the file



1\.	**The claim.** One dictionary per agent per question. List these keys, each with one line of meaning:

&#x09;	o mission\_id: the mission number.

&#x20;               o question: 'dist' or 'time' in the test world.

&#x09;	o key: the fact asked about, for example ('W1', 'H2').

&#x09;	o agent\_id and domain.

&#x09;	o answer: the agent's own final answer. It equals its first (primary) reading.

&#x09;	o readings: a list of two dictionaries, each with tool\_id and value. The value is already converted to the answer's unit.

&#x09;	o inputs: extra inputs. For a time question it holds resolved\_distance\_km.



2\.	**The decision.** What the defense returns: decision\_id (built as the mission id, a colon, and the question, for example '17:time'), question, key, value, support (how many readings back the value), tied (True if another value had equal support), candidates (a dictionary from value to support), claims, and revised\_parent (None until Phase D).



3\.	**The defense functions:** decide(question, key, agents, ask, parent=None), end\_mission(decisions), learn\_audit(decision\_id, true\_value), get\_trust(entity\_id), is\_quarantined(entity\_id, key=None) and report(). Explain ask(agent\_ids): it returns the claims of those agents and charges 2 tool calls per agent. The defense must use ask to get claims, so agents it skips are not paid for.



4\.	**The ledger entry.** One per reading: decision\_id, agent\_id, tool\_id, key, value, parent\_decision\_ids, agreed\_with\_verdict, audit\_correct, excused\_by\_parent.

Questions to answer in the file: who counts tool calls (the evaluator), who decides audits (the evaluator), whether the ledger stores one entry per reading (yes), and what a quarantined entity means (its readings get no vote).

Check: three replies saying OK, with changes included.





**Step A3. Settings**



What this step does: puts every number in one place, so no threshold is hidden inside the code.



What it delivers: settings.py with a Settings class and a load\_settings function, plus a small test file.



**The class Settings**

•	What it is: a container whose attributes are the numbers, read as settings.min\_claims.

•	\_\_init\_\_(self, \*\*overrides): \*\*overrides collects any named arguments into a dictionary, so you can write Settings(min\_claims=20).



&#x09;o	Lines 1 to 8, the defaults. One line each, written as self.name = value: n\_missions = 300, slip\_rate = 0.05, n\_scattered\_poison\_keys = 3, min\_claims = 10, t\_agent = 0.30, 		t\_tool = 0.15, support\_needed = 3, audit\_rate = 0.0. Put them in \_\_init\_\_ and not at class level, so that two Settings objects never share values.



&#x09;o	Lines 9 to 14, Phase D settings (add them now so you do not return later): trust\_fast\_path = 0.90, slice\_flag\_after = 2, n\_probation = 15, use\_cascade\_revision = True, 		use\_fact\_quarantine = True, use\_fast\_path = True.



&#x09;o	The override loop: for name, value in overrides.items():. Inside it, check hasattr(self, name). If it is False, raise a ValueError that names the bad setting. Otherwise 		call setattr(self, name, value). Why the check: a typo such as t\_agnet=0.5 would otherwise be ignored without any warning.



•	load\_settings(\*\*overrides): one line, return Settings(\*\*overrides). It is the single entry point, so later it can read the team's shared file.



**Tests to write (4**): the defaults are right; an override changes the value; an unknown name raises ValueError; changing one object's value does not change another's.

Check: the four tests pass, and a search for 0.30 and 0.15 in the other files finds nothing.





**Step A4. Fake ledger and its contract test**



**What this step does**: adapts the stand-in ledger to the new fields: one entry per reading, two separate outcomes, and the ids of the parent decisions.

**What it delivers:** the updated fake\_ledger.py, and a test, check\_ledger, that works for any ledger (the real one in Phase E).



The class FakeLedger (changes from the version you wrote before)



&#x09;•	\_\_init\_\_(self): unchanged. self.entries = \[] is the notebook.



&#x09;•	append(self, entry):

&#x09;	a.	stored = dict(entry) makes a copy, so changing the caller's dictionary later cannot change the record.

&#x09;	b.	Four stored.setdefault(...) lines fill what the caller left out: 'parent\_decision\_ids' as an empty list, 'agreed\_with\_verdict' as None, 'audit\_correct' as None, 			'excused\_by\_parent' as False. setdefault keeps the caller's value when there is one and only fills the gaps.

&#x09;	c.	stored\['entry\_id'] = len(self.entries) gives the next number (0, 1, 2, ...).

&#x09;	d.	Append stored to the list.

&#x09;	e.	Return the id.



&#x09;•	query(self, agent\_id): unchanged. A list comprehension keeping entries whose agent\_id matches.



&#x09;•	query\_decision(self, decision\_id) (new): the same pattern, on decision\_id. Phase D needs it to answer "which readings were behind decision 17:dist?".



&#x09;•	set\_outcome(self, entry\_id, agreed=None, audit\_correct=None, excused=None):

&#x09;	a.	entry = self.entries\[entry\_id] finds the entry.

&#x09;	b.	Three lines of the form if agreed is not None: entry\['agreed\_with\_verdict'] = agreed, and the same for audit\_correct and excused (which sets excused\_by\_parent).

&#x09;	c.	Why the is not None checks: you can set one outcome without erasing the other. An audit may arrive long after the agreement was recorded.



&#x09;•	verify\_chain(self): unchanged. Returns True.



**The test check\_ledger(ledger) (rewrite these lines)**



1\.	Append two entries, with decision\_id, tool\_id, key and value, for two different agents. Check the ids differ.

2\.	Check the defaults are present on a fresh entry (parents empty, both outcomes None, excused False).

3\.	query returns only the right agent's entry.

4\.	query\_decision returns both entries when they share a decision id, and one when they do not.

5\.	Call set\_outcome(id, agreed=True). Check audit\_correct is still None.

6\.	Later call set\_outcome(id, audit\_correct=False). Check agreed\_with\_verdict is still True.

7\.	verify\_chain() is True.

8\.	test\_fake\_ledger() calls check\_ledger(FakeLedger()).



**Check:** the test passes. Then break set\_outcome so that it overwrites both fields, run the test, and confirm it fails. Undo the break.





***Phase B: Test world and baselines***



**Step B1. The world: truth, tools and poison**



**What this step does:** builds the pretend facts, the value each of the six tools would return, and the poison.

**What it delivers:** the first half of fake\_claims.py: the constants, poison\_value, make\_truth, pick\_poison\_keys, make\_sequence, make\_noise, and the World class with true\_value and tool\_value. Plus tests for them.



**The constants, at the top of the file**

&#x09;1.	import random on the first line.



&#x09;2.	WAREHOUSES: the list \['W1', ..., 'W5']. HOSPITALS: \['H1', 'H2', 'H3'].



&#x09;3.	KEYS: a list of tuples (warehouse, hospital), built with a list comprehension over both lists. It has 15 entries, in a fixed order. The fixed order matters: it makes every 		seeded choice repeat exactly.



&#x09;4.	LOGISTICS\_AGENTS and TRANSPORT\_AGENTS: the two lists of three ids.

&#x09;5.	AGENT\_TOOLS: a dictionary from agent id to a tuple (primary\_tool, backup\_tool), as listed in the names section.

&#x09;6.	DOMAIN\_AGENTS: a dictionary, {'dist': LOGISTICS\_AGENTS, 'time': TRANSPORT\_AGENTS}.

&#x09;	poison\_value(value)



&#x09;•	One line: return value + max(10, value // 2). Why: the result is always different from the input (at least 10 more), and the rule has no randomness, so every reader of a 		poisoned fact gets the same wrong number.



**make\_truth(seed)**

&#x09;1.	Make a random generator: rng = random.Random(f'truth-{seed}'). A text seed repeats exactly, and putting the word truth in it gives this function its own dice.

&#x09;2.	Start an empty dictionary.

&#x09;3.	Loop over KEYS.

&#x09;4.	For each key, store 20 \* rng.randint(1, 15). That gives distances of 20, 40, ..., 300 km.

&#x09;5.	Return the dictionary. The true time in minutes equals the true distance, because every vehicle is the Van at 60 km/h. Say that in a comment.

&#x09;	pick\_poison\_keys(seed, mode, n\_scattered)



1\.	Make the generator random.Random(f'poison-{seed}').

2\.	If mode == 'none', return an empty set.

3\.	If mode == 'scattered', return set(rng.sample(KEYS, n\_scattered)). sample picks different keys with no repeats.

4\.	If mode == 'aligned', pick a warehouse with rng.choice(WAREHOUSES) and return the set of keys whose first element is that warehouse. That is 3 keys, all in one slice.

5\.	Any other mode: raise ValueError.



make\_sequence(seed, n)

•	Make a generator, and return a list of n keys, each picked with rng.choice(KEYS). This is the order of missions. Every defense faces the same sequence.

make\_noise(seed, n\_missions)

•	What it is: a table of random numbers made once, before any defense runs. Why: a defense that asks fewer agents would otherwise use fewer random numbers, and every later random draw would shift. Then two defenses would face different slips and lies, and the comparison would be unfair. With a precomputed table, an agent's slip or lie on a given mission is fixed, whoever asks.

•	Lines:

a.	Make the generator. Start an empty dictionary.

b.	Loop over m in range(n\_missions), then over the two question types, then over every agent in AGENT\_TOOLS.

c.	For each, build a list of two tuples (one per reading). Each tuple holds three numbers: rng.random() (the slip roll), rng.randint(1, 5) \* rng.choice(\[-1, 1]) (the slip size), and rng.randint(5, 50) \* rng.choice(\[-1, 1]) (the lie offset).

d.	Always draw all three numbers, even if a reading will not use them. Then the stream never shifts.

e.	Store the list under the key (m, qtype, agent).

The class World

•	\_\_init\_\_(self, seed, poison\_mode='none', liar=None, poison\_tool='L1', settings=None): if settings is None, call load\_settings(). Then store: self.settings, self.truth = make\_truth(seed), self.poison\_keys = pick\_poison\_keys(...), self.poison\_tool, self.liar, self.sequence = make\_sequence(seed, n\_missions), and self.noise = make\_noise(seed, n\_missions).

•	true\_value(self, qtype, key): return self.truth\[key]. Both question types have the same truth in this world.

•	tool\_value(self, tool, key, dres):

a.	If the tool is 'T1' or 'T2' (fleet and GPS), the base value is dres, the resolved distance the Coordinator passed in. Otherwise the base is self.truth\[key].

b.	If tool == self.poison\_tool and key in self.poison\_keys, return poison\_value(base).

c.	Otherwise return the base.

o	Note that when a T1 or T2 reading is poisoned, the poison is applied to the value derived from the distance.

Tests to write (6): the same seed gives the same truth, poison keys and sequence; all distances are multiples of 20 from 20 to 300; the three poison modes give 0, 3 and 3 keys (and in aligned mode all 3 share a warehouse); poison\_value(v) != v for v from 0 to 1999; the poison tool returns poison\_value on exactly the poison keys and the true value elsewhere; make\_noise is identical for the same seed.

Check: all six pass.

Step B2. Readings and claims

What this step does: makes agents read their two tools, with honest slips and lies.

What it delivers: World.read, returning a claim in the agreed format.

World.read(self, agent, key, m, qtype, dres=None), line by line

1\.	truth = self.true\_value(qtype, key).

2\.	Start an empty list readings.

3\.	Loop with for tool, (slip\_roll, slip\_size, lie\_offset) in zip(AGENT\_TOOLS\[agent], self.noise\[(m, qtype, agent)]):. zip pairs the agent's first tool with the first noise tuple, and the second tool with the second.

4\.	value = self.tool\_value(tool, key, dres): what the tool says.

5\.	if agent == self.liar: replace the value with truth + lie\_offset. A liar ignores the tool, and since the offset is never 0, the lie is never the truth.

6\.	elif slip\_roll < self.settings.slip\_rate / 2: add slip\_size. Why divide by 2: an agent has two readings, so a slip rate of 5% per agent is 2.5% per reading.

7\.	Append {'tool\_id': tool, 'value': value} to readings.

8\.	After the loop, return the claim dictionary: mission\_id is m, question is qtype, key, agent\_id is agent, domain is 'logistics' for LA agents and 'transportation' for TA agents, answer is readings\[0]\['value'], readings, and inputs, which is {'resolved\_distance\_km': dres} when the question is 'time' and an empty dictionary otherwise.

Tests to write (5): reading the same agent twice gives the identical claim; a liar's two readings never equal the truth; in a clean world, an honest agent's reading equals the tool value except for about 2.5% (count over all missions and agents, accept 1% to 4%); every claim has exactly the agreed keys and two readings; two agents that read the same poisoned tool and key get the same wrong value.

Check: all five pass.

Step B3. Scenarios and generator tests

What this step does: defines the five scenarios you will compare methods on.

What it delivers: SCENARIOS, the function scenario\_runs, and a generator test file.

SCENARIOS: a dictionary from a name to a short description, for printing: S0 clean, S1 one liar, S2s scattered poison, S2a aligned poison, S3 a liar and scattered poison.

scenario\_runs(name)

•	It returns a list of (poison\_mode, liar) pairs. One pair is one run per seed.

o	S0: \[('none', None)].

o	S1: \[('none', agent) for agent in ALL\_AGENTS], which is 6 runs, one per possible liar.

o	S2s: \[('scattered', None)]. S2a: \[('aligned', None)].

o	S3: \[('scattered', agent) for agent in ALL\_AGENTS], which is 6 runs.

•	ALL\_AGENTS is LOGISTICS\_AGENTS + TRANSPORT\_AGENTS. Why one run per liar: the liar's position matters (it may share a tool with the poisoned one), so you average over all six positions.

•	Unknown names: raise ValueError.

Tests to write (4): scenario\_runs('S1') and ('S3') have 6 pairs, the others 1; running every scenario for one seed creates a World without error; the same pair and seed give identical sequences; the liar in S3 is never the same entity as the poisoned tool (they are an agent and a tool, so check the ids differ in type).

Check: pytest passes for all generator tests (B1, B2 and B3).

Step B4. The evaluator

What this step does: runs one defense through all the missions of one world. It counts tool calls, checks the answers against the truth, and measures false punishments. The evaluator is the only part of the code that sees the true answers.

What it delivers: evaluate.py with make\_ask, run\_mission, run\_world, summarize and results\_table.

make\_ask(world, key, m, qtype, dres, tally)

•	What it does: builds the function that the defense calls to get claims.

•	Lines:

a.	Define an inner function ask(agent\_ids).

b.	Inside it: claims = \[world.read(a, key, m, qtype, dres) for a in agent\_ids].

c.	Inside it: tally\['calls'] += 2 \* len(agent\_ids). Each claim costs 2 tool calls, one per reading.

d.	Inside it: return claims.

e.	Outside it: return ask.

•	Why a function inside a function: the inner function remembers world, key, m, qtype, dres and tally. So the defense only has to say which agents it wants.

•	tally: a dictionary such as {'calls': 0}, shared for the whole run. ask changes it.

run\_mission(world, defense, m, tally)

1\.	key = world.sequence\[m]: the fact for this mission.

2\.	Distance question: ask = make\_ask(world, key, m, 'dist', None, tally), then dec\_d = defense.decide('dist', key, DOMAIN\_AGENTS\['dist'], ask).

3\.	Time question: dres = dec\_d\['value']. This is the Coordinator passing the resolved distance on. Then ask = make\_ask(world, key, m, 'time', dres, tally) and dec\_t = defense.decide('time', key, DOMAIN\_AGENTS\['time'], ask, parent=dec\_d).

4\.	defense.end\_mission(\[dec\_d, dec\_t]).

5\.	Final distance: use dec\_t\['revised\_parent'] if it exists and is not None, otherwise dec\_d\['value']. Use dec\_t.get('revised\_parent') with an is not None test, because simple defenses leave the key out or set it to None.

6\.	ok\_d = final\_d == world.true\_value('dist', key) and ok\_t = dec\_t\['value'] == world.true\_value('time', key).

7\.	Return {'dist': ok\_d, 'time': ok\_t, 'mission': ok\_d and ok\_t}.

•	Important: the true value appears only in step 6. It never goes into decide or ask.

run\_world(world, defense)

1\.	tally = {'calls': 0}, and three counters for distance, time and mission successes.

2\.	Loop for m in range(len(world.sequence)). Call run\_mission and add its three flags to the counters.

3\.	After the loop, report = defense.report().

4\.	False punishments:

o	honest\_agents\_quarantined = len(report\['quarantined\_agents'] - {world.liar}). Set subtraction removes the real liar, so only innocents are counted.

o	bad\_tools = {world.poison\_tool} if world.poison\_keys else set(), then clean\_tools\_quarantined = len(report\['quarantined\_tools'] - bad\_tools).

5\.	Return a dictionary: mission\_success, dist\_acc, time\_acc (each a counter divided by the number of missions), calls\_per\_mission = tally\['calls'] / n, honest\_agents\_quarantined, clean\_tools\_quarantined.

summarize(results)

•	Takes a list of the dictionaries from run\_world. For each metric, return the mean (statistics.mean) and the standard error (statistics.stdev(values) / len(values) \*\* 0.5). With fewer than 2 values, the standard error is 0.0.

results\_table(factories, scenario\_names, seeds, settings)

•	factories is a dictionary from a method name to a function factory(settings, seed) that returns a new defense.

•	Lines:

a.	Loop over the scenario names. Inside it, loop over the factories.

b.	For each seed, and each (poison\_mode, liar) pair from scenario\_runs(name): build World(seed, poison\_mode, liar, settings=settings), build a fresh defense with factory(settings, seed), call run\_world, and append the result. A fresh defense per run matters: otherwise trust learned in one run leaks into the next.

c.	Summarize, and print one row: method name, mission success with its standard error, calls per mission, the total of honest agents quarantined, and the total of clean tools quarantined.

d.	Return all the rows, so they can be saved to a file.

Tests to write (5):

1\.	A dummy defense (in the test file) that takes the first claim's answer: run\_world returns metrics between 0 and 1.

2\.	A defense that asks all 3 agents on each question: calls\_per\_mission is exactly 12 (2 questions times 3 agents times 2 readings).

3\.	Spy test: a defense that stores every claim it receives. After a run, every claim has exactly the agreed keys, and no claim contains a true\_value key.

4\.	Running run\_world twice with the same seed gives identical results.

5\.	Plumbing test: a defense that returns a deliberately wrong distance. The time claims it receives must then carry that wrong value in inputs\['resolved\_distance\_km'].

Check: all five pass.

Step B5. D1 and D1b

What this step does: builds the two vote baselines, and the tie-break they share with every later defense.

What it delivers: the Defense base class, plurality and make\_decision in defense.py, and MajorityVote (D1) and ReadingVote (D1b) in baselines.py.

plurality(votes, rng), in defense.py

•	votes is a Counter that maps a value to how many votes it has.

•	Lines:

a.	If votes is empty, return (None, 0, False).

b.	top = max(votes.values()): the highest number of votes.

c.	leaders = sorted(v for v, c in votes.items() if c == top): the values that have it. Sorting makes the order independent of insertion order.

d.	tied = len(leaders) > 1.

e.	value = rng.choice(leaders) if tied else leaders\[0].

f.	Return (value, top, tied).

•	Why a seeded random tie-break: it repeats exactly for the same seed, and it has no hidden bias. A rule such as "pick the smallest value" would quietly favor some outcomes. Every defense uses this same tie-break as its last step.

make\_decision(question, key, claims, value, support, tied, candidates)

1\.	mission = claims\[0]\['mission\_id'].

2\.	decision\_id = f'{mission}:{question}'.

3\.	Return a dictionary with decision\_id, question, key, value, support, tied, candidates (as a plain dictionary), claims, and revised\_parent set to None.

•	Why it exists: every defense builds the decision in the same shape, so the evaluator and later code never have to guess.

The class Defense (the base class), in defense.py

•	\_\_init\_\_(self, settings, seed): store self.settings, and make self.rng = random.Random(f'ties-{seed}'). The word ties gives the tie-break its own dice.

•	decide(self, question, key, agents, ask, parent=None): raise NotImplementedError. Each real defense replaces it.

•	end\_mission(self, decisions): pass. Learning defenses use it later.

•	learn\_audit(self, decision\_id, true\_value): pass. Audits arrive in Phase E.

•	get\_trust(self, entity\_id): return None.

•	is\_quarantined(self, entity\_id, key=None): return False.

•	report(self): return {'quarantined\_agents': set(), 'quarantined\_tools': set(), 'flags': set()}.

•	Why a base class: the evaluator calls the same functions on every defense. A baseline with no memory only needs to write decide.

MajorityVote(Defense) (D1), in baselines.py

•	decide:

a.	claims = ask(agents): ask all agents of the domain.

b.	votes = Counter(claim\['answer'] for claim in claims).

c.	value, support, tied = plurality(votes, self.rng).

d.	Return make\_decision(question, key, claims, value, support, tied, votes).

•	D1 looks at each agent's final answer only. It ignores the readings.

ReadingVote(Defense) (D1b)

•	Same as D1, except line 2: votes = Counter(reading\['value'] for claim in claims for reading in claim\['readings']). Every reading is a vote, so there are up to 6 votes per question.

Tests to write (6): use a fake ask, such as lambda agent\_ids: prepared\_claims.

1\.	Answers \[50, 50, 60]: D1 returns 50, support 2, tied False.

2\.	Answers \[50, 60, 70]: tied is True and the value is one of the three. The same seed gives the same value twice.

3\.	A case where D1 and D1b differ: three agents whose answers are 50, 70 and 80, but whose second readings are all 60. D1 is a three-way tie. D1b returns 60, with support 3.

4\.	plurality on an empty counter returns (None, 0, False).

5\.	The decision dictionary has exactly the agreed keys.

6\.	Defense().report() has the three keys.

Check: all six pass.

Step B6. Baseline results

What this step does: runs both baselines on every scenario and saves the first results table.

What it delivers: a text file results/phase\_b\_baselines.txt with D1 and D1b on S0, S1, S2s, S2a and S3, on development seeds 1 to 20.

What to do

1\.	Create the folder results/.

2\.	At the bottom of evaluate.py, add if \_\_name\_\_ == '\_\_main\_\_':. Inside it:

o	Build the factories dictionary: 'D1 answer vote' maps to a function that returns MajorityVote(settings, seed), and 'D1b reading vote' to one that returns ReadingVote(settings, seed).

o	Set settings = load\_settings(), the scenario names \['S0', 'S1', 'S2s', 'S2a', 'S3'], and seeds = range(1, 21).

o	Call results\_table, and write its rows to results/phase\_b\_baselines.txt.

3\.	Run it with python -m defense.evaluate from the folder that contains defense. The -m makes Python treat defense as a package, so the imports work.

4\.	Under the table, write 3 to 5 sentences about what you see, whatever it is.

What to look for: the calls per mission (12 for both), how the two baselines differ in S3, and whether anything is not 1.000 in S0.

For orientation only: in my prototype (test seeds, so your numbers will differ a little), D1 scored 0.922 in S3, 0.966 in S1 and 0.991 in S2s, while D1b scored 0.983, 1.000 and 0.999. If D1b is far worse than D1, or the calls are not 12, look for a bug before you trust the table.

Check: the file is saved, and the table has 5 scenarios times 2 methods.

Phase C: The fair trust defense, D4-Base

Step C1. The blame rule and blame.py

What this step does: decides who is at fault on one question, as a set of pure functions with no memory. A pure function gives the same output for the same input, so you can test it with small hand-made examples.

What it delivers: the written blame rule as the first comment block of blame.py, and three functions: tool\_agreed\_values, is\_right and question\_evidence. Plus eight hand-made tests.

The blame rule (write this first, as the comment at the top of blame.py)

Agree on the rule before you write any code. Paste this block at the top of the file, and copy it into your design page.

\# THE BLAME RULE (version 1)

\#

\# Input: the claims of ONE question, the verdict (the value judged right),

\#        and a set of excused tools (empty until Phase D).

\# A reading is (agent, tool, value). A reading is RIGHT if its value equals

\# the verdict, or if its tool is excused. Otherwise it is WRONG.

\#

\# Rule 1  Agreed value of a tool. If a tool was read at least twice on this

\#         question and every reading has the same value, that value is the

\#         tool's agreed value. Otherwise the tool has no agreed value.

\# Rule 2  Tool evidence. For every tool that has an agreed value and is not

\#         excused: the tool is WRONG if its agreed value differs from the

\#         verdict, otherwise RIGHT. A tool with no agreed value gets no

\#         evidence on this question.

\# Rule 3  Agent evidence. An agent is BAD only if BOTH of its readings are

\#         wrong, unless both wrong readings are explained by tools (each one

\#         equals its tool's agreed value). Otherwise the agent is GOOD.

\# Rule 4  No verdict, no blame. If the question has no verdict, nothing is

\#         recorded. (The caller enforces this.)

\# Rule 5  Excused tools (the cascade, Phase D). Their readings count as

\#         right, and they get no tool evidence.

\#

\# Why Rule 3 says BOTH: a liar invents both of its readings, so both are

\# wrong. An honest agent hit by a poisoned tool or a slip is wrong in one

\# reading at most, because its other tool is right. So one wrong reading

\# is never enough to blame an agent.

\#

\# Known limits:

\#  - A liar who lies in only one reading is not caught by Rule 3.

\#  - If the verdict itself is wrong, the right readings are blamed.

\#  - An honest agent wrong in both readings (two bad tools, or two slips)

\#    is blamed unless both tools agreed on the wrong value.

\#  - A poisoned tool whose two readers include a liar gets no evidence

\#    on that question (its readers disagree).

Why this rule: my prototype tested two versions. Blaming an agent for any single wrong reading made honest agents get quarantined in 13% of combined-attack runs. Blaming only when both readings are wrong made it 0 of 240, while the liar was still quarantined every time. Treat that as a hint, not proof, and re-measure on your own world.

The functions

tool\_agreed\_values(claims)

•	What it does: for every tool that appears in the claims, finds its agreed value, or None. This is Rule 1.

•	Lines:

a.	by\_tool = {}: a dictionary from tool id to a list of values.

b.	Two nested loops: for claim in claims: then for reading in claim\['readings']:. Append reading\['value'] to by\_tool.setdefault(reading\['tool\_id'], \[]). setdefault creates the list the first time a tool is seen.

c.	agreed = {}. Loop over by\_tool.items(). If len(values) >= 2 and len(set(values)) == 1, store agreed\[tool] = values\[0]. Otherwise store agreed\[tool] = None. set(values) has one element only when all the values are equal.

d.	Return agreed.

•	An assumption to write in a comment: an agent's two tools are different, so two readings of one tool come from two different agents.

is\_right(reading, verdict, excused)

•	One line: return reading\['value'] == verdict or reading\['tool\_id'] in excused.

question\_evidence(claims, verdict, excused=frozenset())

•	What it does: applies Rules 2, 3 and 5, and returns the evidence for one question.

•	Lines:

a.	agreed = tool\_agreed\_values(claims).

b.	Tool evidence: tools = {}. Loop over agreed.items(). Skip (use continue) if value is None or tool in excused. Otherwise set tools\[tool] = 'right' if value == verdict else 'wrong'.

c.	Agent evidence: agents = {}. Loop over the claims. For each claim, readings = claim\['readings'].

▪	wrong = \[not is\_right(r, verdict, excused) for r in readings]: a list of two booleans.

▪	explained = \[agreed\[r\['tool\_id']] is not None and agreed\[r\['tool\_id']] == r\['value'] for r in readings]: True when the reading equals its tool's agreed value, which means the tool is the cause.

▪	bad = all(wrong) and not all(explained): both readings wrong, and not both explained by tools.

▪	agents\[claim\['agent\_id']] = 'bad' if bad else 'good'.

d.	Return {'agents': agents, 'tools': tools}.

•	Why it returns a plain dictionary and keeps no memory: you can test it with tiny inputs. The memory lives in trust.py.

The eight hand-made tests

Write a small helper claim(agent, first, second) that builds a claim from two (tool, value) pairs. Use three agents on three tools in the same triangle: A reads X and Z, B reads Y and X, C reads Z and Y. The verdict is 100.

1\.	Clean: every reading is 100. All agents good, all tools right.

2\.	One liar: B reports 70 and 130, the others report 100. B is bad. The tools B read have disagreeing readings, so they get no evidence. The one tool B did not read is right.

3\.	Poisoned tool: both readers of Y report 140, everything else is 100. Y is wrong, X and Z are right, and every agent is good.

4\.	Poisoned tool shared with a liar: Y is read by an honest agent (140) and by the liar (60). Y gets no evidence. The honest agent is good, the liar is bad.

5\.	One honest slip: one reading is 103, all others 100. Every agent is good, and the slipped tool gets no evidence.

6\.	Two poisoned tools: Y and Z both return 140 to both of their readers. The agent that reads both is good, because both wrong readings are explained. Y and Z are wrong, X is right.

7\.	One echo and one garbage reading: an agent reads Y (agreed wrong 140) and Z (garbage 55). It is bad, because the second reading is not explained by Z.

8\.	Excused tool: with excused={'Y'}, readings of Y count as right, Y gets no evidence, and an agent whose only wrong reading is the Y one is good.

Check: all eight pass. Read them as a team (Crispin and Bessie) before moving on, and ask whether the rule matches your idea of fair blame.

Step C2. Trust memory

What this step does: keeps the counters, turns them into trust scores, and decides who is quarantined.

What it delivers: trust.py with the class TrustMemory, and its tests.

The class TrustMemory

•	\_\_init\_\_(self, settings):

a.	Store self.settings.

b.	Four Counter objects (from collections): self.agent\_seen, self.agent\_bad, self.tool\_seen, self.tool\_wrong. A Counter returns 0 for a name it has not seen, so you never need to check first.

c.	Two empty sets: self.q\_agents and self.q\_tools, the quarantined entities.

•	record(self, evidence): takes the dictionary from question\_evidence.

a.	for agent, verdict in evidence\['agents'].items(): add 1 to agent\_seen\[agent], and if the verdict is 'bad', add 1 to agent\_bad\[agent].

b.	The same for evidence\['tools'], with 'wrong' and tool\_wrong.

c.	Call self.\_update\_quarantine().

•	\_update\_quarantine(self):

a.	Loop over self.agent\_seen. Let n = self.agent\_seen\[a]. If n >= self.settings.min\_claims and self.agent\_bad\[a] / n > self.settings.t\_agent, add a to self.q\_agents.

b.	The same for tools, with t\_tool and tool\_wrong.

o	Why > and not >=: the limit itself is not enough. Why min\_claims: a bad rate over 2 or 3 observations is luck, and a quarantine is permanent in this phase (recovery comes in Phase D).

•	agent\_trust(self, agent): (self.agent\_seen\[agent] - self.agent\_bad\[agent] + 1) / (self.agent\_seen\[agent] + 2). A new entity starts at 0.5. After many good observations it approaches 1.

•	tool\_trust(self, tool): the same with the tool counters.

•	is\_quarantined(self, entity\_id): return entity\_id in self.q\_agents or entity\_id in self.q\_tools.

•	quarantined\_agents(self) and quarantined\_tools(self): return copies, set(self.q\_agents) and set(self.q\_tools), so outside code cannot change the originals.

Tests to write (7):

1\.	A new entity has trust 0.5.

2\.	After 10 good observations, trust is 11/12 (about 0.917).

3\.	After 10 observations of which 4 are bad (0.4 is above 0.30), the agent is quarantined.

4\.	After 9 observations that are all bad, it is not quarantined (below min\_claims).

5\.	After exactly 10 observations with 3 bad (rate exactly 0.30), it is not quarantined.

6\.	A tool with 10 observations and 2 wrong (0.2 is above 0.15) is quarantined. With 1 wrong, it is not.

7\.	Agent counters and tool counters are separate, and an empty evidence dictionary changes nothing.

Check: all seven pass.

Step C3. The D4-Base class

What this step does: puts the blame rule and the memory behind the Defense interface. D4-Base uses full redundancy (it asks every agent), votes over readings, learns from agreement, and quarantines.

What it delivers: the class D4Base in defense.py, which also writes one ledger entry per reading.

Imports to add: question\_evidence from blame, TrustMemory from trust, and FakeLedger from fake\_ledger.

D4Base(Defense)

•	\_\_init\_\_(self, settings, seed, ledger=None):

a.	super().\_\_init\_\_(settings, seed) sets up the settings and the tie-break dice.

b.	self.memory = TrustMemory(settings).

c.	self.ledger = ledger if ledger is not None else FakeLedger(). The default is the fake ledger, so Phase E can pass in the real one.

•	\_usable\_votes(self, claims):

a.	votes = Counter().

b.	For each claim: continue if self.memory.is\_quarantined(claim\['agent\_id']).

c.	For each reading of that claim: continue if the reading's tool is quarantined. Otherwise votes\[reading\['value']] += 1.

d.	Return votes. Quarantined entities get no vote.

•	\_write\_ledger(self, decision, claims, parent):

a.	parents = \[parent\['decision\_id']] if parent else \[].

b.	ids = \[]. Loop over claims and readings. For each reading call self.ledger.append({...}) with decision\_id, agent\_id, tool\_id, key, value and parent\_decision\_ids. Append (entry\_id, reading\['value']) to ids.

c.	Return ids.

•	\_set\_agreement(self, ids, verdict): for each (entry\_id, value) in ids, call self.ledger.set\_outcome(entry\_id, agreed=(value == verdict)).

•	decide(self, question, key, agents, ask, parent=None):

a.	claims = ask(agents): ask every agent of the domain.

b.	votes = self.\_usable\_votes(claims).

c.	If votes is empty (everyone is quarantined), fall back to every reading: Counter(r\['value'] for c in claims for r in c\['readings']). A defense must always return a value.

d.	value, support, tied = plurality(votes, self.rng), then decision = make\_decision(question, key, claims, value, support, tied, votes).

e.	ids = self.\_write\_ledger(decision, claims, parent).

f.	Learn only if support >= self.settings.support\_needed. Then evidence = question\_evidence(claims, value), self.memory.record(evidence) and self.\_set\_agreement(ids, value). Why the condition: with fewer than 3 readings behind the value, the "verdict" may be a coin flip, and learning from it would punish the readings that were right.

g.	Return decision.

•	end\_mission(self, decisions): inherited, does nothing. D4-Base learns immediately inside decide. (D4+ will learn at the end of the mission, because a later question can revise an earlier one.)

•	learn\_audit: inherited, does nothing for now.

•	get\_trust(self, entity\_id): if entity\_id in self.memory.agent\_seen, return self.memory.agent\_trust(entity\_id). Otherwise if it is in tool\_seen, return the tool trust. Otherwise 0.5. This avoids importing the test world's agent list.

•	is\_quarantined(self, entity\_id, key=None): return self.memory.is\_quarantined(entity\_id).

•	report(self): return the two quarantined sets from the memory, and an empty set under 'flags'.

Tests to write (6):

1\.	A full run on S0 completes, and the number of ledger entries equals the tool calls (one entry per reading).

2\.	On a learned decision, every ledger entry has agreed\_with\_verdict set (True or False).

3\.	If you add 'LA1' to memory.q\_agents by hand and call decide with prepared claims, LA1's wrong readings get no vote.

4\.	If every agent is quarantined, decide still returns a value.

5\.	A decision with support below 3 (all readings different) changes no counters, and its ledger entries keep agreed\_with\_verdict as None.

6\.	get\_trust of an unseen id is 0.5.

Check: all six pass.

Step C4. D4-Base scenario tests and results

What this step does: measures D4-Base on every scenario, next to D1 and D1b.

What it delivers: scenario tests, and the saved table results/phase\_c.txt with D1, D1b and D4-Base.

What to change first (small edits to evaluate.py)

1\.	In run\_world, add one more entry to the returned dictionary: liar\_quarantined, which is 1 if world.liar in report\['quarantined\_agents'] and 0 if not. Use None when the world has no liar.

2\.	In results\_table, add a column that sums liar\_quarantined over the runs that have a liar, and prints it as a count out of the number of those runs.

3\.	Add the D4Base factory to the dictionary in the \_\_main\_\_ block, and run for seeds 1 to 20.

Scenario tests to write (4): these test properties, not an expected ranking.

1\.	Liar caught: over 5 seeds of S1 (6 liar positions each), count the runs where the liar is quarantined at the end. Assert at least 90%. If it is lower, find out why and write it down.

2\.	No false alarms in a clean world: over 20 seeds of S0, count honest agents quarantined and clean tools quarantined. Print both numbers.

3\.	Poison alone: over 20 seeds of S2s and S2a, count honest agents quarantined. Print it.

4\.	Combined: over 20 seeds of S3, count clean tools quarantined and honest agents quarantined. Print both.

For orientation only: in my prototype (test seeds), D4-Base scored about 0.984 in S3 and 1.000 in the other scenarios, quarantined no honest agent in 240 combined runs, and quarantined a clean tool in about 21 of those 240 runs. Those clean tools were the time tools, blamed because a wrong distance spoiled their readings. That is the cascade problem, and Phase D fixes it. Save your own numbers as the baseline the fix is measured against.

Check: the table is saved, and you have written down for S1, S3 and S0 how many liars were caught and how many innocents were punished.

What you will have at the end of Phase C

•	A test world with six tools, 15 facts, scripted agents, a liar and two kinds of poison.

•	An evaluator that counts tool calls and false punishments, and never shows the truth to a defense.

•	Three defenses: D1, D1b and D4-Base, with saved results on development seeds.

•	A written blame rule, tested on eight hand-made cases.

Send me your results tables from Steps B6 and C4 and any test that surprised you. We then move on to Phase D: cascade revision, the fast path, fact-level flags, and recovery.

