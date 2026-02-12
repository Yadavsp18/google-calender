"""
Cancel Meeting Handlers
Handles all meeting cancellation/deletion functionality.
"""

from flask import jsonify, session, render_template

from services.calendar import load_email_book, find_matching_events, delete_calendar_event
from ..utils import format_event_datetime
from modules.date_utils import extract_date
from modules.meeting_extractor import extract_meeting_details

def handle_cancel_meeting(sentence, service=None):
    """Handle cancel meeting request."""
    # Extract date from sentence for filtering
    date_result = extract_date(sentence)
    # extract_date returns (date, is_past) tuple
    extracted_date = date_result[0] if date_result else None
    email_book = load_email_book()
    details = extract_meeting_details(sentence, email_book)
    attendee_names = details.get('attendee_names', [])
    attendees = details.get('attendees', [])


    
    print(f"DEBUG: Cancel search - extracted_date: {extracted_date}")
    print(f"DEBUG: Cancel search - attendee_names: {attendee_names}")
    if service is None:
        from services.calendar import get_calendar_service
        service = get_calendar_service()
        
        if not service:
            return jsonify({
                'success': False,
                'error': 'Not authenticated',
                'redirect': '/auth'
            })
    
    matching_events = find_matching_events(
        service, sentence, email_book,
        extracted_date=extracted_date,
        attendee_names=attendee_names,
        attendees=attendees
    )
    
    if not matching_events:
        return jsonify({
            'success': False,
            'title': 'No Matching Events',
            'icon': '🔍',
            'message': 'No meetings matching your request were found to cancel.'
        })
    
    # If only one match, delete it directly
    if len(matching_events) == 1:
        return _delete_single_event(matching_events[0], service)
    
    # Multiple matches - return selection UI as JSON
    return _show_delete_selection_json(matching_events)


def _delete_single_event(matching_event, service):
    """Delete a single event."""
    event_id = matching_event.get('id')
    event_summary = matching_event.get('summary', 'Meeting')
    event_start = matching_event.get('start', {}).get('dateTime', matching_event.get('start', {}).get('date', ''))
    event_end = matching_event.get('end', {}).get('dateTime', matching_event.get('end', {}).get('date', ''))
    event_location = matching_event.get('location', '')
    event_attendees = matching_event.get('attendees', [])
    event_description = matching_event.get('description', '')
    
    result = delete_calendar_event(event_id)
    
    if result['success']:
        # Format the event details for display
        from dateutil.parser import parse as date_parse
        from ..utils import format_event_datetime
        
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
        attendees_str = ', '.join(attendees_list) if attendees_list else ''
        
        # Return JSON response with all event details
        return jsonify({
            'success': True,
            'title': 'Meeting Cancelled',
            'icon': '🗑️',
            'message': f"Meeting '{event_summary}' has been cancelled successfully!",
            'show_details': True,
            'summary': event_summary,
            'start': start_formatted,
            'end': end_formatted,
            'location': event_location,
            'attendees': attendees_str,
            'description': event_description,
            'message_type': 'success',
            'action': 'cancel',
            'redirect': '/'
        })
    else:
        return jsonify({
            'success': False,
            'title': 'Cancellation Failed',
            'icon': '❌',
            'message': result.get('error', 'Unknown error'),
            'message_type': 'error'
        })


def _show_delete_selection_json(matching_events):
    """Return event selection as JSON when multiple matches found."""
    formatted_events = []
    for event_match in matching_events:
        # Extract full event details
        summary = event_match.get('summary', 'Untitled Event')
        start = event_match.get('start', {}).get('dateTime', event_match.get('start', {}).get('date', ''))
        end = event_match.get('end', {}).get('dateTime', event_match.get('end', {}).get('date', ''))
        location = event_match.get('location', '')
        attendees = event_match.get('attendees', [])
        description = event_match.get('description', '')
        
        # Format start time
        from dateutil.parser import parse as date_parse
        start_formatted = ''
        if start:
            try:
                start_dt = date_parse(start)
                start_formatted = start_dt.strftime("%A, %B %d at %I:%M %p")
            except Exception:
                start_formatted = start
        
        # Format end time
        end_formatted = ''
        if end:
            try:
                end_dt = date_parse(end)
                end_formatted = end_dt.strftime("%I:%M %p")
            except Exception:
                end_formatted = end
        
        # Format attendees
        attendees_list = [a.get('email', '') for a in attendees if a.get('email')]
        
        formatted_events.append({
            'id': event_match.get('id'),
            'summary': summary,
            'start': start_formatted,
            'end': end_formatted,
            'location': location,
            'attendees': ', '.join(attendees_list),
            'description': description[:100] + '...' if len(description) > 100 else description
        })
    
    return jsonify({
        'success': True,
        'title': 'Select Meeting to Cancel',
        'icon': '🗑️',
        'message': 'Multiple meetings found. Please select one to cancel:',
        'events': formatted_events,
        'show_selection': True
    })
