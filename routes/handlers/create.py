"""
Create Meeting Handlers
Handles all meeting creation functionality.
"""

from flask import render_template
from datetime import timedelta, timezone

from services.calendar import load_email_book, create_calendar_event_with_attachment
from modules.meeting_extractor import extract_meeting_details
from ..utils import build_event_resource


def handle_create_meeting(sentence, service, drive_file_id=None, drive_file_name=None, drive_file_url=None):
    """Handle meeting creation from natural language - without clarification steps."""
    email_book = load_email_book()
    details = extract_meeting_details(sentence, email_book)
    
    # Check for error in details
    if details.get('error'):
        return render_template('message_standalone.html',
            title="Error",
            icon="❌",
            message=details['error'],
            message_type="error")
    
    # Auto-handle times - default to now + 30 minutes if not specified
    from datetime import datetime
    ist = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(ist)
    
    if details.get('start') is None:
        # Default to now + 30 minutes
        start_dt = now + timedelta(minutes=30)
        end_dt = start_dt + timedelta(minutes=details.get('duration_min', 30))
        details['start'] = start_dt
        details['end'] = end_dt
    elif details.get('end') is None:
        # Calculate end time based on duration
        start_dt = details['start']
        end_dt = start_dt + timedelta(minutes=details.get('duration_min', 30))
        details['end'] = end_dt
    
    # Make datetimes timezone-aware
    if details['start'].tzinfo is None:
        details['start'] = details['start'].replace(tzinfo=ist)
    if details['end'].tzinfo is None:
        details['end'] = details['end'].replace(tzinfo=ist)
    
    return _execute_create_meeting(details, sentence, service, drive_file_id=drive_file_id, drive_file_name=drive_file_name, drive_file_url=drive_file_url)


def _execute_create_meeting(details, sentence, service, drive_file_id=None, drive_file_name=None, drive_file_url=None):
    """Execute the actual meeting creation."""
    from dateutil.parser import parse as date_parse
    
    custom_meet_link = details.get('meet_link', '')
    meal_time_adjusted = details.get('meal_time_adjusted', False)
    original_time = details.get('original_time', '')
    adjusted_time = details.get('adjusted_time', '')
    
    event = build_event_resource(details, custom_meet_link)
    
    print(f"DEBUG: drive_file_id={drive_file_id}, drive_file_name={drive_file_name}, drive_file_url={drive_file_url}")
    
    try:
        # Create event with attachment if file was uploaded
        if drive_file_id and drive_file_name:
            print(f"DEBUG: Creating event with attachment: {drive_file_name}")
            created_event = create_calendar_event_with_attachment(
                service, event, drive_file_id, drive_file_name, drive_file_url
            )
            if created_event:
                print(f"DEBUG: Event created with ID: {created_event.get('id')}")
                print(f"DEBUG: Event attachments: {created_event.get('attachments', [])}")
            else:
                print("DEBUG: Event creation returned None")
        else:
            print("DEBUG: No file attachment - creating event without attachment")
            created_event = service.events().insert(
                calendarId='primary',
                body=event,
                conferenceDataVersion=1 if details.get('use_meet') else 0,
                sendUpdates='all'
            ).execute()
        
        # Extract all event details for display
        event_summary = created_event.get('summary', 'Untitled Meeting')
        event_start = created_event.get('start', {}).get('dateTime', '')
        event_end = created_event.get('end', {}).get('dateTime', '')
        event_description = created_event.get('description', '')
        event_location = created_event.get('location', '')
        event_attendees = created_event.get('attendees', [])
        event_attachments = created_event.get('attachments', [])
        hangout_link = created_event.get('hangoutLink', '')
        html_link = created_event.get('htmlLink', '')
        
        # Print all details to terminal for verification
        print("\n" + "="*60)
        print("MEETING CREATED SUCCESSFULLY - ALL DETAILS")
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
        
        # Build detailed bot response matching meeting_details.html format
        bot_response_parts = [f"✅ Meeting '{event_summary}' has been created successfully!"]
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
        
        return render_template('meeting_details_standalone.html',
            title="Meeting Created",
            icon="✅",
            message=f"'{event_summary}' has been created successfully!",
            show_details=True,
            summary=event_summary,
            start=formatted_start,
            end=formatted_end,
            location=event_location,
            description=event_description,
            attachments=event_attachments,
            attendees=", ".join([a.get('email', '') for a in event_attendees]) if event_attendees else "",
            hangout_link=hangout_link,
            html_link=html_link,
            meeting_mode=details.get('mode', 'online'),
            message_type="bot",
            action="create")
        
    except Exception as e:
        return render_template('message_standalone.html',
            title="Creation Failed",
            icon="❌",
            message=str(e),
            message_type="error")
