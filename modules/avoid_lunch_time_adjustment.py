"""
Meal Time Avoidance Module
Handles meeting requests that avoid meal times (breakfast, lunch, dinner).
"""

import re
from typing import Tuple, Optional, Dict, Any
from datetime import datetime, timezone, timedelta


# Meal time windows (in 24-hour format)
MEAL_TIME_WINDOWS = {
    'breakfast': {'start': (7, 0), 'end': (9, 0)},   # 7:00 AM - 9:00 AM
    'lunch': {'start': (12, 0), 'end': (14, 0)},      # 12:00 PM - 2:00 PM
    'dinner': {'start': (19, 0), 'end': (21, 0)},     # 7:00 PM - 9:00 PM
    'brunch': {'start': (10, 0), 'end': (14, 0)},     # 10:00 AM - 2:00 PM
    'snack': {'start': (15, 0), 'end': (16, 0)},      # 3:00 PM - 4:00 PM
}


# Patterns to detect meal time avoidance requests
MEAL_AVOID_PATTERNS = [
    r'\bavoid\s+(?:the\s+)?(?:breakfast|lunch|dinner|brunch|snack)\s*(?:time)?\b',
    r'\b(no|not|skip)\s+(?:the\s+)?(?:breakfast|lunch|dinner|brunch|snack)\b',
    r'\b(?:during|at)\s+(?:noon|lunchtime|dinnertime|breakfast\s*time)\b',
    r'\boutside\s+(?:of\s+)?(?:breakfast|lunch|dinner)\s*(?:time)?\b',
    r'\b(?:before|after)\s+(?:breakfast|lunch|dinner)\b',
    r'\b(?:not|never)\s+(?:at\s+)?(?:breakfast|lunch|dinner)\b',
    r'\bavoid\s+meal\s*(?:time)?\b',
    r'\bschedule\s+(?:around|outside)\s+(?:the\s+)?meals?\b',
]


def detect_meal_time_avoidance(sentence: str) -> Tuple[bool, list]:
    """
    Detect if the sentence mentions avoiding meal times.
    
    Args:
        sentence: The natural language sentence
        
    Returns:
        Tuple of (needs_avoidance, list of meal types to avoid)
    """
    text = sentence.lower().strip()
    meals_to_avoid = []
    
    for pattern in MEAL_AVOID_PATTERNS:
        if re.search(pattern, text):
            # Check which specific meals are mentioned
            if 'breakfast' in text:
                meals_to_avoid.append('breakfast')
            if 'lunch' in text:
                meals_to_avoid.append('lunch')
            if 'dinner' in text:
                meals_to_avoid.append('dinner')
            if 'brunch' in text:
                meals_to_avoid.append('brunch')
            if 'snack' in text:
                meals_to_avoid.append('snack')
            if 'meal' in text and not meals_to_avoid:
                meals_to_avoid = ['breakfast', 'lunch', 'dinner']
            break
    
    return len(meals_to_avoid) > 0, list(set(meals_to_avoid))


def is_time_in_meal_window(dt: datetime, meal: str) -> bool:
    """
    Check if a given datetime falls within a meal time window.
    
    Args:
        dt: The datetime to check
        meal: The meal type ('breakfast', 'lunch', 'dinner', 'brunch', 'snack')
        
    Returns:
        True if the time is within the meal window
    """
    if meal not in MEAL_TIME_WINDOWS:
        return False
    
    window = MEAL_TIME_WINDOWS[meal]
    current_hour = dt.hour
    current_minute = dt.minute
    start_hour, start_minute = window['start']
    end_hour, end_minute = window['end']
    
    # Convert to minutes since midnight for comparison
    current_total = current_hour * 60 + current_minute
    start_total = start_hour * 60 + start_minute
    end_total = end_hour * 60 + end_minute
    
    return start_total <= current_total < end_total


