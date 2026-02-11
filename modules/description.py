"""
Meeting Description Extraction Module
Extracts meeting description from natural language sentences.
"""

import re
from typing import Optional, Dict, Any

from modules.location import extract_meeting_location, format_location_for_print


def extract_meeting_description(sentence: str) -> str:
    """
    Extract meeting description from natural language sentence.
    
    Args:
        sentence: The natural language sentence
        
    Returns:
        Meeting description string
    """
    text = sentence.lower().strip()
    
    # Patterns for description extraction
    desc_patterns = [
        r'\babout\s+(.{3,})',
        r'\bregarding\s+(.{3,})',
        r'\bre\s+(.{3,})',  # Handle "re term sheet" pattern
        r'\btopic\s+(.{3,})',
        r'\bfor\s+(?:the\s+)?(?:discussion|review|update|plan)\s+(?:of\s+)?(.{3,})',
        r'\bon\s+(?:the\s+)?(?:topic|subject)\s+(?:of\s+)?(.{3,})',
        r'\bto\s+(?:discuss|talk|review|plan)\s+(.{3,})',
    ]
    
    for pattern in desc_patterns:
        try:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                desc = match.group(1).strip()
                # Clean up the description - remove trailing keywords
                trailing_pattern = r'\s+(?:at|on|tomorrow|today|with|for|next|this|week|monday|tuesday|wednesday|thursday|friday|saturday|sunday|morning|afternoon|evening|am|pm)\s*$'
                desc = re.sub(trailing_pattern, '', desc, flags=re.IGNORECASE)
                desc = re.sub(r'\s+re:\s*', ' ', desc, flags=re.IGNORECASE)
                desc = re.sub(r'\s+', ' ', desc)
                desc = desc.strip('.,;:!?')
                if len(desc) > 2:
                    return desc.capitalize()
        except re.error:
            continue
    
    return ''


def extract_meeting_agenda(sentence: str) -> str:
    """
    Extract meeting agenda from natural language sentence.
    
    Args:
        sentence: The natural language sentence
        
    Returns:
        Meeting agenda string
    """
    text = sentence.lower().strip()
    
    # Agenda patterns
    agenda_patterns = [
        r'\bagenda\s+(.{3,})',
        r'\btopics?\s+(.{3,})',
        r'\bdiscuss\s+(.{3,})',
        r'\btalk\s+about\s+(.{3,})',
        r'\bagenda:\s+(.{3,})',
        r'\btopic:\s+(.{3,})',
    ]
    
    for pattern in agenda_patterns:
        try:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                agenda = match.group(1).strip()
                trailing_pattern = r'\s+(?:at|on|tomorrow|today|with|for|next|this|week|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s*$'
                agenda = re.sub(trailing_pattern, '', agenda, flags=re.IGNORECASE)
                agenda = agenda.strip('.,;:!?')
                if len(agenda) > 2:
                    return agenda.capitalize()
        except re.error:
            continue
    
    return ''


def format_meeting_details_for_print(details: dict, sentence: str = None) -> str:
    """
    Format meeting details for printing/display.
    
    Args:
        details: Dictionary containing meeting details
        sentence: Original sentence for location extraction (optional)
        
    Returns:
        Formatted string for display
    """
    lines = []
    
    if details.get('summary'):
        lines.append(f"Title: {details['summary']}")
    
    if details.get('date'):
        lines.append(f"Date: {details['date']}")
    
    if details.get('time'):
        lines.append(f"Time: {details['time']}")
    
    if details.get('duration'):
        lines.append(f"Duration: {details['duration']}")
    
    if details.get('attendees'):
        attendees_str = ', '.join(details['attendees'])
        lines.append(f"Attendees: {attendees_str}")
    
    # Handle location - use details location or extract from sentence
    if details.get('location_info'):
        location_str = format_location_for_print(details['location_info'])
        lines.append(f"Location: {location_str}")
    elif sentence:
        location_info = extract_meeting_location(sentence)
        location_str = format_location_for_print(location_info)
        lines.append(f"Location: {location_str}")
    
    if details.get('description'):
        lines.append(f"Description: {details['description']}")
    
    if details.get('agenda'):
        lines.append(f"Agenda: {details['agenda']}")
    
    return '\n'.join(lines) if lines else 'No meeting details available'
