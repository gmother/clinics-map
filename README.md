# Clinics Map

A tool for converting clinic data from CSV to JSON and geolocating clinics using LocationIQ, OpenCage, and Google Geocoding APIs.

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   make install
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   ```
   Then edit `.env` and add your API keys:
   - `LOCATIONIQ_API_KEY` - Get your key at [https://locationiq.com/](https://locationiq.com/)
   - `OPENCAGE_API_KEY` - Get your key at [https://opencagedata.com/](https://opencagedata.com/)
   - `GOOGLE_API_KEY` - Get your key at [https://console.cloud.google.com/](https://console.cloud.google.com/) (enable Geocoding API)

## Usage

### Convert CSV to JSON
```bash
make convert-csv
```
Converts `network-amber.csv` to `network-amber.json`.

### Geolocate with LocationIQ
```bash
make locationiq
```
Geolocates clinics using LocationIQ API (default: 10 requests).

To specify a custom limit:
```bash
make locationiq LIMIT=100
```

### Geolocate with OpenCage (fallback)
```bash
make opencage
```
Geolocates clinics that failed with LocationIQ using OpenCage API (default: 10 requests).

To specify a custom limit:
```bash
make opencage LIMIT=100
```

### Geolocate with Google (fallback)
```bash
make google
```
Geolocates clinics that failed with LocationIQ using Google Geocoding API (default: 10 requests).

To specify a custom limit:
```bash
make google LIMIT=100
```

### Build clinics data for web
```bash
make build
```
Processes `network-amber-located.json` and generates `docs/clinics.js` with:
- Cleaned clinic names (removed emirate in parentheses)
- Addresses with phone numbers
- Valid coordinates (prioritizing LocationIQ, then OpenCage, then Google)
- Tags extracted from clinic names (pharmacy, hospital, clinic, optical, dental, lab)

## Workflow

1. Run `make convert-csv` to convert your CSV data to JSON
2. Run `make locationiq LIMIT=<number>` to geolocate clinics (LocationIQ is cheaper)
3. Run `make opencage LIMIT=<number>` to geolocate clinics that failed with LocationIQ
4. Run `make google LIMIT=<number>` to geolocate clinics that failed with LocationIQ using Google Geocoding API
5. Run `make build` to generate `docs/clinics.js` for the web map

Results are saved to `network-amber-located.json` with coordinates stored in `locationiq`, `opencage`, and `google` arrays. The final web-ready data is in `docs/clinics.js`.

