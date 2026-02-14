"""
Update Meeting Handlers
Handles all meeting update/reschedule functionality.
"""

from flask import render_template, session
from datetime import datetime, timezone, timedelta
from dateutil.parser import parse as date_parse
import re

from services.calendar import load_email_book, find_matching_events, update_calendar_event
from modules.summary import extract_meeting_title, is_update_sentence
from modules.meeting_extractor import extract_meeting_title, extract_attendees, load_email_book as load_book
from modules.date_utils import extract_date
from modules.time_utils import handle_time_clarification_logic
from modules.action_utils import extract_action_intent
from ..utils import build_event_resource


def extract_update_details(sentence: str, email_book: list = None) -> dict:
    """Extract update-specific details from sentence."""
    if email_book is None:
        email_book = load_book()
    
    sentence_lower = sentence.lower()
    
    # Extract action intent
    intent_info = extract_action_intent(sentence)
    
    # Check if this is an update sentence - don't try to extract new meeting title
    if is_update_sentence(sentence_lower):
        meeting_identifier = ""
        print(f"DEBUG: Detected update sentence - not extracting new title")
    else:
        # Only extract title for non-update sentences
        meeting_identifier = extract_meeting_title(sentence)
    
    # Extract attendees
    attendees = extract_attendees(sentence, email_book)
    
    # Extract date
    extracted_date, _ = extract_date(sentence)
    
    # Check for duration changes
    duration_changed = bool(re.search(r'\b(\d+)\s*(minute|hour|min|hr)s?', sentence_lower))
    duration_min = None
    if duration_changed:
        duration_match = re.search(r'(\d+)\s*(minute|hour|min|hr)s?', sentence_lower)
        if duration_match:
            val = int(duration_match.group(1))
            unit = duration_match.group(2)
            duration_min = val * 60 if 'hour' in unit else val
    
    # Detect fields mentioned
    fields_to_update = []
    if re.search(r'\b(tomorrow|today|next\s+\w+|\d{1,2}(?:st|nd|rd|th)?\s+\w+|\w+\s+\d{1,2}(?:st|nd|rd|th)?)\b', sentence_lower):
        fields_to_update.append('date')
    if re.search(r'\b(\d{1,2}:\d{2}|\d{1,2}\s*(?:am|pm)|morning|afternoon|evening|night)\b', sentence_lower):
        fields_to_update.append('time')
    
    # Check for "same X" phrases
    same_meeting_phrase = bool(re.search(r'\bsame\s+(agenda|meeting|description)\b', sentence_lower))
    same_attendees = bool(re.search(r'\bsame\s+(attendees?|participants?|people)\b', sentence_lower))
    same_location = bool(re.search(r'\bsame\s+(location|place)\b', sentence_lower))
    
    return {
        'intent': intent_info.get('action', 'update'),
        'meeting_identifier': meeting_identifier,
        'attendees': attendees,
        'new_date': extracted_date,
        'duration_changed': duration_changed,
        'duration_min': duration_min,
        'fields_to_update': fields_to_update,
        'same_meeting_phrase': same_meeting_phrase,
        'same_attendees': same_attendees,
        'same_location': same_location,
    }


def detect_partial_reschedule(update_details: dict, sentence: str) -> dict:
    """Detect if this is a partial reschedule."""
    sentence_lower = sentence.lower()
    
    date_mentioned = bool(re.search(
        r'\b(tomorrow|today|next\s+\w+|\d{1,2}(?:st|nd|rd|th)?\s+\w+|\w+\s+\d{1,2}(?:st|nd|rd|th)?)\b',
        sentence_lower
    ))
    
    time_mentioned = bool(re.search(
        r'\b(\d{1,2}:\d{2}|\d{1,2}\s*(?:am|pm)|morning|afternoon|evening|night|noon|midnight)\b',
        sentence_lower
    ))
    
    relative_shift = bool(re.search(
        r'\b(push|delayed?|postpone|shift|move)\s+(by|to)\s+\d+\s*(minute|hour|day)s?',
        sentence_lower
    ))
    
    return {
        **update_details,
        'date_changed': date_mentioned,
        'time_changed': time_mentioned or relative_shift,
        'preserve_date': not date_mentioned,
        'preserve_time': not time_mentioned and not relative_shift,
    }


