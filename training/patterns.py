"""
Pattern Definitions for Meeting Parser Training
Contains all pattern definitions used for extracting meeting information.
"""

# ============================================================================
# PATTERNS DATABASE
# ============================================================================

# Action to intent mapping
ACTION_TO_INTENT = {
    'schedule_meeting': [
        'schedule', 'set up', 'set a', 'book', 'fix', 'arrange', 
        'create', 'plan', 'block', 'put a', 'add a'
    ],
    'reschedule_meeting': [
        'reschedule', 'move', 'shift', 'push', 'bring forward', 
        'postpone', 'advance'
    ],
    'cancel_meeting': ['cancel', 'delete', 'remove'],
    'update_meeting': ['update', 'change', 'modify', 'edit'],
}

# Location words for online/offline detection
LOCATION_WORDS = [
    'boardroom', 'conference room', 'conference', 'room', 'office', 
    'cabin', 'pantry', 'reception', 'lounge', 'hq', 'building', 
    'floor', 'cafe', 'restaurant',
    'gmeet', 'google meet', 'zoom', 'online', 'virtual', 'remote',
    'in-person', 'face-to-face', 'face to face', 'sit-down', 'sit down',
    'wework', 'mg road', 'at office', 'in office', 'at cabin'
]

# Meeting types
MEETING_TYPES = [
    'meeting', 'call', 'sync', 'discussion', 'appointment', 'demo',
    'standup', 'session', '1:1', 'one-on-one', 'one on one', 
    'catch-up', 'catch up', 'review', 'planning', 'escalation',
    'town hall', 'all hands', 'brainstorm', 'workshop'
]

# Duration patterns (regex, multiplier)
DURATION_PATTERNS = [
    (r'\b(\d+)\s*(?:hour|hr|hrs|hours?)\b', 60),
    (r'\b(\d+)\s*(?:min|minute|mins|minutes)\b', 1),
    (r'\ba\s*n?\s*hour\b', 60),
    (r'\ban\s*n?\s*hour\b', 60),
    (r'\bhalf\s*hour\b', 30),
    (r'\bquarter\s*hour\b', 15),
    (r'\bquick\b', 15),
    (r'\bbrief\b', 15),
    (r'\bshort\b', 15),
]

# Recurrence patterns
RECURRENCE_PATTERNS = [
    r'\bdaily\b', r'\bevery\s*day\b', r'\bweekdays?\b',
    r'\bweekly\b', r'\bevery\s*week\b',
    r'\bmonthly\b', r'\bevery\s*month\b',
]

# Agenda extraction patterns
AGENDA_PATTERNS = [
    (r'\babout\s+([a-zA-Z][a-zA-Z\s]{1,40}[a-zA-Z]?)\b', 1),
    (r'\bfor\s+([a-zA-Z][a-zA-Z\s]{1,40}[a-zA-Z]?)\b', 1),
]

# Attendee extraction patterns
ATTENDEE_PATTERNS = [
    (r'\bwith\s+([A-Z][a-z]+(?:\s+(?:and|&)\s+[A-Z][a-z]+)*)\b', 1),
    (r'\bwith\s+([A-Z][a-z]+(?:\s*,\s*[A-Z][a-z]+)*)\b', 1),
    (r'\bfor\s+([A-Z][a-z]+(?:\s+team)?)\b', 1),
]

# Time modifier patterns
TIME_MODIFIERS = [
    (r'\bby\s+(\d+)\s*(min|minute|minutes)\b', 1),
    (r'\bby\s+(\d+)\s*(hour|hr|hours)\b', 60),
]

# Online/Offline patterns
ONLINE_PATTERNS = [
    r'\bgmeet\b', r'\bgoogle\s*meet\b', r'\bzoom\b',
    r'\bonline\b', r'\bvirtual\b',
]

OFFLINE_PATTERNS = [
    r'\bin\s*boardroom\b', r'\bat\s*boardroom\b', r'\bboardroom\b',
    r'\bin\s*office\b', r'\bin\s*the\s*office\b',
    r'\bin\s*cabin\b', r'\bin\s*cafeteria\b', r'\bin\s*pantry\b',
    r'\bin\s*conference\b', r'\bconference\s*room\b',
    r'\bin-person\b', r'\bface-to-face\b',
]

# Google Meet link pattern
MEET_LINK_PATTERN = r'(https?://)?(meet\.google\.com/|[a-z]{2,3}-meet\.google\.com/)[a-zA-Z0-9_-]+'


__all__ = [
    'ACTION_TO_INTENT',
    'LOCATION_WORDS',
    'MEETING_TYPES',
    'DURATION_PATTERNS',
    'RECURRENCE_PATTERNS',
    'AGENDA_PATTERNS',
    'ATTENDEE_PATTERNS',
    'TIME_MODIFIERS',
    'ONLINE_PATTERNS',
    'OFFLINE_PATTERNS',
    'MEET_LINK_PATTERN',
]
