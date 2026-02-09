"""
Calendar Service Module
Handles Google Calendar API interactions.
"""

import os
import json
from datetime import datetime, timedelta, timezone

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient import errors as googleapiclient_errors
from google_auth_oauthlib.flow import InstalledAppFlow

# Import Drive utilities from separate module
from modules.drive_utils import upload_to_drive


# Import scopes from auth service (unified with Calendar and Drive)
from services.auth import SCOPES as CALENDAR_SCOPES

# Path to token and credentials
TOKEN_FILE = os.path.join(os.path.dirname(__file__), '..', 'config', 'token.json')
CREDS_FILE = os.path.join(os.path.dirname(__file__), '..', 'config', 'credentials.json')


def get_calendar_service():
    """Get authenticated Google Calendar service."""
    creds = None
    
    # Load existing credentials
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, CALENDAR_SCOPES)
    
    # If no valid credentials, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDS_FILE):
                return None
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, CALENDAR_SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials for next run
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    
    return build('calendar', 'v3', credentials=creds)


def load_email_book():
    """Load email book from config/email.json."""
    email_file = os.path.join(os.path.dirname(__file__), '..', 'config', 'email.json')
    if not os.path.exists(email_file):
        return []
    with open(email_file, 'r') as f:
        return json.load(f)


def load_teams():
    """Load teams from config/teams.json."""
    teams_file = os.path.join(os.path.dirname(__file__), '..', 'config', 'teams.json')
    if not os.path.exists(teams_file):
        return {}
    with open(teams_file, 'r') as f:
        return json.load(f)


def resolve_team_members(team_name, teams_data):
    """
    Resolve a team name to list of member emails.
    
    Args:
        team_name: Name of the team (e.g., "tech team", "dm team")
        teams_data: Loaded teams configuration
    
    Returns:
        list: List of member email addresses, or None if team not found
    """
    teams = teams_data.get('teams', {})
    
    # Normalize team name
    team_name_lower = team_name.lower().strip()
    
    # Check exact match and aliases
    for team_key, team_data in teams.items():
        if team_key.lower() == team_name_lower:
            return team_data.get('members', [])
        
        aliases = team_data.get('aliases', [])
        if team_name_lower in [a.lower() for a in aliases]:
            return team_data.get('members', [])
    
    return None


def load_api_key():
    """Load Gemini API key from config."""
    api_key_file = os.path.join(os.path.dirname(__file__), '..', 'config', 'api_key.json')
    if not os.path.exists(api_key_file):
        return None
    with open(api_key_file, 'r') as f:
        data = json.load(f)
        return data.get('GEMINI_API_KEY')


