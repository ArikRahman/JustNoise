# Voice Activity Detection (VAD) Service

Real-time speech detection using Silero VAD, running on the Pi Aggregator.

## Overview

The VAD service processes audio from the ESP32 serial stream (or WAV files) and publishes compact speech detection events to MQTT. This enables:

- **Privacy-preserving speech detection** — no raw audio transmitted or stored
- **Real-time event triggers** — detect when someone starts/stops talking
- **Aggregated metrics** — track speech activity percentage in noise profiles
- **Low latency** — ~30-100ms detection delay

## Architecture

```
ESP32 (I2S Mic) → Serial → VAD Service → MQTT
                                ↓
                    [speech_start/speech_end events]
                    [speech segment summaries]
```

The service runs on the Pi Aggregator alongside the noise profile aggregator.

## Installation

### 1. Install PyTorch and Silero VAD dependencies:

```bash
# Using justfile (recommended)
just setup-vad

# Or manually with uv
uv sync --extra vad
```

This installs PyTorch (CPU-only) and torchaudio. On Raspberry Pi, you may need to use a prebuilt wheel.

### 2. Ensure MQTT broker is running:

```bash
# macOS
brew install mosquitto
brew services start mosquitto

# Linux
sudo apt install mosquitto mosquitto-clients
sudo systemctl start mosquitto
```

## Usage

### Live Detection from ESP32

```bash
# Using justfile
just vad-live

# Or directly
uv run pi-aggregator/vad.py --serial /dev/tty.wchusbserial550D0193611
```

The service will:
1. Connect to the ESP32 serial port
2. Trigger a recording
3. Stream audio through Silero VAD in real-time
4. Publish speech events to MQTT

### CLI Monitor (Debug Mode)

For debugging and testing without MQTT, use the visual CLI monitor:

```bash
# Using justfile (recommended)
just vad-monitor

# Or directly
uv run scripts/vad_monitor.py /dev/tty.wchusbserial550D0193611
```

This displays:
- 🔴 **Visual alerts** when vocals/speech are detected
- Real-time **confidence bars** during speech
- **Session summary** with speech statistics
- No MQTT required — perfect for testing!

### Test on WAV File

```bash
# Using justfile
just vad-test recording.wav

# Or directly
uv run pi-aggregator/vad.py --file recording.wav
```

## MQTT Topics & Payloads

### Speech Events (discrete start/end)

**Topic:** `classroom/<room_id>/pi/aggregator/vad_event`

```json
{
  "timestamp": "2025-12-16T12:00:00Z",
  "device_id": "aggregator1",
  "event": "speech_start",
  "source": "silero_vad_v0"
}
```

### Speech Segments (summaries)

**Topic:** `classroom/<room_id>/pi/aggregator/vad`

```json
{
  "timestamp": "2025-12-16T12:00:05Z",
  "device_id": "aggregator1",
  "speech": true,
  "start_ms": 1234,
  "end_ms": 2345,
  "confidence": 0.93,
  "sample_rate": 16000,
  "source": "silero_vad_v0"
}
```

## Configuration

### Parameters (in `vad.py`)

- **Frame size:** 512 samples (32ms at 16kHz) — **required by Silero VAD**
- **Threshold:** 0.5 (default Silero threshold)
- **Min silence duration:** 500ms — need half second of silence to end speech (prevents choppy toggles during brief pauses)
- **Speech padding:** 100ms — add padding to detected segments for smoother transitions

### MQTT Topics (in `shared/utils/config.py`)

```python
TOPIC_VAD = f"{TOPIC_PREFIX}/pi/aggregator/vad"
TOPIC_VAD_EVENT = f"{TOPIC_PREFIX}/pi/aggregator/vad_event"
```

## Integration with Noise Profiles

Future enhancement: Add VAD-based fields to `pi/aggregator/noise_profile`:

```json
{
  "timestamp": "2025-12-16T12:35:00Z",
  "profile": {
    "count": 12,
    "mean_rms_db": -35.2,
    "max_rms_db": -28.3,
    "speech_fraction": 0.68,
    "last_speech_ts": "2025-12-16T12:34:58Z"
  }
}
```

## Testing

### Subscribe to VAD events:

```bash
# Listen to all VAD topics
mosquitto_sub -t 'classroom/+/pi/aggregator/vad/#' -v

# Listen to events only
mosquitto_sub -t 'classroom/+/pi/aggregator/vad_event' -v
```

### Test with known speech samples:

1. Record a WAV file with clear speech: `just record test_speech.wav`
2. Run VAD on it: `just vad-test test_speech.wav`
3. Verify speech segments are detected

## Performance

- **Latency:** 32-100ms from audio capture to MQTT publish (Silero requires 512-sample chunks)
- **CPU Usage:** ~10-20% on Raspberry Pi 4 (CPU-only PyTorch)
- **Memory:** ~200MB for model + buffers
- **Bandwidth:** <1 KB/s MQTT traffic (vs 32 KB/s for raw audio)

## Privacy & Security

✅ **No raw audio transmitted or stored** — only compact metadata (timestamps, boolean flags, confidence scores)  
✅ **Local processing** — Silero VAD runs on-device (Pi), no cloud services  
✅ **Minimal data retention** — events are ephemeral (MQTT QoS 0)  

## Troubleshooting

### ImportError: torch not found

```bash
just setup-vad
```

### Model download fails

The first run downloads the Silero VAD model (~1.4 MB) from PyTorch Hub. Ensure internet connectivity.

### No speech detected

- Check audio levels: `just info recording.wav`
- Verify sample rate is 16kHz
- Lower threshold in `vad.py` (default 0.5 → try 0.3)

### High false positive rate

- Increase threshold (0.5 → 0.7)
- Increase `min_silence_duration_ms` (500ms → 700ms)

### Speech segments too short (choppy)

**This is the most common issue** - VAD ending speech too quickly during natural pauses.

**Solution**: Increase `min_silence_duration_ms` in `pi-aggregator/vad.py`:
```python
min_silence_duration_ms=500,  # Default: requires 0.5s of silence to end speech
# Try increasing to 700-1000ms for longer natural pauses
```

Also increase padding:
```python
speech_pad_ms=100,  # Default: adds 100ms padding on each side
# Try 150-200ms for smoother transitions
```

## References

- [Silero VAD GitHub](https://github.com/snakers4/silero-vad)
- [PyTorch Hub](https://pytorch.org/hub/)
- [AGENTS.md — VAD Section](../AGENTS.md#silero-vad-real-time-voice-activity-detection)
