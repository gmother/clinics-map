# pip install requests
import time
import requests
import json
import os
import argparse
from pathlib import Path

# Load API key from environment variable
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable is not set. Please set it in .env file.")

URL = "https://maps.googleapis.com/maps/api/geocode/json"

# File paths
INPUT_FILE = "network-amber.json"
OUTPUT_FILE = "network-amber-located.json"


def geocode(q):
    """Geocode an address query using Google Geocoding API and return (lat, lng) tuple or None"""
    params = {"key": API_KEY, "address": q}
    try:
        r = requests.get(URL, params=params, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        if data.get("status") != "OK":
            return None
        if not data.get("results") or len(data["results"]) == 0:
            return None
        location = data["results"][0].get("geometry", {}).get("location", {})
        lat = location.get("lat")
        lng = location.get("lng")
        if lat is None or lng is None:
            return None
        return float(lat), float(lng)
    except Exception as e:
        print(f"Error geocoding '{q}': {e}")
        return None


def load_json_file(filepath):
    """Load JSON file, return empty list if file doesn't exist"""
    if Path(filepath).exists():
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_json_file(filepath, data):
    """Save data to JSON file"""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def is_valid_uae_coordinates(lat, lng):
    """Check if coordinates are within UAE bounds (lat: 22-27, lng: 52-57)"""
    return 22.5 <= lat <= 26.5 and 52.0 <= lng <= 57.0


def should_geocode(clinic):
    """
    Check if clinic should be geocoded with Google.
    Returns True only if:
    - locationiq exists and is an empty array (failed geocoding)
    - google doesn't exist (no previous attempt)
    """
    # google must not exist (no previous attempt)
    if "google" in clinic:
        return False
    
    return True


def main():
    parser = argparse.ArgumentParser(description="Geolocate clinics using Google Geocoding API (fallback after LocationIQ)")
    parser.add_argument(
        "--max-requests",
        type=int,
        default=None,
        help="Maximum number of geolocation requests to make (for testing)"
    )
    args = parser.parse_args()

    # Load input data
    print(f"Loading {INPUT_FILE}...")
    clinics = load_json_file(INPUT_FILE)
    print(f"Loaded {len(clinics)} clinics")

    # Load existing located data
    print(f"Loading {OUTPUT_FILE}...")
    located_clinics = load_json_file(OUTPUT_FILE)
    
    # Create a dictionary for quick lookup by id
    located_dict = {clinic["id"]: clinic for clinic in located_clinics}
    
    # If output file doesn't exist or is empty, initialize with input data
    if not located_clinics:
        located_clinics = clinics.copy()
        located_dict = {clinic["id"]: clinic for clinic in located_clinics}
        # Initialize all with empty locationiq (if not present)
        for clinic in located_clinics:
            if "locationiq" not in clinic:
                clinic["locationiq"] = []
    else:
        # Merge any new clinics from input that aren't in located file
        input_dict = {clinic["id"]: clinic for clinic in clinics}
        for clinic_id, clinic in input_dict.items():
            if clinic_id not in located_dict:
                clinic_copy = clinic.copy()
                if "locationiq" not in clinic_copy:
                    clinic_copy["locationiq"] = []
                located_clinics.append(clinic_copy)
                located_dict[clinic_id] = clinic_copy
        
        # Validate existing google coordinates
        print("Validating existing google coordinates...")
        invalid_count = 0
        for clinic in located_clinics:
            if "google" in clinic and isinstance(clinic["google"], list) and len(clinic["google"]) == 2:
                lat, lng = clinic["google"][0], clinic["google"][1]
                if not is_valid_uae_coordinates(lat, lng):
                    print(f"  Invalid coordinates for {clinic['name']}: [{lat}, {lng}] - clearing")
                    clinic["google"] = []
                    invalid_count += 1
        if invalid_count > 0:
            print(f"Cleared {invalid_count} invalid google coordinates")

    # Process clinics
    geocoded_count = 0
    skipped_count = 0
    total_requests = 0

    for clinic in located_clinics:
        # Check if this clinic should be geocoded
        if not should_geocode(clinic):
            skipped_count += 1
            continue

        # Check max requests limit
        if args.max_requests is not None and total_requests >= args.max_requests:
            print(f"Reached max requests limit ({args.max_requests}), stopping...")
            break

        # Geocode
        query = f"{clinic['name']}, {clinic['address']}"
        print(f"Geocoding with Google: {clinic['name']}...")
        result = geocode(query)

        if result:
            lat, lng = result[0], result[1]
            # Validate coordinates are within UAE bounds
            if is_valid_uae_coordinates(lat, lng):
                clinic["google"] = [lat, lng]
                print(f"  -> Success: [{lat}, {lng}]")
                geocoded_count += 1
            else:
                clinic["google"] = []
                print(f"  -> Failed: coordinates out of UAE bounds [{lat}, {lng}]")
        else:
            clinic["google"] = []
            print(f"  -> Failed")
        
        total_requests += 1

        # Save every 10 requests
        if total_requests % 10 == 0:
            print(f"Saving progress... (processed {total_requests} requests)")
            save_json_file(OUTPUT_FILE, located_clinics)

        # time.sleep(0.1)  # Google allows higher rate limits, but be respectful 

    # Final save
    print(f"Saving final results...")
    save_json_file(OUTPUT_FILE, located_clinics)

    print(f"\nSummary:")
    print(f"  Total requests made: {total_requests}")
    print(f"  Successfully geocoded: {geocoded_count}")
    print(f"  Skipped (already geocoded or not eligible): {skipped_count}")
    print(f"  Results saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

