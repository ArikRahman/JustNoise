# AGENTS (Comprehensive)

## Overview
Classroom Occupancy and Noise Analytics is an integrated IoT + ML system that senses classroom audio, occupancy, and basic environmental signals, builds a rolling "noise profile", and issues automated actuation commands (speaker volume/EQ, display feedback) to improve acoustics and user awareness.

This document consolidates the project design, messaging schemas, development workflows, deployment guidance, and data/ML conventions so contributors and system integrators have a single source of truth.

Key components (reference implementation in this repo):
- `esp32/firmware` — PlatformIO sketch and firmware for the ESP32 sensor nodes.
- `pi-aggregator` — Aggregator service that subscribes to sensor features, maintains noise profiles, and publishes derived metadata.
- `pi-decision` — Decision node that consumes profiles and issues actuation commands; includes training utilities.
- `shared/mqtt/schemas` — JSON Schema files and topic conventions.
- `scripts/publish_sample.py` — Simulator that publishes sample messages to MQTT for testing.

## Architecture and Data Flow

1. ESP32 nodes collect sensor data (audio features, PIR, temperature/humidity) and publish compact JSON messages to MQTT topics.
2. The Aggregator subscribes to audio features and produces a rolling noise profile (summaries like mean/max RMS over a window). It publishes `pi/aggregator/noise_profile` messages.
3. The Decision node subscribes to noise profiles (and optionally raw features) and runs a model/heuristic to produce actuation commands published to `pi/decision/actuation/*` topics.
4. Actuated endpoints (speaker controller, classroom display) subscribe to actuation topics to perform volume/EQ adjustments or show UI feedback.

Design goals:
- Minimize transmission of raw audio; send derived features (RMS, peak, band energies).
- Keep messages small and schema-driven with JSON Schema for validation.
- Provide reproducible training and evaluation pipelines for model development.

## MQTT Topics & Examples

Topic naming convention: `classroom/<room_id>/...`

Core topics used by the reference implementation:
- `classroom/<room_id>/esp32/<node_id>/audio/features` — per-window audio features
- `classroom/<room_id>/esp32/<node_id>/pir` — motion detections
- `classroom/<room_id>/esp32/<node_id>/env` — temperature/humidity
- `classroom/<room_id>/pi/aggregator/noise_profile` — profile summaries (aggregated)
- `classroom/<room_id>/pi/decision/actuation/speaker` — speaker actuation commands
- `classroom/<room_id>/pi/decision/actuation/display` — display/feedback commands

Example payloads

Audio features (`audio/features`):
```
{
  "timestamp": "2025-12-15T12:34:56Z",
  "device_id": "node1",
  "sample_window_ms": 100,
  "rms_db": -32.5,
  "peak_db": -25.0,
  "band_energies": [-40.2, -35.1, -38.9]
}
```

PIR (`pir`):
```
{
  "timestamp": "2025-12-15T12:34:57Z",
  "device_id": "node1",
  "motion": true
}
```

Environment (`env`):
```
{
  "timestamp": "2025-12-15T12:34:57Z",
  "device_id": "node1",
  "temperature_c": 22.1,
  "humidity_pct": 44.3
}
```

Noise profile (`pi/aggregator/noise_profile`):
```
{
  "timestamp": "2025-12-15T12:35:00Z",
  "profile": {"count": 12, "mean_rms_db": -35.2, "max_rms_db": -28.3}
}
```

Actuation command (`pi/decision/actuation/speaker`):
```
{
  "timestamp": "2025-12-15T12:35:01Z",
  "action": "set_volume",
  "level": 0.65,
  "confidence": 0.92,
  "source": "random_forest_v0"
}
```

JSON Schema files are in `shared/mqtt/schemas`. Keep schemas in sync with any changes to the produced payloads.

## Device (ESP32) responsibilities

