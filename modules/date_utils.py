"""
Date Extraction Module
Extracts dates from natural language text.
Handles various date formats and relative date expressions.
"""

import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple


def extract_date(text: str, base_dt: datetime = None) -> Tuple[Optional[datetime], bool]:
    if base_dt is None:
        base_dt = datetime.now(timezone(timedelta(hours=5, minutes=30)))

    text_lower = text.lower().strip()
    today = base_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Debug: print what we're trying to extract
    print(f"DEBUG: extract_date input: '{text}' (today={today.date()})")
    
    month_map = {
        "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
        "apr": 4, "april": 4, "may": 5,
        "jun": 6, "june": 6, "jul": 7, "july": 7,
        "aug": 8, "august": 8, "sep": 9, "september": 9,
        "oct": 10, "october": 10, "nov": 11, "november": 11,
        "dec": 12, "december": 12
    }

    # Month names ordered by length (longest first) to avoid partial matches
    month_names = [
        'january', 'february', 'march', 'april', 'june', 'july', 'august',
        'september', 'october', 'november', 'december',
        'jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'
    ]
    month_pattern = '|'.join(month_names)

    weekday_map = {
        "monday": 0, "tuesday": 1, "wednesday": 2,
        "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6
    }

    # ---------- 1. ISO / FORMAL ----------
    iso = re.search(r'\b(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\b', text_lower)
    if iso:
        y, m, d = map(int, iso.groups())
        try:
            dt = datetime(y, m, d, tzinfo=today.tzinfo)
            return dt, dt < today
        except ValueError:
            pass

    # ---------- 2. NUMERIC DATES ----------
    numeric_patterns = [
        r'\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})\b',  # D-M-Y or M-D-Y
        r'\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{2})\b'   # D-M-YY
    ]

    for p in numeric_patterns:
        m = re.search(p, text_lower)
        if m:
            d1, d2, y = m.groups()
            y = int(y) + 2000 if len(y) == 2 else int(y)
            a, b = int(d1), int(d2)

            for day, month in [(a, b), (b, a)]:
                try:
                    dt = datetime(y, month, day, tzinfo=today.tzinfo)
                    return dt, dt < today
                except ValueError:
                    continue

    # ---------- 3. X DAYS AFTER/FROM EXPLICIT DATE ----------
    # Pattern: "5 days after 23rd feb", "3 weeks after 15th march"
    # Also handles: "5 days from 23rd feb", "3 weeks from 15th march"
    # And: "5 days after feb 23rd", "3 weeks from jan 1st" (month before day)
    
    # First try: "X days after Y MONTH" (day before month)
    days_after_date = re.search(rf'(\d+)\s*days?\s*(?:after|from)\s+(\d{{1,2}})(?:st|nd|rd|th)?\s*(?:of\s+)?({month_pattern})', text_lower)
    if days_after_date:
        num_days = int(days_after_date.group(1))
        day = int(days_after_date.group(2))
        month_name = days_after_date.group(3)
        month = month_map.get(month_name.lower())
        if month:
            year = today.year
            target_date = datetime(year, month, day, 0, 0, 0).replace(tzinfo=today.tzinfo)
            # If the date has passed, use next year
            if target_date < today:
                year = year + 1
            dt = datetime(year, month, day, 0, 0, 0).replace(tzinfo=today.tzinfo) + timedelta(days=num_days)
            return dt, False
    
    # Second try: "X days after MONTH Y" (month before day)
    days_after_date_month_first = re.search(rf'(\d+)\s*days?\s*(?:after|from)\s+({month_pattern})\s+(\d{{1,2}})(?:st|nd|rd|th)?', text_lower)
    if days_after_date_month_first:
        num_days = int(days_after_date_month_first.group(1))
        month_name = days_after_date_month_first.group(2)
        day = int(days_after_date_month_first.group(3))
        month = month_map.get(month_name.lower())
        if month:
            year = today.year
            target_date = datetime(year, month, day, 0, 0, 0).replace(tzinfo=today.tzinfo)
            # If the date has passed, use next year
            if target_date < today:
                year = year + 1
            dt = datetime(year, month, day, 0, 0, 0).replace(tzinfo=today.tzinfo) + timedelta(days=num_days)
            return dt, False

    # ---------- 4. DAY + MONTH (+ year) ----------
    # Day first: "9th feb", "9 feb", "23 february", "10 march 2024"
    day_month_pattern = rf'\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({month_pattern})'
    dm = re.search(day_month_pattern, text_lower)
    if dm:
        day = int(dm.group(1))
        mon = dm.group(2)
        month = month_map[mon.lower()]
        print(f"DEBUG: day_month_pattern matched: day={day}, month={month}")
        
        # Try to find year after the month
        after_month = text_lower[dm.end():]
        year_match = re.search(r'^\s*,?\s*(\d{4})', after_month)
        year = int(year_match.group(1)) if year_match else today.year
        
        try:
            dt = datetime(year, month, day, tzinfo=today.tzinfo)
            # If date has passed and no year was specified, use next year
            if dt < today and not year_match:
                dt = dt.replace(year=today.year + 1)
            print(f"DEBUG: extract_date returning: {dt.date()}")
            return dt, dt < today
        except ValueError:
            print(f"DEBUG: day_month_pattern ValueError, trying next pattern")
            pass
    
    # ---------- 5. MONTH + DAY (+ year) ----------
    # Month first: "february 9th", "feb 9", "march 10 2024"
    month_day_pattern = rf'\b({month_pattern})\s+(\d{{1,2}})(?:st|nd|rd|th)?'
    md = re.search(month_day_pattern, text_lower)
    if md:
        mon = md.group(1)
        day = int(md.group(2))
        month = month_map[mon.lower()]
        
        # Try to find year after the day
        after_day = text_lower[md.end():]
        year_match = re.search(r'^\s*,?\s*(\d{4})', after_day)
        year = int(year_match.group(1)) if year_match else today.year
        
        try:
            dt = datetime(year, month, day, tzinfo=today.tzinfo)
            # If date has passed and no year was specified, use next year
            if dt < today and not year_match:
                dt = dt.replace(year=today.year + 1)
            return dt, dt < today
        except ValueError:
            pass

    # ---------- 6. CHAINED RELATIVES ----------
    # Pattern: "3 days from today", "5 days after tomorrow", "3 days after day after tomorrow"
    # Also handles "tomorro" as abbreviation for "tomorrow"
    chained = re.search(
        r'(\d+)\s*days?\s+(?:after|from)\s+(today|tomorro|tomorrow|tmr|tmrw|day\s+after\s+(?:tomorro|tomorrow|tmr|tmrw))\b',
        text_lower
    )

    if chained:
        num_days = int(chained.group(1))
        anchor = chained.group(2)

        if anchor == "today":
            base = today
        elif anchor in ("tomorrow", "tmr", "tmrw"):
            base = today + timedelta(days=1)
        else:
            base = today + timedelta(days=2)

        dt = base + timedelta(days=num_days)
        return dt, False

    # ---------- 7. SIMPLE RELATIVES ----------
    # Pattern: "in 5 days", "after 3 weeks", "in 2 weeks"
    rel = re.search(r'\b(in|after)\s+(\d+)\s*(days?|weeks?)\b', text_lower)
    if rel:
        num = int(rel.group(2))
        unit = rel.group(3)
        delta = timedelta(days=num if 'day' in unit else 7 * num)
        dt = today + delta
        return dt, False
    
    # Pattern: "5 days from now", "3 weeks from now"
    from_now = re.search(r'(\d+)\s*(days?|weeks?)\s+from\s+now\b', text_lower)
    if from_now:
        num = int(from_now.group(1))
        unit = from_now.group(2)
        delta = timedelta(days=num if 'day' in unit else 7 * num)
        dt = today + delta
        return dt, False
    
    # Pattern: "in the next 5 days", "over the next 3 weeks"
    next_pattern = re.search(r'\b(?:in|over)\s+the\s+next\s+(\d+)\s*(days?|weeks?)\b', text_lower)
    if next_pattern:
        num = int(next_pattern.group(1))
        unit = next_pattern.group(2)
        delta = timedelta(days=num if 'day' in unit else 7 * num)
        dt = today + delta
        return dt, False
    
    # Pattern: "5 days later", "3 weeks later"
    later_pattern = re.search(r'(\d+)\s*(days?|weeks?)\s+later\b', text_lower)
    if later_pattern:
        num = int(later_pattern.group(1))
        unit = later_pattern.group(2)
        delta = timedelta(days=num if 'day' in unit else 7 * num)
        dt = today + delta
        return dt, False
    
    # Pattern: "starting in 5 days", "beginning in 3 weeks"
    starting_pattern = re.search(r'\b(?:starting|beginning)\s+in\s+(\d+)\s*(days?|weeks?)\b', text_lower)
    if starting_pattern:
        num = int(starting_pattern.group(1))
        unit = starting_pattern.group(2)
        delta = timedelta(days=num if 'day' in unit else 7 * num)
        dt = today + delta
        return dt, False

    # ---------- 8. WEEKDAYS ----------
    # Also handles "tomorro" as abbreviation for "tomorrow"
    if re.search(r'\bday\s*(?:after|afte|afta)\s*(tomorro|tomorrow|tmr|tmrw)\b', text_lower):
        return today + timedelta(days=2), False

    if re.search(r'\b(tomorro|tomorrow|tmr|tmrw)\b', text_lower):
        return today + timedelta(days=1), False

    if re.search(r'\btoday\b', text_lower):
        return today, False

    if re.search(r'\byesterday\b', text_lower):
        return today - timedelta(days=1), True

    # Weekday names with "next week" support
    has_next_week = bool(re.search(r'\bnext\s+week\b', text_lower))
    
    for name, idx in weekday_map.items():
        weekday_pattern = r'\b(next\s+week\s+)?' + name + r'\b'
        match = re.search(weekday_pattern, text_lower)
        if match:
            days = (idx - today.weekday()) % 7
            if has_next_week:
                # "next week friday" means 7 days after this week's friday
                days = days + 7
            else:
                days = days or 7  # Default to next occurrence (7 days ahead)
            dt = today + timedelta(days=days)
            return dt, False

    # ---------- 9. MONTH-LEVEL ----------
    if re.search(r'\bthis\s+month\b', text_lower):
        return today.replace(day=1), False

    if re.search(r'\bnext\s+month\b', text_lower):
        year = today.year + (1 if today.month == 12 else 0)
        month = 1 if today.month == 12 else today.month + 1
        return datetime(year, month, 1, tzinfo=today.tzinfo), False

    # ---------- 10. BARE ORDINAL DAY ----------
    # Pattern: "on 6th", "6th", "6th of", "on 6th of"
    # IMPORTANT: Only match if followed by month indicators (of, next, this) NOT just space
    # This prevents "23 feb" from being incorrectly matched as just "23"
    bare_day_pattern = r'\b(\d{1,2})(?:st|nd|rd|th)?\b(?:\s+(?:of\s+)?(?:next|this))?'
    bare_day_matches = list(re.finditer(bare_day_pattern, text_lower))
    print(f"DEBUG: bare_day_pattern found {len(bare_day_matches)} matches: {[m.group(0) for m in bare_day_matches]}")
    
    for bare_day_match in bare_day_matches:
        day = int(bare_day_match.group(1))
        post_text = text_lower[bare_day_match.end():]
        
        # Check if this is followed by a month - if so, this pattern should NOT match
        # Let the day_month pattern handle it
        month_indicators = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec',
                           'january', 'february', 'march', 'april', 'june', 'july', 'august', 'september', 'october', 'november', 'december']
        
        # Check if next word is a month
        next_word_match = re.search(r'^\s*([a-zA-Z]+)', post_text)
        if next_word_match:
            next_word = next_word_match.group(1).lower()
            if next_word in month_indicators:
                # This is a date like "23 feb" - let day_month_pattern handle it
                print(f"DEBUG: bare_day_pattern skipping '{bare_day_match.group(0)}' - next word is month '{next_word}'")
                continue
        
        # Check if this looks like a time range or time
        # Pattern: "from X to Y" or "X-Yam" or "X-Y pm" or "X am/pm" or "X:XX"
        time_range_patterns = [
            r'from\s+\d+\s+to\s+\d',  # "from 4 to 5"
            r'\d+\s*[-–]\s*\d+\s*(?:am|pm)',  # "4-5pm" or "4-5 pm"
            r'between\s+\d+\s+(?:and|to|-|–)\s+\d+',  # "between 4 and 5" or "between 4 to 5"
        ]
        
        is_time_range = any(re.search(p, text_lower) for p in time_range_patterns)
        
        # Also check if this number is followed by am/pm (time indicator)
        is_time = bool(re.search(r'^\s*(?:am|pm)\b', post_text))
        
        # Also check if followed by colon and minutes (time format like "4:15pm")
        is_time_with_colon = bool(re.search(r'^\s*:\d+', post_text))
        
        if is_time_range or is_time or is_time_with_colon:
            # This is part of a time or time range, skip it
            print(f"DEBUG: bare_day_pattern skipping '{bare_day_match.group(0)}' - is time or time range (colon: {is_time_with_colon})")
            continue
        
        # This is a valid bare day date
        if 1 <= day <= 31:
            current_day = today.day
            print(f"DEBUG: bare_day_pattern processing day={day}, current_day={current_day}")
            if day < current_day:
                # Assume next month
                if today.month == 12:
                    year = today.year + 1
                    month = 1
                else:
                    year = today.year
                    month = today.month + 1
                try:
                    dt = datetime(year, month, day, tzinfo=today.tzinfo)
                    print(f"DEBUG: bare_day_pattern returning: {dt.date()}")
                    return dt, False
                except ValueError:
                    pass
            elif day > current_day:
                # Day is still coming this month
                try:
                    dt = datetime(today.year, today.month, day, tzinfo=today.tzinfo)
                    print(f"DEBUG: bare_day_pattern returning: {dt.date()}")
                    return dt, False
                except ValueError:
                    pass
            else:
                print(f"DEBUG: bare_day_pattern day == current_day ({day}), returning today")
    
    # ---------- 11. DATEUTIL FALLBACK ----------
    try:
        from dateutil.parser import parse as date_parse
        parsed = date_parse(text, default=today)
        if parsed:
            dt = parsed if parsed.tzinfo else parsed.replace(tzinfo=today.tzinfo)
            if dt.date() != today.date():
                print(f"DEBUG: dateutil fallback returning: {dt.date()}")
                return dt.replace(hour=0, minute=0, second=0, microsecond=0), dt < today
    except:
        pass
    
    # ---------- NO DATE FOUND ----------
    print(f"DEBUG: extract_date returning None")
    return None, False


