"""
Meeting Summary Extraction Module
Extracts meeting title/summary from natural language sentences.
"""

import re
from typing import Optional, List, Tuple

# Import UPDATE patterns from update_patterns module
from modules.update_patterns import UPDATE_SENTENCE_PATTERNS


# Meeting type patterns that can be combined with purpose
# Format: (pattern, meeting_type, should_combine_with_purpose)
MEETING_TYPE_PATTERNS = [
    # Meeting types that can combine with purpose: sync
    (r'\b(weekly\s*sync|team\s*sync|sync\s*up|\bsync\b)', 'Sync', True),
    # Meeting types that don't combine (standalone)
    (r'\b(1:1|one-on-one|one on one)\b', '1:1 Meeting', False),
    (r'\b(standup|sprint\s*standup|daily\s*standup)\b', 'Standup', False),
    (r'\b(status\s*update|update\s*meeting)\b', 'Status Update', False),
    (r'\b(planning\s*session|planning\s*meeting)\b', 'Planning Session', False),
    (r'\b(sprint\s+planning)\b', 'Sprint Planning', False),
    (r'\b(retro|retrospective)\b', 'Retro', False),
    (r'\b(roadmap|road\s*map)\b', 'Roadmap Review', False),
    (r'\b(kickoff|project\s*kickoff)\b', 'Kickoff', False),
    (r'\b(workshop)\b', 'Workshop', False),
    (r'\b(town\s*hall)\b', 'Town Hall', False),
    (r'\b(all-hands)\b', 'All Hands', False),
    # Meeting types with names (standalone)
    (r'\b(interview)\b', 'Interview', False),
    (r'\b(lunch)\b', 'Lunch', False),
    (r'\b(coffee|coffee\s*chat)\b', 'Coffee Chat', False),
    (r'\b(quick\s*chat|brief\s*chat)\b', 'Quick Chat', False),
    (r'\b(catch-up|catchup|catch up)\b', 'Catch-up', False),
    # Demo patterns
    (r'\b(demo|product\s*demo)\s*call\b', 'Demo Call', False),
    (r'\b(demo|product\s*demo)\b', 'Demo', False),
    # Review patterns
    (r'\b(review|code\s*review|design\s*review)\b', 'Review', False),
]


def is_update_sentence(sentence: str) -> bool:
    """
    Check if the sentence is an update/reschedule request.
    
    Args:
        sentence: The natural language sentence
        
    Returns:
        True if this is an update sentence
    """
    text = sentence.lower().strip()
    
    for pattern in UPDATE_SENTENCE_PATTERNS:
        if re.search(pattern, text):
            return True
    
    return False


def clean_title(title: str) -> str:
    """
    Clean up a title by removing trailing date/time words.
    
    Args:
        title: The extracted title
        
    Returns:
        Cleaned title
    """
    if not title:
        return title
    
    words = title.split()
    cleaned_words = []
    
    for word in words:
        # Skip words that match date/time patterns
        skip = False
        word_lower = word.lower()
        
        # Check for day names
        if word_lower in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
            skip = True
        # Check for simple words
        elif word_lower in ['tomorrow', 'today', 'next', 'this', 'on', 'at', 'in', 'afternoon', 'morning', 'evening', 'noon']:
            skip = True
        # Check for partial words (like 'o' from 'on', 'nex' from 'next')
        elif word_lower in ['o', 'nex', 'thi', 'at', 'in', 'apr', 'mar', 'may', 'feb']:
            skip = True
        # Check for time patterns (like "9:30am", "10am", etc.)
        elif re.match(r'\d{1,2}:\d{2}(?:am|pm)?', word_lower):
            skip = True
        
        if not skip:
            cleaned_words.append(word)
    
    # Reconstruct title
    cleaned = ' '.join(cleaned_words)
    
    # Additional cleanup: remove trailing prepositions
    cleaned = re.sub(r'\s+(?:on|at|in|for|to|with)$', '', cleaned, flags=re.IGNORECASE)
    
    return cleaned.strip()


def extract_attendee_names_from_sentence(sentence: str) -> List[str]:
    """
    Extract attendee names from sentence for title building.
    
    Args:
        sentence: The natural language sentence
        
    Returns:
        List of attendee names
    """
    from modules.attendees import extract_attendee_names
    return extract_attendee_names(sentence)


