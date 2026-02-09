"""
Meeting Location/Mode Extraction Module
Extracts meeting location and mode (online/offline) from natural language sentences.
"""

import re
from typing import Tuple, Optional, Dict, Any

from modules.link_utils import extract_meeting_link


# Offline/Physical location patterns
OFFLINE_PATTERNS = [
    # Office locations
    r'\bin\s*boardroom\b',
    r'\bat\s*boardroom\b',
    r'\bboardroom\b',
    r'\bin\s*office\b',
    r'\bat\s*office\b',
    r'\bin\s*the\s*office\b',
    r'\bin\s*cabin\b',
    r'\bin\s*cafeteria\b',
    r'\bin\s*pantry\b',
    r'\bin\s*conference\b',
    r'\bconference\s*room\b',
    r'\bconference\s*room\s*([a-z]+)\b',
    
    # In-person patterns
    r'\bin-person\b',
    r'\bface-to-face\b',
    r'\bf2f\b',
    
    # Coworking spaces
    r'\bwework\b',
    r'\bwe\s*work\b',
    r'\bcoworking\b',
    r'\bshared\s*office\b',
    
    # Business areas
    r'\bmg\s*road\b',
    r'\breception\b',
    r'\breception\s*lounge\b',
    
    # Common physical venues
    r'\bcafe\b',
    r'\bcafeteria\b',
    r'\brestaurant\b',
    r'\bcoffee\s*shop\b',
    r'\bclinic\b',
    r'\bhospital\b',
    r'\bdentist\b',
    r'\blibrary\b',
    r'\bgym\b',
    r'\bfitness\s*center\b',
    r'\bpark\b',
    r'\bhome\b',
    r'\bhouse\b',
    r'\bat\s*home\b',
    r'\bat\s*my\s*place\b',
    r'\bat\s*their\s*place\b',
    r'\bclient\s*location\b',
    r'\bclient\s*office\b',
    r'\bvendor\s*office\b',
    r'\bpartner\s*office\b',
    r'\bproject\s*site\b',
    r'\bworksite\b',
    r'\bconstruction\s*site\b',
    r'\bevent\s*venue\b',
    r'\bconference\s*center\b',
    r'\bmeeting\s*room\b',
    r'\btraining\s*room\b',
    r'\bseminar\s*room\b',
    r'\bwork\s*shop\b',
]


# Online patterns
ONLINE_PATTERNS = [
    # Google Meet
    r'\bgmeet\b',
    r'\bgoogle\s*meet\b',
    r'\bmeet\.google\.com\b',
    r'\bgoogle\s+meet\b',
    
    # Zoom
    r'\bzoom\b',
    r'\bzoom\.com\b',
    r'\bzoom\s*meeting\b',
    r'\bzoom\s*call\b',
    r'\bzoom\s*session\b',
    
    # Microsoft Teams
    r'\bteams\b',
    r'\bmicrosoft\s*teams\b',
    r'\bms\s*teams\b',
    r'\bteams\s*meeting\b',
    
    # Webex
    r'\bwebex\b',
    r'\bcisco\s*webex\b',
    
    # Other video platforms
    r'\bmeetup\b',
    r'\bdiscord\b',
    r'\bslack\s*call\b',
    r'\bskype\b',
    r'\bhangouts\b',
    r'\bgoogle\s*hangouts\b',
    r'\b Facetime\b',
    r'\bFacetime\b',
    
    # Generic online patterns
    r'\bonline\b',
    r'\bvirtual\b',
    r'\bvideo\s*call\b',
    r'\bvideo\s*meeting\b',
    r'\bweb\s*call\b',
    r'\bwebinar\b',
    r'\bweb\s*conference\b',
    r'\bvc\b',
    r'\bvideo\s*conference\b',
    r'\bteleconference\b',
    r'\bphone\s*call\b',
    r'\btelephone\s*meeting\b',
]


def extract_meeting_mode(sentence: str) -> Tuple[str, Optional[str]]:
    """
    Extract meeting mode (online/offline) from natural language sentence.
    
    Args:
        sentence: The natural language sentence
        
    Returns:
        Tuple of (mode, location)
    """
    text = sentence.lower().strip()
    
    # Check for physical/offline patterns first
    for pattern in OFFLINE_PATTERNS:
        if re.search(pattern, text):
            return 'offline', extract_offline_location(text)
    
    # Check for online patterns
    for pattern in ONLINE_PATTERNS:
        if re.search(pattern, text):
            return 'online', 'Online'
    
    # Check for explicit "in person" or "offline"
    if re.search(r'\bin\s+person\b', text) or re.search(r'\boffline\b', text):
        return 'offline', extract_offline_location(text)
    
    # Default to online with Google Meet
    return 'online', 'Online'