def is_date_ambiguous(text: str) -> bool:
    """
    Check if the date in text is ambiguous (could mean multiple dates).
    """
    text_lower = text.lower()
    
    # Check for ambiguous patterns
    # e.g., "5/6" could be May 6 or June 5
    numeric_ambiguous = re.search(r'\b(\d{1,2})[-/.](\d{1,2})\b', text_lower)
    if numeric_ambiguous:
        d1, d2 = int(numeric_ambiguous.group(1)), int(numeric_ambiguous.group(2))
        # Both could be valid month/day combinations
        if 1 <= d1 <= 12 and 1 <= d2 <= 12 and d1 != d2:
            return True
    
    return False


def format_past_date_error(dt: datetime, base_dt: datetime = None) -> str:
    """
    Format an error message for a past date.
    """
    if base_dt is None:
        base_dt = datetime.now(timezone(timedelta(hours=5, minutes=30)))
    
    # Format the date
    formatted = dt.strftime("%A, %B %d, %Y")
    
    # Calculate how far in the past
    days_diff = (base_dt - dt).days
    if days_diff == 1:
        diff_text = "1 day ago"
    elif days_diff < 30:
        diff_text = f"{days_diff} days ago"
    elif days_diff < 60:
        diff_text = "1 month ago"
    else:
        diff_text = f"{days_diff // 30} months ago"
    
    return f"The date {formatted} is in the past ({diff_text}). Please enter a future date."
