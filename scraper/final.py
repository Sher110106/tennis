import re
import csv
import os


# Helper function to generate player abbreviation
def get_abbreviation(full_name):
    parts = full_name.strip().split()
    return f"{parts[0][0]}. {parts[-1]}" if parts else ""


# Helper function to clean strings for comparison
def clean_string(s):
    return ''.join(s.split()).upper()


# Extract year and gender from the input text
def extract_year_and_gender(text):
    lines = text.splitlines()
    year, gender = None, None
    for line in lines[:5]:
        if not year and (m := re.search(r'\b\d{4}\b', line)):
            year = m.group(0)
        if not gender:
            gender = "M" if "Gentlemen's" in line else "W" if "Ladies'" in line else None
        if year and gender:
            break
    if not year or not gender:
        raise ValueError("Year or gender not found")
    return year, gender


# Create pairs of players for matches
def create_match_pairs(player_list):
    return [(player_list[i], player_list[i + 1]) for i in range(0, len(player_list) - 1, 2)]


# Updated match_player function to handle names correctly with fallback to last name only
def match_player(winner_abbr, player, fallback_to_last_name=True):
    # Remove seeding from abbreviation (e.g., [1])
    winner_abbr = re.sub(r'\s*\[\d+\]', '', winner_abbr).strip()
    parts = winner_abbr.split()

    # Split into initials and last name
    if len(parts) >= 2:
        initials_str = ' '.join(parts[:-1])  # Everything before the last word
        last_name = parts[-1]  # Last word as the last name
    else:
        initials_str = ''
        last_name = parts[0] if parts else ''

    # Process winner's initials
    initials_str = initials_str.replace('.', '').upper()
    winner_initials = []
    for part in initials_str.split():
        if '-' in part:
            winner_initials.extend(p[0] for p in part.split('-') if p)
        else:
            winner_initials.append(part[0])

    # Process player's full name
    player_parts = player["name"].split()
    if len(player_parts) >= 2:
        player_last_name = player_parts[-1]  # Last word as the last name
        player_first_names = player_parts[:-1]  # All preceding words as first names
    else:
        player_last_name = player_parts[0] if player_parts else ''
        player_first_names = []

    # Extract player's initials from first names
    player_initials = []
    for fn in player_first_names:
        if '-' in fn:
            player_initials.extend(p[0].upper() for p in fn.split('-') if p)
        else:
            player_initials.append(fn[0].upper())

    # Match last name and initials
    last_name_match = clean_string(last_name) == clean_string(player_last_name)
    initials_match = all(i in player_initials for i in winner_initials)

    # Return True if last names match and initials are a subset or single initial matches
    if last_name_match:
        if initials_match or (len(winner_initials) == 1 and len(player_initials) >= 1):
            return True
        
        # Fallback to last name only if requested
        if fallback_to_last_name:
            return True
            
    return False


# Parse round results
def parse_round_results(section_text):
    lines = [line.strip() for line in section_text.splitlines() if line.strip()]
    has_score_lines = any(line.startswith('.') for line in lines)
    results = []

    if has_score_lines:
        # Two-line format parsing (unchanged)
        i = 0
        while i < len(lines) - 1:
            if not lines[i].startswith('.') and lines[i + 1].startswith('.'):
                winner_abbr = lines[i].strip()
                score_line = lines[i + 1].strip()
                sets = []
                if re.search(r'\d+/\d+', score_line):
                    for sp in score_line.split():
                        if m := re.search(r'(\d+)/(\d+)', sp):
                            sets.append((m.group(1), m.group(2)))
                elif "retired" in score_line.lower():
                    for sp in re.findall(r'(\d+/\d+)', score_line):
                        w_score, l_score = sp.split("/")
                        sets.append((w_score, l_score))
                    sets.append(("retired",))
                elif "wo." in score_line.lower() or "def" in score_line.lower():
                    sets = []
                else:
                    sets = []
                results.append({"winner_abbr": winner_abbr, "sets": sets})
                i += 2
            else:
                i += 1
    else:
        # Updated regex for single-line format
        score_pattern = re.compile(r'^(.+?)\s*\.{2,}\s*(.*)')
        for line in lines:
            if m := score_pattern.search(line):
                winner_abbr = m.group(1).strip()  # e.g., "V. Kutuzova [1]"
                score_str = m.group(2).strip()    # e.g., "3/6 6/3 6/4"
                sets = []
                score_lower = score_str.lower()
                if "retired" in score_lower:
                    for sp in re.findall(r'(\d+/\d+)', score_str):
                        w_score, l_score = sp.split("/")
                        sets.append((w_score, l_score))
                    sets.append(("retired",))
                elif "wo." in score_lower or "def" in score_lower:
                    sets = []
                else:
                    for sp in score_str.split():
                        if m := re.search(r'(\d+)/(\d+)', sp):
                            sets.append((m.group(1), m.group(2)))
                results.append({"winner_abbr": winner_abbr, "sets": sets})

    print(f"Parsed {len(results)} results")
    return results

