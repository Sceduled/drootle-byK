"""
Utility functions for phone number parsing and formatting.
"""
import re

def normalize_phone(raw: str) -> str:
    """
    Normalizes a phone number to E.164 format.
    """
    # Strip spaces, dashes, brackets, dots
    cleaned = re.sub(r'[\s\-\(\)\.]', '', raw)

    if cleaned.startswith('0') and len(cleaned) == 11:
        # starts with 0 and is 10 digits (0 + 10 = 11)
        cleaned = '+91' + cleaned[1:]
    elif len(cleaned) == 10 and not cleaned.startswith('+'):
        # 10 digits with no country code
        if cleaned[0] not in "6789":
            raise ValueError("no country code, not 10 digits")
        cleaned = '+91' + cleaned
    elif cleaned.startswith('91') and len(cleaned) == 12:
        # starts with 91 and is 12 digits
        cleaned = '+' + cleaned
    elif cleaned.startswith('+'):
        # already starts with +
        pass
    else:
        raise ValueError("Invalid phone number format")

    # Ensure it starts with '+'
    if not cleaned.startswith('+'):
        cleaned = '+' + cleaned

    # Check if result is 10-15 digits after stripping '+'
    digits_only = cleaned.replace('+', '')
    if not (10 <= len(digits_only) <= 15) or not digits_only.isdigit():
        raise ValueError("Invalid phone number length after normalization")
    return cleaned
