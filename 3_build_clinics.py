#!/usr/bin/env python3
"""
Script to build docs/clinics.json from network-amber-located.json
"""

import json
import re


def clean_name(name):
    """Remove parentheses with content at the end"""
    # Remove " (EMIRATE)" or "(EMIRATE)" at the end
    name = re.sub(r'\s*\([^)]+\)\s*$', '', name)
    return name


def extract_tags(name):
    """Extract tags from clinic name based on keywords"""
    if not name:
        return None
    
    name_lower = name.lower()
    tags = []
    has_pharmacy = False
    
    # Check for pharmacy
    if re.search(r'\bpharmacy\b', name_lower):
        tags.append('pharmacy')
        has_pharmacy = True
    
    # Check for hospital (but not if pharmacy found)
    if not has_pharmacy and (re.search(r'\bhospital\b', name_lower) or re.search(r'\bhospitals\b', name_lower)):
        tags.append('hospital')
    
    # Check for clinic/polyclinic/medical center (but not if pharmacy found)
    if not has_pharmacy and (re.search(r'\bclinic\b', name_lower) or 
        re.search(r'\bclinics\b', name_lower) or 
        re.search(r'\bpolyclinic\b', name_lower) or
        re.search(r'\bmedical center\b', name_lower) or
        re.search(r'\bmedical centre\b', name_lower)):
        tags.append('clinic')
    
    # Check for optical (can be combined with other tags)
    if (re.search(r'\boptical\b', name_lower) or 
        re.search(r'\boptics\b', name_lower) or 
        re.search(r'\beye\b', name_lower)):
        tags.append('optical')
    
    # Check for dental (can be combined with other tags)
    if re.search(r'\bdental\b', name_lower):
        tags.append('dental')
    
    # Check for lab (can be combined with other tags)
    if (re.search(r'\blaboratory\b', name_lower) or 
        re.search(r'\blaboratories\b', name_lower) or 
        re.search(r'\bdiagnostic\b', name_lower) or
        re.search(r'\bdiagnostics\b', name_lower) or
        re.search(r'\blab\b', name_lower)):
        tags.append('lab')
    
    # Return tags only if any were found
    return tags if tags else None


def get_coordinates(record):
    """Extract coordinates from locationiq or opencage, return (lat, lon) or None"""
    # Try locationiq first
    if 'locationiq' in record and record['locationiq']:
        loc = record['locationiq']
        if isinstance(loc, list) and len(loc) == 2:
            return (loc[0], loc[1])

    # Try google
    if 'google' in record and record['google']:
        loc = record['google']
        if isinstance(loc, list) and len(loc) == 2:
            return (loc[0], loc[1])
    
    # Try opencage
    if 'opencage' in record and record['opencage']:
        loc = record['opencage']
        if isinstance(loc, list) and len(loc) == 2:
            return (loc[0], loc[1])
    
    return None


def build_address(address, phone):
    """Combine address and phone with comma"""
    if phone:
        return f"{address}, {phone}"
    return address


def process_record(record):
    """Process a single record and return clinic dict or None"""
    # Get coordinates
    coords = get_coordinates(record)
    if coords is None:
        return None  # Skip records without coordinates
    
    lat, lon = coords
    
    # Clean name (remove space before parentheses)
    name = clean_name(record.get('name', ''))
    
    # Build address with phone
    address = build_address(
        record.get('address', ''),
        record.get('phone', '')
    )
    
    # Extract tags from original name (before cleaning)
    original_name = record.get('name', '')
    tags = extract_tags(original_name)
    
    # Build result
    result = {
        'name': name,
        'address': address,
        'lat': lat,
        'lon': lon
    }
    
    # Add tags only if any were found
    if tags:
        result['tags'] = tags
    
    return result


def main():
    # Read source file
    with open('network-amber-located.json', 'r', encoding='utf-8') as f:
        source_data = json.load(f)
    
    # Process records
    clinics = []
    skipped = 0
    
    for record in source_data:
        clinic = process_record(record)
        if clinic:
            clinics.append(clinic)
        else:
            skipped += 1
    
    # Write output file as JavaScript variable (minified JSON)
    with open('docs/clinics.js', 'w', encoding='utf-8') as f:
        json_str = json.dumps(clinics, ensure_ascii=False, separators=(',', ':'))
        f.write(f'const data = {json_str};\n')
    
    print(f"Processed {len(clinics)} clinics")
    print(f"Skipped {skipped} records without coordinates")


if __name__ == '__main__':
    main()

