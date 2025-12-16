# JustNoise - Quick Commands
# Install just: brew install just
# Run: just <command>

# Default recipe - show available commands
default:
    @just --list

# Serial port configuration (macOS CH340 adapter)
serial_port := "/dev/tty.wchusbserial550D0193611"

# Flash the raw PCM streamer firmware to ESP32
flash:
    @echo "📦 Flashing ESP32 with raw PCM streamer firmware..."
    cd arduino/mictest && pio run -t upload --upload-port {{serial_port}}
    @echo "✅ Firmware flashed successfully"

# Stream raw PCM and run VAD (DEFAULT: 500ms grace period)
vad-stream:
    @echo "🎤 Starting raw PCM streamer with VAD (500ms grace period)..."
    @echo "💡 Speak near the microphone to see real-time detection!"
    @echo "💡 This gives a 500ms grace period for brief pauses/breathing"
    @echo ""
    @echo "Note: Make sure ESP32 firmware is flashed first (just flash)"
    @echo ""
    uv run scripts/vad_stream.py {{serial_port}} --min-silence 500

# Stream raw PCM with LESS sensitive VAD (longer grace period)
vad-stream-relaxed:
    @echo "🎤 Starting raw PCM streamer with VAD (1000ms grace period)..."
    @echo "💡 This is more forgiving - 1 second of silence before ending speech"
    @echo ""
    uv run scripts/vad_stream.py {{serial_port}} --min-silence 1000

# Stream raw PCM with MORE relaxed VAD (very long grace period)
vad-stream-very-relaxed:
    @echo "🎤 Starting raw PCM streamer with VAD (1500ms grace period)..."
    @echo "💡 This is VERY forgiving - 1.5 seconds of silence before ending speech"
    @echo ""
    uv run scripts/vad_stream.py {{serial_port}} --min-silence 1500

# Stream raw PCM with AGGRESSIVE VAD (shorter grace period)
vad-stream-aggressive:
    @echo "🎤 Starting raw PCM streamer with VAD (200ms grace period)..."
    @echo "💡 This is more sensitive - quick to detect speech boundaries"
    @echo ""
    uv run scripts/vad_stream.py {{serial_port}} --min-silence 200

# Stream raw PCM with CUSTOM VAD grace period
vad-stream-custom min_silence="1200":
    @echo "🎤 Starting raw PCM streamer with VAD ({{min_silence}}ms grace period)..."
    @echo "💡 Custom grace period: {{min_silence}}ms"
    @echo ""
    uv run scripts/vad_stream.py {{serial_port}} --min-silence {{min_silence}}

# Capture raw PCM stream to audio files (time-based splitting)
capture-pcm:
    @echo "🎙️  Capturing raw PCM to audio files..."
    @echo "💡 Each file is 60 seconds (Press Ctrl+C to stop)"
    @echo ""
    @echo "Note: Make sure ESP32 firmware is flashed first (just flash)"
    @echo ""
    uv run scripts/capture_pcm.py {{serial_port}}

# Capture PCM with custom duration per file
capture-pcm-duration duration="300":
    @echo "🎙️  Capturing raw PCM to audio files ({{duration}}s each)..."
    @echo "💡 Press Ctrl+C to stop"
    @echo ""
    uv run scripts/capture_pcm.py {{serial_port}} --duration {{duration}}

# Capture PCM with VAD-based file splitting (on speech boundaries)
capture-pcm-vad:
    @echo "🎤 Capturing PCM with VAD-based splitting..."
    @echo "💡 Files are split on speech boundaries (Press Ctrl+C to stop)"
    @echo ""
    @echo "Note: Requires VAD support - run 'just setup-vad' first"
    @echo ""
    uv run scripts/capture_pcm.py {{serial_port}} --mode vad

# Capture PCM with size-based file splitting
capture-pcm-size:
    @echo "🎙️  Capturing PCM with size-based splitting..."
    @echo "💡 Files split at 1 MB each (Press Ctrl+C to stop)"
    @echo ""
    uv run scripts/capture_pcm.py {{serial_port}} --mode size

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

# Setup with VAD support (installs PyTorch for Silero VAD)
setup-vad:
    @echo "📦 Setting up project with VAD support..."
    uv sync --extra vad
    @echo "✅ Dependencies installed (including PyTorch for VAD)"

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

# Run VAD from live serial stream
vad-live:
    @echo "🎤 Starting live Voice Activity Detection from ESP32..."
    uv run pi-aggregator/vad.py --serial {{serial_port}}

# Run VAD on a WAV file (for testing)
vad-test file="recording.wav":
    @echo "🎤 Running Voice Activity Detection on {{file}}..."
    uv run pi-aggregator/vad.py --file {{file}}

# Test VAD installation
test-vad:
    @echo "🧪 Testing Silero VAD installation..."
    uv run scripts/test_vad.py

# Monitor live vocals from ESP32 (CLI debugger)
vad-monitor:
    @echo "🎧 Starting live vocal monitor..."
    @echo "💡 Speak near the microphone to see real-time detection!"
    @echo ""
    @echo "Note: Make sure ESP32 firmware is flashed first (just flash)"
    @echo ""
    uv run scripts/vad_monitor.py {{serial_port}}

# Monitor vocals continuously (loops indefinitely)
vad-monitor-continuous:
    @echo "🔄 Starting CONTINUOUS vocal monitor..."
    @echo "💡 Monitoring will loop indefinitely - Press Ctrl+C to stop"
    @echo ""
    @echo "Note: Make sure ESP32 firmware is flashed first (just flash)"
    @echo ""
    uv run scripts/vad_monitor.py {{serial_port}} --continuous

# Flash ESP32 and stream raw PCM (convenience command)
flash-and-stream: flash
    @echo ""
    @echo "✅ Firmware flashed! Starting raw PCM stream with VAD in 2 seconds..."
    @sleep 2
    @just vad-stream

# Flash ESP32 and then monitor vocals (convenience command)
flash-and-monitor: flash
    @echo ""
    @echo "✅ Firmware flashed! Starting vocal monitor in 2 seconds..."
    @sleep 2
    @just vad-monitor

# Flash ESP32 and then monitor vocals continuously
flash-and-monitor-continuous: flash
    @echo ""
    @echo "✅ Firmware flashed! Starting CONTINUOUS vocal monitor in 2 seconds..."
    @sleep 2
    @just vad-monitor-continuous
