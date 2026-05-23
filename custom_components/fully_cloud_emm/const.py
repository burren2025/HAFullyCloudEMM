"""Constants for the Fully Cloud EMM integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "fully_cloud_emm"

CONF_API_EMAIL = "api_email"
CONF_API_KEY = "api_key"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL = timedelta(minutes=5)
DEFAULT_SCAN_INTERVAL_SECONDS = int(DEFAULT_SCAN_INTERVAL.total_seconds())

API_BASE_URL = "https://api.fully-kiosk.com/cloud"

PLATFORMS = ["binary_sensor", "sensor"]

