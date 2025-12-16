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

## WAV File Streaming Over Serial (WORKING — sampling issue in progress)

### Objective
Stream 16-bit mono PCM audio recorded on the ESP32 to a computer via USB serial connection as a binary WAV file, bypassing MQTT for direct offline recording.

### Implementation Status: **WORKING (streaming OK, sample-rate/pitch issue being debugged)**

**ESP32 Firmware (`arduino/mictest/src/main.cpp`):**
- Streams binary WAV file over serial at 115200 baud
- WAV header (44 bytes) sent first, followed by audio samples (2 bytes each, 16-bit little-endian)
- Recording duration: 10 seconds (configurable via `RECORDING_TIME_SEC`)
- Total file size: ~320 KB per recording
- Continuously loops: sends new recording every 12 seconds (10s record + 2s pause)

**Python Capture Script (`scripts/capture_wav.py`):**
- Opens serial port at 115200 baud
- Searches incoming stream for RIFF signature (0x52494646)
- Reads complete 44-byte WAV header
- Extracts audio data size from header
- Streams remaining audio samples to file with progress indicator
- Validates WAV format before writing
- Output: Valid 16kHz 16-bit mono PCM WAV file

**Current Status: WORKING (binary streaming/capture functional; recorded audio shows octave-up pitch / sample-rate mismatch)**
- Firmware compiles and uploads successfully (recent builds ~280 KB binary)
- Serial communication verified and stable
- WAV header correctly constructed with byte-by-byte manual assembly
- RIFF signature reliably detected in stream
- Complete 10-second recordings successfully captured (test files: `recording_timer.wav`, `recording_exact16k.wav`, `recording_31ticks.wav`)
- Recorded audio is intelligible, but currently pitched an octave high (indicative of recording at ~8 kHz while header claims 16 kHz)

**Key Challenges, Current Findings & Plan:**

1. **Binary vs. Text Mixing**: Early attempts mixed Serial.println() debug output with binary data, corrupting the stream.
  - ✓ **Solution**: Removed all text output; now sends pure binary header + samples.

2. **Header Initialization**: C++ struct initialization with member initializers was unreliable for binary transmission.
  - ✓ **Solution**: Manually build WAV header byte-by-byte with explicit bit-shifting for endianness.

3. **Serial Synchronization**: Python capture script would timeout waiting for RIFF header because ESP32's loop() already sent data before script connected.
  - ✓ **Solution**: Script now continuously reads and searches for RIFF in buffer; no reset required.

4. **Serial Port Reset**: DTR/RTS control didn't work reliably on macOS with CH340 adapters.
  - ✓ **Solution**: Removed reset dependency; script polls for data and finds RIFF dynamically.

5. **Sample Rate Timing (previous)**: Initial implementation used delay() which was imprecise.
  - ✓ **Solution**: Implemented prior hardware-timed approach (micros() and busy-wait) and then moved to timer-alarm based sampling.

6. **Sample Rate / Pitch Mismatch (ONGOING)**: After switching to a hardware-timer-based sampling implementation the recordings are intelligible but still pitched an octave up (recorded sample rate appears to be roughly half of the declared 16 kHz).
  - **Observations so far**:
    - Replaced busy-wait with hardware timer (timerBegin + timerAlarmWrite) and tested multiple prescalers/tick values (2 MHz/125 ticks, 1 MHz/31 ticks, etc.).
    - Produced test recordings (`recording_timer.wav`, `recording_exact16k.wav`, `recording_31ticks.wav`) that consistently show octave-up pitch.
  - **Likely causes under investigation**:
    - Missed timer ticks: ISR currently sets a boolean flag; if the main loop's ADC read/Serial write can't keep up, multiple timer alarms may occur and samples are effectively skipped.
    - ADC read latency: `analogRead()` may be too slow to run in the main loop at 16 kHz, causing effective sample rate to drop.
    - Timer configuration semantics or interaction with other code paths causing effective period doubling.
  - **Immediate diagnostic / mitigation plan**:
    1. Add an instrumented "diagnostic mode" build that emits sampling telemetry (sample counts, measured elapsed micros between the first and last sample, missed-tick counters) as ASCII (no binary WAV) so we can reliably measure effective sample rate without having to parse binary.
    2. Replace the ISR flag (bool) with a counter (volatile uint32_t tickCount) to detect missed ticks; log tickCount after recording in diagnostic mode.
    3. If tick misses are observed, move ADC sample capture into the ISR (using the fastest ADC read path safe in ISR) or switch to the ESP32 I2S / ADC DMA capture mode to avoid software scheduling bottlenecks.
    4. Add a GPIO toggle test (pin toggle in ISR) so a scope or logic analyzer can confirm ISR frequency and compare to expected timer frequency.
  - **Acceptance criteria**: Recorded vocal audio plays at normal pitch (no octave shift), and measured sample count matches SAMPLE_RATE * RECORDING_TIME_SEC within a 1% tolerance.

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

3. **Verify WAV File:**
   ```bash
   file recording.wav
   # Output: RIFF (little-endian) data, WAVE audio, Microsoft PCM, 16 bit, mono 16000 Hz
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

