"""
Time Extraction Module
Extracts times from natural language text.
Handles various time formats (12-hour, 24-hour) and time expressions.
"""

import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, Dict, Any


def extract_time(text: str, base_dt: datetime = None) -> Optional[datetime]:
    """Extract time from natural language text."""
    if base_dt is None:
        base_dt = datetime.now(timezone(timedelta(hours=5, minutes=30)))
    
    text_lower = text.lower().strip()
    
    # 12-hour format with am/pm (e.g., "10:00 AM", "4:00 PM", "11:30 AM")
    time_match = re.search(r'(?:at\s+)?(\d{1,2})(:(\d{2}))?\s*(am|pm)', text_lower, re.IGNORECASE)
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(3)) if time_match.group(3) else 0
        ampm = time_match.group(4).lower()
        
        if ampm == 'pm' and hour != 12:
            hour += 12
        elif ampm == 'am' and hour == 12:
            hour = 0
        
        return base_dt.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    # Informal time without colon (e.g., "5pm", "6pm", "11am", "3pm")
    informal_time = re.search(r'(?:at\s+)?(\d{1,2})\s*(am|pm)(?!:)', text_lower, re.IGNORECASE)
    if informal_time:
        hour = int(informal_time.group(1))
        ampm = informal_time.group(2).lower()
        
        if ampm == 'pm' and hour != 12:
            hour += 12
        elif ampm == 'am' and hour == 12:
            hour = 0
        
        return base_dt.replace(hour=hour, minute=0, second=0, microsecond=0)
    
    # Time range format like "2-5pm" or "11am-1pm"
    time_range_inline = re.search(r'(\d{1,2})\s*(am|pm)?\s*[-–]\s*(\d{1,2})\s*(am|pm)', text_lower, re.IGNORECASE)
    if time_range_inline:
        # Just return start time for single meeting
        hour = int(time_range_inline.group(1))
        ampm = time_range_inline.group(2)
        
        if ampm:
            ampm = ampm.lower()
            if ampm == 'pm' and hour != 12:
                hour += 12
            elif ampm == 'am' and hour == 12:
                hour += 12
        else:
            # Do NOT infer AM/PM - return None to trigger clarification
            # Only handle_time_clarification_logic() should decide ambiguity
            return None
        
        return base_dt.replace(hour=hour % 24, minute=0, second=0, microsecond=0)
    
    # 24-hour format (e.g., "14:30", "09:00")
    time_24 = re.search(r'(?:at\s+)?(\d{1,2}):(\d{2})(?::\d{2})?(?!\s*(?:am|pm))', text_lower)
    if time_24:
        hour = int(time_24.group(1))
        minute = int(time_24.group(2))
        if 0 <= hour <= 23:
            return base_dt.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    # Time of day defaults
    if re.search(r'\bmorning\b', text_lower):
        return base_dt.replace(hour=9, minute=0, second=0, microsecond=0)
    
    if re.search(r'\bafternoon\b', text_lower):
        return base_dt.replace(hour=14, minute=0, second=0, microsecond=0)
    
    if re.search(r'\bevening\b', text_lower):
        return base_dt.replace(hour=18, minute=0, second=0, microsecond=0)
    
    if re.search(r'\bnight\b', text_lower):
        return base_dt.replace(hour=20, minute=0, second=0, microsecond=0)
    
    if re.search(r'\btonight\b', text_lower):
        return base_dt.replace(hour=18, minute=0, second=0, microsecond=0)
    
    if re.search(r'\b(?:at\s+)?noon\b', text_lower):
        return base_dt.replace(hour=12, minute=0, second=0, microsecond=0)
    
    if re.search(r'\b(?:at\s+)?midnight\b', text_lower):
        return base_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # "Lunch" - default to 1:00 PM
    if re.search(r'\b(?:at\s+)?lunch(?:\s*time)?\b', text_lower):
        return base_dt.replace(hour=13, minute=0, second=0, microsecond=0)
    
    # "Breakfast" - default to 8:00 AM
    if re.search(r'\b(?:at\s+)?breakfast(?:\s*time)?\b', text_lower):
        return base_dt.replace(hour=8, minute=0, second=0, microsecond=0)
    
    # "Dinner" - default to 7:00 PM
    if re.search(r'\b(?:at\s+)?dinner(?:\s*time)?\b', text_lower):
        return base_dt.replace(hour=19, minute=0, second=0, microsecond=0)
    
    # "Brunch" - default to 11:00 AM
    if re.search(r'\b(?:at\s+)?brunch\b', text_lower):
        return base_dt.replace(hour=11, minute=0, second=0, microsecond=0)
    
    # EOD (End of Day)
    if re.search(r'\b(eod|cob)\b', text_lower):
        return base_dt.replace(hour=17, minute=0, second=0, microsecond=0)
    
    # Early morning
    if re.search(r'\bearly\s+morning\b', text_lower):
        return base_dt.replace(hour=6, minute=0, second=0, microsecond=0)
    
    # Late night
    if re.search(r'\blate\s+night\b', text_lower):
        return base_dt.replace(hour=22, minute=0, second=0, microsecond=0)
    
    # "Now" - current time
    if re.search(r'\bnow\b', text_lower):
        return base_dt.replace(second=0, microsecond=0)
    
    return None


