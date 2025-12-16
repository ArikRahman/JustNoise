# Visual Guide: Grace Period Effects

## The Problem (Default 500ms)

```
Timeline of speech with natural pause:

Speaker: "What is..." [brief breath/pause] "...this?"
         ▁▁▁▁▁▁▁▁▁▁░░░░░░░▁▁▁▁▁▁▁▁▁▁▁▁
         
         |-- 200ms --|
         
VAD sees:
[SPEECH DETECTED ✓]
  ↓ (200ms silence)
[SPEECH ENDED ✗] ← Too quick!
  ↓ (instantly starts listening again)
[SPEECH DETECTED ✓] ← Treats as new segment


Result: ONE sentence split into 2-3 segments ❌
```

## The Solution (1000ms Grace Period - RELAXED)

```
Same speaker, same pause:

Speaker: "What is..." [brief breath/pause] "...this?"
         ▁▁▁▁▁▁▁▁▁▁░░░░░░░▁▁▁▁▁▁▁▁▁▁▁▁
         
         |-- 200ms --|
         grace: 1000ms
         |----------|

VAD sees:
[SPEECH DETECTED ✓]
  ↓ (200ms silence - but grace period is 1000ms)
[WAITING... grace period counting: 200ms < 1000ms]
  ↓ (new speech starts before grace expires)
[GRACE PERIOD RESETS - still SPEECH ✓]


Result: ONE sentence = ONE segment ✅
```

## Grace Period Settings Comparison

### 200ms (AGGRESSIVE)
```
Duration: 0.2 seconds
Visual:   ░

Perfect for: Rapid speech detection
Problem: Cuts off on ANY pause
Use when: You need sharp speech boundaries
```

### 500ms (DEFAULT)
```
Duration: 0.5 seconds
Visual:   ░░

Perfect for: General use
Problem: Cuts off on breathing pauses
Use when: Fine-tuning other parameters
```

### 1000ms (RELAXED) ⭐ RECOMMENDED
```
Duration: 1.0 seconds
Visual:   ░░░░░░░░░░

Perfect for: Classroom, natural speech
Problem: May merge very close speakers
Use when: Starting to tune for your use case
```

### 1500ms (VERY RELAXED)
```
Duration: 1.5 seconds
Visual:   ░░░░░░░░░░░░░░░░

Perfect for: Lectures, long pauses
Problem: Definitely merges speakers
Use when: Speech has very long pauses
```

---

## Real-World Scenarios

### Classroom Teacher (Try: RELAXED 1000ms)
```
Teacher: "Today we'll learn..." [thinks for 1.5s] "...about biology."
         ▁▁▁▁▁▁▁▁▁▁▁▁▁░░░░░░░░░░░░▁▁▁▁▁▁▁▁▁▁▁▁▁▁
         
         ← ~200ms → ← thinking ~1.5s → ← continues →

With 1000ms grace:
  ✓ SPEECH (thinking counted as pause, not end)
  ✓ One segment for whole sentence
  
With 500ms grace:
  ✗ SPEECH END after thinking starts
  ✗ New segment when continues
```

### Student Answering (Try: RELAXED 1000ms)
```
Student: "Um..." [hesitation ~800ms] "...the answer is 42."
         ▁░░░░░░░░░▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁

With 1000ms grace:
  ✓ Whole answer is one segment
  
With 500ms grace:
  ✗ "Um" is separate segment
  ✗ Answer is separate segment
```

### Back-and-Forth Dialogue (Try: AGGRESSIVE 200ms)
```
Person A: "Ready?"      Person B: "Yes!"
         ▁▁▁▁░░░░░░░▁▁▁
         
With 200ms grace:
  ✓ Two clear separate segments
  
With 1000ms grace:
  ? May merge if timing is tight
```

---

## Decision Tree: Which Grace Period?

```
Does your speech have natural pauses?
│
├─ YES (breathing, thinking, hesitation)
│  └─ Use RELAXED (1000ms) or VERY RELAXED (1500ms)
│
└─ NO (rapid, staccato speech)
   └─ Use DEFAULT (500ms) or AGGRESSIVE (200ms)


Are two speakers being merged?
│
├─ YES (one segment when should be two)
│  └─ DECREASE grace period (try -250ms)
│
└─ NO (separate segments when should be one)
   └─ INCREASE grace period (try +250ms)
```

---

## How to Read the Output

```
🎤 RAW PCM VOICE ACTIVITY MONITOR
===============================================
Min Silence: 1000ms ← This is your grace period
```

When you see:
```
🔴 VOCALS DETECTED - SPEECH STARTED!
[progress bar showing confidence]

[pause happens here]

[still showing progress bar? grace period is working ✓]

🟢 Speech ended (duration: 2.45s)
```

The 2.45s duration = the entire sentence with pauses = ONE segment ✓

---

## Step-by-Step Tuning Visual

```
Session 1: just vad-stream-relaxed (1000ms)
Speaker: "Hello." [breath] "How are you?"
Result:  [=========ONE SEGMENT=========] ✓
Decision: GOOD! Keep it.

Session 2: just vad-stream-custom min_silence="1200"
Speaker: [same as above]
Result:  [=========ONE SEGMENT=========] ✓
Decision: Also good, slightly more forgiving.

Session 3: just vad-stream-aggressive (200ms)
Speaker: [same as above]
Result:  [===END] [breath] [===END] ✗
Decision: Too sensitive, revert to 1000ms.
```

---

## Grace Period vs Other Parameters

```
Grace Period (min_silence_ms)
├─ Affects: How long silence must persist to end speech
├─ Range: 200ms - 1500ms (your new options)
└─ What to tune: If pauses are being cut off

Threshold (built-in)
├─ Affects: What counts as "speech" vs "noise"
├─ Range: 0.0 - 1.0
└─ What to tune: If picking up background noise as speech

Min Speech Duration (min_speech_ms)
├─ Affects: Minimum speech burst length to count
├─ Range: 0ms - 500ms
└─ What to tune: If picking up single coughs as speech

You can adjust these independently! Start with grace period.
```

---

## Quick Decision Table

| Your Issue | Observation | Fix | Command |
|-----------|-------------|-----|---------|
| Speech cuts off at pauses | "What is" → END → "this?" | Increase grace | `just vad-stream-relaxed` |
| Still cutting off | Still happening with 1000ms | Very long grace | `just vad-stream-very-relaxed` |
| Two speakers merged | One segment when should be two | Decrease grace | `just vad-stream-custom min_silence="750"` |
| Background noise detected | Noise triggering speech | Not grace period | This is a threshold issue (future tuning) |
| Perfect! | Pauses grouped, speakers separate | Keep it | Remember your command |

---

## Summary

```
🎙️ OLD (500ms grace) → Speech ends immediately on pause
   
   "What is" [breath] "this?"
   └─ SEGMENT 1 ┘ └─ SEGMENT 2 ┘ ✗

🎙️ NEW (1000ms grace) → Pauses don't end speech
   
   "What is" [breath] "this?"
   └─ ONE SEGMENT ─────────────┘ ✓
```

**Start with**: `just vad-stream-relaxed`
**Tune to**: Your environment
**Enjoy**: Natural speech detection without jitter!