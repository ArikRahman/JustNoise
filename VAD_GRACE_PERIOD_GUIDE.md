# VAD Grace Period Tuning Guide

## What is the Grace Period?

The **grace period** (also called `min_silence_duration_ms`) is how long the VAD will wait for silence before deciding that speech has **ended**. A longer grace period means brief pauses (breathing, thinking, hesitation) won't abruptly cut off the speech detection.

### The Problem You're Experiencing
By default, the VAD is too sensitive to brief silences and cuts off speech detection immediately when it hears a pause. This means a single breath or short pause gets treated as a separate speech segment.

### The Solution
Increase the grace period so the VAD "waits" through brief pauses before ending the segment.

---

## Quick Start: Pick Your Preset

### Default (Balanced)
```bash
just vad-stream
```
- **Grace period**: 500ms (half second)
- **Best for**: Most classroom/office scenarios
- **Tradeoff**: May not catch very short speech bursts

### Relaxed (Recommended for Your Use Case)
```bash
just vad-stream-relaxed
```
- **Grace period**: 1000ms (1 second)
- **Best for**: Natural speech with pauses, breathing, hesitation
- **Tradeoff**: Slightly more delay before ending a speech segment

### Very Relaxed (Most Forgiving)
```bash
just vad-stream-very-relaxed
```
- **Grace period**: 1500ms (1.5 seconds)
- **Best for**: Teaching/lecture scenarios with frequent pauses between sentences
- **Tradeoff**: Longer wait times; may combine separate speakers if they speak close together

### Aggressive (Sensitive to Boundaries)
```bash
just vad-stream-aggressive
```
- **Grace period**: 200ms (0.2 seconds)
- **Best for**: Detecting rapid speech switches or intentional pauses
- **Tradeoff**: Will split speech on brief breathing pauses

### Custom
```bash
just vad-stream-custom min_silence="1200"
```
- **Grace period**: Whatever you specify (in milliseconds)
- **Best for**: Fine-tuning for your specific environment
- **Example**: `just vad-stream-custom min_silence="800"` for 800ms

---

## How to Tune

### Step 1: Start with Relaxed
```bash
just vad-stream-relaxed
```

### Step 2: Speak Naturally
- Talk in your normal classroom/meeting voice
- Include pauses between sentences
- Include breaths and hesitations
- Watch the output for speech segment boundaries

### Step 3: Adjust Based on Behavior

| If You See | Problem | Solution |
|-----------|---------|----------|
| Speech ends too quickly on pauses | Grace period too short | Increase it (try +250ms steps) |
| Separate speakers blended together | Grace period too long | Decrease it (try -250ms steps) |
| Perfect! | Just right | Keep it! |

### Step 4: Find Your Sweet Spot

Try these progressions:

**Too short → increase**:
```bash
just vad-stream-custom min_silence="500"   # baseline
just vad-stream-custom min_silence="750"   # add 250ms
just vad-stream-custom min_silence="1000"  # add another 250ms
```

**Too long → decrease**:
```bash
just vad-stream-custom min_silence="1500"  # baseline
just vad-stream-custom min_silence="1200"  # remove 300ms
just vad-stream-custom min_silence="1000"  # remove another 200ms
```

---

## What's Actually Happening

### Real-Time Flow (with 1000ms grace period)
```
🎤 Person speaks: "What is this?"
   └─ VAD detects speech → SPEECH STARTED

🎤 Brief pause/breath (200ms)
   └─ VAD hears silence... but waits (grace period active)

🎤 Person continues: "It's amazing!"
   └─ Grace period ends before 1000ms → still in SPEECH

🎤 Person stops talking (2000ms of silence)
   └─ Silence exceeds 1000ms → SPEECH ENDED
   └─ Entire segment treated as one continuous speech
```

### Without Grace Period (what's happening now)
```
🎤 Person speaks: "What is this?"
   └─ VAD detects speech → SPEECH STARTED

🎤 Brief pause/breath (200ms)
   └─ VAD hears silence → SPEECH ENDED ❌ (too quick!)

🎤 Person continues: "It's amazing!"
   └─ VAD detects speech → SPEECH STARTED ❌ (new segment)
```

