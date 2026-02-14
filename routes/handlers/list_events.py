"""
List Events Handler
Handles listing/viewing calendar events.
"""

from flask import render_template
from datetime import datetime, timedelta, timezone
import dateutil.parser

from modules.list_events_patterns import (
    extract_list_event_details,
    detect_time_period,
    needs_clarification
)
from services.calendar import get_calendar_service, get_calendar_events


def handle_list_events(sentence, service):
    """
    Handle listing events from natural language input.
    
    Args:
        sentence: The user's input sentence
        service: Google Calendar service instance
        
    Returns:
        HTML template response
    """
    # Extract details about the list request
    details = extract_list_event_details(sentence)
    
    print(f"DEBUG: List events details: {details}")
    
    # Check if clarification is needed
    if details.get('time_period', {}).get('clarification_needed'):
        # Need to ask user for time period clarification
        return render_template('list_clarify_standalone.html',
            title="Clarification Needed",
            icon="🤔",
            message="Please specify the time period for which you'd like to see events.",
            message_type="info")
    
    # Get the time period
    time_period = details.get('time_period', {})
    period_type = time_period.get('period_type', 'all')
    start_date = time_period.get('start_date')
    end_date = time_period.get('end_date')
    
    # Calculate date range based on period type - use UTC for Google Calendar API
    utc = timezone.utc
    now_utc = datetime.now(utc)
    now_ist = now_utc.astimezone(timezone(timedelta(hours=5, minutes=30)))
    
    today_start_utc = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end_utc = now_utc.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    if period_type == 'today':
        time_min = today_start_utc.isoformat()
        time_max = today_end_utc.isoformat()
        period_label = "Today"
    elif period_type == 'tomorrow':
        tomorrow_start = today_start_utc + timedelta(days=1)
        tomorrow_end = today_end_utc + timedelta(days=1)
        time_min = tomorrow_start.isoformat()
        time_max = tomorrow_end.isoformat()
        period_label = "Tomorrow"
    elif period_type == 'day after tomorrow':
        dat_start = today_start_utc + timedelta(days=2)
        dat_end = today_end_utc + timedelta(days=2)
        time_min = dat_start.isoformat()
        time_max = dat_end.isoformat()
        period_label = "Day After Tomorrow"
    elif period_type == 'this_week':
        # Start from current moment (not Monday)
        time_min_dt = now_utc

        # Calculate how many days until Sunday
        days_until_sunday = 6 - now_utc.weekday()

        # End of Sunday (23:59:59)
        week_end = today_start_utc + timedelta(
        days=days_until_sunday,
        hours=23,
        minutes=59,
        seconds=59
    )

        time_min = time_min_dt.isoformat()
        time_max = week_end.isoformat()
        period_label = "Rest of This Week"
    elif period_type == 'next_week':
        # Get start of next week (Monday) in UTC
        days_until_monday = 7 - now_utc.weekday()
        next_week_start = today_start_utc + timedelta(days=days_until_monday)
        next_week_end = next_week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
        time_min = next_week_start.isoformat()
        time_max = next_week_end.isoformat()
        period_label = "Next Week"
    elif period_type == 'range' and start_date and end_date:
        # Parse the date range from the sentence
        try:
            # Check if start_date is a relative keyword like 'today' or 'tomorrow'
            if start_date.lower() in ['today', 'tomorrow']:
                # Handle relative start date
                if start_date.lower() == 'today':
                    range_start = today_start_utc
                else:  # tomorrow
                    range_start = today_start_utc + timedelta(days=1)
                
                # Handle end_date being 'tomorrow' or a numeric day
                if end_date.lower() == 'tomorrow':
                    range_end = today_end_utc + timedelta(days=1)
                    period_label = f"Events from {start_date.capitalize()} to Tomorrow"
                    time_min = range_start.isoformat()
                    time_max = range_end.isoformat()
                    print(f"DEBUG: Relative date range parsed (today to tomorrow): {time_min} to {time_max}")
                else:
                    # Parse end date as numeric day
                    month_map = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                                'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
                                'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
                                'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12}
                    
                    # Find month in sentence
                    month = None
                    sentence_lower = sentence.lower()
                    for mon, mon_num in month_map.items():
                        if mon in sentence_lower:
                            month = mon_num
                            break
                    
                    year = now_utc.year
                    end_day = int(end_date)
                    
                    range_end = datetime(year, month or now_utc.month, end_day, 23, 59, 59, tzinfo=utc)
                    
                    # Handle month transition if end day < today's day and no explicit month
                    if month is None and end_day < now_ist.day:
                        range_end = datetime(year, now_utc.month + 1, end_day, 23, 59, 59, tzinfo=utc)
                    
                    time_min = range_start.isoformat()
                    time_max = range_end.isoformat()
                    period_label = f"Events from {start_date.capitalize()} to {end_day}"
                    print(f"DEBUG: Relative date range parsed: {time_min} to {time_max}")
            else:
                # Original logic for numeric date ranges
                # Try to parse start and end dates
                # Look for month in sentence
                month_map = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
                            'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
                            'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12}
                
                # Find month in sentence
                month = None
                sentence_lower = sentence.lower()
                for mon, mon_num in month_map.items():
                    if mon in sentence_lower:
                        month = mon_num
                        break
                
                year = now_utc.year
                
                start_day = int(start_date)
                end_day = int(end_date)
                
                range_start = datetime(year, month or now_utc.month, start_day, 0, 0, 0, tzinfo=utc)
                range_end = datetime(year, month or now_utc.month, end_day, 23, 59, 59, tzinfo=utc)
                
                # Handle month transition if end day < start day
                if end_day < start_day:
                    range_end = datetime(year, (month or now_utc.month) + 1, end_day, 23, 59, 59, tzinfo=utc)
                
                time_min = range_start.isoformat()
                time_max = range_end.isoformat()
                period_label = f"Events from {start_day} to {end_day}"
                print(f"DEBUG: Date range parsed: {time_min} to {time_max}")
        except Exception as e:
            print(f"ERROR parsing date range: {str(e)}")
            # Fallback to default
            time_min = today_start_utc.isoformat()
            time_max = (today_start_utc + timedelta(days=30)).isoformat()
            period_label = "Events"
    elif period_type == 'date' and start_date:
        # Parse single date
        try:
            month_map = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
                        'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
                        'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12}
            
            # Find month in sentence
            month = None
            sentence_lower = sentence.lower()
            for mon, mon_num in month_map.items():
                if mon in sentence_lower:
                    month = mon_num
                    break
            
            year = now_utc.year
            day = int(start_date)
            
            date_start = datetime(year, month or now_utc.month, day, 0, 0, 0, tzinfo=utc)
            date_end = datetime(year, month or now_utc.month, day, 23, 59, 59, tzinfo=utc)
            
            time_min = date_start.isoformat()
            time_max = date_end.isoformat()
            period_label = f"Events on {month or now_utc.month}/{day}"
            print(f"DEBUG: Single date parsed: {time_min} to {time_max}")
        except Exception as e:
            print(f"ERROR parsing date: {str(e)}")
            time_min = today_start_utc.isoformat()
            time_max = (today_start_utc + timedelta(days=30)).isoformat()
            period_label = "Events"
    elif period_type == 'date':
        # For specific date, use a wider range
        time_min = today_start_utc.isoformat()
        time_max = (today_start_utc + timedelta(days=30)).isoformat()
        period_label = "Events"
    elif period_type == 'range':
        time_min = today_start_utc.isoformat()
        time_max = (today_start_utc + timedelta(days=30)).isoformat()
        period_label = "Events"
    else:
        # Default: show upcoming events for the next 30 days
        time_min = now_utc.isoformat()
        time_max = (now_utc + timedelta(days=30)).isoformat()
        period_label = "Upcoming Events"
    
    print(f"DEBUG: Final date range - time_min: {time_min}, time_max: {time_max}")
    
    print(f"DEBUG: Fetching events from {time_min} to {time_max}")
    
    try:
        # Get events from Google Calendar
        events = get_calendar_events(service, time_min, time_max)
        
        print(f"DEBUG: Number of events returned: {len(events) if events else 0}")
        if events:
            for i, evt in enumerate(events[:3]):  # Print first 3 events
                print(f"DEBUG: Event {i+1}: {evt.get('summary')} - {evt.get('start', {})}")
        
        if not events or len(events) == 0:
            return render_template('message_standalone.html',
                title=f"No Events Found",
                icon="📅",
                message=f"No events found for {period_label}. Would you like to create a new meeting?",
                message_type="info")
        
        # Format events for display
        formatted_events = []
        for event in events:
            start = event.get('start', {})
            end = event.get('end', {})
            
            # Parse start time
            start_dt = None
            if start.get('dateTime'):
                start_dt = dateutil.parser.parse(start['dateTime'])
            elif start.get('date'):
                start_dt = dateutil.parser.parse(start['date'])
            
            # Parse end time
            end_dt = None
            if end.get('dateTime'):
                end_dt = dateutil.parser.parse(end['dateTime'])
            elif end.get('date'):
                end_dt = dateutil.parser.parse(end['date'])
            
            # Format times
            start_str = start_dt.strftime("%A, %B %d at %I:%M %p") if start_dt else "All Day"
            end_str = end_dt.strftime("%I:%M %p") if end_dt else ""
            
            # Get attendees
            attendees = event.get('attendees', [])
            attendee_list = []
            for attendee in attendees:
                if not attendee.get('resource', False):
                    email = attendee.get('email', '')
                    attendee_list.append(email)
            
            formatted_events.append({
                'id': event.get('id'),
                'summary': event.get('summary', 'Untitled Event'),
                'start': start_str,
                'end': end_str,
                'location': event.get('location', ''),
                'attendees': ', '.join(attendee_list) if attendee_list else '',
                'description': event.get('description', ''),
                'hangoutLink': event.get('hangoutLink', ''),
                'htmlLink': event.get('htmlLink', '')
            })
        
        print(f"DEBUG: Formatted events count: {len(formatted_events)}")
        if formatted_events:
            print(f"DEBUG: First formatted event: {formatted_events[0]}")
        
        # Render events template
        return render_template('events_standalone.html',
            events=formatted_events,
            title=f"{period_label}",
            show_back_button=True,
            action="list")
        
    except Exception as e:
        print(f"ERROR fetching events: {str(e)}")
        return render_template('message_standalone.html',
            title="Error",
            icon="❌",
            message=f"Error fetching events: {str(e)}",
            message_type="error")


def handle_clarify_list_events(sentence, service, selected_period):
    """
    Handle clarification response for list events.
    
    Args:
        sentence: The user's response (e.g., "today", "this week")
        service: Google Calendar service instance
        selected_period: The selected time period
        
    Returns:
        HTML template response
    """
    # Create a new sentence with the selected period
    full_sentence = f"list events for {selected_period}"
    return handle_list_events(full_sentence, service)
