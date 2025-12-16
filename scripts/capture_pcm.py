#!/usr/bin/env python3
"""
Capture raw PCM stream from ESP32 and save to audio files.

This script continuously reads raw 16-bit PCM from serial and saves chunks to WAV files.
Supports multiple splitting modes: time, size, vad, manual.

Usage:
  python capture_pcm.py /dev/tty.wchusbserial550D0193611
  python capture_pcm.py /dev/tty.wchusbserial550D0193611 --duration 30
  python capture_pcm.py /dev/tty.wchusbserial550D0193611 --mode vad
"""

import argparse
import os
import sys
import time
import wave
from datetime import datetime
from pathlib import Path

try:
    import numpy as np
    import serial
except ImportError:
    print("ERROR: Missing dependencies. Run: pip install pyserial numpy")
    sys.exit(1)


class PCMCapture:
    """Capture raw PCM stream and save to audio files."""

    SAMPLE_RATE = 16000
    CHANNELS = 1
    SAMPLE_WIDTH = 2  # 16-bit = 2 bytes
    BAUDRATE = 921600

    def __init__(
        self,
        serial_port,
        output_dir="./recordings",
        mode="time",
        duration=60,
        max_size=1024 * 1024,
        debug=False,
    ):
        """Initialize PCM capture."""
        self.serial_port = serial_port
        self.output_dir = Path(output_dir)
        self.mode = mode
        self.duration = duration
        self.max_size = max_size
        self.debug = debug

        # VAD setup (if needed)
        self.vad = None
        if mode == "vad":
            try:
                sys.path.insert(
                    0, os.path.join(os.path.dirname(__file__), "..", "pi-aggregator")
                )
                from vad import SileroVAD

                self.vad = SileroVAD(sample_rate=self.SAMPLE_RATE, device="cpu")
            except ImportError:
                print("ERROR: VAD mode requires Silero VAD. Run: just setup-vad")
                sys.exit(1)

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Stats
        self.file_count = 0
        self.total_samples = 0
        self.start_time = None
        self.current_file = None
        self.current_file_samples = 0
        self.bytes_received = 0

    def debug_print(self, msg):
        """Print debug message if debug mode enabled."""
        if self.debug:
            print(f"[DEBUG] {msg}")

    def get_output_filename(self, prefix="recording"):
        """Generate timestamped output filename."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{timestamp}.wav"
        return self.output_dir / filename

    def create_wav_file(self):
        """Create and return a new WAV file object."""
        filepath = self.get_output_filename()

        # Create WAV file
        wav_file = wave.open(str(filepath), "wb")
        wav_file.setnchannels(self.CHANNELS)
        wav_file.setsampwidth(self.SAMPLE_WIDTH)
        wav_file.setframerate(self.SAMPLE_RATE)

        self.current_file = (wav_file, filepath)
        self.current_file_samples = 0
        self.file_count += 1

        return wav_file

    def close_current_file(self):
        """Close current WAV file and print info."""
        if self.current_file is None:
            return

        wav_file, filepath = self.current_file
        wav_file.close()

        duration = self.current_file_samples / self.SAMPLE_RATE
        size = filepath.stat().st_size

        print(f"✅ Saved: {filepath.name}")
        print(f"   Duration: {duration:.1f}s ({self.current_file_samples} samples)")
        print(f"   File size: {size / 1024:.1f} KB")

        self.current_file = None
        self.current_file_samples = 0

    def connect_serial(self):
        """Connect to serial port."""
        try:
            ser = serial.Serial(self.serial_port, baudrate=self.BAUDRATE, timeout=2)
            print(f"✓ Connected to {self.serial_port} at {self.BAUDRATE} baud")
            return ser
        except serial.SerialException as e:
            print(f"❌ ERROR: Failed to connect to {self.serial_port}")
            print(f"   {e}")
            print("\nTroubleshooting:")
            print(f"  1. Check device is connected: ls -la {self.serial_port}")
            print(f"  2. Flash firmware: just flash")
            print(f"  3. Test connection: just check")
            return None

    def send_trigger(self, ser):
        """Send trigger to ESP32."""
        time.sleep(0.5)
        self.debug_print("Sending trigger 'G' to ESP32...")
        ser.write(b"G")
        ser.flush()
        print("✓ Trigger sent to ESP32, waiting for audio stream...")
        time.sleep(0.2)

    def wait_for_data(self, ser, timeout=10):
        """Wait for data to arrive on serial port."""
        print(f"\n⏳ Waiting for audio data (timeout: {timeout}s)...")
        start = time.time()

        # Try to read existing data first
        time.sleep(0.2)
        available = ser.in_waiting
        if available > 0:
            self.debug_print(f"Data already available: {available} bytes")
            print(f"✓ Receiving audio data ({available} bytes waiting)...")
            return True

        while time.time() - start < timeout:
            available = ser.in_waiting
            if available > 0:
                self.debug_print(f"Data available: {available} bytes")
                print(f"✓ Receiving audio data ({available} bytes waiting)...")
                return True

            elapsed = time.time() - start
            if int(elapsed) % 2 == 0 and elapsed == int(elapsed):
                print(f"  Still waiting... {elapsed:.0f}s elapsed")

            time.sleep(0.1)

        print(f"\n❌ ERROR: No data received from ESP32 after {timeout} seconds")
        print("\nTroubleshooting:")
        print(f"  1. Verify ESP32 is connected: just check")
        print(f"  2. Check firmware is flashed: just flash")
        print(f"  3. Try different serial port in justfile")
        print(f"  4. Test with serial monitor: just monitor")
        return False

    def capture_time_based(self, ser):
        """Capture with time-based file splitting."""
        print(f"\n{'=' * 70}")
        print(f"📊 TIME-BASED CAPTURE MODE")
        print(f"{'=' * 70}")
        print(f"Duration per file: {self.duration}s")
        print(f"Output directory: {self.output_dir}")
        print(f"{'=' * 70}\n")

        pcm_buffer = b""
        frame_samples = 512
        frame_bytes = frame_samples * 2

        file_start_time = None
        last_data_time = time.time()
        data_timeout = 5  # seconds without data before warning

        try:
            while True:
                # Read from serial
                available = ser.in_waiting
                if available > 0:
                    data = ser.read(min(available, 4096))
                    pcm_buffer += data
                    self.bytes_received += len(data)
                    last_data_time = time.time()

                    self.debug_print(
                        f"Received {len(data)} bytes, buffer: {len(pcm_buffer)} bytes"
                    )

                # Check for data timeout
                if time.time() - last_data_time > data_timeout:
                    print(
                        f"\n⚠️  WARNING: No data for {data_timeout}s. Stream may have stopped."
                    )
                    if self.bytes_received == 0:
                        print("   No data received at all. Check firmware/connection.")
                        break
                    last_data_time = time.time()  # Reset timer

                # Open file if needed
                if self.current_file is None:
                    wav = self.create_wav_file()
                    file_start_time = time.time()
                    print(f"\n🔴 Recording started... ({self.duration}s)")

                # Process complete frames
                while len(pcm_buffer) >= frame_bytes:
                    frame_data = pcm_buffer[:frame_bytes]
                    pcm_buffer = pcm_buffer[frame_bytes:]

                    # Convert to samples
                    samples = np.frombuffer(frame_data, dtype=np.int16)
                    wav_file, _ = self.current_file
                    wav_file.writeframes(samples.tobytes())

                    self.current_file_samples += frame_samples
                    self.total_samples += frame_samples

                    # Check if duration exceeded
                    elapsed = time.time() - file_start_time
                    if elapsed >= self.duration:
                        self.close_current_file()
                        break

                    # Print progress every second
                    if self.current_file_samples % self.SAMPLE_RATE == 0:  # Every 1s
                        remaining = self.duration - elapsed
                        print(
                            f"\r  Recording... {elapsed:.1f}s / {self.duration}s (remaining: {remaining:.1f}s)",
                            end="",
                            flush=True,
                        )

                # Small sleep to prevent busy-waiting
                if available == 0:
                    time.sleep(0.001)

        except KeyboardInterrupt:
            print("\n\n⚠️  Capture stopped by user")
            if self.current_file is not None:
                self.close_current_file()

    def print_summary(self):
        """Print capture summary."""
        if self.total_samples == 0:
            print(f"\n⚠️  No samples captured!")
            print(f"   Total bytes received from serial: {self.bytes_received}")
            if self.bytes_received == 0:
                print("\n🔧 Troubleshooting:")
                print(f"   1. Verify serial connection: just check")
                print(f"   2. Flash new firmware: just flash")
                print(f"   3. Test with monitor: just monitor")
                print(f"   4. Check baudrate is 921600")
            return

        total_duration = self.total_samples / self.SAMPLE_RATE

        print(f"\n\n{'=' * 70}")
        print(f"📊 CAPTURE SUMMARY")
        print(f"{'=' * 70}")
        print(f"Files created:      {self.file_count}")
        print(f"Total samples:      {self.total_samples:,}")
        print(f"Total duration:     {total_duration:.1f}s")
        print(f"Output directory:   {self.output_dir}")
        print(f"Bytes from serial:  {self.bytes_received:,}")
        print(f"{'=' * 70}")

    def run(self):
        """Main capture loop."""
        print(f"\n{'=' * 70}")
        print(f"🎙️  PCM STREAM CAPTURE - {self.mode.upper()} MODE")
        print(f"{'=' * 70}")

        # Connect to serial
        ser = self.connect_serial()
        if not ser:
            return False

        try:
            # Send trigger
            self.send_trigger(ser)

            # Wait for data to arrive (don't clear buffer, data is already coming)
            if not self.wait_for_data(ser, timeout=10):
                return False

            # Start capture
            self.start_time = time.time()

            if self.mode == "time":
                self.capture_time_based(ser)
            else:
                print(f"ERROR: Mode '{self.mode}' not yet implemented")
                return False

        finally:
            ser.close()
            self.print_summary()

        return True


def main():
    parser = argparse.ArgumentParser(
        description="Capture raw PCM stream from ESP32 and save to audio files"
    )

    parser.add_argument(
        "port",
        nargs="?",
        default="/dev/tty.wchusbserial550D0193611",
        help="Serial port (default: /dev/tty.wchusbserial550D0193611)",
    )

    parser.add_argument(
        "--output-dir",
        "-o",
        default="./recordings",
        help="Output directory for WAV files (default: ./recordings)",
    )

    parser.add_argument(
        "--mode",
        "-m",
        choices=["time", "size", "vad", "manual"],
        default="time",
        help="Capture mode (default: time)",
    )

    parser.add_argument(
        "--duration",
        "-d",
        type=int,
        default=60,
        help="Duration per file in seconds for time mode (default: 60)",
    )

    parser.add_argument(
        "--max-size",
        "-s",
        type=int,
        default=1024 * 1024,
        help="Max file size in bytes for size mode (default: 1MB)",
    )

    parser.add_argument(
        "--baudrate",
        "-b",
        type=int,
        default=921600,
        help="Serial baud rate (default: 921600)",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output",
    )

    args = parser.parse_args()

    # Create capture instance
    capture = PCMCapture(
        args.port,
        output_dir=args.output_dir,
        mode=args.mode,
        duration=args.duration,
        max_size=args.max_size,
        debug=args.debug,
    )

    try:
        success = capture.run()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
