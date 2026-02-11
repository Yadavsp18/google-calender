"""
Action/Intent Extraction Module
Extracts action type (create/update/cancel) and intent from natural language sentences.
Includes pattern-based action detection for meeting-related queries.
"""

import re
from typing import Dict, Any, Tuple


# =============================================================================
# Action to Intent Mapping
# =============================================================================

ACTION_TO_INTENT = {
    'schedule_meeting': ['schedule', 'set up', 'book', 'fix', 'arrange', 'create', 'plan', 'block', 'have', 'host', 'make'],
    'reschedule_meeting': ['reschedule', 'move', 'shift', 'push', 'postpone', 'bring forward'],
    'cancel_meeting': ['cancel', 'delete', 'remove', 'drop', 'scrap', 'abort', 'void', 'nullify'],
    'update_meeting': ['update', 'change', 'modify', 'replace', 'switch', 'adjust', 'amend', 'edit', 'revise', 'alter'],
}


# =============================================================================
# Action Detection Patterns
# =============================================================================

CREATE_PATTERNS = [
    # Direct create patterns (explicit create keywords)
    r'\bcreate\s+(?:a\s+|an\s+)?(?:meeting|event|call|appointment|standup|session)\b',
    r'\bmake\s+(?:a\s+|an\s+)?(?:meeting|event|call|appointment|standup|session)\b',
    r'\bbook\s+(?:a\s+|an\s+)?(?:meeting|event|call|appointment|standup|session)\b',
    r'\bschedule\s+(?:a\s+|an\s+)?(?:meeting|event|call|appointment|standup|session)\b',
    r'\barrange\s+(?:a\s+|an\s+)?(?:meeting|event|call|appointment|standup|session)\b',
    r'\borganize\s+(?:a\s+|an\s+)?(?:meeting|event|call|appointment|standup|session)\b',
    r'\bset\s+up\s+(?:a\s+|an\s+)?(?:meeting|event|call|appointment|standup|session)\b',
    r'\bput\s+(?:a\s+|an\s+)?(?:meeting|event|call|appointment|standup|session)\b',
    r'\bfix\s+(?:a\s+|an\s+)?(?:meeting|event|call|appointment|standup|session)\b',
    r'\bblock\s+(?:a\s+|an\s+)?(?:meeting|event|call|appointment|slot|time|standup|session)\b',
    r'\bhave\s+(?:a\s+|an\s+)?(?:meeting|event|call|appointment|standup|session)\b',
    r'\bhost\s+(?:a\s+|an\s+)?(?:meeting|event|call|appointment|standup|session)\b',
    # Flexible patterns for "Schedule a team standup" style
    r'\b(schedule|book|arrange|organize|set\s+up|plan|setup)\s+.*(?:standup|session|meeting|call|appointment)\b',
    # Meeting with person patterns (implicit create) - ONLY if no reschedule or cancel keywords
    r'(?!.*(?:move|shift|push|postpone|reschedule|bring\s+forward|drop|cancel|delete|remove|scrap|abort|void|nullify|update|change|modify|replace|switch|adjust|amend|edit|revise|alter))\b(meeting|call|chat|hangout)\s+with\b',
]

CANCEL_PATTERNS = [
    # Direct cancel patterns - simplified to match cancel words followed by meeting/event/appointment
    r'cancel(?:ing)?\s+.*(?:meeting|event|appointment|it|this|that)',
    r'delete\s+.*(?:meeting|event|appointment|it|this|that)',
    r'remove\s+.*(?:meeting|event|appointment|it|this|that)',
    r'drop\s+(?:meeting|it|this|that)',
    r'drop\s+.*(?:meeting|event|appointment|it|this|that)',
    r'scrap\s+.*(?:meeting|event|appointment|it|this|that)',
    r'abort\s+.*(?:meeting|event|appointment|it|this|that)',
    r'void\s+.*(?:meeting|event|appointment)',
    r'nullify\s+.*(?:meeting|event|appointment)',
    # Also match cancel words directly followed by any word (for "remove it", "drop this", etc.)
    r'\b(cancel|delete|remove|drop|scrap|abort|void|nullify)\s+(it|this|that|everything)',
    # Match standalone cancel keywords when followed by meeting-related words
    r'\b(cancel|delete|remove|drop|scrap)\b.*(?:meeting|event|appointment|call|sync)',
]

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
]

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


def detect_action(sentence: str) -> Tuple[bool, bool, bool, bool]:
    """
    Detect the action type from the sentence.
    
    Args:
        sentence: The natural language sentence to analyze
        
    Returns:
        Tuple of (is_create, is_cancel, is_update, is_reschedule) booleans
    """
    import traceback
    # Get the calling function name
    stack = traceback.extract_stack()
    caller = stack[-2] if len(stack) > 2 else None
    caller_name = caller.name if caller else 'unknown'
    
    # Debug print
    print(f"\nDEBUG detect_action (called from: {caller_name}): '{sentence}'")
    
    # Check cancel/update/reschedule first (these take priority over create)
    is_cancel = any(re.search(p, sentence, re.IGNORECASE) for p in CANCEL_PATTERNS)
    print(f"DEBUG: is_cancel={is_cancel}")
    if is_cancel:
        for p in CANCEL_PATTERNS:
            match = re.search(p, sentence, re.IGNORECASE)
            if match:
                print(f"DEBUG: Matched cancel pattern: '{p}' -> '{match.group(0)}'")
    
    is_update = any(re.search(p, sentence, re.IGNORECASE) for p in UPDATE_PATTERNS)
    is_reschedule = any(re.search(p, sentence, re.IGNORECASE) for p in RESCHEDULE_PATTERNS)
    
    # Only check create patterns if no cancel/update/reschedule detected
    # This ensures "drop a meeting with john" is recognized as cancel, not create
    is_create = False
    if not (is_cancel or is_update or is_reschedule):
        is_create = any(re.search(p, sentence, re.IGNORECASE) for p in CREATE_PATTERNS)
    
    print(f"DEBUG: Final - is_create={is_create}, is_cancel={is_cancel}, is_update={is_update}, is_reschedule={is_reschedule}")
    
    return is_create, is_cancel, is_update, is_reschedule