# Extract winners from the next round
def extract_winners_from_next_round(section_text):
    return [line.strip() for line in section_text.splitlines() if line.strip() and line[0].isalpha()]


# Main processing
input_text = """
The Championships 2010
Qualifying Ladies' Singles
First Round
1. Kaia Kanepi [1].................................................................. (EST)
2. Olga Savchuk..................................................................... (UKR)
3. Elena Bovina.......................................................................(RUS)
4. Mandy Minella..................................................................... (LUX)
5. Arina Rodionova................................................................. (RUS)
6. Ekaterina Dzehalevich.........................................................(BLR)
7. Ajla Tomljanovic................................................................. (CRO)
8. Kristina Kucova [24]......................................................... (SVK)
9. Johanna Jenny Larsson [2].............................................(SWE)
10. Sesil Karatantcheva............................................................ (KAZ)
11. Nuria Llagostera Vives........................................................(ESP)
12. Darya Kustova.....................................................................(BLR)
13. Xinyun Han.........................................................................(CHN)
14. Julia Schruff........................................................................(GER)
15. Lauren Riley Albanese........................................................(USA)
16. Vesna Manasieva [15].......................................................(RUS)
17. Ksenia Pervak [3]..............................................................(RUS)
18. Alexandra Panova.............................................................. (RUS)
19. Romina Sarina Oprandi........................................................ (ITA)
20. Aniko Kapros...................................................................... (HUN)
21. Ekaterina Ivanova...............................................................(RUS)
22. Katalin Marosi.....................................................................(HUN)
23. Shannon Maree Golds........................................................(AUS)
24. Stephanie Cohen-Aloro [23].............................................(FRA)
25. Bethanie Mattek-Sands [4]...............................................(USA)
26. Iryna Kuryanovich................................................................(BLR)
27. Nina Bratchikova.................................................................(RUS)
28. Elena Chalova.................................................................... (RUS)
29. Julie Ditty............................................................................ (USA)
30. Margalita Chakhnashvili..................................................... (GEO)
31. Melanie Klaffner.................................................................. (AUT)
32. Jelena Dokic [21]...............................................................(AUS)
33. Shuai Zhang [5].................................................................(CHN)
34. Anna Tatishvili....................................................................(GEO)
35. Julia Cohen.........................................................................(USA)
36. Severine Beltrame...............................................................(FRA)
(WC) 37. Emily Webley-Smith........................................................... (GBR)
(WC) 38. Marina Erakovic...................................................................(NZL)
(WC) 39. Lucy Brown.........................................................................(GBR)
40. Shenay Perry [17]..............................................................(USA)
41. Simona Halep [6].............................................................. (ROU)
42. Yulia Fedossova..................................................................(FRA)
43. Anastasiya Yakimova..........................................................(BLR)
44. Rebecca Marino..................................................................(CAN)
45. Misaki Doi............................................................................(JPN)
46. Ivana Lisjak........................................................................ (CRO)
47. Corinna Dentoni....................................................................(ITA)
48. Lilia Osterloh [18]..............................................................(USA)
49. Evgeniya Rodina [7]......................................................... (RUS)
50. Laura Pous Tio....................................................................(ESP)
51. Beatriz Garcia-Vidagany..................................................... (ESP)
52. Olivia Sanchez.................................................................... (FRA)
53. Ksenia Palkina.................................................................... (KGZ)
54. Madison Brengle.................................................................(USA)
55. Irina Buryachok...................................................................(UKR)
56. Greta Arn [20]....................................................................(HUN)
57. Patricia Mayr [8]................................................................ (AUT)
58. Eva Birnerova......................................................................(CZE)
59. Mirjana Lucic...................................................................... (CRO)
(WC) 60. Anna Smith.........................................................................(GBR)
61. Zuzana Ondraskova............................................................(CZE)
62. Rika Fujiwara.......................................................................(JPN)
63. Neuza Silva........................................................................ (POR)
64. Michaella Krajicek [13]..................................................... (NED)
65. Sophie Ferguson [9]......................................................... (AUS)
66. Kurumi Nara........................................................................ (JPN)
(WC) 67. Tamira Paszek.................................................................... (AUT)
68. Irina Begu...........................................................................(ROU)
69. Nikola Hofmanova...............................................................(AUT)
(WC) 70. Naomi Broady.....................................................................(GBR)
71. Eloisa Compostizo De Andres............................................ (ESP)
72. Stephanie Dubois [14]......................................................(CAN)
73. Ekaterina Bychkova [10].................................................. (RUS)
74. Olivia Rogowska................................................................. (AUS)
75. Junri Namigata.................................................................... (JPN)
76. Karolina Pliskova.................................................................(CZE)
(WC) 77. Jocelyn Rae........................................................................(GBR)
78. Monica Niculescu............................................................... (ROU)
79. Vitalia Diatchenko...............................................................(RUS)
80. Kathrin Woerle [19]...........................................................(GER)
(Alt) 81. Mona Barthel...................................................................... (GER)
82. Anna Floris............................................................................(ITA)
(WC) 83. Lisa Whybourn....................................................................(GBR)
84. Sally Peers..........................................................................(AUS)
85. Naomi Cavaday..................................................................(GBR)
86. Lesya Tsurenko.................................................................. (UKR)
87. Oksana Kalashnikova.........................................................(GEO)
88. Andrea Hlavackova [22]....................................................(CZE)
89. Masa Zec Peskiric [12]......................................................(SLO)
90. Catalina Castano................................................................ (COL)
91. Eleni Daniilidou...................................................................(GRE)
92. Heidi El Tabakh.................................................................. (CAN)
93. Maria Irigoyen.....................................................................(ARG)
94. Yi-Miao Zhou...................................................................... (CHN)
95. Silvia Soler Espinosa.......................................................... (ESP)
96. Anastasia Pivovarova [16]............................................... (RUS)
Second Round
K. Kanepi [1]..............................................6/1 7/5
E. Bovina............................................ 4/6 6/4 11/9
E. Dzehalevich............................................6/0 6/0
A. Tomljanovic...................................... 1/6 6/4 6/1
S. Karatantcheva.................................. 4/6 6/3 6/4
N. Llagostera Vives.................................... 6/2 6/1
X. Han...................................................5/7 7/5 8/6
V. Manasieva [15]......................................6/2 6/1
K. Pervak [3]..............................................6/2 7/5
R. Oprandi.................................................. 6/1 6/1
E. Ivanova...................................................6/1 6/4
S. Golds................................................. 7/6(3) 6/4
B. Mattek-Sands [4].................................. 6/2 6/1
N. Bratchikova........................................7/6(2) 6/1
J. Ditty.........................................................6/4 6/3
J. Dokic [21].............................................. 6/2 6/1
S. Zhang [5].....................................6/1 6/7(2) 6/2
S. Beltrame............................................ 6/3 7/6(4)
M. Erakovic.................................. 6/7(5) 7/6(6) 6/3
S. Perry [17]...............................................6/2 7/5
S. Halep [6]................................. 6/7(8) 7/6(2) 6/2
A. Yakimova........................................... 6/4 7/6(3)
M. Doi................................................... 4/6 7/5 8/6
C. Dentoni.............................................6/4 2/6 6/4
E. Rodina [7]..............................................6/4 6/2
B. Garcia-Vidagany.......................... 4/6 7/6(9) 6/3
M. Brengle.................................................. 6/2 6/1
G. Arn [20]................................................. 6/2 6/4
E. Birnerova................................................6/2 6/3
M. Lucic...................................................... 6/4 6/2
Z. Ondraskova...................................... 4/6 6/3 6/0
M. Krajicek [13]......................................... 6/1 6/3
K. Nara................................................. 3/6 6/3 6/2
T. Paszek....................................................6/4 6/2
N. Hofmanova.............................................6/4 6/4
S. Dubois [14]............................................6/1 6/1
E. Bychkova [10].................................3/6 6/2 6/3
J. Namigata...................................... 6/2 4/6 14/12
M. Niculescu............................................... 6/3 6/4
V. Diatchenko............................................. 6/2 6/3
A. Floris................................................ 7/5 3/6 6/2
L. Whybourn...........................................6/4 7/6(3)
N. Cavaday...........................................6/2 3/6 6/3
A. Hlavackova [22]..............................7/5 4/6 6/3
M. Zec Peskiric [12].................................. 7/5 6/2
E. Daniilidou........................................... 7/6(3) 6/3
M. Irigoyen...................................3/6 6/2 4/1 Ret'd
A. Pivovarova [16].................................... 6/1 6/3
Third Round
K. Kanepi [1]
.............................................6/1 6/2
A. Tomljanovic
.............................................6/4 6/3
N. Llagostera Vives
.......................................6/3 2/6 6/3
V. Manasieva [15]
.............................................6/2 6/3
R. Oprandi
.............................................6/3 6/4
E. Ivanova
.............................................6/2 6/2
B. Mattek-Sands [4]
.......................................6/3 0/6 6/2
J. Ditty
.......................................5/7 7/5 6/2
S. Beltrame
.............................................6/0 6/2
S. Perry [17]
.............................................6/4 6/2
A. Yakimova
.............................................6/4 6/1
M. Doi
.............................................6/4 6/2
B. Garcia-Vidagany
.............................................6/4 6/2
G. Arn [20]
.........................................6/1 7/6(3)
M. Lucic
.............................................6/1 7/5
M. Krajicek [13]
.............................................6/2 6/3
K. Nara
.............................................7/5 6/4
S. Dubois [14]
.........................................7/6(4) 6/4
J. Namigata
.......................................3/6 6/4 6/4
M. Niculescu
.............................................7/5 6/2
L. Whybourn
.............................................6/1 6/4
A. Hlavackova [22]
.............................................6/1 6/2
E. Daniilidou
.............................................6/2 6/2
A. Pivovarova [16]
.............................................6/2 6/4
Qualifiers
K. Kanepi [1]
.............................................6/1 6/2
N. Llagostera Vives
.........................................7/6(4) 6/4
R. Oprandi
.......................................6/3 3/6 6/4
B. Mattek-Sands [4]
.......................................6/1 4/6 6/4
S. Perry [17]
.......................................3/6 6/4 6/3
A. Yakimova
.......................................2/6 6/4 6/4
G. Arn [20]
.......................................5/7 6/3 6/2
M. Lucic
.............................................6/3 6/2
K. Nara
.........................................7/6(2) 6/4
M. Niculescu
.............................................6/4 6/0
A. Hlavackova [22]
.............................................6/1 6/2
E. Daniilidou
.............................................6/0 6/0
This material is the copyright of the All England Lawn Tennis Club and may not be reproduced in any form without written permission.
"""
year, gender = extract_year_and_gender(input_text)
round_splits = re.split(r'(First Round|Second Round|Third Round|Qualifiers)', input_text)
round_data = {}
order = []
for i in range(1, len(round_splits), 2):
    round_name = round_splits[i].strip()
    round_data[round_name] = round_splits[i + 1].strip()
    order.append(round_name)