def delete_calendar_event(event_id):
    """Delete a calendar event."""
    from googleapiclient.errors import HttpError
    
    service = get_calendar_service()
    
    if not service:
        return {'success': False, 'error': 'Not authenticated'}
    
    try:
        # First verify the event exists
        try:
            event = service.events().get(calendarId='primary', eventId=event_id).execute()
            event_summary = event.get('summary', 'Unknown Event')
        except HttpError as e:
            if e.resp.status == 404:
                return {'success': False, 'error': f'Event with ID {event_id} not found in Google Calendar'}
            raise e
        
        # Delete the event
        service.events().delete(
            calendarId='primary',
            eventId=event_id,
            sendUpdates='all'
        ).execute()
        
        return {'success': True, 'message': f"Event '{event_summary}' has been cancelled successfully!"}
    except HttpError as e:
        return {'success': False, 'error': f'Google API Error: {str(e)}'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def update_calendar_event(event_id, event_data):
    """Update a calendar event."""
    service = get_calendar_service()
    
    if not service:
        return {'success': False, 'error': 'Not authenticated'}
    
    try:
        updated_event = service.events().update(
            calendarId='primary',
            eventId=event_id,
            body=event_data,
            sendUpdates='all'
        ).execute()
        return {'success': True, 'message': 'Event updated successfully', 'event': updated_event}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_calendar_event(event_id):
    """Get a single calendar event by ID."""
    service = get_calendar_service()
    
    if not service:
        return None
    
    try:
        event = service.events().get(
            calendarId='primary',
            eventId=event_id
        ).execute()
        return event
    except Exception:
        return None


def get_upcoming_events():
    """Get upcoming events from Google Calendar."""
    service = get_calendar_service()
    
    if not service:
        return []
    
    try:
        now = datetime.now(timezone.utc)
        events_result = service.events().list(
            calendarId='primary',
            timeMin=now.isoformat(),
            maxResults=10,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        return events_result.get('items', [])
    except Exception:
        return []


def create_calendar_event(service, event_data):
    """Create a calendar event."""
    try:
        created_event = service.events().insert(
            calendarId='primary',
            body=event_data,
            conferenceDataVersion=0,
            sendUpdates='all'
        ).execute()
        
        return created_event
    except Exception as e:
        print(f"Error creating event: {e}")
        return None


def create_calendar_event_with_attachment(service, event_data, drive_file_id, drive_file_name, drive_file_url=None):
    """Create a calendar event with a Google Drive attachment."""
    try:
        # Add attachment to event
        if 'attachments' not in event_data:
            event_data['attachments'] = []
        
        # Use provided URL or construct from fileId
        file_url = drive_file_url or f'https://drive.google.com/file/d/{drive_file_id}/view'
        
        event_data['attachments'].append({
            'fileId': drive_file_id,
            'fileUrl': file_url,
            'title': drive_file_name,
            'mimeType': 'application/octet-stream'
        })
        
        created_event = service.events().insert(
            calendarId='primary',
            body=event_data,
            conferenceDataVersion=0,
            sendUpdates='all'
        ).execute()
        
        return created_event
    except Exception as e:
        print(f"Error creating event with attachment: {e}")
        return None


def find_matching_events(service, sentence, email_book):
    """
    Find events matching a natural language description.
    
    Args:
        service: Google Calendar service
        sentence: Natural language description
        email_book: Email book for name resolution
    
    Returns:
        list: List of matching events
    """
    from modules.meeting_extractor import extract_meeting_details
    
    # Use timezone-aware datetime for Google Calendar API
    from datetime import timezone
    now = datetime.now(timezone.utc)
    # Extended search range to 60 days
    time_min = now.isoformat()
    time_max = (now + timedelta(days=60)).isoformat()
    
    try:
        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            maxResults=50,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])
    except Exception:
        events = []
    
    import re
    
    # Extract search term from cancel sentence
    # Patterns: "cancel meeting with john", "delete meeting john", "remove meeting john"
    search_terms = []
    team_member_emails = []  # Track team member emails for matching
    
    # Pattern to extract name(s) after "with" - handles comma/&/and-separated names too
    attendee_pattern = r'with\s+([A-Za-z]+(?:\s*[,&\s]\s*[A-Za-z]+)*)'
    attendee_match = re.search(attendee_pattern, sentence, re.IGNORECASE)
    if attendee_match:
        extracted_name = attendee_match.group(1).strip().lower()
        
        # Split by comma or & to get individual names
        name_parts = re.split(r'\s*[,&]\s*', extracted_name)
        for name in name_parts:
            name = name.strip()
            # Skip common connector words
            if not name or name in ['and', '&', ',']:
                continue
            
            # Check if it's a team name
            teams_data = load_teams()
            team_emails = resolve_team_members(name, teams_data)
            if team_emails:
                # It's a team - add all team member emails for matching
                team_member_emails.extend([e.lower() for e in team_emails])
                if name not in search_terms:
                    search_terms.append(name)
            elif name not in search_terms:
                search_terms.append(name)
    
    # Also try to extract from cancel patterns
    cancel_patterns = [
        r'(?:cancel|delete|remove)\s+(?:meeting\s+)?(?:with\s+)?(.+)',
        r'(?:cancel|delete|remove)\s+(?:my\s+)?(?:meeting\s+)?(?:with\s+)?(.+)',
    ]
    for pattern in cancel_patterns:
        match = re.search(pattern, sentence, re.IGNORECASE)
        if match:
            term = match.group(1).strip().lower()
            # Clean up common words
            term = re.sub(r'\b(?:meeting|event|appointment|my)\b', '', term).strip()
            
            # Check if it's a team name
            if term:
                teams_data = load_teams()
                team_emails = resolve_team_members(term, teams_data)
                if team_emails:
                    team_member_emails.extend([e.lower() for e in team_emails])
                    if term not in search_terms:
                        search_terms.append(term)
                elif term not in search_terms:
                    search_terms.append(term)
            break
    
    # Also extract from extract_meeting_details
    details = extract_meeting_details(sentence, email_book)
    attendee_names = [name.lower() for name in details.get('attendee_names', [])]
    search_terms.extend(attendee_names)
    
    # Get meeting title keywords
    meeting_title = details.get('meeting_title', '').lower()
    # Extract name from "with X" pattern in title
    title_name_match = re.search(r'with\s+([A-Za-z]+(?:\s+and?\s+[A-Za-z]+)?)', meeting_title, re.IGNORECASE)
    if title_name_match:
        title_name = title_name_match.group(1).strip().lower()
        if title_name not in search_terms:
            search_terms.append(title_name)
    
    matching_events = []
    
    print(f"DEBUG: Searching for events with terms: {search_terms}")
    print(f"DEBUG: Team member emails: {team_member_emails}")
    print(f"DEBUG: Attendee names: {attendee_names}")
    
    for event in events:
        event_summary = event.get('summary', '').lower()
        event_description = event.get('description', '').lower()
        
        is_match = False
        
        # Check if this is a "with X" type meeting (matching by name in title)
        # Only match if the search term is part of a "with X" pattern
        for term in search_terms:
            if term:
                # Check for "with X" pattern in the title
                with_pattern = r'with\s+' + re.escape(term) + r'(?:\s|$|,)'
                if re.search(with_pattern, event_summary):
                    is_match = True
                    break
        
        # Check team member emails if team was specified
        if team_member_emails and not is_match:
            event_attendees = [a.get('email', '').lower() for a in event.get('attendees', [])]
            for team_email in team_member_emails:
                for event_email in event_attendees:
                    if team_email in event_email:
                        is_match = True
                        break
                if is_match:
                    break
        
        # Check if any attendee name is in the event attendees (by email or display name)
        # This is the most important check - only match if person is an attendee
        if not is_match and attendee_names:
            for name in attendee_names:
                name_lower = name.lower().strip()
                name_parts = name_lower.split()
                
                for event_attendee in event.get('attendees', []):
                    attendee_email = event_attendee.get('email', '').lower()
                    attendee_display_name = event_attendee.get('displayName', '').lower()
                    
                    # Check if full name matches email or display name
                    if name_lower in attendee_email or name_lower in attendee_display_name:
                        is_match = True
                        break
                    
                    # Check if all name parts are found (for partial matching)
                    # Require at least 2 matching parts for multi-word names, or exact match for single-word names
                    if len(name_parts) == 1:
                        # Single name - check if it substantially matches (at least 4 chars)
                        if len(name_parts[0]) >= 4:
                            if name_parts[0] in attendee_email or name_parts[0] in attendee_display_name:
                                is_match = True
                                break
                    else:
                        # Multi-word name - check if all parts are found
                        all_parts_found = True
                        for part in name_parts:
                            if len(part) < 2:  # Skip very short parts
                                continue
                            if part not in attendee_email and part not in attendee_display_name:
                                all_parts_found = False
                                break
                        if all_parts_found:
                            is_match = True
                            break
                
                if is_match:
                    break
        
        if is_match:
            matching_events.append(event)
            print(f"DEBUG: Matched event: {event_summary}")
    
    print(f"DEBUG: Total matching events: {len(matching_events)}")
    return matching_events
