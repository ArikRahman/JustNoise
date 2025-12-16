# JustNoise

Classroom Occupancy and Noise Analytics

This project contains firmware and software for an IoT system that senses classroom audio, occupancy and environment, builds a noise profile, and issues actuation decisions.

**NEW: WAV Audio Recording Over Serial** - The ESP32 can now record 10-second WAV files and stream them directly to your computer over USB. See the "WAV Recording" section below.

**NEW: Real-time Voice Detection** - Silero VAD integration for live speech detection with visual CLI monitor. See the "Voice Activity Detection" section below.

See `AGENTS.md` for complete project details.

## Directories
- `esp32/firmware`: PlatformIO project for ESP32 sensor node firmware (MQTT mode).
- `arduino/mictest`: Simplified ESP32 sketch for WAV file recording over serial.
- `pi-aggregator`: Raspberry Pi aggregator code that maintains noise profiles and publishes metadata.
- `pi-decision`: Raspberry Pi decision node with ML model to predict noisiness and publish actuation commands.
- `shared`: Shared MQTT topics and schemas and utilities.
- `scripts`: Helper scripts including WAV capture utility.

## WAV Recording (Serial Mode)

### Quick Start

1. **Hardware Setup:**
   - Connect MAX4466 microphone to ESP32 GPIO 35
   - Connect ESP32 to computer via USB

2. **Flash Firmware:**
   ```bash
   cd arduino/mictest
   pio run -t upload --upload-port /dev/tty.wchusbserial550D0193611  # macOS
   # or /dev/ttyUSB0 on Linux
   ```

3. **Capture Audio:**
   ```bash
   uv run scripts/capture_wav.py /dev/tty.wchusbserial550D0193611 recording.wav
   ```

4. **Play Recording:**
   ```bash
   afplay recording.wav  # macOS
   # or aplay recording.wav on Linux
   ```

### Output
- **Format**: 16-bit mono PCM WAV
- **Sample Rate**: 16 kHz
- **Duration**: 10 seconds
- **File Size**: ~320 KB

The ESP32 continuously loops, sending a new recording every 12 seconds. The Python script automatically finds the WAV header in the stream and captures the audio data.

## Voice Activity Detection (VAD)

Real-time speech detection using Silero VAD, perfect for detecting when someone is talking in a classroom.

### Quick Start

1. **Install VAD dependencies:**
   ```bash
   just setup-vad  # Installs PyTorch + Silero VAD
   ```

2. **Test installation:**
   ```bash
   just test-vad
   ```

3. **Live vocal monitoring (CLI debugger):**
   ```bash
   # Single recording (10 seconds)
   just vad-monitor
   
   # Continuous mode (loops indefinitely)
   just vad-monitor-continuous
   ```
   
   This displays **real-time visual alerts** when vocals are detected:
   - 🔴 **Big alerts** when speech starts
   - 🟢 Notification when speech ends
   - **Progress bars** showing confidence during speech
   - **Session summary** with statistics
   - 🔄 **Continuous mode** keeps monitoring across multiple recordings
   
   Example output:
   ```
   🗣️  🗣️  🗣️  🗣️  🗣️  🗣️  🗣️  🗣️  🗣️  🗣️  
   [12:34:56.789] 🔴 VOCALS DETECTED - SPEECH STARTED!
   🗣️  🗣️  🗣️  🗣️  🗣️  🗣️  🗣️  🗣️  🗣️  🗣️  
   
   🔴 SPEECH [████████████████████░░░░░░░░░░░░░░░░] 65.3%
   ```

4. **MQTT mode (production):**
   ```bash
   just vad-live  # Publishes events to MQTT
   ```

### Features
- ✅ **Privacy-first**: No raw audio transmitted, only metadata
- ✅ **Low latency**: ~32ms detection delay
- ✅ **Accurate**: Silero VAD model (state-of-the-art)
- ✅ **Visual feedback**: CLI monitor for debugging

See `pi-aggregator/VAD_README.md` for complete documentation.

## MQTT Mode (IoT System)

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
