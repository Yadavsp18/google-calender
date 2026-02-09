"""
Meeting Attendees Extraction Module
Extracts meeting attendees from natural language sentences.
"""

import re
import json
import os
from typing import List, Dict, Any, Optional


def load_email_book() -> List[Dict[str, str]]:
    """
    Load email book from config/email.json.
    
    Returns:
        List of attendee dictionaries with name and email
    """
    email_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'email.json')
    
    if not os.path.exists(email_file):
        return []
    
    try:
        with open(email_file, 'r') as f:
            return json.load(f)
    except Exception:
        return []


def find_email_by_name(name: str, email_book: List[Dict[str, str]] = None) -> Optional[str]:
    """
    Find email address for a given name.
    
    Args:
        name: The name to search for
        email_book: Optional email book, will be loaded if not provided
        
    Returns:
        Email address or None
    """
    if email_book is None:
        email_book = load_email_book()
    
    name_lower = name.lower().strip()
    
    # Remove honorifics and titles
    honorifics = ['sir', 'madam', 'dr', 'prof', 'mr', 'mrs', 'ms', 'miss', 'mx']
    name_parts = name_lower.split()
    cleaned_parts = [p for p in name_parts if p not in honorifics]
    cleaned_name = ' '.join(cleaned_parts).strip()
    
    for entry in email_book:
        entry_name_lower = entry.get('name', '').lower()
        
        # Exact match
        if entry_name_lower == name_lower:
            return entry.get('email')
        
        # Exact match with cleaned name (without honorifics)
        if cleaned_name and entry_name_lower == cleaned_name:
            return entry.get('email')
        
        # Check if the name is contained in the entry or vice versa
        if cleaned_name in entry_name_lower or entry_name_lower in cleaned_name:
            return entry.get('email')
        
        # Also check in aliases or nicknames if available
        if 'aliases' in entry:
            for alias in entry['aliases']:
                alias_lower = alias.lower()
                if alias_lower == name_lower or alias_lower == cleaned_name:
                    return entry.get('email')
    
    return None


def extract_attendee_names(sentence: str) -> List[str]:
    """
    Extract attendee names from natural language sentence.
    
    Args:
        sentence: The natural language sentence
        
    Returns:
        List of attendee names
    """
    person_names = []
    
    # Pattern for "with X" where X is one or more names
    with_match = re.search(
        r'\bwith\s+(.+?)(?:\s+(?:about|for|at|on|tomorrow|today|next|this|week|evening|morning|afternoon|night|monday|tuesday|wednesday|thursday|friday|saturday|sunday|after|in|by|to|for)|$)',
        sentence,
        re.IGNORECASE
    )
    
    if with_match:
        attendee_str = with_match.group(1).strip()
        
        # Handle different name formats
        if ' + ' in attendee_str:
            parts = re.split(r'\s*\+\s*', attendee_str)
            for part in parts:
                part = part.strip()
                if part and len(part) > 1:
                    person_names.append(part.title())
        elif re.search(r'\s+and\s+|\s+&\s+', attendee_str, re.IGNORECASE):
            names = re.split(r'\s+(?:and|&)\s+', attendee_str, flags=re.IGNORECASE)
            for name in names:
                name = name.strip()
                if ',' in name:
                    parts = re.split(r'\s*,\s*', name)
                    for part in parts:
                        part = part.strip()
                        if part and len(part) > 1:
                            person_names.append(part.title())
                elif name and len(name) > 1:
                    person_names.append(name.title())
        elif ',' in attendee_str:
            parts = re.split(r'\s*,\s*', attendee_str)
            for part in parts:
                part = part.strip()
                if part and len(part) > 1:
                    person_names.append(part.title())
        else:
            if attendee_str and len(attendee_str) > 1:
                person_names.append(attendee_str.title())
    
    # Filter out common non-name words
    person_names = [name for name in person_names if name.lower() not in ['me', 'and', 'or', 'everyone', 'all']]
    person_names = [name for name in person_names if ',' not in name]
    
    return person_names


def extract_attendees(sentence: str, email_book: List[Dict[str, str]] = None) -> List[Dict[str, str]]:
    """
    Extract complete attendee information from sentence.
    
    Args:
        sentence: The natural language sentence
        email_book: Optional email book for email lookup
        
    Returns:
        List of attendee dictionaries with email
    """
    if email_book is None:
        email_book = load_email_book()
    
    person_names = extract_attendee_names(sentence)
    
    attendees = []
    for person_name in person_names:
        # Check if it's a team name and expand to all team members
        team_members = find_team_members(person_name, email_book)
        if team_members:
            # Add all team members
            for member_email in team_members:
                if {"email": member_email} not in attendees:
                    attendees.append({"email": member_email})
        else:
            email = find_email_by_name(person_name, email_book)
            if email:
                attendees.append({"email": email})
            else:
                # Generate fallback email
                fallback = person_name.lower().replace(" ", ".") + "@example.com"
                if {"email": fallback} not in attendees:
                    attendees.append({"email": fallback})
    
    return attendees


def find_team_members(team_name: str, email_book: List[Dict[str, str]] = None) -> Optional[List[str]]:
    """
    Find all members of a team.
    
    Args:
        team_name: The team name to search for
        email_book: Optional email book (loaded from teams.json if not provided)
        
    Returns:
        List of team member emails or None if team not found
    """
    import json
    
    team_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'teams.json')
    
    if not os.path.exists(team_file):
        return None
    
    try:
        with open(team_file, 'r') as f:
            teams_config = json.load(f)
    except Exception:
        return None
    
    teams = teams_config.get('teams', {})
    team_name_lower = team_name.lower().strip()
    
    # Check for exact team name or aliases
    for team_key, team_data in teams.items():
        if team_key.lower() == team_name_lower:
            return team_data.get('members', [])
        
        # Check aliases
        aliases = team_data.get('aliases', [])
        for alias in aliases:
            if alias.lower() == team_name_lower:
                return team_data.get('members', [])
    
    return None


def extract_additional_attendees(sentence: str) -> List[str]:
    """
    Extract additional attendees from patterns like "+ John" or "invite John".
    
    Args:
        sentence: The natural language sentence
        
    Returns:
        List of additional attendee names
    """
    additional_names = []
    
    # Pattern for "+ Name" or "+ invite Name"
    invite_match = re.search(r'\+\s*(?:invite\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', sentence)
    if invite_match:
        invite_name = invite_match.group(1).strip()
        if invite_name.lower() not in ['and', 'or', 'me', 'too', 'also']:
            additional_names.append(invite_name.title())
    
    return additional_names
