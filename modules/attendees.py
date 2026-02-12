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


def get_team_members(team_name: str, email_book: List[Dict[str, str]]) -> List[str]:
    """Get list of email addresses for a team."""
    team_name_lower = team_name.lower()
    for team in email_book:
        if team.get('team', '').lower() == team_name_lower:
            return team.get('members', [])
    return []


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


# Load exclusion words from config
_exclusion_words_cache = None


def get_invalid_words() -> set:
    """Get the set of invalid words (from config + hardcoded)."""
    global _exclusion_words_cache
    if _exclusion_words_cache is None:
        # Merge config exclusion words with hardcoded invalid words
        config_words = load_exclusion_words()
        hardcoded_words = {
            'me', 'myself', 'my', 'we', 'us', 'our', 'ours', 'you', 'your', 'yours',
            'him', 'her', 'his', 'hers', 'them', 'their', 'theirs', 'it', 'its',
            'who', 'what', 'when', 'where', 'why', 'how', 'which', 'whom',
            'this', 'that', 'these', 'those',
            'meeting', 'call', 'chat', 'discussion', 'hangout',
            'everyone', 'all', 'team', 'group', 'anyone', 'anybody',
            'tomorrow', 'today', 'yesterday', 'morning', 'afternoon', 'evening',
            'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
            'next', 'last', 'previous', 'current',
            'email', 'text', 'message',
            'finance', 'legal', 'engineering', 'sales', 'marketing', 'hr', 'human resources',
            'support', 'operations',
            'ceo', 'cto', 'cfo', 'coo', 'vp', 'director', 'manager', 'lead',
            # Honorifics
            'sir', "ma'am", 'maam', 'madam', 'dr', 'prof', 'mr', 'mrs', 'miss',
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


def clean_name(name: str) -> str:
    """Remove honorifics and clean up a name using exclusion words from config."""
    exclusion_words = get_invalid_words()
    name_clean = name.strip()
    name_lower = name_clean.lower()
    
    # Remove exclusion words from the beginning of the name
    for word in exclusion_words:
        if name_lower.startswith(word):
            parts = name_clean.split()
            if parts[0].lower() == word:
                name_clean = ' '.join(parts[1:])
                name_lower = name_clean.lower()
                break
    
    # Remove exclusion words from the end of the name
    for word in exclusion_words:
        if name_lower.endswith(word):
            parts = name_clean.split()
            if parts[-1].lower() == word:
                name_clean = ' '.join(parts[:-1])
                break
    
    return name_clean.strip()


def extract_attendee_names(sentence: str) -> List[str]:
    """
    Extract attendee names from natural language sentence.
    
    Args:
        sentence: The natural language sentence to parse
        
    Returns:
        List of attendee names
    """
    person_names = []
    
    # Pattern for "with X" where X is one or more names
    # Note: We need to handle "John + finance + legal" where + separates attendees
    # and "tomorrow" is a time word, not part of the name
    
    # First, try to find "with X" pattern
    with_match = re.search(
        r'\bwith\s+(.+?)(?:\s+(?:about|for|at|on|today|next|this|week|evening|morning|afternoon|night|monday|tuesday|wednesday|thursday|friday|saturday|sunday|after|in|by|to|for|re)|$)',
        sentence,
        re.IGNORECASE
    )
    
    if with_match:
        attendee_str = with_match.group(1).strip()
        
        # Handle different name formats
        # Handle "+" as separator (with or without spaces)
        if '+' in attendee_str:
            # Split by + and clean up each part
            parts = re.split(r'\s*\+\s*', attendee_str)
            for part in parts:
                part = part.strip()
                # Remove any trailing time/date words and description markers
                part = re.sub(r'\s+(?:tomorrow|today|next|am|pm|at|on|re)\s*$', '', part, flags=re.IGNORECASE)
                part = re.sub(r'\s+\d{1,2}(?:am|pm)?\s*$', '', part, flags=re.IGNORECASE)  # Remove time like "6pm"
                part = clean_name(part)  # Remove honorifics
                if part and len(part) > 1 and is_valid_name(part):
                    person_names.append(part.title())
        elif re.search(r'\s+and\s+|\s+&\s+', attendee_str, re.IGNORECASE):
            names = re.split(r'\s+(?:and|&)\s+', attendee_str, flags=re.IGNORECASE)
            for name in names:
                name = name.strip()
                if ',' in name:
                    parts = re.split(r'\s*,\s*', name)
                    for part in parts:
                        part = part.strip()
                        part = clean_name(part)  # Remove honorifics
                        if part and len(part) > 1 and is_valid_name(part):
                            person_names.append(part.title())
                else:
                    name = clean_name(name)  # Remove honorifics
                    if name and len(name) > 1 and is_valid_name(name):
                        person_names.append(name.title())
        elif ',' in attendee_str:
            parts = re.split(r'\s*,\s*', attendee_str)
            for part in parts:
                part = part.strip()
                part = clean_name(part)  # Remove honorifics
                if part and len(part) > 1 and is_valid_name(part):
                    person_names.append(part.title())
        else:
            attendee_str = clean_name(attendee_str)  # Remove honorifics
            if attendee_str and len(attendee_str) > 1 and is_valid_name(attendee_str):
                person_names.append(attendee_str.title())
    
    # Filter out common non-name words
    person_names = [name for name in person_names if name.lower() not in ['me', 'and', 'or', 'everyone', 'all']]
    person_names = [name for name in person_names if ',' not in name]
    
    return person_names


def extract_attendee_emails(sentence: str) -> List[str]:
    """
    Extract email addresses directly mentioned in the sentence.
    
    Args:
        sentence: The natural language sentence to parse
        
    Returns:
        List of email addresses found in the sentence
    """
    # Pattern to match email addresses in text
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, sentence)
    return emails


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
            # Look up individual in email book
            email = None
            for entry in email_book:
                if entry.get('name', '').lower() == person_name_lower:
                    email = entry.get('email')
                    break
                # Also check if name is in email (e.g., "John Doe" matches "john.doe@example.com")
                email_addr = entry.get('email', '')
                if person_name_lower in email_addr.lower().replace('@example.com', '').replace('.', ' '):
                    email = entry.get('email')
                    break
            
            if email:
                attendees.append({"email": email})
            else:
                # Generate fallback email
                fallback = person_name.lower().replace(" ", ".") + "@example.com"
                if {"email": fallback} not in attendees:
                    attendees.append({"email": fallback})
    
    return attendees