def extract_time_range(text: str, base_dt: datetime = None) -> Tuple[Optional[datetime], Optional[datetime]]:
    """Extract start and end times from 'from X to Y' pattern."""
    if base_dt is None:
        base_dt = datetime.now(timezone(timedelta(hours=5, minutes=30)))
    
    text_lower = text.lower().strip()
    
    # Pattern: "from 2:00 PM to 3:00 PM" or "from 4pm to 5pm" or "from 4 to 5pm"
    # Handle the case where both times have am/pm
    from_to_pattern = re.search(r'from\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)\s+to\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)', text_lower, re.IGNORECASE)
    if from_to_pattern:
        start_hour = int(from_to_pattern.group(1))
        start_minute = int(from_to_pattern.group(2)) if from_to_pattern.group(2) else 0
        start_ampm = from_to_pattern.group(3)
        
        end_hour = int(from_to_pattern.group(4))
        end_minute = int(from_to_pattern.group(5)) if from_to_pattern.group(5) else 0
        end_ampm = from_to_pattern.group(6)
        
        # Handle AM/PM for start time
        if start_ampm:
            start_ampm = start_ampm.lower()
            if start_ampm == 'pm' and start_hour != 12:
                start_hour += 12
            elif start_ampm == 'am' and start_hour == 12:
                start_hour = 0
        
        # Handle AM/PM for end time
        if end_ampm:
            end_ampm = end_ampm.lower()
            if end_ampm == 'pm' and end_hour != 12:
                end_hour += 12
            elif end_ampm == 'am' and end_hour == 12:
                end_hour = 0
        
        start_dt = base_dt.replace(hour=start_hour % 24, minute=start_minute, second=0, microsecond=0)
        end_dt = base_dt.replace(hour=end_hour % 24, minute=end_minute, second=0, microsecond=0)
        
        return start_dt, end_dt
    
    # Pattern: "from 4 to 5pm" - only end has am/pm
    # Or "from 4pm to 5" - only start has am/pm
    from_to_pattern2 = re.search(r'from\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s+to\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', text_lower, re.IGNORECASE)
    if from_to_pattern2:
        groups = from_to_pattern2.groups()
        
        # Find which groups are present
        # groups: (start_hour, start_minute, start_ampm, end_hour, end_minute, end_ampm)
        # But optional groups change the indices
        
        # Use a more robust approach: extract all numbers and am/pm separately
        numbers = re.findall(r'(\d{1,2})', text_lower)
        ampm_matches = re.findall(r'\b(am|pm)\b', text_lower)
        
        if len(numbers) >= 2:
            start_hour = int(numbers[0])
            end_hour = int(numbers[1])
            
            start_minute = 0
            end_minute = 0
            
            # Check for minutes
            minute_matches = re.findall(r':(\d{2})', text_lower)
            if len(minute_matches) >= 2:
                start_minute = int(minute_matches[0])
                end_minute = int(minute_matches[1])
            elif len(minute_matches) == 1:
                # Both times share the same minute pattern or only one has minutes
                if 'to' in text_lower:
                    parts = text_lower.split('to')
                    if ':' in parts[0]:
                        start_minute = int(re.search(r':(\d{2})', parts[0]).group(1))
                    if ':' in parts[1]:
                        end_minute = int(re.search(r':(\d{2})', parts[1]).group(1))
            
            # Determine AM/PM
            start_ampm = None
            end_ampm = None
            
            # Check which part has am/pm
            if ampm_matches:
                if len(ampm_matches) == 2:
                    start_ampm = ampm_matches[0]
                    end_ampm = ampm_matches[1]
                elif len(ampm_matches) == 1:
                    # Check if the am/pm is near the start or end
                    start_pos = text_lower.find('am') if 'am' in text_lower else text_lower.find('pm')
                    if start_pos != -1:
                        to_pos = text_lower.find('to')
                        if to_pos != -1:
                            if start_pos < to_pos:
                                start_ampm = ampm_matches[0]
                            else:
                                end_ampm = ampm_matches[0]
            
            # Handle AM/PM for start time
            if start_ampm:
                start_ampm = start_ampm.lower()
                if start_ampm == 'pm' and start_hour != 12:
                    start_hour += 12
                elif start_ampm == 'am' and start_hour == 12:
                    start_hour = 0
            
            # Handle AM/PM for end time
            if end_ampm:
                end_ampm = end_ampm.lower()
                if end_ampm == 'pm' and end_hour != 12:
                    end_hour += 12
                elif end_ampm == 'am' and end_hour == 12:
                    end_hour = 0
            
            # Do NOT infer AM/PM for missing parts - return None to trigger clarification
            # Only handle_time_clarification_logic() should decide ambiguity
            if not start_ampm or not end_ampm:
                return None, None
            
            start_dt = base_dt.replace(hour=start_hour % 24, minute=start_minute, second=0, microsecond=0)
            end_dt = base_dt.replace(hour=end_hour % 24, minute=end_minute, second=0, microsecond=0)
            
            return start_dt, end_dt
    
    # Pattern: "between 9:00 AM and 6:00 PM"
    between_pattern = re.search(r'between\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s+and\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', text_lower, re.IGNORECASE)
    if between_pattern:
        groups = between_pattern.groups()
        
        # Find which groups are present
        numbers = re.findall(r'(\d{1,2})', text_lower)
        ampm_matches = re.findall(r'\b(am|pm)\b', text_lower)
        
        if len(numbers) >= 2:
            start_hour = int(numbers[0])
            end_hour = int(numbers[1])
            
            start_minute = 0
            end_minute = 0
            minute_matches = re.findall(r':(\d{2})', text_lower)
            if len(minute_matches) >= 2:
                start_minute = int(minute_matches[0])
                end_minute = int(minute_matches[1])
            
            # Determine AM/PM
            start_ampm = None
            end_ampm = None
            
            if ampm_matches:
                if len(ampm_matches) == 2:
                    start_ampm = ampm_matches[0]
                    end_ampm = ampm_matches[1]
                elif len(ampm_matches) == 1:
                    between_pos = text_lower.find('between')
                    and_pos = text_lower.find('and')
                    ampm_pos = text_lower.find(ampm_matches[0])
                    if between_pos < ampm_pos < and_pos:
                        start_ampm = ampm_matches[0]
                    elif and_pos < ampm_pos:
                        end_ampm = ampm_matches[0]
            
            if start_ampm:
                start_ampm = start_ampm.lower()
                if start_ampm == 'pm' and start_hour != 12:
                    start_hour += 12
                elif start_ampm == 'am' and start_hour == 12:
                    start_hour = 0
            
            if end_ampm:
                end_ampm = end_ampm.lower()
                if end_ampm == 'pm' and end_hour != 12:
                    end_hour += 12
                elif end_ampm == 'am' and end_hour == 12:
                    end_hour = 0
            
            start_dt = base_dt.replace(hour=start_hour % 24, minute=start_minute, second=0, microsecond=0)
            end_dt = base_dt.replace(hour=end_hour % 24, minute=end_minute, second=0, microsecond=0)
            
            return start_dt, end_dt
    
    return None
    
    # Pattern: "between 9:00 AM and 6:00 PM"
    between_pattern = re.search(r'between\s+(\d{1,2})(:(\d{2}))?\s*(am|pm)?\s+and\s+(\d{1,2})(:(\d{2}))?\s*(am|pm)?', text_lower, re.IGNORECASE)
    if between_pattern:
        start_hour = int(between_pattern.group(1))
        start_minute = int(between_pattern.group(3)) if between_pattern.group(3) else 0
        start_ampm = between_pattern.group(5)
        
        end_hour = int(between_pattern.group(4))
        end_minute = int(between_pattern.group(6)) if between_pattern.group(6) else 0
        end_ampm = between_pattern.group(8)
        
        if start_ampm:
            start_ampm = start_ampm.lower()
            if start_ampm == 'pm' and start_hour != 12:
                start_hour += 12
            elif start_ampm == 'am' and start_hour == 12:
                start_hour = 0
        
        if end_ampm:
            end_ampm = end_ampm.lower()
            if end_ampm == 'pm' and end_hour != 12:
                end_hour += 12
            elif end_ampm == 'am' and end_hour == 12:
                end_hour = 0
        
        start_dt = base_dt.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
        end_dt = base_dt.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
        
        return start_dt, end_dt
    
    return None, None


