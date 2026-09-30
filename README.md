# LEGO Mario Home Assistant Integration

This integration connects LEGO Mario / Luigi / Peach to Home Assistant via Bluetooth (BLE).

## Features
- Scan & Auto-discovery via HA Bluetooth
- Sensor for Scanned Barcodes / Colors
- Sensor for Pants Type
- Binary Sensor for BLE Connection status
- Fires `lego_mario_scanned` events for Home Assistant Automations

## Installation via HACS
1. Open HACS in Home Assistant.
2. Click on the 3 dots in the top right corner and select **Custom repositories**.
3. Add the URL of this repository, select **Integration** as the category.
4. Click **Download**.
5. Restart Home Assistant.