def extract_offline_location(sentence: str) -> str:
    """
    Extract specific offline location from sentence.
    
    Args:
        sentence: The natural language sentence
        
    Returns:
        Location string
    """
    text = sentence.lower().strip()
    
    location_patterns = [
        # Office locations
        (r'\bboardroom\b', 'Boardroom'),
        (r'\bconference\s*room\s*([a-z]+)\b', lambda m: f"Conference Room {m.group(1).upper()}"),
        (r'\bconference\s*room\b', 'Conference Room'),
        (r'\bmeeting\s*room\b', 'Meeting Room'),
        (r'\btraining\s*room\b', 'Training Room'),
        (r'\bcabin\b', 'Cabin'),
        (r'\bcafeteria\b', 'Cafeteria'),
        (r'\bpantry\b', 'Pantry'),
        (r'\breception\s*lounge\b', 'Reception Lounge'),
        (r'\breception\b', 'Reception'),
        (r'\bwework\s*mg\s*road\b', 'WeWork MG Road'),
        (r'\bwework\b', 'WeWork'),
        (r'\bcoworking\s*space\b', 'Coworking Space'),
        
        # Healthcare locations
        (r'\bdentist\s*office\b', 'Dentist Office'),
        (r'\bdentist\b', 'Dentist'),
        (r'\bclinic\b', 'Clinic'),
        (r'\bhospital\b', 'Hospital'),
        (r'\bdoctor.*office\b', "Doctor's Office"),
        
        # Fitness locations
        (r'\bgym\b', 'Gym'),
        (r'\bfitness\s*center\b', 'Fitness Center'),
        (r'\byoga\s*studio\b', 'Yoga Studio'),
        (r'\bfitness\s*studio\b', 'Fitness Studio'),
        
        # Food & Beverage
        (r'\bcafe\b', 'Cafe'),
        (r'\bcoffee\s*shop\b', 'Coffee Shop'),
        (r'\brestaurant\b', 'Restaurant'),
        
        # Educational
        (r'\blibrary\b', 'Library'),
        (r'\buniversity\b', 'University'),
        (r'\bcollege\b', 'College'),
        (r'\bschool\b', 'School'),
        
        # Outdoor
        (r'\bpark\b', 'Park'),
        (r'\bgarden\b', 'Garden'),
        
        # Home/Personal
        (r'\bhome\b', 'Home'),
        (r'\bhouse\b', 'House'),
        (r'\bat\s*my\s*place\b', 'My Place'),
        (r'\bat\s*their\s*place\b', 'Their Place'),
        
        # Business
        (r'\bclient\s*location\b', 'Client Location'),
        (r'\bclient\s*office\b', 'Client Office'),
        (r'\bvendor\s*office\b', 'Vendor Office'),
        (r'\bpartner\s*office\b', 'Partner Office'),
        (r'\bproject\s*site\b', 'Project Site'),
        (r'\bworksite\b', 'Worksite'),
        (r'\bevent\s*venue\b', 'Event Venue'),
        (r'\bconference\s*center\b', 'Conference Center'),
        
        # Generic address patterns
        (r'\bat\s+(?:the\s+)?(cafe|restaurant|shop|store|mall|building|floor|street|road|library|gym|park|home|house|office|lab|studio|center|venue|place)\b', 
         lambda m: m.group(1).title()),
        
        # Floor/Level patterns
        (r'\b(\d+)(?:st|nd|rd|th)\s*floor\b', lambda m: f"{m.group(1)}{m.group(0)[-5:]} Floor"),
        (r'\bfloor\s*(\d+)\b', lambda m: f"Floor {m.group(1)}"),
    ]
    
    for pattern, result in location_patterns:
        match = re.search(pattern, text)
        if match:
            if callable(result):
                return result(match)
            return result
    
    return 'TBD'


def extract_online_location(sentence: str) -> Tuple[str, bool]:
    """
    Extract online meeting details from sentence.
    Delegates to link_utils.extract_meeting_link for URL extraction.
    
    Args:
        sentence: The natural language sentence
        
    Returns:
        Tuple of (location_string, use_google_meet)
    """
    link, is_auto = extract_meeting_link(sentence)
    
    if link:
        return link, False
    
    # Check for Google Meet patterns
    text = sentence.lower().strip()
    for pattern in ONLINE_PATTERNS:
        if re.search(pattern, text):
            # Check for "usual" or "regular" Meet link
            if re.search(r'\busual\b', text) or re.search(r'\bregular\b', text):
                return 'Online', False
            return 'Online', True
    
    return 'Online', True


