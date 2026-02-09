"""
Test script to create a meeting with Rajit Sir at 4 PM on 6th for 42 minutes
using Google Meet link: https://meet.google.com/cxq-mubp-wxx
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta, timezone
from services.calendar import get_calendar_service, load_email_book, create_calendar_event
from modules.meeting_extractor import extract_meeting_details
from modules.link_utils import extract_meeting_link
from modules.date_utils import extract_date
from routes.utils import build_event_resource


def test_create_meeting():
    """Test creating a meeting with Rajit Sir."""
    
    # The sentence to process
    sentence = "fix a meeting with rajit sir at 4 pm on 6th for 42 min - use https://meet.google.com/cxq-mubp-wxx"
    
    print("="*60)
    print("TESTING: Create meeting with Rajit Sir")
    print("="*60)
    print(f"Input sentence: {sentence}")
    print()
    
    # Get calendar service
    service = get_calendar_service()
    if not service:
        print("ERROR: Not authenticated with Google Calendar")
        return
    
    # Load email book
    email_book = load_email_book()
    print(f"Email book loaded: {len(email_book)} entries")
    
    # Test date extraction
    print(f"\nTesting date extraction...")
    extracted_date, is_past = extract_date(sentence)
    if extracted_date:
        print(f"  - Extracted date: {extracted_date}")
        print(f"  - Is past: {is_past}")
    else:
        print("  - No date extracted")
    
    # Extract meeting details
    details = extract_meeting_details(sentence, email_book)
    print(f"\nExtracted details:")
    print(f"  - Action: {details.get('action')}")
    print(f"  - Attendee names: {details.get('attendee_names', [])}")
    print(f"  - Start: {details.get('start')}")
    print(f"  - End: {details.get('end')}")
    print(f"  - Duration: {details.get('duration_min')} min")
    
    # Extract meeting link
    meet_link, is_auto = extract_meeting_link(sentence)
    print(f"  - Meeting link: {meet_link}")
    print(f"  - Is auto-generated: {is_auto}")
    
    if details.get('error'):
        print(f"\nERROR: {details.get('error_message', details.get('error'))}")
        return
    
    if not details.get('start') or not details.get('end'):
        print("\nERROR: Could not determine meeting time!")
        return
    
    # Build event resource
    event_resource = build_event_resource(details, meet_link)
    
    print(f"\nEvent resource to be sent:")
    print(f"  - Summary: {event_resource.get('summary')}")
    print(f"  - Start: {event_resource.get('start')}")
    print(f"  - End: {event_resource.get('end')}")
    print(f"  - Location: {event_resource.get('location')}")
    print(f"  - Description: {event_resource.get('description')}")
    print(f"  - Attendees: {event_resource.get('attendees', [])}")
    
    # Create the event
    print(f"\nCreating event...")
    result = create_calendar_event(service, event_resource)
    
    if result:
        print("\n" + "="*60)
        print("MEETING CREATED SUCCESSFULLY!")
        print("="*60)
        
        print(f"Summary:      {result.get('summary')}")
        print(f"Start:       {result.get('start', {}).get('dateTime')}")
        print(f"End:         {result.get('end', {}).get('dateTime')}")
        print(f"Location:    {result.get('location')}")
        print(f"Description: {result.get('description')}")
        print(f"Attendees:   {[a.get('email', '') for a in result.get('attendees', [])]}")
        print(f"Google Meet: {result.get('hangoutLink', 'N/A')}")
        print(f"HTML Link:   {result.get('htmlLink', 'N/A')}")
        print("="*60)
    else:
        print("ERROR: Failed to create event")


if __name__ == "__main__":
    test_create_meeting()
