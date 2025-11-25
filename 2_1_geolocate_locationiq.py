# pip install requests
import time
import requests
import json
import os
import argparse
from pathlib import Path

# Load API key from environment variable
API_KEY = os.getenv("LOCATIONIQ_API_KEY")
if not API_KEY:
    raise ValueError("LOCATIONIQ_API_KEY environment variable is not set. Please set it in .env file.")

URL = "https://us1.locationiq.com/v1/search.php"

# File paths
INPUT_FILE = "network-amber.json"
OUTPUT_FILE = "network-amber-located.json"


def geocode(q):
    """Geocode an address query and return (lat, lng) tuple or None"""
    params = {"key": API_KEY, "q": q, "format": "json", "limit": 1}
    try:
        r = requests.get(URL, params=params, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        if not data:
            return None
        return float(data[0]["lat"]), float(data[0]["lon"])
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


def main():
    parser = argparse.ArgumentParser(description="Geolocate clinics using LocationIQ API")
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
        # Initialize all with empty locationiq
        for clinic in located_clinics:
            clinic["locationiq"] = []
    else:
        # Merge any new clinics from input that aren't in located file
        input_dict = {clinic["id"]: clinic for clinic in clinics}
        for clinic_id, clinic in input_dict.items():
            if clinic_id not in located_dict:
                clinic_copy = clinic.copy()
                clinic_copy["locationiq"] = []
                located_clinics.append(clinic_copy)
                located_dict[clinic_id] = clinic_copy
        
        # Validate existing locationiq coordinates
        print("Validating existing locationiq coordinates...")
        invalid_count = 0
        for clinic in located_clinics:
            if "locationiq" in clinic and isinstance(clinic["locationiq"], list) and len(clinic["locationiq"]) == 2:
                lat, lng = clinic["locationiq"][0], clinic["locationiq"][1]
                if not is_valid_uae_coordinates(lat, lng):
                    print(f"  Invalid coordinates for {clinic['name']}: [{lat}, {lng}] - clearing")
                    clinic["locationiq"] = []
                    invalid_count += 1
        if invalid_count > 0:
            print(f"Cleared {invalid_count} invalid locationiq coordinates")

    # Process clinics
    geocoded_count = 0
    skipped_count = 0
    total_requests = 0

    for clinic in located_clinics:
        # Skip if locationiq already exists (whether successful or failed)
        if "locationiq" in clinic:
            skipped_count += 1
            continue
        
        # Initialize locationiq if it doesn't exist
        clinic["locationiq"] = []

        # Check max requests limit
        if args.max_requests is not None and total_requests >= args.max_requests:
            print(f"Reached max requests limit ({args.max_requests}), stopping...")
            break

        # Geocode
        query = f"{clinic['name']}, {clinic['address']}"
        print(f"Geocoding: {clinic['name']}...")
        result = geocode(query)

        if result:
            lat, lng = result[0], result[1]
            # Validate coordinates are within UAE bounds
            if is_valid_uae_coordinates(lat, lng):
                clinic["locationiq"] = [lat, lng]
                print(f"  -> Success: [{lat}, {lng}]")
                geocoded_count += 1
            else:
                clinic["locationiq"] = []
                print(f"  -> Failed: coordinates out of UAE bounds [{lat}, {lng}]")
        else:
            clinic["locationiq"] = []
            print(f"  -> Failed")
        
        total_requests += 1

        # Save every 10 requests
        if total_requests % 10 == 0:
            print(f"Saving progress... (processed {total_requests} requests)")
            save_json_file(OUTPUT_FILE, located_clinics)

        time.sleep(0.6)  # ~1.6 rps -> respect rate limits (2rps officially allowed) 

    # Final save
    print(f"Saving final results...")
    save_json_file(OUTPUT_FILE, located_clinics)

    print(f"\nSummary:")
    print(f"  Total requests made: {total_requests}")
    print(f"  Successfully geocoded: {geocoded_count}")
    print(f"  Skipped (already geocoded): {skipped_count}")
    print(f"  Results saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
