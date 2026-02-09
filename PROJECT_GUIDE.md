# Project Structure Guide

## Quick Overview

```
flask_google_calendar/
├── app.py                          # Main entry point
├── PROJECT_GUIDE.md                # This file
├── config/                         # Configuration files
├── routes/                         # Flask route handlers
├── services/                       # Business logic
├── modules/                        # NLP processing
├── training/                       # Pattern learning
└── templates/                      # HTML templates
```

---

## File Functionality Reference

### Main Entry
| File | Functionality |
|------|---------------|
| [`app.py`](app.py) | Main Flask app, registers blueprints, starts server |

### Routes (URL Handlers) - `routes/`
| File | Functionality |
|------|---------------|
| [`routes/auth.py`](routes/auth.py) | `/authorize`, `/logout`, `/oauth/callback/` - OAuth login/logout |
| [`routes/meetings.py`](routes/meetings.py) | `/`, `/nlp_create`, `/events`, `/delete_event/<id>` - Meeting CRUD |

### Services (Business Logic) - `services/`
| File | Functionality |
|------|---------------|
| [`services/auth.py`](services/auth.py) | `credentials_to_dict()` - Convert OAuth credentials to dict |
| [`services/calendar.py`](services/calendar.py) | `get_calendar_service()`, `create_calendar_event()`, `delete_calendar_event()`, `get_upcoming_events()`, `find_matching_events()` - Google Calendar API operations |

### NLP/Processing Modules - `modules/`
| File | Functionality |
|------|---------------|
| [`modules/datetime_utils.py`](modules/datetime_utils.py) | `parse_natural_language_date()`, `parse_relative_date()` - Parse natural language dates like "tomorrow at 3pm" |
| [`modules/meeting_extractor.py`](modules/meeting_extractor.py) | `extract_meeting_details()` - Extract title, attendees, time from natural language |

### Training (Pattern Learning) - `training/`
| File | Functionality |
|------|---------------|
| [`training/learner.py`](training/learner.py) | `learn_patterns()`, `analyze_training_data()` - Learn patterns from examples |
| [`training/generator.py`](training/generator.py) | `generate_training_examples()`, `save_training_data()` - Generate training data |

### Templates (HTML Pages) - `templates/`
| File | Functionality |
|------|---------------|
| [`templates/base.html`](templates/base.html) | Main layout - CSS styles, header, footer, navigation |
| [`templates/index.html`](templates/index.html) | Home page - Auth status, create meeting form, cancel meeting form |
| [`templates/event_created.html`](templates/event_created.html) | Shows ALL event details after creation (title, time, attendees, description, raw JSON) |
| [`templates/events.html`](templates/events.html) | List all upcoming events |
| [`templates/delete_select.html`](templates/delete_select.html) | Show multiple matches when canceling - select which to delete |
| [`templates/message.html`](templates/message.html) | Generic success/error message display |

### Config (JSON Files) - `config/`
| File | Functionality |
|------|---------------|
| `config/credentials.json` | Google OAuth client ID/secret from Google Cloud Console |
| `config/token.json` | OAuth access/refresh tokens (auto-generated) |
| `config/email.json` | Email book - maps names to email addresses |
| `config/names.json` | Names dictionary for NLP |

---

## How It Works

### 1. User Flow
1. User visits `/` → See auth status
2. Click "Connect Google Calendar" → Redirect to Google OAuth
3. Google redirects to `/oauth/callback/` → Save credentials
4. User enters natural language: "Meeting with John tomorrow at 3pm"
5. Form submits to `/nlp_create` → Routes to [`routes/meetings.py`](routes/meetings.py)

### 2. Meeting Creation Flow
```
/nlp_create (route)
    ↓
extract_meeting_details() (modules/meeting_extractor.py)
    ↓
get_calendar_service() (services/calendar.py)
    ↓
service.events().insert() (Google API)
    ↓
render event_created.html (templates/event_created.html)
```

### 3. Key Functions
| Function | Location | Purpose |
|----------|----------|---------|
| `get_calendar_service()` | services/calendar.py | Get authenticated Google Calendar API service |
| `extract_meeting_details()` | modules/meeting_extractor.py | Parse "Meeting with John tomorrow at 3pm" → {title, attendees, start, end} |
| `parse_natural_language_date()` | modules/datetime_utils.py | Parse "tomorrow at 3pm" → datetime object |

---

## Adding New Features

### To add a new page:
1. Create template in `templates/`
2. Add route in `routes/`
3. Register blueprint in `app.py`

### To modify meeting creation:
- Change [`routes/meetings.py`](routes/meetings.py) → `handle_create_meeting()` function

### To change NLP parsing:
- Modify [`modules/meeting_extractor.py`](modules/meeting_extractor.py) → `extract_meeting_details()` function

### To change date parsing:
- Modify [`modules/datetime_utils.py`](modules/datetime_utils.py)

### To add new API calls:
- Add to [`services/calendar.py`](services/calendar.py)
