"""
Meeting Routes
Handles meeting creation, deletion, and viewing routes.

Routes:
- / - Main page (redirects to auth if not authenticated)
- /nlp_create - Create/cancel meeting from natural language
- /events - View upcoming events
- /delete_event/<event_id> - Delete specific event
"""

from flask import Blueprint, request, render_template, session, redirect, jsonify, make_response
import os
import json
from datetime import datetime, timezone

from services.calendar import (
    get_calendar_service,
    delete_calendar_event,
    get_upcoming_events,
    upload_to_drive,
    create_calendar_event_with_attachment
)
from .handlers import (
    handle_create_meeting,
    handle_update_meeting,
    handle_cancel_meeting
)
from modules.action_utils import detect_action


# Token file path for checking authentication
TOKEN_FILE = os.path.join(os.path.dirname(__file__), '..', 'config', 'token.json')


def is_authenticated():
    """Check if user is authenticated with Google Calendar."""
    if not os.path.exists(TOKEN_FILE):
        return False
    
    try:
        with open(TOKEN_FILE, 'r') as f:
            token_data = json.load(f)
        
        # Check if token has expiry
        if 'expiry' in token_data and token_data['expiry']:
            expiry_str = token_data['expiry']
            
            # Parse expiry datetime - handle various formats
            try:
                # Try parsing with timezone
                if expiry_str.endswith('Z'):
                    expiry_str = expiry_str[:-1] + '+00:00'
                
                # Handle different timezone offsets
                if '+' in expiry_str or expiry_str.count('-') > 2:
                    expiry_dt = datetime.fromisoformat(expiry_str)
                else:
                    # No timezone, assume UTC
                    expiry_dt = datetime.fromisoformat(expiry_str).replace(tzinfo=timezone.utc)
                
                # Get current time in UTC
                now_dt = datetime.now(timezone.utc)
                
                # Check if token is expired (add 5 minute buffer)
                if now_dt > expiry_dt:
                    return False
            except (ValueError, TypeError, AttributeError) as e:
                # If we can't parse expiry, assume it's valid but warn
                print(f"Warning: Could not parse token expiry: {e}")
        
        return True
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Error reading token file: {e}")
        return False


meetings_bp = Blueprint('meetings', __name__)




@meetings_bp.route('/')
def index():
    """Main page - show index.html with chat interface."""
    if not is_authenticated():
        return redirect('/auth')
    
    # Check for action messages (cancelled, updated, etc.)
    action_message = session.pop('last_action_message', None)
    cancelled = request.args.get('cancelled', False)
    cancel_failed = request.args.get('cancel_failed', False)
    
    return render_template('index.html', 
                           authenticated=True,
                           action_message=action_message,
                           cancelled=cancelled,
                           cancel_failed=cancel_failed)


