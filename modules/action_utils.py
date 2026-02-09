"""
Action/Intent Extraction Module
Extracts action type (create/update/cancel) and intent from natural language sentences.
"""

import re
from typing import Dict, Any


def extract_action_intent(sentence: str) -> Dict[str, str]:
    """
    Extract action and intent from sentence.
    
    Args:
        sentence: The natural language sentence
        
    Returns:
        Dictionary with action and intent
    """
    text = sentence.lower().strip()
    
    # Define action patterns
    action_patterns = {
        'cancel': [
            r'\bto\s+(cancel|delete|remove)\b',
            r'\b(cancel|delete|remove)\s+(the|my|our|this|that|it|meeting|event)\b',
        ],
        'update': [
            r'\b(to|should|need\s+to)\s+(update|change|modify|reschedule|move|shift|postpone)\b',
            r'\b(update|change|modify|reschedule|move|shift|postpone)\s+(the|my|our|this|that|it|meeting|event|appointment|call)\b',
        ],
        'reschedule': [
            r'\bto\s+(reschedule|move|shift|push|postpone)\b',
            r'\b(reschedule|move|shift|push|postpone)\s+(the|my|our|this|that|it|meeting|event|appointment|call)\b',
        ],
    }
    
    # Check for cancel first (highest priority)
    for pattern in action_patterns['cancel']:
        if re.search(pattern, text, re.IGNORECASE):
            return {
                "action": "cancel",
                "intent": "cancel_meeting"
            }
    
    # Check for reschedule/update
    for pattern in action_patterns['reschedule']:
        if re.search(pattern, text, re.IGNORECASE):
            return {
                "action": "reschedule",
                "intent": "reschedule_meeting"
            }
    
    for pattern in action_patterns['update']:
        if re.search(pattern, text, re.IGNORECASE):
            return {
                "action": "update",
                "intent": "update_meeting"
            }
    
    # Default to create
    return {
        "action": "create",
        "intent": "schedule_meeting"
    }
