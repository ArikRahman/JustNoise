# VAD Grace Period Changes - Summary

## What Changed

You can now easily control how long the VAD waits before ending a speech segment. This solves the problem of brief pauses (breathing, thinking) cutting off speech detection.

## Files Modified

### 1. `scripts/vad_stream.py`
**Added parameters to PCMVADMonitor class:**
- `min_silence_ms`: Grace period in milliseconds (default 500ms)
- `min_speech_ms`: Minimum speech duration to accept (default 0ms)

**Command-line arguments added:**
```python
--min-silence    # Grace period in ms before ending speech (default: 500)
--min-speech     # Minimum speech duration in ms before accepting speech (default: 0)
```

**Display improvements:**
- Header now shows configured grace period and minimum speech duration
- Better visual feedback during monitoring

**Hysteresis logic added:**
- Implements frame-by-frame grace period counter
- Silence must exceed threshold before ending speech segment
- Prevents jittery speech/silence toggling

### 2. `pi-aggregator/vad.py`
**Updated SileroVAD constructor:**
```python
def __init__(self, sample_rate=16000, device="cpu", min_silence_duration_ms=500):
```

- Now accepts `min_silence_duration_ms` parameter
- Passes it directly to VADIterator for smoothing
- Default is 500ms (half second)

### 3. `justfile`
**New VAD streaming commands with presets:**

| Command | Grace Period | Purpose |
|---------|--------------|---------|
| `just vad-stream` | 500ms | Default balanced setting |
| `just vad-stream-relaxed` | 1000ms | Recommended for classroom |
| `just vad-stream-very-relaxed` | 1500ms | Most forgiving (lectures) |
| `just vad-stream-aggressive` | 200ms | Quick boundaries |
| `just vad-stream-custom min_silence="X"` | X ms | Custom tuning |

## How to Use

### Start with the Relaxed Preset
```bash
just vad-stream-relaxed
```
This waits for 1 full second of silence before ending speech—plenty of time for natural breathing pauses.

### Fine-Tune if Needed
```bash
just vad-stream-custom min_silence="1200"
```
Increase the value (milliseconds) if pauses are being cut off.
Decrease it if different speakers are being merged together.

### Try Different Presets
```bash
just vad-stream              # 500ms
just vad-stream-relaxed      # 1000ms
just vad-stream-very-relaxed # 1500ms
just vad-stream-aggressive   # 200ms
```

## Example: Classroom Tuning

1. Flash firmware:
   ```bash
   just flash
   ```

2. Start VAD with relaxed grace period:
   ```bash
   just vad-stream-relaxed
   ```

3. Speak naturally into the microphone (include pauses, breathing)

4. Watch the output:
   - Speech segments should stay together through pauses
   - Each sentence (with pauses) = one continuous segment

5. If tweaking needed:
   ```bash
   # Speech still being cut off?
   just vad-stream-very-relaxed
   
   # Segments too long / merging speakers?
   just vad-stream-custom min_silence="800"
   ```

## Technical Details

### Grace Period Flow (1000ms example)

```
Person speaks + pauses + speaks again (all within 1 second)
    ↓
VAD detects pause (silence)
    ↓
Grace period counter starts (need 1000ms continuous silence)
    ↓
Person speaks again during grace period (before 1000ms reached)
    ↓
Grace period resets → still ONE speech segment ✓
```

### Without Grace Period

```
Person speaks + brief pause (200ms)
    ↓
VAD detects silence → immediately ends segment ✗
    ↓
Person speaks again
    ↓
VAD detects speech → new segment ✗
```

## Recommended Settings by Use Case

| Scenario | Command | Grace Period |
|----------|---------|--------------|
| **Classroom/Lecture** | `just vad-stream-relaxed` | 1000ms |
| **Meeting/Conference** | `just vad-stream-custom min_silence="800"` | 800ms |
| **Podcast/Interview** | `just vad-stream-relaxed` | 1000ms |
| **Fast conversation** | `just vad-stream-aggressive` | 200ms |
| **Noisy environment** | `just vad-stream-very-relaxed` | 1500ms |

## Backwards Compatibility

- Old commands still work: `just vad-stream` uses default 500ms
- If no grace period specified, defaults to 500ms (original behavior)
- No breaking changes to existing code or MQTT schemas

## Next Steps

1. **Try it**: `just vad-stream-relaxed`
2. **Tune it**: Adjust until pauses feel natural
3. **Use it**: Once tuned, use that same command in production
4. **Monitor**: Run `just capture-pcm` simultaneously to record and verify

---

**Questions?** Check `VAD_GRACE_PERIOD_GUIDE.md` for detailed tuning instructions.