def extract_purpose(sentence: str) -> str:
    """
    Extract the meeting purpose/topic from the sentence.
    
    Args:
        sentence: The natural language sentence
        
    Returns:
        Extracted purpose/topic or empty string
    """
    text = sentence.lower().strip()
    
    # Purpose patterns - extract what comes after these prepositions
    # Order matters: more specific patterns first
    purpose_patterns = [
        # "re: X" - reference (before "about" because "re:" is more specific)
        (r'\bre:\s*(.{3,})', True),
        # "about X" - most common
        (r'\babout\s+(.{3,})', True),
        # "regarding X"
        (r'\bregarding\s+(.{3,})', True),
        # "to discuss X" / "to review X" / "to plan X" / "to finalize X"
        (r'\bto\s+(discuss|talk|review|plan|finalize)\s+(.{3,})', True),
        # "on X" - topic indicator
        (r'\bon\s+(?:the\s+)?(?:topic|subject)?\s*(.{3,})', True),
        # "for X" - common for purpose (after "to discuss" because it's more general)
        (r'\bfor\s+(?:the\s+)?(?:discussion|review|update|plan|meeting)?\s*(.{3,})', True),
        # "topic X"
        (r'\btopic\s+(.{3,})', True),
        # "agenda X"
        (r'\bagenda\s+(.{3,})', True),
    ]
    
    for pattern, _ in purpose_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Get the last group (the actual purpose)
            if match.lastindex and match.lastindex >= 2:
                purpose = match.group(match.lastindex)
            else:
                purpose = match.group(1)
            
            purpose = purpose.strip()
            
            # Clean up the purpose - remove trailing keywords
            trailing_pattern = r'\s+(?:at|on|tomorrow|today|with|for|next|this|week|monday|tuesday|wednesday|thursday|friday|saturday|sunday|morning|afternoon|evening|am|pm)\s*$'
            purpose = re.sub(trailing_pattern, '', purpose, flags=re.IGNORECASE)
            purpose = re.sub(r'\s+re:\s*', ' ', purpose, flags=re.IGNORECASE)
            purpose = re.sub(r'\s+', ' ', purpose)
            purpose = purpose.strip('.,;:!?')
            
            # Remove leading "the" from purpose
            purpose = re.sub(r'^the\s+', '', purpose, flags=re.IGNORECASE)
            
            # Filter out common non-purpose words
            if len(purpose) > 2:
                invalid_purposes = [
                    'me', 'everyone', 'all', 'team', 'you', 'the', 'this', 'next', 
                    'today', 'tomorrow', 'morning', 'evening', 'afternoon', 'day', 
                    'week', 'hour', 'minute', 'monday', 'tuesday', 'wednesday', 
                    'thursday', 'friday', 'saturday', 'sunday', 'am', 'pm'
                ]
                if purpose.lower() not in invalid_purposes:
                    # Capitalize properly
                    purpose_words = purpose.split()
                    capitalized_words = []
                    for i, word in enumerate(purpose_words):
                        # Don't capitalize small words in middle of phrase
                        if i == 0 or word.lower() not in ['a', 'an', 'the', 'and', 'or', 'but', 'for', 'to']:
                            capitalized_words.append(word.title())
                        else:
                            capitalized_words.append(word.lower())
                    return ' '.join(capitalized_words)
    
    return ''


def find_meeting_type(text: str) -> Tuple[str, bool]:
    """
    Find if there's a meeting type in the sentence.
    
    Args:
        text: Lowercase sentence
        
    Returns:
        Tuple of (meeting_type, should_combine_with_purpose)
    """
    for pattern, meeting_type, should_combine in MEETING_TYPE_PATTERNS:
        if re.search(pattern, text):
            return meeting_type, should_combine
    return None, False


def build_title_from_purpose_and_attendees(purpose: str, attendees: List[str], meeting_type: str = None, should_combine: bool = False) -> str:
    """
    Build a meeting title from purpose, attendees, and optional meeting type.
    
    Args:
        purpose: The meeting purpose/topic
        attendees: List of attendee names
        meeting_type: Optional meeting type (like "Sync")
        should_combine: Whether to combine purpose with meeting type
        
    Returns:
        Formatted meeting title
    """
    # Case 1: Purpose exists AND should combine with meeting type
    if purpose and should_combine and meeting_type:
        return f"{purpose} {meeting_type}"
    
    # Case 2: Purpose exists - use purpose + attendees (or just purpose if no attendees)
    if purpose:
        if attendees:
            if len(attendees) == 1:
                return f"{purpose} with {attendees[0]}"
            elif len(attendees) == 2:
                return f"{purpose} with {attendees[0]} & {attendees[1]}"
            else:
                return f"{purpose} with {', '.join(attendees[:-1])} & {attendees[-1]}"
        else:
            return purpose
    
    # Case 3: Meeting type exists (but no purpose)
    if meeting_type:
        if attendees:
            if len(attendees) == 1:
                return f"{meeting_type} with {attendees[0]}"
            elif len(attendees) == 2:
                return f"{meeting_type} with {attendees[0]} & {attendees[1]}"
            else:
                return f"{meeting_type} with {', '.join(attendees[:-1])} & {attendees[-1]}"
        else:
            return meeting_type
    
    # Case 4: Only attendees
    if attendees:
        if len(attendees) == 1:
            return f"Meeting with {attendees[0]}"
        elif len(attendees) == 2:
            return f"Meeting with {attendees[0]} & {attendees[1]}"
        else:
            return f"Meeting with {', '.join(attendees[:-1])} & {attendees[-1]}"
    
    # Default
    return 'Meeting'


def extract_meeting_title(sentence: str) -> str:
    """
    Extract meeting title from natural language sentence.
    
    For update sentences, returns empty string to preserve existing title.
    
    Args:
        sentence: The natural language sentence
        
    Returns:
        Meeting title string (empty string for updates)
    """
    text = sentence.lower().strip()
    
    # Check if this is an update sentence - don't extract title for updates
    if is_update_sentence(text):
        print(f"DEBUG: Detected update sentence: '{sentence}' - returning empty title to preserve existing")
        return ""
    
    # Extract purpose, attendees, and meeting type
    purpose = extract_purpose(sentence)
    attendees = extract_attendee_names_from_sentence(sentence)
    meeting_type, should_combine = find_meeting_type(text)
    
    print(f"DEBUG: extract_meeting_title for '{sentence}'")
    print(f"  purpose: '{purpose}'")
    print(f"  attendees: {attendees}")
    print(f"  meeting_type: '{meeting_type}', should_combine: {should_combine}")
    
    # Build title based on what we extracted
    title = build_title_from_purpose_and_attendees(purpose, attendees, meeting_type, should_combine)
    print(f"  Built title: '{title}'")
    
    # Clean up the title
    title = clean_title(title)
    
    return title


def is_meeting_title_ambiguous(sentence: str) -> bool:
    """
    Check if the meeting title needs clarification.
    
    Args:
        sentence: The natural language sentence
        
    Returns:
        True if title is ambiguous and needs clarification
    """
    # If no specific patterns match, the title is generic
    title = extract_meeting_title(sentence)
    return title == 'Meeting'
