# Quick Start: Raw PCM Streaming with VAD

## One-Command Setup

```bash
# Flash firmware and start monitoring in one go
just flash-and-stream
```

That's it! You'll see real-time speech detection output immediately.

## Individual Commands

### Flash the ESP32
```bash
just flash
```
Flashes the new raw PCM streaming firmware (no WAV headers).

### Start VAD Monitoring
```bash
just vad-stream
```
Begins continuous PCM streaming and voice activity detection.
- Displays real-time alerts when speech is detected
- Shows confidence levels and progress bars
- Prints session statistics when you press Ctrl+C

### Check if ESP32 is Connected
```bash
just check
```

### Monitor Serial Output (for debugging)
```bash
just monitor
```

## What to Expect

When you run `just vad-stream`, you'll see:

```
======================================================================
🎤 RAW PCM VOICE ACTIVITY MONITOR
======================================================================
Serial Port: /dev/tty.wchusbserial550D0193611
Baudrate:    921600
Sample Rate: 16000 Hz
Chunk Size:  512 samples (32ms)
Mode:        🔄 CONTINUOUS (Press Ctrl+C to stop)
======================================================================

⏳ Waiting for ESP32 raw PCM stream...

[12:34:56] ℹ️  Connected to /dev/tty.wchusbserial550D0193611 at 921600 baud
[12:34:56] ℹ️  Trigger sent to ESP32...

======================================================================
🎧 MONITORING STARTED - Listening for vocals...
======================================================================
```

Then start speaking! When speech is detected:

```
🗣️  🗣️  🗣️  🗣️  🗣️  🗣️  🗣️  🗣️  🗣️  🗣️  
[12:34:58] 🔴 VOCALS DETECTED - SPEECH STARTED!
🗣️  🗣️  🗣️  🗣️  🗣️  🗣️  🗣️  🗣️  🗣️  🗣️  

🔴 SPEECH [████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 65.32% 
```

Press Ctrl+C to stop and see stats:

```
======================================================================
📊 SESSION SUMMARY
======================================================================
Session duration:       8.2s
Total chunks processed: 256
Speech chunks:          104
Speech percentage:      40.6%
Speech segments:        1
Total speech time:      3.24s
Average segment:        3.24s
Longest segment:        3.24s
======================================================================
```

## Prerequisites

Make sure you have VAD dependencies installed:

```bash
just setup-vad
```

This installs PyTorch and other requirements for Silero VAD.

## Troubleshooting

### "ESP32 not found"
```bash
just check
```
Make sure your ESP32 is connected via USB. The default port is `/dev/tty.wchusbserial550D0193611` (macOS with CH340 adapter).

### "Error: Could not import VAD module"
```bash
just setup-vad
```

### Audio is silent or garbled
Make sure the firmware is flashed:
```bash
just flash
```

## Comparison with Old WAV Approach

| Feature | Old (WAV) | New (Raw PCM) |
|---------|-----------|---------------|
| Header overhead | 44 bytes every 10s | None |
| Continuous? | No, 10s chunks | Yes, unlimited |
| Processing delay | Wait for header | Immediate |
| Command | `just vad-monitor-continuous` | `just vad-stream` |

## Advanced: Custom Serial Port

If your ESP32 is on a different serial port:

```bash
uv run scripts/vad_stream.py /dev/ttyUSB0
```

Or if you prefer a different baud rate:

```bash
uv run scripts/vad_stream.py /dev/tty.wchusbserial550D0193611 --baudrate 115200
```

## Documentation

For technical details, see:
- `docs/RAW_PCM_STREAMING.md` — In-depth architecture and design
- `REFACTOR_SUMMARY.md` — What changed from WAV approach

## Need Help?

Check the serial connection:
```bash
just monitor
```

This shows all raw data coming from ESP32. If you see binary data streaming, the connection is good.

Test VAD independently:
```bash
just test-vad
```

This verifies Silero VAD is working properly.