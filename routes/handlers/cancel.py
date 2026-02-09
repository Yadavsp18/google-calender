"""
Cancel Meeting Handlers
Handles all meeting cancellation/deletion functionality.
"""

from flask import render_template

from services.calendar import load_email_book, find_matching_events, delete_calendar_event
from ..utils import format_event_datetime


def handle_cancel_meeting(sentence, service=None):
    """Handle cancel meeting request."""
    if service is None:
        from services.calendar import get_calendar_service
        service = get_calendar_service()
        
        if not service:
            return render_template('message.html',
                title="Authentication Required",
                icon="🔐",
                message="Please connect your Google Calendar first.",
                message_type="warning"), 401
    
    email_book = load_email_book()
    matching_events = find_matching_events(service, sentence, email_book)
    
    if not matching_events:
        return render_template('message.html',
            title="No Matching Events",
            icon="🔍",
            message="No meetings matching your request were found to cancel.",
            message_type="warning")
    
    # Show selection for all matches (even single ones)
    return _show_delete_selection(matching_events)


def _delete_single_event(matching_event, service):
    """Delete a single event."""
    event_id = matching_event.get('id')
    event_summary = matching_event.get('summary', 'Meeting')
    
    result = delete_calendar_event(event_id)
    
    if result['success']:
        return render_template('message.html',
            title="Meeting Cancelled",
            icon="✅",
            message=f"Meeting '{event_summary}' has been cancelled successfully!",
            message_type="success")
    else:
        return render_template('message.html',
            title="Cancellation Failed",
            icon="❌",
            message=result.get('error', 'Unknown error'),
            message_type="error")


def _show_delete_selection(matching_events):
    """Show event selection when multiple matches found."""
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
                end = end
        
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
    
    return render_template('delete_select.html', events=formatted_events)
