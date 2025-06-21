import re
import csv
import os
import sys

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
    for line in lines[:20]:  # Increased search range for better detection
        if not year and (m := re.search(r'\b(\d{4})\b', line)):
            year = m.group(1)
        if not gender:
            gender = "M" if any(male_term in line for male_term in ["Gentlemen's", "Men", "Qualifying Men"]) else \
                    "W" if any(female_term in line for female_term in ["Ladies'", "Women", "Qualifying Women"]) else None
        if year and gender:
            break
    
    if not year or not gender:
        # Try harder to find the year and gender
        filename_pattern = re.search(r'(\d{4})_QS_([MW])', '\n'.join(lines))
        if filename_pattern:
            if not year:
                year = filename_pattern.group(1)
            if not gender:
                gender = filename_pattern.group(2)
    
    if not year or not gender:
        print("WARNING: Year or gender not found in text, using defaults")
        # If still not found, use defaults based on processing
        year = year or "2000"
        gender = gender or "M"
        
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
    print(f"Parsing round results with text length: {len(section_text)}")
    lines = [line.strip() for line in section_text.splitlines() if line.strip()]
    print(f"Found {len(lines)} non-empty lines")
    
    # Log a sample of lines to help with debugging
    if lines:
        print(f"Sample lines: {lines[:3]}")
    
    # Check for various formats the results might be in
    has_score_lines = any(line.startswith('.') for line in lines)
    has_dots_format = any('..' in line for line in lines)
    
    results = []
    
    if has_score_lines:
        # Two-line format parsing
        i = 0
        while i < len(lines) - 1:
            if not lines[i].startswith('.') and lines[i + 1].startswith('.'):
                winner_abbr = lines[i].strip()
                score_line = lines[i + 1].strip()
                sets = []
                if re.search(r'\d+/\d+', score_line):
                    for score in re.finditer(r'(\d+)/(\d+)', score_line):
                        sets.append((score.group(1), score.group(2)))
                elif "retired" in score_line.lower():
                    for score in re.finditer(r'(\d+)/(\d+)', score_line):
                        sets.append((score.group(1), score.group(2)))
                    sets.append(("retired",))
                elif "wo." in score_line.lower() or "def" in score_line.lower():
                    sets = []
                else:
                    sets = []
                results.append({"winner_abbr": winner_abbr, "sets": sets})
                i += 2
            else:
                i += 1
    elif has_dots_format:
        # Single-line format with dots and scores
        for line in lines:
            if m := re.match(r'^([A-Z][\.\w\s\[\]\-]+?)\.{2,}\s*(.*?)(?:\s+[A-Z][\.\w\s\[\]\-]+\.{2,}.*)?$', line):
                winner_abbr = m.group(1).strip()
                score_str = m.group(2).strip()
                sets = []
                
                if "retired" in score_str.lower():
                    # Handle retired matches
                    for score in re.finditer(r'(\d+)/(\d+)', score_str):
                        sets.append((score.group(1), score.group(2)))
                    sets.append(("retired",))
                elif any(x in score_str.lower() for x in ["wo.", "def"]):
                    # Handle walkovers and defaults
                    sets = []
                else:
                    # Handle normal scores
                    for score in re.finditer(r'(\d+)/(\d+)', score_str):
                        sets.append((score.group(1), score.group(2)))
                
                results.append({"winner_abbr": winner_abbr, "sets": sets})
    else:
        # Try to find any format with scores
        score_pattern = re.compile(r'([A-Z][\.\w\s\[\]\-]+)\s+(\d+/\d+\s+\d+/\d+(?:\s+\d+/\d+)?)')
        for line in lines:
            if m := score_pattern.search(line):
                winner_abbr = m.group(1).strip()
                score_str = m.group(2).strip()
                sets = []
                for score in re.finditer(r'(\d+)/(\d+)', score_str):
                    sets.append((score.group(1), score.group(2)))
                if sets:
                    results.append({"winner_abbr": winner_abbr, "sets": sets})
    
    print(f"Parsed {len(results)} results")
    return results

# Extract winners from the next round
def extract_winners_from_next_round(section_text):
    winners = []
    lines = [line.strip() for line in section_text.splitlines() if line.strip()]
    
    # Try to find lines that look like winner names (start with letters, may contain [seed])
    for line in lines:
        if line.strip() and line[0].isalpha() and not line.startswith(('First', 'Second', 'Third', 'Qualifiers')):
            # Clean up the winner name (remove dots at the end if present)
            winner = re.sub(r'\.+$', '', line.strip())
            winners.append(winner)
    
    return winners

