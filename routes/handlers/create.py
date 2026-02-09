"""
Create Meeting Handlers
Handles all meeting creation functionality.
"""

from flask import render_template
from datetime import timedelta, timezone

from services.calendar import load_email_book, create_calendar_event_with_attachment
from modules.meeting_extractor import extract_meeting_details
from ..utils import build_event_resource
from .clarify import (
    handle_time_clarification_wrapper,
    handle_time_clarification, 
    handle_meal_time_clarification,
    handle_time_range_clarification
)
from modules.avoid_lunch_time_adjustment import detect_meal_time_avoidance


def handle_create_meeting(sentence, service, drive_file_id=None, drive_file_name=None, drive_file_url=None):
    """Handle meeting creation from natural language."""
    email_book = load_email_book()
    details = extract_meeting_details(sentence, email_book)
    
    # Check for error in details
    if details.get('error'):
        return render_template('message.html',
            title="Error",
            icon="❌",
            message=details['error'],
            message_type="error")
    
    # Check if meal time clarification is needed
    needs_meal_clarification, meals_to_avoid = detect_meal_time_avoidance(sentence)
    if needs_meal_clarification:
        return handle_meal_time_clarification(sentence, meals_to_avoid=meals_to_avoid, 
                                               drive_file_id=drive_file_id, drive_file_name=drive_file_name, 
                                               drive_file_url=drive_file_url)
    
    # Handle time ambiguity and defaulting
    time_result = handle_time_clarification_wrapper(sentence)
    
    if time_result["needs_clarification"]:
        # Check if this is a time range clarification
        time_range = time_result.get("time_range")
        if time_range:
            return handle_time_range_clarification(
                sentence,
                time_range=time_range,
                drive_file_id=drive_file_id, drive_file_name=drive_file_name, drive_file_url=drive_file_url
            )
        return handle_time_clarification(
            sentence, 
            error_message=time_result["clarification_message"],
            extracted_time=time_result.get("extracted_time"),
            drive_file_id=drive_file_id, drive_file_name=drive_file_name, drive_file_url=drive_file_url
        )
    
    # Use resolved times if available
    if time_result["start_time"] and time_result["end_time"]:
        from datetime import timezone as tz
        start_dt = time_result["start_time"]
        end_dt = time_result["end_time"]
        
        # If duration is explicitly mentioned, recalculate end time
        # Otherwise use the end time from clarify.py (for time ranges)
        if details.get('duration_min', 30) != 30 or 'hour' in sentence.lower() or 'minute' in sentence.lower():
            duration_min = details.get('duration_min', 30)
            end_dt = start_dt + timedelta(minutes=duration_min)
        
        # Make datetime timezone-aware if not already
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=tz.utc)
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=tz.utc)
        
        # Update details with resolved times
        details['start'] = start_dt
        details['end'] = end_dt
    
    # Validate start and end times
    if details.get('start') is None or details.get('end') is None:
        return render_template('message.html',
            title="Error",
            icon="❌",
            message="Could not determine meeting time",
            message_type="error")
    
    return _execute_create_meeting(details, service, drive_file_id=drive_file_id, drive_file_name=drive_file_name, drive_file_url=drive_file_url)


def _execute_create_meeting(details, service, drive_file_id=None, drive_file_name=None, drive_file_url=None):
    """Execute the actual meeting creation."""
    from modules.chat_logger import add_chat_message
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
        
        # Add to chat history
        add_chat_message(
            user_message="",
            bot_response=bot_response,
            message_type="success"
        )
        
        return render_template('meeting_details.html',
            title="Meeting Created",
            icon="✅",
            message=f"Meeting '{event_summary}' has been created successfully!",
            show_details=True,
            event_json=created_event,
            summary=event_summary,
            start=formatted_start,
            end=formatted_end,
            location=event_location,
            description=event_description,
            attachments=event_attachments,
            attendees=", ".join([a.get('email', '') for a in event_attendees]) if event_attendees else "",
            hangout_link=hangout_link,
            html_link=html_link,
            message_type="success")
        
    except Exception as e:
        return render_template('message.html',
            title="Creation Failed",
            icon="❌",
            message=str(e),
            message_type="error")
