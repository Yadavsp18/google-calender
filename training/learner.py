"""
Pattern Learning Module
Learns patterns from testcases.json and builds the patterns database.
"""

import json
import re
from collections import defaultdict

# Import config for testcases path
from config import get_testcases_path


def load_training_data(filename=None):
    """Load training data from config/testcases.json."""
    if filename is None:
        filename = get_testcases_path()
    with open(filename, 'r') as f:
        return json.load(f)


def extract_patterns_from_utterance(utterance):
    """Extract potential patterns from a single utterance."""
    patterns = {
        'actions': [],
        'intents': [],
        'online': [],
        'offline': [],
        'times': [],
        'durations': [],
        'agendas': [],
        'attendees': [],
    }
    
    utterance_lower = utterance.lower()
    
    # Extract time patterns
    time_patterns = [
        r'\b\d{1,2}:\d{2}\s*(?:am|pm)?\b',
        r'\b\d{1,2}\s*(?:am|pm)\b',
        r'\b(?:today|tomorrow|yesterday)\b',
        r'\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
        r'\b(?:next|this)\s*(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
    ]
    
    for pattern in time_patterns:
        matches = re.findall(pattern, utterance_lower)
        patterns['times'].extend(matches)
    
    # Extract duration patterns
    duration_patterns = [
        r'\b\d+\s*(?:hour|hr|min|minute)s?\b',
        r'\b(?:half|quarter)\s*(?:an?\s*)?hour\b',
        r'\b(?:quick|brief|short)\b',
    ]
    
    for pattern in duration_patterns:
        matches = re.findall(pattern, utterance_lower)
        patterns['durations'].extend(matches)
    
    # Extract attendee patterns
    attendee_patterns = [
        r'\bwith\s+([A-Z][a-z]+(?:\s+(?:and|&)\s+[A-Z][a-z]+)*)\b',
        r'\bwith\s+([A-Z][a-z]+(?:\s*,\s*[A-Z][a-z]+)*)\b',
        r'\bfor\s+([A-Z][a-z]+(?:\s+team)?)\b',
    ]
    
    for pattern in attendee_patterns:
        matches = re.findall(pattern, utterance, re.IGNORECASE)
        patterns['attendees'].extend(matches)
    
    return patterns


def learn_patterns(training_data):
    """
    Learn patterns from training data.
    
    Args:
        training_data: Dictionary with 'records' key containing training examples
    
    Returns:
        Dictionary with learned patterns
    """
    records = training_data.get('records', [])
    
    learned = {
        'action_patterns': defaultdict(list),
        'intent_patterns': defaultdict(list),
        'mode_patterns': {'online': [], 'offline': []},
        'link_preference_patterns': defaultdict(list),
        'time_window_patterns': [],
        'recurrence_patterns': [],
        'extracted_patterns': [],
    }
    
    for record in records:
        utterance = record.get('utterance', '').lower()
        action = record.get('action', '')
        intent = record.get('intent', '')
        mode = record.get('mode', '')
        link_pref = record.get('link_preference', '')
        constraints = record.get('constraints', [])
        
        # Extract patterns from utterance
        extracted = extract_patterns_from_utterance(utterance)
        learned['extracted_patterns'].append({
            'utterance': utterance,
            'action': action,
            'intent': intent,
            'mode': mode,
            'extracted': extracted
        })
        
        if action:
            learned['action_patterns'][action].append(utterance)
        if intent:
            learned['intent_patterns'][intent].append(utterance)
        if mode == 'online':
            learned['mode_patterns']['online'].append(utterance)
        elif mode == 'offline':
            learned['mode_patterns']['offline'].append(utterance)
        if link_pref:
            learned['link_preference_patterns'][link_pref].append(utterance)
        if 'time_window' in str(constraints):
            learned['time_window_patterns'].append(utterance)
        if 'recurrence' in str(constraints):
            learned['recurrence_patterns'].append(utterance)
    
    return learned


def analyze_patterns(learned):
    """
    Analyze learned patterns and generate insights.
    
    Args:
        learned: Dictionary with learned patterns
    
    Returns:
        Analysis results
    """
    analysis = {
        'action_counts': {},
        'intent_counts': {},
        'mode_counts': {'online': 0, 'offline': 0},
        'common_time_patterns': [],
        'common_duration_patterns': [],
    }
    
    # Count actions and intents
    for action, examples in learned['action_patterns'].items():
        analysis['action_counts'][action] = len(examples)
    
    for intent, examples in learned['intent_patterns'].items():
        analysis['intent_counts'][intent] = len(examples)
    
    # Count modes
    analysis['mode_counts']['online'] = len(learned['mode_patterns']['online'])
    analysis['mode_counts']['offline'] = len(learned['mode_patterns']['offline'])
    
    # Analyze extracted patterns
    all_times = []
    all_durations = []
    
    for item in learned['extracted_patterns']:
        all_times.extend(item['extracted'].get('times', []))
        all_durations.extend(item['extracted'].get('durations', []))
    
    # Count common patterns
    from collections import Counter
    time_counts = Counter(all_times)
    duration_counts = Counter(all_durations)
    
    analysis['common_time_patterns'] = time_counts.most_common(10)
    analysis['common_duration_patterns'] = duration_counts.most_common(10)
    
    return analysis


def generate_pattern_report(learned, analysis):
    """
    Generate a human-readable report of learned patterns.
    
    Args:
        learned: Dictionary with learned patterns
        analysis: Analysis results
    
    Returns:
        Report string
    """
    lines = []
    lines.append("=" * 60)
    lines.append("PATTERN LEARNING REPORT")
    lines.append("=" * 60)
    
    # Actions
    lines.append("\n📋 ACTIONS:")
    for action, count in analysis['action_counts'].items():
        lines.append(f"  • {action}: {count} examples")
    
    # Intents
    lines.append("\n🎯 INTENTS:")
    for intent, count in analysis['intent_counts'].items():
        lines.append(f"  • {intent}: {count} examples")
    
    # Modes
    lines.append("\n📍 MODES:")
    lines.append(f"  • Online: {analysis['mode_counts']['online']} examples")
    lines.append(f"  • Offline: {analysis['mode_counts']['offline']} examples")
    
    # Common time patterns
    lines.append("\n⏰ COMMON TIME PATTERNS:")
    for pattern, count in analysis['common_time_patterns']:
        lines.append(f"  • '{pattern}': {count} occurrences")
    
    # Common duration patterns
    lines.append("\n⏱️ COMMON DURATION PATTERNS:")
    for pattern, count in analysis['common_duration_patterns']:
        lines.append(f"  • '{pattern}': {count} occurrences")
    
    return '\n'.join(lines)


if __name__ == "__main__":
    # Example usage
    training_data = load_training_data()
    learned = learn_patterns(training_data)
    analysis = analyze_patterns(learned)
    
    report = generate_pattern_report(learned, analysis)
    print(report)
