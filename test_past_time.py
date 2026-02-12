#!/usr/bin/env python
"""Test script for past time handling."""

from datetime import datetime, timezone, timedelta
from modules.date_utils import extract_date
from modules.time_utils import extract_time

# Simulate the current time being around 4:45 PM
now = datetime.now(timezone(timedelta(hours=5, minutes=30)))
print(f"Current time (IST): {now}")
print(f"Current time: {now.strftime('%A, %B %d at %I:%M %p')}")
print()

# Test with a time that's already passed
sentence = "create a meeting with rahul at 4:14pm to discuss the investment for the new business"

print(f"Testing: '{sentence}'")
print("="*60)

extracted_date, is_past_date = extract_date(sentence, base_dt=now)
print(f"extracted_date: {extracted_date}")
print(f"is_past_date: {is_past_date}")

extracted_time = extract_time(sentence)
print(f"extracted_time: {extracted_time}")

if extracted_date is not None and extracted_time is not None:
    # Create datetime for the requested meeting
    requested_dt = extracted_date.replace(hour=extracted_time.hour, minute=extracted_time.minute, second=0, microsecond=0)
    print(f"requested_dt: {requested_dt}")
    print(f"now: {now}")
    print(f"requested_dt <= now: {requested_dt <= now}")
    
    if requested_dt <= now:
        is_past = True
        print("TIME IS IN THE PAST - should return error")
    else:
        is_past = False
        print("Time is in the future - OK")
else:
    print("Could not extract date or time")

print()

# Test with a future time
sentence2 = "create a meeting at 6pm tomorrow"
print(f"Testing: '{sentence2}'")
print("="*60)

extracted_date2, is_past_date2 = extract_date(sentence2, base_dt=now)
extracted_time2 = extract_time(sentence2)
print(f"extracted_date: {extracted_date2}")
print(f"extracted_time: {extracted_time2}")

if extracted_date2 is not None and extracted_time2 is not None:
    requested_dt2 = extracted_date2.replace(hour=extracted_time2.hour, minute=extracted_time2.minute, second=0, microsecond=0)
    print(f"requested_dt: {requested_dt2}")
    print(f"now: {now}")
    print(f"requested_dt <= now: {requested_dt2 <= now}")
