# Fully Cloud EMM for Home Assistant

Custom Home Assistant integration for Fully Cloud EMM device status.

The integration connects to the Fully Cloud REST API and creates Home Assistant entities from the device information returned for every device available to the configured API token.

## Current Scope

- Config flow setup with Fully Cloud account email and REST API access token.
- Polls `https://api.fully-kiosk.com/cloud/devices` once per hour by default.
- Provides a `fully_cloud_emm.refresh` service for manual or automation-triggered refreshes.
- Provides actions to restart the Fully Kiosk app or reboot selected devices.
- Creates binary sensors for boolean fields.
- Creates sensors for scalar text and numeric fields.
- Flattens nested JSON fields so detailed heartbeat values can become Home Assistant entities.
- Does not store credentials in the repository.

## HACS Development Install

1. Push this repository to GitHub.
2. In HACS, add the repository as a custom repository with category `Integration`.
3. Install `Fully Cloud EMM`.
4. Restart Home Assistant.
5. Go to **Settings > Devices & services > Add Integration** and search for **Fully Cloud EMM**.

HACS only downloads the integration files. It will not ask for the Fully Cloud email or API token during install. That prompt appears when adding the integration from **Settings > Devices & services** after Home Assistant has restarted.

If **Fully Cloud EMM** does not appear in the add integration dialog after restart, check that Home Assistant has this directory:

```text
custom_components/fully_cloud_emm/
```

Then check **Settings > System > Logs** for startup errors mentioning `fully_cloud_emm`.

During setup, a failed credential test will log a line starting with `Fully Cloud setup failed:`. That line should show whether Home Assistant received an HTTP error, a non-JSON response, a timeout, or a network connection error.

## Refresh Interval

Fully Cloud EMM refreshes device data once per hour by default.

To refresh more frequently, create a Home Assistant automation that calls the `fully_cloud_emm.refresh` action on your preferred schedule.

## Device Actions

Fully Cloud EMM provides these Home Assistant actions:

- `fully_cloud_emm.restart_app`
- `fully_cloud_emm.reboot_device`

Both actions include a **Fully Cloud EMM devices** field in the automation UI. Select one or more friendly Home Assistant device names there, and the integration uses the Fully device ID internally when it sends the command.

The reboot command depends on Fully Kiosk device support and may require rooted/provisioned devices.

## Notes

Fully Cloud API credentials are entered through the Home Assistant config flow and stored by Home Assistant in its private config entry storage. Do not commit API keys, email addresses, or local Home Assistant secret files.
