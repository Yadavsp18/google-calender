"""
Update Patterns Module
Contains all patterns and keywords for detecting update/reschedule meeting actions.
"""

import re
from typing import List, Dict


# =============================================================================
# Update Action Patterns
# =============================================================================

UPDATE_PATTERNS = [
    # Direct update patterns
    r'update\s+.*meeting',
    r'change\s+.*meeting',
    r'modify\s+.*meeting',
    r'edit\s+.*meeting',
    r'revise\s+.*meeting',
    r'alter\s+.*meeting',
    r'adjust\s+.*meeting',
    r'amend\s+.*meeting',
    r'replace\s+.*(?:Google\s+Meet|Google Meet|meet\.google|gmeet|zoom|video\s+call|link|location|room)',
    r'(?:change|extend|shorten|increase|decrease)\s+.*(?:duration|length|time)',
    r'from\s+\d+\s*(?:minute|hour|min|hr)s?\s+to\s+\d+\s*(?:minute|hour|min|hr)s?',
    # Patterns with prepositions
    r'\bto\s+(update|change|modify|edit|revise|alter|adjust|amend|replace)\b',
    r'\b(update|change|modify|edit|revise|alter|adjust|amend|replace)\s+(a|the|my|our|this|that|it|meeting|event|appointment|call)',
    # Patterns with meeting BEFORE action (for sentences like "meeting update...")
    r'\bmeeting\s+(update|change|modify|edit|revise|alter|adjust|amend|replace)\b',
    r'\bproject\s+meeting\s+(update|change|modify|edit|revise|alter|adjust|amend|replace)\b',
]

# =============================================================================
# Reschedule Action Patterns
# =============================================================================

RESCHEDULE_PATTERNS = [
    # Direct reschedule patterns - simplified to match reschedule words followed by meeting/event/appointment
    r'reschedule\s+.*meeting',
    r'postpone\s+.*meeting',
    r'move\s+.*meeting',
    r'shift\s+.*meeting',
    r'push\s+.*meeting',
    r'bring\s+forward',
    # Also match reschedule keywords directly (for "push it", "move this", etc.)
    r'\b(postpone|push|move|shift)\s+(it|this|that|back)',
    r'\b(reschedule|move|shift|postpone|push)\s+(a|the|my|our|this|that|it|meeting|event|appointment|call|sync)',
    # Match standalone reschedule keywords followed by time/date indicators
    r'\b(postpone|push|move|shift)\s+.*(?:to|by|from)\s+\d',
]

# Update keywords for fuzzy matching
UPDATE_KEYWORDS = [
    'update', 'updating', 'updated',
    'change', 'changing', 'changed',
    'modify', 'modifying', 'modified',
    'replace', 'replacing', 'replaced',
    'switch', 'switching', 'switched',
    'adjust', 'adjusting', 'adjusted',
    'amend', 'amending', 'amended',
    'edit', 'editing', 'edited',
    'revise', 'revising', 'revised',
    'alter', 'altering', 'altered'
]

# Reschedule keywords for fuzzy matching
RESCHEDULE_KEYWORDS = [
    'reschedule', 'rescheduling', 'rescheduled',
    'postpone', 'postponing', 'postponed',
    'push', 'pushing', 'pushed',
    'move', 'moving', 'moved',
    'shift', 'shifting', 'shifted',
    'bring', 'forward'
]

# Combined update/reschedule keyword set
UPDATE_RESCHEDULE_KW_SET = {
    'update', 'updating', 'updated',
    'change', 'changing', 'changed',
    'modify', 'modifying', 'modified',
    'replace', 'replacing', 'replaced',
    'switch', 'switching', 'switched',
    'adjust', 'adjusting', 'adjusted',
    'amend', 'amending', 'amended',
    'edit', 'editing', 'edited',
    'revise', 'revising', 'revised',
    'alter', 'altering', 'altered',
    'reschedule', 'rescheduling', 'rescheduled',
    'postpone', 'postponing', 'postponed',
    'push', 'pushing', 'pushed',
    'move', 'moving', 'moved',
    'shift', 'shifting', 'shifted',
    'bring', 'forward'
}


def is_update_pattern(sentence: str) -> bool:
    """
    Check if the sentence matches any update pattern.
    
    Args:
        sentence: The natural language sentence to check
        
    Returns:
        True if the sentence matches any update pattern
    """
    return any(re.search(pattern, sentence, re.IGNORECASE) for pattern in UPDATE_PATTERNS)


