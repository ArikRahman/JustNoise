# Raw PCM Streaming for Continuous VAD Monitoring

## Why Raw PCM Instead of WAV?

Previously, the system was streaming audio as **WAV files** with a 44-byte header sent every 10 seconds. For continuous VAD monitoring, this is wasteful:

### Problems with WAV approach:
- **44 bytes of overhead every 10 seconds** = extra serial traffic
- **Time gaps** between recordings (2s delay in original firmware)
- **Complex parsing** to find and validate RIFF headers
- **Not true continuous monitoring** - discrete 10s windows

### Benefits of Raw PCM approach:
- **Zero overhead** - just pure 16-bit samples, 2 bytes per sample
- **True continuous streaming** - no gaps or boundaries
- **Simpler processing** - direct sample-to-VAD pipeline
- **More efficient** - 921600 baud is fully utilized for actual audio data
- **Lower latency** - VAD can run continuously without waiting for headers

## Architecture

```
ESP32 (Raw PCM Streamer)
    ↓
    (16-bit mono PCM @ 16kHz, continuous)
    ↓
Serial → Python Script (vad_stream.py)
    ↓
    (Buffering & framing into 512-sample chunks)
    ↓
Silero VAD
    ↓
    (Speech/no-speech classification + confidence)
    ↓
CLI Output (Real-time alerts & statistics)
```

## How It Works

### ESP32 Firmware (`arduino/mictest/src/main.cpp`)
- **No WAV header generation** - removed ~90 lines of boilerplate
- Streams raw 16-bit PCM samples directly to serial
- Continuous loop with no preset duration limit
- Runs indefinitely until serial connection is lost

### Python Script (`scripts/vad_stream.py`)
- Receives raw bytes from serial (no header parsing needed)
- Buffers samples into 512-sample chunks (32ms frames for VAD)
- Feeds each chunk to Silero VAD
- Displays real-time alerts and confidence metrics
- Tracks speech segments and generates session statistics

## Usage

### Flash the new firmware:
```bash
just flash
```

### Run continuous VAD monitoring (Raw PCM):
```bash
just vad-stream
```

### Or in one command:
```bash
just flash-and-stream
```

## Output Example

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

🗣️  🗣️  🗣️  🗣️  🗣️  🗣️  🗣️  🗣️  🗣️  🗣️  
[12:34:58] 🔴 VOCALS DETECTED - SPEECH STARTED!
🗣️  🗣️  🗣️  🗣️  🗣️  🗣️  🗣️  🗣️  🗣️  🗣️  

🔴 SPEECH [████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 65.32% 
[12:35:01] 🟢 Speech ended (duration: 3.24s)

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

## Technical Details

### Serial Protocol
- **Baudrate**: 921600 baud (required for 32 kB/s audio throughput)
- **Format**: 16-bit signed PCM, little-endian
- **Sample rate**: 16000 Hz (standard for VAD)
- **Channels**: 1 (mono)
- **Bytes per second**: 32,000 bytes/s (32 kB/s)

### VAD Processing
- **Silero VAD v5** (PyTorch-based)
- **Frame size**: 512 samples = 32ms at 16kHz
- **Overlap/stride**: VAD internally handles timing
- **Output**: Speech/no-speech classification + confidence score (0.0-1.0)

### Buffer Management
- Serial buffer: 4KB reads at a time (prevents overflow)
- PCM frame buffer: Accumulates bytes until 512-sample chunk is available
- No pre-allocation needed - dynamic growing buffer

## Comparison: WAV vs Raw PCM

| Aspect | WAV Approach | Raw PCM Approach |
|--------|-------------|------------------|
| **Header overhead** | 44 bytes per recording | 0 bytes |
| **Duration limit** | Fixed (10s per recording) | Continuous/unlimited |
| **Processing delay** | Wait for full WAV | Real-time streaming |
| **Serial efficiency** | ~98% (WAV data) | 100% (all data is audio) |
| **VAD latency** | High (wait for header) | Low (immediate) |
| **Parsing complexity** | High (RIFF header search) | None |
| **Best for** | Batch processing | Real-time monitoring |

## What Changed

### Files Modified:
1. **`arduino/mictest/src/main.cpp`**
   - Removed `sendWAVHeader()` function
   - Removed fixed recording duration
   - Changed loop to continuous streaming
   - Simplified logic

2. **`scripts/vad_stream.py`** (NEW)
   - Direct raw PCM reading
   - Simple byte-to-sample buffering
   - Continuous frame processing
   - Real-time output

3. **`justfile`**
   - Added `vad-stream` command
   - Added `flash-and-stream` convenience command
   - Updated firmware description (WAV → raw PCM)

### Backward Compatibility
- Old `vad_monitor.py` (WAV-based) still works for 10-second recordings
- Old firmware can still be flashed if needed
- New approach is purely additive

## Next Steps

1. **Flash the new firmware**: `just flash`
2. **Test with VAD streaming**: `just vad-stream`
3. **Monitor real-time output** for speech detection accuracy
4. **Integrate with MQTT** for remote actuation commands
5. **Add persistence** to save speech statistics/logs