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
        session['credentials'] = credentials_to_dict(credentials)
        save_credentials_to_file(credentials)
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
    clear_credentials()
    return redirect('/')


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
