# Quick VAD Grace Period Tuning

## TL;DR

Your VAD is **too quick to end speech** when it hears brief pauses (breathing, hesitation). You want a **longer grace period** — that's the `--min-silence` parameter.

### Try This Right Now
```bash
just vad-stream-relaxed
```

This gives a **1-second grace period** instead of the default 500ms. Speech won't end until there's a full second of silence.

---

## The Commands (Ranked by "Forgiving-ness")

| Command | Grace Period | When to Use |
|---------|--------------|------------|
| `just vad-stream-aggressive` | **200ms** | Detect fast speech boundaries |
| `just vad-stream` | **500ms** | Default (balanced) |
| `just vad-stream-relaxed` | **1000ms** | 👈 **Start here** — natural speech with pauses |
| `just vad-stream-very-relaxed` | **1500ms** | Lectures/long pauses between sentences |
| `just vad-stream-custom min_silence="900"` | **Custom** | Fine-tune your exact need |

---

## What You'll See

**Before** (sensitive, splits on pauses):
```
🔴 VOCALS DETECTED - SPEECH STARTED!   [person says "What is"]
🟢 Speech ended (duration: 0.3s)       [brief breath]
🔴 VOCALS DETECTED - SPEECH STARTED!   [person says "this?"]
🟢 Speech ended (duration: 0.2s)
```

**After** (relaxed, keeps pauses together):
```
🔴 VOCALS DETECTED - SPEECH STARTED!   [person says "What is" + breath + "this?"]
🟢 Speech ended (duration: 0.8s)       [after 1 full second of silence]
```

---

## How to Tune

1. **Start**: `just vad-stream-relaxed`
2. **Speak naturally** near the mic (include breaths, pauses)
3. **Watch the output** for speech segment boundaries
4. **Adjust** if needed:
   - Too short on pauses? → Use `very-relaxed` or `custom min_silence="1200"`
   - Too long (merges speakers)? → Use `custom min_silence="800"`

---

## What's Actually Changing

The grace period controls how long the VAD **waits for silence** before deciding speech has ended.

- **Short grace period (200ms)**: Speech ends immediately when any silence is heard
- **Long grace period (1500ms)**: Speech can pause for up to 1.5 seconds and still be one segment

---

## For Your Classroom/Office

**Recommendation**: Start with `just vad-stream-relaxed` (1000ms).

This handles:
- ✅ Natural breathing pauses
- ✅ Thinking pauses ("umm...")
- ✅ Sentence breaks
- ✅ Hesitations
- ✅ Typical speech patterns

If two speakers are being merged, drop it to `just vad-stream-custom min_silence="750"`.
If speech is still being cut off, raise it to `just vad-stream-very-relaxed` (1500ms).

---

## Run While Recording

Want to capture audio and test VAD at the same time?

**Terminal 1** (run VAD with your grace period):
```bash
just vad-stream-relaxed
```

**Terminal 2** (capture the audio):
```bash
just capture-pcm
```

Press Ctrl+C to stop. Then play back and verify the speech boundaries match what you expect:
```bash
just play-last
```

---

## Pro Tip: Experiment

Each grace period takes ~10-20 seconds to judge. Try these in sequence:
```bash
just vad-stream-relaxed         # 1000ms
# Speak, watch output, assess
# If good, done! If not...

just vad-stream-custom min_silence="1200"  # Try longer
# Repeat

just vad-stream-custom min_silence="800"   # Try shorter
# Repeat
```

Find the sweet spot where pauses stay grouped but different speakers are separate.

---

## Commands Reference

```bash
just vad-stream                    # 500ms (default)
just vad-stream-relaxed           # 1000ms (recommended start)
just vad-stream-very-relaxed      # 1500ms (most forgiving)
just vad-stream-aggressive        # 200ms (most sensitive)
just vad-stream-custom min_silence="1100"  # Custom value (milliseconds)
```

---

Done! Start with `just vad-stream-relaxed` and tune from there. 🎙️