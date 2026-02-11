"""
Services Package
Contains business logic services for the application.
"""

from .calendar import (
    get_calendar_service,
    delete_calendar_event,
    get_upcoming_events,
    create_calendar_event,
    load_email_book,
    load_api_key,
    # New functions for event search and update
    search_events_by_name,
    find_event_by_name_and_date,
    get_event_id,
    modify_event_fields,
    update_calendar_event,
    patch_calendar_event,
    find_upcoming_event_by_name,
    search_and_confirm_event,
)

from .auth import (
    get_oauth_flow,
    credentials_to_dict,
    save_credentials_to_file,
    clear_credentials,
)

__all__ = [
    'get_calendar_service',
    'delete_calendar_event',
    'get_upcoming_events',
    'create_calendar_event',
    'load_email_book',
    'load_api_key',
    # New functions for event search and update
    'search_events_by_name',
    'find_event_by_name_and_date',
    'get_event_id',
    'modify_event_fields',
    'update_calendar_event',
    'patch_calendar_event',
    'find_upcoming_event_by_name',
    'search_and_confirm_event',
    'get_oauth_flow',
    'credentials_to_dict',
    'save_credentials_to_file',
    'clear_credentials',
]
