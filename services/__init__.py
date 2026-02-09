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
    'get_oauth_flow',
    'credentials_to_dict',
    'save_credentials_to_file',
    'clear_credentials',
]
