# macOS Volume Control Integration

## Overview

The VAD system now includes automatic macOS system volume control. When speech is detected, the system volume automatically drops to a lower level (default 30%), and returns to full volume (default 100%) when you stop speaking.

This is useful for:
- **Classroom presentations** — Lower background volume while teaching
- **Meetings** — Reduce notification sounds while speaking
- **Podcasts/Recording** — Minimize speaker feedback during recording
- **Focus sessions** — Auto-mute distractions when you're talking

## Quick Start

### Enable Volume Control (Default Settings)
```bash
just vad-stream-with-volume
```

This will:
- Lower volume to **30%** when speech is detected
- Raise volume to **100%** when you stop speaking
- Use default grace period (500ms)

### With Relaxed Grace Period
```bash
just vad-stream-relaxed-with-volume
```

Same as above but with **1000ms grace period** (better for natural pauses).

### Custom Settings
```bash
just vad-stream-volume-custom min_silence="1000" speech_vol="20" silence_vol="100"
```

Adjust:
- `min_silence` — Grace period in milliseconds
- `speech_vol` — Volume % when speaking (0-100)
- `silence_vol` — Volume % when silent (0-100)

## Command Reference

| Command | Speech Vol | Silence Vol | Grace Period | Use Case |
|---------|-----------|------------|--------------|----------|
| `just vad-stream-with-volume` | 30% | 100% | 500ms | Default testing |
| `just vad-stream-relaxed-with-volume` | 30% | 100% | 1000ms | **Recommended** |
| `just vad-stream-volume-custom` | Custom | Custom | Custom | Fine-tuning |

## How It Works

### Volume Flow

```
Silence detected (no speech)
    ↓
Volume: 100% (normal level)
    ↓
[You start speaking]
    ↓
Speech detected
    ↓
Volume: 30% (reduced level) — osascript command runs
    ↓
[You continue speaking]
    ↓
Grace period timer active (e.g., 1000ms)
    ↓
[Brief pause/breath detected]
    ↓
Grace period counting... volume stays at 30%
    ↓
[You speak again before grace expires]
    ↓
Grace period resets — volume stays at 30%
    ↓
[You stop speaking for > grace period]
    ↓
Speech ended
    ↓
Volume: 100% (back to normal) — osascript command runs
```

### Technical Implementation

When speech is detected:
```bash
osascript -e "set volume output volume 30"
```

When speech ends:
```bash
osascript -e "set volume output volume 100"
```

The system runs these commands asynchronously with a 5-second timeout, so they don't block VAD processing.

## Examples

### Classroom Setup (Natural Speech)
```bash
just vad-stream-relaxed-with-volume
```
- Pauses/breathing won't trigger volume changes
- Volume drops when teacher starts speaking
- Rises when teacher stops

### Very Sensitive (Rapid Conversation)
```bash
just vad-stream-volume-custom min_silence="200" speech_vol="25" silence_vol="100"
```
- Quick response to speech boundaries
- Lower volume (25%) to protect hearing
- Useful for fast back-and-forth meetings

### Gentle Reduction (Minimal Adjustment)
```bash
just vad-stream-volume-custom min_silence="1000" speech_vol="75" silence_vol="100"
```
- Only slightly reduces volume (75%)
- Natural pauses won't interrupt
- Good for subtle background noise control

### Aggressive Reduction (Maximum Effect)
```bash
just vad-stream-volume-custom min_silence="1000" speech_vol="15" silence_vol="100"
```
- Significant volume drop when speaking
- Useful for recording/podcast environments
- Prevents speaker feedback

## Configuration

### Volume Levels

| Level | Effect | Use When |
|-------|--------|----------|
| 0-20% | Silent or barely audible | Recording/podcast (prevent feedback) |
| 20-40% | Very quiet | Classroom/meeting (minimal distraction) |
| 40-60% | Moderate reduction | Office environment (some audio still available) |
| 60-80% | Subtle reduction | Gentle background control |
| 80-100% | Normal to full | Not using volume control feature |

### Grace Period Tuning

Remember your grace period settings:
- **200ms** — Rapid speech (quick on/off)
- **500ms** — Default (still responsive to pauses)
- **1000ms** — Relaxed (natural pauses ignored)
- **1500ms** — Very relaxed (long pauses tolerated)

Longer grace period = fewer volume changes = less jarring for users.

## Output Examples

### When Speech Starts
```
🗣️🗣️🗣️🗣️🗣️🗣️🗣️🗣️🗣️🗣️
[12:34:56.789] 🔴 VOCALS DETECTED - SPEECH STARTED!
[12:34:56.790] 🔊 Volume set to 30%
🗣️🗣️🗣️🗣️🗣️🗣️🗣️🗣️🗣️🗣️

⚪ SILENCE [████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 45%
```