def adjust_time_for_meal_avoidance(dt: datetime, meals_to_avoid: list) -> datetime:
    """
    Adjust a datetime to avoid specified meal times.
    
    Args:
        dt: The original datetime
        meals_to_avoid: List of meal types to avoid
        
    Returns:
        Adjusted datetime that avoids the meal times
    """
    adjusted_dt = dt
    
    for meal in meals_to_avoid:
        if meal in MEAL_TIME_WINDOWS and is_time_in_meal_window(adjusted_dt, meal):
            window = MEAL_TIME_WINDOWS[meal]
            # Move to the end of the meal window
            end_hour, end_minute = window['end']
            adjusted_dt = adjusted_dt.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
            # Add a small buffer (15 minutes after meal time)
            adjusted_dt = adjusted_dt.replace(minute=adjusted_dt.minute + 15)
    
    return adjusted_dt


def find_available_slot(base_dt: datetime, duration_minutes: int, meals_to_avoid: list, 
                         start_hour: int = 9, end_hour: int = 18) -> Optional[datetime]:
    """
    Find the next available time slot that avoids meal times.
    
    Args:
        base_dt: Starting datetime to search from
        duration_minutes: Meeting duration in minutes
        meals_to_avoid: List of meal types to avoid
        start_hour: Business hours start (default 9 AM)
        end_hour: Business hours end (default 6 PM)
        
    Returns:
        Available datetime or None if no slot found
    """
    current_dt = base_dt.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    
    # If base_dt is earlier than business hours, start from business hours
    if current_dt < base_dt:
        current_dt = base_dt
    
    # Search for the next 7 days
    for _ in range(7):
        # Check each hour in business hours
        for hour in range(start_hour, end_hour):
            slot_dt = current_dt.replace(hour=hour, minute=0, second=0, microsecond=0)
            
            # Check if slot is during a meal time
            during_meal = False
            for meal in meals_to_avoid:
                if is_time_in_meal_window(slot_dt, meal):
                    during_meal = True
                    break
            
            if not during_meal:
                # Check if the meeting would end before business hours
                end_dt = slot_dt.replace(minute=slot_dt.minute + duration_minutes)
                if end_dt.hour <= end_hour or (end_dt.hour == end_hour and end_dt.minute == 0):
                    return slot_dt
            
            # Move to next hour
            current_dt = current_dt.replace(hour=hour + 1)
        
        # Move to next day
        current_dt = (current_dt + timedelta(days=1)).replace(hour=start_hour, minute=0)
    
    return None


def format_meal_time_clarification(meals_to_avoid: list) -> str:
    """
    Format meal times for display in clarification message.
    
    Args:
        meals_to_avoid: List of meal types to avoid
        
    Returns:
        Formatted string of meal times
    """
    meal_descriptions = {
        'breakfast': 'Breakfast (7:00 AM - 9:00 AM)',
        'lunch': 'Lunch (12:00 PM - 2:00 PM)',
        'dinner': 'Dinner (7:00 PM - 9:00 PM)',
        'brunch': 'Brunch (10:00 AM - 2:00 PM)',
        'snack': 'Snack time (3:00 PM - 4:00 PM)',
    }
    
    descriptions = [meal_descriptions.get(m, m) for m in meals_to_avoid]
    return ', '.join(descriptions)


def check_meal_time_clarification(sentence: str) -> Tuple[bool, str, list]:
    """
    Check if meal time clarification is needed.
    
    Args:
        sentence: The user input sentence
        
    Returns:
        Tuple of (needs_clarification, message, meals_to_avoid)
    """
    needs_avoidance, meals_to_avoid = detect_meal_time_avoidance(sentence)
    
    if needs_avoidance:
        meal_list = format_meal_time_clarification(meals_to_avoid)
        message = f"You mentioned avoiding {', '.join(meals_to_avoid)} time. Please specify a clear meeting time."
        return True, message, meals_to_avoid
    
    return False, "", []
