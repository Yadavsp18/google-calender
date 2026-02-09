"""
Training Package for Meeting Parser
Contains modules for learning patterns and generating code.

Package Structure:
- training/patterns.py - Pattern definitions
- training/learner.py - Pattern learning logic
- training/generator.py - Code generation
"""

from .patterns import (
    ACTION_TO_INTENT,
    LOCATION_WORDS,
    MEETING_TYPES,
    DURATION_PATTERNS,
    RECURRENCE_PATTERNS,
    AGENDA_PATTERNS,
    ATTENDEE_PATTERNS,
    TIME_MODIFIERS,
    ONLINE_PATTERNS,
    OFFLINE_PATTERNS,
    MEET_LINK_PATTERN,
)

from .learner import (
    load_training_data,
    learn_patterns,
    analyze_patterns,
    generate_pattern_report,
    extract_patterns_from_utterance,
)

from .generator import (
    generate_trained_patterns_code,
    save_generated_code,
    generate_and_save,
)

__all__ = [
    # Patterns
    'ACTION_TO_INTENT',
    'LOCATION_WORDS',
    'MEETING_TYPES',
    'DURATION_PATTERNS',
    'RECURRENCE_PATTERNS',
    'AGENDA_PATTERNS',
    'ATTENDEE_PATTERNS',
    'TIME_MODIFIERS',
    'ONLINE_PATTERNS',
    'OFFLINE_PATTERNS',
    'MEET_LINK_PATTERN',
    
    # Functions
    'load_training_data',
    'learn_patterns',
    'analyze_patterns',
    'generate_pattern_report',
    'extract_patterns_from_utterance',
    'generate_trained_patterns_code',
    'save_generated_code',
    'generate_and_save',
]