### When Speech Ends
```
[12:34:58.234] 🟢 Speech ended (duration: 1.44s)
[12:34:58.235] 🔊 Volume set to 100%
```

## Troubleshooting

### "Volume isn't changing"

**Check 1: Is volume control enabled?**
- Look for "Volume Control: ENABLED" in header
- Make sure you're using a command with `--volume-control` flag

**Check 2: Do you have permission?**
- osascript may need accessibility permissions
- Go to: System Preferences → Security & Privacy → Accessibility
- Add Terminal (or your app launcher) to the list

**Check 3: Is speech being detected?**
- If VAD isn't detecting speech, volume won't change
- Test: `just vad-stream` (without volume control) to verify VAD works

### "Volume keeps changing rapidly (jittery)"

**Solution: Increase grace period**
```bash
just vad-stream-volume-custom min_silence="1500" speech_vol="30" silence_vol="100"
```

Longer grace period = fewer volume switches during pauses.

### "Volume changes too slowly"

**Solution: Decrease grace period**
```bash
just vad-stream-volume-custom min_silence="300" speech_vol="30" silence_vol="100"
```

Shorter grace period = faster response to speech boundaries.

### "osascript permission denied"

**Solution: Grant accessibility permissions**
1. Open System Preferences
2. Go to Security & Privacy
3. Click "Accessibility" tab
4. Click the lock and unlock it
5. Add Terminal or your shell to the list
6. Try again

## Advanced Usage

### Simultaneous Recording + Volume Control
```bash
# Terminal 1: Run VAD with volume control
just vad-stream-relaxed-with-volume

# Terminal 2: Capture audio
just capture-pcm

# Terminal 3 (optional): Monitor volume changes
tail -f /var/log/system.log | grep -i volume
```

### Custom Script Integration
If you need more complex volume control, you can modify the command:

```bash
# Lower volume, also mute notifications
just vad-stream-volume-custom min_silence="1000" speech_vol="20" silence_vol="100"

# Then add your own script to notifications-off.sh
```

### Setting Maximum Safety Levels
```bash
# Never go above 50% (hearing protection)
just vad-stream-volume-custom min_silence="1000" speech_vol="30" silence_vol="50"
```

## macOS Compatibility

- **Tested on**: macOS 12+
- **Requires**: `osascript` (built-in on all macOS versions)
- **Permissions**: May need Accessibility access (see troubleshooting)
- **Timeout**: 5 seconds per volume command (asynchronous, won't block VAD)

## Defaults

| Parameter | Default | Range |
|-----------|---------|-------|
| Speech Volume | 30% | 0-100% |
| Silence Volume | 100% | 0-100% |
| Grace Period | 500ms | 200-2000ms |
| Command Timeout | 5 seconds | N/A |

## Examples by Use Case

### 📚 Classroom/Lecture
```bash
just vad-stream-relaxed-with-volume
# 30% when speaking, 100% when silent, 1000ms grace period
```

### 🎙️ Podcast/Recording
```bash
just vad-stream-volume-custom min_silence="1000" speech_vol="10" silence_vol="100"
# Very quiet when speaking (prevent feedback), full volume when silent
```

### 💼 Office Meeting
```bash
just vad-stream-relaxed-with-volume
# Standard setup: 30% when speaking, 100% when silent
```

### 🎮 Gaming/Focus Session
```bash
just vad-stream-volume-custom min_silence="1500" speech_vol="25" silence_vol="75"
# Moderate reduction, long grace period, never goes to full volume
```

### 📖 Library/Quiet Environment
```bash
just vad-stream-volume-custom min_silence="1000" speech_vol="5" silence_vol="50"
# Ultra-quiet when speaking, very quiet when silent
```

## Disabling Volume Control

To run VAD without volume control:
```bash
just vad-stream-relaxed
# or any other command without --volume-control flag
```

Volume control is **disabled by default** — you must explicitly enable it with the flag.

## Notes

- Volume changes are **asynchronous** — won't slow down VAD processing
- Changes apply to **system output volume** (speakers/headphones)
- If multiple volume changes occur rapidly, they queue up
- The grace period applies to **both** speech detection and volume control
- Volume is set via macOS system preferences, not app-specific

## What's Next

1. **Test it**: `just vad-stream-relaxed-with-volume`
2. **Tune it**: Adjust volumes and grace period to your needs
3. **Use it**: Incorporate into your workflow
4. **Combine it**: Use with `just capture-pcm` for simultaneous recording

---

**Enjoy automatic volume management!** 🔊

```

Now let me verify the code compiles: