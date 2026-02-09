"""
Chat Logger Module

Stores every chat message to a JSON file and provides functionality
to retrieve chat history organized by date.
"""

import json
import os
from datetime import datetime, date
from typing import List, Dict, Any, Optional

# Chat history file path - organized by date
CHAT_DIR = os.path.join(os.path.dirname(__file__), '..', 'chats')


def ensure_chat_directory():
    """Ensure the chat directory exists."""
    if not os.path.exists(CHAT_DIR):
        os.makedirs(CHAT_DIR)


def get_chat_file_path(chat_date: str = None) -> str:
    """Get the chat file path for a specific date (YYYY-MM-DD format)."""
    if chat_date is None:
        chat_date = datetime.now().strftime('%Y-%m-%d')
    return os.path.join(CHAT_DIR, f'chat_{chat_date}.json')


def load_daily_chat(chat_date: str = None) -> List[Dict[str, Any]]:
    """Load chat history for a specific date."""
    file_path = get_chat_file_path(chat_date)
    if not os.path.exists(file_path):
        return []
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            return data.get("chats", [])
    except (json.JSONDecodeError, IOError):
        return []


def save_daily_chat(chat_date: str, chats: List[Dict[str, Any]]):
    """Save chat history for a specific date."""
    ensure_chat_directory()
    file_path = get_chat_file_path(chat_date)
    with open(file_path, 'w') as f:
        json.dump({"date": chat_date, "chats": chats, "last_updated": datetime.now().isoformat()}, f, indent=2)


def add_chat_message(user_message: str, bot_response: str, message_type: str = "info") -> Dict[str, Any]:
    """
    Add a new chat message pair to today's history.
    
    Args:
        user_message: The user's message
        bot_response: The bot's response
        message_type: Type of message (info, success, warning, error)
    
    Returns:
        The created chat entry
    """
    today = datetime.now().strftime('%Y-%m-%d')
    chats = load_daily_chat(today)
    
    chat_entry = {
        "id": len(chats) + 1,
        "timestamp": datetime.now().isoformat(),
        "user_message": user_message,
        "bot_response": bot_response,
        "message_type": message_type
    }
    
    chats.append(chat_entry)
    save_daily_chat(today, chats)
    
    return chat_entry


def get_chat_dates() -> List[Dict[str, str]]:
    """Get list of all dates that have chat history."""
    ensure_chat_directory()
    dates = []
    
    for filename in os.listdir(CHAT_DIR):
        if filename.startswith('chat_') and filename.endswith('.json'):
            date_str = filename[5:-5]  # Remove 'chat_' prefix and '.json' suffix
            try:
                chat_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                chat_count = len(load_daily_chat(date_str))
                dates.append({
                    "date": date_str,
                    "display_date": chat_date.strftime('%B %d, %Y'),
                    "day_name": chat_date.strftime('%A'),
                    "chat_count": chat_count
                })
            except ValueError:
                continue
    
    # Sort by date descending (most recent first)
    dates.sort(key=lambda x: x['date'], reverse=True)
    return dates


def get_chats_by_date(chat_date: str) -> List[Dict[str, Any]]:
    """Get all chats for a specific date."""
    return load_daily_chat(chat_date)


def get_recent_chats(limit: int = 50) -> List[Dict[str, Any]]:
    """Get the most recent chats from today."""
    today = datetime.now().strftime('%Y-%m-%d')
    chats = load_daily_chat(today)
    return chats[-limit:]


def clear_daily_chat(chat_date: str = None):
    """Clear all chat history for a specific date."""
    today = chat_date or datetime.now().strftime('%Y-%m-%d')
    save_daily_chat(today, [])


def get_chat_stats() -> Dict[str, Any]:
    """Get statistics about all chat history."""
    dates = get_chat_dates()
    total_chats = sum(d['chat_count'] for d in dates)
    
    today = datetime.now().strftime('%Y-%m-%d')
    today_chats = len(load_daily_chat(today))
    
    return {
        "total_dates": len(dates),
        "total_chats": total_chats,
        "today_chats": today_chats,
        "dates": dates[:5]  # First 5 dates
    }