def is_reschedule_pattern(sentence: str) -> bool:
    """
    Check if the sentence matches any reschedule pattern.
    
    Args:
        sentence: The natural language sentence to check
        
    Returns:
        True if the sentence matches any reschedule pattern
    """
    return any(re.search(pattern, sentence, re.IGNORECASE) for pattern in RESCHEDULE_PATTERNS)


def has_update_keyword(sentence: str) -> bool:
    """
    Check if the sentence contains any update keyword.
    
    Args:
        sentence: The natural language sentence to check
        
    Returns:
        True if the sentence contains any update keyword
    """
    text_lower = sentence.lower()
    return any(keyword.lower() in text_lower for keyword in UPDATE_KEYWORDS)


def has_reschedule_keyword(sentence: str) -> bool:
    """
    Check if the sentence contains any reschedule keyword.
    
    Args:
        sentence: The natural language sentence to check
        
    Returns:
        True if the sentence contains any reschedule keyword
    """
    text_lower = sentence.lower()
    return any(keyword.lower() in text_lower for keyword in RESCHEDULE_KEYWORDS)


def has_update_or_reschedule_action(text: str) -> bool:
    """
    Check if the text contains any update or reschedule action keyword.
    
    Args:
        text: The text to check
        
    Returns:
        True if update or reschedule action is detected
    """
    return bool(UPDATE_RESCHEDULE_KW_SET & set(text.lower().split()))


def extract_update_details(sentence: str) -> Dict[str, any]:
    """
    Extract update/reschedule-related details from sentence.
    
    Args:
        sentence: The natural language sentence to analyze
        
    Returns:
        Dictionary with update action details
    """
    result = {
        'is_update': False,
        'is_reschedule': False,
        'action': None,
        'intent': None,
        'matched_pattern': None,
        'has_meeting_word': False
    }
    
    text_lower = sentence.lower()
    tokens = set(text_lower.split())
    
    # Meeting-related words
    meeting_words = {
        'meeting', 'meetings', 'event', 'events', 'call', 'calls',
        'appointment', 'appointments', 'standup', 'standups', 'session', 'sessions',
        'sync', 'chat', 'chats', 'hangout', 'google meet', 'zoom'
    }
    
    result['has_meeting_word'] = bool(tokens & meeting_words)
    
    # Check reschedule patterns first
    for pattern in RESCHEDULE_PATTERNS:
        match = re.search(pattern, sentence, re.IGNORECASE)
        if match:
            result['is_reschedule'] = True
            result['action'] = 'update'
            result['intent'] = 'update_meeting'
            result['matched_pattern'] = pattern
            return result
    
    # Check update patterns
    for pattern in UPDATE_PATTERNS:
        match = re.search(pattern, sentence, re.IGNORECASE)
        if match:
            result['is_update'] = True
            result['action'] = 'update'
            result['intent'] = 'update_meeting'
            result['matched_pattern'] = pattern
            return result
    
    # Check for reschedule keywords if no pattern matched
    if has_reschedule_keyword(sentence) and result['has_meeting_word']:
        result['is_reschedule'] = True
        result['action'] = 'update'
        result['intent'] = 'update_meeting'
        return result
    
    # Check for update keywords if no pattern matched
    if has_update_keyword(sentence) and result['has_meeting_word']:
        result['is_update'] = True
        result['action'] = 'update'
        result['intent'] = 'update_meeting'
    
    return result


# =============================================================================
# TITLE EXTRACTION PATTERNS (from summary.py)
# =============================================================================

# Patterns that indicate an update operation (for title extraction - prevents
# extracting title from update sentences)
UPDATE_SENTENCE_PATTERNS = [
    r'^update\s+(?:the\s+)?(?:meeting|event)?',
    r'^reschedule\s+(?:the\s+)?(?:meeting|event)?',
    r'^change\s+(?:the\s+)?(?:meeting|event)?',
    r'^modify\s+(?:the\s+)?(?:meeting|event)?',
    r'^move\s+(?:the\s+)?(?:meeting|event)?',
    r'^shift\s+(?:the\s+)?(?:meeting|event)?',
    r'^postpone\s+(?:the\s+)?(?:meeting|event)?',
    r'^bring\s+forward\s+(?:the\s+)?(?:meeting|event)?',
]
