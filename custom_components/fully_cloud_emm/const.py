"""Constants for the Fully Cloud EMM integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "fully_cloud_emm"

CONF_API_EMAIL = "api_email"
CONF_API_KEY = "api_key"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL = timedelta(hours=1)
DEFAULT_SCAN_INTERVAL_SECONDS = int(DEFAULT_SCAN_INTERVAL.total_seconds())

SERVICE_REFRESH = "refresh"
SERVICE_REFRESH_DEVICE = "refresh_device"
SERVICE_REBOOT_DEVICE = "reboot_device"
SERVICE_RESTART_APP = "restart_app"

ATTR_DEVID = "devid"
ATTR_NOWAIT = "nowait"
ATTR_QUEUE_OFFLINE = "queue_offline"

API_BASE_URLS = (
    "https://api.fully-kiosk.com/cloud",
    "https://cloud.fully-kiosk.com/cloud",
)
API_REMOTE_URL = "https://api.fully-kiosk.com/remote/"

PLATFORMS = ["binary_sensor", "sensor"]
