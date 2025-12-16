# JustNoise

Classroom Occupancy and Noise Analytics

This project contains firmware and software for an IoT system that senses classroom audio, occupancy and environment, builds a noise profile, and issues actuation decisions.

See `AGENTS.md` for project details.

Directories:
- `esp32/firmware`: PlatformIO project for ESP32 sensor node firmware.
- `pi-aggregator`: Raspberry Pi aggregator code that maintains noise profiles and publishes metadata.
- `pi-decision`: Raspberry Pi decision node with ML model to predict noisiness and publish actuation commands.
- `shared`: Shared MQTT topics and schemas and utilities.

Quick start (development):
- ESP32: Use PlatformIO to build and flash `esp32/firmware`.
- Python components: This project uses `uv` for dependency management.
  1. Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh` (or via brew/pip).
  2. Sync dependencies: `uv sync`.

Local test (no hardware):
- Run a local MQTT broker (mosquitto): `brew install mosquitto` then `mosquitto`.
- In one terminal run the aggregator: `uv run pi-aggregator/aggregator.py`.
- In another terminal run the decision node: `uv run pi-decision/decision.py`.
- Use the included simulator to publish sample ESP32 messages: `uv run scripts/publish_sample.py`.
