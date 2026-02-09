"""
Meeting Summary Extraction Module
Extracts meeting title/summary from natural language sentences.
"""

import re
from typing import Optional


def extract_meeting_title(sentence: str) -> str:
    """
    Extract meeting title from natural language sentence.
    
    Args:
        sentence: The natural language sentence
        
    Returns:
        Meeting title string
    """
    text = sentence.lower().strip()
    
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
                return f"{prefix.title()} with {name.title()}"
    
    # Pattern 2: Common meeting types
    common_types = [
        (r'\b(standup|sprint\s*standup|daily\s*standup)\b', 'Daily Standup'),
        (r'\b(weekly\s*sync|team\s*sync|sync\s*up)\b', 'Team Sync'),
        (r'\b(1:1|one-on-one|one on one)\b(?:\s+with\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?))?', '1:1 Meeting'),
        (r'\b(status\s*update|update\s*meeting)\b', 'Status Update'),
        (r'\b(planning\s*session|planning\s*meeting)\b', 'Planning Session'),
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
    
    for pattern, title in common_types:
        match = re.search(pattern, text)
        if match:
            if match.lastindex and match.lastindex >= 2:
                name = match.group(2)
                if name and name.lower() not in ['me', 'everyone', 'team']:
                    return f"{title} with {name.title()}"
            return title
    
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
                return f"Meeting about {topic.title()}"
    
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
                return potential_title.title()
    
    # Pattern 5: If sentence starts with a capitalized word, use it
    capitalized_match = re.search(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', text)
    if capitalized_match:
        potential = capitalized_match.group(1)
        if len(potential) > 3:
            return potential
    
    # Default title
    return 'Meeting'


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
