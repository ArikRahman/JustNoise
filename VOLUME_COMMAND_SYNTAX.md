# Volume Control Command Syntax Reference

## Quick Summary

**Just uses positional arguments, NOT key=value syntax**

### ❌ WRONG
```bash
just vad-stream-volume-custom min_silence="1000" speech_vol="60" silence_vol="100"
```

### ✅ CORRECT
```bash
just vad-stream-volume-custom 1000 60 100
```

---

## Available Commands

### 1. Recommended (Easiest)
```bash
just vad-stream-relaxed-with-volume
```
- Grace period: 1000ms
- Speech volume: 30%
- Silence volume: 100%
- **No arguments needed**

---

### 2. Default with Volume Control
```bash
just vad-stream-with-volume
```
- Grace period: 500ms
- Speech volume: 30%
- Silence volume: 100%
- **No arguments needed**

---

### 3. Custom (All Parameters)
```bash
just vad-stream-volume-custom <grace_period> <speech_volume> <silence_volume>
```

**Arguments:**
1. `<grace_period>` — Milliseconds (e.g., 1000)
2. `<speech_volume>` — Percentage 0-100 (e.g., 60)
3. `<silence_volume>` — Percentage 0-100 (e.g., 100)

**Examples:**

Natural speech (1 second grace, 60% volume when speaking):
```bash
just vad-stream-volume-custom 1000 60 100
```

Quick response (500ms grace, 30% volume):
```bash
just vad-stream-volume-custom 500 30 100
```

Podcast (1 second grace, 10% volume when speaking):
```bash
just vad-stream-volume-custom 1000 10 100
```

Hearing protection (never go above 50%):
```bash
just vad-stream-volume-custom 1000 30 50
```

---

### 4. Preset: Podcast
```bash
just vad-stream-volume-podcast
```
- Grace period: 1000ms
- Speech volume: 10% (ultra-quiet, prevents feedback)
- Silence volume: 100%

**Override defaults:**
```bash
just vad-stream-volume-podcast 1200 15
```
(grace_period=1200ms, speech_volume=15%)

---

### 5. Preset: Gaming/Focus
```bash
just vad-stream-volume-gaming
```
- Grace period: 1500ms (long pauses)
- Speech volume: 50% (moderate)
- Silence volume: 75% (never full volume)

**Override defaults:**
```bash
just vad-stream-volume-gaming 1200 40
```
(grace_period=1200ms, speech_volume=40%)

---

### 6. Preset: Office
```bash
just vad-stream-volume-office
```
- Grace period: 1000ms
- Speech volume: 75% (gentle reduction)
- Silence volume: 100%

**Override defaults:**
```bash
just vad-stream-volume-office 1200 80
```
(grace_period=1200ms, speech_volume=80%)

---

## Parameter Explanation

### Grace Period (Milliseconds)

How long VAD waits before ending speech when silence is detected.

| Value | Effect | Use Case |
|-------|--------|----------|
| 200 | Very responsive (rapid on/off) | Fast speech boundaries |
| 500 | Responsive (default) | General use |
| 1000 | Smooth (handles pauses) | **Natural speech** ⭐ |
| 1500 | Very smooth (handles long pauses) | Lectures |
| 2000+ | Extremely smooth | Special cases |

### Speech Volume (0-100%)

System volume when speech is detected.

| Value | Effect | Use Case |
|-------|--------|----------|
| 0-10% | Near silent | Recording/podcast (prevent feedback) |
| 10-30% | Quiet | Classroom/meeting |
| 30-50% | Moderate | Office/balanced |
| 50-75% | Subtle | Gentle control |
| 75-100% | Minimal/none | Hearing protection |

### Silence Volume (0-100%)

System volume when silent/not speaking.

| Value | Effect | Use Case |
|-------|--------|----------|
| 0% | Mute | Complete silence |
| 25-50% | Quiet | Hearing protection |
| 75% | Moderate | Balanced |
| 100% | Full | Normal level |

---

## Real-World Examples

### Classroom Teaching
```bash
just vad-stream-relaxed-with-volume
```
- Natural pauses handled smoothly
- Moderate volume reduction
- Ready to go, no tuning needed

### Podcast Recording
```bash
just vad-stream-volume-podcast
```
Or custom:
```bash
just vad-stream-volume-podcast 1000 8
```
- Ultra-quiet during speech (prevents feedback)
- Full volume when silent (hear audio cues)

