# Volume Control Quick Start

## What This Does

Automatically lowers your Mac's speaker volume when you speak and raises it back to normal when you stop. Perfect for:
- **Classrooms** — Reduce distractions while teaching
- **Meetings** — Quiet notifications while speaking
- **Recording** — Prevent speaker feedback during capture
- **Focus** — Auto-mute background noise during talks

## Try It Right Now

```bash
just vad-stream-relaxed-with-volume
```

That's it. Speak into your microphone. Watch your system volume drop to 30% when you're talking and jump back to 100% when you stop.

## What You'll See

```
🎤 RAW PCM VOICE ACTIVITY MONITOR
===============================================
Min Silence:      1000ms (grace period before ending speech)
Volume Control:   ENABLED (30% when speaking, 100% when silent)
===============================================

🗣️🗣️🗣️🗣️🗣️🗣️🗣️🗣️🗣️🗣️
[12:34:56.789] 🔴 VOCALS DETECTED - SPEECH STARTED!
[12:34:56.790] 🔊 Volume set to 30%
🗣️🗣️🗣️🗣️🗣️🗣️🗣️🗣️🗣️🗣️

⚪ SILENCE [████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 45%

[12:34:58.234] 🟢 Speech ended (duration: 1.44s)
[12:34:58.235] 🔊 Volume set to 100%
```

## Commands

### Default (500ms grace period)
```bash
just vad-stream-with-volume
```
- Lowers to 30% when speaking
- Raises to 100% when silent
- Quick response (500ms grace period)

### Recommended (1000ms grace period)
```bash
just vad-stream-relaxed-with-volume
```
- Lowers to 30% when speaking
- Raises to 100% when silent
- Handles natural pauses (1000ms grace period) ⭐ **START HERE**

### Custom (Adjust everything)
```bash
just vad-stream-volume-custom min_silence="1000" speech_vol="20" silence_vol="100"
```
- `min_silence` — Grace period (milliseconds)
- `speech_vol` — Volume when speaking (0-100%)
- `silence_vol` — Volume when silent (0-100%)

## Examples

### Podcast Recording (Prevent Feedback)
```bash
just vad-stream-volume-custom min_silence="1000" speech_vol="10" silence_vol="100"
```
Ultra-quiet (10%) when recording, full volume when silent.

### Office Meeting (Gentle Control)
```bash
just vad-stream-relaxed-with-volume
```
Standard: 30% when speaking, 100% when silent.

### Gaming (Moderate Reduction)
```bash
just vad-stream-volume-custom min_silence="1500" speech_vol="50" silence_vol="75"
```
Never goes to full volume (hearing protection), long grace period.

### Classroom (Natural Speech)
```bash
just vad-stream-relaxed-with-volume
```
Perfect for teachers — pauses don't trigger volume changes.

## How It Works

1. You speak → VAD detects speech
2. `osascript -e "set volume output volume 30"` runs
3. Your system volume drops to 30%
4. You continue talking (pauses don't interrupt due to grace period)
5. You stop talking for > grace period
6. `osascript -e "set volume output volume 100"` runs
7. Your system volume rises back to 100%

## Volume Levels Guide

| Level | Effect | Use When |
|-------|--------|----------|
| 5-15% | Near silent | Recording/podcast (prevent feedback) |
| 20-30% | Quiet | Classroom/meeting (minimal distraction) |
| 40-50% | Moderate | Office (some audio still available) |
| 60-80% | Subtle | Gentle background control |
| 100% | Full volume | Normal level |

## Troubleshooting

### "Volume isn't changing"

**Check 1:** Is volume control enabled?
```bash
# Look for "Volume Control: ENABLED" in the header
just vad-stream-relaxed-with-volume
```

**Check 2:** Do you have permission?
1. System Preferences → Security & Privacy
2. Click Accessibility
3. Add Terminal (or your shell) to the list
4. Try again

**Check 3:** Is VAD detecting speech?
```bash
# Test VAD without volume control first
just vad-stream-relaxed
```

### "Volume is changing too quickly"

Increase grace period:
```bash
just vad-stream-volume-custom min_silence="1500" speech_vol="30" silence_vol="100"
```

### "Volume changes too slowly"

Decrease grace period:
```bash
just vad-stream-volume-custom min_silence="300" speech_vol="30" silence_vol="100"
```

## Recording + Volume Control

Run both at the same time:

**Terminal 1** (VAD with volume control):
```bash
just vad-stream-relaxed-with-volume
```

**Terminal 2** (Capture audio):
```bash
just capture-pcm
```

Press Ctrl+C to stop both. Your audio will be recorded while volume automatically adjusts.

## Disable Volume Control

To run VAD without volume control:
```bash
just vad-stream-relaxed
```

Volume control is **off by default** — you must enable it with a command that includes the flag.

## Quick Reference Table

| Want to... | Command | Speech Vol | Silence Vol | Grace Period |
|-----------|---------|-----------|------------|--------------|
| Try it out | `just vad-stream-relaxed-with-volume` | 30% | 100% | 1000ms |
| Record podcast | `just vad-stream-volume-custom min_silence="1000" speech_vol="10" silence_vol="100"` | 10% | 100% | 1000ms |
| Quick response | `just vad-stream-with-volume` | 30% | 100% | 500ms |
| Fine-tune | `just vad-stream-volume-custom min_silence="X" speech_vol="Y" silence_vol="Z"` | Custom | Custom | Custom |

## How the Grace Period Applies

Grace period controls **both** speech detection AND volume changes:

```
You speak → VAD detects → Volume drops to 30%
    ↓
[Brief pause/breath]
    ↓
Grace period counting... volume STAYS at 30%
    ↓
[You speak again before grace expires]
    ↓
Grace period resets → volume stays at 30%
    ↓
[Silence lasts > grace period]
    ↓
Speech ends → Volume raises to 100%
```

Longer grace period = smoother volume control during natural speech.

## Next Steps

1. **Try it**: `just vad-stream-relaxed-with-volume`
2. **Test your setup**: Speak naturally, watch volume changes
3. **Adjust if needed**: Use custom command to tune volumes/grace period
4. **Combine it**: Use with `just capture-pcm` to record simultaneously
5. **Integrate it**: Make it part of your workflow

---

**Enjoy automatic volume management!** 🔊
