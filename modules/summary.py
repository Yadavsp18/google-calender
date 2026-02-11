"""
Meeting Summary Extraction Module
Extracts meeting title/summary from natural language sentences.
"""

import re
from typing import Optional


# Patterns that indicate an update operation (not title extraction)
UPDATE_PATTERNS = [
    r'^update\s+(?:the\s+)?(?:meeting|event)?',
    r'^reschedule\s+(?:the\s+)?(?:meeting|event)?',
    r'^change\s+(?:the\s+)?(?:meeting|event)?',
    r'^modify\s+(?:the\s+)?(?:meeting|event)?',
    r'^move\s+(?:the\s+)?(?:meeting|event)?',
    r'^shift\s+(?:the\s+)?(?:meeting|event)?',
    r'^postpone\s+(?:the\s+)?(?:meeting|event)?',
    r'^bring\s+forward\s+(?:the\s+)?(?:meeting|event)?',
]


# Words to strip from the end of titles (date/time/relative words)
TITLE_STRIP_WORDS = [
    'tomorrow', 'today', 'monday', 'tuesday', 'wednesday', 'thursday',
    'friday', 'saturday', 'sunday', 'next', 'this', 'on', 'at', 'in',
    'next week', 'this week', 'this morning', 'this afternoon', 'this evening',
    'afternoon', 'morning', 'evening', 'noon', 'midnight',
    'week', 'day', 'hour', 'minute',
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
    
    for pattern in UPDATE_PATTERNS:
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
        
        if not skip:
            cleaned_words.append(word)
    
    # Reconstruct title
    cleaned = ' '.join(cleaned_words)
    
    # Additional cleanup: remove trailing prepositions
    cleaned = re.sub(r'\s+(?:on|at|in|for|to|with)$', '', cleaned, flags=re.IGNORECASE)
    
    return cleaned.strip()


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
    
    title = ""
    
    # Pattern 1: "Meeting/Call/Chat with [Name]"
    with_patterns = [
        r'\b(meeting|call|chat|hangout|discussion)\s+with\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)',
        r'\b(with|hangout|discussion)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)',
    ]
    for pattern in with_patterns:
        match = re.search(pattern, text)
        if match:
            prefix = match.group(1)
            name = match.group(2)
            # Don't use common words as title
            if name.lower() not in ['me', 'everyone', 'all', 'team', 'you']:
                title = f"{prefix.title()} with {name.title()}"
                break
    
    if not title:
        # Pattern 2: Common meeting types
        common_types = [
            (r'\b(1:1|one-on-one|one on one)\b(?:\s+with\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?))?', '1:1 Meeting'),
            (r'\b(standup|sprint\s*standup|daily\s*standup)\b', 'Daily Standup'),
            (r'\b(weekly\s*sync|team\s*sync|sync\s*up)\b', 'Team Sync'),
            (r'\b(status\s*update|update\s*meeting)\b', 'Status Update'),
            (r'\b(planning\s*session|planning\s*meeting)\b', 'Planning Session'),
            (r'\b(sprint\s+planning)\b', 'Sprint Planning Session'),
            (r'\b(retro|retrospective)\b', 'Retrospective'),
            (r'\b(roadmap|road\s*map)\b', 'Roadmap Review'),
            (r'\b(demo|product\s*demo)\b', 'Product Demo'),
            (r'\b(interview)\b(?:\s+with\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?))?', 'Interview'),
            (r'\b(kickoff|project\s*kickoff)\b', 'Project Kickoff'),
            (r'\b(review|code\s*review|design\s*review)\b', 'Review Meeting'),
            (r'\b(workshop)\b', 'Workshop'),
            (r'\b(town\s*hall)\b', 'Town Hall'),
            (r'\b(all-hands)\b', 'All Hands'),
            (r'\b(lunch)\b(?:\s+with\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?))?', 'Lunch'),
            (r'\b(coffee|coffee\s*chat)\b(?:\s+with\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?))?', 'Coffee Chat'),
            (r'\b(quick\s*chat|brief\s*chat)\b(?:\s+with\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?))?', 'Quick Chat'),
        ]
        
        for pattern, default_title in common_types:
            match = re.search(pattern, text)
            if match:
                if match.lastindex and match.lastindex >= 2:
                    name = match.group(2)
                    if name and name.lower() not in ['me', 'everyone', 'team']:
                        title = f"{default_title} with {name.title()}"
                    else:
                        title = default_title
                else:
                    title = default_title
                break
    
    if not title:
        # Pattern 3: "About [Topic]" and "re: [Topic]"
        about_patterns = [
            r'\babout\s+([a-zA-Z][a-zA-Z\s]*)',
            r'\bre:\s*([a-zA-Z][a-zA-Z\s]*)',
            r'\bfor\s+([a-zA-Z][a-zA-Z\s]{2,})',
        ]
        
        for pattern in about_patterns:
            about_match = re.search(pattern, text)
            if about_match:
                topic = about_match.group(1).strip()
                # Filter out common non-topic words
                if len(topic) > 2 and topic.lower() not in ['me', 'everyone', 'all', 'team', 'you', 'the', 'this', 'next', 'today', 'tomorrow', 'morning', 'evening', 'afternoon', 'day', 'week', 'hour', 'minute', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
                    title = f"Meeting about {topic.title()}"
                    break
    
    if not title:
        # Pattern 4: Extract first meaningful words before time indicator
        time_patterns = [
            r'^([a-zA-Z][a-zA-Z\s]*?)\s+(?:tomorrow|today|monday|tuesday|wednesday|thursday|friday|saturday|sunday|next\s+week|this\s+week|at\s+\d|at\s+(?:am|pm))',
            r'^([a-zA-Z][a-zA-Z\s]*?)\s+(?:for\s+)?(?:\d+:?\d*)',
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, text)
            if match:
                potential_title = match.group(1).strip()
                # Clean up the title
                potential_title = re.sub(r'\s+', ' ', potential_title)
                if len(potential_title) > 3 and potential_title.lower() not in ['meeting', 'call', 'sync']:
                    title = potential_title.title()
                    break
    
    if not title:
        # Pattern 5: If sentence starts with a capitalized word, use it
        capitalized_match = re.search(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', text)
        if capitalized_match:
            potential = capitalized_match.group(1)
            if len(potential) > 3:
                title = potential
    
    if not title:
        # Default title
        title = 'Meeting'
    
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
