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
- Send selected Fully Cloud commands from Home Assistant actions:
  - Restart Fully Kiosk app
  - Reboot device
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
4. Enter your Fully Cloud account email.
5. Enter your Fully Cloud API access token.
6. Submit the form.

HACS only installs the integration files. The email/API token prompt appears when adding the integration from **Devices & services**, not during the HACS install step.

## Actions

Fully Cloud EMM provides these Home Assistant actions:

- `fully_cloud_emm.refresh`
- `fully_cloud_emm.refresh_device`
- `fully_cloud_emm.restart_app`
- `fully_cloud_emm.reboot_device`

The device-targeted actions include a **Fully Cloud EMM devices** field in the automation UI. Select one or more friendly Home Assistant device names there, and the integration uses the Fully device ID internally.

The reboot command depends on Fully Kiosk device support and may require rooted/provisioned devices.

## Logging

Manual command actions and device-targeted refreshes log outcomes at `WARNING` level so they appear in the default Home Assistant Core log. Routine hourly status polling is not logged on success.

If setup fails, Home Assistant logs a message starting with `Fully Cloud setup failed:` with the underlying connection or API response detail.

## Updates

For production Home Assistant instances, install stable GitHub releases only. Beta releases are published as GitHub pre-releases and should be tested in a separate Home Assistant instance before production use.
