"""
Meeting Attendees Extraction Module
Extracts meeting attendees from natural language sentences.
"""

import re
from typing import List, Dict, Optional


def load_email_book() -> List[Dict[str, str]]:
    """Load email book from config file."""
    import json
    import os
    email_file = os.path.join(os.path.dirname(__file__), '..', 'config', 'email.json')
    try:
        with open(email_file, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def load_names_database() -> Dict:
    """Load names database from config file."""
    import json
    import os
    names_file = os.path.join(os.path.dirname(__file__), '..', 'config', 'names.json')
    try:
        with open(names_file, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"names": []}


def load_teams() -> Dict[str, Dict]:
    """Load teams from config file."""
    import json
    import os
    teams_file = os.path.join(os.path.dirname(__file__), '..', 'config', 'teams.json')
    try:
        with open(teams_file, 'r') as f:
            data = json.load(f)
            return data.get('teams', {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def get_team_members(team_name: str, email_book: List[Dict[str, str]] = None) -> List[str]:
    """Get list of email addresses for a team."""
    teams = load_teams()
    team_name_lower = team_name.lower().strip()
    
    for team_key, team_data in teams.items():
        team_name = team_data.get('team', team_key)
        aliases = team_data.get('aliases', [])
        
        if (team_name_lower == team_name.lower() or 
            team_name_lower in [a.lower() for a in aliases]):
            return team_data.get('members', [])
    
    if email_book:
        for team in email_book:
            if team.get('team', '').lower() == team_name_lower:
                return team.get('members', [])
    
    return []


def extract_team_names(sentence: str) -> List[str]:
    """Extract team names from natural language sentence."""
    teams = load_teams()
    sentence_lower = sentence.lower()
    found_teams = []
    
    team_patterns = [
        r'\bwith\s+(.+?)\s+team\b',
        r'\bwith\s+(.+?)\s+team\s+(?:members|colleagues|people)?\b',
        r'\b(.+?)\s+team\b',
    ]
    
    for pattern in team_patterns:
        matches = re.findall(pattern, sentence_lower, re.IGNORECASE)
        for match in matches:
            team_name = match.strip()
            for team_key, team_data in teams.items():
                team_name_orig = team_data.get('team', team_key)
                aliases = team_data.get('aliases', [])
                all_names = [team_name_orig.lower()] + [a.lower() for a in aliases]
                if team_name in all_names:
                    if team_name_orig not in found_teams:
                        found_teams.append(team_name_orig)
                if team_name + ' team' in all_names or team_name in all_names:
                    if team_name_orig not in found_teams:
                        found_teams.append(team_name_orig)
    
    return found_teams


def is_valid_email(email: str) -> bool:
    """Check if a string is a valid email address."""
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_pattern, email.strip()))


def load_exclusion_words() -> set:
    """Load exclusion words from config file."""
    import json
    import os
    exclusion_file = os.path.join(os.path.dirname(__file__), '..', 'config', 'exclusion_words.json')
    try:
        with open(exclusion_file, 'r') as f:
            data = json.load(f)
            return set(word.lower() for word in data.get('exclusion_words', []))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


_exclusion_words_cache = None


def get_invalid_words() -> set:
    """Get the set of invalid words (from config + hardcoded)."""
    global _exclusion_words_cache
    if _exclusion_words_cache is None:
        config_words = load_exclusion_words()
        hardcoded_words = {
            'me', 'myself', 'my', 'we', 'us', 'our', 'ours', 'you', 'your', 'yours',
            'him', 'her', 'his', 'hers', 'them', 'their', 'theirs', 'it', 'its',
            'who', 'what', 'when', 'where', 'why', 'how', 'which', 'whom',
            'this', 'that', 'these', 'those',
            'meeting', 'call', 'chat', 'discussion', 'hangout',
            'everyone', 'all', 'team', 'group', 'anyone', 'anybody',
            'tomorrow', 'today', 'yesterday', 'morning', 'afternoon', 'evening',
            'next', 'last', 'previous', 'current',
            'email', 'text', 'message',
            'finance', 'legal', 'engineering', 'sales', 'marketing', 'hr', 'human resources',
            'support', 'operations',
            'ceo', 'cto', 'cfo', 'coo', 'vp', 'director', 'manager', 'lead',
            'sir', "ma'am", 'maam', 'madam', 'dr', 'prof', 'mr', 'mrs', 'miss',
            'with', 'at', 'on', 'for', 'to', 'about', 'create', 'schedule',
            '5pm', '5am', '10am', '10pm', '12pm', '12am', 'pm', 'am', 'noon', 'midnight',
        }
        _exclusion_words_cache = config_words.union(hardcoded_words)
    return _exclusion_words_cache


def is_valid_name(name: str) -> bool:
    """Check if a name is valid (not a common false positive)."""
    invalid_words = get_invalid_words()
    name_lower = name.lower().strip()
    if name_lower in invalid_words:
        return False
    return True


def extract_attendee_names(sentence: str) -> List[str]:
    """
    Extract attendee names from natural language sentence.
    
    Simple approach:
    1. Split the sentence into words
    2. Match each word against the names.json email book
    
    Args:
        sentence: The natural language sentence to parse
        
    Returns:
        List of attendee names
    """
    person_names = []
    
    # Load the names database
    names_db = load_names_database()
    names_list = names_db.get('names', [])
    
    # Create a set of all valid names (case-insensitive)
    valid_names = {}
    for name_entry in names_list:
        display_name = name_entry.get('display_name', '')
        first_name = name_entry.get('first_name', '')
        email = name_entry.get('email', '')
        if display_name:
            valid_names[display_name.lower()] = {'name': display_name, 'email': email}
        if first_name and first_name != display_name:
            valid_names[first_name.lower()] = {'name': first_name, 'email': email}
    
    # Also load from email.json
    email_book = load_email_book()
    for entry in email_book:
        name = entry.get('name', '')
        email = entry.get('email', '')
        if name:
            name_lower = name.lower()
            if name_lower not in valid_names:
                valid_names[name_lower] = {'name': name, 'email': email}
    
    # Split sentence into words and check each word against valid names
    words = re.findall(r'\b\w+\b', sentence)
    
    # Check each word in the sentence against valid names
    for word in words:
        word_lower = word.lower()
        if word_lower in valid_names:
            name_info = valid_names[word_lower]
            # Avoid duplicates
            if name_info['name'] not in person_names:
                person_names.append(name_info['name'])
    
    # Filter out common non-name words
    person_names = [name for name in person_names if name.lower() not in ['me', 'and', 'or', 'everyone', 'all']]
    person_names = [name for name in person_names if ',' not in name]
    
    return person_names


def extract_attendee_emails(sentence: str) -> List[str]:
    """Extract email addresses directly mentioned in the sentence."""
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, sentence)
    return emails