def format_time_12hr(dt: datetime) -> str:
    """Format datetime to 12-hour string with AM/PM."""
    return dt.strftime("%I:%M %p").lstrip('0')


def format_time_24hr(dt: datetime) -> str:
    """Format datetime to 24-hour string."""
    return dt.strftime("%H:%M")


def _apply_time_match(text, dt, base_dt, allow_past=False, is_end_time=False, skip_past_check=False):
    """Apply explicit time patterns to a date."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=base_dt.tzinfo)
    
    # 12-hour format with am/pm
    time_match = re.search(r'(?:at\s+)?(\d{1,2})(:(\d{2}))?\s*(am|pm)', text, re.IGNORECASE)
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(3)) if time_match.group(3) else 0
        ampm = time_match.group(4).lower()
        
        if ampm == 'pm' and hour != 12:
            hour += 12
        elif ampm == 'am' and hour == 12:
            hour = 0
        
        dt = dt.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    # 24-hour format
    time_24 = re.search(r'(?:at\s+)?(\d{1,2}):(\d{2})(?::\d{2})?(?!\s*(?:am|pm))', text)
    if time_24 and not time_match:
        hour = int(time_24.group(1))
        minute = int(time_24.group(2))
        dt = dt.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    # Time of day defaults
    if not time_match and not time_24:
        if re.search(r'\bmorning\b', text):
            dt = dt.replace(hour=9, minute=0, second=0, microsecond=0)
        elif re.search(r'\bafternoon\b', text):
            dt = dt.replace(hour=14, minute=0, second=0, microsecond=0)
        elif re.search(r'\bevening\b', text):
            dt = dt.replace(hour=18, minute=0, second=0, microsecond=0)
        elif re.search(r'\bnight\b', text):
            dt = dt.replace(hour=20, minute=0, second=0, microsecond=0)
        elif re.search(r'\blunch\b', text):
            dt = dt.replace(hour=12, minute=30, second=0, microsecond=0)
        elif re.search(r'\bnoon\b', text):
            dt = dt.replace(hour=12, minute=0, second=0, microsecond=0)
    
    if re.search(r'\btonight\b', text):
        dt = dt.replace(hour=18, minute=0, second=0, microsecond=0)
    
    is_past_reference = re.search(r'\b(yesterday|today)\b', text)
    
    if not skip_past_check and not is_past_reference and dt <= base_dt:
        dt += timedelta(days=1)
    
    if not allow_past and dt < base_dt:
        return None
    
    return dt


# ==================== TIME CLARIFICATION LOGIC ====================

def handle_time_clarification_logic(sentence: str, base_date: datetime = None, now: datetime = None) -> Dict[str, Any]:
    """
    Core time resolution logic - determines start/end times and whether clarification is needed.
    
    Args:
        sentence: The natural language sentence to parse
        base_date: The base date (from date extraction) to apply times to
        now: Current datetime for comparison
        
    Returns:
        Dict with keys: start_time, end_time, needs_clarification, clarification_message
    """
    ist = timezone(timedelta(hours=5, minutes=30))
    if now is None:
        now = datetime.now(ist)
    
    if base_date is None:
        base_date = now
    
    sentence_lower = sentence.lower().strip()

    # ---------- CLEAN DATE WORDS FOR TIME EXTRACTION ----------
    sentence_for_time = sentence_lower
    date_patterns = [
        r'\btoday\b',
        r'\btomorrow\b',
        r'\btmrw?\b',
        r'\bday\s*after\s*(?:tomorrow|tmrw?)\b',
        r'\b\d+\s*days?\s*after\s*(?:today|tomorrow)\b',
        r'\bafter\s+\d+\s*days?\s*from\s+(?:today|tomorrow|tmrw?|day\s*after\s*(?:tomorrow|tmrw?))\b',
        r'\b\d+\s*days?\s*after\s+\d{1,2}(?:st|nd|rd|th)?\s*(?:of\s+)?(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|may|june|july|august|september|october|november|december)\b',
        r'\bthis\s*month\b',
        r'\bnext\s*month\b',
        r'\b(?:next|coming)\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
        r'\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s*next\s*month\b',
        r'\b\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|may|june|july|august|september|october|november|december)\b',
        r'\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}(?:st|nd|rd|th)?\b',
        # New patterns for "after N days" variations (with and without space)
        r'\b\d+\s*days?\s+from\s+now\b',
        r'\b\d+\s*weeks?\s+from\s+now\b',
        r'\b(?:in|over)\s+the\s+next\s+\d+\s*days?\b',
        r'\b(?:in|over)\s+the\s+next\s+\d+\s*weeks?\b',
        r'\b\d+\s*days?\s+later\b',
        r'\b\d+\s*weeks?\s+later\b',
        r'\b(?:starting|beginning)\s+in\s+\d+\s*days?\b',
        r'\b(?:starting|beginning)\s+in\s+\d+\s*weeks?\b',
    ]
    
    for pattern in date_patterns:
        sentence_for_time = re.sub(pattern, '', sentence_for_time, flags=re.IGNORECASE)
    sentence_for_time = re.sub(r'\s+', ' ', sentence_for_time).strip()

    # ---------- TIME RANGE (with AM/PM for both times) ----------
    range_match = re.search(
        r'\b(?:between\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s*(?:to|-|and)\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b',
        sentence_for_time,
        re.IGNORECASE
    )

    if range_match:
        sh, sm, start_ampm, eh, em, end_ampm = range_match.groups()
        sh, eh = int(sh), int(eh)
        sm, em = int(sm or 0), int(em or 0)
        
        # Check if "between" keyword exists in the sentence
        has_between = bool(re.search(r'\bbetween\b', sentence_lower))
        
        # If "between" exists and AM/PM is missing for either time, ask for clarification
        if has_between and (not start_ampm or not end_ampm):
            return {
                "start_time": None,
                "end_time": None,
                "needs_clarification": True,
                "clarification_message": f"You mentioned a time range {sh}-{eh}. Is this AM or PM?",
                "time_range": f"{sh}-{eh}",
                "extracted_time": f"{sh}-{eh}"
            }
        
        # If "between" doesn't exist, infer missing AM/PM from the specified one
        # "from 5 to 7pm" → infer start as pm
        # "2-5am" → infer end as am
        if not start_ampm and end_ampm:
            start_ampm = end_ampm
        if not end_ampm and start_ampm:
            end_ampm = start_ampm
        
        # If still no AM/PM for either, use current time's AM/PM as last resort
        if not start_ampm:
            start_ampm = now.strftime('%p').lower()
        if not end_ampm:
            end_ampm = now.strftime('%p').lower()
        
        start_ampm = start_ampm.lower()
        end_ampm = end_ampm.lower()

        def to_24h(hour, ampm):
            if ampm == "pm" and hour != 12:
                return hour + 12
            if ampm == "am" and hour == 12:
                return 0
            return hour

        sh_24 = to_24h(sh, start_ampm)
        eh_24 = to_24h(eh, end_ampm)

        # Handle crossing 12 (11-1 pm → 11 → 13)
        if eh_24 <= sh_24:
            eh_24 += 12

        start_dt = base_date.replace(hour=sh_24, minute=sm, second=0, microsecond=0)
        end_dt = base_date.replace(hour=eh_24, minute=em, second=0, microsecond=0)
        
        # If the END time has already passed today, schedule for tomorrow
        if end_dt <= now:
            start_dt = start_dt + timedelta(days=1)
            end_dt = end_dt + timedelta(days=1)

        return {
            "start_time": start_dt,
            "end_time": end_dt,
            "needs_clarification": False,
            "clarification_message": None
        }

    # ---------- SINGLE TIME (with AM/PM required) ----------
    single_time_match = re.search(
        r'\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b',
        sentence_for_time,
        re.IGNORECASE
    )

    if single_time_match:
        hour, minute, ampm = single_time_match.groups()
        hour, minute = int(hour), int(minute or 0)
        ampm = ampm.lower()

        def to_24h(h, ampm):
            if ampm == "pm" and h != 12:
                return h + 12
            if ampm == "am" and h == 12:
                return 0
            return h

        hour_24 = to_24h(hour, ampm)
        start_dt = base_date.replace(hour=hour_24, minute=minute, second=0, microsecond=0)
        
        # If the time has already passed today, schedule for tomorrow
        if start_dt <= now:
            start_dt = start_dt + timedelta(days=1)
        
        end_dt = start_dt + timedelta(minutes=30)

        return {
            "start_time": start_dt,
            "end_time": end_dt,
            "needs_clarification": False,
            "clarification_message": None
        }

    # ---------- TIME WITHOUT AM/PM → ASK FOR CLARIFICATION (only if time is explicitly mentioned) ----------
    # Check if there's an explicit time mention without AM/PM (e.g., "at 3" or "at 3:30")
    # NOT when no time is mentioned at all
    explicit_time_no_ampm = re.search(
        r'\b(?:at\s+)?(\d{1,2})(?::(\d{2}))?\b(?!\s*(?:am|pm))',
        sentence_for_time,
        re.IGNORECASE
    )
    
    # Get all time-related patterns that DO have AM/PM
    has_ampm_time = bool(re.search(r'\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b', sentence_for_time, re.IGNORECASE))
    
    # Check if this is likely a date or other number pattern (avoid false positives)
    # Check for ordinal dates like "9th", "10th"
    likely_not_time = bool(re.search(r'\b(\d{1,2})(?:st|nd|rd|th)\b', sentence_for_time))
    
    # Check for "date month" pattern like "9 feb", "10 march" (number followed by month)
    likely_not_time = likely_not_time or bool(re.search(r'\b\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|may|june|july|august|september|october|november|december)\b', sentence_for_time, re.IGNORECASE))
    
    if explicit_time_no_ampm and not has_ampm_time and not likely_not_time:
        # Check if this looks like a genuine time mention
        time_context_patterns = [
            r'\bat\s+\d',
            r'\bby\s+\d',
            r'\bfrom\s+\d',
            r'\bto\s+\d',
            r'\bmeeting\s+(?:at\s+)?\d',
            r'\bschedule\s+(?:at\s+)?\d',
            r'\bcall\s+(?:at\s+)?\d',
            r'\bdinner\s+(?:at\s+)?\d',
            r'\blunch\s+(?:at\s+)?\d',
            r'\bbreakfast\s+(?:at\s+)?\d',
        ]
        
        is_time_context = any(re.search(pattern, sentence_for_time, re.IGNORECASE) for pattern in time_context_patterns)
        is_isolated = bool(re.search(r'(?:^|\s|\b)(?:at\s+)?(\d{1,2})(?::(\d{2}))?(?:\s|$|\b)', sentence_for_time, re.IGNORECASE))
        
        if is_time_context or is_isolated:
            hour, minute = explicit_time_no_ampm.groups()
            hour = int(hour)
            minute = int(minute or 0)
            
            # Ask for clarification since AM/PM is missing
            extracted_time = f"{hour}:{minute:02d}" if minute else f"{hour}"
            return {
                "start_time": None,
                "end_time": None,
                "needs_clarification": True,
                "clarification_message": f"You mentioned the time {extracted_time}. Is this AM or PM?"
            }

    # ---------- TIME OF DAY (morning, afternoon, evening, night) ----------
    if re.search(r'\bmorning\b', sentence_for_time):
        start_dt = base_date.replace(hour=9, minute=0, second=0, microsecond=0)
        end_dt = start_dt + timedelta(minutes=30)
        return {
            "start_time": start_dt,
            "end_time": end_dt,
            "needs_clarification": False,
            "clarification_message": None
        }
    
    if re.search(r'\bafternoon\b', sentence_for_time):
        start_dt = base_date.replace(hour=14, minute=0, second=0, microsecond=0)
        end_dt = start_dt + timedelta(minutes=30)
        return {
            "start_time": start_dt,
            "end_time": end_dt,
            "needs_clarification": False,
            "clarification_message": None
        }
    
    if re.search(r'\bevening\b', sentence_for_time):
        start_dt = base_date.replace(hour=18, minute=0, second=0, microsecond=0)
        end_dt = start_dt + timedelta(minutes=30)
        return {
            "start_time": start_dt,
            "end_time": end_dt,
            "needs_clarification": False,
            "clarification_message": None
        }
    
    if re.search(r'\bnight\b', sentence_for_time):
        start_dt = base_date.replace(hour=20, minute=0, second=0, microsecond=0)
        end_dt = start_dt + timedelta(minutes=30)
        return {
            "start_time": start_dt,
            "end_time": end_dt,
            "needs_clarification": False,
            "clarification_message": None
        }
    
    if re.search(r'\btonight\b', sentence_for_time):
        start_dt = base_date.replace(hour=18, minute=0, second=0, microsecond=0)
        end_dt = start_dt + timedelta(minutes=30)
        return {
            "start_time": start_dt,
            "end_time": end_dt,
            "needs_clarification": False,
            "clarification_message": None
        }

    # ---------- NO TIME → USE DEFAULT TIME (9:00 AM) ----------
    # For meeting scheduling, use 9:00 AM as default when no time is specified
    # This is more predictable than using the current time
    start_dt = base_date.replace(hour=9, minute=0, second=0, microsecond=0)
    end_dt = start_dt + timedelta(minutes=30)

    return {
        "start_time": start_dt,
        "end_time": end_dt,
        "needs_clarification": False,
        "clarification_message": None
    }


def check_time_range_clarification_needed(sentence: str) -> Tuple[bool, Optional[str]]:
    """
    Check if time range clarification is needed (e.g., "between 3-7pm").
    
    Returns:
        Tuple of (needs_clarification: bool, time_range_str: str or None)
    """
    sentence_lower = sentence.lower()
    
    # Match patterns like "3-5pm", "3 to 5pm", "between 3 and 5pm"
    range_patterns = [
        r'between\s+(\d{1,2})\s*(?:am|pm)?\s*(?:and|to|-)\s*(\d{1,2})\s*(am|pm)',
        r'(\d{1,2})\s*(?:am|pm)?\s*(?:and|to|-)\s*(\d{1,2})\s*(am|pm)',
        r'from\s+(\d{1,2})\s*(?:am|pm)?\s*(?:to|-|until)\s*(\d{1,2})\s*(am|pm)',
    ]
    
    for pattern in range_patterns:
        match = re.search(pattern, sentence_lower)
        if match:
            return True, f"{match.group(1)}-{match.group(2)} {match.group(3)}"
    
    return False, None
