"""
Email lookup utilities - single source of truth for finding emails by name.
"""
import json
import os
from config import get_email_path

def find_email_by_name(name, email_book=None):
    """Find email address by name from email book."""
    if not name:
        return None
    
    name = name.lower().strip()
    
    # Load email book if not provided
    if email_book is None:
        email_file = get_email_path()
        if not os.path.exists(email_file):
            return None
        with open(email_file, 'r') as f:
            email_book = json.load(f)
    
    for entry in email_book:
        entry_name = entry.get("name", "").lower()
        entry_words = entry_name.split()
        if name == entry_name or name in entry_words:
            return entry.get("email")
    
    return None