def extract_team_attendees(sentence: str) -> List[Dict[str, str]]:
    """Extract team attendees from sentence and return as attendee dicts."""
    team_names = extract_team_names(sentence)
    attendees = []
    
    for team_name in team_names:
        members = get_team_members(team_name)
        for member_email in members:
            if {"email": member_email} not in attendees:
                attendees.append({"email": member_email})
    
    return attendees


def extract_attendees(sentence: str, email_book: List[Dict[str, str]] = None) -> List[Dict[str, str]]:
    """
    Extract complete attendee information from sentence.
    
    Args:
        sentence: The natural language sentence to parse
        email_book: Optional email book for attendee lookup
        
    Returns:
        List of attendee dictionaries with email
    """
    if email_book is None:
        email_book = load_email_book()
    
    # First, extract any email addresses directly mentioned
    direct_emails = extract_attendee_emails(sentence)
    
    # Then, extract attendee names for lookup
    person_names = extract_attendee_names(sentence)
    
    # Also extract team attendees explicitly
    team_attendees = extract_team_attendees(sentence)
    
    attendees = []
    
    # Add direct email addresses first
    for email in direct_emails:
        if {"email": email} not in attendees:
            attendees.append({"email": email})
    
    # Process names for lookup in email book
    for person_name in person_names:
        person_name_lower = person_name.lower()
        
        # Skip if this person name looks like an email (already processed)
        if is_valid_email(person_name_lower):
            continue
        
        # Check if it's a team
        team_members = get_team_members(person_name, email_book)
        if team_members:
            for member_email in team_members:
                if {"email": member_email} not in attendees:
                    attendees.append({"email": member_email})
        else:
            # Look up in email_book
            found = False
            for entry in email_book:
                entry_name = entry.get('name', '')
                entry_email = entry.get('email', '')
                
                if (entry_name.lower() == person_name_lower or 
                    entry.get('first_name', '').lower() == person_name_lower):
                    if {"email": entry_email} not in attendees:
                        attendees.append({"email": entry_email})
                    found = True
                    break
            
            # If not found in email_book, don't create a fake email
            if not found:
                print(f"DEBUG: Name '{person_name}' not found in email book, skipping...")
    
    # Add team attendees
    for team_attendee in team_attendees:
        if team_attendee not in attendees:
            attendees.append(team_attendee)
    
    return attendees
