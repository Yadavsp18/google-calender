"""
Chat Routes
Handles chat history storage and retrieval API routes.
"""

from flask import Blueprint, request, jsonify
import os
import json
from datetime import datetime, timezone


# Token file path for checking authentication
TOKEN_FILE = os.path.join(os.path.dirname(__file__), '..', 'config', 'token.json')

CHATS_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'chats.json')

chats_bp = Blueprint('chats', __name__)


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


def load_chats():
    """Load chats from JSON file."""
    if not os.path.exists(CHATS_FILE):
        return {"chats": {}}
    try:
        with open(CHATS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"chats": {}}


def save_chats(data):
    """Save chats to JSON file."""
    os.makedirs(os.path.dirname(CHATS_FILE), exist_ok=True)
    with open(CHATS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


@chats_bp.route('/api/chats', methods=['GET'])
def api_get_chats():
    """Get all chat dates."""
    if not is_authenticated():
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = load_chats()
    chat_dates = list(data.get("chats", {}).keys())
    return jsonify({"success": True, "dates": chat_dates})


@chats_bp.route('/api/chats/<date>', methods=['GET'])
def api_get_chat_for_date(date):
    """Get chat history for a specific date."""
    if not is_authenticated():
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = load_chats()
    chats = data.get("chats", {})
    chat_history = chats.get(date, [])
    return jsonify({"success": True, "date": date, "chats": chat_history})


@chats_bp.route('/api/chats', methods=['POST'])
def api_save_chat():
    """Save a chat message to history."""
    if not is_authenticated():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400
        
        date = data.get('date')
        user_message = data.get('userMessage')
        bot_message = data.get('botMessage')
        message_type = data.get('messageType', 'info')
        file_attachment = data.get('fileAttachment', '')
        update_last = data.get('updateLast', False)
        
        if not date or not user_message:
            return jsonify({"success": False, "error": "Missing required fields"}), 400
        
        # Load existing chats
        chat_data = load_chats()
        chats = chat_data.get("chats", {})
        
        # Initialize date if not exists
        if date not in chats:
            chats[date] = []
        
        # Check if we should update the last entry instead of appending
        if update_last and len(chats[date]) > 0:
            # Update the last entry
            chats[date][-1]['botMessage'] = bot_message
            chats[date][-1]['messageType'] = message_type
            chats[date][-1]['timestamp'] = datetime.now(timezone.utc).isoformat()
        else:
            # Add new chat entry
            chat_entry = {
                "userMessage": user_message,
                "botMessage": bot_message,
                "messageType": message_type,
                "fileAttachment": file_attachment,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            chats[date].append(chat_entry)
        
        # Save to file
        chat_data["chats"] = chats
        save_chats(chat_data)
        
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error saving chat: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@chats_bp.route('/api/chats', methods=['DELETE'])
def api_clear_chats():
    """Clear all chat history."""
    if not is_authenticated():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        save_chats({"chats": {}})
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error clearing chats: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
