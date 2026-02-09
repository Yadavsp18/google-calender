import pytz
import os
import dateparser
import uuid
import json
import re
from datetime import datetime, timedelta, timezone
from dateutil.parser import parse as date_parse
from flask import Flask, redirect, request, session, render_template_string
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload
import tempfile

# Import trained patterns from training module
try:
    from trained_patterns import extract_meeting_details_trained
    USE_TRAINED_MODEL = True
except ImportError:
    USE_TRAINED_MODEL = False
    extract_meeting_details_trained = None


EMAIL_FILE = os.path.join(os.path.dirname(__file__), 'email.json')

def load_email_book():
    if not os.path.exists(EMAIL_FILE):
        return []
    with open(EMAIL_FILE, 'r') as f:
        return json.load(f)

EMAIL_BOOK = load_email_book()


os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)
app.secret_key = 'super-secret-fixed-key-78910'

SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/drive.file'
]


CLIENT_SECRETS_FILE = os.path.join(os.path.dirname(__file__), 'credentials.json')
TOKEN_FILE = os.path.join(os.path.dirname(__file__), 'token.json')
REDIRECT_URI = 'http://localhost:8000/oauth/callback/'

# Load API key from credentials file
def load_api_key():
    if os.path.exists(CLIENT_SECRETS_FILE):
        with open(CLIENT_SECRETS_FILE, 'r') as f:
            creds_data = json.load(f)
            return creds_data.get('web', {}).get('api_key', '')
    return ''

API_KEY = load_api_key()

def creds_to_dict(creds):
    """Convert credentials object to dictionary for session storage."""
    return {
        'token': creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri,
        'client_id': creds.client_id,
        'client_secret': creds.client_secret,
        'scopes': creds.scopes,
        'expiry': creds.expiry.isoformat() if creds.expiry else None
    }

def get_service():
    """Get Google Calendar service, refreshing tokens if needed."""
    data = None

    # First, try to load from file (works outside request context)
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, 'r') as f:
                data = json.load(f)
        except Exception:
            data = None
    
    # Then try session (only if in request context)
    try:
        if 'credentials' in session:
            session_data = session.get('credentials')
            if session_data:
                data = session_data
    except RuntimeError:
        # Outside request context, session is not available
        pass
    
    if not data:
        return None

    if data.get('expiry'):
        data['expiry'] = date_parse(data['expiry'])

    creds = Credentials(
        token=data.get('token'),
        refresh_token=data.get('refresh_token'),
        token_uri=data.get('token_uri'),
        client_id=data.get('client_id'),
        client_secret=data.get('client_secret'),
        scopes=data.get('scopes')
    )

    if not creds.refresh_token:
        # Try to clean up session if available
        try:
            session.pop('credentials', None)
        except RuntimeError:
            pass
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
        return None

    if creds.expired:
        creds.refresh(Request())

    # Only save to session if in request context
    try:
        session['credentials'] = creds_to_dict(creds)
    except RuntimeError:
        # Outside request context, don't save to session
        pass

    return build('calendar', 'v3', credentials=creds)

def find_email_by_name(name):
    if not name:
        return None

    name = name.lower().strip()

    for entry in EMAIL_BOOK:
        entry_name = entry.get("name", "").lower()
        # Exact match OR entry_name contains the search name as a standalone word
        # Split entry_name into words and check if search name matches any word exactly
        entry_words = entry_name.split()
        if name == entry_name or name in entry_words:
            return entry.get("email")

    return None


