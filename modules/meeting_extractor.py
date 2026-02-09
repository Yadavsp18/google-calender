"""
Meeting Extraction Module - Unified Extractor
Combines all extraction modules for complete meeting details.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

from modules.summary import extract_meeting_title
from modules.description import extract_meeting_description, extract_meeting_agenda
from modules.duration import extract_meeting_duration
from modules.location import extract_meeting_location
from modules.attendees import extract_attendees, load_email_book
from modules.date_utils import extract_date, is_date_ambiguous, format_past_date_error
from modules.time_utils import extract_time
from modules.action_utils import extract_action_intent
from modules.link_utils import extract_meeting_link


def extract_meeting_details(
    sentence: str, 
    email_book: list = None, 
    base_dt: datetime = None
) -> Dict[str, Any]:
    """
    Extract complete meeting details from natural language sentence.
    
    Args:
        sentence: The natural language sentence to parse
        email_book: Optional email book for attendee lookup
        base_dt: Optional base datetime for relative date calculations
        
    Returns:
        Dictionary with all meeting details. 
        If date is past, returns {'error': 'past_date', 'details': error_info}
    """
    # Load email book if not provided
    if email_book is None:
        email_book = load_email_book()
    
    # Get current datetime for base
    now = base_dt if base_dt is not None else datetime.now(timezone(timedelta(hours=5, minutes=30)))
    
    # Extract all components
    title = extract_meeting_title(sentence)
    description = extract_meeting_description(sentence)
    agenda = extract_meeting_agenda(sentence)
    duration_min, _ = extract_meeting_duration(sentence)
    location_info = extract_meeting_location(sentence)
    attendees = extract_attendees(sentence, email_book)
    
    # Get meeting link from location_info (not calling extract_meeting_link separately)
    # location_info['location'] contains URL if provided, or 'Online' if not
    # location_info['use_meet'] is True if Google Meet should be auto-generated
    meet_link = location_info.get('location') if not location_info.get('use_meet') else None
    is_auto_generated = location_info.get('use_meet', True)
    
    # Extract date and check if it's in the past
    extracted_date, is_past = extract_date(sentence, base_dt=now)
    
    # Extract time from sentence
    extracted_time = extract_time(sentence)
    
    # Check if date is same as today AND time has already passed
    if extracted_date is not None and extracted_time is not None:
        # Create datetime for the requested meeting
        requested_dt = extracted_date.replace(hour=extracted_time.hour, minute=extracted_time.minute, second=0, microsecond=0)
        # If the requested datetime is in the past (same day but time has passed)
        if requested_dt <= now:
            is_past = True
    
    if extracted_date is not None and is_past:
        # Return error indicator for past date
        error_msg = format_past_date_error(extracted_date, base_dt=now)
        return {
            'error': 'past_date',
            'error_message': error_msg,
            'extracted_date': extracted_date,
            'today': now.replace(hour=0, minute=0, second=0, microsecond=0),
            'action': 'create',
            'intent': 'schedule_meeting',
        }
    
    # Resolve datetime using extracted date and time
    start_dt = None
    if extracted_date:
        # If time was found, use it; otherwise use default (14:00 = 2pm)
        if extracted_time:
            start_dt = extracted_date.replace(hour=extracted_time.hour, minute=extracted_time.minute, second=0, microsecond=0)
        else:
            # No time mentioned - use current default time (14:00 = 2pm)
            start_dt = extracted_date.replace(hour=14, minute=0, second=0, microsecond=0)
    
    # Calculate end time
    end_dt = None
    if start_dt:
        end_dt = start_dt + timedelta(minutes=duration_min)
    
    # Build result
    result = {
        "action": "create",
        "intent": "schedule_meeting",
        "attendees": attendees,
        "attendee_names": [a.get('email', '').replace('@example.com', '').replace('.', ' ').title() for a in attendees],
        "datetime_text": "",
        "duration_min": duration_min,
        "mode": location_info.get('mode', 'online'),
        "location": location_info.get('location', ''),
        "use_meet": location_info.get('use_meet', True),
        "link_preference": location_info.get('link_preference', 'auto_generate_meet'),
        "meet_link": meet_link,
        "is_auto_generated_link": is_auto_generated,
        "agenda": agenda or description,
        "meeting_title": title,
        "constraints": [],
        "time_window": None,
        "recurrence": [],
        "start": start_dt,
        "end": end_dt,
        "description": description,
        "requestId": str(uuid.uuid4()),
        "reminders": {"useDefault": False, "overrides": [{"method": "popup", "minutes": 10}]}
    }
    
    return result


def extract_action_intent_only(sentence: str) -> Dict[str, str]:
    """Extract only action and intent from sentence."""
    return extract_action_intent(sentence)