def extract_meeting_location(sentence: str) -> Dict[str, Any]:
    """
    Extract complete location/mode information from sentence.
    
    Args:
        sentence: The natural language sentence
        
    Returns:
        Dictionary with mode, location, use_meet, and link_preference
    """
    mode, location = extract_meeting_mode(sentence)
    
    if mode == 'online':
        online_location, use_meet = extract_online_location(sentence)
        return {
            'mode': mode,
            'location': online_location,
            'use_meet': use_meet,
            'link_preference': 'auto_generate_meet' if use_meet else 'use_provided_link'
        }
    else:
        return {
            'mode': mode,
            'location': location if location else 'TBD',
            'use_meet': False,
            'link_preference': None
        }


def extract_physical_address(sentence: str) -> Dict[str, Any]:
    """
    Extract physical address details from sentence.
    
    Args:
        sentence: The natural language sentence
        
    Returns:
        Dictionary with address components
    """
    text = sentence.lower().strip()
    
    address_info = {
        'street': '',
        'city': '',
        'state': '',
        'country': '',
        'zipcode': '',
        'full_address': ''
    }
    
    # Extract street address
    street_match = re.search(r'\b(\d+[\s\w]+(?:street|st|avenue|ave|road|rd|drive|dr|lane|ln|boulevard|blvd|way|place|pl|court|ct))\b', text)
    if street_match:
        address_info['street'] = street_match.group(1).title()
    
    # Extract city names (common Indian cities)
    cities = [
        r'\b(mumbai|delhi|bangalore|chennai|hyderabad|kolkata|pune|bengaluru|ahmedabad|jaipur|'
        r'new\s*york|los\s*angeles|chicago|houston|phoenix|philadelphia|san\s*antonio|san\s*diego|'
        r'dallas|san\s*jose|austin|jacksonville|san\s*francisco|seattle|denver|boston)\b'
    ]
    for city in cities:
        city_match = re.search(city, text)
        if city_match:
            address_info['city'] = city_match.group(1).title()
            break
    
    # Extract common locations/landmarks
    if not address_info['city']:
        landmark_match = re.search(r'\bat\s+(?:the\s+)?([\w\s]+?)(?:\s*,|\s*on|\s*$|\s*tomorrow|\s*today)', text)
        if landmark_match:
            location = landmark_match.group(1).strip()
            if len(location) > 2 and len(location) < 50:
                address_info['city'] = location.title()
    
    # Build full address
    parts = [p for p in [
        address_info.get('street'),
        address_info.get('city'),
        address_info.get('state'),
        address_info.get('country'),
        address_info.get('zipcode')
    ] if p]
    
    if parts:
        address_info['full_address'] = ', '.join(parts)
    
    return address_info


def is_hybrid_meeting(sentence: str) -> bool:
    """
    Check if the meeting is hybrid (both online and in-person).
    
    Args:
        sentence: The natural language sentence
        
    Returns:
        True if hybrid meeting
    """
    text = sentence.lower().strip()
    
    # Check for explicit hybrid patterns
    hybrid_patterns = [
        r'\bhybrid\b',
        r'\bonline\s+and\s+(?:in-)?person\b',
        r'\b(in-)?person\s+and\s+online\b',
        r'\bvirtual\s+and\s+(in-)?person\b',
        r'\bboth\s+online\s+and\s+(in-)?person\b',
    ]
    
    for pattern in hybrid_patterns:
        if re.search(pattern, text):
            return True
    
    return False


def format_location_for_print(location_info: Dict[str, Any]) -> str:
    """
    Format location information for printing/display.
    
    Args:
        location_info: Dictionary from extract_meeting_location()
        
    Returns:
        Formatted string for display
    """
    mode = location_info.get('mode', 'unknown')
    location = location_info.get('location', '')
    use_meet = location_info.get('use_meet', False)
    link_preference = location_info.get('link_preference', None)
    
    if mode == 'online':
        if use_meet:
            return f"Online (Google Meet link will be generated)"
        elif location and location != 'Online':
            return f"Online ({location})"
        else:
            return "Online"
    elif mode == 'offline':
        if location and location != 'TBD':
            return f"Offline ({location})"
        else:
            return "Offline"
    else:
        return "Location not specified"
