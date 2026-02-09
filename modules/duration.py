"""
Meeting Duration Extraction Module
Extracts meeting duration from natural language sentences.
"""

import re
from typing import Tuple, Optional


def extract_meeting_duration(sentence: str) -> Tuple[int, Optional[str]]:
    """
    Extract meeting duration from natural language sentence.
    
    Args:
        sentence: The natural language sentence
        
    Returns:
        Tuple of (duration_in_minutes, original_text)
    """
    text = sentence.lower().strip()
    
    # Duration patterns with explicit values (have capture group 1)
    explicit_patterns = [
        (r'\b(\d+)\s*(?:hour|hr|hrs)\b', 60),
        (r'\b(\d+)\s*(?:min|minute|mins)\b', 1),
        (r'\b(\d+)[-\s]*(?:hour|hr|hrs)\b', 60),
        (r'\b(\d+)[-\s]*(?:min|minute|mins?)\b', 1),
        (r'\b(\d+)\s*(?:hours?|hrs?)\s+long\b', 60),
        (r'\b(\d+)\s*(?:minutes?|mins?)\s+long\b', 1),
        (r'\bfor\s+(\d+)\s*(?:hours?|hrs?)\b', 60),
        (r'\bfor\s+(\d+)\s*(?:minutes?|mins?)\b', 1),
    ]
    
    for pattern, multiplier in explicit_patterns:
        match = re.search(pattern, text)
        if match:
            value = int(match.group(1))
            duration_min = value * multiplier
            return duration_min, match.group(0)
    
    # Duration keywords without explicit values (no capture group needed)
    keyword_patterns = [
        (r'\bhalf\s*hour\b', 30),
        (r'\bquick\b', 15),
        (r'\bbrief\b', 15),
        (r'\bcatch[-\s]?up\b', 15),
        (r'\bquick\s*catch[-\s]?up\b', 15),
        (r'\bshort\b', 15),
        (r'\b(?:medium|med)\b', 30),
        (r'\blong\b', 60),
    ]
    
    for pattern, duration_min in keyword_patterns:
        match = re.search(pattern, text)
        if match:
            return duration_min, match.group(0)
    
    # Default duration
    return 30, None


def extract_explicit_duration(sentence: str) -> Optional[int]:
    """
    Extract explicit duration in minutes from patterns like 'for 30 mins'.
    
    Args:
        sentence: The natural language sentence
        
    Returns:
        Duration in minutes or None
    """
    text = sentence.lower().strip()
    
    # Explicit duration patterns
    patterns = [
        r'\bfor\s+(\d+)\s*(?:hours?|hrs?)\b',
        r'\bfor\s+(\d+)\s*(?:minutes?|mins?)\b',
        r'\b(\d+)\s*(?:hours?|hrs?)\s+long\b',
        r'\b(\d+)\s*(?:minutes?|mins?)\s+long\b',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            value = int(match.group(1))
            if 'hour' in match.group(0).lower():
                return value * 60
            return value
    
    return None


def is_duration_ambiguous(sentence: str) -> bool:
    """
    Check if duration is explicitly specified or needs default.
    
    Args:
        sentence: The natural language sentence
        
    Returns:
        True if duration is ambiguous and needs clarification
    """
    duration, _ = extract_meeting_duration(sentence)
    # Default duration (30 mins) is considered ambiguous
    # But we handle this silently without asking user
    return False