def resolve_update_time(sentence: str, now: datetime = None, base_date: datetime = None) -> dict:
    """Resolve time using handle_time_clarification_logic()."""
    ist = timezone(timedelta(hours=5, minutes=30))
    if now is None:
        now = datetime.now(ist)
    if base_date is None:
        base_date = now
    
    time_result = handle_time_clarification_logic(sentence, base_date=base_date, now=now)
    
    return {
        'start_time': time_result.get('start_time'),
        'end_time': time_result.get('end_time'),
        'needs_clarification': time_result.get('needs_clarification', False),
        'clarification_message': time_result.get('clarification_message'),
    }


def handle_update_meeting(sentence: str, service):
    """Handle update/reschedule meeting request."""
    email_book = load_email_book()
    now = datetime.now(timezone(timedelta(hours=5, minutes=30)))
    
    # Step 1: Extract update-specific details
    update_details = extract_update_details(sentence, email_book)
    
    # Step 2: Detect partial reschedule
    update_details = detect_partial_reschedule(update_details, sentence)
    
    # Step 3: Find matching events (pass extracted_date to filter by date)
    # Note: attendee_names is not passed because find_matching_events already extracts names from sentence
    matching_events = find_matching_events(
        service, 
        sentence, 
        email_book, 
        extracted_date=update_details.get('new_date')
    )
    
    if not matching_events:
        return render_template('message_standalone.html',
            title="No Matching Events",
            icon="🔍",
            message="No meetings matching your request were found to update.",
            message_type="warning")
    
    # Step 4: Determine base_date for time resolution
    base_date_for_time = now
    if matching_events and update_details.get('preserve_date', True):
        original_start_str = matching_events[0].get('start', {}).get('dateTime', '')
        if original_start_str:
            original_start = date_parse(original_start_str)
            base_date_for_time = original_start.replace(hour=9, minute=0, second=0)
    
    # Step 5: Resolve time
    time_result = resolve_update_time(sentence, base_date=base_date_for_time, now=now)
    
    if time_result['needs_clarification']:
        from .clarify import handle_time_clarification
        return handle_time_clarification(
            sentence, 
            error_message=time_result['clarification_message']
        )
    
    # Store for selection handler
    session['update_sentence'] = sentence
    session['update_details'] = update_details
    session['resolved_time'] = {
        'start': time_result['start_time'].isoformat() if time_result['start_time'] else None,
        'end': time_result['end_time'].isoformat() if time_result['end_time'] else None,
    }
    session['extraction_done'] = True
    
    # Check if user specified a new date/time
    date_mentioned = update_details.get('date_changed', False)
    time_mentioned = update_details.get('time_changed', False)
    user_specified_date = date_mentioned or time_mentioned
    
    # CRITICAL: Set user_specified_date flag when user provides new date/time
    # This prevents using original date instead of user-specified date
    if user_specified_date:
        session['user_specified_date'] = True
        
        # Store the extracted date for use when user selects an event
        extracted_date = update_details.get('new_date')
        if extracted_date:
            session['update_new_date'] = {
                'year': extracted_date.year,
                'month': extracted_date.month,
                'day': extracted_date.day,
            }
    
    if len(matching_events) == 1:
        return _apply_update_to_event(
            matching_events[0], 
            update_details, 
            time_result,
            sentence
        )
    
    return _show_update_selection(matching_events, update_details, sentence)


