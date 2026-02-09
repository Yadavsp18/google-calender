"""
Meeting Link/URL Extraction Module
Extracts meeting link URLs (Google Meet, Zoom, etc.) from natural language sentences.
"""

import re
from typing import Tuple, Optional


def extract_meeting_link(sentence: str) -> Tuple[Optional[str], bool]:
    """
    Extract meeting link from natural language sentence.
    
    Args:
        sentence: The natural language sentence
        
    Returns:
        Tuple of (link_url, is_auto_generated)
        - link_url: The extracted URL or None for auto-generation
        - is_auto_generated: True if link should be auto-generated, False if provided
    """
    text = sentence.lower().strip()
    
    # Google Meet URL patterns (with or without http)
    meet_link_patterns = [
        r'(https?://)?(meet\.google\.com/)[a-zA-Z0-9_-]+',
        r'(https?://)?([a-z]{2,3}-meet\.google\.com/)[a-zA-Z0-9_-]+',
    ]
    
    for pattern in meet_link_patterns:
        meet_link_match = re.search(pattern, text, re.IGNORECASE)
        if meet_link_match:
            link = meet_link_match.group(0)
            if not link.startswith('http'):
                link = 'https://' + link
            return link, False  # Use provided link, don't auto-generate
    
    # Zoom URL patterns
    zoom_link_pattern = r'(https?://)?(zoom\.us/j/|zoom\.us/meet/)[0-9]+'
    zoom_match = re.search(zoom_link_pattern, text, re.IGNORECASE)
    if zoom_match:
        link = zoom_match.group(0)
        if not link.startswith('http'):
            link = 'https://' + link
        return link, False
    
    # Teams URL patterns
    teams_pattern = r'(https?://)?(teams\.microsoft\.com/l/meetup-join/)[a-zA-Z0-9_%/-]+'
    teams_match = re.search(teams_pattern, text, re.IGNORECASE)
    if teams_match:
        link = teams_match.group(0)
        if not link.startswith('http'):
            link = 'https://' + link
        return link, False
    
    # Generic URL pattern for any https/http link
    generic_url_pattern = r'https?://[a-zA-Z0-9][-a-zA-Z0-9]*(\.[a-zA-Z0-9][-a-zA-Z0-9]*)+(/[^\s]*)?'
    generic_match = re.search(generic_url_pattern, text, re.IGNORECASE)
    if generic_match:
        return generic_match.group(0), False
    
    # Check for "usual" or "default" link
    if re.search(r'\busual\b', text) or re.search(r'\bdefault\b', text):
        return 'Online', False
    
    # No specific link found - return for auto-generation
    return None, True


def is_meeting_link_provided(sentence: str) -> bool:
    """
    Check if a meeting link is explicitly provided in the sentence.
    
    Args:
        sentence: The natural language sentence
        
    Returns:
        True if a meeting link is provided
    """
    text = sentence.lower().strip()
    
    link_patterns = [
        r'meet\.google\.com',
        r'zoom\.us',
        r'teams\.microsoft\.com',
        r'https?://',
    ]
    
    for pattern in link_patterns:
        if re.search(pattern, text):
            return True
    
    return False


def extract_custom_link(sentence: str) -> Optional[str]:
    """
    Extract any custom URL from the sentence.
    
    Args:
        sentence: The natural language sentence
        
    Returns:
        The extracted URL or None
    """
    text = sentence.lower().strip()
    
    # Generic URL pattern
    url_pattern = r'(https?://)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(/[a-zA-Z0-9-._~:?#[\]@!$&\'()*+,;=]*)?'
    url_match = re.search(url_pattern, text, re.IGNORECASE)
    
    if url_match:
        url = url_match.group(0)
        if not url.startswith('http'):
            url = 'https://' + url
        return url
    
    return None
