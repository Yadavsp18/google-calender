"""
Authentication Routes
Handles OAuth authentication routes.

Routes:
- /authorize - Initiate OAuth flow
- /oauth/callback/ - Handle OAuth callback
- /logout - Logout and clear credentials
- /api/auth/token - Get current access token for frontend use
"""

from flask import Blueprint, redirect, request, session, render_template, jsonify, current_app

from services.auth import (
    get_authorization_url,
    exchange_code_for_credentials,
    save_credentials_to_file,
    clear_credentials,
    credentials_to_dict,
    SCOPES,
    TOKEN_FILE
)
import os
import json


auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/authorize')
def authorize():
    """Initiate OAuth flow for Google authentication."""
    authorization_url, state = get_authorization_url()
    session['state'] = state
    return redirect(authorization_url)


@auth_bp.route('/oauth/callback/')
def oauth_callback():
    """Handle OAuth callback from Google."""
    state = session.get('state', request.args.get('state'))
    
    if not state:
        return render_template('message.html', 
            title="Authentication Error",
            icon="❌",
            message="Missing state parameter. Please start the OAuth flow from /authorize",
            message_type="error"), 400
    
    try:
        credentials = exchange_code_for_credentials(request.url)
        # Save credentials to file (not session)
        save_credentials_to_file(credentials)
        print(f"DEBUG: Credentials saved to file: {TOKEN_FILE}")
        return redirect('/')
    except Exception as e:
        return render_template('message.html',
            title="Authentication Failed",
            icon="❌",
            message=str(e),
            message_type="error"), 500


@auth_bp.route('/logout')
def logout():
    """Logout and clear credentials."""
    from flask import session
    
    print("DEBUG: Logout called")
    print(f"DEBUG: Token file exists: {os.path.exists(TOKEN_FILE)}")
    
    # Clear only authentication-related session data (not chat history)
    session.pop('state', None)
    session.pop('update_sentence', None)
    session.pop('update_details', None)
    session.pop('resolved_time', None)
    session.pop('extraction_done', None)
    session.pop('user_specified_date', None)
    session.pop('update_new_date', None)
    session.pop('update_event_data', None)
    session.pop('update_meet_link', None)
    session.pop('update_new_start', None)
    session.pop('update_new_end', None)
    session.pop('original_dates', None)
    
    # Clear token file
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)
        print(f"DEBUG: Removed token file: {TOKEN_FILE}")
    
    # Return a redirect page that auto-navigates to /auth
    from flask import make_response
    response = make_response('<!DOCTYPE html><html><head><title>Logging out...</title><meta http-equiv="refresh" content="0; url=/auth"></head><body><p>Logging out... <a href="/auth">Click here</a> if you are not redirected automatically.</p></body></html>')
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@auth_bp.route('/api/auth/token')
def get_token():
    """Get the current access token for frontend use (Google Drive Picker)."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    
    token_file = TOKEN_FILE
    
    if not os.path.exists(token_file):
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        creds_data = json.load(open(token_file))
        creds = Credentials(
            token=creds_data.get('token'),
            refresh_token=creds_data.get('refresh_token'),
            token_uri=creds_data.get('token_uri'),
            client_id=creds_data.get('client_id'),
            client_secret=creds_data.get('client_secret'),
            scopes=creds_data.get('scopes')
        )
        
        # Refresh the token if needed
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                # Save updated credentials
                with open(token_file, 'w') as f:
                    json.dump(credentials_to_dict(creds), f)
            else:
                return jsonify({'error': 'Credentials expired. Please re-authenticate.'}), 401
        
        return jsonify({
            'access_token': creds.token,
            'valid': creds.valid
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/api/auth/check')
def check_auth():
    """Check if user is authenticated."""
    import os
    token_file = TOKEN_FILE
    
    if os.path.exists(token_file):
        return jsonify({'authenticated': True})
    else:
        return jsonify({'authenticated': False})


@auth_bp.route('/api/calendar/events')
def get_calendar_events():
    """Get calendar events for the authenticated user."""
    from services.calendar import get_calendar_service
    from datetime import datetime, timezone
    import os
    
    token_file = TOKEN_FILE
    
    if not os.path.exists(token_file):
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        service = get_calendar_service()
        if not service:
            return jsonify({'error': 'Failed to get calendar service'}), 500
        
        # Fetch user's email from calendar list
        calendars_result = service.calendarList().list().execute()
        user_email = ''
        for calendar in calendars_result.get('items', []):
            if calendar.get('primary'):
                user_email = calendar.get('id', '')
                break
        
        # If no primary calendar found, try to get from calendar entry
        if not user_email:
            calendar_entry = service.calendars().get(calendarId='primary').execute()
            user_email = calendar_entry.get('id', '')
        
        # Fetch events directly
        now = datetime.now(timezone.utc)
        events_result = service.events().list(
            calendarId='primary',
            timeMin=now.isoformat(),
            maxResults=20,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        # Format events for frontend
        formatted_events = []
        for event in events:
            formatted_events.append({
                'id': event.get('id'),
                'summary': event.get('summary', 'Untitled Event'),
                'start': event.get('start'),
                'end': event.get('end'),
                'location': event.get('location', ''),
                'description': event.get('description', ''),
                'attendees': event.get('attendees', [])
            })
        
        return jsonify({
            'events': formatted_events,
            'count': len(formatted_events),
            'user_email': user_email
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