# Updated regex to handle (WC) and (Alt) prefixes
first_round_pattern = re.compile(
    r'^(?P<prefix>\((WC|Alt)\))?\s*(?P<num>\d+)\.\s+(?P<name>[^\[\.\n]+)(?:\s*\[(?P<seeding>\d+)\])?.*?\(?\s*(?P<country>[A-Z]{3})\)?',
    re.IGNORECASE
)

# Parse First Round players
players = []
for line in round_data["First Round"].splitlines():
    if line.strip() and (match := first_round_pattern.search(line.strip())):
        # Strip (WC) or (Alt) from the name if present
        name = match.group("name").strip()
        prefix = match.group("prefix")
        # Only set "wild" to "1" for (WC), ignore (Alt)
        wild = "1" if prefix == "(WC)" else ""
        players.append({
            "num": int(match.group("num")),
            "name": name,
            "seeding": match.group("seeding") or "",
            "country": match.group("country").strip(),
            "wild": wild,
            "abbrev": get_abbreviation(name)
        })
players.sort(key=lambda x: x["num"])
print(f"Number of players parsed: {len(players)}")

# Process matches
match_result_sections = [r for r in order if r != "First Round"]
round_mapping = {"Second Round": "R128", "Third Round": "R64", "Qualifiers": "R32"}
round_num_mapping = {"Second Round": "128", "Third Round": "64", "Qualifiers": "32"}
match_rows = []
current_matches = create_match_pairs(players)