# Preprocess text to improve consistency
def preprocess_text(text):
    """Clean and normalize the text for better parsing."""
    # Replace various whitespace characters with a single space
    text = re.sub(r'\s+', ' ', text)
    
    # Ensure round headers are on their own line
    for header in ['First Round', 'Second Round', 'Third Round', 'Qualifiers']:
        text = re.sub(f'({header})', r'\n\1\n', text)
    
    # Clean up player numbers and ensure they're properly formatted
    text = re.sub(r'(\d+)\s*\.\s*', r'\1. ', text)
    
    # Clean up player seeds
    text = re.sub(r'\[\s*(\d+)\s*\]', r'[\1]', text)
    
    # Fix common OCR errors
    text = text.replace('l/', '1/').replace('O/', '0/')
    
    return text

# Main processing function
def process_tournament_text(input_text):
    # Preprocess the text
    input_text = preprocess_text(input_text)
    
    # Extract year and gender
    year, gender = extract_year_and_gender(input_text)
    print(f"Processing tournament data: Year {year}, Gender {gender}")
    
    # Split the text into rounds
    round_splits = re.split(r'(First Round|Second Round|Third Round|Qualifiers)', input_text)
    
    round_data = {}
    order = []
    
    for i in range(1, len(round_splits), 2):
        if i < len(round_splits):
            round_name = round_splits[i].strip()
            round_content = round_splits[i + 1].strip() if i + 1 < len(round_splits) else ""
            round_data[round_name] = round_content
            order.append(round_name)
    
    # Fixed regex to use 'name' group consistently
    first_round_pattern = re.compile(
        r'^(?:\((?P<prefix>WC|Alt)\))?\s*(?P<num>\d+)\.\s*(?P<name>[^\[\.\n]+)(?:\s*\[(?P<seeding>\d+)\])?.*?\(?\s*(?P<country>[A-Z]{3})\)?',
        re.MULTILINE
    )
    
    # Parse First Round players
    players = []
    if "First Round" in round_data:
        for line in round_data["First Round"].splitlines():
            if line.strip() and (match := first_round_pattern.search(line.strip())):
                name = match.group("name").strip() if match.group("name") else ""
                num = match.group("num") if match.group("num") else ""
                prefix = match.group("prefix") if match.group("prefix") else ""
                
                players.append({
                    "num": int(num) if num else 0,
                    "name": name,
                    "seeding": match.group("seeding") or "",
                    "country": match.group("country").strip() if match.group("country") else "",
                    "wild": "1" if prefix == "WC" else "",
                    "abbrev": get_abbreviation(name)
                })
    
    # Sort players by number
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
            if j >= len(results):
                print(f"Warning: Not enough results for match {j + 1}")
                continue
                
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
            l_scores = [sets[k][1] if k < len(sets) and len(sets[k]) > 1 else "" for k in range(5)]
            
            # Calculate set participation (1 if played, 0 if not)
            w_set_participation = [1 if w_scores[k] and w_scores[k] != "retired" else 0 for k in range(5)]
            l_set_participation = [1 if l_scores[k] else 0 for k in range(5)]
            
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
    
    return match_rows

# Write data to CSV
def write_to_csv(match_rows, output_file="output.csv"):
    # Check if file exists to determine if we need to write headers
    file_exists = os.path.exists(output_file) and os.path.getsize(output_file) > 0
    
    mode = 'a' if file_exists else 'w'
    with open(output_file, mode, newline="", encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(["Match Id", "Round", "W_name", "W_seed", "W_Wc", "W_country",
                             "W_set1", "W_set2", "W_set3", "W_set4", "W_set5",
                             "W_set1_p", "W_set2_p", "W_set3_p", "W_set4_p", "W_set5_p", "W_set",
                             "L_name", "L_seed", "L_Wc", "L_country",
                             "L_set1", "L_set2", "L_set3", "L_set4", "L_set5",
                             "L_set1_p", "L_set2_p", "L_set3_p", "L_set4_p", "L_set5_p", "L_set"])
        writer.writerows(match_rows)
    
    print(f"Data has been written to {output_file}")

# Main entry point
if __name__ == "__main__":
    # Check if we have input from stdin
    if not sys.stdin.isatty():
        input_text = sys.stdin.read()
        print(f"Received {len(input_text)} characters from stdin")
    else:
        # Use the sample data from the original script for testing
        print("No input from stdin, using sample data")
        from test_final import input_text
    
    # Process the input text
    match_rows = process_tournament_text(input_text)
    
    # Write to CSV
    write_to_csv(match_rows)