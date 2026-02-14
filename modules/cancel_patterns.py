"""
Cancel Patterns Module
Contains all patterns and keywords for detecting cancel/delete meeting actions.
"""

import re
from typing import List, Dict


# =============================================================================
# Cancel Action Patterns
# =============================================================================

CANCEL_PATTERNS = [
    # Direct cancel patterns - cancel verb before meeting
    r'\b(cancel(?:ing)?|delete|remove|drop|scrap|abort|void|nullify|terminate|stop)\s+(?:the\s+)?(?:meeting|event|appointment|call|sync|chat|message|it|this|that)\b',
    
    # Reverse order: "meeting cancel" - cancel noun after meeting
    r'\b(?:meeting|event|appointment|call|sync|chat|message)\s+(?:with\s+)?(?:cancel(?:lation)?|deletion|removal|drop|scrap|abort|termination|stop)\b',
    
    # Also match: "meeting with john cancel" - cancel keyword at the end
    r'\b(?:meeting|event|appointment|call|sync)\s+.*\b(cancel(?:ed|ing|lation)?|delete(?:d|ing)?|remove(?:d|ing)?|drop(?:ped|ping)?|scrap(?:ped|ping)?|abort(?:ed|ing)?|terminate(?:d|ing)?|stop(?:ped|ping)?)\b',
    
    # Match patterns where user might use extra words like "Please", "I want", etc.
    r'(?:please|kindly|can\s+you|would\s+you)\s+(?:cancel|delete|remove|drop|scrap|abort|terminate|stop)\s+(?:the\s+)?(?:meeting|event|appointment|call|sync|chat|message|it|this|that)\b',
    
    # "Cancel" followed by extra description (e.g., "Cancel the meeting at 2 PM")
    r'\b(cancel(?:ing)?|delete|remove|drop|scrap|abort|terminate|stop)\s+(?:the\s+)?(?:meeting|event|appointment|call|sync|chat|message)\s+(?:at\s+\d{1,2}\s*(?:AM|PM)?)?\b',
    
    # Patterns for phrases with extra details like time (e.g., "Cancel the meeting at 3 PM tomorrow")
    r'\b(cancel(?:ing)?|delete|remove|drop|scrap|abort|terminate|stop)\s+(?:the\s+)?(?:meeting|event|appointment|call|sync|chat|message)\s+(?:at|on|for)\s+\S+\b',
    
    # Also match cancel words directly followed by any word (for "remove it", "drop this", etc.)
    r'\b(cancel|delete|remove|drop|scrap|abort|void|nullify|terminate|stop)\s+(it|this|that|everything|the\s+thing|that\s+event|the\s+meeting)\b',
    
    # Handle different ordering: "cancel event this" or "cancel this event"
    r'\b(cancel(?:ing)?|delete|remove|drop|scrap|abort|terminate|stop)\s+(?:this|that|it)\s+(?:meeting|event|appointment|call|sync|chat|message)\b',
    
    # Match standalone cancel keywords when followed by meeting-related words
    r'\b(cancel|delete|remove|drop|scrap|abort|terminate|stop)\b\s+(?:meeting|event|appointment|call|sync|message|chat)',

    # For more complex expressions with adverbs and modals (e.g., "I really want to cancel the meeting")
    r'\b(?:I\s+really\s+want\s+to|I\s+would\s+like\s+to|can\s+you)\s+(?:cancel|delete|remove|drop|scrap|abort|terminate|stop)\s+(?:the\s+)?(?:meeting|event|appointment|call|sync|chat|message|it|this|that)\b',

    # Handling more ambiguous cancel phrases: "Cancel this thing"
    r'\b(cancel|delete|remove|drop|scrap|abort|terminate|stop)\s+(?:this|it|that|thing)\s+(?:thing|event|appointment|meeting)\b',
    
    # Handling plural form or related patterns like "cancelling all meetings"
    r'\b(cancel(?:ing)?|delete|remove|drop|scrap|abort|terminate|stop)\s+all\s+(?:meetings|events|appointments|calls|messages)\b',
    
    # Handle cancel phrases with modal verbs like "could you", "would you"
    r'\b(?:could\s+you|would\s+you|can\s+you)\s+(?:cancel|delete|remove|drop|scrap|abort|terminate|stop)\s+(?:the\s+)?(?:meeting|event|appointment|call|sync|chat|message|it|this|that)\b',
    
    # Case where "cancel" might come after time or date: "Cancel at 2 PM" or "Cancel tomorrow"
    r'\b(?:cancel|delete|remove|drop|scrap|abort|terminate|stop)\s+(?:the\s+)?(?:meeting|event|appointment)\s+(?:at|on|for)\s+\S+',
    
    # Priority fallback: If sentence contains any cancel keyword, treat as cancel
    r'\bcancel(?:ed|ing|lation)?\b',
    r'\bdelete[ds]?\b',
    r'\bremove[ds]?\b',
    r'\bdro(p|ped|ping)\b',
    r'\bscrap(?:ped|ping)?\b',
    r'\babort(?:ed|ing)?\b',
    
    # Jumbled word patterns - meeting/event BEFORE cancel keywords
    r'\b(?:project\s+)?(?:meeting|event|appointment|call|sync)\s+(?:with\s+[^\s]+\s+)?(?:cancel|delete|remove|drop|scrap|abort)\b',
    r'\b(?:meeting|event)\s+.*(?:cancel|delete|remove|drop|scrap|abort)\b',
]

