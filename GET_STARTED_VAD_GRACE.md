# Getting Started: VAD Grace Period (Speech Pause Tolerance)

## What Just Happened?

Your VAD was **hearing silence and immediately stopping speech detection**. Now it has a "grace period" — it waits for sustained silence before ending a speech segment. Brief pauses (breathing, thinking) no longer cut off your speech.

## Right Now: Try This

```bash
just vad-stream-relaxed
```

That's it. Speak into your microphone naturally — include pauses, breathing, hesitation. Watch the output. Speech segments should now stay together through pauses.

## What You'll See

**Before** (too sensitive):
```
🔴 VOCALS DETECTED - SPEECH STARTED!
[person says "What is"]
🟢 Speech ended (duration: 0.3s)
[person takes breath]
🔴 VOCALS DETECTED - SPEECH STARTED!
[person says "this?"]
🟢 Speech ended (duration: 0.2s)
```

**After** (with grace period):
```
🔴 VOCALS DETECTED - SPEECH STARTED!
[person says "What is" + breath + "this?"]
🟢 Speech ended (duration: 0.8s)
```

## The Commands

| What You Want | Command | Grace Period |
|---------------|---------|--------------|
| Start here (natural speech) | `just vad-stream-relaxed` | **1000ms** ⭐ |
| Very forgiving (lectures) | `just vad-stream-very-relaxed` | 1500ms |
| Balanced (default) | `just vad-stream` | 500ms |
| Quick boundaries (rapid speech) | `just vad-stream-aggressive` | 200ms |
| Custom tuning (your milliseconds) | `just vad-stream-custom min_silence="900"` | X ms |

## How to Tune

### Step 1: Flash (if you haven't)
```bash
just flash
```

### Step 2: Start monitoring
```bash
just vad-stream-relaxed
```

### Step 3: Speak naturally
- Include pauses between sentences
- Include breathing and hesitation
- Watch the output for 10-20 seconds

### Step 4: Assess
- ✅ Pauses are staying together? Perfect! You're done.
- ❌ Speech still being cut off? Try `just vad-stream-very-relaxed`
- ❌ Different speakers merging? Try `just vad-stream-custom min_silence="800"`

### Step 5: Repeat until satisfied
Once you find your sweet spot, remember that command!

## Simultaneous Recording

Want to capture audio while testing VAD?

**Terminal 1** (run VAD):
```bash
just vad-stream-relaxed
```

**Terminal 2** (capture audio):
```bash
just capture-pcm
```

Then play back:
```bash
just play-last
```

Verify the speech boundaries match what you heard.

## What's a Grace Period?

Think of it like this:

**Without grace period (too quick)**:
- VAD hears any silence → immediately ends speech ❌

**With grace period (waits)**:
- VAD hears silence → starts counting
- If speech resumes before timer expires → resets timer, still one segment ✓
- If silence lasts longer than grace period → ends segment

Grace period = how long VAD waits (in milliseconds) before deciding speech really ended.

## Grace Period Values Explained

| Value | Behavior | Use When |
|-------|----------|----------|
| 200ms | Super sensitive (cuts off on any pause) | You want quick speech boundaries |
| 500ms | Moderate (default) | Fine-tuning other things |
| 1000ms | Forgiving (waits 1 second) | **Natural speech with pauses** ← Start here |
| 1500ms | Very forgiving (waits 1.5s) | Long pauses between sentences |
| 2000ms+ | Extremely forgiving | Rare scenarios; usually overkill |

## Recommended Settings by Scenario

### Classroom
```bash
just vad-stream-relaxed  # 1000ms
```
Teachers pause naturally between points. This handles it.

### Meeting
```bash
just vad-stream-custom min_silence="800"  # 800ms
```
Professional speakers with moderate pauses.

### Podcast/Interview
```bash
just vad-stream-relaxed  # 1000ms
```
Long-form speaking with natural breath pauses.

### Fast Conversation
```bash
just vad-stream-aggressive  # 200ms
```
Quick back-and-forth requires sharp boundaries.

## Troubleshooting

### "Speech is still being cut off at pauses"
→ Your grace period is too short
→ Try: `just vad-stream-very-relaxed` (1500ms)
→ Or: `just vad-stream-custom min_silence="1200"`

### "Different speakers are being merged into one segment"
→ Your grace period is too long
→ Try: `just vad-stream-custom min_silence="750"`
→ Or: `just vad-stream-custom min_silence="600"`

### "It's perfect! How do I remember this?"
→ Save the command in a text file
→ Or create an alias in your shell config
→ Or just keep this guide handy

### "I'm not seeing any speech detected at all"
→ This isn't a grace period issue
→ Check: Is your microphone connected? `just check`
→ Try speaking louder
→ Verify ESP32 is flashed: `just flash`

## What Changed

Behind the scenes:

1. **`vad_stream.py`** — Now accepts `--min-silence` parameter
2. **`vad.py`** — SileroVAD accepts `min_silence_duration_ms` parameter
3. **`justfile`** — New commands with presets for quick access

All backwards compatible. Nothing broke.

## Next Steps

1. ✅ Test with `just vad-stream-relaxed`
2. ✅ Tune to your environment
3. ✅ Capture audio with `just capture-pcm` to verify
4. ✅ Use in production with your favorite setting

## Questions?

- **Quick answers**: Read `QUICK_VAD_GRACE.md`
- **Detailed guide**: Read `VAD_GRACE_PERIOD_GUIDE.md`
- **Visual examples**: Read `GRACE_PERIOD_VISUAL.md`
- **Technical details**: Read `VAD_GRACE_CHANGES.md`

## TL;DR

```bash
# Right now, try this:
just vad-stream-relaxed

# Speak naturally, watch output
# If good → you're done!
# If not → tune with: just vad-stream-custom min_silence="YOUR_VALUE"
```

---

**Happy speech detecting!** 🎙️