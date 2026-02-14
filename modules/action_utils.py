"""
Action/Intent Extraction Module
Extracts action type (create/update/cancel) and intent from natural language sentences.
Includes pattern-based action detection for meeting-related queries.

Note: This module now imports patterns from separate modules:
- modules/create_patterns.py
- modules/cancel_patterns.py
- modules/update_patterns.py
"""

import re
from typing import Dict, Any, Tuple
from collections import Counter

# Import patterns from separate modules
from modules.create_patterns import (
    CREATE_KEYWORDS,
    NOT_CREATE_KEYWORDS,
    extract_create_details,
    is_create_intent,
    CREATE_PATTERNS
)

from modules.cancel_patterns import (
    CANCEL_PATTERNS,
    CANCEL_KEYWORDS,
    CANCEL_KW_SET,
    is_cancel_pattern,
    has_cancel_keyword,
    extract_cancel_details,
    has_cancel_action
)

from modules.update_patterns import (
    UPDATE_PATTERNS,
    RESCHEDULE_PATTERNS,
    UPDATE_KEYWORDS,
    RESCHEDULE_KEYWORDS,
    UPDATE_RESCHEDULE_KW_SET,
    is_update_pattern,
    is_reschedule_pattern,
    has_update_keyword,
    has_reschedule_keyword,
    has_update_or_reschedule_action,
    extract_update_details
)


# =============================================================================
# Action to Intent Mapping
# Note: reschedule keywords (move, shift, push, postpone) now map to update_meeting intent
# =============================================================================

ACTION_TO_INTENT = {
    'schedule_meeting': ['schedule', 'set up', 'book', 'fix', 'arrange', 'create', 'plan', 'block', 'have', 'host', 'make'],
    'update_meeting': ['update', 'change', 'modify', 'replace', 'switch', 'adjust', 'amend', 'edit', 'revise', 'alter', 'reschedule', 'move', 'shift', 'push', 'postpone', 'bring forward'],
    'cancel_meeting': ['cancel', 'delete', 'remove', 'drop', 'scrap', 'abort', 'void', 'nullify'],
}


# =============================================================================
# Main Detection Functions
# =============================================================================

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
    print(f"\n=== DEBUG detect_action ===")
    print(f"Sentence: '{sentence}'")
    print(f"Called from: {caller_name}")
    
    # Check cancel first
    print("\n--- Checking CANCEL_PATTERNS ---")
    is_cancel = False
    for p in CANCEL_PATTERNS:
        match = re.search(p, sentence, re.IGNORECASE)
        if match:
            is_cancel = True
            print(f"MATCHED: '{p}' -> '{match.group(0)}'")
    print(f"is_cancel = {is_cancel}")
    
    # Check update
    print("\n--- Checking UPDATE_PATTERNS ---")
    is_update = any(re.search(p, sentence, re.IGNORECASE) for p in UPDATE_PATTERNS)
    print(f"is_update = {is_update}")
    
    # Check reschedule
    print("\n--- Checking RESCHEDULE_PATTERNS ---")
    is_reschedule = any(re.search(p, sentence, re.IGNORECASE) for p in RESCHEDULE_PATTERNS)
    print(f"is_reschedule = {is_reschedule}")
    
    # Check create (only if no cancel/update/reschedule)
    print("\n--- Checking CREATE_PATTERNS ---")
    is_create = False
    if not (is_cancel or is_update or is_reschedule):
        for p in CREATE_PATTERNS:
            match = re.search(p, sentence, re.IGNORECASE)
            if match:
                is_create = True
                print(f"MATCHED: '{p}' -> '{match.group(0)}'")
    print(f"is_create = {is_create}")
    
    print(f"\n=== FINAL RESULT ===")
    print(f"is_create={is_create}, is_cancel={is_cancel}, is_update={is_update}, is_reschedule={is_reschedule}")
    
    return is_create, is_cancel, is_update, is_reschedule


# Keywords that indicate update/reschedule (these should NOT trigger create)
UPDATE_KEYWORDS_LIST = [
    'reschedule', 'move', 'shift', 'push', 'postpone', 'bring forward',
    'update', 'change', 'modify', 'replace', 'switch', 'adjust', 'amend',
    'edit', 'revise', 'alter', 'forward'  # 'forward' for 'bring forward'
]

# Keywords that indicate cancel (but not reschedule)
CANCEL_KEYWORDS_LIST = [
    'cancel', 'delete', 'remove', 'drop', 'scrap', 'abort', 'void', 'nullify'
]


def has_create_keyword(sentence: str) -> bool:
    """
    Check if the sentence contains any create keyword.
    
    Args:
        sentence: The natural language sentence to check
        
    Returns:
        True if the sentence contains any create keyword
    """
    text_lower = sentence.lower()
    return any(keyword.lower() in text_lower for keyword in CREATE_KEYWORDS)


def extract_action_intent(sentence: str) -> Dict[str, str]:
    """
    Extract action and intent from sentence using pattern-based detection.
    
    Args:
        sentence: The natural language sentence to analyze
        
    Returns:
        Dictionary with action and intent
    """
    # Pattern-based detection
    is_create, is_cancel, is_update, is_reschedule = detect_action(sentence)
    
    # Priority: Cancel > Update/Reschedule > Create
    if is_cancel:
        return {"action": "cancel", "intent": "cancel_meeting"}
    
    if is_update or is_reschedule:
        return {"action": "update", "intent": "update_meeting"}
    
    if is_create:
        return {"action": "create", "intent": "schedule_meeting"}
    
    # Default: assume create if meeting-related words are present
    text_lower = sentence.lower()
    if any(word in text_lower for word in ['meeting', 'call', 'event', 'appointment', 'standup', 'sync']):
        return {"action": "create", "intent": "schedule_meeting"}
    
    # Last resort: check for create keywords without meeting words
    if has_create_keyword(sentence):
        return {"action": "create", "intent": "schedule_meeting"}
    
    return {"action": "unknown", "intent": None}