# Cancel keywords for fuzzy matching
CANCEL_KEYWORDS = [
    'cancel', 'cancelling', 'canceling', 'cancelled', 'canceled',
    'delete', 'deleted', 'deleting',
    'remove', 'removing', 'removed',
    'drop', 'dropping', 'dropped',
    'scrap', 'scrapping', 'scrapped',
    'abort', 'aborting', 'aborted',
    'void', 'voiding', 'voided',
    'nullify', 'nullifying', 'nullified',
    'terminate', 'terminating', 'terminated',
    'stop', 'stopping', 'stopped'
]

# Cancel keyword set for fast lookup
CANCEL_KW_SET = {
    'cancel', 'cancelling', 'canceling', 'cancelled', 'canceled',
    'delete', 'deleted', 'deleting',
    'remove', 'removing', 'removed',
    'drop', 'dropping', 'dropped',
    'scrap', 'scrapping', 'scrapped',
    'abort', 'aborting', 'aborted',
    'void', 'voiding', 'voided',
    'nullify', 'nullifying', 'nullified',
    'terminate', 'terminating', 'terminated',
    'stop', 'stopping', 'stopped'
}


def is_cancel_pattern(sentence: str) -> bool:
    """
    Check if the sentence matches any cancel pattern.
    
    Args:
        sentence: The natural language sentence to check
        
    Returns:
        True if the sentence matches any cancel pattern
    """
    return any(re.search(pattern, sentence, re.IGNORECASE) for pattern in CANCEL_PATTERNS)


def has_cancel_keyword(sentence: str) -> bool:
    """
    Check if the sentence contains any cancel keyword.
    
    Args:
        sentence: The natural language sentence to check
        
    Returns:
        True if the sentence contains any cancel keyword
    """
    text_lower = sentence.lower()
    return any(keyword.lower() in text_lower for keyword in CANCEL_KEYWORDS)


def extract_cancel_details(sentence: str) -> Dict[str, any]:
    """
    Extract cancel-related details from sentence.
    
    Args:
        sentence: The natural language sentence to analyze
        
    Returns:
        Dictionary with cancel action details
    """
    result = {
        'is_cancel': False,
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
    
    # Check patterns
    for pattern in CANCEL_PATTERNS:
        match = re.search(pattern, sentence, re.IGNORECASE)
        if match:
            result['is_cancel'] = True
            result['action'] = 'cancel'
            result['intent'] = 'cancel_meeting'
            result['matched_pattern'] = pattern
            return result
    
    # Check for cancel keywords if no pattern matched
    if has_cancel_keyword(sentence) and result['has_meeting_word']:
        result['is_cancel'] = True
        result['action'] = 'cancel'
        result['intent'] = 'cancel_meeting'
    
    return result


def has_cancel_action(text: str) -> bool:
    """
    Check if the text contains any cancel action keyword.
    
    Args:
        text: The text to check
        
    Returns:
        True if cancel action is detected
    """
    return bool(CANCEL_KW_SET & set(text.lower().split()))
