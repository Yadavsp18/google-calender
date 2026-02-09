"""
Config Package
Contains all JSON configuration files.
"""

import os
import json

# Get the directory where this file is located
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))


def load_json(filename):
    """Load a JSON file from the config directory."""
    filepath = os.path.join(CONFIG_DIR, filename)
    with open(filepath, 'r') as f:
        return json.load(f)


def save_json(filename, data):
    """Save data to a JSON file in the config directory."""
    filepath = os.path.join(CONFIG_DIR, filename)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)


# File paths for common config files
def get_credentials_path():
    return os.path.join(CONFIG_DIR, 'credentials.json')


def get_email_path():
    return os.path.join(CONFIG_DIR, 'email.json')


def get_token_path():
    return os.path.join(CONFIG_DIR, 'token.json')


def get_names_path():
    return os.path.join(CONFIG_DIR, 'names.json')


def get_testcases_path():
    return os.path.join(CONFIG_DIR, 'testcases.json')


__all__ = [
    'CONFIG_DIR',
    'load_json',
    'save_json',
    'get_credentials_path',
    'get_email_path',
    'get_token_path',
    'get_names_path',
    'get_testcases_path',
]
