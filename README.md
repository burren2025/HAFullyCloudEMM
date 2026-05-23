# Fully Cloud EMM for Home Assistant

Custom Home Assistant integration for Fully Cloud EMM device status.

The integration connects to the Fully Cloud REST API and creates Home Assistant entities from the device information returned for every device available to the configured API token.

## Current Scope

- Config flow setup with Fully Cloud account email and REST API access token.
- Polls `https://api.fully-kiosk.com/cloud/devices`.
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

## Notes

Fully Cloud API credentials are entered through the Home Assistant config flow and stored by Home Assistant in its private config entry storage. Do not commit API keys, email addresses, or local Home Assistant secret files.

