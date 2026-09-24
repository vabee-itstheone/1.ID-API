import re
import datetime
from email.utils import parseaddr

def is_valid_email(email):
    """Validate email format."""
    return '@' in parseaddr(email)[1]

def is_valid_string(text):
    """Check if the string contains only alphabets and spaces."""
    return bool(re.match(r"^[a-zA-Z\s]*$", text)) if text else False

def is_alphanumeric(text):
    """Check if the string contains only alphanumeric characters."""
    return bool(re.match(r"^[a-zA-Z0-9]*$", text)) if text else False

def has_extra_spaces(text):
    """Check if the string has extra spaces between words."""
    return bool(re.search(r"\s{2,}", text)) if text else False

def has_more_names(text, limit=3):
    """Check if the string has more than the allowed number of words."""
    return len(re.split(r"[ ,;]+", text.strip())) > limit if text else False

def has_arabic_characters_only(text):
    """Check if the string contains only Arabic characters and spaces."""
    return all(re.match(r"[\u0600-\u06FF\s]", char) for char in text) if text else False

def is_future_date(date_str):
    """Check if a given date string is in the future."""
    try:
        date = datetime.datetime.fromisoformat(date_str)
        return date > datetime.datetime.now()
    except ValueError:
        return False
