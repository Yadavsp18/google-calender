"""
Authentication Service
Handles Google OAuth authentication.

This module provides:
- OAuth flow initialization
- Credentials handling
- Token save/clear operations
"""

import os
import json

from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request

from config import (
    get_credentials_path,
    get_token_path
)


# =============================================================================
# Configuration
# =============================================================================

SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/drive.file'
]

CLIENT_SECRETS_FILE = get_credentials_path()
TOKEN_FILE = get_token_path()
REDIRECT_URI = 'http://localhost:8000/oauth/callback/'

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'


# =============================================================================
# Authentication Functions
# =============================================================================

def get_oauth_flow(state=None):
    """
    Create and configure OAuth flow.
    
    Args:
        state: Optional state string for callback verification
    
    Returns:
        Flow: Configured OAuth flow
    """
    if state:
        return Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, scopes=SCOPES, state=state
        )
    else:
        return Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, scopes=SCOPES
        )


def credentials_to_dict(creds):
    """Convert credentials object to dictionary."""
    return {
        'token': creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri,
        'client_id': creds.client_id,
        'client_secret': creds.client_secret,
        'scopes': creds.scopes,
        'expiry': creds.expiry.isoformat() if creds.expiry else None
    }


def save_credentials_to_file(creds):
    """Save credentials to token.json file."""
    with open(TOKEN_FILE, 'w') as f:
        json.dump(credentials_to_dict(creds), f)


def clear_credentials():
    """Clear credentials from session and file."""
    from flask import session
    
    session.pop('credentials', None)
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)


def get_authorization_url():
    """Get OAuth authorization URL."""
    flow = get_oauth_flow()
    flow.redirect_uri = REDIRECT_URI
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    
    return authorization_url, state


def exchange_code_for_credentials(authorization_response):
    """
    Exchange authorization code for credentials.
    
    Args:
        authorization_response: Full OAuth callback URL
    
    Returns:
        Credentials: OAuth credentials
    """
    from flask import session
    
    state = session.get('state', '')
    flow = get_oauth_flow(state=state)
    flow.redirect_uri = REDIRECT_URI
    
    flow.fetch_token(authorization_response=authorization_response)
    
    return flow.credentials
