# Microphone Gain Control

## Overview

The ESP32 microphone now has **real-time adjustable gain** (amplification). You can change the sensitivity without restarting the device, making it easy to pick up audio from different distances.

## Quick Start

### Adjust Gain Interactively
```bash
just mic-gain
```
This opens an interactive menu where you can adjust gain in real-time while listening.

### Set Specific Gain Level
```bash
just mic-gain-set 3
```
Levels: 0=1x, 1=2x, 2=4x, 3=8x, 4=16x (default)

### Presets (No Arguments)
```bash
just mic-gain-max      # 16x (distant sources)
just mic-gain-medium   # 8x (classroom/office)
just mic-gain-min      # 1x (loud sources close up)
```

---

## Gain Levels Explained

| Level | Multiplier | Use Case | Examples |
|-------|-----------|----------|----------|
| 0 | 1x | No amplification | Loud speakers, person very close |
| 1 | 2x | Minimal | Normal volume speech 1-2 feet away |
| 2 | 4x | Light | Classroom teacher, moderate distance |
| 3 | 8x | Medium | **Most common classroom use** |
| 4 | 16x | High (default) | Distant speech, quiet environments |

---

## How Gain Works

**Gain = amplification of audio signal**

- **Higher gain**: Picks up quieter sounds from farther away (but amplifies noise too)
- **Lower gain**: Only picks up loud/close sounds clearly (reduces background noise)

### Example Scenarios

**Scenario 1: Recording a lecture across a room**
```bash
just mic-gain-max
# 16x gain - picks up even whispered speech from far away
```

**Scenario 2: Classroom with teacher standing at desk**
```bash
just mic-gain-medium
# 8x gain - good balance of distance and clarity
```

**Scenario 3: Capturing very loud speaker close to mic**
```bash
just mic-gain-min
# 1x gain - prevents audio distortion/clipping
```

---

## Available Commands

### Interactive Gain Control
```bash
just mic-gain
```
Opens interactive menu:
- Type `0-4` to adjust gain
- Type `i` to show info
- Type `q` to quit
- Adjustments apply immediately while streaming

### Set Gain to Specific Level
```bash
just mic-gain-set 3
```
Syntax: `just mic-gain-set <level>`
- `<level>` = 0, 1, 2, 3, or 4

### Preset Commands (Easiest)
```bash
just mic-gain-max      # 4 = 16x amplification
just mic-gain-medium   # 3 = 8x amplification
just mic-gain-min      # 0 = 1x (no amplification)
```

### Test Mode
```bash
just mic-gain-test 3
```
Sets gain and shows you the settings. Use this before running VAD to verify.

---

## Firmware Details

### Serial Protocol

The ESP32 listens for serial commands:

| Command | Function | Example |
|---------|----------|---------|
| `G<0-4>` | Set gain level | `G3` = 8x gain |
| `I` | Display info | Shows current settings |
| Any other byte | Start streaming | Begins PCM output |

### Real-Time Adjustment

You can change gain **while streaming** without stopping VAD:

```bash
# Terminal 1: Start VAD
just vad-stream-relaxed

# Terminal 2: Adjust gain while VAD is running
just mic-gain-set 2    # Change to 4x gain
just mic-gain-set 4    # Change to 16x gain
```

### Gain Shift Calculation

Internally, gain is applied as a bit shift:
```
Shift 0 = >> (12-0) = 1x
Shift 1 = >> (12-1) = 2x
Shift 2 = >> (12-2) = 4x
Shift 3 = >> (12-3) = 8x
Shift 4 = >> (12-4) = 16x
```

---

## Practical Examples

### Classroom Setup (Teacher Recording)

**Goal**: Pick up speech from anywhere in the room

```bash
# Step 1: Flash firmware with new gain feature
just flash

# Step 2: Start VAD monitoring
just vad-stream-relaxed-with-volume &

# Step 3: Test different gain levels
just mic-gain-medium    # Try 8x first

# Step 4: Walk around room and speak
# Listen to VAD output - speech should be detected

# Step 5: Adjust if needed
just mic-gain-max       # If still not picking up from far away
just mic-gain-min       # If too much background noise
```

### Podcast Recording (Close to Mic)

**Goal**: Prevent distortion from loud speaker very close to mic

```bash
# Use minimum gain to avoid clipping
just mic-gain-min

# Then record
just capture-pcm
```

### Meeting Scenario (Multiple Speakers)

**Goal**: Pick up all speakers regardless of distance

```bash
# Start with medium gain
just mic-gain-medium

# Monitor VAD while meeting happens
just vad-stream-relaxed-with-volume &

# Adjust on-the-fly if someone speaks from far away
just mic-gain-set 4    # Increase to 16x
```

---

## Troubleshooting

### "I'm not picking up audio from far away"

**Solution**: Increase gain
```bash
just mic-gain-max       # Try maximum (16x)
```

If still not working:
1. Check microphone connection
2. Verify firmware is flashed: `just flash`
3. Check serial port: `just check`

### "Audio sounds distorted/clipped"

**Solution**: Decrease gain
```bash
just mic-gain-min       # Try minimum (1x)
```

Or try intermediate levels:
```bash
just mic-gain-set 1     # 2x
just mic-gain-set 2     # 4x
```

### "Background noise is too loud"

**Solution**: Reduce gain to filter noise
```bash
# Lower gain means only loud sounds (speech) are captured clearly
just mic-gain-medium    # 8x instead of 16x
just mic-gain-min       # 1x if noise is severe
```