def _apply_update_to_event(original_event: dict, update_details: dict, time_result: dict, sentence: str):
    """Apply partial update to a single event."""
    event_id = original_event.get('id')
    
    original_start_str = original_event.get('start', {}).get('dateTime', '')
    original_end_str = original_event.get('end', {}).get('dateTime', '')
    
    original_start = date_parse(original_start_str) if original_start_str else None
    original_end = date_parse(original_end_str) if original_end_str else None
    
    original_duration = None
    if original_start and original_end:
        original_duration = (original_end - original_start).total_seconds() / 60
    
    # Always preserve original summary and description unless explicitly changed
    existing_summary = original_event.get('summary', '')
    existing_description = original_event.get('description', '')
    existing_location = original_event.get('location', '')
    existing_attendees = original_event.get('attendees', [])
    
    new_start = None
    new_end = None
    
    extracted_date = update_details.get('new_date')
    preserve_date = update_details.get('preserve_date', True)
    resolved_start = time_result.get('start_time')
    resolved_end = time_result.get('end_time')
    preserve_time = update_details.get('preserve_time', True)
    
    # Debug output
    print(f"DEBUG: _apply_update_to_event:")
    print(f"  extracted_date = {extracted_date}")
    print(f"  preserve_date = {preserve_date}")
    print(f"  resolved_start = {resolved_start}")
    print(f"  resolved_end = {resolved_end}")
    print(f"  preserve_time = {preserve_time}")
    
    if not preserve_date and extracted_date and resolved_start:
        new_start = extracted_date.replace(
            hour=resolved_start.hour,
            minute=resolved_start.minute,
            second=0,
            microsecond=0,
            tzinfo=resolved_start.tzinfo
        )
        print(f"  Using extracted_date with resolved time: {new_start}")
    elif not preserve_time and resolved_start and original_start:
        new_start = original_start.replace(
            hour=resolved_start.hour,
            minute=resolved_start.minute,
            second=0,
            microsecond=0
        )
        print(f"  Using original date with new time: {new_start}")
    elif resolved_start and resolved_end:
        new_start = resolved_start
        new_end = resolved_end
        print(f"  Using resolved times directly: {new_start} - {new_end}")
    
    if new_start:
        if update_details.get('duration_changed') and update_details.get('duration_min'):
            new_end = new_start + timedelta(minutes=update_details['duration_min'])
        elif original_duration:
            new_end = new_start + timedelta(minutes=original_duration)
        elif resolved_end:
            new_end = resolved_end
        else:
            new_end = new_start + timedelta(minutes=30)
    
    update_payload = {}
    
    # Always preserve original summary (unless explicitly changed)
    if existing_summary:
        update_payload['summary'] = existing_summary
    
    # Preserve description (unless explicitly changed)
    if existing_description:
        update_payload['description'] = existing_description
    
    # Preserve location (unless explicitly changed)
    if existing_location:
        update_payload['location'] = existing_location
    
    # Preserve attendees (unless explicitly changed)
    if existing_attendees:
        update_payload['attendees'] = existing_attendees
    
    # Apply date/time changes
    if new_start:
        from datetime import timezone as tz
        if new_start.tzinfo is None:
            new_start = new_start.replace(tzinfo=tz.utc)
        update_payload['start'] = {'dateTime': new_start.isoformat()}
    
    if new_end:
        from datetime import timezone as tz
        if new_end.tzinfo is None:
            new_end = new_end.replace(tzinfo=tz.utc)
        update_payload['end'] = {'dateTime': new_end.isoformat()}
    
    print(f"DEBUG: update_payload = {update_payload}")
    
    result = update_calendar_event(event_id, update_payload)
    
    if result['success']:
        return _show_update_success(result.get('event', {}))
    else:
        return render_template('message_standalone.html',
            title="Update Failed",
            icon="❌",
            message=result.get('error', 'Unknown error'),
            message_type="error")


def _show_update_selection(matching_events: list, update_details: dict, sentence: str):
    """Show event selection when multiple matches found."""
    formatted_events = []
    
    # Extract update parameters to pass via URL
    extracted_date = update_details.get('new_date')
    resolved_time = session.get('resolved_time', {})
    
    # Build query string with update parameters
    query_params = []
    if extracted_date:
        query_params.append(f"year={extracted_date.year}")
        query_params.append(f"month={extracted_date.month}")
        query_params.append(f"day={extracted_date.day}")
    
    resolved_start = resolved_time.get('start_time')
    if resolved_start:
        query_params.append(f"hour={resolved_start.hour}")
        query_params.append(f"minute={resolved_start.minute}")
    
    query_string = '&'.join(query_params) if query_params else ""
    
    for event_match in matching_events:
        summary = event_match.get('summary', 'Untitled Event')
        start = event_match.get('start', {}).get('dateTime', event_match.get('start', {}).get('date', ''))
        
        start_formatted = ''
        if start:
            try:
                start_dt = date_parse(start)
                start_formatted = start_dt.strftime("%A, %B %d at %I:%M %p")
            except Exception:
                start_formatted = start
        
        # Build URL with query parameters
        event_id = event_match.get('id', '')
        event_url = f"/update_event/{event_id}"
        if query_string:
            event_url = f"{event_url}?{query_string}"
        
        formatted_events.append({
            'id': event_id,
            'url': event_url,
            'summary': summary,
            'start': start_formatted,
        })
    
    return render_template('update_select_standalone.html', 
        events=formatted_events, 
        original_sentence=sentence)


