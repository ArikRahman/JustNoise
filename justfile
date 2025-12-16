# JustNoise - Quick Commands
# Install just: brew install just
# Run: just <command>

# Default recipe - show available commands
default:
    @just --list

# Serial port configuration (macOS CH340 adapter)
serial_port := "/dev/tty.wchusbserial550D0193611"

# Flash the WAV recorder firmware to ESP32
flash:
    @echo "📦 Flashing ESP32 with WAV recorder firmware..."
    cd arduino/mictest && pio run -t upload --upload-port {{serial_port}}
    @echo "✅ Firmware flashed successfully"

# Record audio to a file (auto-generates timestamped filename)
record output="recording.wav":
    @echo "🎙️  Recording audio from ESP32..."
    @echo "💡 Make some noise near the microphone!"
    uv run scripts/capture_wav.py {{serial_port}} {{output}}
    @echo "✅ Recording saved to {{output}}"

# Record with timestamp in filename
record-now:
    #!/usr/bin/env bash
    timestamp=$(date +"%Y%m%d_%H%M%S")
    filename="recordings/recording_${timestamp}.wav"
    mkdir -p recordings
    echo "🎙️  Recording to ${filename}..."
    uv run scripts/capture_wav.py {{serial_port}} ${filename}
    echo "✅ Recording saved!"
    ls -lh ${filename}

# Play the most recent recording (macOS)
play file="recording.wav":
    @echo "🔊 Playing {{file}}..."
    afplay {{file}}

# Play the most recent timestamped recording
play-last:
    #!/usr/bin/env bash
    latest=$(ls -t recordings/recording_*.wav 2>/dev/null | head -1)
    if [ -z "$latest" ]; then
        echo "❌ No recordings found in recordings/"
        exit 1
    fi
    echo "🔊 Playing ${latest}..."
    afplay "$latest"

# Analyze WAV file properties
info file="recording.wav":
    @echo "📊 WAV File Info: {{file}}"
    @file {{file}}
    @uv run python3 -c "import wave; w=wave.open('{{file}}','r'); print(f'Channels: {w.getnchannels()}'); print(f'Sample rate: {w.getframerate()} Hz'); print(f'Sample width: {w.getsampwidth()} bytes'); print(f'Frames: {w.getnframes()}'); print(f'Duration: {w.getnframes()/w.getframerate():.1f}s'); w.close()"

# Clean up old recordings
clean-recordings:
    @echo "🗑️  Removing all recordings..."
    rm -f recordings/recording_*.wav recording*.wav
    @echo "✅ Cleaned up"

# Setup: Install dependencies
setup:
    @echo "📦 Setting up project dependencies..."
    uv sync
    @echo "✅ Dependencies installed"

# Monitor serial output (for debugging)
monitor:
    @echo "👀 Monitoring serial port {{serial_port}}..."
    @echo "Press Ctrl+C to stop"
    cd arduino/mictest && pio device monitor --port {{serial_port}} --baud 115200

# Check if ESP32 is connected
check:
    @echo "🔍 Checking for ESP32..."
    @ls -la {{serial_port}} 2>/dev/null && echo "✅ ESP32 found at {{serial_port}}" || echo "❌ ESP32 not found at {{serial_port}}"

# Run MQTT aggregator (for MQTT mode)
aggregator:
    @echo "🔄 Starting MQTT aggregator..."
    uv run pi-aggregator/aggregator.py

# Run MQTT decision node (for MQTT mode)
decision:
    @echo "🤖 Starting decision node..."
    uv run pi-decision/decision.py

# Run MQTT simulator (for testing without hardware)
simulate:
    @echo "🎭 Publishing simulated sensor data..."
    uv run scripts/publish_sample.py
