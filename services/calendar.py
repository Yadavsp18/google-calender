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

# Import Drive utilities from existing module
from modules.drive_utils import upload_to_drive

# Import Event Matching module
from modules.event_matching import find_matching_events


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
    from dateutil.parser import parse as date_parse
    
    service = get_calendar_service()
    
    if not service:
        return {'success': False, 'error': 'Not authenticated'}
    
    try:
        # First verify the event exists and get its details
        try:
            event = service.events().get(calendarId='primary', eventId=event_id).execute()
            event_summary = event.get('summary', 'Unknown Event')
            event_start = event.get('start', {}).get('dateTime', event.get('start', {}).get('date', ''))
            event_end = event.get('end', {}).get('dateTime', event.get('end', {}).get('date', ''))
            event_location = event.get('location', '')
            event_attendees = event.get('attendees', [])
            event_description = event.get('description', '')
        except HttpError as e:
            if e.resp.status == 404:
                return {'success': False, 'error': f'Event with ID {event_id} not found in Google Calendar'}
            raise e
        
        # Format start time
        start_formatted = ''
        if event_start:
            try:
                start_dt = date_parse(event_start)
                start_formatted = start_dt.strftime("%A, %B %d at %I:%M %p")
            except Exception:
                start_formatted = event_start
        
        # Format end time
        end_formatted = ''
        if event_end:
            try:
                end_dt = date_parse(event_end)
                end_formatted = end_dt.strftime("%I:%M %p")
            except Exception:
                end_formatted = event_end
        
        # Format attendees
        attendees_list = [a.get('email', '') for a in event_attendees if a.get('email')]
        
        # Build detailed message
        details_parts = []
        details_parts.append(f"Meeting '{event_summary}' has been cancelled successfully!")
        details_parts.append(f"📅 Date/Time: {start_formatted} - {end_formatted}")
        
        if event_location:
            details_parts.append(f"📍 Location: {event_location}")
        
        if attendees_list:
            details_parts.append(f"👥 Attendees: {', '.join(attendees_list)}")
        
        if event_description:
            desc_preview = event_description[:150] + '...' if len(event_description) > 150 else event_description
            details_parts.append(f"📝 Description: {desc_preview}")
        
        detailed_message = '\n'.join(details_parts)
        
        # Delete the event
        service.events().delete(
            calendarId='primary',
            eventId=event_id,
            sendUpdates='all'
        ).execute()
        
        return {'success': True, 'message': detailed_message}
    except HttpError as e:
        return {'success': False, 'error': f'Google API Error: {str(e)}'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


# ============================================================
# Step 2: Search events by meeting name
# ============================================================

def search_events_by_name(service, meeting_name, max_results=10):
    """
    Search events by meeting name using the q parameter.
    
    The q parameter searches both summary and description.
    
    Args:
        service: Google Calendar service
        meeting_name: Name of the meeting to search for
        max_results: Maximum number of results to return
    
    Returns:
        dict: Contains 'events' list and 'success' status
    """
    try:
        # Use current time as timeMin to get upcoming events
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        
        events_result = service.events().list(
            calendarId="primary",
            q=meeting_name,
            timeMin=now_iso,
            singleEvents=True,
            orderBy="startTime",
            maxResults=max_results
        ).execute()
        
        events = events_result.get("items", [])
        print(f"DEBUG: search_events_by_name found {len(events)} events matching '{meeting_name}'")
        
        return {
            'success': True,
            'events': events,
            'total_found': len(events)
        }
    except Exception as e:
        print(f"DEBUG: Error searching events by name: {e}")
        return {
            'success': False,
            'events': [],
            'error': str(e)
        }


# ============================================================
# Step 3: Filter the correct event (strict matching)
# ============================================================

def find_event_by_name_and_date(service, meeting_name, target_date=None, target_time=None, 
                                  time_window_hours=2):
    """
    Find event by strictly matching summary and optionally date/time.
    
    Best practice: Also check date/time as names can collide.
    
    Args:
        service: Google Calendar service
        meeting_name: Exact or partial meeting name to match
        target_date: Optional target date (datetime.date)
        target_time: Optional target time (datetime.time)
        time_window_hours: Window in hours to search around target time
    
    Returns:
        dict: Contains 'event' or None, and 'success' status
    """
    # Step 1: Search by name
    search_result = search_events_by_name(service, meeting_name, max_results=20)
    
    if not search_result['success']:
        return {'success': False, 'event': None, 'error': search_result.get('error')}
    
    events = search_result['events']
    
    if not events:
        return {'success': False, 'event': None, 'error': 'No events found matching the meeting name'}
    
    # Step 2: Filter by strict summary match
    matching_event = None
    meeting_name_lower = meeting_name.lower().strip()
    
    for event in events:
        event_summary = event.get("summary", "").lower().strip()
        
        # Strict match on summary
        if event_summary == meeting_name_lower:
            matching_event = event
            break
    
    # If no exact match, try partial match (contains)
    if not matching_event:
        for event in events:
            event_summary = event.get("summary", "").lower().strip()
            
            # Partial match - meeting name contained in summary
            if meeting_name_lower in event_summary or event_summary in meeting_name_lower:
                matching_event = event
                break
    
    if not matching_event:
        return {
            'success': False, 
            'event': None, 
            'error': 'No event found with matching summary',
            'found_events': events
        }
    
    # Step 3: If date/time provided, filter further
    if target_date:
        from dateutil.parser import parse as date_parse
        
        for event in events:
            event_summary = event.get("summary", "").lower().strip()
            
            if event_summary == meeting_name_lower:
                start_str = event.get('start', {}).get('dateTime', '')
                if start_str:
                    event_start = date_parse(start_str)
                    
                    # Check if same date
                    if event_start.date() == target_date:
                        # If time provided, check time window
                        if target_time:
                            event_time = event_start.time()
                            
                            # Calculate time difference
                            from datetime import datetime, timedelta
                            target_dt = datetime.combine(target_date, target_time)
                            event_dt = datetime.combine(event_start.date(), event_time)
                            
                            diff_hours = abs((event_dt - target_dt).total_seconds()) / 3600
                            
                            if diff_hours <= time_window_hours:
                                matching_event = event
                                break
                        else:
                            matching_event = event
                            break
    
    return {
        'success': True,
        'event': matching_event,
        'all_matching_events': events
    }


# ============================================================
# Step 4: Extract the eventId
# ============================================================

def get_event_id(event):
    """
    Extract eventId from an event dictionary.
    
    Args:
        event: Event dictionary from Google Calendar API
    
    Returns:
        str: Event ID or None if not found
    """
    if not event or not isinstance(event, dict):
        return None
    
    return event.get('id')


# ============================================================
# Step 5: Modify the event fields
# ============================================================

def modify_event_fields(event, updates):
    """
    Modify event fields with the provided updates.
    
    Only modifies fields that are provided in updates dict.
    
    Args:
        event: Original event dictionary
        updates: Dict of fields to update
    
    Returns:
        dict: Modified event dictionary
    """
    if not event:
        return None
    
    modified_event = event.copy()
    
    # Handle summary update
    if 'summary' in updates:
        modified_event['summary'] = updates['summary']
        print(f"DEBUG: Updated summary to '{updates['summary']}'")
    
    # Handle description update
    if 'description' in updates:
        modified_event['description'] = updates['description']
        print(f"DEBUG: Updated description")
    
    # Handle dateTime updates (reschedule)
    if 'start' in updates:
        modified_event['start'] = {'dateTime': updates['start']}
        print(f"DEBUG: Updated start time to '{updates['start']}'")
    
    if 'end' in updates:
        modified_event['end'] = {'dateTime': updates['end']}
        print(f"DEBUG: Updated end time to '{updates['end']}'")
    
    # Handle location update
    if 'location' in updates:
        modified_event['location'] = updates['location']
        print(f"DEBUG: Updated location to '{updates['location']}'")
    
    # Handle attendees update
    if 'attendees' in updates:
        modified_event['attendees'] = updates['attendees']
        print(f"DEBUG: Updated attendees")
    
    return modified_event


# ============================================================
# Step 6: Call Events.update / Events.patch
# ============================================================

def update_calendar_event(event_id, event_data):
    """Update a calendar event using full UPDATE method."""
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


def patch_calendar_event(event_id, update_fields):
    """
    Partially update a calendar event using PATCH method.
    
    This is safer than full update as it only changes specified fields.
    
    Args:
        event_id: The event ID to update
        update_fields: Dict of fields to update (e.g., {'location': 'Room B'})
    
    Returns:
        dict: Response with success status and updated event
    """
    service = get_calendar_service()
    
    if not service:
        return {'success': False, 'error': 'Not authenticated'}
    
    try:
        updated_event = service.events().patch(
            calendarId='primary',
            eventId=event_id,
            body=update_fields,
            sendUpdates='all'
        ).execute()
        return {'success': True, 'message': 'Event patched successfully', 'event': updated_event}
    except Exception as e:
        return {'success': False, 'error': str(e)}


# ============================================================
# Helper: Handle duplicate meeting names
# ============================================================

def find_upcoming_event_by_name(service, meeting_name):
    """
    Find the nearest upcoming event matching the name.
    
    Use when multiple events have the same name.
    Picks the one closest to now.
    
    Args:
        service: Google Calendar service
        meeting_name: Name of the meeting to search for
    
    Returns:
        dict: Event dict or None
    """
    # Get current time
    now = datetime.utcnow().isoformat() + "Z"
    
    try:
        events_result = service.events().list(
            calendarId="primary",
            q=meeting_name,
            timeMin=now,
            singleEvents=True,
            orderBy="startTime",
            maxResults=5
        ).execute()
        
        events = events_result.get("items", [])
        
        if not events:
            return None
        
        # Return the first (upcoming) event
        return events[0]
    except Exception as e:
        print(f"DEBUG: Error finding upcoming event: {e}")
        return None


def search_and_confirm_event(service, meeting_name, target_date=None, target_time=None):
    """
    Complete workflow: Search → Filter → Confirm event.
    
    Returns event if unique match found.
    Returns multiple events if duplicates exist.
    Returns None if no match.
    
    Args:
        service: Google Calendar service
        meeting_name: Name of the meeting
        target_date: Optional target date for filtering
        target_time: Optional target time for filtering
    
    Returns:
        dict: With 'event', 'events', or 'error' keys
    """
    # Search by name
    search_result = search_events_by_name(service, meeting_name, max_results=10)
    
    if not search_result['success']:
        return {'status': 'error', 'error': search_result.get('error')}
    
    events = search_result['events']
    
    if not events:
        return {'status': 'not_found', 'message': f'No events found matching "{meeting_name}"'}
    
    # Filter by exact summary match
    meeting_name_lower = meeting_name.lower().strip()
    matching_events = []
    
    for event in events:
        event_summary = event.get("summary", "").lower().strip()
        if event_summary == meeting_name_lower:
            matching_events.append(event)
    
    # If no exact match, use partial
    if not matching_events:
        for event in events:
            event_summary = event.get("summary", "").lower().strip()
            if meeting_name_lower in event_summary:
                matching_events.append(event)
    
    # Apply date/time filter if provided
    if target_date and target_time:
        from dateutil.parser import parse as date_parse
        from datetime import timedelta
        
        filtered_events = []
        target_dt = datetime.combine(target_date, target_time)
        
        for event in matching_events:
            start_str = event.get('start', {}).get('dateTime', '')
            if start_str:
                event_dt = date_parse(start_str)
                
                # Check same day and within 2 hours
                if event_dt.date() == target_date:
                    diff = abs((event_dt - target_dt).total_seconds()) / 3600
                    if diff <= 2:
                        filtered_events.append(event)
        
        matching_events = filtered_events
    
    # Determine result
    if len(matching_events) == 0:
        return {'status': 'not_found', 'message': 'No events match criteria'}
    
    if len(matching_events) == 1:
        return {
            'status': 'unique', 
            'event': matching_events[0],
            'all_events': matching_events
        }
    
    # Multiple matches
    return {
        'status': 'multiple',
        'events': matching_events,
        'count': len(matching_events)
    }


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


def get_calendar_events(service, time_min, time_max, max_results=50):
    """
    Get events from Google Calendar within a date range.
    
    Args:
        service: Google Calendar service instance
        time_min: Start time in ISO format
        time_max: End time in ISO format
        max_results: Maximum number of events to return
        
    Returns:
        List of event dictionaries
    """
    if not service:
        return []
    
    try:
        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        return events_result.get('items', [])
    except Exception as e:
        print(f"ERROR getting calendar events: {str(e)}")
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
        
        # Always use direct download link for attachments (not preview link)
        # Google Calendar API requires direct download links for attachments to work
        file_url = f'https://drive.google.com/uc?id={drive_file_id}&export=download' if drive_file_id else ''
        
        # Try to get actual MIME type and file info from Drive
        from modules.drive_utils import get_drive_service
        drive_service = get_drive_service()
        actual_mime_type = 'application/octet-stream'
        
        if drive_service:
            try:
                drive_file = drive_service.files().get(
                    fileId=drive_file_id,
                    fields='mimeType'
                ).execute()
                actual_mime_type = drive_file.get('mimeType', 'application/octet-stream')
                print(f"DEBUG: Drive file MIME type: {actual_mime_type}")
            except Exception as mime_error:
                print(f"DEBUG: Could not get MIME type: {mime_error}")
        
        attachment = {
            'fileId': drive_file_id,
            'fileUrl': file_url,
            'title': drive_file_name,
            'mimeType': actual_mime_type
        }
        
        print(f"DEBUG: Attachment fileUrl: {file_url}")
        
        print(f"DEBUG: Adding attachment to event_data: {attachment}")
        print(f"DEBUG: event_data['attachments'] before: {event_data.get('attachments', [])}")
        
        event_data['attachments'].append(attachment)
        
        print(f"DEBUG: event_data['attachments'] after: {event_data.get('attachments', [])}")
        
        # Log the full event_data for debugging
        print(f"DEBUG: Full event_data keys: {list(event_data.keys())}")
        
        print(f"DEBUG: Calling events().insert with attachments")
        
        # Add attachment link to description as fallback (in case API attachment doesn't work)
        event_description = event_data.get('description', '')
        event_description += f"\n\n📎 Attachment: {drive_file_name}\n{drive_file_url}"
        event_data['description'] = event_description
        
        created_event = service.events().insert(
            calendarId='primary',
            body=event_data,
            conferenceDataVersion=0,
            sendUpdates='all'
        ).execute()
        
        print(f"DEBUG: events().insert completed")
        print(f"DEBUG: created_event has attachments: {'attachments' in created_event}")
        print(f"DEBUG: created_event attachments: {created_event.get('attachments', [])}")
        
        return created_event
    except Exception as e:
        print(f"Error creating event with attachment: {e}")
        # Try creating event without attachment as fallback
        print("DEBUG: Trying fallback - creating event without attachment")
        try:
            created_event = service.events().insert(
                calendarId='primary',
                body=event_data,
                conferenceDataVersion=0,
                sendUpdates='all'
            ).execute()
            return created_event
        except:
            return None

