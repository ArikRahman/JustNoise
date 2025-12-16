# PCM Capture - Quick Reference

## One-Liners

```bash
# Record with default settings (60s files)
just capture-pcm

# Record with custom duration (5 minutes per file)
just capture-pcm-duration 300

# Record with VAD-based splitting (on speech boundaries)
just capture-pcm-vad

# Record with size-based splitting (1 MB per file)
just capture-pcm-size
```

## Monitor + Record Simultaneously

**Terminal 1: Real-time speech detection**
```bash
just vad-stream
```

**Terminal 2: Save all audio to files**
```bash
just capture-pcm
```

Result: Live alerts + permanent recordings! 🎙️

## Capture Modes at a Glance

| Mode | Command | When to Use | Output |
|------|---------|-------------|--------|
| **Time** | `just capture-pcm` | Consistent chunks | 60s per file |
| **Time (custom)** | `just capture-pcm-duration 300` | Flexible duration | 300s per file |
| **VAD** | `just capture-pcm-vad` | Speech segments | One file per segment |
| **Size** | `just capture-pcm-size` | Limited storage | 1 MB per file |

## Key Facts

- **Format:** WAV (16-bit PCM, 16 kHz, mono)
- **Size:** ~1.9 MB per minute of audio
- **Default output:** `./recordings/`
- **Naming:** `recording_YYYYMMDD_HHMMSS.wav`
- **No file limit:** Runs indefinitely until you press Ctrl+C

## File Splitting Explained

### Time-Based (Default)
```
[60s] → recording_001.wav
[60s] → recording_002.wav
[60s] → recording_003.wav
```
Best for: Regular analysis, predictable sizes

### Size-Based
```
[~32s = 1MB] → recording_001.wav
[~32s = 1MB] → recording_002.wav
[~32s = 1MB] → recording_003.wav
```
Best for: Storage constraints, cloud upload

### VAD-Based
```
[speech 3.2s] → recording_001.wav (speech)
[silence 1.5s] → recording_002.wav (silence)
[speech 4.8s] → recording_003.wav (speech)
[silence 2.1s] → recording_004.wav (silence)
```
Best for: ML training, speech analysis, segment tracking

## Usage Scenarios

### Scenario 1: Classroom All-Day Recording
```bash
just capture-pcm-duration 600  # 10-minute files
```
Files automatically rotate every 10 minutes.

### Scenario 2: Speech-Only Dataset
```bash
just capture-pcm-vad
```
Creates separate files for each speech segment. Perfect for training models.

### Scenario 3: Storage-Limited Device
```bash
just capture-pcm-size
```
Files capped at 1 MB (~32 seconds). Easy to manage.

### Scenario 4: Real-Time Monitoring + Recording
```bash
# Terminal 1
just vad-stream

# Terminal 2
just capture-pcm
```
Get live alerts while recording everything to disk.

## Playing Back Recordings

```bash
# macOS
afplay ./recordings/recording_20250115_143022.wav

# Linux
aplay ./recordings/recording_20250115_143022.wav

# Windows
start ./recordings/recording_20250115_143022.wav

# Any platform (requires ffmpeg)
ffplay ./recordings/recording_20250115_143022.wav
```

## Analyzing Files

```python
import wave

with wave.open('./recordings/recording_20250115_143022.wav', 'r') as w:
    print(f"Duration: {w.getnframes() / w.getframerate():.1f}s")
    print(f"Sample rate: {w.getframerate()} Hz")
    print(f"Channels: {w.getnchannels()}")
```

## Batch Processing

```bash
# List all files with duration
for f in recordings/*.wav; do
  python3 -c "import wave; w=wave.open('$f'); print(f'{f}: {w.getnframes()/w.getframerate():.1f}s')" 2>/dev/null
done

# Convert all to MP3
for f in recordings/*.wav; do
  ffmpeg -i "$f" "${f%.wav}.mp3"
done

# Upload to cloud
for f in recordings/*.wav; do
  aws s3 cp "$f" s3://my-bucket/audio/
done
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| No files created | Run `just flash` to flash firmware |
| Serial connection lost | Reconnect ESP32, run `just check` |
| Files too small | Use `just capture-pcm-duration 300` |
| Running out of space | Use `just capture-pcm-size` with smaller max size |
| VAD mode crashes | Run `just setup-vad` first |

## Storage Calculation

- **1 minute:** 1.9 MB
- **1 hour:** 115 MB
- **1 day (24h):** 2.76 GB
- **1 week:** 19.3 GB
- **1 month:** 83.2 GB

## Python Integration

```python
from pathlib import Path
import wave

# Find latest recording
latest = sorted(Path('./recordings').glob('*.wav'))[-1]

# Load with librosa
import librosa
y, sr = librosa.load(str(latest))

# Analyze
print(f"Duration: {len(y) / sr:.1f}s")
```

## Advanced Options (CLI)

```bash
# Custom output directory
python scripts/capture_pcm.py /dev/tty.wchusbserial550D0193611 \
  --output-dir /mnt/usb_drive

# VAD mode with custom directory
python scripts/capture_pcm.py /dev/tty.wchusbserial550D0193611 \
  --mode vad \
  --output-dir ./speech_segments

# Size-based with custom limit
python scripts/capture_pcm.py /dev/tty.wchusbserial550D0193611 \
  --mode size \
  --max-size 5242880  # 5 MB per file
```

## Combining with VAD Analysis

```bash
# 1. Record with VAD splitting
just capture-pcm-vad

# 2. Analyze which files are speech vs silence
python3 << 'EOF'
from pathlib import Path
import wave

for f in sorted(Path('./recordings').glob('*.wav')):
    w = wave.open(str(f))
    dur = w.getnframes() / w.getframerate()
    w.close()
    
    # Files < 2s are usually silence
    label = "SILENCE" if dur < 2.0 else "SPEECH"
    print(f"{label}: {f.name} ({dur:.1f}s)")
EOF
```

## What You Get

✅ **Real-time VAD monitoring** (with `vad-stream`)
✅ **Permanent WAV files** (with `capture-pcm`)
✅ **Multiple split strategies** (time/size/VAD)
✅ **Zero configuration** (sensible defaults)
✅ **Standard format** (plays anywhere)
✅ **Easy analysis** (Python/Audacity/ffmpeg)

## See Also

- Full guide: `docs/PCM_CAPTURE.md`
- Real-time VAD: `QUICK_START_RAW_PCM.md`
- Architecture: `AGENTS.md`
