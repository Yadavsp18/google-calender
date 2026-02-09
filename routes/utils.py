"""
Shared Utilities for Meeting Routes
Contains common functions used across different handlers.
"""

from datetime import datetime, timezone
from dateutil.parser import parse as date_parse


# IST Timezone constant
IST_TZ = timezone.utc  # Keep it simple, rely on the service API


def format_datetime_for_display(dt_str):
    """Format datetime string for display."""
    if not dt_str:
        return 'No date'
    try:
        dt = date_parse(dt_str)
        return dt.strftime("%A, %B %d, %Y at %I:%M %p")
    except Exception:
        return dt_str


def format_event_datetime(event):
    """Format event datetime for display in selection lists."""
    start = event.get('start', {}).get('dateTime', event.get('start', {}).get('date', 'No date'))
    if start != 'No date':
        try:
            start_dt = date_parse(start)
            return start_dt.strftime("%A, %B %d at %I:%M %p")
        except Exception:
            pass
    return start


def build_event_resource(details, user_meet_link=None):
    """Build a Google Calendar event resource from meeting details."""
    # Check for custom meet link from details first, then fallback to parameter
    custom_meet_link = details.get('meet_link') or user_meet_link
    is_auto_generated = details.get('is_auto_generated_link', True)
    
    # Helper to get timezone string in Google Calendar compatible format
    def get_tz_str(dt):
        if dt.tzinfo is None:
            return 'UTC'
        tz = dt.tzinfo
        
        # Try different methods to get a valid timezone string
        # Method 1: Check for common timezone names
        tz_name = None
        if hasattr(tz, 'tzname') and callable(tz.tzname):
            try:
                tz_name = tz.tzname(dt)
            except Exception:
                pass
        elif hasattr(tz, 'tzname'):
            tz_name = tz.tzname
        
        # Clean up and validate the timezone string
        tz_name = str(tz_name).strip() if tz_name else str(tz)
        
        # Check for UTC variants
        if tz_name in ['UTC', 'GMT', 'tzutc()', '<UTC>']:
            return 'UTC'
        
        # Check for offset-based timezones
        if 'tzoffset' in tz_name or 'offset' in tz_name:
            # Extract the offset in seconds
            import re
            offset_match = re.search(r'offset\(None,\s*(\d+)\)', tz_name)
            if offset_match:
                offset_seconds = int(offset_match.group(1))
                offset_hours = offset_seconds / 3600
                # Format as UTC+HH:MM
                if offset_hours >= 0:
                    return f'UTC+{int(offset_hours):02d}:{int((offset_hours % 1) * 60):02d}'
                else:
                    return f'UTC-{int(abs(offset_hours)):02d}:{int((abs(offset_hours) % 1) * 60):02d}'
            else:
                # Try to get the offset from the datetime
                offset = dt.utcoffset()
                if offset:
                    total_seconds = int(offset.total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    if hours >= 0:
                        return f'UTC+{hours:02d}:{minutes:02d}'
                    else:
                        return f'UTC-{abs(hours):02d}:{minutes:02d}'
        
        # Return the cleaned timezone name if it looks valid
        if tz_name and len(tz_name) <= 50 and not '<' in tz_name:
            return tz_name
        
        # Fallback: try to get offset from datetime
        offset = dt.utcoffset()
        if offset:
            total_seconds = int(offset.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            if hours >= 0:
                return f'UTC+{hours:02d}:{minutes:02d}'
            else:
                return f'UTC-{abs(hours):02d}:{minutes:02d}'
        
        return 'UTC'
    
    event = {
        'summary': details.get('meeting_title', 'Meeting'),
        'description': details.get('agenda', ''),
        'start': {
            'dateTime': details['start'].isoformat(),
            'timeZone': get_tz_str(details['start'])
        },
        'end': {
            'dateTime': details['end'].isoformat(),
            'timeZone': get_tz_str(details['end'])
        },
        'attendees': details.get('attendees', []),
        'reminders': details.get('reminders', {'useDefault': False}),
        'recurrence': details.get('recurrence', [])
    }
    
    # Add meeting location and link handling
    custom_meet_link = details.get('meet_link') or user_meet_link
    is_auto_generated = details.get('is_auto_generated_link', True)
    mode = details.get('mode', 'online')
    location = details.get('location', '')
    use_meet = details.get('use_meet', False)
    
    # Priority 1: Custom link provided (Zoom/Teams/Meet URL) → use that link
    if custom_meet_link and not is_auto_generated:
        event['location'] = custom_meet_link
        event['description'] = (event.get('description', '') + '\n\nMeeting Link: ' + custom_meet_link).strip()
    # Priority 2: Generate Google Meet (use_meet=True and no custom link)
    elif use_meet and not custom_meet_link:
        event['conferenceData'] = {
            'createRequest': {
                'requestId': details.get('requestId', 'sample123'),
                'conferenceSolutionKey': {'type': 'hangoutsMeet'}
            }
        }
        event['location'] = 'Google Meet'
    # Priority 3: Offline meeting with physical location
    elif mode == 'offline' and location:
        event['location'] = location
    # Priority 4: Online meeting without link generation
    elif mode == 'online' and not use_meet:
        event['location'] = location if location else 'Online'
    # Default: Generate Google Meet
    else:
        event['conferenceData'] = {
            'createRequest': {
                'requestId': details.get('requestId', 'sample123'),
                'conferenceSolutionKey': {'type': 'hangoutsMeet'}
            }
        }
        event['location'] = 'Google Meet'
    
    return event
