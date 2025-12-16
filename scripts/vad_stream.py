#!/usr/bin/env python3
"""
Real-time VAD Monitor - Continuous raw PCM streaming from ESP32.

Reads raw 16-bit PCM samples directly from ESP32 serial stream (no WAV headers)
and feeds them into Silero VAD for real-time speech detection.

Usage:
  python vad_stream.py /dev/tty.wchusbserial550D0193611
  python vad_stream.py /dev/tty.wchusbserial550D0193611 --baudrate 921600

  or use: just vad-stream
"""

import argparse
import os
import struct
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

    def __init__(self, serial_port, baudrate=921600):
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.vad = SileroVAD(sample_rate=16000, device="cpu")

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
        print(f"Serial Port: {self.serial_port}")
        print(f"Baudrate:    {self.baudrate}")
        print(f"Sample Rate: 16000 Hz")
        print(f"Chunk Size:  512 samples (32ms)")
        print(f"Mode:        🔄 CONTINUOUS (Press Ctrl+C to stop)")
        print("=" * 70)
        print("\n⏳ Waiting for ESP32 raw PCM stream...\n")

    def print_alert(self, message, alert_type="info"):
        """Print colored alert message."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        if alert_type == "speech_start":
            print(f"\n{'🗣️  ' * 10}")
            print(f"[{timestamp}] 🔴 VOCALS DETECTED - SPEECH STARTED!")
            print(f"{'🗣️  ' * 10}\n")
        elif alert_type == "speech_end":
            duration = (datetime.now() - self.current_speech_start).total_seconds()
            print(f"\n[{timestamp}] 🟢 Speech ended (duration: {duration:.2f}s)")
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

                    # Detect state changes
                    if is_speech and not self.last_state:
                        # Speech started!
                        self.current_speech_start = datetime.now()
                        self.print_alert("", "speech_start")
                        self.last_state = True
                        self.speech_chunks += 1

                    elif not is_speech and self.last_state:
                        # Speech ended
                        self.print_alert("", "speech_end")
                        segment_duration = (
                            datetime.now() - self.current_speech_start
                        ).total_seconds()
                        self.speech_segments.append(segment_duration)
                        self.current_speech_start = None
                        self.last_state = False
                        print()  # New line after progress bar

                    elif is_speech:
                        # Continuing speech
                        self.speech_chunks += 1

                    # Update progress bar (only when speech detected)
                    if is_speech:
                        self.print_progress_bar(confidence, is_speech)

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

    args = parser.parse_args()

    # Create monitor
    monitor = PCMVADMonitor(args.port, args.baudrate)
    monitor.print_header()

    try:
        monitor.process_pcm_stream()
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