for i, section in enumerate(match_result_sections):
    round_label = round_mapping.get(section, f"R?{section}")
    round_num = round_num_mapping.get(section, "?")
    section_text = round_data.get(section, "")
    results = parse_round_results(section_text)
    next_winners = extract_winners_from_next_round(round_data.get(match_result_sections[i + 1], "")) if i + 1 < len(
        match_result_sections) else []
    expected_matches = len(current_matches)
    if len(results) != expected_matches:
        print(
            f"Warning: Number of results ({len(results)}) in {section} does not match expected matches ({expected_matches})")
    winners = []
    match_num = 1
    for j, (p1, p2) in enumerate(current_matches[:len(results)]):
        result = results[j]
        winner_abbr = result["winner_abbr"]
        sets = result["sets"]
        
        # First try with strict matching (no fallback)
        if match_player(winner_abbr, p1, fallback_to_last_name=False):
            winner, loser = p1, p2
            print(f"{section} Match {j + 1}: {winner['name']} beat {loser['name']}")
        elif match_player(winner_abbr, p2, fallback_to_last_name=False):
            winner, loser = p2, p1
            print(f"{section} Match {j + 1}: {winner['name']} beat {loser['name']}")
        else:
            # If strict matching failed, try with fallback to last name only
            if match_player(winner_abbr, p1, fallback_to_last_name=True):
                winner, loser = p1, p2
                print(f"{section} Match {j + 1}: {winner['name']} beat {loser['name']} (matched by last name)")
            elif match_player(winner_abbr, p2, fallback_to_last_name=True):
                winner, loser = p2, p1
                print(f"{section} Match {j + 1}: {winner['name']} beat {loser['name']} (matched by last name)")
            else:
                # If even fallback matching fails, try next round information
                print(f"{section} Match {j + 1}: Cannot match '{winner_abbr}' to {p1['name']} or {p2['name']}")
                if j < len(next_winners) and next_winners[j]:
                    if match_player(next_winners[j], p1):
                        winner, loser = p1, p2
                        print(f"{section} Match {j + 1}: {winner['name']} beat {loser['name']} (via next round)")
                    elif match_player(next_winners[j], p2):
                        winner, loser = p2, p1
                        print(f"{section} Match {j + 1}: {winner['name']} beat {loser['name']} (via next round)")
                    else:
                        winner, loser = p1, p2
                        print(f"{section} Match {j + 1}: Fallback to {winner['name']} (unmatched '{next_winners[j]}')")
                else:
                    winner, loser = p1, p2
                    print(f"{section} Match {j + 1}: Fallback to {winner['name']} (no next round info)")
        
        # Extract set scores
        w_scores = [sets[k][0] if k < len(sets) else "" for k in range(5)]
        l_scores = [sets[k][1] if k < len(sets) else "" for k in range(5)]
        
        # Calculate set participation (1 if played, 0 if not)
        w_set_participation = [1 if w_scores[k] and w_scores[k] != "retired" else 0 for k in range(5)]
        l_set_participation = [1 if l_scores[k] and (len(sets[k]) > 1 if k < len(sets) else False) else 0 for k in range(5)]
        
        # Calculate total sets played
        w_set = sum(w_set_participation)
        l_set = sum(l_set_participation)
        
        match_id_str = f"{year}_{gender}_{round_num}_{match_num}"
        match_rows.append([
            match_id_str, round_label, winner["name"], winner["seeding"], winner["wild"], winner["country"],
            *w_scores, *w_set_participation, w_set,
            loser["name"], loser["seeding"], loser["wild"], loser["country"],
            *l_scores, *l_set_participation, l_set
        ])
        match_num += 1
        winners.append(winner)
    current_matches = create_match_pairs(winners)

# Write to CSV
if not os.path.exists("output.csv"):
    with open("output.csv", "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Match Id", "Round", "W_name", "W_seed", "W_Wc", "W_country",
                         "W_set1", "W_set2", "W_set3", "W_set4", "W_set5",
                         "W_set1_p", "W_set2_p", "W_set3_p", "W_set4_p", "W_set5_p", "W_set",
                         "L_name", "L_seed", "L_Wc", "L_country",
                         "L_set1", "L_set2", "L_set3", "L_set4", "L_set5",
                         "L_set1_p", "L_set2_p", "L_set3_p", "L_set4_p", "L_set5_p", "L_set"])
with open("output.csv", "a", newline="") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerows(match_rows)

print("CSV file 'output.csv' has been updated with set participation and total sets columns.")