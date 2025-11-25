#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to convert network-amber.csv to network-amber.json
with data cleaning and phone number normalization
"""

import csv
import json
import re
from typing import List, Optional, Tuple


def clean_text(text: str) -> str:
    """Clean text: remove duplicate spaces, trailing punctuation, fix parentheses"""
    if not text:
        return ""
    
    # Remove replacement characters () and other invalid Unicode characters
    text = text.replace('', '')
    # Remove other common replacement characters and invalid Unicode
    text = re.sub(r'[\uFFFD\uFFFE\uFFFF]', '', text)
    
    # Replace ABUDHABI with ABU DHABI
    text = re.sub(r'\bABUDHABI\b', 'ABU DHABI', text, flags=re.IGNORECASE)
    
    # Fix spaces around commas: remove space before comma, ensure space after comma
    text = re.sub(r'\s+,', ',', text)  # Remove space before comma
    text = re.sub(r',([^\s])', r', \1', text)  # Add space after comma if missing
    
    # Add space before opening parenthesis if missing
    text = re.sub(r'([^\s(])\s*\(', r'\1 (', text)
    
    # Remove spaces inside parentheses next to the parentheses
    text = re.sub(r'\(\s+', '(', text)
    text = re.sub(r'\s+\)', ')', text)
    
    # Remove trailing dashes with spaces, commas, and other punctuation
    text = re.sub(r'\s*-\s*$', '', text)
    text = re.sub(r'[,\s]+$', '', text)
    
    # Remove duplicate spaces
    text = re.sub(r'\s+', ' ', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text


def normalize_single_phone(phone: str, inferred_area_code: Optional[str] = None) -> Optional[str]:
    """Normalize a single phone number, optionally using inferred area code for partial numbers"""
    phone = phone.strip()
    if not phone:
        return None
    
    # Remove all non-digit characters except + at the start
    digits_only = re.sub(r'[^\d+]', '', phone)
    
    # If starts with +, keep it, otherwise remove it
    if digits_only.startswith('+'):
        digits_only = digits_only[1:]
    
    # Remove leading zeros
    digits_only = digits_only.lstrip('0')
    
    # If empty after removing zeros, skip
    if not digits_only:
        return None
    
    area_code = None
    rest = None
    
    # Handle different formats:
    # - 9712... or 009712... -> +971 2...
    # - 9714... or 009714... -> +971 4...
    # - 9715... or 009715... -> +971 5...
    # - 02... -> +971 2...
    # - 04... -> +971 4...
    # - 05... -> +971 5...
    # - 2... (7-8 digits) -> +971 2...
    # - 4... (7-8 digits) -> +971 4...
    # - 5... (8-9 digits) -> +971 5...
    
    if digits_only.startswith('971'):
        # Already has country code
        area_code = digits_only[3]
        rest = digits_only[4:]
    elif digits_only.startswith('00971'):
        # Has 00971 prefix
        area_code = digits_only[5]
        rest = digits_only[6:]
    elif len(digits_only) >= 2 and digits_only[0] == '0' and digits_only[1] in ['2', '4', '5']:
        # Starts with 02, 04, 05
        area_code = digits_only[1]
        rest = digits_only[2:]
    elif len(digits_only) >= 1 and digits_only[0] in ['2', '4', '5']:
        # Starts with 2, 4, or 5 (local number)
        area_code = digits_only[0]
        rest = digits_only[1:]
    else:
        # Try to infer from length and pattern
        # If 7-9 digits, might be a partial number
        if len(digits_only) >= 7:
            # If we have an inferred area code and the number is 7 digits, use it
            if inferred_area_code and len(digits_only) == 7:
                area_code = inferred_area_code
                rest = digits_only
            # If 8-9 digits and starts with 2, 4, or 5, assume it's a local number
            elif len(digits_only) >= 8 and digits_only[0] in ['2', '4', '5']:
                area_code = digits_only[0]
                rest = digits_only[1:]
            # If 7 digits and starts with 4, try area code 2 or 4 (prefer 2 if inferred)
            elif len(digits_only) == 7 and digits_only[0] == '4':
                if inferred_area_code:
                    area_code = inferred_area_code
                else:
                    # Default to area code 2 for 7-digit numbers starting with 4 (common in Abu Dhabi)
                    area_code = '2'
                rest = digits_only
            else:
                return None
        else:
            return None
    
    # Validate the rest of the number
    # Area code 2 or 4: should have 7-8 digits
    # Area code 5: should have 8-9 digits
    if area_code in ['2', '4']:
        if len(rest) < 7 or len(rest) > 8:
            return None
    elif area_code == '5':
        if len(rest) < 8 or len(rest) > 9:
            return None
    else:
        return None
    
    # Format as +971 (area_code)(rest)
    return f"+971 {area_code}{rest}"


def extract_emirate_from_name(name: str) -> Optional[str]:
    """Extract emirate name from parentheses at the end of name or from the end of name"""
    if not name:
        return None
    
    # First, try to find emirate in parentheses at the end
    match = re.search(r'\(([^)]+)\)\s*$', name)
    if match:
        emirate = match.group(1).strip().upper()
        
        # Handle special cases
        if emirate == 'GOVERNMENT-DHA':
            return 'DUBAI'
        elif emirate in ['AL AIN', 'ALAIN']:
            return 'AL AIN'  # Special marker for Al Ain
        
        return emirate
    
    # If not found in parentheses, try to find emirate at the end of name (after last parenthesis or dash)
    # Look for patterns like "MUSSAFAH-ABUDHABI" or "DUBAI" at the end
    name_upper = name.upper().strip()
    
    # Check for emirates at the end (after dash, space, or directly)
    emirate_patterns = [
        (r'[- ](ABU\s+DHABI|ABUDHABI)\s*$', 'ABU DHABI'),
        (r'[- ](DUBAI)\s*$', 'DUBAI'),
        (r'[- ](SHARJAH)\s*$', 'SHARJAH'),
        (r'[- ](AJMAN)\s*$', 'AJMAN'),
        (r'[- ](UMM\s+AL\s+QUWAIN)\s*$', 'UMM AL QUWAIN'),
        (r'[- ](RAS\s+AL\s+KHAIMAH)\s*$', 'RAS AL KHAIMAH'),
        (r'[- ](FUJAIRAH)\s*$', 'FUJAIRAH'),
        # Also check for emirates directly at the end (without dash/space before)
        (r'(DUBAI)\s*$', 'DUBAI'),
        (r'(SHARJAH)\s*$', 'SHARJAH'),
        (r'(AJMAN)\s*$', 'AJMAN'),
    ]
    
    for pattern, emirate_name in emirate_patterns:
        match = re.search(pattern, name_upper)
        if match:
            return emirate_name
    
    # Check for unclosed parentheses with emirate
    match = re.search(r'\(([^)]*ABU\s*DHABI[^)]*)$', name_upper)
    if match:
        return 'ABU DHABI'
    
    match = re.search(r'\(([^)]*DUBAI[^)]*)$', name_upper)
    if match:
        return 'DUBAI'
    
    return None


def normalize_emirate_name(emirate: str) -> str:
    """Convert emirate name from uppercase to title case"""
    if not emirate:
        return ""
    
    emirate_upper = emirate.upper().strip()
    
    # Map common emirate names
    emirate_map = {
        'ABU DHABI': 'Abu Dhabi',
        'DUBAI': 'Dubai',
        'SHARJAH': 'Sharjah',
        'AJMAN': 'Ajman',
        'UMM AL QUWAIN': 'Umm Al Quwain',
        'RAS AL KHAIMAH': 'Ras Al Khaimah',
        'FUJAIRAH': 'Fujairah',
        'ABU - DHABI': 'Abu Dhabi',
        'ABU-DHABI': 'Abu Dhabi',
    }
    
    if emirate_upper in emirate_map:
        return emirate_map[emirate_upper]
    
    # Default: convert to title case
    return emirate.title()


def has_emirate_at_end(address: str) -> bool:
    """Check if address ends with emirate name like ', Dubai' or ', Abu Dhabi'"""
    if not address:
        return False
    
    address_lower = address.lower().strip()
    
    # Check for common patterns with comma before emirate
    emirate_patterns = [
        r',\s*dubai\s*$',
        r',\s*abu\s+dhabi\s*$',
        r',\s*sharjah\s*$',
        r',\s*ajman\s*$',
        r',\s*umm\s+al\s+quwain\s*$',
        r',\s*ras\s+al\s+khaimah\s*$',
        r',\s*fujairah\s*$',
    ]
    
    for pattern in emirate_patterns:
        if re.search(pattern, address_lower, re.IGNORECASE):
            return True
    
    return False


def extract_emirate_from_address(address: str) -> Optional[str]:
    """Extract emirate name from address if present"""
    if not address:
        return None
    
    # Patterns for emirates (case insensitive)
    emirate_patterns = [
        (r'\bABU\s+DHABI\b', 'Abu Dhabi'),
        (r'\bDUBAI\b', 'Dubai'),
        (r'\bSHARJAH\b', 'Sharjah'),
        (r'\bAJMAN\b', 'Ajman'),
        (r'\bUMM\s+AL\s+QUWAIN\b', 'Umm Al Quwain'),
        (r'\bRAS\s+AL\s+KHAIMAH\b', 'Ras Al Khaimah'),
        (r'\bFUJAIRAH\b', 'Fujairah'),
    ]
    
    for pattern, normalized in emirate_patterns:
        if re.search(pattern, address, re.IGNORECASE):
            return normalized
    
    return None


def extract_country_from_address(address: str) -> Optional[str]:
    """Extract country name from address if present"""
    if not address:
        return None
    
    # Patterns for country names (case insensitive)
    country_patterns = [
        (r'\bU\.?A\.?E\.?\b', 'UAE'),
        (r'\bUNITED\s+ARAB\s+EMIRATES\b', 'UAE'),
    ]
    
    for pattern, normalized in country_patterns:
        if re.search(pattern, address, re.IGNORECASE):
            return normalized
    
    return None


def remove_emirate_and_country_from_address(address: str) -> Tuple[str, Optional[str], Optional[str]]:
    """Remove emirate and country from address, return cleaned address and found values"""
    if not address:
        return address, None, None
    
    # Extract emirate and country before removing
    emirate = extract_emirate_from_address(address)
    country = extract_country_from_address(address)
    
    # Remove emirate patterns (with surrounding commas, spaces, and dashes)
    # Pattern: comma/space/dash, then emirate, then optional comma/space/dash
    address = re.sub(r'[, ]\s*ABU\s+DHABI\s*([, -]|$)', r'\1', address, flags=re.IGNORECASE)
    address = re.sub(r'-\s*ABU\s+DHABI\s*([, -]|$)', r'\1', address, flags=re.IGNORECASE)
    address = re.sub(r'[, ]\s*DUBAI\s*([, -]|$)', r'\1', address, flags=re.IGNORECASE)
    address = re.sub(r'-\s*DUBAI\s*([, -]|$)', r'\1', address, flags=re.IGNORECASE)
    address = re.sub(r'[, ]\s*SHARJAH\s*([, -]|$)', r'\1', address, flags=re.IGNORECASE)
    address = re.sub(r'-\s*SHARJAH\s*([, -]|$)', r'\1', address, flags=re.IGNORECASE)
    address = re.sub(r'[, ]\s*AJMAN\s*([, -]|$)', r'\1', address, flags=re.IGNORECASE)
    address = re.sub(r'-\s*AJMAN\s*([, -]|$)', r'\1', address, flags=re.IGNORECASE)
    address = re.sub(r'[, ]\s*UMM\s+AL\s+QUWAIN\s*([, -]|$)', r'\1', address, flags=re.IGNORECASE)
    address = re.sub(r'-\s*UMM\s+AL\s+QUWAIN\s*([, -]|$)', r'\1', address, flags=re.IGNORECASE)
    address = re.sub(r'[, ]\s*RAS\s+AL\s+KHAIMAH\s*([, -]|$)', r'\1', address, flags=re.IGNORECASE)
    address = re.sub(r'-\s*RAS\s+AL\s+KHAIMAH\s*([, -]|$)', r'\1', address, flags=re.IGNORECASE)
    address = re.sub(r'[, ]\s*FUJAIRAH\s*([, -]|$)', r'\1', address, flags=re.IGNORECASE)
    address = re.sub(r'-\s*FUJAIRAH\s*([, -]|$)', r'\1', address, flags=re.IGNORECASE)
    
    # Remove country patterns
    address = re.sub(r'[, ]\s*U\.?A\.?E\.?\s*([, -]|$)', r'\1', address, flags=re.IGNORECASE)
    address = re.sub(r'-\s*U\.?A\.?E\.?\s*([, -]|$)', r'\1', address, flags=re.IGNORECASE)
    address = re.sub(r'[, ]\s*UNITED\s+ARAB\s+EMIRATES\s*([, -]|$)', r'\1', address, flags=re.IGNORECASE)
    address = re.sub(r'-\s*UNITED\s+ARAB\s+EMIRATES\s*([, -]|$)', r'\1', address, flags=re.IGNORECASE)
    
    # Clean up multiple commas, dashes, and spaces
    address = re.sub(r',\s*,+', ',', address)  # Multiple commas
    address = re.sub(r'-\s*-+', '-', address)  # Multiple dashes
    address = re.sub(r'\s+', ' ', address)  # Multiple spaces
    address = re.sub(r',\s*-\s*', ' - ', address)  # Comma-dash pattern
    address = re.sub(r'-\s*,\s*', ' - ', address)  # Dash-comma pattern
    address = re.sub(r',\s*$', '', address)  # Trailing comma
    address = re.sub(r'-\s*$', '', address)  # Trailing dash
    address = re.sub(r'\s+$', '', address)  # Trailing space
    address = address.strip()
    
    return address, emirate, country


def add_emirate_to_address(address: str, name: str) -> str:
    """Add emirate name to address if it's missing, in format 'Emirate, UAE'"""
    # Handle empty addresses - extract emirate from name and add it
    if not address or not address.strip():
        emirate_raw = extract_emirate_from_name(name)
        if emirate_raw:
            # Special handling for Al Ain
            if emirate_raw == 'AL AIN':
                return "Al Ain, Abu Dhabi, UAE"
            else:
                emirate = normalize_emirate_name(emirate_raw)
                if emirate:
                    return f"{emirate}, UAE"
        # If no emirate found in name, return empty string
        return address
    
    # Remove all existing emirate and country mentions from address
    cleaned_address, found_emirate, found_country = remove_emirate_and_country_from_address(address)
    
    # Determine emirate: use found one or extract from name
    emirate = found_emirate
    if not emirate:
        emirate_raw = extract_emirate_from_name(name)
        if emirate_raw:
            # Special handling for Al Ain
            if emirate_raw == 'AL AIN':
                # For Al Ain, add "Al Ain, Abu Dhabi, UAE" format
                country = found_country if found_country else 'UAE'
                # Check if "Al Ain" is already in address
                if not re.search(r'\bAl\s+Ain\b', cleaned_address, re.IGNORECASE):
                    cleaned_address = f"{cleaned_address}, Al Ain"
                return f"{cleaned_address}, Abu Dhabi, {country}"
            else:
                emirate = normalize_emirate_name(emirate_raw)
    
    if not emirate:
        return cleaned_address
    
    # Use found country or default to UAE
    country = found_country if found_country else 'UAE'
    
    # Add emirate and country in standard format
    return f"{cleaned_address}, {emirate}, {country}"


