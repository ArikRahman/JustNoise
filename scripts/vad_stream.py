#!/usr/bin/env python3
"""
Real-time VAD Monitor - Continuous raw PCM streaming from ESP32.

Reads raw 16-bit PCM samples directly from ESP32 serial stream (no WAV headers)
and feeds them into Silero VAD for real-time speech detection.

Usage:
  python vad_stream.py /dev/tty.wchusbserial550D0193611
  python vad_stream.py /dev/tty.wchusbserial550D0193611 --baudrate 921600
  python vad_stream.py /dev/tty.wchusbserial550D0193611 --min-silence 1500 --min-speech 300

  or use: just vad-stream
           just vad-stream-aggressive
           just vad-stream-custom min_silence=1500 min_speech=300
"""

import argparse
import os
import struct
import subprocess
import sys
import time
from datetime import datetime

try:
    import numpy as np
    import torch
except ImportError:
    print("ERROR: Dependencies not installed. Run: just setup-vad")
    sys.exit(1)

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pi-aggregator"))
try:
    from vad import SileroVAD
except ImportError:
    print("ERROR: Could not import VAD module")
    sys.exit(1)


class PCMVADMonitor:
    """Real-time VAD monitor for raw PCM stream."""

    def __init__(
        self,
        serial_port,
        baudrate=921600,
        min_silence_ms=1500,
        min_speech_ms=0,
        enable_volume_control=False,
        speech_volume=60,
        silence_volume=100,
    ):
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.min_silence_ms = min_silence_ms
        self.min_speech_ms = min_speech_ms
        self.vad = SileroVAD(
            sample_rate=16000, device="cpu", min_silence_duration_ms=min_silence_ms
        )

        # Volume control settings
        self.enable_volume_control = enable_volume_control
        self.speech_volume = speech_volume
        self.silence_volume = silence_volume

        # Stats
        self.total_chunks = 0
        self.speech_chunks = 0
        self.current_speech_start = None
        self.speech_segments = []
        self.session_start = None

        # Display
        self.last_state = False
        self.bar_width = 50

    def print_header(self):
        """Print monitor header."""
        print("=" * 70)
        print("🎤 RAW PCM VOICE ACTIVITY MONITOR")
        print("=" * 70)
        print(f"Serial Port:      {self.serial_port}")
        print(f"Baudrate:         {self.baudrate}")
        print(f"Sample Rate:      16000 Hz")
        print(f"Chunk Size:       512 samples (32ms)")
        print(f"Mode:             🔄 CONTINUOUS (Press Ctrl+C to stop)")
        print(
            f"Min Silence:      {self.min_silence_ms}ms (grace period before ending speech)"
        )
        print(
            f"Min Speech:       {self.min_speech_ms}ms (minimum duration to accept speech)"
        )
        if self.enable_volume_control:
            print(
                f"Volume Control:   ENABLED ({self.speech_volume}% when speaking, {self.silence_volume}% when silent)"
            )
        else:
            print(f"Volume Control:   DISABLED")
        print("=" * 70)
        print("\n⏳ Waiting for ESP32 raw PCM stream...\n")

    def set_volume(self, volume):
        """Set macOS system volume using osascript."""
        if not self.enable_volume_control:
            return

        try:
            applescript = f"set volume output volume {volume}"
            subprocess.run(
                ["osascript", "-e", applescript],
                check=False,
                capture_output=True,
                timeout=5,
            )
        except Exception as e:
            print(f"⚠️  Volume control error: {e}")

    def print_alert(self, message, alert_type="info"):
        """Print colored alert message."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        if alert_type == "speech_start":
            print(f"\n{'🗣️  ' * 10}")
            print(f"[{timestamp}] 🔴 VOCALS DETECTED - SPEECH STARTED!")
            if self.enable_volume_control:
                print(f"[{timestamp}] 🔊 Volume set to {self.speech_volume}%")
            print(f"{'🗣️  ' * 10}\n")
        elif alert_type == "speech_end":
            duration = (datetime.now() - self.current_speech_start).total_seconds()
            print(f"\n[{timestamp}] 🟢 Speech ended (duration: {duration:.2f}s)")
            if self.enable_volume_control:
                print(f"[{timestamp}] 🔊 Volume set to {self.silence_volume}%")
        elif alert_type == "info":
            print(f"[{timestamp}] ℹ️  {message}")
        else:
            print(f"[{timestamp}] {message}")

    def print_progress_bar(self, confidence, is_speech):
        """Print visual confidence bar."""
        filled = int(confidence * self.bar_width)
        bar = "█" * filled + "░" * (self.bar_width - filled)

        # Color coding
        if is_speech:
            status = "🔴 SPEECH"
        else:
            status = "⚪ SILENCE"

        # Print bar
        print(f"\r{status} [{bar}] {confidence:.2%} ", end="", flush=True)

    def process_pcm_stream(self):
        """Process raw PCM stream from ESP32 and monitor for speech."""
        import serial

        # Open serial connection
        ser = serial.Serial(self.serial_port, baudrate=self.baudrate, timeout=5)
        self.print_alert(f"Connected to {self.serial_port} at {self.baudrate} baud")

        try:
            self._stream_pcm(ser)
        except KeyboardInterrupt:
            print("\n\n⚠️  Monitoring stopped by user")
        finally:
            ser.close()
            self.print_summary()

    def _stream_pcm(self, ser):
        """Stream and process continuous raw PCM from ESP32."""
        # Send initial trigger
        time.sleep(0.5)
        ser.write(b"G")
        ser.flush()
        self.print_alert("Trigger sent to ESP32...")
        time.sleep(0.1)

        self.session_start = datetime.now()
        print("\n" + "=" * 70)
        print("🎧 MONITORING STARTED - Listening for vocals...")
        print("=" * 70 + "\n")

        # Buffer for collecting PCM samples
        pcm_buffer = b""
        frame_samples = 512  # Required by Silero VAD (32ms at 16kHz)
        frame_bytes = frame_samples * 2  # 16-bit = 2 bytes per sample
        frame_duration_ms = 32  # 512 samples at 16kHz = 32ms

        # Hysteresis tracking (grace period for brief silences)
        potential_speech_start = None
        silence_counter = 0
        silence_threshold = (
            self.min_silence_ms / frame_duration_ms
        )  # How many silent frames before ending

        # Process streaming data
        while True:
            try:
                # Read available data from serial
                available = ser.in_waiting
                if available > 0:
                    data = ser.read(min(available, 4096))
                    pcm_buffer += data

                # Process complete frames
                while len(pcm_buffer) >= frame_bytes:
                    # Extract one frame
                    frame_data = pcm_buffer[:frame_bytes]
                    pcm_buffer = pcm_buffer[frame_bytes:]

                    # Convert to numpy array
                    samples = np.frombuffer(frame_data, dtype=np.int16)

                    # Run VAD
                    result = self.vad.process_chunk(samples)
                    self.total_chunks += 1

                    # Get confidence
                    confidence = result.get("confidence", 0.0)
                    is_speech = result["speech"]

                    # Hysteresis logic with grace period
                    if is_speech:
                        # Reset silence counter when speech detected
                        silence_counter = 0

                        # Detect speech start
                        if not self.last_state:
                            # Speech started!
                            self.current_speech_start = datetime.now()
                            self.set_volume(self.speech_volume)
                            self.print_alert("", "speech_start")
                            self.last_state = True
                            self.speech_chunks += 1

                        # Continuing speech
                        self.speech_chunks += 1

                        # Update progress bar
                        self.print_progress_bar(confidence, is_speech)

                    else:
                        # Silence detected
                        if self.last_state:
                            # We're in speech but got a silent frame
                            # Increment silence counter (grace period)
                            silence_counter += 1

                            # Only end speech if silence exceeds threshold
                            if silence_counter >= silence_threshold:
                                self.set_volume(self.silence_volume)
                                self.print_alert("", "speech_end")
                                segment_duration = (
                                    datetime.now() - self.current_speech_start
                                ).total_seconds()
                                self.speech_segments.append(segment_duration)
                                self.current_speech_start = None
                                self.last_state = False
                                silence_counter = 0
                                print()  # New line after progress bar

                # Small sleep to prevent busy-waiting when buffer is empty
                if available == 0:
                    time.sleep(0.001)

            except Exception as e:
                print(f"\n⚠️  Error processing stream: {e}")
                # Try to reconnect
                time.sleep(1)

    def print_summary(self):
        """Print session summary."""
        if self.session_start is None:
            return

        session_duration = (datetime.now() - self.session_start).total_seconds()

        print("\n\n" + "=" * 70)
        print("📊 SESSION SUMMARY")
        print("=" * 70)
        print(f"Session duration:       {session_duration:.1f}s")
        print(f"Total chunks processed: {self.total_chunks}")
        print(f"Speech chunks:          {self.speech_chunks}")
        print(
            f"Speech percentage:      {(self.speech_chunks / self.total_chunks * 100) if self.total_chunks > 0 else 0:.1f}%"
        )
        print(f"Speech segments:        {len(self.speech_segments)}")

        if self.speech_segments:
            print(f"Total speech time:      {sum(self.speech_segments):.2f}s")
            print(
                f"Average segment:        {sum(self.speech_segments) / len(self.speech_segments):.2f}s"
            )
            print(f"Longest segment:        {max(self.speech_segments):.2f}s")

        print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Real-time PCM VAD Monitor")
    parser.add_argument(
        "port",
        nargs="?",
        default="/dev/tty.wchusbserial550D0193611",
        help="Serial port (default: /dev/tty.wchusbserial550D0193611)",
    )
    parser.add_argument(
        "--baudrate", type=int, default=921600, help="Baud rate (default: 921600)"
    )
    parser.add_argument(
        "--min-silence",
        type=int,
        default=1500,
        help="Grace period in milliseconds before ending speech (default: 1500ms). Increase this for longer grace period during brief pauses.",
    )
    parser.add_argument(
        "--min-speech",
        type=int,
        default=0,
        help="Minimum speech duration in milliseconds before accepting speech (default: 0ms)",
    )
    parser.add_argument(
        "--volume-control",
        action="store_true",
        help="Enable macOS volume control (lowers volume when speech detected, raises when silent)",
    )
    parser.add_argument(
        "--speech-volume",
        type=int,
        default=60,
        help="Volume level when speech is detected (default: 60%%)",
    )
    parser.add_argument(
        "--silence-volume",
        type=int,
        default=100,
        help="Volume level when silent (default: 100%%)",
    )

    args = parser.parse_args()

    # Create monitor with smoothing parameters
    monitor = PCMVADMonitor(
        args.port,
        args.baudrate,
        min_silence_ms=args.min_silence,
        min_speech_ms=args.min_speech,
        enable_volume_control=args.volume_control,
        speech_volume=args.speech_volume,
        silence_volume=args.silence_volume,
    )
    monitor.print_header()

    try:
        monitor.process_pcm_stream()
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