- Interface with sensors: MAX4466 microphone (ADC), HC-SR501 PIR (digital), AHT10 (I2C) or equivalent.
- Produce features locally: RMS, peak, optional band energies (lightweight FFT), and publish periodically (e.g., every 1-5s for audio features; env every 30-60s; PIR on change).
- Publish messages using stable `classroom/<room_id>/esp32/<node_id>/...` topics.
- Implement minimal buffering and retries for MQTT connectivity loss; record local diagnostics for offline debugging.

Reference: `esp32/firmware` contains a PlatformIO sketch with an example implementation (RMS computation + messages published). There is also an Arduino example (`arduino/sketch_oct24a`) that demonstrates subscribing and displaying messages on a TFT.

## Aggregator (Pi) responsibilities

- Subscribe to audio features from all nodes in a room.
- Maintain a rolling window (default 60s) and compute summary statistics (mean/max/min RMS) and derived signals for model training.
- Publish `pi/aggregator/noise_profile` summaries at a configurable interval.
- Optionally persist anonymized summaries for later training (keep raw audio off-network when possible).

Reference implementation: `pi-aggregator/aggregator.py`.

## Decision Node (Pi) responsibilities

- Subscribe to noise profiles and any additional signals (PIR, env).
- Run model (or heuristic fallback) to compute actuation commands.
- Publish actuation commands to `pi/decision/actuation/*` topics.
- Provide a training script and a model format (e.g., `joblib` for scikit-learn) for reproducibility.

Reference implementation: `pi-decision/decision.py`, training helper `pi-decision/train.py`.

Model & training conventions

- Start with RandomForestRegressor (baseline) that maps profile features (e.g., mean_rms_db) to a target noisiness score or target volume level.
- Training data format (CSV):
  - timestamp, device_id, mean_rms_db, max_rms_db, target_noisiness
- Version models and store metadata (training dataset, hyperparameters, evaluation metrics) alongside the serialized model file (`model.joblib`).

Evaluation metrics

- Track mean absolute error (MAE), root mean squared error (RMSE), and a simple policy-simulated metric: how often model decisions reduce measured noise in a subsequent window.

## Testing & Simulation

- Use `scripts/publish_sample.py` to simulate ESP32 messages for development and unit testing of aggregator/decision pipelines.
- Unit tests for Python services should validate schema conformance, edge conditions (empty windows), and actuation mapping behavior.
- Consider a Docker Compose setup for CI that brings up an MQTT broker (e.g., Eclipse Mosquitto) and runs integration tests.

## Security & Privacy

- Minimize storing raw audio; prefer derived features and short retention of any sensitive recordings.
- Use TLS for MQTT in production and authenticated brokers.
- Limit data retention and provide clear policies for model/data export, especially when used in real classrooms.

## Deployment & Operations

- For local development: install Mosquitto, run aggregator and decision scripts, and use the simulator to publish mock data.
- For production: run aggregator and decision on dedicated Raspberry Pi devices, enable systemd services, monitor MQTT throughput, and ensure disk rotation for any persisted logs.

Quick start (developer):
1. Install MQTT broker (mosquitto) and start it: `brew install mosquitto && mosquitto` (macOS) or use your distro package.
2. Start aggregator: `python3 pi-aggregator/aggregator.py`
3. Start decision node: `python3 pi-decision/decision.py`
4. Publish simulated data: `python3 scripts/publish_sample.py`

## Hardware & Wiring notes

- MAX4466: connect output to ADC pin, set proper gain on breakout, add biasing as needed.
- PIR HC-SR501: digital input with stable power and appropriate timeout/trigger configuration.
- AHT10: I2C SDA/SCL to ESP32 I2C pins; ensure proper pull-ups.

## Contribution & Roadmap

- Short-term:
  - Improve ESP32 feature set (band energies via lightweight FFT), implement robust MQTT reconnect and NTP time sync.
  - Add unit & integration tests, and a Docker Compose for local CI.
- Mid-term:
  - Implement model evaluation suite and automated retraining pipeline.
  - Add secure deployment artifacts (systemd unit files, certificate management).

If you want, I can implement any of the next steps (ESP32 FFT features, add MQTT TLS config, Docker Compose + CI, or model evaluation and retraining). Tell me which to do next.

