"""
List Events Patterns Module
Handles pattern recognition for listing/viewing calendar events.
"""

import re
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta, timezone


# =============================================================================
# KEYWORD GROUPS
# =============================================================================

LIST_KEYWORDS: Set[str] = {
    'list', 'lists', 'listed', 'listing',
    'show', 'shows', 'showing', 'showed',
    'view', 'views', 'viewing', 'viewed',
    'display', 'displays', 'displaying', 'displayed',
    'get', 'gets', 'getting',
    'see', 'sees', 'seeing', 'saw',
    'check', 'checks', 'checking', 'checked',
    'fetch', 'fetches', 'fetching',
    'retrieve', 'retrieves', 'retrieving',
    'what', "what's", 'whatis',
    'tell', 'tells', 'telling',
    'give', 'gives', 'giving',
    'load', 'loads', 'loading'
}

EVENT_WORDS: Set[str] = {
    'event', 'events',
    'meeting', 'meetings',
    'appointment', 'appointments',
    'calendar', 'calendars',
    'schedule', 'schedules',
    'slots', 'availability',
    'busy', 'free'
}

# Time period keywords
TODAY_KEYWORDS: Set[str] = {
    'today', 'this day', 'current day'
}

TOMORROW_KEYWORDS: Set[str] = {
    'tomorrow', 'next day', 'following day', 'tmr', 'tmrw'
}

DAY_AFTER_TOMORROW_KEYWORDS: Set[str] = {
    'day after tomorrow', 'day after tmrw', 'day after tmr'
}

THIS_WEEK_KEYWORDS: Set[str] = {
    'this week', 'current week', 'within this week', 'during this week'
}

NEXT_WEEK_KEYWORDS: Set[str] = {
    'next week', 'following week', 'upcoming week'
}

DATE_KEYWORDS: Set[str] = {
    'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
    'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun',
    'january', 'february', 'march', 'april', 'may', 'june',
    'july', 'august', 'september', 'october', 'november', 'december',
    'jan', 'feb', 'mar', 'apr', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'
}

DATE_RANGE_KEYWORDS: Set[str] = {
    'from', 'between', 'range', 'period',
    'start', 'end', 'until'
}

ALL_KEYWORDS: Set[str] = {
    'all', 'every', 'each', 'all of', 'all my', 'all the'
}


# =============================================================================
# TEXT NORMALIZATION
# =============================================================================