@meetings_bp.route('/auth')
def auth_page():
    """Authentication page - show login button."""
    response = make_response(render_template('auth.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@meetings_bp.route('/logout', methods=['POST'])
def logout():
    """Logout and clear credentials."""
    # Import the auth logout function
    from routes.auth import logout as auth_logout
    return auth_logout()


# =============================================================================
# Chat History API Routes
# =============================================================================

@meetings_bp.route('/api/drive/upload', methods=['POST'])
def api_drive_upload():
    """Upload a file to Google Drive."""
    if not is_authenticated():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        file_name = request.form.get('file_name', 'Untitled')
        file_content = request.form.get('file_content', '')
        file_type = request.form.get('file_type', '')
        
        print(f"DEBUG: api_drive_upload called")
        print(f"DEBUG: file_name={file_name}")
        print(f"DEBUG: file_content length={len(file_content) if file_content else 0}")
        print(f"DEBUG: file_type={file_type}")
        
        # Determine mime type
        mime_type = None
        if file_type:
            mime_type = file_type
        else:
            import mimetypes
            mime_type, _ = mimetypes.guess_type(file_name)
        
        print(f"DEBUG: mime_type={mime_type}")
        
        result = upload_to_drive(file_name, file_content, mime_type)
        
        print(f"DEBUG: upload_to_drive result={result}")
        
        if 'error' in result:
            return jsonify({'error': result['error']}), 500
        
        return jsonify({'success': True, 'file': result})
    except Exception as e:
        print(f"DEBUG: api_drive_upload exception: {e}")
        return jsonify({'error': str(e)}), 500


@meetings_bp.route('/api/drive/file-info', methods=['POST'])
def api_drive_file_info():
    """Get info about an existing Google Drive file by ID."""
    if not is_authenticated():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        data = request.get_json() or {}
        file_id = data.get('fileId')
        
        if not file_id:
            return jsonify({'error': 'No file ID provided'}), 400
        
        # Get file metadata from Drive
        from modules.drive_utils import get_drive_service
        service = get_drive_service()
        
        if not service:
            return jsonify({'error': 'Not authenticated with Google Drive'}), 401
        
        # Get file metadata
        file_metadata = service.files().get(
            fileId=file_id,
            fields='id,name,mimeType,webViewLink'
        ).execute()
        
        # Ensure the file is publicly accessible
        try:
            service.permissions().create(
                fileId=file_id,
                body={'type': 'anyone', 'role': 'reader'},
                sendNotificationEmail=False
            ).execute()
        except Exception as perm_error:
            print(f"Warning: Could not set file permissions: {perm_error}")
        
        return jsonify({
            'success': True,
            'file': {
                'id': file_metadata.get('id'),
                'name': file_metadata.get('name'),
                'mimeType': file_metadata.get('mimeType'),
                'webViewLink': file_metadata.get('webViewLink') or f'https://drive.google.com/file/d/{file_id}/view'
            }
        })
    except Exception as e:
        print(f"Error getting Drive file info: {e}")
        return jsonify({'error': str(e)}), 500


@meetings_bp.route('/nlp_create', methods=['POST'])
def nlp_create():   
    """Create or cancel a meeting from natural language input."""
    service = get_calendar_service()
    
    if not service:
        return render_template('message_standalone.html',
            title="Authentication Required",
            icon="🔐",
            message="Please connect your Google Calendar first.",
            message_type="warning"), 401
    sentence = request.form.get('sentence', '').strip()
    
    # Count words
    word_count = len(sentence.split())

    print(f"DEBUG: Word count = {word_count}")

    # If sentence too short, ask for more details
    if word_count <= 6:
        return render_template('message_standalone.html',
            title="More Details Required",
            icon="📝",
            message="Please provide detailed information about the event (date, time, attendees, etc.).",
            message_type="warning")

    
    
    if not sentence:
        return render_template('message_standalone.html',
            title="Missing Input",
            icon="⚠️",
            message="Please describe the meeting.",
            message_type="warning")
    
    # Check for file upload
    file_name = request.form.get('file_name', '')
    file_content = request.form.get('file_content', '')
    file_type = request.form.get('file_type', '')
    
    # Check for pre-selected Google Drive file
    drive_file_id = request.form.get('drive_file_id', '')
    drive_file_name = request.form.get('drive_file_name', '')
    drive_file_url = request.form.get('drive_file_url', '')
    
    # Upload file to Google Drive if present (and no pre-selected file)
    if file_name and file_content and not drive_file_id:
        result = upload_to_drive(file_name, file_content, file_type if file_type else None)
        if 'error' not in result:
            drive_file_id = result.get('id')
            drive_file_name = result.get('name')
            drive_file_url = result.get('webViewLink', '')
            print(f"DEBUG: File uploaded to Drive: {drive_file_name} (ID: {drive_file_id})")
        else:
            print(f"DEBUG: File upload failed: {result.get('error')}")
    
    is_create, is_cancel, is_update, is_reschedule = detect_action(sentence)
    
    # Debug output
    print(f"\nDEBUG: Sentence='{sentence}'")
    print(f"DEBUG: is_create={is_create}, is_cancel={is_cancel}, is_update={is_update}, is_reschedule={is_reschedule}")
    print(f"DEBUG: drive_file_id={drive_file_id}, drive_file_name={drive_file_name}, drive_file_url={drive_file_url}")
    
    if is_cancel:
        print("DEBUG: Routing to handle_cancel_meeting")
        return handle_cancel_meeting(sentence, service)
    elif is_reschedule or is_update:
        print("DEBUG: Routing to handle_update_meeting")
        return handle_update_meeting(sentence, service)
    elif is_create:
        print("DEBUG: Routing to handle_create_meeting")
        return handle_create_meeting(sentence, service, drive_file_id=drive_file_id, drive_file_name=drive_file_name, drive_file_url=drive_file_url)
    else:
        # Default to create if no pattern matches
        print("DEBUG: No action detected, defaulting to handle_create_meeting")
        return handle_create_meeting(sentence, service, drive_file_id=drive_file_id, drive_file_name=drive_file_name, drive_file_url=drive_file_url)


@meetings_bp.route('/events')
def events():
    """View upcoming events."""
    from dateutil.parser import parse as date_parse
    
    if not is_authenticated():
        return render_template('auth.html')
    
    events_list = get_upcoming_events()
    
    formatted_events = []
    for event in events_list:
        start = event.get('start', {}).get('dateTime', event.get('start', {}).get('date', 'No date'))
        if start != 'No date':
            try:
                start_dt = date_parse(start)
                start = start_dt.strftime("%A, %B %d, %Y at %I:%M %p")
            except Exception:
                pass
        
        formatted_events.append({
            'id': event.get('id'),
            'summary': event.get('summary', 'Untitled Event'),
            'start': start,
            'description': event.get('description', '')
        })
    
    return render_template('events.html', events=formatted_events)


@meetings_bp.route('/delete_event/<event_id>')
def delete_event(event_id):
    """Delete a specific event by ID."""
    from dateutil.parser import parse as date_parse
    
    print(f"DEBUG: delete_event called with event_id: {event_id}")
    if not is_authenticated():
        print("DEBUG: User not authenticated")
        return jsonify({
            'success': False,
            'error': 'Not authenticated',
            'redirect': '/auth'
        })
    
    service = get_calendar_service()
    if not service:
        return jsonify({
            'success': False,
            'error': 'Not authenticated',
            'redirect': '/auth'
        })
    
    # First, get the event details before deleting
    try:
        event = service.events().get(calendarId='primary', eventId=event_id).execute()
    except Exception as e:
        print(f"DEBUG: Error getting event: {e}")
        return jsonify({
            'success': False,
            'error': 'Could not find the event to delete.'
        })
    
    # Extract event details
    event_summary = event.get('summary', 'Meeting')
    event_start = event.get('start', {}).get('dateTime', event.get('start', {}).get('date', ''))
    event_end = event.get('end', {}).get('dateTime', event.get('end', {}).get('date', ''))
    event_location = event.get('location', '')
    event_attendees = event.get('attendees', [])
    event_description = event.get('description', '')
    
    # Format times for display
    start_formatted = ''
    if event_start:
        try:
            start_dt = date_parse(event_start)
            start_formatted = start_dt.strftime("%A, %B %d at %I:%M %p")
        except Exception:
            start_formatted = event_start
    
    end_formatted = ''
    if event_end:
        try:
            end_dt = date_parse(event_end)
            end_formatted = end_dt.strftime("%I:%M %p")
        except Exception:
            end_formatted = event_end
    
    attendees_list = [a.get('email', '') for a in event_attendees if a.get('email')]
    attendees_str = ', '.join(attendees_list) if attendees_list else ''
    
    # Now delete the event
    print(f"DEBUG: Attempting to delete event: {event_id}")
    result = delete_calendar_event(event_id)
    print(f"DEBUG: Delete result: {result}")
    
    if result['success']:
        # Store message in session for display after redirect
        session['last_action_message'] = {
            'type': 'success',
            'title': 'Meeting Cancelled',
            'icon': '🗑️',
            'message': f"Meeting '{event_summary}' has been cancelled successfully!"
        }
        session['cancelled'] = True
        
        return jsonify({
            'success': True,
            'title': 'Meeting Cancelled',
            'icon': '🗑️',
            'message': f"Meeting '{event_summary}' has been cancelled successfully!",
            'redirect': '/'
        })
    else:
        session['last_action_message'] = {
            'type': 'error',
            'title': 'Cancellation Failed',
            'icon': '❌',
            'message': result.get('error', 'Unknown error')
        }
        session['cancel_failed'] = True
        
        return jsonify({
            'success': False,
            'title': 'Cancellation Failed',
            'icon': '❌',
            'message': result.get('error', 'Unknown error'),
            'redirect': '/'
        })


@meetings_bp.route('/update_event/<event_id>', methods=['GET', 'POST'])
def update_event(event_id):
    """Update a specific event by ID."""
    from datetime import datetime, timezone, timedelta
    from dateutil.parser import parse as date_parse
    
    service = get_calendar_service()
    
    if not service:
        return render_template('message_standalone.html',
            title="Authentication Required",
            icon="🔐",
            message="Please connect your Google Calendar first.",
            message_type="warning"), 401
    
    # Extract update parameters from query string
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    day = request.args.get('day', type=int)
    hour = request.args.get('hour', type=int)
    minute = request.args.get('minute', type=int)
    
    print(f"\n=== DEBUG update_event ===")
    print(f"event_id: {event_id}")
    print(f"update params: year={year}, month={month}, day={day}, hour={hour}, minute={minute}")
    
    # Build new date/time from query parameters
    new_start = None
    new_end = None
    
    if year and month and day:
        # User specified a new date
        from datetime import timezone as tz
        if hour is not None and minute is not None:
            new_start = datetime(year, month, day, hour, minute, tzinfo=tz.utc)
            new_end = new_start + timedelta(minutes=30)
        else:
            # Default to 9 AM if time not specified
            new_start = datetime(year, month, day, 9, 0, tzinfo=tz.utc)
            new_end = new_start + timedelta(minutes=30)
    elif hour is not None and minute is not None:
        # User specified new time - need to get original date from event
        pass
    
    # Get the original event
    try:
        original_event = service.events().get(calendarId='primary', eventId=event_id).execute()
    except Exception as e:
        print(f"Error getting event: {e}")
        return render_template('message_standalone.html',
            title="Event Not Found",
            icon="⚠️",
            message="Could not find the event to update.",
            message_type="error")
    
    # Extract original event details
    original_start_str = original_event.get('start', {}).get('dateTime', original_event.get('start', {}).get('date', ''))
    original_end_str = original_event.get('end', {}).get('dateTime', original_event.get('end', {}).get('date', ''))
    
    original_start = date_parse(original_start_str) if original_start_str else None
    original_end = date_parse(original_end_str) if original_end_str else None
    
    # Preserve original details
    existing_summary = original_event.get('summary', '')
    existing_description = original_event.get('description', '')
    existing_location = original_event.get('location', '')
    existing_attendees = original_event.get('attendees', [])
    
    # Build the update payload
    update_payload = {}
    
    if existing_summary:
        update_payload['summary'] = existing_summary
    if existing_description:
        update_payload['description'] = existing_description
    if existing_location:
        update_payload['location'] = existing_location
    if existing_attendees:
        update_payload['attendees'] = existing_attendees
    
    # Apply date/time changes
    if new_start:
        update_payload['start'] = {'dateTime': new_start.isoformat()}
        update_payload['end'] = {'dateTime': new_end.isoformat()}
    elif hour is not None and minute is not None and original_start:
        # Keep original date, change time
        from datetime import timezone as tz
        new_start = original_start.replace(hour=hour, minute=minute, second=0, microsecond=0, tzinfo=tz.utc)
        
        # Calculate duration
        if original_end:
            duration = (original_end - original_start).total_seconds() / 60
            new_end = new_start + timedelta(minutes=duration)
        else:
            new_end = new_start + timedelta(minutes=30)
        
        update_payload['start'] = {'dateTime': new_start.isoformat()}
        update_payload['end'] = {'dateTime': new_end.isoformat()}
    
    print(f"DEBUG: update_payload = {update_payload}")
    
    # Check if there's anything to update
    if not update_payload or (not update_payload.get('start') and not update_payload.get('end')):
        return render_template('message_standalone.html',
            title="No Update Data",
            icon="⚠️",
            message="No update information found. Please try again.",
            message_type="warning")
    
    from services.calendar import update_calendar_event
    result = update_calendar_event(event_id, update_payload)
    
    if result['success']:
        updated_event = result.get('event', {})
        hangout_link = updated_event.get('hangoutLink', '')
        html_link = updated_event.get('htmlLink', '')
        event_summary = updated_event.get('summary', 'Meeting')
        event_start = updated_event.get('start', {}).get('dateTime', '')
        event_end = updated_event.get('end', {}).get('dateTime', '')
        event_description = updated_event.get('description', '')
        event_location = updated_event.get('location', '')
        event_attendees = updated_event.get('attendees', [])
        event_attachments = updated_event.get('attachments', [])
    
    # Rebuild event with original date preserved
    if new_start_str and new_end_str:
        try:
            from datetime import timezone as tz
            new_start_dt = date_parse(new_start_str)
            new_end_dt = date_parse(new_end_str)
            
            # Make timezone-aware if not already
            if new_start_dt.tzinfo is None:
                new_start_dt = new_start_dt.replace(tzinfo=tz.utc)
            if new_end_dt.tzinfo is None:
                new_end_dt = new_end_dt.replace(tzinfo=tz.utc)
            
            # Find the original date or use user-specified date
            user_specified_date = session.get('user_specified_date', False)
            if user_specified_date:
                # Use the user-specified date (from extracted date in the sentence)
                user_new_date = session.get('update_new_date', {})
                if user_new_date:
                    new_start_dt = new_start_dt.replace(
                        year=user_new_date.get('year', new_start_dt.year),
                        month=user_new_date.get('month', new_start_dt.month),
                        day=user_new_date.get('day', new_start_dt.day)
                    )
                    new_end_dt = new_end_dt.replace(
                        year=user_new_date.get('year', new_end_dt.year),
                        month=user_new_date.get('month', new_end_dt.month),
                        day=user_new_date.get('day', new_end_dt.day)
                    )
                    print(f"DEBUG: Using user-specified date: {new_start_dt.date()}")
            elif original_dates and original_dates[0]:
                # Only use original date if user didn't specify a new date
                original_date = date_parse(original_dates[0])
                new_start_dt = new_start_dt.replace(
                    year=original_date.year,
                    month=original_date.month,
                    day=original_date.day
                )
                new_end_dt = new_end_dt.replace(
                    year=original_date.year,
                    month=original_date.month,
                    day=original_date.day
                )
            
            # Rebuild update_data with correct datetime
            update_data['start'] = new_start_dt
            update_data['end'] = new_end_dt
            
            # Debug print
            print(f"DEBUG: update_data['start'] = {update_data['start']}")
            print(f"DEBUG: update_data['end'] = {update_data['end']}")
            
            # Rebuild the event resource
            from .utils import build_event_resource
            update_data = build_event_resource(update_data, meet_link)
            
            # Debug print
            print(f"DEBUG: Built event start = {update_data.get('start')}")
            print(f"DEBUG: Built event end = {update_data.get('end')}")
        except Exception as e:
            print(f"Error rebuilding event: {e}")
            import traceback
            traceback.print_exc()
    
    try:
        from services.calendar import update_calendar_event
        result = update_calendar_event(event_id, update_data)
        
        session.pop('update_event_data', None)
        session.pop('update_meet_link', None)
        session.pop('update_new_start', None)
        session.pop('update_new_end', None)
        session.pop('update_new_date', None)
        session.pop('original_dates', None)
        session.pop('user_specified_date', None)
        
        if result['success']:
            updated_event = result.get('event', {})
            hangout_link = updated_event.get('hangoutLink', meet_link)
            html_link = updated_event.get('htmlLink', '')
            event_summary = updated_event.get('summary', 'Meeting')
            event_start = updated_event.get('start', {}).get('dateTime', '')
            event_end = updated_event.get('end', {}).get('dateTime', '')
            event_description = updated_event.get('description', '')
            event_location = updated_event.get('location', '')
            event_attendees = updated_event.get('attendees', [])
            event_attachments = updated_event.get('attachments', [])
            
            # Print all details to terminal for verification
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
            from datetime import datetime
            from dateutil.parser import parse as date_parse
            
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
            
            return render_template('meeting_details_standalone.html',
                title="Meeting Updated",
                icon="✅",
                message=f"Meeting '{event_summary}' has been updated successfully!",
                show_details=True,
                event_json=updated_event,
                summary=event_summary,
                start=formatted_start,
                end=formatted_end,
                location=event_location,
                description=event_description,
                attachments=event_attachments,
                attendees=", ".join([a.get('email', '') for a in event_attendees]) if event_attendees else "",
                hangout_link=hangout_link,
                html_link=html_link,
                message_type="success",
                action="update")
        else:
            return render_template('message_standalone.html',
                title="Update Failed",
                icon="❌",
                message=result.get('error', 'Unknown error'),
                message_type="error")
    except Exception as e:
        return render_template('message_standalone.html',
            title="Update Failed",
            icon="❌",
            message=str(e),
            message_type="error")
