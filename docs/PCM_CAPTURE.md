# PCM Stream Capture to Audio Files

Now you can capture the continuous raw PCM stream from ESP32 and save it to properly formatted audio files (WAV, FLAC, etc.) with multiple splitting strategies.

## Why Capture PCM Streams?

You get the best of both worlds:

1. **Real-time VAD monitoring** — Process audio as it streams for immediate speech detection
2. **Permanent recordings** — Save audio files for later analysis, training, or compliance

The old WAV approach forced you to choose. Now you can do both simultaneously:
- Stream raw PCM continuously to ESP32
- Run VAD in real-time with `just vad-stream`
- Simultaneously capture to audio files with `just capture-pcm`

## Quick Start

### Capture to WAV (default, 60s per file)
```bash
just capture-pcm
```

### Capture with custom duration (e.g., 5 minutes per file)
```bash
just capture-pcm-duration 300
```

### Capture with VAD-based splitting (on speech boundaries)
```bash
just capture-pcm-vad
```

### Capture with size-based splitting (1 MB per file)
```bash
just capture-pcm-size
```

## Capture Modes

### 1. Time-Based (`--mode time`)

**Default mode.** Splits files at regular time intervals.

```bash
just capture-pcm                    # 60s per file
just capture-pcm-duration 300       # 5 minutes per file
just capture-pcm-duration 1800      # 30 minutes per file
```

**Use when:**
- You want predictable file sizes and durations
- You're doing batch analysis
- You need to sync with external timestamps

**Output:**
```
recording_20250115_120000.wav       (60 seconds)
recording_20250115_120100.wav       (60 seconds)
recording_20250115_120200.wav       (60 seconds)
...
```

### 2. Size-Based (`--mode size`)

**Splits files at a maximum size threshold.**

```bash
just capture-pcm-size               # 1 MB per file (default)
```

Custom size:
```bash
python scripts/capture_pcm.py /dev/tty.wchusbserial550D0193611 --mode size --max-size 5242880  # 5 MB
```

**Use when:**
- You have limited storage
- You want to control exact file sizes
- You're streaming to cloud storage with bandwidth limits

**Calculation:**
- 16 kHz × 2 bytes/sample = 32 KB/s
- 1 MB file ≈ 32 seconds of audio

### 3. VAD-Based (`--mode vad`)

**Splits files on speech boundaries (requires Silero VAD).**

```bash
just capture-pcm-vad
```

First install VAD support:
```bash
just setup-vad
```

**Use when:**
- You want separate files for each speech segment
- You're analyzing classroom lectures
- You want silence separated from speech
- You're building training datasets

**Output:**
```
recording_20250115_120010.wav       (speech segment 1, 3.5s)
recording_20250115_120014.wav       (silence, 2.1s)
recording_20250115_120016.wav       (speech segment 2, 5.2s)
recording_20250115_120022.wav       (silence, 1.8s)
...
```

**How it works:**
- Silero VAD processes each 32ms frame
- When speech starts: creates new file
- When speech ends: saves file, starts silence file
- Automatically splits on transitions

### 4. Manual (`--mode manual`)

**Capture everything to buffer, save on demand.**

```bash
python scripts/capture_pcm.py /dev/tty.wchusbserial550D0193611 --mode manual
```

Then press `Ctrl+C` to save everything to a single file.

**Use when:**
- You want full control over file creation
- You're experimenting with different durations
- You want to manually mark boundaries

## Usage Examples

### Example 1: Continuous 10-minute files
```bash
just capture-pcm-duration 600
```

Creates a new WAV file every 10 minutes automatically.

### Example 2: VAD-based recording for classroom analysis
```bash
just capture-pcm-vad
```

Automatically saves each speech utterance as a separate file. Perfect for:
- Analyzing student participation
- Measuring speech rate
- Building voice datasets

### Example 3: Parallel monitoring + recording

**Terminal 1: Real-time speech detection**
```bash
just vad-stream
```

**Terminal 2: Permanent audio recording**
```bash
just capture-pcm
```

Both run simultaneously! Monitor speech in real-time while recording all audio.

### Example 4: Custom output directory
```bash
python scripts/capture_pcm.py /dev/tty.wchusbserial550D0193611 \
  --output-dir /mnt/usb_storage \
  --duration 300
```

Save to external storage.

## Command Reference

### Justfile Commands

```bash
just capture-pcm                    # Time-based (60s files)
just capture-pcm-duration 300       # Time-based (custom duration)
just capture-pcm-vad                # VAD-based (speech boundaries)
just capture-pcm-size               # Size-based (1 MB files)
```

### Python Script (Direct)

```bash
# Time-based
python scripts/capture_pcm.py /dev/tty.wchusbserial550D0193611 \
  --mode time \
  --duration 60

# Size-based
python scripts/capture_pcm.py /dev/tty.wchusbserial550D0193611 \
  --mode size \
  --max-size 1048576

# VAD-based
python scripts/capture_pcm.py /dev/tty.wchusbserial550D0193611 \
  --mode vad

# Custom output
python scripts/capture_pcm.py /dev/tty.wchusbserial550D0193611 \
  --output-dir ./my_recordings \
  --duration 300
```

## Output Format

### Default: WAV Files