---

## Recommended Starting Points by Use Case

### Classroom / Lecture
```bash
just vad-stream-relaxed
# (1000ms grace period)
# Teachers naturally pause between sentences
```

### Meeting / Conference
```bash
just vad-stream-custom min_silence="800"
# (800ms grace period)
# Professional speakers with moderate pauses
```

### Podcast / Interview
```bash
just vad-stream-relaxed
# (1000ms grace period)
# Long-form speaking with natural breath pauses
```

### Call Center / Rapid Exchange
```bash
just vad-stream-aggressive
# (200ms grace period)
# Quick back-and-forth requires sharp boundaries
```

### Noisy Environment
```bash
just vad-stream-very-relaxed
# (1500ms grace period)
# Longer grace period filters out noise-induced false ends
```

---

## Understanding the Output

When you run `just vad-stream-relaxed`, you'll see:

```
🎤 RAW PCM VOICE ACTIVITY MONITOR
===============================================
Serial Port:      /dev/tty.wchusbserial550D0193611
Baudrate:         921600
Sample Rate:      16000 Hz
Chunk Size:       512 samples (32ms)
Mode:             🔄 CONTINUOUS (Press Ctrl+C to stop)
Min Silence:      1000ms (grace period before ending speech)  ← YOUR SETTING
Min Speech:       0ms (minimum duration to accept speech)
===============================================

[timestamp] 🔴 VOCALS DETECTED - SPEECH STARTED!
⚪ SILENCE [████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 45.2%

[timestamp] 🟢 Speech ended (duration: 2.34s)
```

---

## Fine-Tuning Tips

### "Speech is being cut off mid-sentence"
→ Increase grace period by 250-500ms
```bash
just vad-stream-custom min_silence="1250"
```

### "Two different speakers are being merged into one segment"
→ Decrease grace period by 200-300ms
```bash
just vad-stream-custom min_silence="800"
```

### "False speech starts from ambient noise"
→ This is a different issue (threshold, not grace period)
→ Try: The grace period won't help; consider the `--min-speech` parameter (minimum speech duration)

### "Want to record and experiment"
Capture PCM while running VAD:
```bash
# Terminal 1: Run VAD with your chosen setting
just vad-stream-custom min_silence="1000"

# Terminal 2: Capture audio to files
just capture-pcm
```

Then play back with:
```bash
just play-last
```

---

## Command Reference

| Command | Grace Period | Use Case |
|---------|--------------|----------|
| `just vad-stream` | 500ms | Baseline/testing |
| `just vad-stream-relaxed` | 1000ms | **Recommended** for classroom |
| `just vad-stream-very-relaxed` | 1500ms | Very paused speech (lectures) |
| `just vad-stream-aggressive` | 200ms | Fast speech boundaries |
| `just vad-stream-custom min_silence="X"` | X ms | Precise tuning |

---

## Pro Tips

1. **Record a test session**: Run `just capture-pcm` while testing with different grace periods, then compare the output files.

2. **Watch the progress bar**: The confidence bar shows how confident VAD is that speech is happening. Higher = more confident speech.

3. **Trust your ears**: If it sounds right when you listen, the grace period is tuned correctly.

4. **Save your setting**: Once you find your sweet spot, update the justfile or create a wrapper script to remember your preference.

---

## What's Next?

- Once you've tuned the grace period, you can:
  - Run `just capture-pcm` to record with your tuned settings
  - Run `just vad-live` to publish VAD events to MQTT
  - Integrate with the decision node for automated actuation

---

## Troubleshooting

**"I'm not seeing any speech detection"**
- Make sure your microphone is plugged in
- Try speaking louder
- Check: `just check` to verify ESP32 connection

**"Everything is speech (even silence)"**
- Microphone gain too high
- Try a different threshold (this is separate from grace period)

**"Grace period doesn't seem to change anything"**
- Make sure you're using the right command
- Verify the parameter is showing in the header (it prints "Min Silence: XXXms")
- Try a much larger difference (500ms → 1500ms) to test

---

Happy tuning! 🎙️