def normalize_text(text: str) -> str:
    """
    Normalize input text:
    - Lowercase
    - Remove extra spaces
    - Keep punctuation for date parsing
    - Convert ordinal numbers (1st, 2nd, 3rd, 4th, etc.) to plain numbers
    """
    text = text.lower()
    # Convert ordinal numbers to plain numbers (e.g., "1st" -> "1", "23rd" -> "23")
    text = re.sub(r'\b(\d{1,2})(?:st|nd|rd|th)\b', r'\1', text)
    text = re.sub(r'[^\w\s:/-]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def tokenize(text: str) -> Set[str]:
    """
    Tokenize text into unique words.
    """
    return set(re.findall(r'\b\w+\b', text))


# =============================================================================
# TIME PERIOD DETECTION
# =============================================================================

def detect_time_period(sentence: str) -> Dict[str, any]:
    """
    Detect what time period the user wants to list events for.
    Returns details about the detected period.
    """
    result = {
        'has_time_period': False,
        'period_type': None,  # 'today', 'tomorrow', 'this_week', 'next_week', 'date', 'range', 'all', 'unspecified'
        'start_date': None,
        'end_date': None,
        'confidence': 0.0,
        'clarification_needed': False,
        'signals': []
    }
    
    if not sentence or not sentence.strip():
        result['clarification_needed'] = True
        return result
    
    text = normalize_text(sentence)
    words = text.split()
    word_set = set(words)
    
    # Create a stemmed version for matching
    text_for_matching = text
    
    # Check for ALL events (no specific time)
    all_found = False
    for word in words:
        if word in ALL_KEYWORDS:
            all_found = True
            result['signals'].append(f"all_keyword:{word}")
            break
    
    # Check for date range patterns first (e.g., "from 15 feb to 23 feb", "between 15 and 23 feb", "from today to 23 feb", "from today to tomorrow")
    import re
    
    # Pattern: from today to tomorrow
    range_today_tomorrow = re.search(r'from\s+today\s+to\s+tomorrow', text_for_matching)
    if range_today_tomorrow:
        result['has_time_period'] = True
        result['period_type'] = 'range'
        result['confidence'] = 0.95
        result['start_date'] = 'today'
        result['end_date'] = 'tomorrow'
        result['signals'].append(f"range_today_tomorrow:{range_today_tomorrow.group(0)}")
        return result
    
    # Pattern: from today/tomorrow to DD (month)
    range_from_relative = re.search(r'from\s+(today|tomorrow)\s+to\s+(\d{1,2})\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|may|june|july|august|september|october|november|december)?', text_for_matching)
    if range_from_relative:
        result['has_time_period'] = True
        result['period_type'] = 'range'
        result['confidence'] = 0.95
        result['start_date'] = range_from_relative.group(1)  # 'today' or 'tomorrow'
        result['end_date'] = range_from_relative.group(2)  # end day
        result['end_month'] = range_from_relative.group(3)  # optional month
        result['signals'].append(f"range_from_relative:{range_from_relative.group(0)}")
        return result
    
    # Pattern: from DD to DD (both with optional months)
    range_from_match = re.search(r'from\s+(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|may|june|july|august|september|october|november|december)?\s*to\s+(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|may|june|july|august|september|october|november|december)?', text_for_matching)
    if range_from_match:
        result['has_time_period'] = True
        result['period_type'] = 'range'
        result['confidence'] = 0.95
        result['start_date'] = range_from_match.group(1)  # start day
        result['end_date'] = range_from_match.group(3)  # end day
        result['signals'].append(f"range_from_match:{range_from_match.group(0)}")
        return result
    
    # Pattern: between DD and DD
    range_between_match = re.search(r'between\s+(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|may|june|july|august|september|october|november|december)?\s+(and|to)\s+(\d{1,2})', text_for_matching)
    if range_between_match:
        result['has_time_period'] = True
        result['period_type'] = 'range'
        result['confidence'] = 0.95
        result['start_date'] = range_between_match.group(1)
        result['end_date'] = range_between_match.group(4)
        result['signals'].append(f"range_between_match:{range_between_match.group(0)}")
        return result
    
    # Check for specific dates with month (e.g., "15 feb", "february 15")
    date_with_month = re.search(r'(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|may|june|july|august|september|october|november|december)', text_for_matching)
    if date_with_month:
        result['has_time_period'] = True
        result['period_type'] = 'date'
        result['confidence'] = 0.90
        result['start_date'] = date_with_month.group(1)
        result['end_date'] = date_with_month.group(1)
        result['signals'].append(f"date_with_month:{date_with_month.group(0)}")
        return result
    
    # Check for DAY AFTER TOMORROW (must check before TOMORROW since it contains "tomorrow")
    for phrase in DAY_AFTER_TOMORROW_KEYWORDS:
        if phrase in text_for_matching:
            result['has_time_period'] = True
            result['period_type'] = 'day after tomorrow'
            result['confidence'] = 0.95
            result['signals'].append(f"day_after_tomorrow_keyword:{phrase}")
            return result
    
    # Check for TODAY
    for word in words:
        if word in TODAY_KEYWORDS:
            result['has_time_period'] = True
            result['period_type'] = 'today'
            result['confidence'] = 0.95
            result['signals'].append(f"today_keyword:{word}")
            return result
    
    # Check for TOMORROW
    for word in words:
        if word in TOMORROW_KEYWORDS:
            result['has_time_period'] = True
            result['period_type'] = 'tomorrow'
            result['confidence'] = 0.95
            result['signals'].append(f"tomorrow_keyword:{word}")
            return result
    
    # Check for THIS WEEK
    for phrase in THIS_WEEK_KEYWORDS:
        if phrase in text_for_matching:
            result['has_time_period'] = True
            result['period_type'] = 'this_week'
            result['confidence'] = 0.95
            result['signals'].append(f"this_week_keyword:{phrase}")
            return result
    
    # Check for NEXT WEEK
    for phrase in NEXT_WEEK_KEYWORDS:
        if phrase in text_for_matching:
            result['has_time_period'] = True
            result['period_type'] = 'next_week'
            result['confidence'] = 0.95
            result['signals'].append(f"next_week_keyword:{phrase}")
            return result
    
    # Check for specific date (day of week only)
    for word in words:
        if word in DATE_KEYWORDS:
            result['has_time_period'] = True
            result['period_type'] = 'date'
            result['confidence'] = 0.85
            result['signals'].append(f"date_keyword:{word}")
            return result
    
    # Check for date range keywords
    for word in words:
        if word in DATE_RANGE_KEYWORDS:
            result['has_time_period'] = True
            result['period_type'] = 'range'
            result['confidence'] = 0.80
            result['signals'].append(f"range_keyword:{word}")
            return result
    
    # If we found "all" but no specific time period
    if all_found:
        result['has_time_period'] = True
        result['period_type'] = 'all'
        result['confidence'] = 0.70
        result['signals'].append("all_events_requested")
        return result
    
    # No time period detected - need clarification
    result['clarification_needed'] = True
    result['period_type'] = 'unspecified'
    result['signals'].append("no_time_period_detected")
    
    return result


# =============================================================================
# MAIN DETECTION FUNCTION
# =============================================================================

def extract_list_event_details(sentence: str) -> Dict[str, any]:
    """
    Detect if sentence indicates listing/viewing events.
    Returns intent details and time period information.
    """
    
    result = {
        'is_list_events': False,
        'action': None,
        'intent': None,
        'confidence': 0.0,
        'signals': [],
        'time_period': None
    }
    
    if not sentence or not sentence.strip():
        return result
    
    # 1️⃣ Normalize text
    text = normalize_text(sentence)
    words = text.split()
    word_set = set(words)
    
    # 2️⃣ Check LIST keywords
    list_found = False
    for word in words:
        if word in LIST_KEYWORDS:
            list_found = True
            result['signals'].append(f"list_word:{word}")
            break
    
    # 3️⃣ Check EVENT keywords
    event_found = False
    for word in words:
        if word in EVENT_WORDS:
            event_found = True
            result['signals'].append(f"event_word:{word}")
            break
    
    # 4️⃣ Detect time period
    time_info = detect_time_period(sentence)
    result['time_period'] = time_info
    
    # 5️⃣ Decision Logic
    
    # Case: "list events" or "show events" etc.
    if list_found and event_found:
        result['is_list_events'] = True
        result['action'] = 'list_events'
        result['intent'] = 'view_events'
        
        if time_info['has_time_period']:
            result['confidence'] = 0.95
        else:
            # No time period specified - need clarification
            result['confidence'] = 0.90
            result['signals'].append("needs_clarification")
        
        return result
    
    # Case: Just event-related words (like "my events")
    if event_found and not list_found:
        # Check if it looks like a list request (e.g., "what events do I have")
        question_words = {'what', 'which', 'how', 'do', 'does', 'have', 'any'}
        if any(w in word_set for w in question_words):
            result['is_list_events'] = True
            result['action'] = 'list_events'
            result['intent'] = 'view_events'
            
            if time_info['has_time_period']:
                result['confidence'] = 0.85
            else:
                result['confidence'] = 0.80
                result['signals'].append("needs_clarification")
            
            return result
    
    # Case: List keywords without event words - might be something else
    if list_found:
        # Check if followed by time period - could be listing events
        if time_info['has_time_period']:
            result['is_list_events'] = True
            result['action'] = 'list_events'
            result['intent'] = 'view_events'
            result['confidence'] = 0.60
            result['signals'].append("possible_list_request")
            return result
    
    return result


# =============================================================================
# SIMPLE BOOLEAN WRAPPER
# =============================================================================

def is_list_events_intent(sentence: str) -> bool:
    """
    Simple boolean wrapper to check if sentence is about listing events.
    """
    return extract_list_event_details(sentence)['is_list_events']


def needs_clarification(sentence: str) -> bool:
    """
    Check if the list events request needs time period clarification.
    """
    details = extract_list_event_details(sentence)
    if not details['is_list_events']:
        return False
    
    time_period = details.get('time_period', {})
    return time_period.get('clarification_needed', False)


# =============================================================================
# REGEX PATTERNS FOR detect_action()
# =============================================================================

LIST_EVENTS_PATTERNS = [
    # List events patterns
    r'\b(list|show|view|display|get|check|fetch|retrieve|see)\s+(all\s+)?(my\s+)?(upcoming\s+)?(the\s+)?(events|meetings|appointments|schedule|calendar)\b',
    r'\b(list|show|view|display|get|check|fetch|retrieve|see)\s+(all\s+)?(my\s+)?(upcoming\s+)?(events|meetings|appointments|schedule)\s+(for|on|this|next|today|tomorrow)\b',
    r'\bwhat\s+(events|meetings|appointments|schedule)\b',
    r'\bdo\s+I\s+(have|get)\s+(any\s+)?(upcoming\s+)?(events|meetings|appointments)\b',
    r'\bshow\s+me\s+(my\s+)?(upcoming\s+)?(events|meetings)\b',
    r'\blist\s+my\s+(upcoming\s+)?(events|meetings|schedule)\b',
    r'\bevents\s+for\s+(today|tomorrow|this\s+week|next\s+week)\b',
    r'\bmeetings\s+(today|tomorrow|this\s+week|next\s+week)\b',
    r'\bupcoming\s+(events|meetings|appointments)\b',
    r'\bmy\s+(events|meetings|schedule|calendar)\b',
]

# Combined pattern for detect_action in routes
LIST_PATTERNS = [
    # List events patterns
    r'\b(list|show|view|display|get|check|fetch|retrieve|see)\s+(all\s+)?(my\s+)?(upcoming\s+)?(the\s+)?(events|meetings|appointments|schedule|calendar)\b',
    r'\b(list|show|view|display|get|check|fetch|retrieve|see)\s+(all\s+)?(my\s+)?(upcoming\s+)?(events|meetings|appointments|schedule)\s+(for|on|this|next|today|tomorrow)\b',
    r'\bwhat\s+(events|meetings|appointments|schedule)\b',
    r'\bdo\s+I\s+(have|get)\s+(any\s+)?(upcoming\s+)?(events|meetings|appointments)\b',
    r'\bshow\s+me\s+(my\s+)?(upcoming\s+)?(events|meetings)\b',
    r'\blist\s+my\s+(upcoming\s+)?(events|meetings|schedule)\b',
    r'\bevents\s+for\s+(today|tomorrow|this\s+week|next\s+week)\b',
    r'\bmeetings\s+(today|tomorrow|this\s+week|next\s+week)\b',
    r'\bupcoming\s+(events|meetings|appointments)\b',
    r'\bmy\s+(events|meetings|schedule|calendar)\b',
    # Short patterns for 6 or less words
    r'\blist\s+events\b',
    r'\bshow\s+events\b',
    r'\bview\s+events\b',
    r'\blist\s+meetings\b',
    r'\bshow\s+meetings\b',
    r'\bview\s+meetings\b',
    r'\bmy\s+events\b',
    r'\bmy\s+meetings\b',
    r'\bupcoming\b',
    r'\btoday\s+events\b',
    r'\btomorrow\s+events\b',
    r'\bthis\s+week\b',
    r'\bnext\s+week\b',
    # Reversed order patterns (noun then verb) - "event list" instead of "list events"
    r'\b(event|events|meeting|meetings|appointment|appointments)\s+(list|show|view|display|get|check|fetch|retrieve|see)\b',
    r'\b(event|events)\s+list\b',
    r'\b(meeting|meetings)\s+list\b',
    r'\b(events|meetings)\s+(list|show|view)\b',
]
