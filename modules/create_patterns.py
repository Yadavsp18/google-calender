"""
Create Patterns Module (Improved Version)
Handles jumbled word order and natural language variations.
"""

import re
from typing import Dict, Set


# =============================================================================
# KEYWORD GROUPS
# =============================================================================

CREATE_KEYWORDS: Set[str] = {
    'create', 'creating', 'created',
    'make', 'making', 'made',
    'book', 'booking', 'booked',
    'schedule', 'scheduling', 'scheduled',
    'arrange', 'arranging', 'arranged',
    'organize', 'organizing', 'organized',
    'setup', 'set', 'setting',
    'fix', 'fixing', 'fixed',
    'block', 'blocking', 'blocked',
    'have', 'having', 'had',
    'host', 'hosting', 'hosted',
    'plan', 'planning', 'planned'
}

MEETING_WORDS: Set[str] = {
    'meeting', 'meetings',
    'event', 'events',
    'call', 'calls',
    'appointment', 'appointments',
    'standup', 'standups',
    'session', 'sessions',
    'sync', 'chat', 'chats',
    'hangout', 'zoom', 'meet'
}

NOT_CREATE_KEYWORDS: Set[str] = {
    'reschedule', 'move', 'shift', 'push',
    'postpone', 'update', 'change',
    'modify', 'replace', 'switch',
    'adjust', 'amend', 'edit',
    'revise', 'alter',
    'cancel', 'delete', 'remove',
    'drop', 'scrap', 'abort',
    'void', 'nullify'
}


# =============================================================================
# TEXT NORMALIZATION
# =============================================================================

def normalize_text(text: str) -> str:
    """
    Normalize input text:
    - Lowercase
    - Remove extra spaces
    - Remove punctuation (except time/date related symbols)
    """
    text = text.lower()
    text = re.sub(r'[^\w\s:/-]', ' ', text)  # keep time/date characters
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def tokenize(text: str) -> Set[str]:
    """
    Tokenize text into unique words.
    """
    return set(re.findall(r'\b\w+\b', text))


# =============================================================================
# MAIN LOGIC
# =============================================================================

def extract_create_details(sentence: str) -> Dict[str, any]:
    """
    Detect if sentence indicates creating/scheduling a meeting.
    Handles jumbled and free-form input.
    """

    result = {
        'is_create': False,
        'action': None,
        'intent': None,
        'confidence': 0.0,
        'signals': []
    }

    if not sentence or not sentence.strip():
        return result

    # 1️⃣ Normalize text
    text = normalize_text(sentence)

    # 2️⃣ Split into words (ORDER DOES NOT MATTER)
    words = text.split()

    # 3️⃣ Convert to set for fast lookup
    word_set = set(words)

    # 4️⃣ Check NEGATIVE keywords first (block)
    for word in words:
        if word in NOT_CREATE_KEYWORDS:
            result['signals'].append(f"blocked_by:{word}")
            return result

    # 5️⃣ Check CREATE keywords
    create_found = False
    for word in words:
        if word in CREATE_KEYWORDS:
            create_found = True
            result['signals'].append(f"create_word:{word}")
            break

    # 6️⃣ Check MEETING keywords
    meeting_found = False
    for word in words:
        if word in MEETING_WORDS:
            meeting_found = True
            result['signals'].append(f"meeting_word:{word}")
            break

    # 7️⃣ Decision Logic
    if create_found and meeting_found:
        result['is_create'] = True
        result['action'] = 'create'
        result['intent'] = 'schedule_meeting'
        result['confidence'] = 0.95
        return result

    # 8️⃣ Fallback — meeting + with pattern
    if meeting_found and "with" in word_set:
        result['is_create'] = True
        result['action'] = 'create'
        result['intent'] = 'schedule_meeting'
        result['confidence'] = 0.75
        result['signals'].append("meeting_with_pattern")
        return result

    # 9️⃣ Weak create signal
    if create_found:
        result['confidence'] = 0.40
        result['signals'].append("weak_create_only")

    return result



# =============================================================================
# OPTIONAL HELPER
# =============================================================================

def is_create_intent(sentence: str) -> bool:
    """
    Simple boolean wrapper.
    """
    return extract_create_details(sentence)['is_create']


# =============================================================================
# REGEX PATTERNS FOR detect_action()
# =============================================================================

CREATE_PATTERNS = [
    r'\b(create|make|book|schedule|arrange|organize|setup|set up|fix|block|have|host|plan)\s+(?:a|an|the|my|our)?\s*(?:meeting|event|appointment|call|sync|chat|standup|session)\b',
    r'\b(create|make|book|schedule|arrange|organize|setup|set up|fix|block|have|host|plan)\s+(?:a|an)?\s*(?:meeting|event|appointment|call|sync|chat|standup|session)\s+(?:with|at|on|for|tomorrow|today|monday|tuesday|wednesday|thursday|friday|saturday|sunday|week|day|time)\b',
    r'\bschedule\b',
    r'\bbook\b',
    r'\barrange\b',
    r'\borganize\b',
]