def normalize_phone(phone_str: str) -> str:
    """Normalize UAE phone numbers to +971 format"""
    if not phone_str:
        return ""
    
    # Split by common separators (/, comma, etc.) to handle multiple phones
    phones = [p.strip() for p in re.split(r'[/,;]', phone_str) if p.strip()]
    normalized_phones = []
    inferred_area_code = None
    processed_phones = set()
    
    # First pass: normalize complete numbers and infer area code
    for phone in phones:
        normalized = normalize_single_phone(phone)
        if normalized:
            normalized_phones.append(normalized)
            processed_phones.add(phone)
            # Extract area code from normalized number for inference
            match = re.search(r'\+971 ([245])\d+', normalized)
            if match:
                inferred_area_code = match.group(1)
    
    # Second pass: try to normalize partial numbers using inferred area code
    if inferred_area_code:
        for phone in phones:
            if phone in processed_phones:
                continue
            
            normalized = normalize_single_phone(phone, inferred_area_code)
            if normalized and normalized not in normalized_phones:
                normalized_phones.append(normalized)
                processed_phones.add(phone)
    
    return ", ".join(normalized_phones) if normalized_phones else ""


def convert_csv_to_json(csv_file: str, json_file: str):
    """Convert CSV to JSON with data cleaning"""
    results = []
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            # Extract and clean fields
            provider_number = row.get('PROVIDER NUMBER', '').strip()
            provider_name = clean_text(row.get('PROVIDER NAME', ''))
            address = clean_text(row.get('ADDRESS', ''))
            phone = normalize_phone(row.get('Phone No', ''))
            
            # Add emirate to address if missing
            address = add_emirate_to_address(address, provider_name)
            
            # Convert provider number to int
            try:
                provider_id = int(provider_number)
            except ValueError:
                # Skip rows with invalid provider numbers
                continue
            
            # Create JSON object
            result = {
                "id": provider_id,
                "name": provider_name,
                "address": address,
                "phone": phone
            }
            
            results.append(result)
    
    # Write to JSON file
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"Converted {len(results)} records from {csv_file} to {json_file}")


if __name__ == "__main__":
    convert_csv_to_json('network-amber.csv', 'network-amber.json')

