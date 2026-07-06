# Fully Cloud EMM for Home Assistant

Fully Cloud EMM is a Home Assistant custom integration for monitoring Fully Cloud EMM devices.

The integration connects to the Fully Cloud REST API, discovers the devices available to your API token, and creates Home Assistant entities from the device status fields returned by Fully Cloud.

## Features

- Configure from the Home Assistant UI.
- Poll Fully Cloud device data once per hour by default.
- Create binary sensors for boolean device fields.
- Create sensors for text and numeric device fields.
- Group entities under each Fully Cloud device.
- Manually refresh all devices or selected devices from Home Assistant actions.
- Send selected Fully Cloud commands from Home Assistant actions, including screen control, URL loading, text-to-speech, app restart, and device reboot.
- Log manual command and device-refresh outcomes in Home Assistant Core logs.

## Prerequisites

Before installing the integration, create a Fully Cloud API access token:

1. Go to the Fully Cloud EMM web app: https://cloud.fully-kiosk.com/cloud/
2. Sign in with your Fully Cloud account.
3. Open **Settings**.
4. Create or copy an **API access token**.
5. Keep the account email and API access token available for Home Assistant setup.

Do not commit your email address, API token, or Home Assistant secrets to GitHub.

## Install With HACS

This integration is installed as a custom HACS repository.

1. In Home Assistant, open **HACS**.
2. Open the HACS menu and choose **Custom repositories**.
3. Add this repository URL:

   ```text
   https://github.com/burren2025/HAFullyCloudEMM
   ```

4. Select category **Integration**.
5. Click **Add**.
6. Search HACS for **Fully Cloud EMM**.
7. Download the latest stable release.
8. Restart Home Assistant.

## Configure In Home Assistant

After Home Assistant restarts:

1. Go to **Settings > Devices & services**.
2. Click **Add Integration**.
3. Search for **Fully Cloud EMM**.
4. Choose **Add cloud account**, **Add local device**, or **Add multiple local devices**.

Choose **Add cloud account** to enter your Fully Cloud account email and API access token. Once the cloud account is added, all Fully Cloud devices available to the API token are added to Home Assistant.

Choose **Add local device** for a Fully Kiosk tablet reachable from Home Assistant. Enter the IP address or host name, the Remote Admin port, and the Remote Admin password. The default port is `2323`.

HACS only installs the integration files. The email/API token or local device prompt appears when adding the integration from **Devices & services**, not during the HACS install step.

## Optional Local API

If a Fully Kiosk device is reachable on the same network as Home Assistant, you can add it directly from **Add Integration > Fully Cloud EMM > Add local device**. Fully Kiosk Remote Admin commonly listens on port `2323`. Enable Remote Admin on the tablet first and use the Remote Admin password from Fully Kiosk.

Cloud accounts can also add local endpoints from the integration **Configure** menu when you want cloud status plus local command routing for the same device.

Examples:

```text
192.168.1.50|remote_admin_password
http://192.168.1.50:2323|remote_admin_password
57626449-1551598e|192.168.1.50:2323|remote_admin_password
```

When a local endpoint matches a cloud device, the integration adds local `deviceInfo` fields under `local_device_info_*` entities and sends command actions through the local API for that device. Devices without a local endpoint continue to use Fully Cloud.

## Actions

Fully Cloud EMM provides these Home Assistant actions:

- `fully_cloud_emm.refresh`
- `fully_cloud_emm.refresh_device`
- `fully_cloud_emm.load_start_url`
- `fully_cloud_emm.load_url`
- `fully_cloud_emm.restart_app`
- `fully_cloud_emm.reboot_device`
- `fully_cloud_emm.screen_on`
- `fully_cloud_emm.screen_off`
- `fully_cloud_emm.start_screensaver`
- `fully_cloud_emm.stop_screensaver`
- `fully_cloud_emm.set_overlay_message`
- `fully_cloud_emm.start_application`
- `fully_cloud_emm.text_to_speech`
- `fully_cloud_emm.stop_text_to_speech`
- `fully_cloud_emm.set_audio_volume`

The device-targeted actions include a **Fully Cloud EMM devices** field in the automation UI. Select one or more friendly Home Assistant device names there, and the integration uses the Fully device ID internally.

The reboot command depends on Fully Kiosk device support and may require rooted/provisioned devices.

## Logging

Manual command actions log outcomes at `WARNING` level so they appear in the default Home Assistant Core log. Refresh actions and routine status polling are not logged on success.

If setup fails, Home Assistant logs a message starting with `Fully Cloud setup failed:` with the underlying connection or API response detail.

## Updates

Install updates from stable GitHub releases. After downloading an update in HACS, restart Home Assistant so the updated integration code is loaded.
