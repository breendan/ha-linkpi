# LinkPi HDMI Encoder – Home Assistant Custom Integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-blue.svg)](https://hacs.xyz/)
[![Release](https://img.shields.io/github/v/release/breendan/ha-linkpi?sort=semver)](https://github.com/breendan/ha-linkpi/releases)
[![Downloads](https://img.shields.io/github/downloads/breendan/ha-linkpi/total.svg)](https://github.com/breendan/ha-linkpi/releases)
[![Last Commit](https://img.shields.io/github/last-commit/breendan/ha-linkpi.svg)](https://github.com/breendan/ha-linkpi/commits)
[![License](https://img.shields.io/github/license/breendan/ha-linkpi.svg)](LICENSE)

Monitor basic system, network, and video input state from a LinkPi HDMI Encoder device inside Home Assistant.

## Features

- System metrics:
  - CPU usage
  - Memory usage
  - Core temperature
- Network metrics:
  - TX / RX rate
- Video input availability sensors (one entity per channel)
- Config Flow (UI) based setup
- Adjustable polling interval via Options Flow
- Auto re‑login & digest authentication handling
- Graceful session recovery on timeout/401

## Installation

### HACS
1. Add this repository as a custom repository in HACS
2. Install “LinkPi HDMI Encoder”.
3. Restart Home Assistant.
4. Add the integration via: Settings → Devices & Services → “+” → Search for “LinkPi”.

### Manual
1. Copy `custom_components/linkpi/` into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.
3. Add the integration through the UI (Config Flow).

## Configuration (UI)
Fields:
- Host: The IP or hostname of the LinkPi device.
- Username / Password: Credentials used in the web interface.

## Options
After setup, open the integration’s options to adjust:
- Scan interval (seconds, 10–3600)

## Entities

| Entity Name Pattern | Description |
|---------------------|-------------|
| `sensor.linkpi_encoder_cpu_usage` | CPU usage (%) |
| `sensor.linkpi_encoder_memory_usage` | Memory usage (%) |
| `sensor.linkpi_encoder_core_temperature` | Core temp (°C) |
| `sensor.linkpi_encoder_network_tx_rate` | Network TX rate (kbps) |
| `sensor.linkpi_encoder_network_rx_rate` | Network RX rate (kbps) |
| `sensor.linkpi_<input_name>_(chnX)` | Video input availability (on/off) |

Each video input entity exposes additional attributes such as protocol, resolution, etc. (depends on device response).


## License

Released under the MIT License (see LICENSE).

## Disclaimer

This integration is not affiliated with or endorsed by the LinkPi vendor. Use at your own risk.