# Keywords that indicate update/reschedule (these should NOT trigger create)
UPDATE_KEYWORDS = [
    'reschedule', 'move', 'shift', 'push', 'postpone', 'bring forward',
    'update', 'change', 'modify', 'replace', 'switch', 'adjust', 'amend',
    'edit', 'revise', 'alter', 'forward'  # 'forward' for 'bring forward'
]

# Keywords that indicate cancel (but not reschedule)
CANCEL_KEYWORDS = [
    'cancel', 'delete', 'remove', 'drop', 'scrap', 'abort', 'void', 'nullify'
]


def extract_action_intent(sentence: str) -> Dict[str, str]:
    """
    Extract action and intent from sentence.
    
    Args:
        sentence: The natural language sentence
        
    Returns:
        Dictionary with action and intent
    """
    text = sentence.lower().strip()
    
    # Check for update/reschedule keywords
    has_update_keyword = any(kw in text for kw in UPDATE_KEYWORDS)
    has_cancel_keyword = any(kw in text for kw in CANCEL_KEYWORDS)
    has_reschedule_keyword = any(kw in text for kw in ['reschedule', 'move', 'shift', 'push', 'postpone', 'bring forward'])
    
    # Define cancel patterns (only if no reschedule keywords)
    cancel_patterns = [
        r'cancel(?:ing)?\s+.*(?:meeting|event|appointment|it|this|that)',
        r'delete\s+.*(?:meeting|event|appointment|it|this|that)',
        r'remove\s+.*(?:meeting|event|appointment|it|this|that)',
        r'drop\s+(?:meeting|it|this|that)',
        r'drop\s+.*(?:meeting|event|appointment|it|this|that)',
        r'scrap\s+.*(?:meeting|event|appointment|it|this|that)',
        r'abort\s+.*(?:meeting|event|appointment|it|this|that)',
        r'void\s+.*(?:meeting|event|appointment)',
        r'nullify\s+.*(?:meeting|event|appointment)',
        r'\b(cancel|delete|remove|drop|scrap|abort|void|nullify)\s+(it|this|that|everything)',
    ]

    
    # Define update/reschedule patterns
    update_patterns = [
        # Direct action keywords
        r'\b(reschedule|move|shift|push|postpone|bring\s+forward|update|change|modify|replace|switch|adjust|amend|edit|revise|alter)\b.*(?:meeting|event|call|appointment)',
        # Flexible patterns without requiring "meeting"
        r'\bpostpone\b.*(?:it|this|that|by|to)\b',
        r'\bpush\b.*(?:it|this|that|by|to|back)\b',
        r'\bmove\b.*(?:it|this|that|to|by)\b',
        r'\bshift\b.*(?:it|this|that|to|by)\b',
        r'\breschedule\b.*(?:it|this|that|to|by)\b',
        r'\b(from|to)\s+\d{1,2}:\d{2}\b',  # time range patterns like "from 5pm to 6pm"
        # Location/link change
        r'(?:change|replace|switch)\s+(?:the\s+)?(?:meeting\s+)?(?:location|room|platform|link|Google\s+Meet|Meet|gmeet|zoom)',
        # Duration change
        r'(?:change|extend|shorten|increase|decrease)\s+(?:the\s+)?(?:meeting\s+)?(?:duration|length|time)',
        r'\bfrom\s+\d+\s*(?:minute|hour|min|hr)s?\s+to\s+\d+\s*(?:minute|hour|min|hr)s?\b',
        # Time reference patterns
        r'\bto\s+\d{1,2}:?\d{2}\s*(?:am|pm)?\b',
        r'\bpush\s+.*\s+by\s+\d+\s*(?:minute|hour|min|hr)s?\b',
        r'\bmove\s+.*(?:to|from)\s+\w+\s+\d+(?:st|nd|rd|th)?\b',
    ]
    
    for pattern in cancel_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return {
                "action": "cancel",
                "intent": "cancel_meeting"
            }

    
    # Check for update/reschedule patterns
    if has_update_keyword:
        for pattern in update_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return {
                    "action": "update",
                    "intent": "update_meeting"
                }
    
    # Additional check: if has reschedule keyword, treat as update even if no specific pattern matched
    if has_reschedule_keyword:
        return {
            "action": "update",
            "intent": "update_meeting"
        }
    
    # Check for explicit create patterns
    create_patterns = [
        r'\b(create|make|book|schedule|arrange|organize|set\s+up|fix|block|have|host)\s+(?:a\s+)?(?:meeting|event|call|appointment)\b',
        r'\b(meeting|call|chat|hangout)\s+with\b(?!.*(?:move|shift|push|postpone|reschedule|change|update|replace|drop|cancel|delete|remove|scrap))',
    ]
    
    for pattern in create_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return {
                "action": "create",
                "intent": "schedule_meeting"
            }
    
    # Default to create (fallback)
    return {
        "action": "create",
        "intent": "schedule_meeting"
    }
