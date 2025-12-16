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

## Silero VAD (Real-time Voice Activity Detection)

- Purpose: add a lightweight, high-quality VAD to detect speech segments in real-time and emit compact speech/no-speech events (not raw audio). We recommend using the Silero VAD model from `snakers4/silero-vad` (PyTorch hub) to detect speech on the Pi/aggregator or on a transient edge host.

- Where to run (options):
  - On the Pi Aggregator (recommended): run VAD close to the audio ingress (serial WAV capture, USB microphone, or short PCM chunks from ESP32) and publish boolean/segment events to MQTT. Keeps raw audio local and minimizes downstream bandwidth and privacy exposure.
  - On a dedicated edge worker (for CPU / thermal isolation): run VAD in a container on a nearby machine and publish events to the same MQTT topics.
  - On-device (ESP32): not recommended for Silero (PyTorch dependency and compute cost). For microcontroller-only VAD, consider WebRTC VAD or simple energy-based heuristics.

- Dependencies & install notes:
  - Requires PyTorch and torchaudio (CPU builds are fine). Example (x86/arm):
    - pip install torch torchaudio numpy
    - Use torch.hub to load model: `torch.hub.load('snakers4/silero-vad', 'silero_vad', force_reload=False)`
  - On Raspberry Pi, follow PyTorch's Pi-specific install instructions or use a prebuilt wheel for the target OS.

- Real-time pipeline (high level):
  1. Capture short PCM frames (e.g., 30-500 ms) at 16 kHz mono.
  2. Buffer frames into overlapping windows and feed them into Silero utils (`get_speech_timestamps`, `VADIterator`) for smoothing and detection.
  3. When a speech segment is detected, publish a compact event to MQTT (see topic/payload below).
  4. Optionally emit boundary events (speech_start/speech_end) and aggregated speech activity percentages for the current profile window (used by `pi-decision`).

- Example MQTT topics & payloads:
  - `classroom/<room_id>/pi/aggregator/vad` — speech segment summary
    ```json
    {
      "timestamp": "2025-12-16T12:00:00Z",
      "device_id": "aggregator1",
      "speech": true,
      "start_ms": 1234,
      "end_ms": 2345,
      "confidence": 0.93,
      "sample_rate": 16000,
      "source": "silero_vad_v0"
    }
    ```
  - `classroom/<room_id>/pi/aggregator/vad_event` — discrete start/end event
    ```json
    {"timestamp":"2025-12-16T12:00:00Z","device_id":"aggregator1","event":"speech_start","source":"silero_vad_v0"}
    ```

- Implementation tips & tuning:
  - Use 16 kHz PCM input for best model compatibility (resample if necessary).
  - Silero VAD requires exactly 512 samples per chunk for 16kHz (32ms), or 256 for 8kHz.
  - Use `VADIterator` or custom hysteresis to reduce choppy toggles (silero utils provide smoothing helpers).
  - Emit both per-window speech fraction (for `noise_profile`) and boundary events (for UI/actuation triggers).

- Testing & Simulation:
  - Reuse `scripts/publish_sample.py` to stream prerecorded speech/non-speech WAVs into the VAD pipeline for unit/integration tests.
  - Add unit tests that validate VAD outputs against known sample timestamps and ensure MQTT message schemas (`shared/mqtt/schemas`) reflect vad events where applicable.

- Privacy & Security:
  - Do not publish or persist raw audio unless explicitly required and consented to; send only compact metadata (timestamps, speech flag, confidence).
  - Run models locally (on-Pi) to avoid transmitting raw audio to cloud services.

- Next steps / integration checklist:
  - [x] Add lightweight VAD service in `pi-aggregator/` (e.g., `pi-aggregator/vad.py`) with configuration hooks.
  - [ ] Add VAD-based fields to `pi/aggregator/noise_profile` (e.g., `speech_fraction`, `last_speech_ts`).
  - [ ] Add unit/integration tests and a sample dataset for VAD (use `peaks/` or a new `test_data/` folder).
  - [ ] Document dependency installation in `README.md` and/or `pyproject.toml` extras.

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

## WAV File Streaming Over Serial (WORKING — sampling issue in progress)

### Objective
Stream 16-bit mono PCM audio recorded on the ESP32 to a computer via USB serial connection as a binary WAV file, bypassing MQTT for direct offline recording.

### Implementation Status: **WORKING (I2S MEMS Mic Configured)**

**ESP32 Firmware (`arduino/mictest/src/main.cpp`):**
- Streams binary WAV file over serial at **921600 baud** (increased from 115200 to prevent buffer overflows)
- Uses I2S peripheral for high-quality audio capture from Fermion I2S MEMS Mic
- WAV header (44 bytes) sent first, followed by audio samples (2 bytes each, 16-bit little-endian)
- Recording duration: 10 seconds (configurable via `RECORDING_TIME_SEC`)
- **Trigger Mechanism**: Waits for serial byte 'G' before starting recording to ensure sync

