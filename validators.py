# utils/validators.py
import re

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_phone(phone):
    pattern = r'^\+?1?\d{9,15}$'
    return bool(re.match(pattern, phone))

def validate_password(password):
    if len(password) < 6:
        return False, "Password must be at least 6 characters"
    return True, ""

def validate_job_data(data):
    errors = []
    
    if not data.get('title') or len(data['title']) < 3:
        errors.append("Job title must be at least 3 characters")
    
    if not data.get('description') or len(data['description']) < 20:
        errors.append("Job description must be at least 20 characters")
    
    return errors