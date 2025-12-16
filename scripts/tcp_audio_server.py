#!/usr/bin/env python3
"""
TCP Audio Server for ESP32 PCM Streaming

Receives raw 16-bit PCM audio from ESP32 over TCP and saves to WAV files.
Supports real-time streaming and command handling.

Usage:
  python tcp_audio_server.py                    # Listen on all interfaces
  python tcp_audio_server.py --host 10.45.232.125  # Specific IP
  python tcp_audio_server.py --port 8080       # Custom port
  python tcp_audio_server.py --output-dir ./audio  # Custom output dir
"""

import argparse
import os
import socket
import struct
import threading
import time
import wave
from datetime import datetime
from pathlib import Path


class TCPAudioServer:
    """TCP server for receiving PCM audio from ESP32."""

    SAMPLE_RATE = 16000
    CHANNELS = 1
    SAMPLE_WIDTH = 2  # 16-bit
    BUFFER_SIZE = 4096

    def __init__(self, host="0.0.0.0", port=8080, output_dir="./recordings"):
        self.host = host
        self.port = port
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.server_socket = None
        self.client_socket = None
        self.client_address = None
        self.is_running = False
        self.is_recording = False
        self.current_wav_file = None
        self.total_samples = 0
        self.session_start_time = None

        print(f"🎵 TCP Audio Server initialized")
        print(f"   Host: {host}")
        print(f"   Port: {port}")
        print(f"   Output: {output_dir}")
        print(f"   Expected: 16kHz 16-bit mono PCM")

    def start(self):
        """Start the TCP server."""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(1)

            self.is_running = True
            print(f"\n🔄 Server listening on {self.host}:{self.port}")
            print("   Waiting for ESP32 connection...")

            # Start accept thread
            accept_thread = threading.Thread(target=self._accept_connections)
            accept_thread.daemon = True
            accept_thread.start()

            # Keep main thread alive
            while self.is_running:
                time.sleep(1)

        except KeyboardInterrupt:
            print("\n⚠️  Server shutdown requested")
        except Exception as e:
            print(f"\n❌ Server error: {e}")
        finally:
            self.stop()

    def stop(self):
        """Stop the server and cleanup."""
        self.is_running = False

        if self.is_recording:
            self._stop_recording()

        if self.client_socket:
            self.client_socket.close()
            self.client_socket = None

        if self.server_socket:
            self.server_socket.close()
            self.server_socket = None

        print("🛑 Server stopped")

    def _accept_connections(self):
        """Accept incoming connections."""
        while self.is_running:
            try:
                self.client_socket, self.client_address = self.server_socket.accept()
                print(
                    f"\n✅ ESP32 connected from {self.client_address[0]}:{self.client_address[1]}"
                )

                # Start handling client
                self._handle_client()

            except OSError:
                # Socket was closed
                break
            except Exception as e:
                print(f"❌ Connection error: {e}")
                time.sleep(1)

    def _handle_client(self):
        """Handle client connection and data reception."""
        self.session_start_time = time.time()
        self.total_samples = 0

        print("🎤 Ready to receive audio data...")
        print("   Send 'S' to ESP32 to start streaming")

        try:
            while self.is_running and self.client_socket:
                # Check for data
                data = self.client_socket.recv(self.BUFFER_SIZE)

                if not data:
                    # Connection closed
                    print("📴 ESP32 disconnected")
                    break

                # Process audio data
                self._process_audio_data(data)

        except Exception as e:
            print(f"❌ Client handling error: {e}")
        finally:
            if self.is_recording:
                self._stop_recording()
            if self.client_socket:
                self.client_socket.close()
                self.client_socket = None
            print("🔌 Client connection closed")

    def _process_audio_data(self, data):
        """Process incoming audio data."""
        if len(data) % 2 != 0:
            print(
                f"⚠️  Warning: Received odd number of bytes ({len(data)}), expected even"
            )
            return

        num_samples = len(data) // 2

        # Start recording if not already
        if not self.is_recording:
            self._start_recording()

        # Write to WAV file
        if self.current_wav_file:
            # Convert bytes to samples and write
            samples = []
            for i in range(0, len(data), 2):
                sample = struct.unpack("<h", data[i : i + 2])[0]
                samples.append(sample)

            self.current_wav_file.writeframes(
                struct.pack("<" + "h" * len(samples), *samples)
            )
            self.total_samples += len(samples)

            # Progress update every 1 second worth of audio
            if self.total_samples % self.SAMPLE_RATE == 0:
                duration = self.total_samples / self.SAMPLE_RATE
                print(f"🎵 Recording... {duration:.1f}s ({self.total_samples} samples)")

    def _start_recording(self):
        """Start recording to a new WAV file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tcp_audio_{timestamp}.wav"
        filepath = self.output_dir / filename

        try:
            self.current_wav_file = wave.open(str(filepath), "wb")
            self.current_wav_file.setnchannels(self.CHANNELS)
            self.current_wav_file.setsampwidth(self.SAMPLE_WIDTH)
            self.current_wav_file.setframerate(self.SAMPLE_RATE)

            self.is_recording = True
            print(f"🔴 Started recording: {filename}")

        except Exception as e:
            print(f"❌ Failed to create WAV file: {e}")
            self.current_wav_file = None

    def _stop_recording(self):
        """Stop recording and finalize WAV file."""
        if self.current_wav_file:
            self.current_wav_file.close()
            self.current_wav_file = None

            duration = self.total_samples / self.SAMPLE_RATE
            size_mb = (self.total_samples * self.SAMPLE_WIDTH) / (1024 * 1024)

            print(f"✅ Recording saved ({duration:.1f}s, {size_mb:.2f} MB)")
            print(f"   Total samples: {self.total_samples:,}")

        self.is_recording = False
        self.total_samples = 0

    def get_status(self):
        """Get server status."""
        status = {
            "running": self.is_running,
            "client_connected": self.client_socket is not None,
            "client_address": self.client_address[0] if self.client_address else None,
            "recording": self.is_recording,
            "total_samples": self.total_samples,
            "session_duration": time.time() - self.session_start_time
            if self.session_start_time
            else 0,
        }
        return status


def main():
    parser = argparse.ArgumentParser(
        description="TCP Audio Server for ESP32 PCM Streaming"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Server host IP (default: 0.0.0.0 for all interfaces)",
    )
    parser.add_argument(
        "--port", type=int, default=8080, help="Server port (default: 8080)"
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default="./recordings",
        help="Output directory for WAV files (default: ./recordings)",
    )

    args = parser.parse_args()

    server = TCPAudioServer(host=args.host, port=args.port, output_dir=args.output_dir)

    try:
        server.start()
    except KeyboardInterrupt:
        print("\n⚠️  Shutdown requested by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
    finally:
        server.stop()


if __name__ == "__main__":
    main()
