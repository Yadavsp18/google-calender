"""
Clarification Handlers
Handles clarification requests for ambiguous or invalid inputs.
"""

from flask import render_template, request
from datetime import datetime, timezone, timedelta

from modules.date_utils import extract_date
from modules.time_utils import handle_time_clarification_logic, check_time_range_clarification_needed


def handle_date_clarification(original_sentence: str, error_message: str = None, drive_file_id=None, drive_file_name=None, drive_file_url=None):
    now = datetime.now(timezone(timedelta(hours=5, minutes=30)))
    today_formatted = now.strftime("%A, %B %d, %Y")

    if not error_message:
        error_message = "The date you specified is in the past. Please enter a valid future date."

    return render_template(
        'date_clarify_standalone.html',
        title="Invalid Date",
        icon="📅",
        error_message=error_message,
        today=today_formatted,
        original_sentence=original_sentence,
        drive_file_id=drive_file_id or '',
        drive_file_name=drive_file_name or '',
        drive_file_url=drive_file_url or '',
        message_type="warning"
    )


def handle_time_clarification(original_sentence: str, extracted_time: str = None, error_message: str = None, drive_file_id=None, drive_file_name=None, drive_file_url=None):
    now = datetime.now(timezone(timedelta(hours=5, minutes=30)))
    current_time = now.strftime("%I:%M %p")

    if not error_message:
        if extracted_time:
            error_message = f"The time '{extracted_time}' is ambiguous. Please specify AM or PM."
        else:
            error_message = "The time you specified is unclear. Please enter a valid time."

    return render_template(
        'time_clarify_standalone.html',
        title="Clarify Time",
        icon="⏰",
        error_message=error_message,
        current_time=current_time,
        original_sentence=original_sentence,
        extracted_time=extracted_time or "",
        drive_file_id=drive_file_id or '',
        drive_file_name=drive_file_name or '',
        drive_file_url=drive_file_url or '',
        message_type="info"
    )


def handle_time_clarification_wrapper(sentence, now=None, drive_file_id=None, drive_file_name=None, drive_file_url=None):
    """
    Wrapper that coordinates date and time extraction for clarification.
    Uses centralized extract_date from date_utils and handle_time_clarification_logic from time_utils.
    
    Handles:
    - "default" keyword: defaults to now + 30 minutes
    - No date/time specified: defaults to now + 30 minutes
    - Past dates: auto-corrects to tomorrow at same time
    """
    ist = timezone(timedelta(hours=5, minutes=30))
    if now is None:
        now = datetime.now(ist)
    
    # Check for "default" keyword - if found, default to now + 30 mins
    if 'default' in sentence.lower():
        default_start = now + timedelta(minutes=30)
        default_end = default_start + timedelta(minutes=30)
        return {
            "start_time": default_start,
            "end_time": default_end,
            "needs_clarification": False
        }

    # Extract date first using centralized function
    extracted_date, is_past = extract_date(sentence, base_dt=now)
    
    # Check if a specific date was mentioned in the sentence
    date_mentioned = extracted_date is not None
    
    if extracted_date is not None:
        # Handle past dates: auto-correct to tomorrow
        if is_past and extracted_date < now:
            extracted_date = extracted_date + timedelta(days=1)
        base_date = extracted_date.replace(hour=9, minute=0, second=0, microsecond=0)
    else:
        # No date found - use None so time_utils can detect no time was specified
        base_date = None

    # Use centralized time clarification logic from time_utils
    time_result = handle_time_clarification_logic(sentence, base_date=base_date, now=now)
    
    # If clarification is needed, render the appropriate template with drive file info
    if time_result.get("needs_clarification"):
        # Check if this is a time range clarification
        time_range = time_result.get("time_range")
        if time_range:
            return handle_time_range_clarification(
                sentence,
                time_range=time_range,
                drive_file_id=drive_file_id, drive_file_name=drive_file_name, drive_file_url=drive_file_url
            )
        return handle_time_clarification(
            sentence,
            error_message=time_result["clarification_message"],
            extracted_time=time_result.get("extracted_time"),
            drive_file_id=drive_file_id, drive_file_name=drive_file_name, drive_file_url=drive_file_url
        )
    
    # If no time was found or clarification needed, default to now + 30 mins
    # Also default to now + 30 mins if no date was mentioned (user didn't specify a date)
    if time_result.get("start_time") is None or not date_mentioned:
        # Check if this is the default 9:00 AM time with no date specified
        if not date_mentioned:
            default_start = now + timedelta(minutes=30)
            default_end = default_start + timedelta(minutes=30)
            return {
                "start_time": default_start,
                "end_time": default_end,
                "needs_clarification": False
            }
        # If date was mentioned but no time, default to 9:00 AM on that date
        if time_result.get("start_time") is None:
            default_start = now.replace(hour=9, minute=0, second=0, microsecond=0)
            default_end = default_start + timedelta(minutes=30)
            return {
                "start_time": default_start,
                "end_time": default_end,
                "needs_clarification": False
            }
    
    # Check if the resolved time is in the past
    if time_result.get("start_time") and time_result["start_time"] < now:
        # Auto-correct to tomorrow at same time
        corrected_start = time_result["start_time"] + timedelta(days=1)
        corrected_end = time_result["end_time"] + timedelta(days=1) if time_result.get("end_time") else corrected_start + timedelta(minutes=30)
        return {
            "start_time": corrected_start,
            "end_time": corrected_end,
            "needs_clarification": False
        }
    
    return time_result


def handle_meal_time_clarification(original_sentence: str, error_message: str = None, meals_to_avoid: list = None, drive_file_id=None, drive_file_name=None, drive_file_url=None):
    """
    Handle clarification for meal time avoidance requests.
    """
    if not meals_to_avoid:
        meals_to_avoid = []
    
    if not error_message:
        error_message = "You mentioned avoiding meal times. Please specify a clear meeting time."
    
    # Format meal times for display
    meal_descriptions = {
        'breakfast': 'Breakfast (7:00 AM - 9:00 AM)',
        'lunch': 'Lunch (12:00 PM - 2:00 PM)',
        'dinner': 'Dinner (7:00 PM - 9:00 PM)',
        'brunch': 'Brunch (10:00 AM - 2:00 PM)',
        'snack': 'Snack time (3:00 PM - 4:00 PM)',
    }
    
    formatted_meals = [meal_descriptions.get(m, m) for m in meals_to_avoid]
    
    # Generate before/after options for each meal
    meal_options = []
    meal_time_mapping = {
        'breakfast': {'before': '7:00 AM', 'after': '9:00 AM'},
        'lunch': {'before': '11:30 AM', 'after': '2:00 PM'},
        'dinner': {'before': '6:30 PM', 'after': '9:00 PM'},
        'brunch': {'before': '9:30 AM', 'after': '2:00 PM'},
        'snack': {'before': '2:30 PM', 'after': '4:00 PM'},
    }
    
    for meal in meals_to_avoid:
        if meal in meal_time_mapping:
            times = meal_time_mapping[meal]
            meal_options.append({'label': f"Before {meal.title()} ({times['before']})", 'time': times['before']})
            meal_options.append({'label': f"After {meal.title()} ({times['after']})", 'time': times['after']})
    
    return render_template('meal_time_clarify_standalone.html',
        title="Meal Time Clarification",
        icon="🍽️",
        error_message=error_message,
        meals_to_avoid=formatted_meals,
        meal_options=meal_options,
        original_sentence=original_sentence,
        drive_file_id=drive_file_id or '',
        drive_file_name=drive_file_name or '',
        drive_file_url=drive_file_url or '',
        message_type="info")


def handle_time_range_clarification(original_sentence: str, time_range: str, drive_file_id=None, drive_file_name=None, drive_file_url=None):
    """
    Handle clarification for ambiguous time ranges.
    """
    now = datetime.now(timezone(timedelta(hours=5, minutes=30)))
    current_time = now.strftime("%I:%M %p")
    
    # Parse the time range to get AM/PM options
    range_match = range_match = None
    import re
    range_match = re.match(r'(\d{1,2})\s*-\s*(\d{1,2})\s*(am|pm)', time_range, re.IGNORECASE)
    
    if range_match:
        start_hour = int(range_match.group(1))
        end_hour = int(range_match.group(2))
        ampm = range_match.group(3).upper()
        
        time_options = []
        
        # Generate AM/PM swap options
        for option_ampm in ['AM', 'PM']:
            if option_ampm != ampm:
                time_str = f"{start_hour}:00 {option_ampm} - {end_hour}:00 {option_ampm}"
                time_options.append(time_str)
        
        return render_template('time_range_clarify.html',
            title="Clarify Time Range",
            icon="⏰",
            original_sentence=original_sentence,
            time_range=time_range,
            time_options=time_options,
            current_time=current_time,
            drive_file_id=drive_file_id or '',
            drive_file_name=drive_file_name or '',
            drive_file_url=drive_file_url or '',
            message_type="info")
    
    # Fallback to regular time clarification
    return handle_time_clarification(original_sentence, time_range, drive_file_id=drive_file_id, drive_file_name=drive_file_name, drive_file_url=drive_file_url)