**Python Capture Script (`scripts/capture_wav.py`):**
- Opens serial port at **921600 baud**
- Sends trigger byte 'G' to start recording
- Searches incoming stream for RIFF signature (0x52494646)
- Reads complete 44-byte WAV header
- Extracts audio data size from header
- Streams remaining audio samples to file with progress indicator
- Validates WAV format before writing
- Output: Valid 16kHz 16-bit mono PCM WAV file

**Current Status: WORKING (I2S Audio Capture + Serial Streaming)**
- **Hardware**: Fermion I2S MEMS Microphone (SCK=25, WS=16, SD=26, SEL=2)
- **Configuration**: Stereo Mode (Right+Left), extracting Right channel (SEL=HIGH)
- **Gain**: 16x digital gain applied (bit shift `>> 12`)
- **Fixes Applied**:
  - **Silent Audio**: Fixed by using `I2S_CHANNEL_FMT_RIGHT_LEFT` (Stereo) instead of `ONLY_RIGHT`.
  - **Repetition/Stutter**: Fixed by flushing I2S DMA buffers (`i2s_zero_dma_buffer`) before recording.
  - **"Fast" Playback**: Identified as Serial bandwidth bottleneck (32kB/s audio > 11.5kB/s serial). **Fix: Increasing baud rate to 921600.**

**Key Challenges & Solutions:**

1. **Silent Audio with I2S Mic**:
   - **Issue**: `I2S_CHANNEL_FMT_ONLY_RIGHT` produced all zeros.
   - **Solution**: Switched to `I2S_CHANNEL_FMT_RIGHT_LEFT` (Stereo) and manually extracted the right channel sample from the interleaved buffer.

2. **"Test Test Test" Repetition**:
   - **Issue**: Old data in the DMA buffer was being read at the start of a new recording.
   - **Solution**: Added `i2s_zero_dma_buffer(I2S_PORT)` and a dummy read loop to flush the pipeline before starting capture.

3. **"Fast" Audio (Time Compression)**:
   - **Issue**: Audio played at correct pitch but sounded "rushed" or "fast".
   - **Cause**: Serial baud rate (115200) was too slow for 16kHz 16-bit audio (32kB/s). The blocking `Serial.write` caused the I2S buffer to overflow, dropping chunks of time.
   - **Solution**: Increase Serial baud rate to **921600** (approx 92kB/s capacity).

**Usage:**

1. **Flash ESP32:**
   ```bash
   cd arduino/mictest
   pio run -t upload --upload-port /dev/tty.wchusbserial550D0193611
   ```

2. **Capture Recording:**
   ```bash
   uv run scripts/capture_wav.py /dev/tty.wchusbserial550D0193611 recording.wav
   ```


**Output Specifications:**
- **Format**: WAV (RIFF), Microsoft PCM
- **Sample Rate**: 16000 Hz
- **Bit Depth**: 16-bit
- **Channels**: Mono (1)
- **Duration**: 10 seconds
- **File Size**: 320,044 bytes (44-byte header + 320,000 bytes audio data)

### Hardware Setup
- **ESP32**: WROOM-32 dev board
- **Microphone**: MAX4466 electret mic amplifier → GPIO 35 (ADC1_CH7)
- **USB Serial**: CH340 USB-to-serial adapter @ 115200 baud
- **Power**: USB 5V
- **Recording Parameters**: 16 kHz sample rate, 16-bit depth, mono, 10 second duration

## Contribution & Roadmap

- Short-term:
  - ✅ **COMPLETED**: WAV streaming over serial (working end-to-end)
  - Improve ESP32 feature set (band energies via lightweight FFT for MQTT mode)
  - Implement robust MQTT reconnect and NTP time sync
  - Add unit & integration tests, and a Docker Compose for local CI
- Mid-term:
  - Implement model evaluation suite and automated retraining pipeline
  - Add secure deployment artifacts (systemd unit files, certificate management)
  - Add SD card support for offline recording without computer connection
  - Implement battery power mode with deep sleep between recordings

**Completed Features:**
- ✅ Serial WAV streaming (ESP32 → Computer via USB)
- ✅ Real-time ADC audio capture at 16 kHz
- ✅ Python capture script with progress reporting
- ✅ Valid WAV file output (tested and verified)

**Next Priorities:**
1. Integrate timer-based interrupts for more precise sampling (optional enhancement)
2. Add audio analysis features (RMS, peak detection, frequency bands)
3. Implement MQTT publishing of audio features alongside serial capture
4. Build ML model training pipeline for noise classification

