import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

# Known answer corrections mapping (test_num, q_num) -> list of valid answer strings
EXPLICIT_CORRECTIONS = {
    # Test 11
    (11, 21): ["power", "powering"],
    (11, 22): ["waste streams", "settling ponds"],
    (11, 23): ["contaminants", "bioremediation"],
    (11, 26): ["increase capacity", "produce one million", "capacity"],
    (11, 27): ["photosynthesis"],
    (11, 29): ["status and wealth"],
    (11, 31): ["classical"],

    # Test 12
    (12, 3): ["molten zinc", "milten zinc"],
    (12, 23): ["reschedule", "rechedule"],

    # Test 13
    (13, 10): ["wealthy people", "wealth people"],
    (13, 13): ["tiled roofs", "titled roofs"],

    # Test 14
    (14, 36): ["aisles", "ailes"],

    # Test 15
    (15, 37): ["colloquial terminology", "colloquail terminilogy"],
    (15, 40): ["general relativity"],

    # Test 17
    (17, 38): ["racist assumptions", "racist assumption"],
    (17, 39): ["archaeological and historical", "archeological and historical"],
    (17, 40): ["inhumane behavior", "inhuman behavior"],

    # Test 18
    (18, 7): ["complex, non-repetitive", "complex, non- repetitive"],
    (18, 20): ["horizontal force", "horizontal forces"],

    # Test 19
    (19, 18): ["adventures", "adventure"],

    # Test 21
    (21, 18): ["950 degrees", "950 degress"],

    # Test 22
    (22, 24): ["1998 and 2002", "1988 and 2002"],

    # Test 23
    (23, 15): ["identical", "indentical"],
    (23, 18): ["fruit flies", "fruits flies"],
    (23, 29): ["bone", "hammer bone", "body"],

    # Test 24
    (24, 9): ["hardens", "harderns"],
    (24, 32): ["controversial", "controverial"],

    # Test 25 (Questions 5-10 correspond to option letters D, E, A, J, G, F)
    (25, 5): ["D"],
    (25, 6): ["E"],
    (25, 7): ["A"],
    (25, 8): ["J"],
    (25, 9): ["G"],
    (25, 10): ["F"],
    (25, 33): ["three cards", "3 cards"],

    # Test 26
    (26, 13): ["vicarianism", "vicarisanism"],

    # Test 27
    (27, 7): ["museology", "the new museology"],

    # Test 31
    (31, 10): ["65%", "85%"],
    (31, 22): ["shy", "being shy", "shyness"],
    (31, 25): ["partnership project", "patnership project", "network of sites"],
    (31, 26): ["Otter and brown-hare", "brown-hare", "otter"],

    # Test 32
    (32, 7): ["hundred English words", "100 words", "English words"],

    # Test 33
    (33, 3): ["highfrequency", "high-frequency", "high-frequenncy"],
    (33, 5): ["noise maps", "noise map"],
    (33, 25): ["tags", "tag"],
    (33, 26): ["protective equipment", "protective equiment"],

    # Test 34
    (34, 11): ["mountain air", "dry mountain air", "air"]
}

# Real answer keys for Test 20 (publisher printed duplicate of Test 19)
TEST_20_KEYS = {
    1: "A", 2: "D", 3: "C", 4: "B", 5: "A",
    6: "C", 7: "D", 8: "A", 9: "B",
    10: ["tourism", "travel", "natural", "resort"],
    11: ["educational", "educational tour"],
    12: ["tropical forests", "forests"],
    13: ["illegal hunting", "hunting", "poaching"],
    14: "C", 15: "D", 16: "B", 17: "A",
    18: ["memory"],
    19: ["psychological"],
    20: ["semantic memory", "semantic"],
    21: ["episodic memory", "episodic"],
    22: ["algebra"],
    23: ["vocabulary", "Spanish vocabulary"],
    24: "E", 25: "B", 26: "A", 27: "C",
    28: ["68 seconds"],
    29: ["complex distinction", "distinction"],
    30: ["breathing"],
    31: ["stretching"],
    32: ["brain", "brain damage"],
    33: "E", 34: "B", 35: "F", 36: "D", 37: "H",
    38: "NOT GIVEN", 39: "TRUE", 40: "FALSE"
}

# Real answer keys for Test 21 Questions 1-13 (publisher printed shifted roman headings)
TEST_21_S1_KEYS = {
    1: "B", 2: "D", 3: "C", 4: "C", 5: "A",
    6: ["2-3 seconds", "3 seconds", "2 seconds"],
    7: ["10 seconds", "ten seconds"],
    8: ["100 and 120", "100-120", "100 to 120"],
    9: ["200", "200 w.p.m."],
    10: "A", 11: "B", 12: "C", 13: "D"
}

print("Loaded patch definitions.")
