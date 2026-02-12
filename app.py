"""
Google Calendar Meeting Creator - Flask Application
Main entry point for the web application.

This module orchestrates:
- Route registration
- App configuration

For business logic, see:
- services/calendar.py - Calendar operations
- services/auth.py - Authentication
- routes/auth.py - Auth routes
- routes/meetings.py - Meeting routes

For NLP processing, see:
- modules/datetime_utils.py - Date/time parsing
- modules/meeting_extractor.py - Meeting extraction
"""

from flask import Flask

from routes.auth import auth_bp
from routes.meetings import meetings_bp
from routes.chats import chats_bp
from config import get_credentials_path


# =============================================================================
# App Configuration
# =============================================================================

app = Flask(__name__)
app.secret_key = 'super-secret-fixed-key-78910'


# =============================================================================
# Context Processors - Inject API key into all templates
# =============================================================================

@app.context_processor
def inject_api_key():
    """Make API key available to all templates."""
    import json
    creds_file = get_credentials_path()
    api_key = ''
    try:
        with open(creds_file, 'r') as f:
            creds = json.load(f)
            api_key = creds.get('api_key', '')
    except Exception:
        api_key = ''
    return dict(DEVELOPER_KEY=api_key)


# =============================================================================
# Register Blueprints
# =============================================================================

app.register_blueprint(auth_bp)
app.register_blueprint(meetings_bp, url_prefix='')
app.register_blueprint(chats_bp, url_prefix='')


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