### Gaming/Focus Session
```bash
just vad-stream-volume-gaming
```
Or custom:
```bash
just vad-stream-volume-gaming 1200 40
```
- Never goes to full volume (hearing protection)
- Long grace period (natural speech)
- Moderate reduction (notifications still audible)

### Office Meeting
```bash
just vad-stream-relaxed-with-volume
```
Or gentle reduction:
```bash
just vad-stream-volume-office
```
- Minimal volume change (still hear notifications)
- Smooth grace period (natural speech)
- Professional setup

### Library/Quiet Environment
```bash
just vad-stream-volume-custom 1000 5 50
```
- Ultra-quiet speaking (5%)
- Quiet when silent (50%)
- Extreme consideration for surroundings

---

## Common Use Cases Cheat Sheet

```bash
# Natural speech (classroom, teaching)
just vad-stream-relaxed-with-volume

# Podcast (prevent feedback)
just vad-stream-volume-podcast

# Gaming/Focus (hearing protection)
just vad-stream-volume-gaming

# Office (gentle reduction)
just vad-stream-volume-office

# Quick response (testing)
just vad-stream-with-volume

# Custom (your exact needs)
just vad-stream-volume-custom 1000 30 100
```

---

## Troubleshooting

### "I'm getting an error about invalid int value"

**Problem:** You're using key=value syntax
```bash
❌ just vad-stream-volume-custom min_silence="1000" speech_vol="60" silence_vol="100"
```

**Solution:** Use positional arguments (just numbers)
```bash
✅ just vad-stream-volume-custom 1000 60 100
```

### "Which command was I using?"

If you want to remember your favorite setup:

**Option 1:** Use a preset
```bash
just vad-stream-relaxed-with-volume
```

**Option 2:** Use one of the preset aliases
```bash
just vad-stream-volume-podcast
just vad-stream-volume-gaming
just vad-stream-volume-office
```

**Option 3:** Create your own shell alias
```bash
alias my-vad="just vad-stream-volume-custom 1000 60 100"
# Then use: my-vad
```

### "Can I just use one command for everything?"

Yes! Use:
```bash
just vad-stream-relaxed-with-volume
```
This is optimized for natural speech and works great for most cases.

---

## Understanding the Output

When you run a command, you'll see:

```
🎤 Starting VAD with custom volume control...
💡 Grace period: 1000ms | Speech volume: 60% | Silence volume: 100%

🎤 RAW PCM VOICE ACTIVITY MONITOR
===============================================
Serial Port:      /dev/tty.wchusbserial550D0193611
Baudrate:         921600
Sample Rate:      16000 Hz
Chunk Size:       512 samples (32ms)
Mode:             🔄 CONTINUOUS (Press Ctrl+C to stop)
Min Silence:      1000ms (grace period before ending speech)
Min Speech:       0ms (minimum duration to accept speech)
Volume Control:   ENABLED (60% when speaking, 100% when silent)  ← Your settings
===============================================
```

This confirms your parameters are set correctly.

---

## Quick Decision Tree

```
Do you want easy, no-tuning setup?
  └─ Yes: just vad-stream-relaxed-with-volume
  └─ No:  Continue below

Do you know exactly what you need?
  └─ Yes: just vad-stream-volume-custom <grace> <speech> <silence>
  └─ No:  Continue below

What's your primary use case?
  ├─ Recording/podcast: just vad-stream-volume-podcast
  ├─ Gaming/focus: just vad-stream-volume-gaming
  ├─ Office/meeting: just vad-stream-volume-office
  └─ Something else: just vad-stream-relaxed-with-volume
```

---

## Formula for Custom Commands

**3 numbers, in this order:**

```
just vad-stream-volume-custom [grace_period_ms] [speech_vol_%] [silence_vol_%]
                              └─ 200-2000ms      └─ 0-100%      └─ 0-100%
```

Examples:
- `just vad-stream-volume-custom 1000 30 100` — Classic setup
- `just vad-stream-volume-custom 500 60 100` — Quick response
- `just vad-stream-volume-custom 1500 20 80` — Hearing protection
- `just vad-stream-volume-custom 800 50 100` — Balanced

---

**Remember:** Positional arguments (just the numbers), no key=value pairs! ✅