def extract_additional_attendees(sentence: str) -> List[str]:
    """
    Extract additional attendees from patterns like "+ John" or "invite John".
    
    Args:
        sentence: The natural language sentence to parse
        
    Returns:
        List of additional attendee names
    """
    additional = []
    
    # Pattern for "+ Name" or "+ invite Name"
    invite_match = re.search(r'\+\s*(?:invite\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', sentence)
    if invite_match:
        additional.append(invite_match.group(1))
    
    return additional


if __name__ == "__main__":
    # Test the module
    test_sentences = [
        "Meeting with John",
        "Meeting with John and Jane",
        "Meeting with John, Jane, and Bob",
        "Call with John + Jane + Bob",
        "Chat with the team",
        "Sync with engineering team",
        "1:1 with John",
        "Have a meeting with Bob tomorrow",
        "create a meeting with John + finance + legal tomorrow 6pm re term sheet",
        "create a meeting with john123@gmail.com",
        "schedule a call with john123@gmail.com and jane@example.com tomorrow",
        "fix a meeting with rajit sir at 4 pm on 6th for 42 min",
    ]
    
    for sentence in test_sentences:
        print(f"\nSentence: {sentence}")
        names = extract_attendee_names(sentence)
        emails = extract_attendee_emails(sentence)
        print(f"Names: {names}")
        print(f"Emails: {emails}")
        attendees = extract_attendees(sentence)
        print(f"Attendees: {attendees}")
