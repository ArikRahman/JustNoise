# Microphone Gain Quick Start

## What is Gain?

**Gain = Microphone Sensitivity (Amplification)**

- Higher gain → Picks up quieter/distant speech
- Lower gain → Only picks up loud/close speech

## One-Minute Setup

### Pick Your Scenario

**Distant speakers (lecture hall, large classroom)?**
```bash
just mic-gain-max
```
Uses 16x amplification — picks up even whispered speech from far away.

**Normal classroom/office distance?**
```bash
just mic-gain-medium
```
Uses 8x amplification — good balance for typical classroom setup.

**Loud speaker very close to microphone?**
```bash
just mic-gain-min
```
Uses 1x (no amplification) — prevents distortion.

**Don't know? Start here:**
```bash
just mic-gain-medium
```
Then adjust if needed.

---

## Real-Time Adjustment

Once you have the firmware flashed, you can adjust gain **while VAD is running**:

```bash
# Terminal 1: Start VAD monitoring
just vad-stream-relaxed-with-volume

# Terminal 2: Adjust gain on-the-fly
just mic-gain-set 3        # Change to 8x
just mic-gain-set 4        # Change to 16x
just mic-gain-set 2        # Change to 4x
```

No restart needed — changes apply instantly!

---

## Gain Levels at a Glance

| Level | Multiplier | Use Case |
|-------|-----------|----------|
| 0 | 1x | Loud speaker very close |
| 1 | 2x | Close/normal volume |
| 2 | 4x | Medium distance |
| 3 | 8x | **Classroom (recommended)** |
| 4 | 16x | Distant/quiet sources |

---

## How to Use

### Step 1: Flash Firmware
```bash
just flash
```

### Step 2: Set Microphone Gain
```bash
just mic-gain-medium
```

Or adjust interactively:
```bash
just mic-gain
# Type 0-4 to adjust gain, 'q' to quit
```

### Step 3: Start VAD
```bash
just vad-stream-relaxed-with-volume
```

### Step 4: Test
Speak at various distances from the microphone. Watch for consistent speech detection.

### Step 5: Fine-Tune if Needed
```bash
just mic-gain-set 2        # Too quiet? Increase gain
just mic-gain-set 4        # Too much noise? Decrease gain
```

---

## Quick Troubleshooting

**"I'm not picking up distant speech"**
```bash
just mic-gain-max
```

**"Audio sounds distorted/clipped"**
```bash
just mic-gain-min
```

**"Too much background noise"**
```bash
just mic-gain-medium
```

**"Gain isn't changing"**
```bash
just check              # Verify ESP32 is connected
just flash              # Update firmware with gain feature
```

---

## Interactive Mode (Easiest)

```bash
just mic-gain
```

Then:
- Type `3` to set 8x gain
- Type `4` to set 16x gain
- Type `i` to see current settings
- Type `q` to quit

Changes happen instantly. Perfect for finding your perfect setting!

---

## Integration with VAD

Gain is **separate** from VAD grace period:

```bash
# Set microphone sensitivity
just mic-gain-medium

# Set speech detection smoothness
just vad-stream-relaxed-with-volume
```

Both work together for best results.

---

## Pro Tips

1. **Start with medium (8x)** — good default for most classrooms
2. **Test your actual environment** — microphone placement matters
3. **Record while testing** — `just capture-pcm` to save audio for analysis
4. **Adjust in small steps** — each level changes 2x sensitivity
5. **Lower gain if noisy** — helps filter background noise

---

## Commands Reference

```bash
# Interactive (try different values)
just mic-gain

# Set specific level (0-4)
just mic-gain-set 3

# Quick presets
just mic-gain-max      # 16x
just mic-gain-medium   # 8x
just mic-gain-min      # 1x

# Test mode
just mic-gain-test 3
```

---

## Real-World Example

**Scenario: Recording a classroom lecture**

```bash
# Step 1: Flash firmware
just flash

# Step 2: Start VAD in one terminal
just vad-stream-relaxed-with-volume &

# Step 3: Adjust gain while listening
just mic-gain-set 3        # Try 8x first

# Walk around room, speak from different distances
# Watch VAD output — should detect speech from 3-15 feet away

# Step 4: Fine-tune if needed
just mic-gain-set 4        # Increase to 16x if needed
# or
just mic-gain-set 2        # Decrease to 4x if too much noise

# Step 5: Once dialed in, start recording
just capture-pcm
```

---

## That's It!

You now have adjustable microphone gain. Pick a level that works for your distance and environment.

**Still not sure which gain to use?**
```bash
just mic-gain-medium
```

This works for 90% of classroom/office scenarios. Then adjust if needed! 🎙️
