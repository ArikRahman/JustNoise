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
- Pi components: Create a Python virtual environment and install requirements in `pi-aggregator/requirements.txt` and `pi-decision/requirements.txt`.

Local test (no hardware):
- Run a local MQTT broker (mosquitto): `brew install mosquitto` then `mosquitto`.
- In one terminal run the aggregator: `python3 pi-aggregator/aggregator.py`.
- In another terminal run the decision node: `python3 pi-decision/decision.py`.
- Use the included simulator to publish sample ESP32 messages: `python3 scripts/publish_sample.py`.
