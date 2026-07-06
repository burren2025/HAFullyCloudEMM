"""Constants for the Fully Cloud EMM integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "fully_cloud_emm"

CONF_API_EMAIL = "api_email"
CONF_API_KEY = "api_key"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_LOCAL_DEVICES = "local_devices"
CONF_LOCAL_HOST = "local_host"
CONF_LOCAL_PORT = "local_port"
CONF_LOCAL_PASSWORD = "local_password"
CONF_ENTRY_TYPE = "entry_type"
ENTRY_TYPE_CLOUD = "cloud"
ENTRY_TYPE_LOCAL = "local"

DEFAULT_SCAN_INTERVAL = timedelta(hours=1)
DEFAULT_SCAN_INTERVAL_SECONDS = int(DEFAULT_SCAN_INTERVAL.total_seconds())
DEFAULT_LOCAL_API_PORT = 2323

SERVICE_LOAD_START_URL = "load_start_url"
SERVICE_LOAD_URL = "load_url"
SERVICE_REFRESH = "refresh"
SERVICE_REFRESH_DEVICE = "refresh_device"
SERVICE_REBOOT_DEVICE = "reboot_device"
SERVICE_RESTART_APP = "restart_app"
SERVICE_SCREEN_OFF = "screen_off"
SERVICE_SCREEN_ON = "screen_on"
SERVICE_SET_AUDIO_VOLUME = "set_audio_volume"
SERVICE_SET_OVERLAY_MESSAGE = "set_overlay_message"
SERVICE_START_APPLICATION = "start_application"
SERVICE_START_SCREENSAVER = "start_screensaver"
SERVICE_STOP_SCREENSAVER = "stop_screensaver"
SERVICE_STOP_TEXT_TO_SPEECH = "stop_text_to_speech"
SERVICE_TEXT_TO_SPEECH = "text_to_speech"

ATTR_ACTION = "action"
ATTR_DEVID = "devid"
ATTR_ENGINE = "engine"
ATTR_FOCUS = "focus"
ATTR_LEVEL = "level"
ATTR_LOCALE = "locale"
ATTR_NEW_TAB = "new_tab"
ATTR_NOWAIT = "nowait"
ATTR_PACKAGE = "package"
ATTR_QUEUE = "queue"
ATTR_QUEUE_OFFLINE = "queue_offline"
ATTR_STREAM = "stream"
ATTR_TAB = "tab"
ATTR_TEXT = "text"
ATTR_URL = "url"

API_BASE_URLS = (
    "https://api.fully-kiosk.com/cloud",
    "https://cloud.fully-kiosk.com/cloud",
)
API_REMOTE_URL = "https://api.fully-kiosk.com/remote/"

PLATFORMS = ["binary_sensor", "sensor"]