def delete_meeting(meeting_id):
    """
    Delete/cancel a meeting by its event ID.
    
    Args:
        meeting_id: The Google Calendar event ID to delete
    
    Returns:
        dict: Result containing success status and message
    """
    # Try to get service - handles both request context and standalone use
    try:
        service = get_service()
    except RuntimeError:
        # Outside request context, try to load credentials from file
        service = None
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'r') as f:
                data = json.load(f)
            if data.get('expiry'):
                data['expiry'] = date_parse(data['expiry'])
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            creds = Credentials(
                token=data.get('token'),
                refresh_token=data.get('refresh_token'),
                token_uri=data.get('token_uri'),
                client_id=data.get('client_id'),
                client_secret=data.get('client_secret'),
                scopes=data.get('scopes')
            )
            if creds.refresh_token:
                if creds.expired:
                    creds.refresh(Request())
                service = build('calendar', 'v3', credentials=creds)
    
    if not service:
        return {
            'success': False,
            'error': 'Not authenticated or invalid credentials'
        }
    
    try:
        # First, get the event to return its details
        event = service.events().get(calendarId='primary', eventId=meeting_id).execute()
        event_summary = event.get('summary', 'Untitled Event')
        
        # Delete the event
        service.events().delete(calendarId='primary', eventId=meeting_id).execute()
        
        return {
            'success': True,
            'message': f'Meeting "{event_summary}" has been deleted successfully',
            'deleted_event': event_summary
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def resolve_datetime_from_text(text, base_dt=None):
    """Extract date/time from natural language text."""
    if base_dt is None:
        base_dt = datetime.now()
    
    text = text.lower().strip()
    now = base_dt
    
    # Relative time expressions
    # Check "tomorrow eod" or "tomorroweod" first (end of day tomorrow)
    if re.search(r'\b(tomorrow|tmrw)\s*eod\b|\b(tomorrow|tmrw)eod\b', text):
        dt = (now + timedelta(days=1)).replace(hour=17, minute=0, second=0, microsecond=0)
        return _apply_time_match(text, dt, now)
    
    # Check "tomorrow cob" or "tomorrowcob" (close of business)
    if re.search(r'\b(tomorrow|tmrw)\s*cob\b|\b(tomorrow|tmrw)cob\b', text):
        dt = (now + timedelta(days=1)).replace(hour=17, minute=0, second=0, microsecond=0)
        return _apply_time_match(text, dt, now)
    
    # Check "tomorrow" or "tmrw" (default 6 PM if no explicit time)
    if re.search(r'\b(tomorrow|tmrw)\b', text):
        dt = (now + timedelta(days=1)).replace(hour=18, minute=0, second=0, microsecond=0)
        return _apply_time_match(text, dt, now)
    
    if re.search(r'\bday after tomorrow\b', text):
        dt = (now + timedelta(days=2)).replace(hour=9, minute=0, second=0, microsecond=0)
        return _apply_time_match(text, dt, now)
    
    if re.search(r'\byesterday\b', text):
        dt = (now - timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
        return _apply_time_match(text, dt, now)
    
    # Check "today eod" or "today cob" BEFORE general "today" check
    if re.search(r'\b(today)\s*eod\b|\b(today)eod\b', text):
        dt = now.replace(hour=17, minute=0, second=0, microsecond=0)
        if dt <= now:
            dt += timedelta(days=1)
        return _apply_time_match(text, dt, now)
    
    if re.search(r'\b(today)\s*cob\b|\b(today)cob\b', text):
        dt = now.replace(hour=17, minute=0, second=0, microsecond=0)
        if dt <= now:
            dt += timedelta(days=1)
        return _apply_time_match(text, dt, now)
    
    # General "today" check (only if no eod/cob specified)
    if re.search(r'\btoday\b', text):
        dt = now + timedelta(hours=1)
        return _apply_time_match(text, dt, now)
    
    rel = re.search(r'\b(in|after)\s+(\d+)\s*(hour|hr|minute|min|day|days)s?', text)
    if rel:
        value = int(rel.group(2))
        unit = rel.group(3).lower()
        if 'hour' in unit:
            dt = now + timedelta(hours=value)
        elif 'minute' in unit:
            dt = now + timedelta(minutes=value)
        elif 'day' in unit:
            dt = (now + timedelta(days=value)).replace(hour=9, minute=0, second=0, microsecond=0)
        return _apply_time_match(text, dt, now)
    
    # General EOD/COB handling (when no specific day is mentioned)
    if re.search(r'\b(eod|cob)\b', text):
        dt = now.replace(hour=17, minute=0, second=0, microsecond=0)
        if dt <= now:
            dt += timedelta(days=1)
        return _apply_time_match(text, dt, now)
    
    if re.search(r'\beow\b', text):
        days_until_friday = (4 - now.weekday()) % 7
        if days_until_friday == 0 and now.weekday() == 4 and now.hour >= 17:
            days_until_friday = 7
        dt = (now + timedelta(days=days_until_friday)).replace(hour=17, minute=0, second=0, microsecond=0)
        return _apply_time_match(text, dt, now)
    
    if re.search(r'\beom\b', text):
        if now.month == 12:
            dt = now.replace(year=now.year + 1, month=1, day=1, hour=17, minute=0, second=0, microsecond=0)
        else:
            dt = now.replace(month=now.month + 1, day=1, hour=17, minute=0, second=0, microsecond=0)
        return _apply_time_match(text, dt, now)
    
    # Weekday expressions
    weekday_dt = resolve_weekday(text, now)
    if weekday_dt:
        return _apply_time_match(text, weekday_dt, now)
    
    this_next_pattern = re.search(r'\b(this|next|coming|on)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', text)
    if this_next_pattern:
        modifier = this_next_pattern.group(1)
        if modifier == "on":
            modifier = "this"
        day_name = this_next_pattern.group(2)
        weekday_map = {
            "monday": 0, "tuesday": 1, "wednesday": 2,
            "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6
        }
        target_day = weekday_map[day_name]
        days_ahead = (target_day - now.weekday()) % 7
        
        if modifier == "next" or (modifier == "this" and days_ahead == 0):
            days_ahead += 7
        elif modifier == "this" and days_ahead == 0:
            days_ahead = 0
        
        dt = (now + timedelta(days=days_ahead)).replace(hour=9, minute=0, second=0, microsecond=0)
        return _apply_time_match(text, dt, now)
    
    bare_weekday_pattern = re.search(r'\bon\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', text)
    if bare_weekday_pattern:
        day_name = bare_weekday_pattern.group(1)
        weekday_map = {
            "monday": 0, "tuesday": 1, "wednesday": 2,
            "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6
        }
        target_day = weekday_map[day_name]
        days_ahead = (target_day - now.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        dt = (now + timedelta(days=days_ahead)).replace(hour=9, minute=0, second=0, microsecond=0)
        return _apply_time_match(text, dt, now)
    
    # Month/date expressions
    month_map = {
        "january": 1, "jan": 1,
        "february": 2, "feb": 2,
        "march": 3, "mar": 3,
        "april": 4, "apr": 4,
        "may": 5,
        "june": 6, "jun": 6,
        "july": 7, "jul": 7,
        "august": 8, "aug": 8,
        "september": 9, "sep": 9, "sept": 9,
        "october": 10, "oct": 10,
        "november": 11, "nov": 11,
        "december": 12, "dec": 12
    }
    
    month_date_pattern = r'(?:on\s+)?(\d{1,2})(?:st|nd|rd|th)?\s*(?:of\s+)?(' + '|'.join(month_map.keys()) + r')?|\b(' + '|'.join(month_map.keys()) + r')\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s+on)?\b'
    month_date_pattern = re.search(month_date_pattern, text)
    
    if month_date_pattern:
        groups = month_date_pattern.groups()
        day = None
        month = None
        
        if groups[0] and groups[1]:
            day = int(groups[0])
            month_name = groups[1] if groups[1] else groups[2]
            month = month_map.get(month_name.lower() if month_name else '')
        elif groups[2] and groups[3]:
            month_name = groups[2]
            day = int(groups[3])
            month = month_map.get(month_name.lower())
        
        if day and month:
            try:
                dt = now.replace(month=month, day=day, hour=9, minute=0, second=0, microsecond=0)
                if dt <= now:
                    dt = dt.replace(year=now.year + 1)
                return _apply_time_match(text, dt, now)
            except ValueError:
                pass
    
    # "This [day of month]" expressions
    this_day_pattern = re.search(r'\bthis\s+(\d{1,2})(?:st|nd|rd|th)?\b', text)
    if this_day_pattern:
        day = int(this_day_pattern.group(1))
        try:
            dt = now.replace(day=day, hour=9, minute=0, second=0, microsecond=0)
            if dt <= now:
                if now.month == 12:
                    dt = dt.replace(year=now.year + 1, month=1)
                else:
                    dt = dt.replace(month=now.month + 1)
            return _apply_time_match(text, dt, now)
        except ValueError:
            pass
    
    # Relative week expressions
    if re.search(r'\bnext week\b', text):
        dt = (now + timedelta(weeks=1)).replace(hour=9, minute=0, second=0, microsecond=0)
        return _apply_time_match(text, dt, now)
    
    if re.search(r'\bthis week\b', text):
        for day_name in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
            if day_name in text:
                dt = resolve_weekday(text, now)
                if dt:
                    return _apply_time_match(text, dt, now)
        days_until_monday = (7 - now.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        dt = (now + timedelta(days=days_until_monday)).replace(hour=9, minute=0, second=0, microsecond=0)
        return _apply_time_match(text, dt, now)
    
    # Relative month expressions
    if re.search(r'\bnext month\b', text):
        if now.month == 12:
            dt = now.replace(year=now.year + 1, month=1, day=1, hour=9, minute=0, second=0, microsecond=0)
        else:
            dt = now.replace(month=now.month + 1, day=1, hour=9, minute=0, second=0, microsecond=0)
        return _apply_time_match(text, dt, now)
    
    # Dateparser fallback
    dt = dateparser.parse(
        text,
        settings={
            "RELATIVE_BASE": now,
            "PREFER_DATES_FROM": "future",
            "STRICT_PARSING": False,
            "PREFER_DAY_OF_MONTH": "first",
        }
    )
    
    if dt:
        return _apply_time_match(text, dt, now)
    
    # Generic date patterns
    iso_match = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', text)
    if iso_match:
        try:
            year, month, day = int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3))
            dt = datetime(year, month, day, 9, 0, 0)
            return _apply_time_match(text, dt, now)
        except ValueError:
            pass
    
    us_match = re.search(r'(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})', text)
    if us_match:
        try:
            month, day, year = int(us_match.group(1)), int(us_match.group(2)), int(us_match.group(3))
            if year < 100:
                year += 2000
            dt = datetime(year, month, day, 9, 0, 0)
            return _apply_time_match(text, dt, now)
        except ValueError:
            pass
    
    return _apply_time_match(text, now + timedelta(hours=1), now)


def _apply_time_match(text, dt, base_dt):
    """Apply explicit time patterns to a date."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=base_dt.tzinfo)
    
    # 12-hour format with am/pm
    time_match = re.search(r'(?:at\s+)?(\d{1,2})(:(\d{2}))?\s*(am|pm)', text, re.IGNORECASE)
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(3)) if time_match.group(3) else 0
        ampm = time_match.group(4).lower()
        
        if ampm == 'pm' and hour != 12:
            hour += 12
        elif ampm == 'am' and hour == 12:
            hour = 0
        
        dt = dt.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    # 24-hour format
    time_24 = re.search(r'(?:at\s+)?(\d{1,2}):(\d{2})(?::\d{2})?(?!\s*(?:am|pm))', text)
    if time_24 and not time_match:
        hour = int(time_24.group(1))
        minute = int(time_24.group(2))
        dt = dt.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    # Standalone number like "10" in "morning 10" (without am/pm)
    # Pattern: "morning 10", "afternoon 3", "evening 6"
    standalone_time = re.search(r'\b(morning|afternoon|evening|night)\s+(\d{1,2})\b', text, re.IGNORECASE)
    if standalone_time and not time_match and not time_24:
        time_period = standalone_time.group(1).lower()
        hour = int(standalone_time.group(2))
        # For afternoon/evening/night, assume PM if hour < 12
        if time_period in ['afternoon', 'evening', 'night'] and hour < 12:
            hour += 12
        # For hours 6-9 in evening/night context, default to PM
        elif time_period in ['evening', 'night'] and 6 <= hour <= 9:
            hour += 12  # 6-9 PM (18:00-21:00)
        dt = dt.replace(hour=hour, minute=0, second=0, microsecond=0)
    
    # Handle standalone hours 6-9 without AM/PM (common meeting times)
    # Pattern: "at 6", "at 7", "at 8", "at 9" without AM/PM
    standalone_hour = re.search(r'\bat\s+(\d{1,2})(?!:\d{2})\b(?!.*\b(am|pm|a\.m\.|p\.m\.)\b)', text, re.IGNORECASE)
    if standalone_hour and not time_match and not time_24 and not standalone_time:
        hour = int(standalone_hour.group(1))
        # Default hours 6-9 to PM (18:00-21:00) for typical meeting times
        if 6 <= hour <= 9:
            hour += 12
        dt = dt.replace(hour=hour, minute=0, second=0, microsecond=0)
    
    # Time of day defaults (only if no explicit time was found)
    if not time_match and not time_24 and not standalone_time:
        if re.search(r'\bmorning\b', text):
            dt = dt.replace(hour=9, minute=0, second=0, microsecond=0)
        elif re.search(r'\bafternoon\b', text):
            dt = dt.replace(hour=14, minute=0, second=0, microsecond=0)
        elif re.search(r'\bevening\b', text):
            dt = dt.replace(hour=18, minute=0, second=0, microsecond=0)
    
    if re.search(r'\btonight\b', text):
        dt = dt.replace(hour=18, minute=0, second=0, microsecond=0)
    
    if re.search(r'\b(?:at\s+)?noon\b', text):
        dt = dt.replace(hour=12, minute=0, second=0, microsecond=0)
    
    if re.search(r'\b(?:at\s+)?midnight\b', text):
        dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    
    is_past_reference = re.search(r'\b(yesterday|today)\b', text)
    if not is_past_reference and dt <= base_dt:
        dt += timedelta(days=1)
    
    return dt


def resolve_weekday(text, base_dt):
    """Resolve weekday expressions like 'next friday', 'this monday'."""
    weekdays = {
        "monday": 0, "tuesday": 1, "wednesday": 2,
        "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6
    }
    
    for day, idx in weekdays.items():
        if re.search(r'\b(?:on\s+)?' + day + r'\b', text):
            days_ahead = (idx - base_dt.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            return (base_dt + timedelta(days=days_ahead)).replace(
                hour=9, minute=0, second=0, microsecond=0
            )
    
    return None


def extract_meeting_details_fallback(sentence):
    """Fallback extraction function when trained model is not available."""
    text = sentence.lower().strip()
    now = datetime.now()
    
    details = {}

    def generate_summary(text, start_dt=None):
        """Generate summary and description using the parsed start date/time."""
        result = {"summary": "Meeting", "description": ""}
        
        text_lower = text.lower()
        
        if start_dt is None:
            start_dt = resolve_datetime_from_text(text, datetime.now())

        day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        day = day_names[start_dt.weekday()].title() if start_dt else None
        time_str = start_dt.strftime("%#I:%M %p") if start_dt else None
        
        meeting_match = re.search(
            r"\b(meeting|call|discussion|appointment|sync|video call|gym|workout|task|reminder|standup|demo|lunch)\b",
            text_lower
        )
        meeting_type = meeting_match.group(1).title() if meeting_match else "Event"
        
        # Attendee extraction
        comma_pattern = r'\bwith\s+([a-zA-Z]+(?:\s*,\s*[a-zA-Z]+(?:\s*,\s*[a-zA-Z]+)*))\b'
        comma_match = re.search(comma_pattern, text_lower)
        
        attendees_list = []
        if comma_match:
            names_str = comma_match.group(1)
            attendees_list = [name.strip().title() for name in names_str.split(',')]
        else:
            and_pattern = r'\bwith\s+([a-zA-Z]+(?:\s+(?:and|&)\s+[a-zA-Z]+(?:\s+(?:and|&)\s+[a-zA-Z]+)*))\b'
            and_match = re.search(and_pattern, text_lower)
            if and_match:
                names_str = and_match.group(1)
                names = re.split(r'\s+(?:and|&)\s+', names_str)
                attendees_list = [name.strip().title() for name in names if name.strip()]
        
        if not attendees_list:
            single_match = re.search(r"\bwith\s+([a-zA-Z]{2,15})\b", text_lower)
            attendee = single_match.group(1).title() if single_match else None
            attendees_list = [attendee] if attendee else []
        
        if len(attendees_list) == 1:
            attendee_str = f"with {attendees_list[0]}"
        elif len(attendees_list) == 2:
            attendee_str = f"with {attendees_list[0]} and {attendees_list[1]}"
        elif len(attendees_list) > 2:
            attendee_str = "with " + ", ".join(attendees_list[:-1]) + f", and {attendees_list[-1]}"
        else:
            attendee_str = ""

        result["attendee_names"] = [a for a in attendees_list if a]

        # Duration
        duration_match = re.search(r'\bfor\s+(\d+)\s*(min|minutes?|hr|hours?)\b|\b(\d+)\s*(min|minutes?|hr|hours?)\b', text_lower)
        duration = "1 hr"
        if duration_match:
            duration_num = duration_match.group(1) or duration_match.group(3)
            duration = f"{duration_num} min"
        
        # Topic/Reason
        topic_text = text_lower
        if day:
            topic_text = re.sub(rf'\b{day.lower()}\b', '', topic_text)
        if time_str:
            topic_text = re.sub(rf'{re.escape(time_str)}', '', topic_text, flags=re.IGNORECASE)
        
        reason_match = re.search(
            r"(?:to\s+(?:discuss|talk\s+about|review)|about|regarding|for)\s+([a-zA-Z][a-zA-Z\s]{1,50}[a-zA-Z]?)",
            topic_text
        )
        reason = reason_match.group(1).strip().title() if reason_match else ""
        reason = re.sub(r'\b(the|a|an|to|for|on|at)\b', '', reason).strip()
        reason = re.sub(r'\s+', ' ', reason)
        result["reason"] = reason

        # Summary
        summary_parts = [meeting_type]
        if attendee_str:
            summary_parts.append(attendee_str)
        if reason:
            summary_parts.append(f"{reason}")
        if time_str and day:
            summary_parts.append(f"at {time_str} on {day}")
        
        result["summary"] = " ".join(summary_parts).strip()

        # Description
        if day and time_str:
            date_time = f"{day} at {time_str}"
        elif day:
            date_time = day
        elif time_str:
            date_time = time_str
        else:
            date_time = "Not specified"

        purpose = reason if reason else "Discussion"
        
        if details.get("location") == "Online":
            location = "Google Meet"
            physical_address = "N/A (Online Meeting)"
        elif details.get("use_meet", False):
            location = "Google Meet"
            physical_address = "N/A"
        else:
            location = "In-person"
            physical_address = details.get("location") or "Not specified"

        result["description"] = (
            f"Date & Time: {date_time}\n"
            f"Purpose: {purpose}\n"
            f"Location: {location}\n"
            f"Physical Address: {physical_address}\n"
        )

        return result

    # Location handling
    physical_indicators = [
    # Office & workplace
    "office", "office room", "meeting room", "conference room", "boardroom",
    "cabin", "workspace", "cubicle", "floor", "building", "wing",
    "hq", "headquarters", "branch", "campus",

    # Inside office common areas
    "reception", "lobby", "pantry", "cafeteria", "break room",
    "training room", "war room", "lab",

    # External indoor places
    "conference center", "business center", "coworking space",
    "wework", "regus",

    # Public places
    "cafe", "coffee shop", "restaurant", "hotel", "hotel lobby",
    "mall", "food court",

    # Specific locations
    "address", "location", "site", "venue", "premises",
    "client office", "customer office", "their office",

    # Outdoor / misc
    "street", "campus", "park",

    # Rooms by letter/number
    "room a", "room b", "room 1", "room 2", "hall", "auditorium"
    ]

    online_indicators = [
    # Generic virtual terms
    "online", "virtual", "remote", "video", "video call",
    "audio call", "conference call",

    # Popular platforms
    "zoom", "google meet", "gmeet", "microsoft teams", "teams",
    "webex", "cisco webex", "skype", "slack huddle",
    "gotomeeting", "bluejeans", "jitsi",

    # Links & tech hints
    "meeting link", "join link", "call link", "invite link",
    "calendar link",

    # Streaming / webinar
    "webinar", "livestream", "live session",

    # Casual language
    "quick call", "sync call", "catch-up call", "standup call"
    ]

    
    details["location"] = ""
    
    # Check for explicit Google Meet link first
    meet_link_pattern = r'(https?://)?(meet\.google\.com/|[a-z]{2,3}-meet\.google\.com/)[a-zA-Z0-9_-]+'
    meet_link_match = re.search(meet_link_pattern, sentence, re.IGNORECASE)
    if meet_link_match:
        details["location"] = "Online"
        details["use_meet"] = True
        details["link_preference"] = "use_provided_link"
        meet_link = meet_link_match.group(0)
        if not meet_link.startswith('http'):
            meet_link = 'https://' + meet_link
        details["meet_link"] = meet_link
    elif any(indicator in text for indicator in online_indicators):
        details["location"] = "Online"
        details["use_meet"] = True
    else:
        physical_patterns = [
            r'(?:at|in)\s+(room(?:\s*|#|number)?\s*[0-9a-zA-Z]+)',
            r'(?:at|in)\s+(conference(?:\s*room)?\s*[0-9a-zA-Z]+)',
            r'(?:at|in)\s+([a-zA-Z][a-zA-Z0-9\s,\-\'\.]+(?:cafe|restaurant|office|center|hq))',
        ]
        
        for pattern in physical_patterns:
            physical_match = re.search(pattern, sentence, re.IGNORECASE)
            if physical_match:
                details["location"] = physical_match.group(1).strip()
                break
    
    # Parse datetime
    # Resolve start datetime
    start_dt = resolve_datetime_from_text(sentence, now)
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))

    summary_result = generate_summary(sentence, start_dt)
    details["summary"] = summary_result["summary"]
    details["description"] = summary_result["description"]

    end_dt = None

    ambiguous_match = re.search(r'\bat\s+(\d{1,2})(?!\s*(?:am|pm|:\d{2}))', sentence, re.IGNORECASE)
    if ambiguous_match:
        hour = int(ambiguous_match.group(1))
        if 1 <= hour <= 12:
            details['ambiguous_hour'] = hour
            print(f"🔍 Ambiguous time '{hour}' detected - popup will confirm AM/PM")
    # ============ END ADD ============

    # -------------------------------------------------
    # 1️⃣ Try to extract explicit END TIME (6 to 7pm, 6pm - 7pm, till 7, etc.)
    # -------------------------------------------------
    def extract_explicit_end_time(sentence, start_dt):
        match = re.search(
            r'\b(?:to|-|till|until)\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b',
            sentence,
            re.IGNORECASE
        )

        if not match:
            return None

        hour = int(match.group(1))
        minute = int(match.group(2) or 0)
        ampm = match.group(3)

        # Infer AM/PM if missing
        if ampm:
            if ampm.lower() == "pm" and hour < 12:
                hour += 12
            elif ampm.lower() == "am" and hour == 12:
                hour = 0
        else:
            if start_dt.hour >= 12 and hour < 12:
                hour += 12

        end_dt = start_dt.replace(
            hour=hour,
            minute=minute,
            second=0,
            microsecond=0
        )

        if end_dt <= start_dt:
            end_dt += timedelta(hours=1)

        return end_dt
    explicit_end = extract_explicit_end_time(sentence, start_dt)
    if explicit_end:
        end_dt = explicit_end
        duration_minutes = int((end_dt - start_dt).total_seconds() / 60)
    elif is_update and existing_event:
        old_start = parse(existing_event['start']['dateTime'])
        old_end = parse(existing_event['end']['dateTime'])
        duration_minutes = int((old_end - old_start).total_seconds() / 60)
        end_dt = start_dt + timedelta(minutes=duration_minutes)
    else:
        duration_minutes = 60  # default

    if re.search(r'\b(quick|brief|short)\b', sentence):
        duration_minutes = 15
    elif re.search(r'\bhalf\s*hour\b', sentence):
        duration_minutes = 30

    end_dt = start_dt + timedelta(minutes=duration_minutes)





    # -------------------------------------------------
    # 3️⃣ Final assignment
    # -------------------------------------------------
    details["start"] = start_dt
    details["end"] = end_dt
    details["duration_min"] = duration_minutes

    
    # Attendees
    details["attendees"] = [{"email": e} for e in re.findall(r'[\w\.-]+@[\w\.-]+', sentence)]
    
    comma_pattern = r'\bwith\s+([a-zA-Z]+(?:\s*,\s*[a-zA-Z]+(?:\s*,\s*[a-zA-Z]+)*))'
    comma_match = re.search(comma_pattern, sentence, re.IGNORECASE)
    
    person_names = []
    if comma_match:
        names_str = comma_match.group(1)
        person_names = [name.strip() for name in names_str.split(',')]
    else:
        and_pattern = r'\bwith\s+([a-zA-Z]+(?:\s+(?:and|&)\s+[a-zA-Z]+(?:\s+(?:and|&)\s+[a-zA-Z]+)*))'
        and_match = re.search(and_pattern, sentence, re.IGNORECASE)
        if and_match:
            names_str = and_match.group(1)
            person_names = re.split(r'\s+(?:and|&)\s+', names_str)
            person_names = [name.strip() for name in person_names if name.strip()]
    
    if not person_names:
        single_match = re.search(r'\bwith\s+([a-zA-Z]+(?:\s+[a-zA-Z]+){0,2})', sentence, re.IGNORECASE)
        if single_match:
            person_names = [single_match.group(1).strip()]
    
    attendees_emails = []
    for person_name in person_names:
        email = find_email_by_name(person_name)
        if email:
            attendees_emails.append({"email": email})
        else:
            fallback_email = person_name.lower().replace(" ", ".") + "@example.com"
            if {"email": fallback_email} not in attendees_emails:
                attendees_emails.append({"email": fallback_email})
    
    if attendees_emails:
        details["attendees"] = attendees_emails

    details["requestId"] = str(uuid.uuid4())
    details["reminders"] = {"useDefault": False, "overrides": [{"method": "popup", "minutes": 10}]}
    details["recurrence"] = []

    if re.search(r'\b(weekly|every\s*week|recurring)\b', text):
        details["recurrence"] = ['RRULE:FREQ=WEEKLY']
    if re.search(r'\b(daily|every\s*day)\b', text):
        details["recurrence"] = ['RRULE:FREQ=DAILY']
    if re.search(r'\b(monthly|every\s*month)\b', text):
        details["recurrence"] = ['RRULE:FREQ=MONTHLY']

    return details


def extract_meeting_details(sentence):
    """
    Extract meeting details from natural language sentence.
    Uses trained model from testcases.json when available.
    """
    # Use trained model if available
    if USE_TRAINED_MODEL and extract_meeting_details_trained:
        result = extract_meeting_details_trained(sentence)
        
        # Resolve attendee emails using email book
        for i, attendee in enumerate(result.get('attendees', [])):
            if '@example.com' in attendee.get('email', ''):
                # Try to find real email
                name = attendee['email'].replace('@example.com', '').replace('.', ' ').title()
                real_email = find_email_by_name(name)
                if real_email:
                    result['attendees'][i]['email'] = real_email
        
        return result
    
    # Fallback to original implementation
    return extract_meeting_details_fallback(sentence)


def get_drive_service():
    data = session.get('credentials')
    if not data:
        return None

    if data.get('expiry'):
        data['expiry'] = date_parse(data['expiry'])

    creds = Credentials(
        token=data.get('token'),
        refresh_token=data.get('refresh_token'),
        token_uri=data.get('token_uri'),
        client_id=data.get('client_id'),
        client_secret=data.get('client_secret'),
        scopes=data.get('scopes')
    )

    if creds.expired:
        creds.refresh(Request())

    return build('drive', 'v3', credentials=creds)

def upload_file_to_drive(file_storage):
    drive = get_drive_service()
    if not drive:
        return None

    import tempfile
    import io
    from googleapiclient.http import MediaFileUpload

    # Read file content into memory first, then write to temp
    file_content = file_storage.read()
    file_storage.seek(0)  # Reset file pointer for potential reuse
    
    # Create temp file with delete=False so we can control cleanup
    with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix=os.path.splitext(file_storage.filename)[1]) as temp_file:
        temp_path = temp_file.name
        temp_file.write(file_content)
    
    try:
        media = MediaFileUpload(
            temp_path,
            mimetype=file_storage.mimetype,
            resumable=True
        )

        uploaded = drive.files().create(
            body={"name": file_storage.filename},
            media_body=media,
            fields="id"
        ).execute()

        return uploaded.get("id")
    finally:
        # Cleanup temp file after upload is complete
        try:
            os.remove(temp_path)
        except OSError:
            pass  # File may already be deleted or locked




@app.route('/')
def index():
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>Google Calendar Meeting Creator</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .section { margin: 20px 0; padding: 20px; border: 1px solid #ccc; border-radius: 5px; }
        h2 { color: #333; }
        input[type="text"] { padding: 8px; margin: 5px 0; }
        input[type="submit"] { padding: 8px 16px; background: #4285f4; color: white; border: none; border-radius: 4px; cursor: pointer; }
        input[type="submit"]:hover { background: #3367d6; }
        a { color: #4285f4; }
        .examples { background: #f0f0f0; padding: 10px; margin: 10px 0; border-radius: 5px; font-size: 14px; }
    </style>
</head>
                                  <script src="https://apis.google.com/js/api.js"></script>

<script>
let oauthToken = {% if session.get('credentials') %}"{{ session['credentials']['token'] }}"{% else %}null{% endif %};

function openDrivePicker() {
    gapi.load('picker', {'callback': createPicker});
}

function createPicker() {
    const picker = new google.picker.PickerBuilder()
        .addView(google.picker.ViewId.DOCS)
        .setOAuthToken(oauthToken)
        .setDeveloperKey("{{ api_key }}")
        .setCallback(pickerCallback)
        .build();
    picker.setVisible(true);
}

function pickerCallback(data) {
    if (data.action === google.picker.Action.PICKED) {
        const file = data.docs[0];
        document.getElementById("drive_file_id").value = file.id;
        document.getElementById("file-name").innerText =
            "Selected file: " + file.name;
    }
}
</script>

<body>
    <h1>📅 Google Calendar Meeting Creator</h1>
    
    <div class="section">
        <h3>🔐 Authentication</h3>
        {% if session.get('credentials') %}
            <p>✅ You are authenticated!</p>
            <a href="/logout"><input type="submit" value="Logout"></a>
        {% else %}
            <a href="/authorize"><input type="submit" value="Connect Google Calendar"></a>
        {% endif %}
    </div>
    
    {% if session.get('credentials') %}
    <div class="section">
        <h3>📝 Create Meeting via Sentence</h3>
        <form action="/nlp_create" method="post" enctype="multipart/form-data" id="meetingForm">
    Describe the meeting:
    <input type="text" name="sentence" id="sentenceInput" size="80" required><br><br>
    
    <!-- ADD THIS LINE - MISSING FILE INPUT -->
    <input type="file" name="attachment"><br><br>
    
    Attach file (optional):
    <input type="hidden" name="drive_file_id" id="drive_file_id">
    <button type="button" onclick="openDrivePicker()">📁 Choose from Google Drive</button>
    <p id="file-name"></p>
    
    <input type="submit" value="Create Meeting">
</form>




    </div>
    
    <div class="section">
        <h3>🗑️ Cancel/Delete Meeting</h3>
        <form action="/nlp_create" method="post">
    Describe the meeting to cancel (e.g., "Cancel my meeting with John tomorrow" or "Delete the marketing plan discussion"):
    <input type="text" name="sentence" size="80" required><br><br>
    <input type="submit" value="Cancel Meeting" style="background: #dc3545;">
</form>
    </div>
    
    <div class="section">
        <h3>📋 Upcoming Events</h3>
        <a href="/events"><input type="submit" value="View Events"></a>
    {% endif %}
</body>
</html>
    ''')


@app.route('/authorize')
def authorize():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES)
    
    flow.redirect_uri = REDIRECT_URI
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true')
    
    session['state'] = state
    
    return redirect(authorization_url)


@app.route('/oauth/callback/')
def oauth_callback():
    # Get state from session or from request args (Google sends it back)
    state = session.get('state', request.args.get('state'))
    
    if not state:
        return "Error: Missing state parameter. Please start the OAuth flow from /authorize", 400
    
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES, state=state)
    
    flow.redirect_uri = REDIRECT_URI
    
    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)
    
    credentials = flow.credentials
    
    session['credentials'] = creds_to_dict(credentials)
    
    with open(TOKEN_FILE, 'w') as f:
        json.dump(creds_to_dict(credentials), f)
    
    return redirect('/')


def handle_cancel_meeting(sentence, details):
    """
    Handle cancel/delete meeting requests.
    Searches for matching meetings and deletes them.
    """
    service = get_service()
    
    if not service:
        return "Error: Not authenticated or invalid credentials", 401
    
    try:
        # Build query to find matching events
        calendar_id = 'primary'
        
        # Get the time range for searching
        now = datetime.now()
        time_min = now.isoformat()
        
        # If a specific date was mentioned, use it
        if details.get('start'):
            time_min = details['start'].isoformat()
        
        # Search for events (next 30 days by default)
        time_max = (now + timedelta(days=30)).isoformat()
        if details.get('end'):
            time_max = details['end'].isoformat()
        
        # Fetch events
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            maxResults=10,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        # Filter events based on details
        meeting_title = details.get('meeting_title', '').lower()
        agenda = details.get('agenda', '').lower()
        attendee_names = [name.lower() for name in details.get('attendee_names', [])]
        
        # Also extract names directly from sentence for better matching
        sentence_lower = sentence.lower()
        
        matching_events = []
        
        for event in events:
            event_summary = event.get('summary', '').lower()
            event_attendees = [a.get('email', '').lower() for a in event.get('attendees', [])]
            
            # Check if this event matches
            is_match = False
            
            # Match by title/agenda
            if meeting_title and meeting_title in event_summary:
                is_match = True
            elif agenda and agenda != 'meeting' and agenda in event_summary:
                is_match = True
            
            # Match by attendees if specified
            if attendee_names:
                # Check if any of the mentioned attendees are in the event
                attendee_matches = 0
                for name in attendee_names:
                    for email in event_attendees:
                        if name in email:
                            attendee_matches += 1
                            break
                if attendee_matches >= len(attendee_names):
                    is_match = True
            
            # Also match by names from sentence (for "cancel meeting with john")
            # Look for name patterns in sentence
            for name in ['john', 'rahul', 'finance', 'legal']:
                if name in sentence_lower:
                    # Check if name is in summary or attendees
                    if name in event_summary:
                        is_match = True
                        break
                    for email in event_attendees:
                        if name in email:
                            is_match = True
                            break
            
            if is_match:
                matching_events.append(event)
        
        # If no events found, return message
        if not matching_events:
            return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>No Matching Events Found</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .message { background: white; padding: 30px; border-radius: 8px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }
        .warning { color: #ffc107; font-size: 48px; margin-bottom: 20px; }
        a { display: inline-block; padding: 12px 24px; background: #4285f4; color: white; text-decoration: none; border-radius: 4px; margin-top: 20px; }
    </style>
</head>
<body>
    <h1>🔍 No Matching Events Found</h1>
    <div class="message">
        <p class="warning">⚠️</p>
        <p>No meetings matching your request were found.</p>
        <p>Try being more specific about the meeting title, attendees, or date.</p>
        <a href="/">📅 Back to Home</a>
    </div>
</body>
</html>
            ''', sentence=sentence)
        
        # If only one event matches, delete it directly
        if len(matching_events) == 1:
            event = matching_events[0]
            event_id = event.get('id')
            event_summary = event.get('summary', 'Untitled Event')
            
            # Delete the event
            service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
            
            return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>Meeting Deleted</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .message { background: white; padding: 30px; border-radius: 8px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }
        .success { color: #28a745; font-size: 48px; margin-bottom: 20px; }
        a { display: inline-block; padding: 12px 24px; background: #4285f4; color: white; text-decoration: none; border-radius: 4px; margin-top: 20px; }
    </style>
</head>
<body>
    <h1>✅ Meeting Deleted Successfully</h1>
    <div class="message">
        <p class="success">🗑️</p>
        <p>The following meeting has been cancelled:</p>
        <h3>{{ event_summary }}</h3>
        <a href="/">📅 Back to Home</a>
    </div>
</body>
</html>
            ''', event_summary=event_summary)
        
        # Multiple events match - show selection
        events_html_list = []
        for i, event in enumerate(matching_events):
            event_id = event.get('id')
            event_summary = event.get('summary', 'Untitled Event')
            event_start = event.get('start', {}).get('dateTime', event.get('start', {}).get('date', 'No date'))
            events_html_list.append({
                'id': event_id,
                'summary': event_summary,
                'start': event_start
            })
        
        return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>Select Meeting to Delete</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .selection-form { background: white; padding: 30px; border-radius: 8px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .warning { color: #ffc107; font-size: 18px; margin-bottom: 20px; }
        a { display: inline-block; padding: 12px 24px; background: #4285f4; color: white; text-decoration: none; border-radius: 4px; margin-top: 20px; }
        .event-item { background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 4px; border-left: 4px solid #4285f4; }
        .event-item small { color: #666; }
    </style>
</head>
<body>
    <h1>🗑️ Delete Meeting</h1>
    
    <div class="selection-form">
        <p class="warning">⚠️ Multiple meetings match your request. Please select one to delete:</p>
        
        {% for event in events_list %}
        <div class="event-item">
            <strong>{{ event['summary'] }}</strong><br>
            <small>{{ event['start'] }}</small><br>
            <a href="/delete_event/{{ event['id'] }}" style="background: #dc3545; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px; display: inline-block; margin-top: 10px;">🗑️ Delete This Meeting</a>
        </div>
        {% endfor %}
        
        <a href="/">❌ Cancel</a>
    </div>
</body>
</html>
        ''', events_list=events_html_list)
        
    except Exception as e:
        import traceback
        return f"Error cancelling meeting: {{str(e)}}<br><br>{{traceback.format_exc()}}", 500


# Update functionality is available via /edit_event/{event_id} route
    service = get_service()
    
    if not service:
        return "Error: Not authenticated or invalid credentials", 401
    
    try:
        # Build query to find matching events
        calendar_id = 'primary'
        
        # Get the time range for searching
        now = datetime.now()
        time_min = now.isoformat()
        
        # If a specific date was mentioned, use it
        if details.get('start'):
            time_min = details['start'].isoformat()
        
        # Search for events (next 30 days by default)
        time_max = (now + timedelta(days=30)).isoformat()
        if details.get('end'):
            time_max = details['end'].isoformat()
        
        # Fetch events
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            maxResults=10,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        # Filter events based on details
        meeting_title = details.get('meeting_title', '').lower()
        agenda = details.get('agenda', '').lower()
        attendee_names = [name.lower() for name in details.get('attendee_names', [])]
        
        matching_events = []
        
        for event in events:
            event_summary = event.get('summary', '').lower()
            event_attendees = [a.get('email', '').lower() for a in event.get('attendees', [])]
            
            # Check if this event matches
            is_match = False
            
            # Match by title/agenda
            if meeting_title and meeting_title in event_summary:
                is_match = True
            elif agenda and agenda != 'meeting' and agenda in event_summary:
                is_match = True
            
            # Match by attendees if specified
            if attendee_names:
                # Check if any of the mentioned attendees are in the event
                attendee_matches = 0
                for name in attendee_names:
                    for email in event_attendees:
                        if name in email:
                            attendee_matches += 1
                            break
                if attendee_matches >= len(attendee_names):
                    is_match = True
            
            if is_match:
                matching_events.append(event)
        
        # If no events found, return message
        if not matching_events:
            return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>No Matching Events Found</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .message { background: white; padding: 30px; border-radius: 8px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }
        .warning { color: #ffc107; font-size: 48px; margin-bottom: 20px; }
        a { display: inline-block; padding: 12px 24px; background: #4285f4; color: white; text-decoration: none; border-radius: 4px; margin-top: 20px; }
    </style>
</head>
<body>
    <h1>No Matching Events Found</h1>
    <div class="message">
        <p class="warning">⚠️</p>
        <p>No meetings matching your request were found.</p>
        <p>Try being more specific about the meeting title, attendees, or date.</p>
        <a href="/">Back to Home</a>
    </div>
</body>
</html>
            ''', sentence=sentence)
        
        # If only one event matches, update it directly
        if len(matching_events) == 1:
            event = matching_events[0]
            event_id = event.get('id')
            event_summary = event.get('summary', 'Untitled Event')
            
            # Prepare updated event body
            # Preserve original timezone if possible
            original_timezone = event.get('start', {}).get('timeZone', 'UTC')
            
            # Update fields from details
            updated_event = event.copy()
            
            # Update summary if provided
            new_summary = details.get('meeting_title') or details.get('summary') or details.get('agenda')
            if new_summary:
                updated_event['summary'] = new_summary
            
            # Update description if provided
            if details.get('description'):
                updated_event['description'] = details['description']
            
            # Update start time if provided
            if details.get('start'):
                updated_event['start'] = {
                    'dateTime': details['start'].isoformat(),
                    'timeZone': str(details['start'].tzinfo) or original_timezone
                }
            
            # Update end time if provided
            if details.get('end'):
                updated_event['end'] = {
                    'dateTime': details['end'].isoformat(),
                    'timeZone': str(details['end'].tzinfo) or original_timezone
                }
            
            # Update attendees if provided
            if details.get('attendees'):
                updated_event['attendees'] = details['attendees']
            
            # Update the event
            updated = service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=updated_event,
                sendUpdates='all'
            ).execute()
            
            return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>Meeting Updated</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .message { background: white; padding: 30px; border-radius: 8px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }
        .success { color: #28a745; font-size: 48px; margin-bottom: 20px; }
        a { display: inline-block; padding: 12px 24px; background: #4285f4; color: white; text-decoration: none; border-radius: 4px; margin-top: 20px; }
    </style>
</head>
<body>
    <h1>Meeting Updated Successfully</h1>
    <div class="message">
        <p class="success">✏️</p>
        <p>The following meeting has been updated:</p>
        <h3>{{ event_summary }}</h3>
        <a href="/events">View All Events</a>
    </div>
</body>
</html>
            ''', event_summary=updated.get('summary', event_summary))
        
        # Multiple events match - show selection
        events_list = []
        for i, event in enumerate(matching_events):
            event_id = event.get('id')
            event_summary = event.get('summary', 'Untitled Event')
            event_start = event.get('start', {}).get('dateTime', event.get('start', {}).get('date', 'No date'))
            events_list.append({
                'id': event_id,
                'summary': event_summary,
                'start': event_start
            })
        
        # Build edit URLs for each event
        edit_urls = []
        for event in matching_events:
            edit_urls.append(f"/edit_event/{event.get('id')}")
        
        return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>Select Meeting to Update</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .selection-form { background: white; padding: 30px; border-radius: 8px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .warning { color: #ffc107; font-size: 18px; margin-bottom: 20px; }
        a { display: inline-block; padding: 12px 24px; background: #4285f4; color: white; text-decoration: none; border-radius: 4px; margin-top: 20px; }
        .event-item { background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 4px; border-left: 4px solid #4285f4; }
    </style>
</head>
<body>
    <h1>Update Meeting</h1>
    
    <div class="selection-form">
        <p class="warning">⚠️ Multiple meetings match your request. Please select one to update:</p>
        
        {% for event in events %}
        <div class="event-item">
            <strong>{{ event['summary'] }}</strong><br>
            <small>{{ event['start'] }}</small><br>
            <a href="/edit_event/{{ event['id'] }}" style="background: #28a745; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px; display: inline-block; margin-top: 10px;">✏️ Edit This Meeting</a>
        </div>
        {% endfor %}
        
        <a href="/">Cancel</a>
    </div>
</body>
</html>
        ''', events=events_list)
        
    except Exception as e:
        import traceback
        return f"Error updating meeting: {str(e)}<br><br>{traceback.format_exc()}", 500


# NOTE: handle_update_meeting function removed - use /edit_event/{event_id} to edit meetings




def detect_ambiguous_time(sentence):
    """
    Detects ambiguous time like 'at 6' or 'from 6 to 9' without AM/PM.
    Returns the hour if ambiguous, else None.
    For hours 6-9, always return as ambiguous to prompt for AM/PM clarification.
    """
    sentence = sentence.lower()

    # If AM/PM already exists → not ambiguous
    if re.search(r'\b(am|pm|a\.m\.|p\.m\.)\b', sentence):
        return None

    # Match 'from 6 to 9' pattern (time range without AM/PM)
    range_match = re.search(r'\bfrom\s+(\d{1,2})\s+to\s+(\d{1,2})\b', sentence)
    if range_match:
        start_hour = int(range_match.group(1))
        end_hour = int(range_match.group(2))
        # If either start or end is in 6-9 range, flag as ambiguous
        if 6 <= start_hour <= 9 or 6 <= end_hour <= 9:
            return start_hour  # Return start hour for clarification
        elif 1 <= start_hour <= 12:
            return start_hour
        return None

    # Match 'at 6' or 'at 6:00'
    match = re.search(r'\bat\s+(\d{1,2})(?::\d{2})?\b', sentence)
    if not match:
        return None

    hour = int(match.group(1))

    # Hours 6-9 are always ambiguous (common meeting times that need clarification)
    if 6 <= hour <= 9:
        return hour
    
    # Valid ambiguous hour range for other hours
    if 1 <= hour <= 12:
        return hour

    return None

AMPM_CLARIFICATION_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Clarify Time</title>
    <style>
        body { font-family: Arial; margin: 40px; }
        .box { background: #fff3cd; padding: 20px; border-radius: 8px; max-width: 600px; }
        .error { color: red; margin-top: 10px; }
        input { padding: 10px; width: 200px; }
        button { padding: 10px 16px; margin-top: 10px; }
    </style>
</head>
<body>

<div class="box">
    <h3>🕐 Time clarification needed</h3>
    <p>You entered <strong>at {{ hour }}</strong>. Is this AM or PM?</p>

    <form method="POST" action="/nlp_create">
        <!-- Preserve original sentence -->
        <input type="hidden" name="sentence" value="{{ sentence }}">

        <!-- Sub-input field -->
        <input
            type="text"
            name="ampm_input"
            placeholder="AM / PM / 6am / 6pm"
            autofocus
            required
        >

        <br><br>
        <button type="submit">Confirm</button>

        {% if error %}
            <div class="error">{{ error }}</div>
        {% endif %}
    </form>
</div>

</body>
</html>
"""

@app.route('/create_meeting', methods=['POST'])
@app.route('/nlp_create', methods=['POST'])
def nlp_create():
    sentence = request.form.get('sentence', '').strip()
    ampm_input = request.form.get('ampm_input', '').strip()

    if not sentence:
        return "Error: No sentence provided", 400

    # Ensure sentence is passed to detect_ambiguous_time
    ambiguous_hour = detect_ambiguous_time(sentence)  # This needs the sentence argument

    if ambiguous_hour and not ampm_input:
        return render_template_string(
            AMPM_CLARIFICATION_TEMPLATE,
            sentence=sentence,
            hour=ambiguous_hour
        )

    if ambiguous_hour and ampm_input:
        normalized = normalize_ampm_input(ambiguous_hour, ampm_input)
        if not normalized:
            return render_template_string(
                AMPM_CLARIFICATION_TEMPLATE,
                sentence=sentence,
                hour=ambiguous_hour,
                error="Please enter AM or PM (e.g., AM, 6am, PM)"
            )

        # Replace ambiguous time patterns with clarified versions
        # Handle "at 6" pattern
        sentence = re.sub(
            rf'\bat\s+{ambiguous_hour}\b',
            f'at {normalized}',
            sentence,
            flags=re.IGNORECASE
        )
        
        # Handle "from 6 to 9" pattern - replace both start and end with AM/PM
        if re.search(rf'\bfrom\s+{ambiguous_hour}\s+to\s+\d+\b', sentence, re.IGNORECASE):
            # Find the end hour from the pattern
            range_match = re.search(rf'\bfrom\s+{ambiguous_hour}\s+to\s+(\d+)\b', sentence, re.IGNORECASE)
            if range_match:
                end_hour = int(range_match.group(1))
                end_normalized = f'{end_hour} {normalized.split()[-1]}'  # Use same AM/PM as start
                sentence = re.sub(
                    rf'\bfrom\s+{ambiguous_hour}\s+to\s+{end_hour}\b',
                    f'from {normalized} to {end_normalized}',
                    sentence,
                    flags=re.IGNORECASE
                )



    details = extract_meeting_details(sentence)
    selected_ampm = request.form.get('selected_ampm')
    ambiguous_hour = details.get('ambiguous_hour')
    
    if ambiguous_hour and selected_ampm:
        new_hour = ambiguous_hour
        if selected_ampm.upper() == 'PM' and new_hour != 12:
            new_hour += 12
        elif selected_ampm.upper() == 'AM' and new_hour == 12:
            new_hour = 0
        
        # Fix the start time
        details['start'] = details['start'].replace(
            hour=new_hour, minute=0, second=0, microsecond=0
        )
        # Recalculate end time
        duration_minutes = details.get('duration_min', 60)
        details['end'] = details['start'] + timedelta(minutes=duration_minutes)
        
        print(f"✅ Fixed ambiguous time: {ambiguous_hour}:00 → {new_hour}:00 {selected_ampm}")
    # ============ END ADD ============
    
    # ===== Handle CANCEL/DELETE MEETING intent =====
    if details.get('intent') == 'cancel_meeting':
        return handle_cancel_meeting(sentence, details)
    # ===== End CANCEL/DELETE handling =====
    
    service = get_service()
    
    if not service:
        return "Error: Not authenticated or invalid credentials", 401
    
    try:
        # Handle optional file upload from Google Drive picker OR direct file upload
        attachments = []
        attachment_error = None
        
        # Check if Google Drive file was selected via picker
        drive_file_id = request.form.get('drive_file_id', '').strip()
        
        if drive_file_id and len(drive_file_id) > 10:
            # Get file info from Drive to get the title
            drive_service = get_drive_service()
            if drive_service:
                try:
                    file_metadata = drive_service.files().get(fileId=drive_file_id, fields='name,mimeType').execute()
                    attachments.append({
                        "fileUrl": f"https://drive.google.com/file/d/{drive_file_id}/view",
                        "title": file_metadata.get('name', 'Attachment'),
                        "fileId": drive_file_id
                    })
                except Exception as e:
                    # Log the error but don't fail - file might not be accessible
                    attachment_error = str(e)
                    print(f"Warning: Could not attach Drive file: {e}")
                    # Fallback: Still add attachment with just the link
                    attachments.append({
                        "fileUrl": f"https://drive.google.com/file/d/{drive_file_id}/view",
                        "title": 'Drive File (access required)',
                        "fileId": drive_file_id
                    })
        
        # Handle direct file upload - upload local file to Drive first, then add to calendar event
        uploaded_file = request.files.get('attachment')
        if uploaded_file and uploaded_file.filename:
            drive_file_id = upload_file_to_drive(uploaded_file)
            if drive_file_id:
                attachments.append({
                    "fileUrl": f"https://drive.google.com/file/d/{drive_file_id}/view",
                    "title": uploaded_file.filename,
                    "fileId": drive_file_id 
                })
        
        # Set location correctly for online vs physical meetings
        if details.get('use_meet', False):
            event_location = "Google Meet"
        elif details.get('location') == "Online":
            event_location = "Google Meet"
        else:
            event_location = details.get('location', '')
        
        event_body = {
            'summary': details.get('meeting_title') or details.get('summary') or details.get('agenda', 'Meeting'),
            'location': event_location,
            'description': details['description'],
            'start': {
                'dateTime': details['start'].isoformat(),
                'timeZone': str(details['start'].tzinfo),
            },
            'end': {
                'dateTime': details['end'].isoformat(),
                'timeZone': str(details['end'].tzinfo),
            },
            'attendees': details.get('attendees', []),
            'reminders': details.get('reminders', {
                'useDefault': False,
                'overrides': [{'method': 'popup', 'minutes': 10}]
            }),
            'recurrence': details.get('recurrence', []),
        }

        # Handle "me" - the current user (organizer doesn't need to be in attendees)
        attendees_to_remove = []
        for attendee in event_body['attendees']:
            if attendee.get('email') == 'CURRENT_USER':
                attendees_to_remove.append(attendee)
        for attendee in attendees_to_remove:
            event_body['attendees'].remove(attendee)

        # ✅ STEP 6 – attach file ONLY if uploaded
        if attachments:
            event_body['attachments'] = attachments

        if details.get('use_meet', False):
            if details.get('link_preference') == 'use_provided_link' and details.get('meet_link'):
                # Use the provided meet link
                event_body['conferenceData'] = {
                    'entryPoints': [{
                        'entryPointType': 'video',
                        'uri': details.get('meet_link'),
                        'label': details.get('meet_link')
                    }],
                    'conferenceSolution': {
                        'key': {'type': 'hangoutsMeet'},
                        'name': 'Google Meet',
                        'iconUri': 'https://fonts.gstatic.com/s/i/productlogos/meet_2020q4/v6/web-512dp/logo_meet_2020q4_color_2x_web_512dp.png'
                    }
                }
            else:
                # Auto-generate Google Meet link
                event_body['conferenceData'] = {
                    'createRequest': {
                        'requestId': details.get('requestId', str(uuid.uuid4())),
                        'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                    }
                }


        event = service.events().insert(
            calendarId='primary',
            body=event_body,
            supportsAttachments=True,  # ✅ REQUIRED
            conferenceDataVersion=1 if details.get('use_meet', False) else 0,
            sendUpdates='all'
        ).execute()
        
        # ===== ADD TEST CASE TO testcases.json =====
        try:
            testcase_file = os.path.join(os.path.dirname(__file__), 'testcases.json')
            if os.path.exists(testcase_file):
                with open(testcase_file, 'r') as f:
                    testcases_data = json.load(f)
                
                # Generate new ID
                records = testcases_data.get('records', [])
                new_id = f'm{len(records) + 1:03d}'
                
                # Format datetime text from the sentence
                datetime_text = ''
                if details.get('start'):
                    dt = details['start']
                    day_name = dt.strftime('%A')
                    time_str = dt.strftime('%I:%M %p')
                    date_str = dt.strftime('%B %d')
                    datetime_text = f'{day_name} {time_str}'
                
                # Format attendees list
                attendees_names = details.get('attendee_names', [])
                
                # Determine link preference
                link_pref = details.get('link_preference', 'auto_generate_meet')
                if details.get('meet_link'):
                    link_pref = 'use_provided_link'
                
                # Create test case record
                new_testcase = {
                    "id": new_id,
                    "utterance": sentence,
                    "action": details.get('action', 'create'),
                    "intent": details.get('intent', 'schedule_meeting'),
                    "attendees": attendees_names,
                    "datetime_text": datetime_text,
                    "duration_min": details.get('duration_min', 30),
                    "mode": details.get('mode', 'online'),
                    "location": details.get('location'),
                    "link_preference": link_pref,
                    "agenda": details.get('agenda', 'Meeting'),
                    "meeting_title": details.get('meeting_title', ''),
                    "constraints": details.get('constraints', [])
                }
                
                # Append to records
                testcases_data['records'].append(new_testcase)
                
                # Write back to file
                with open(testcase_file, 'w') as f:
                    json.dump(testcases_data, f, indent=4)
                
                print(f"Test case {new_id} added to testcases.json")
        except Exception as tc_error:
            print(f"Warning: Could not add test case: {tc_error}")
        # ===== END TEST CASE ADDITION =====
        
        # Extract meet link from conferenceData if present
        meet_link = ''
        if event.get('conferenceData') and event['conferenceData'].get('entryPoints'):
            for ep in event['conferenceData']['entryPoints']:
                if ep.get('entryPointType') == 'video':
                    meet_link = ep.get('uri', '')
                    break
        
        # Format start and end times
        start_dt = event.get('start', {}).get('dateTime', '')
        end_dt = event.get('end', {}).get('dateTime', '')
        
        # Extract date and time parts
        event_date = start_dt[:10] if start_dt else ''
        start_time = start_dt[11:16] if start_dt else ''
        end_time = end_dt[11:16] if end_dt else ''
        
        # Calculate duration
        duration = ''
        if start_dt and end_dt:
            try:
                from datetime import datetime
                start = datetime.fromisoformat(start_dt.replace('Z', '+00:00'))
                end = datetime.fromisoformat(end_dt.replace('Z', '+00:00'))
                duration_min = int((end - start).total_seconds() / 60)
                duration = f'{duration_min} minutes'
            except:
                duration = 'N/A'
        
        # Format attendees
        attendees_list = event.get('attendees', [])
        attendees_html = ''
        if attendees_list:
            attendees_html = '<div style="margin: 10px 0 10px 130px;">'
            for a in attendees_list:
                attendees_html += f'<span style="display: inline-block; background: #e0e0e0; padding: 3px 8px; margin: 2px; border-radius: 3px; font-size: 14px;">{a.get("email", "")}</span>'
            attendees_html += '</div>'
        
        # Format recurrence
        recurrence = event.get('recurrence', [])
        recurrence_html = ''
        if recurrence:
            recurrence_html = f'<div style="margin: 10px 0;"><span style="font-weight: bold; width: 120px; display: inline-block;">Recurrence:</span>{recurrence[0]}</div>'
        
        # Format meet link
        meet_link_html = ''
        if meet_link:
            meet_link_html = f'<div style="margin: 10px 0;"><span style="font-weight: bold; width: 120px; display: inline-block;">Meet Link:</span><a href="{meet_link}" target="_blank" style="background: #4285f4; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px;">{meet_link}</a></div>'
        
        html_link = event.get('htmlLink', '')
        calendar_link_html = f'<div style="margin: 10px 0;"><span style="font-weight: bold; width: 120px; display: inline-block;">Calendar:</span><a href="{html_link}" target="_blank">View in Google Calendar</a></div>' if html_link else ''
        
        # Build all event fields HTML
        all_fields_html = ''
        field_labels = {
            'id': 'Event ID',
            'status': 'Status',
            'htmlLink': 'Calendar Link',
            'created': 'Created',
            'updated': 'Updated',
            'summary': 'Summary',
            'description': 'Description',
            'location': 'Location',
            'start': 'Start',
            'end': 'End',
            'duration': 'Duration',
            'attendees': 'Attendees',
            'recurrence': 'Recurrence',
            'recurringEventId': 'Recurring Event ID',
            'originalStartTime': 'Original Start',
            'visibility': 'Visibility',
            'transparency': 'Transparency',
            'locked': 'Locked',
            'source': 'Source',
            'guestsCanInviteOthers': 'Guests Can Invite',
            'guestsCanModify': 'Guests Can Modify',
            'guestsCanSeeOthers': 'Guests Can See Others',
            'privateCopyObject': 'Private Copy',
            'confirmationStatus': 'Confirmation Status',
            'umannagedParticipants': 'Unmanaged Participants',
            'useDefaultAlerts': 'Use Default Alerts',
            'notifications': 'Notifications',
            'colorId': 'Color ID',
            'creator': 'Creator',
            'organizer': 'Organizer',
        }
        
        for field, label in field_labels.items():
            value = event.get(field)
            if value is None or value == '':
                continue
            
            # Skip complex nested objects that need special formatting
            if field in ['start', 'end']:
                continue
            
            if field == 'attendees':
                if isinstance(value, list) and value:
                    attendees_display = '<div style="margin-left: 130px; margin-top: 5px;">'
                    for a in value:
                        email = a.get('email', '')
                        response = a.get('responseStatus', '')
                        attendees_display += f'<span style="display: inline-block; background: #e0e0e0; padding: 3px 8px; margin: 2px; border-radius: 3px; font-size: 14px;">{email}</span> '
                        if response:
                            attendees_display += f'<small style="color: #666;">({response})</small>'
                    attendees_display += '</div>'
                    all_fields_html += f'<div style="margin: 10px 0;"><span style="font-weight: bold; width: 120px; display: inline-block;">{label}:</span>{attendees_display}</div>'
            elif field == 'recurrence' and isinstance(value, list):
                all_fields_html += f'<div style="margin: 10px 0;"><span style="font-weight: bold; width: 120px; display: inline-block;">{label}:</span>{value[0] if value else ""}</div>'
            elif field in ['htmlLink', 'calendarLink']:
                all_fields_html += f'<div style="margin: 10px 0;"><span style="font-weight: bold; width: 120px; display: inline-block;">{label}:</span><a href="{value}" target="_blank">{value}</a></div>'
            elif field in ['creator', 'organizer'] and isinstance(value, dict):
                all_fields_html += f'<div style="margin: 10px 0;"><span style="font-weight: bold; width: 120px; display: inline-block;">{label}:</span>{value.get("email", "")}</div>'
            elif field == 'notifications' and isinstance(value, list):
                notifs = ", ".join([n.get('type', '') for n in value])
                all_fields_html += f'<div style="margin: 10px 0;"><span style="font-weight: bold; width: 120px; display: inline-block;">{label}:</span>{notifs}</div>'
            elif isinstance(value, bool):
                all_fields_html += f'<div style="margin: 10px 0;"><span style="font-weight: bold; width: 120px; display: inline-block;">{label}:</span>{"Yes" if value else "No"}</div>'
            elif isinstance(value, list):
                all_fields_html += f'<div style="margin: 10px 0;"><span style="font-weight: bold; width: 120px; display: inline-block;">{label}:</span>{", ".join(str(v) for v in value)}</div>'
            else:
                all_fields_html += f'<div style="margin: 10px 0;"><span style="font-weight: bold; width: 120px; display: inline-block;">{label}:</span>{value}</div>'
        
        return render_event_details(event, title="✅ Meeting Created Successfully!", show_raw_data=True, back_url="/", back_text="← Back to Home")
        
    except Exception as e:
        return f"Error creating meeting: {str(e)}", 500



        
        try:
            # Search for events matching the description
            now = datetime.utcnow().isoformat() + 'Z'
            events_result = service.events().list(
                calendarId='primary',
                timeMin=now,
                maxResults=50,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Find matching event based on attendees, summary, or description
            target_event = None
            sentence_lower = sentence.lower()
            
            # Extract time info from the sentence for new time
            new_time_match = re.search(r'(\d{1,2}):?(\d{2})?\s*(am|pm)', sentence_lower)
            new_time_2_match = re.search(r'(\d{1,2}):(\d{2})', sentence_lower)
            
            # Parse the new start and end times
            new_start_dt = None
            new_end_dt = None
            
            # Look for time patterns like "5pm to 6pm" or "5:30pm to 6:30pm"
            # First match the full time range, then parse individual times
            time_range_match = re.search(r'(\d{1,2}):?(\d{2})?\s*(am|pm)?\s*(?:to|-)\s*(\d{1,2}):?(\d{2})?\s*(am|pm)?', sentence_lower)
            
            if time_range_match:
                # Extract start time
                start_hour = int(time_range_match.group(1))
                start_min = int(time_range_match.group(2)) if time_range_match.group(2) else 0
                start_ampm = time_range_match.group(3)
                
                if start_ampm:
                    if start_ampm == 'pm' and start_hour != 12:
                        start_hour += 12
                    elif start_ampm == 'am' and start_hour == 12:
                        start_hour = 0
                
                # Extract end time
                end_hour = int(time_range_match.group(4))
                end_min = int(time_range_match.group(5)) if time_range_match.group(5) else 0
                end_ampm = time_range_match.group(6)
                
                if end_ampm:
                    if end_ampm == 'pm' and end_hour != 12:
                        end_hour += 12
                    elif end_ampm == 'am' and end_hour == 12:
                        end_hour = 0
                elif start_ampm and end_hour <= start_hour:
                    # No ampm for end, assume same as start and add 12 if needed
                    if start_ampm == 'pm':
                        end_hour += 12
                
                # Parse the date from sentence
                new_start_dt = resolve_datetime_from_text(sentence, datetime.now())
                
                # Set the new times
                new_start_dt = new_start_dt.replace(hour=start_hour, minute=start_min, second=0, microsecond=0)
                new_end_dt = new_start_dt.replace(hour=end_hour, minute=end_min, second=0, microsecond=0)
                
                # If end hour is earlier than start hour, add a day
                if new_end_dt <= new_start_dt:
                    new_end_dt += timedelta(days=1)
                
                # Calculate duration for logging/debugging
                duration_minutes = int((new_end_dt - new_start_dt).total_seconds() / 60)
            
            # Search for event with matching attendees or title
            for event in events:
                # Check attendees
                attendees = event.get('attendees', [])
                for att in attendees:
                    email = att.get('email', '').lower()
                    name = email.split('@')[0].replace('.', ' ')
                    if name in sentence_lower:
                        target_event = event
                        break
                
                # Check summary
                if not target_event:
                    summary = event.get('summary', '').lower()
                    if any(word in summary for word in sentence_lower.split() if len(word) > 3):
                        target_event = event
                        break
                
                if target_event:
                    break
            
            if not target_event:
                return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>Event Not Found</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .error { color: red; margin-bottom: 20px; }
        .back-btn { padding: 10px 20px; background: #4285f4; color: white; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; margin-top: 20px; }
    </style>
</head>
<body>
    <h1 class="error">❌ Event Not Found</h1>
    <p>Could not find an event matching "{{ sentence }}".</p>
    <p>Try being more specific about the meeting (e.g., "Meeting with John").</p>
    <a href="/" class="back-btn">← Back to Home</a>
</body>
</html>
                ''', sentence=sentence)
            
            # Update the event with new times
            event = target_event
            
            # Preserve original timezone
            original_timezone = event.get('start', {}).get('timeZone', 'Asia/Calcutta')
            
            if new_start_dt and new_end_dt:
                # new_end_dt was explicitly parsed from the sentence, use it directly
                # Update event
                event['start']['dateTime'] = new_start_dt.isoformat()
                event['start']['timeZone'] = str(new_start_dt.tzinfo) if new_start_dt.tzinfo else original_timezone
                event['end']['dateTime'] = new_end_dt.isoformat()
                event['end']['timeZone'] = str(new_end_dt.tzinfo) if new_end_dt.tzinfo else original_timezone
            
            # Check for summary updates
            if 'change title' in sentence_lower or 'change summary' in sentence_lower or 'rename' in sentence_lower:
                title_match = re.search(r'(?:change|update|set)\s+(?:title|summary)\s+(?:to\s+)?["\']?([^"\'\n]+)', sentence_lower)
                if title_match:
                    new_title = title_match.group(1).strip()
                    # Remove quotes if present
                    new_title = new_title.strip('"\'')
                    event['summary'] = new_title
            
            # Check for location updates
            if 'change location' in sentence_lower or 'move to' in sentence_lower:
                location_match = re.search(r'(?:change|location|move)\s+(?:to\s+)?["\']?([^"\'\n]+)', sentence_lower)
                if location_match:
                    new_location = location_match.group(1).strip()
                    new_location = new_location.strip('"\'')
                    event['location'] = new_location
            
            # Remove read-only fields (copy first to avoid modifying original)
            event_copy = event.copy()
            readonly_fields = ['etag', 'htmlLink', 'created', 'updated', 'creator', 'organizer', 
                             'conferenceData', 'recurringEventId', 'originalStartTime']
            for field in readonly_fields:
                event_copy.pop(field, None)
            
            # Update the event in Google Calendar
            updated_event = service.events().update(
                calendarId='primary',
                eventId=event.get('id'),
                body=event_copy,
                sendUpdates='all'
            ).execute()
            
            return render_event_details(updated_event, title="✅ Event Updated Successfully!", show_raw_data=True, back_url="/", back_text="← Back to Home")
            
        except Exception as e:
            import traceback
            return f"Error updating meeting: {str(e)}<br><br>{traceback.format_exc()}", 500
    # Show the create form instead
    return render_template_string('''<!DOCTYPE html>
<html>
<head>
    <title>Create Meeting</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .section { background: white; padding: 30px; border-radius: 8px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #333; }
        input[type="text"] { padding: 10px; margin: 5px 0; width: 100%; max-width: 600px; border: 1px solid #ccc; border-radius: 4px; font-size: 16px; }
        input[type="submit"] { padding: 12px 24px; background: #4285f4; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; margin-top: 10px; }
        input[type="submit"]:hover { background: #3367d6; }
        input[type="submit"]:disabled { background: #ccc; cursor: not-allowed; }
        .time-popup { 
            background: #fff3cd; padding: 20px; border-radius: 8px; margin: 15px 0; 
            border-left: 5px solid #ffc107; box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .time-popup h4 { margin: 0 0 10px 0; color: #856404; }
        .time-buttons { margin: 15px 0; }
        .time-btn { 
            padding: 12px 24px; margin: 0 10px; border: none; border-radius: 6px; 
            font-size: 16px; cursor: pointer; transition: all 0.3s;
        }
        .time-btn:hover { transform: translateY(-2px); }
        .am-btn { background: #007bff; color: white; }
        .pm-btn { background: #28a745; color: white; }
        .time-btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        .examples { background: #f0f0f0; padding: 15px; border-radius: 5px; margin-top: 20px; font-size: 14px; }
        .back-btn { padding: 10px 20px; background: #ccc; color: #333; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; margin-top: 20px; }
    </style>
</head>
<body>
    <h1>📅 Create a New Meeting</h1>
    
    <div class="section">
        <h3>Describe your meeting</h3>
        <form action="/nlp_create" method="post" id="meetingForm">
            <input type="hidden" name="details_json" value="{{ details_json }}">
            <input type="hidden" name="selected_ampm" id="selected_ampm" value="">
            
            Describe your meeting (e.g., "Meeting with John tomorrow at 3pm"):
            <input type="text" name="sentence" value="{{ sentence or '' }}" size="80" required><br><br>
            
            {% if ambiguous_hour %}
            <div class="time-popup">
                <h4>🕐 Confirm Time: {{ ambiguous_hour }}:00</h4>
                <p><strong>Is this AM or PM?</strong></p>
                <div class="time-buttons">
                    <button type="button" class="time-btn am-btn" onclick="selectTime('AM')">🌅 AM ({{ '%d:00 AM' % ambiguous_hour }})</button>
                    <button type="button" class="time-btn pm-btn" onclick="selectTime('PM')">🌇 PM ({{ '%d:00 PM' % ambiguous_hour if ambiguous_hour != 12 else '12:00 PM' }})</button>
                </div>
                <p id="timeConfirm" style="color: #28a745; font-weight: bold; margin-top: 10px; display: none;">
                    ✅ Time confirmed! You can now create the meeting.
                </p>
            </div>
            {% endif %}
            
            <input type="submit" id="submitBtn" value="{% if ambiguous_hour %}Please confirm time first{% else %}Create Meeting{% endif %}" 
                   {% if ambiguous_hour %}disabled{% endif %}>
        </form>
        
        <div class="examples">
            <h3>Example prompts:</h3>
            <ul>
                <li>"Meeting with John tomorrow at 3pm"</li>
                <li>"Team standup every Monday at 9am"</li>
                <li>"Call with Sarah next Friday at 2:30pm"</li>
            </ul>
        </div>
    </div>
    
    <script>
        function selectTime(ampm) {
        document.getElementById('selectedampm').value = ampm;
        document.getElementById('submitBtn').disabled = false;
        document.getElementById('submitBtn').value = `Create Meeting at ${ambiguoushour}:00 ${ampm}`;
        document.getElementById('submitBtn').style.background = '#28a745';
        document.getElementById('timeConfirm').textContent = `Time confirmed: ${ambiguoushour}:00 ${ampm}`;
        document.getElementById('timeConfirm').style.display = 'block';
        document.querySelectorAll('.time-btn').forEach(btn => btn.disabled = true);
    }
    document.getElementById('meetingForm').onsubmit = function() {
        if (ambiguoushour && !document.getElementById('selectedampm').value) {
            alert('Please confirm AM or PM!');
            return false;
        }
        return true;
            };
        </script>
    
    <a href="/" class="back-btn">← Back to Home</a>
</body>
</html>
''', sentence=sentence, ambiguous_hour=ambiguous_hour)

def normalize_ampm_input(hour, user_input):
    """
    Accepts: AM, PM, 6am, 6 am, pm, etc.
    Returns normalized string like '6 AM' or '6 PM'
    """
    text = user_input.lower().replace(" ", "")

    if text in ["am", "a.m.", f"{hour}am"]:
        return f"{hour} AM"

    if text in ["pm", "p.m.", f"{hour}pm"]:
        return f"{hour} PM"

    return None



@app.route('/events')
def list_events():
    service = get_service()
    
    if not service:
        return "Error: Not authenticated or invalid credentials", 401
    
    try:
        now = datetime.utcnow().isoformat() + 'Z'
        events_result = service.events().list(
            calendarId='primary',
            timeMin=now,
            maxResults=10,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>Upcoming Events</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .event { padding: 15px; margin: 10px 0; background: #f5f5f5; border-radius: 5px; }
        .event h3 { margin: 0 0 10px 0; }
        .event a { color: #4285f4; }
    </style>
</head>
<body>
    <h1>📋 Upcoming Events</h1>
    <a href="/"><input type="submit" value="Back to Home"></a>
    
    {% if events %}
        {% for event in events %}
        <div class="event">
            <h3>{{ event.summary }}</h3>
            <p><strong>Start:</strong> {{ event.start.dateTime or event.start.date }}</p>
            <p><strong>End:</strong> {{ event.end.dateTime or event.end.date }}</p>
            {% if event.location %}<p><strong>Location:</strong> {{ event.location }}</p>{% endif %}
            {% if event.htmlLink %}<p><a href="{{ event.htmlLink }}">View in Google Calendar</a></p>{% endif %}
        </div>
        {% endfor %}
    {% else %}
        <p>No upcoming events found.</p>
    {% endif %}
</body>
</html>
        ''', events=events)
        
    except Exception as e:
        return f"Error fetching events: {str(e)}", 500


# Unified event details template
def render_event_details(event, title="Event Details", show_raw_data=True, back_url="/", back_text="Back to Home"):
    """Render event details in a unified template."""
    import json
    
    # Format start and end times
    start_dt = event.get('start', {}).get('dateTime', '')
    end_dt = event.get('end', {}).get('dateTime', '')
    
    event_date = start_dt[:10] if start_dt else ''
    start_time = start_dt[11:16] if start_dt else ''
    end_time = end_dt[11:16] if end_dt else ''
    
    # Calculate duration
    duration = ''
    if start_dt and end_dt:
        try:
            from datetime import datetime
            start = datetime.fromisoformat(start_dt.replace('Z', '+00:00'))
            end = datetime.fromisoformat(end_dt.replace('Z', '+00:00'))
            duration_min = int((end - start).total_seconds() / 60)
            duration = f'{duration_min} minutes'
        except:
            duration = 'N/A'
    
    # Format attendees
    attendees_list = event.get('attendees', [])
    attendees_html = ''
    if attendees_list:
        attendees_html = '<div style="margin: 10px 0 10px 130px;">'
        for a in attendees_list:
            attendees_html += f'<span style="display: inline-block; background: #e0e0e0; padding: 3px 8px; margin: 2px; border-radius: 3px; font-size: 14px;">{a.get("email", "")}</span>'
        attendees_html += '</div>'
    
    # Format recurrence
    recurrence = event.get('recurrence', [])
    recurrence_html = ''
    if recurrence:
        recurrence_html = f'<div style="margin: 10px 0;"><span style="font-weight: bold; width: 120px; display: inline-block;">Recurrence:</span>{recurrence[0]}</div>'
    
    # Format meet link
    meet_link_html = ''
    if event.get('conferenceData') and event['conferenceData'].get('entryPoints'):
        for ep in event['conferenceData']['entryPoints']:
            if ep.get('entryPointType') == 'video':
                meet_link = ep.get('uri', '')
                meet_link_html = f'<div style="margin: 10px 0;"><span style="font-weight: bold; width: 120px; display: inline-block;">Meet Link:</span><a href="{meet_link}" target="_blank" style="background: #4285f4; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px;">{meet_link}</a></div>'
                break
    
    # Calendar link
    html_link = event.get('htmlLink', '')
    calendar_link_html = f'<div style="margin: 10px 0;"><span style="font-weight: bold; width: 120px; display: inline-block;">Calendar:</span><a href="{html_link}" target="_blank">View in Google Calendar</a></div>' if html_link else ''
    
    # Conference data
    conference_html = ''
    if event.get('conferenceData'):
        cd = event['conferenceData']
        if cd.get('entryPoints'):
            for ep in cd['entryPoints']:
                ep_uri = ep.get('uri', '')
                ep_label = ep.get('label', '')
                conference_html += f'<div style="margin: 10px 0;"><span style="font-weight: bold; width: 120px; display: inline-block;">Conference:</span><a href="{ep_uri}" target="_blank" style="background: #4285f4; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px;">{ep_label or ep_uri}</a></div>'
        if cd.get('conferenceSolution'):
            cs = cd['conferenceSolution']
            conference_html += f'<div style="margin: 10px 0;"><span style="font-weight: bold; width: 120px; display: inline-block;">Solution:</span>{cs.get("name", "")}</div>'
    
    # Attachments
    attachments_html = ''
    if event.get('attachments'):
        attachments_html = '<div style="margin: 10px 0;"><span style="font-weight: bold; width: 120px; display: inline-block; vertical-align: top;">Attachments:</span><div style="display: inline-block; vertical-align: top;">'
        for att in event['attachments']:
            file_url = att.get('fileUrl', '')
            title = att.get('title', 'File')
            attachments_html += f'<div style="margin: 5px 0;"><a href="{file_url}" target="_blank">{title}</a></div>'
        attachments_html += '</div></div>'
    
    # Edit button HTML
    edit_button_html = ''
    if show_raw_data and event.get('id'):
        edit_button_html = f'<a href="/edit_event/{event["id"]}" class="back-btn" style="background: #f0a500;">✏️ Edit Event</a>'
    
    return f'''
<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
        .success {{ color: green; margin-bottom: 20px; }}
        .event-details {{ background: white; padding: 30px; border-radius: 8px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .section {{ margin-bottom: 20px; }}
        .section h3 {{ margin: 0 0 15px 0; padding-bottom: 10px; border-bottom: 2px solid #4285f4; color: #333; }}
        .detail-row {{ margin: 8px 0; padding: 5px 0; }}
        .detail-label {{ font-weight: bold; width: 150px; display: inline-block; color: #555; }}
        .detail-value {{ display: inline-block; }}
        .back-btn {{ padding: 10px 20px; background: #4285f4; color: white; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; margin-top: 20px; margin-right: 10px; }}
        .back-btn:hover {{ background: #3367d6; }}
        .json-data {{ background: #f8f8f8; padding: 15px; border-radius: 5px; margin-top: 20px; font-family: monospace; font-size: 12px; overflow-x: auto; }}
    </style>
</head>
<body>
    <h1 class="success">{title}</h1>
    
    <div class="event-details">
        <div class="section">
            <h3>📅 Event Details</h3>
            <div class="detail-row"><span class="detail-label">Summary:</span><span class="detail-value">{event.get('summary', '')}</span></div>
            <div class="detail-row"><span class="detail-label">Date:</span><span class="detail-value">{event_date}</span></div>
            <div class="detail-row"><span class="detail-label">Time:</span><span class="detail-value">{start_time} - {end_time}</span></div>
            <div class="detail-row"><span class="detail-label">Duration:</span><span class="detail-value">{duration}</span></div>
            <div class="detail-row"><span class="detail-label">Location:</span><span class="detail-value">{event.get('location', 'Not specified')}</span></div>
            {meet_link_html}
            <div class="detail-row"><span class="detail-label" style="vertical-align: top;">Description:</span><span class="detail-value" style="white-space: pre-wrap;">{event.get('description', '')}</span></div>
            {attendees_html}
            {recurrence_html}
            {conference_html}
            {attachments_html}
            {calendar_link_html}
            <div class="detail-row"><span class="detail-label">Status:</span><span class="detail-value">Event successfully added to your calendar</span></div>
        </div>
        
        {f"""
        <div class=\"section\">
            <h3>🔧 Raw Event Data (JSON)</h3>
            <div class=\"json-data\"><pre>{json.dumps(event, indent=2, default=str)}</pre></div>
            {edit_button_html}
        </div>
        """ if show_raw_data else ""}
    </div>
    
    <a href="{back_url}" class="back-btn">{back_text}</a>
</body>
</html>
    '''


@app.route('/logout')
def logout():
    session.pop('credentials', None)
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)
    return redirect('/')


@app.route('/edit_event/<event_id>', methods=['GET', 'POST'])
def edit_event(event_id):
    """Edit an existing calendar event."""
    service = get_service()
    
    if not service:
        return "Error: Not authenticated or invalid credentials", 401
    
    try:
        # Fetch the existing event
        event = service.events().get(calendarId='primary', eventId=event_id).execute()
        
        if request.method == 'POST':
            # Update the event with new values
            event['summary'] = request.form.get('summary', event.get('summary', ''))
            event['description'] = request.form.get('description', event.get('description', ''))
            event['location'] = request.form.get('location', event.get('location', ''))
            
            # Handle start datetime - preserve timezone if present
            start_date = request.form.get('start_date', '')
            start_time = request.form.get('start_time', '')
            if start_date and start_time:
                # Get original timezone
                original_timezone = event.get('start', {}).get('timeZone', 'UTC')
                start_datetime = f"{start_date}T{start_time}:00"
                # Add timezone if we have it
                if original_timezone:
                    start_datetime += f"+05:30"  # Default to IST
                event['start']['dateTime'] = start_datetime
                event['start']['timeZone'] = original_timezone
            
            # Handle end datetime
            end_date = request.form.get('end_date', '')
            end_time = request.form.get('end_time', '')
            if end_date and end_time:
                # Get original timezone
                original_timezone = event.get('end', {}).get('timeZone', 'UTC')
                end_datetime = f"{end_date}T{end_time}:00"
                # Add timezone if we have it
                if original_timezone:
                    end_datetime += f"+05:30"  # Default to IST
                event['end']['dateTime'] = end_datetime
                event['end']['timeZone'] = original_timezone
            
            # Remove read-only fields that can't be updated
            readonly_fields = ['id', 'etag', 'htmlLink', 'created', 'updated', 'creator', 'organizer', 
                             'conferenceData', 'recurringEventId', 'originalStartTime']
            for field in readonly_fields:
                event.pop(field, None)
            
            # Update the event
            updated_event = service.events().update(
                calendarId='primary',
                eventId=event_id,
                body=event,
                sendUpdates='all'
            ).execute()
            
            return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>Event Updated</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .success { color: green; margin-bottom: 20px; }
        .event-details { background: white; padding: 30px; border-radius: 8px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .back-btn { padding: 10px 20px; background: #4285f4; color: white; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; margin-top: 20px; }
        .back-btn:hover { background: #3367d6; }
    </style>
</head>
<body>
    <h1 class="success">✅ Event Updated Successfully!</h1>
    <div class="event-details">
        <p><strong>Summary:</strong> {{ updated_event.summary }}</p>
        <p><strong>Start:</strong> {{ updated_event.start.dateTime }}</p>
        <p><strong>End:</strong> {{ updated_event.end.dateTime }}</p>
        {% if updated_event.htmlLink %}<p><a href="{{ updated_event.htmlLink }}">View in Google Calendar</a></p>{% endif %}
    </div>
    <a href="/events" class="back-btn">← Back to Events</a>
</body>
</html>
            ''', updated_event=updated_event)
        
        # Parse current event details for form
        start_dt = event.get('start', {}).get('dateTime', '') or event.get('start', {}).get('date', '')
        end_dt = event.get('end', {}).get('dateTime', '') or event.get('end', {}).get('date', '')
        
        # Handle date-only events (all-day events)
        if start_dt and len(start_dt) == 10:  # YYYY-MM-DD format for all-day events
            start_date = start_dt
            start_time = '09:00'
        elif start_dt:
            start_date = start_dt[:10]
            start_time = start_dt[11:16]
        else:
            start_date = ''
            start_time = ''
        
        if end_dt and len(end_dt) == 10:
            end_date = end_dt
            end_time = '10:00'
        elif end_dt:
            end_date = end_dt[:10]
            end_time = end_dt[11:16]
        else:
            end_date = ''
            end_time = ''
        
        return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>Edit Event</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .edit-form { background: white; padding: 30px; border-radius: 8px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .form-group { margin: 15px 0; }
        .form-group label { display: block; font-weight: bold; margin-bottom: 5px; color: #333; }
        .form-group input, .form-group textarea { width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 4px; font-size: 14px; }
        .form-group textarea { height: 100px; resize: vertical; }
        .submit-btn { padding: 12px 24px; background: #4285f4; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
        .submit-btn:hover { background: #3367d6; }
        .cancel-btn { padding: 12px 24px; background: #ccc; color: #333; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; text-decoration: none; margin-left: 10px; }
        .cancel-btn:hover { background: #bbb; }
    </style>
</head>
<body>
    <h1>✏️ Edit Event</h1>
    
    <div class="edit-form">
        <form method="POST">
            <div class="form-group">
                <label for="summary">Summary:</label>
                <input type="text" id="summary" name="summary" value="{{ event.get('summary', '') }}" required>
            </div>
            
            <div class="form-group">
                <label for="description">Description:</label>
                <textarea id="description" name="description">{{ event.get('description', '') }}</textarea>
            </div>
            
            <div class="form-group">
                <label for="location">Location:</label>
                <input type="text" id="location" name="location" value="{{ event.get('location', '') }}">
            </div>
            
            <div class="form-group">
                <label for="start_date">Start Date:</label>
                <input type="date" id="start_date" name="start_date" value="{{ start_date }}" required>
            </div>
            
            <div class="form-group">
                <label for="start_time">Start Time:</label>
                <input type="time" id="start_time" name="start_time" value="{{ start_time }}" required>
            </div>
            
            <div class="form-group">
                <label for="end_date">End Date:</label>
                <input type="date" id="end_date" name="end_date" value="{{ end_date }}" required>
            </div>
            
            <div class="form-group">
                <label for="end_time">End Time:</label>
                <input type="time" id="end_time" name="end_time" value="{{ end_time }}" required>
            </div>
            
            <button type="submit" class="submit-btn">💾 Save Changes</button>
            <a href="/events" class="cancel-btn">❌ Cancel</a>
        </form>
    </div>
</body>
</html>
        ''', event=event, start_date=start_date, start_time=start_time, end_date=end_date, end_time=end_time)
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return f"Error editing event: {str(e)}<br><br>{error_details}", 500


@app.route('/delete_event/<event_id>', methods=['GET', 'POST'])
def delete_event(event_id):
    """Delete an existing calendar event."""
    service = get_service()
    
    if not service:
        return "Error: Not authenticated or invalid credentials", 401
    
    try:
        # Fetch the existing event first to show confirmation
        event = service.events().get(calendarId='primary', eventId=event_id).execute()
        
        if request.method == 'POST':
            # Confirm deletion
            confirm = request.form.get('confirm', 'no')
            if confirm == 'yes':
                # Delete the event
                service.events().delete(calendarId='primary', eventId=event_id).execute()
                return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>Event Deleted</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .message { background: white; padding: 30px; border-radius: 8px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }
        .success { color: #28a745; }
        a { display: inline-block; padding: 12px 24px; background: #4285f4; color: white; text-decoration: none; border-radius: 4px; margin-top: 20px; }
        a:hover { background: #3367d6; }
    </style>
</head>
<body>
    <h1>✅ Event Deleted Successfully</h1>
    <div class="message">
        <p class="success">The event <strong>{{ event.get('summary', 'Untitled Event') }}</strong> has been deleted.</p>
        <a href="/events">📅 View All Events</a>
    </div>
</body>
</html>
                ''', event=event)
            else:
                return redirect(f'/edit_event/{event_id}')
        
        # Show confirmation page
        return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>Delete Event</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .confirm-form { background: white; padding: 30px; border-radius: 8px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .warning { color: #dc3545; font-size: 18px; margin-bottom: 20px; }
        .event-info { background: #f8f9fa; padding: 15px; border-radius: 4px; margin-bottom: 20px; }
        .btn-danger { padding: 12px 24px; background: #dc3545; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
        .btn-danger:hover { background: #c82333; }
        .btn-secondary { padding: 12px 24px; background: #6c757d; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; text-decoration: none; margin-left: 10px; }
        .btn-secondary:hover { background: #5a6268; }
    </style>
</head>
<body>
    <h1>🗑️ Delete Event</h1>
    
    <div class="confirm-form">
        <p class="warning">⚠️ Are you sure you want to delete this event? This action cannot be undone.</p>
        
        <div class="event-info">
            <strong>{{ event.get('summary', 'Untitled Event') }}</strong>
            {% if event.get('start') %}
                <br><small>{{ event.get('start', {}).get('dateTime', event.get('start', {}).get('date', 'No date')) }}</small>
            {% endif %}
        </div>
        
        <form method="POST">
            <input type="hidden" name="confirm" value="yes">
            <button type="submit" class="btn-danger">🗑️ Yes, Delete Event</button>
            <a href="/events" class="btn-secondary">❌ Cancel</a>
        </form>
    </div>
</body>
</html>
        ''', event=event)
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return f"Error deleting event: {str(e)}<br><br>{error_details}", 500


def create_marketing_plan_meeting_with_hr():
    """
    Create a meeting with Shreya and HR team for marketing plan discussion.
    Time: Next week Tuesday at 12pm
    """
    from datetime import datetime, timedelta
    
    # Calculate next Tuesday at 12pm
    now = datetime.now()
    current_weekday = now.weekday()  # Monday is 0, Sunday is 6
    # Tuesday is weekday 1
    days_until_tuesday = (1 - current_weekday) % 7
    if days_until_tuesday == 0:
        days_until_tuesday = 7  # If today is Tuesday, get next Tuesday
    
    next_tuesday = now + timedelta(days=days_until_tuesday)
    start_time = next_tuesday.replace(hour=12, minute=0, second=0, microsecond=0)
    end_time = start_time + timedelta(hours=1)  # 1 hour meeting
    
    # Get timezone
    ist_tz = pytz.timezone('Asia/Calcutta')
    if start_time.tzinfo is None:
        start_time = ist_tz.localize(start_time)
        end_time = ist_tz.localize(end_time)
    
    # Prepare event details
    event_body = {
        'summary': 'Marketing Plan Discussion with HR Team',
        'location': 'Google Meet',
        'description': 'Discussion about marketing plan with HR team participation.\\n\\nAttendees:\\n- Shreya\\n- HR Team Representatives',
        'start': {
            'dateTime': start_time.isoformat(),
            'timeZone': str(start_time.tzinfo),
        },
        'end': {
            'dateTime': end_time.isoformat(),
            'timeZone': str(end_time.tzinfo),
        },
        'attendees': [
            {'email': 'shreya.agarwal@example.com'},
            {'email': 'hr.team@example.com'},
        ],
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'popup', 'minutes': 30},
                {'method': 'email', 'minutes': 60},
            ],
        },
        'conferenceData': {
            'createRequest': {
                'requestId': str(uuid.uuid4()),
                'conferenceSolutionKey': {'type': 'hangoutsMeet'}
            }
        }
    }
    
    return event_body


@app.route('/create_hr_marketing_meeting')
def create_hr_marketing_meeting():
    """
    Route to create a marketing plan meeting with Shreya and HR team.
    Access this URL to create the meeting directly.
    """
    service = get_service()
    
    if not service:
        return "Error: Not authenticated or valid credentials. Please <a href='/authorize'>authenticate first</a>.", 401
    
    try:
        event_body = create_marketing_plan_meeting_with_hr()
        
        event = service.events().insert(
            calendarId='primary',
            body=event_body,
            supportsAttachments=True,
            conferenceDataVersion=1,
            sendUpdates='all'
        ).execute()
        
        return render_event_details(event, title="✅ Meeting Created Successfully!", show_raw_data=False, back_url="/", back_text="← Back to Home")
        
    except Exception as e:
        return f"Error creating meeting: {str(e)}", 500


if __name__ == '__main__':
    app.run(debug=True, port=8000)