All output files are standard WAV (RIFF) format:
- **Sample Rate:** 16000 Hz (16 kHz)
- **Bit Depth:** 16-bit signed PCM
- **Channels:** 1 (mono)
- **Encoding:** Linear PCM (uncompressed)

Compatible with:
- ✅ All audio editing software (Audacity, Adobe Audition, etc.)
- ✅ All audio analysis tools (librosa, scipy, etc.)
- ✅ Streaming services and cloud storage
- ✅ Python libraries (soundfile, wave, scipy, etc.)

### File Naming

Files are automatically timestamped:
```
recording_YYYYMMDD_HHMMSS.wav
```

Example:
```
recording_20250115_120000.wav
recording_20250115_120100.wav
recording_20250115_120200.wav
```

### File Locations

By default, files are saved to:
```
JustNoise/recordings/
```

Change with `--output-dir`:
```bash
python scripts/capture_pcm.py /dev/tty.wchusbserial550D0193611 \
  --output-dir ./my_audio_files
```

## Typical File Sizes

| Duration | Mode | Typical Size | Notes |
|----------|------|--------------|-------|
| 1 minute | time | ~1.9 MB | 16kHz × 2 bytes × 60s |
| 10 minutes | time | ~19 MB | Default sensible size |
| 1 hour | time | ~1.15 GB | Large but manageable |
| Speech segment | vad | 100KB - 500KB | Varies by speech length |
| 1 MB | size | ~32 seconds | Configurable limit |

## Practical Workflows

### Workflow 1: Real-time monitoring + Recording

**Setup:**
- Terminal 1: `just vad-stream` (see real-time alerts)
- Terminal 2: `just capture-pcm` (save all audio)

**Benefits:**
- Instant feedback on speech detection
- Complete audio archive
- Can analyze missed detections

### Workflow 2: Classroom All-Day Recording

```bash
just capture-pcm-duration 1800  # 30-minute files
```

**Result:**
- Automatic file rotation every 30 minutes
- Clean boundaries for later analysis
- Easy to sync with lesson schedules

### Workflow 3: Speech Segmentation

```bash
just capture-pcm-vad
```

**Result:**
- Automatic separation of speech/silence
- Clean training data for ML models
- Perfect for speaker diarization
- Easy statistics (speech duration, segments, etc.)

### Workflow 4: Storage-Constrained Environments

```bash
just capture-pcm-size  # 1 MB files (~32 seconds each)
```

**Result:**
- Predictable file sizes
- Easy to manage on limited storage
- Can stream to cloud storage incrementally

## Integration with VAD Monitoring

You can run **both** monitoring and recording simultaneously:

```bash
# Terminal 1: Real-time VAD alerts
just vad-stream

# Terminal 2 (new terminal): Record all audio to files
just capture-pcm-duration 300
```

**What happens:**
- Terminal 1 shows real-time speech detection
- Terminal 2 continuously saves to WAV files
- Both processes are independent
- You get live alerts AND permanent recordings

## Analyzing Captured Files

### Using Python with soundfile

```python
import soundfile as sf
import numpy as np

# Load audio
audio, sr = sf.read('recording_20250115_120000.wav')

# Process
print(f"Sample rate: {sr} Hz")
print(f"Duration: {len(audio) / sr:.1f}s")
print(f"RMS level: {np.sqrt(np.mean(audio**2)):.1f}")

# Process further...
```

### Using librosa

```python
import librosa

# Load
y, sr = librosa.load('recording_20250115_120000.wav')

# Analyze
S = librosa.feature.melspectrogram(y=y, sr=sr)
```

### Using Audacity

1. File → Open → select WAV file
2. Analyze speech patterns, filter, etc.
3. Export if needed

## Troubleshooting

### No files being created

1. Check ESP32 is connected: `just check`
2. Flash firmware: `just flash`
3. Verify serial port in `justfile`
4. Check `recordings/` directory exists

### Files are too small/large

Adjust with `--duration` or `--max-size`:
```bash
just capture-pcm-duration 120      # Smaller files (2 minutes)
just capture-pcm-duration 1200     # Larger files (20 minutes)
```

### VAD mode not working

Install VAD support first:
```bash
just setup-vad
```

### Running out of disk space

Use size-based splitting with smaller size:
```bash
python scripts/capture_pcm.py /dev/tty.wchusbserial550D0193611 \
  --mode size \
  --max-size 524288  # 512 KB files (~16 seconds each)
```

## Performance & Specifications

### Serial Transfer
- **Baudrate:** 921600 bps
- **Throughput:** 32 KB/s
- **Overhead:** 0% (pure PCM data)

### File Writing
- **Latency:** ~100ms (Python buffering)
- **Throughput:** No limit (local disk)
- **Concurrent writes:** Single stream

### Storage
- **16 kHz audio:** ~1.9 MB per minute
- **1 hour:** ~1.15 GB
- **10 hours:** ~11.5 GB

## Next Steps

1. **Start capturing:** `just capture-pcm`
2. **Monitor simultaneously:** `just vad-stream` (in another terminal)
3. **Analyze saved files** using audio tools
4. **Integrate with MQTT** for remote actuation
5. **Build datasets** for ML training

## See Also

- **Real-time VAD:** See `QUICK_START_RAW_PCM.md`
- **Architecture:** See `AGENTS.md`
- **Serial protocol:** See `docs/RAW_PCM_STREAMING.md`
