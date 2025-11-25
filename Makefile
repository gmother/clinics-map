.PHONY: install convert-csv locationiq opencage google build

# Default limit for geolocation requests
LIMIT ?= 10

# Use Python from virtual environment if it exists, otherwise use system Python
PYTHON := $(shell if [ -f venv/bin/python ]; then echo venv/bin/python; else echo python3; fi)

install:
	@if [ ! -d venv ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv venv; \
	fi
	@echo "Installing dependencies..."
	@venv/bin/pip install --upgrade pip
	@venv/bin/pip install -r requirements.txt
	@echo "Installation complete! You can now use 'make locationiq', 'make opencage', 'make google' or 'make convert-csv'"

convert-csv:
	$(PYTHON) 1_convert_csv_to_json.py

locationiq:
	@if [ -f .env ]; then export $$(grep -v '^#' .env | grep -v '^$$' | xargs); fi; \
	$(PYTHON) 2_1_geolocate_locationiq.py --max-requests $(LIMIT)

opencage:
	@if [ -f .env ]; then export $$(grep -v '^#' .env | grep -v '^$$' | xargs); fi; \
	$(PYTHON) 2_2_geolocate_opencage.py --max-requests $(LIMIT)

google:
	@if [ -f .env ]; then export $$(grep -v '^#' .env | grep -v '^$$' | xargs); fi; \
	$(PYTHON) 2_3_geolocate_google.py --max-requests $(LIMIT)

build:
	$(PYTHON) 3_build_clinics.py
