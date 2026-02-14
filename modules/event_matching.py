"""
Event Matching Module
Handles finding and matching calendar events based on natural language descriptions.
This module was extracted from services/calendar.py to reduce complexity.
"""

import re
from datetime import datetime, timedelta, timezone
from dateutil.parser import parse as date_parse


def find_matching_events(service, sentence, email_book, extracted_date=None, attendee_names=None, attendees=None):
    """
    Find events matching a natural language description.
    
    Matching priority:
    1. Date match (required if provided)
    2. Name/email match in event title or attendees
    
    Args:
        service: Google Calendar service
        sentence: Natural language description
        email_book: Email book for name resolution
        extracted_date: Optional date to filter by
        attendee_names: Optional list of attendee names to match
        attendees: Optional list of attendee emails to match
    
    Returns:
        list: List of matching events
    """
    from modules.meeting_extractor import extract_meeting_details
    from services.calendar import load_teams, resolve_team_members
    
    # Use timezone-aware datetime for Google Calendar API
    now = datetime.now(timezone.utc)
    
    # Determine search range: use extended range if extracted_date is provided and far in future
    time_min = now.isoformat()
    
    if extracted_date:
        # If extracted date is more than 60 days in future, extend search range
        extracted_date_aware = extracted_date
        if extracted_date.tzinfo is None:
            extracted_date_aware = extracted_date.replace(tzinfo=now.tzinfo)
        
        if extracted_date_aware > (now + timedelta(days=60)):
            # Event is more than 60 days away, extend search to cover it
            # Add some buffer (e.g., 2 days after the event)
            time_max = (extracted_date_aware + timedelta(days=2)).isoformat()
        else:
            time_max = (now + timedelta(days=60)).isoformat()
    else:
        time_max = (now + timedelta(days=60)).isoformat()
    
    print(f"DEBUG: Search range: {time_min} to {time_max}")
    
    try:
        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            maxResults=50,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])
    except Exception:
        events = []
    
    # Extract search terms from sentence
    search_terms = []
    team_member_emails = []
    
    # Pattern to extract name(s) after "with" - stops at common prepositions and date/time words
    attendee_pattern = r'with\s+([A-Za-z]+(?:\s+[A-Za-z]+)?(?:\s*[,&]\s*[A-Za-z]+(?:\s+[A-Za-z]+)?)*)'
    attendee_match = re.search(attendee_pattern, sentence, re.IGNORECASE)
    if attendee_match:
        extracted_name = attendee_match.group(1).strip().lower()
        
        # Clean up: remove common trailing words
        trailing_words = ['to', 'at', 'on', 'for', 'next', 'this', 'same', 'with', 'today', 'tomorrow', 'yesterday']
        name_parts = extracted_name.split()
        cleaned_parts = [part for part in name_parts if part.lower() not in trailing_words]
        cleaned_name = ' '.join(cleaned_parts)
        
        if cleaned_name:
            # Split by comma or & to get individual names
            name_parts = re.split(r'\s*[,&]\s*', cleaned_name)
            for name in name_parts:
                name = name.strip()
                if not name or name in ['and', '&', ',']:
                    continue
                
                # Check if it's a team name
                teams_data = load_teams()
                team_emails = resolve_team_members(name, teams_data)
                if team_emails:
                    team_member_emails.extend([e.lower() for e in team_emails])
                    if name not in search_terms:
                        search_terms.append(name)
                elif name not in search_terms:
                    search_terms.append(name)
    
    # Also use the passed attendee_names and attendees
    if attendee_names:
        attendee_names_lower = [name.lower() for name in attendee_names]
        search_terms.extend(attendee_names_lower)
    
    # Handle "[name] delete/cancel [rest]" pattern where name comes before cancel keyword
    # This handles sentences like "john delete on 4th may meeting discuss project details"
    cancel_kw_pattern = r'\b(cancel|delete|remove|drop|scrap|abort)\b'
    cancel_match = re.search(cancel_kw_pattern, sentence, re.IGNORECASE)
    if cancel_match:
        before_cancel = sentence[:cancel_match.start()].strip()
        
        # Words to skip (date/time/common words)
        skip_words = {'meeting', 'meetings', 'event', 'events', 'call', 'calls', 'on', 'at', 'for',
                      'to', 'about', 'regarding', 'discuss', 'discussion', 'project', 'the', 'a', 'an',
                      'this', 'that', 'today', 'tomorrow', 'yesterday', 'morning', 'afternoon',
                      'evening', 'night', 'details', 'detail', 'schedule', 'scheduling',
                      'am', 'pm', '5pm', '5am', '10am', '10pm', '12pm', '12am', 'noon', 'midnight',
                      'with', 'with,'}

        # Split and look backwards from the end (name is usually closer to cancel keyword)
        before_words = before_cancel.split()
        potential_names = []

        for i, word in enumerate(reversed(before_words)):
            word_clean = word.strip().lower()
            # Skip common words
            if word_clean in skip_words:
                continue
            # Skip words that are just numbers/dates
            if word_clean.isdigit() and (i < 2):  # Year like 2024
                continue
            # Skip ordinals like 23rd, 4th
            if re.match(r'^\d+(?:st|nd|rd|th)$', word_clean):
                continue
            # Skip month names
            month_names = {'jan', 'january', 'feb', 'february', 'mar', 'march', 'apr', 'april', 'may',
                          'jun', 'june', 'jul', 'july', 'aug', 'august', 'sep', 'september',
                          'oct', 'october', 'nov', 'november', 'dec', 'december'}
            if word_clean in month_names:
                continue
            
            # This might be a name
            if len(word_clean) >= 2:
                potential_names.append(word_clean)
                break  # Take the first valid word from the end
        
        if potential_names:
            potential_name = potential_names[0]
            # Capitalize first letter for consistency
            potential_name = potential_name.title()
            if potential_name.lower() not in [t.lower() for t in search_terms]:
                search_terms.append(potential_name.lower())
                print(f"DEBUG: Extracted name '{potential_name}' from '[name] delete' pattern")
    
    # Get meeting details for additional name extraction
    details = extract_meeting_details(sentence, email_book)
    meeting_title = details.get('meeting_title', '').lower()
    
    # Extract name from "with X" pattern in title
    title_name_match = re.search(r'with\s+([A-Za-z]+(?:\s+and?\s+[A-Za-z]+)?)', meeting_title, re.IGNORECASE)
    if title_name_match:
        title_name = title_name_match.group(1).strip().lower()
        if title_name not in search_terms:
            search_terms.append(title_name)
    
    matching_events = []
    matched_event_ids = set()
    
    print(f"DEBUG: Searching for events with terms: {search_terms}")
    print(f"DEBUG: Team member emails: {team_member_emails}")
    print(f"DEBUG: Attendee names: {attendee_names}")
    print(f"DEBUG: Extracted date: {extracted_date}")
    
    for event in events:
        event_id = event.get('id')
        event_summary = event.get('summary', '').lower()
        event_description = event.get('description', '').lower()
        event_start_str = event.get('start', {}).get('dateTime', '')
        
        # Check date match (required if date is specified)
        date_match = True
        if extracted_date and event_start_str:
            try:
                event_dt = date_parse(event_start_str)
                # Normalize extracted_date to compare just the date portion
                extracted_date_date = extracted_date.date() if hasattr(extracted_date, 'date') else extracted_date
                if event_dt.date() != extracted_date_date:
                    date_match = False
            except Exception as e:
                print(f"DEBUG: Error comparing dates: {e}")
                date_match = False
        
        # Skip if date doesn't match
        if not date_match:
            continue
        
        is_match = False
        match_reason = ""
        
        # Skip if already matched (deduplication)
        if event_id in matched_event_ids:
            continue
        
        # Priority 1: Check if search term is in "with X" portion of title
        if search_terms:
            for term in search_terms:
                if term and len(term) >= 2:
                    if term in ['with', 'and', 'for', 'the', 'meeting', 'event']:
                        continue
                    
                    # Check "with X" pattern in title
                    if 'with ' in event_summary:
                        with_portion = event_summary.split('with ')[-1]
                        # Clean up trailing words
                        for trailing in [',', ' ', '-', '/']:
                            if trailing in with_portion:
                                with_portion = with_portion.split(trailing)[0]
                        if term in with_portion:
                            is_match = True
                            match_reason = f"name in title 'with {with_portion}'"
                            break
        
        # Priority 2: Check team member emails in event attendees
        if not is_match and team_member_emails:
            event_attendees = [a.get('email', '').lower() for a in event.get('attendees', [])]
            for team_email in team_member_emails:
                for event_email in event_attendees:
                    if team_email in event_email:
                        is_match = True
                        match_reason = "team member email match"
                        break
                if is_match:
                    break
        
        # Priority 3: Check if any attendee name is in event attendees
        if not is_match and attendee_names:
            for name in attendee_names:
                name_lower = name.lower().strip()
                for event_attendee in event.get('attendees', []):
                    attendee_email = event_attendee.get('email', '').lower()
                    attendee_display_name = event_attendee.get('displayName', '').lower()
                    
                    if name_lower in attendee_email or name_lower in attendee_display_name:
                        is_match = True
                        match_reason = f"attendee match: {name}"
                        break
                if is_match:
                    break
        
        # Priority 4: Check if search term matches attendee email
        if not is_match and search_terms:
            event_attendees = [a.get('email', '').lower() for a in event.get('attendees', [])]
            for term in search_terms:
                if term and len(term) >= 3:
                    if term in ['with', 'and', 'for', 'the', 'meeting', 'event']:
                        continue
                    for event_email in event_attendees:
                        term_clean = term.replace(' ', '.')
                        if term_clean in event_email or term in event_email:
                            is_match = True
                            match_reason = f"email match: {term}"
                            break
                    if is_match:
                        break
        
        # Priority 5: Match by date only when name doesn't match but date is specified
        # This handles cases where the event exists but name extraction failed
        if not is_match and extracted_date:
            if event_start_str:
                try:
                    event_dt = date_parse(event_start_str)
                    if event_dt.date() == extracted_date:
                        is_match = True
                        match_reason = f"date match: {extracted_date}"
                        print(f"DEBUG: Matched by date only: {event.get('summary')}")
                except Exception as e:
                    print(f"DEBUG: Error parsing event date: {e}")
        
        if is_match:
            matching_events.append(event)
            matched_event_ids.add(event_id)
            print(f"DEBUG: Matched event: {event.get('summary')} (reason: {match_reason})")
    
    print(f"DEBUG: Total matching events: {len(matching_events)}")
    
    return matching_events
