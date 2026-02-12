import re

def extract_recurrence(sentence: str):
    """
    Detect recurrence patterns from sentence.
    Returns Google Calendar RRULE list or empty list.
    """

    sentence = sentence.lower()

    # Daily
    if re.search(r'\b(daily|every day|each day)\b', sentence):
        return ["RRULE:FREQ=DAILY"]

    # Weekly
    if re.search(r'\b(weekly|every week)\b', sentence):
        return ["RRULE:FREQ=WEEKLY"]

    # Monthly
    if re.search(r'\b(monthly|every month)\b', sentence):
        return ["RRULE:FREQ=MONTHLY"]

    # Yearly
    if re.search(r'\b(yearly|every year|annually)\b', sentence):
        return ["RRULE:FREQ=YEARLY"]

    # Weekdays
    if re.search(r'\b(every weekday|weekdays)\b', sentence):
        return ["RRULE:FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR"]

    # Custom: every Monday
    match = re.search(r'every (monday|tuesday|wednesday|thursday|friday|saturday|sunday)', sentence)
    if match:
        day_map = {
            "monday": "MO",
            "tuesday": "TU",
            "wednesday": "WE",
            "thursday": "TH",
            "friday": "FR",
            "saturday": "SA",
            "sunday": "SU"
        }
        day = match.group(1)
        return [f"RRULE:FREQ=WEEKLY;BYDAY={day_map[day]}"]

    return []