def _show_update_success(updated_event: dict):
    """Display successful update."""
    from dateutil.parser import parse as date_parse
    
    event_summary = updated_event.get('summary', 'Untitled Meeting')
    event_start = updated_event.get('start', {}).get('dateTime', '')
    event_end = updated_event.get('end', {}).get('dateTime', '')
    event_description = updated_event.get('description', '')
    event_location = updated_event.get('location', '')
    event_attendees = updated_event.get('attendees', [])
    hangout_link = updated_event.get('hangoutLink', '')
    html_link = updated_event.get('htmlLink', '')
    event_attachments = updated_event.get('attachments', [])
    
    print("\n" + "="*60)
    print("MEETING UPDATED SUCCESSFULLY - ALL DETAILS")
    print("="*60)
    print(f"Summary:      {event_summary}")
    print(f"Start:        {event_start}")
    print(f"End:          {event_end}")
    print(f"Location:     {event_location}")
    print(f"Description:  {event_description}")
    print(f"Attendees:    {[a.get('email', '') for a in event_attendees]}")
    print(f"Attachments:  {[a.get('title', '') for a in event_attachments]}")
    print(f"Google Meet:  {hangout_link}")
    print(f"Calendar URL: {html_link}")
    print("="*60 + "\n")
    
    # Format a detailed message for chat
    formatted_start = ""
    if event_start:
        try:
            start_dt = date_parse(event_start)
            formatted_start = start_dt.strftime("%A, %B %d at %I:%M %p")
        except:
            formatted_start = event_start
    
    formatted_end = ""
    if event_end:
        try:
            end_dt = date_parse(event_end)
            formatted_end = end_dt.strftime("%I:%M %p")
        except:
            formatted_end = event_end
    
    attendees_list = [a.get('email', '') for a in event_attendees]
    attendees_str = ", ".join(attendees_list) if attendees_list else ""
    
    attachments_list = [a.get('title', '') for a in event_attachments]
    attachments_str = ", ".join(attachments_list) if attachments_list else ""
    
    # Build detailed bot response showing the updated event title
    bot_response_parts = [f"✅ Meeting '{event_summary}' has been updated successfully!"]
    bot_response_parts.append(f"Title: {event_summary}")
    bot_response_parts.append(f"📅 Start: {formatted_start}")
    bot_response_parts.append(f"⏰ End: {formatted_end}")
    if event_location:
        bot_response_parts.append(f"📍 Location: {event_location}")
    if attendees_str:
        bot_response_parts.append(f"👥 Attendees: {attendees_str}")
    if attachments_str:
        bot_response_parts.append(f"📎 Attachments: {attachments_str}")
    if hangout_link:
        bot_response_parts.append(f"🔗 Google Meet: {hangout_link}")
    if html_link:
        bot_response_parts.append(f"📆 Calendar: {html_link}")
    
    bot_response = "\n".join(bot_response_parts)
    
    # Use the updated event summary as the title
    # Detect if meeting is offline based on location
    meeting_mode = 'offline' if event_location and 'meet.google.com' not in event_location and 'Online' not in event_location else 'online'
    
    return render_template('meeting_details_standalone.html',
        title=event_summary,  # Show the updated event title
        icon="✅",
        message=f"Meeting '{event_summary}' has been updated successfully!",
        show_details=True,
        summary=event_summary,
        start=formatted_start,
        end=formatted_end,
        location=event_location,
        description=event_description,  # Pass description
        attachments=event_attachments,
        attendees=", ".join([a.get('email', '') for a in event_attendees]) if event_attendees else "",
        hangout_link=hangout_link,
        html_link=html_link,
        meeting_mode=meeting_mode,
        message_type="bot",
        action="update")