### "Gain isn't changing"

**Check 1**: Are you connected to the right serial port?
```bash
just check
```

**Check 2**: Is ESP32 firmware updated with gain feature?
```bash
just flash
```

**Check 3**: Try setting gain manually
```bash
python3 scripts/mic_gain_control.py /dev/tty.wchusbserial550D0193611 --gain 3
```

---

## Advanced Usage

### Setting Default Gain in Justfile

Edit `justfile` and change:
```bash
mic_gain := "4"    # Default to 4 (16x)
```

To:
```bash
mic_gain := "3"    # Default to 3 (8x)
```

### Scripting Gain Adjustment

```bash
#!/bin/bash
# my_meeting_recorder.sh

# Set up for meeting scenario
echo "Recording meeting with automatic gain adjustment..."

# Start VAD monitor
just vad-stream-relaxed-with-volume &
VAD_PID=$!

# Start capturing audio
just capture-pcm &
CAPTURE_PID=$!

# Wait 5 seconds then check if picking up speech
sleep 5

# If no speech detected, increase gain
echo "Checking audio levels..."
just mic-gain-max

# Continue for 1 hour
sleep 3600

# Clean up
kill $VAD_PID $CAPTURE_PID
```

---

## Understanding Noise vs Gain

### When Gain is TOO HIGH (16x):
```
Desirable sound: LOUD
Background noise: also LOUD
Distant speech: detectable but noisy
Result: False positives on noise
```

**Solution**: Lower gain to filter noise

### When Gain is TOO LOW (1x):
```
Desirable sound: detectable
Background noise: filtered out ✓
Distant speech: TOO QUIET to detect ✗
Result: Misses distant speakers
```

**Solution**: Raise gain to pick up speech

### Optimal Gain:
```
Desirable sound: CLEAR
Background noise: present but manageable
Distant speech: detectable ✓
Result: Good VAD accuracy
```

---

## Gain vs VAD Grace Period

These are **different** settings:

| Setting | Controls | Adjusts |
|---------|----------|---------|
| **Gain** | How loud the mic captures sound | Microphone sensitivity |
| **Grace Period** | How long before ending speech on silence | Speech detection timing |

**Use together**:
```bash
# Good microphone setup
just mic-gain-medium              # Capture audio well

# Good speech detection
just vad-stream-relaxed           # Handle natural pauses
```

---

## Specifications

### Gain Range
- **Minimum**: 1x (0 gain)
- **Maximum**: 16x (4 gain)
- **Default**: 16x (4 gain)

### Supported Distances
With default 16x gain:
- **Close** (0-1 foot): Works well
- **Medium** (1-10 feet): Works well
- **Far** (10-30 feet): Works with good microphone
- **Very far** (30+ feet): Difficult, may need external mic

### Audio Quality
- **Sample rate**: 16 kHz (fixed)
- **Bit depth**: 16-bit (fixed)
- **Channels**: Mono (fixed)
- **Adjustable**: Gain only

---

## Integration with Other Features

### With Volume Control
```bash
# Set microphone gain AND volume control
just mic-gain-medium                          # Adjust mic sensitivity
just vad-stream-relaxed-with-volume          # Auto volume adjustment
```

### With Recording
```bash
# Adjust gain before recording
just mic-gain-max                             # Maximize sensitivity

# Then record
just capture-pcm
```

### With MQTT Publishing
```bash
# Set gain, then start VAD with MQTT
just mic-gain-medium
just vad-live                                 # If you have MQTT setup
```

---

## Best Practices

1. **Start with medium gain (8x)** for most scenarios
2. **Adjust based on distance**:
   - Close (< 2 feet): Reduce gain
   - Medium (2-10 feet): Medium gain
   - Far (> 10 feet): Maximum gain
3. **Test with actual environment** before deploying
4. **Record a few seconds** to verify audio quality
5. **Adjust in small steps** (each level changes 2x sensitivity)

---

## Reference Table

### Quick Lookup

```
Need to pick up from...    → Use this command
─────────────────────────────────────────────
Very loud source (< 1 ft)  → just mic-gain-min
Normal speech (1-5 ft)     → just mic-gain-medium
Distant speech (5-20 ft)   → just mic-gain-max
Noisy environment          → Lower gain
Quiet environment          → Higher gain
Testing/tuning             → just mic-gain (interactive)
```

---

## Next Steps

1. **Flash firmware with gain feature**:
   ```bash
   just flash
   ```

2. **Test gain control**:
   ```bash
   just mic-gain
   ```

3. **Find your optimal gain for your environment**:
   ```bash
   just mic-gain-medium      # Start here
   just mic-gain-set 2       # Adjust as needed
   ```

4. **Run VAD with optimized settings**:
   ```bash
   just vad-stream-relaxed-with-volume
   ```

5. **Monitor and adjust**:
   ```bash
   just mic-gain-set 3       # Real-time adjustment
   ```

---

## Questions?

- **How do I know if gain is too high?** → Audio sounds distorted or picks up background noise
- **How do I know if gain is too low?** → Distant speech isn't detected by VAD
- **Can I change gain while streaming?** → Yes! Use `just mic-gain-set X`
- **Will changing gain affect speech detection?** → No, VAD adapts automatically
- **Do I need to restart ESP32 to change gain?** → No, serial command changes it instantly

---

Enjoy flexible microphone control! 🎙️