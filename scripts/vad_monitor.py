#!/usr/bin/env python3
"""
Real-time VAD Monitor - CLI debugger for live voice detection from ESP32.

Displays visual alerts when speech/vocals are detected in real-time.

Usage:
  python vad_monitor.py /dev/tty.wchusbserial550D0193611
  python vad_monitor.py /dev/tty.wchusbserial550D0193611 --continuous
  
  or use: just vad-monitor
  or use: just vad-monitor-continuous
"""

import sys
import os
import time
import argparse
from datetime import datetime
import struct

try:
    import numpy as np
    import torch
except ImportError:
    print("ERROR: Dependencies not installed. Run: just setup-vad")
    sys.exit(1)

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'pi-aggregator'))
try:
    from vad import SileroVAD
except ImportError:
    print("ERROR: Could not import VAD module")
    sys.exit(1)


class VADMonitor:
    """CLI monitor for real-time voice activity detection."""
    
    def __init__(self, serial_port, baudrate=921600, continuous=False):
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.continuous = continuous
        self.vad = SileroVAD(sample_rate=16000, device='cpu')
        
        # Stats
        self.total_chunks = 0
        self.speech_chunks = 0
        self.current_speech_start = None
        self.speech_segments = []
        self.recording_count = 0
        
        # Display
        self.last_state = False
        self.bar_width = 50
        
    def print_header(self):
        """Print monitor header."""
        print("=" * 70)
        print("🎤 REAL-TIME VOICE ACTIVITY MONITOR")
        print("=" * 70)
        print(f"Serial Port: {self.serial_port}")
        print(f"Sample Rate: 16000 Hz")
        print(f"Chunk Size:  512 samples (32ms)")
        if self.continuous:
            print(f"Mode:        🔄 CONTINUOUS (Press Ctrl+C to stop)")
        else:
            print(f"Mode:        Single recording (10 seconds)")
        print("=" * 70)
        print("\n⏳ Waiting for ESP32 audio stream...\n")
    
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
    
    def process_audio_stream(self):
        """Process ESP32 audio stream and monitor for speech."""
        import serial
        
        # Open serial connection
        ser = serial.Serial(self.serial_port, baudrate=self.baudrate, timeout=5)
        self.print_alert(f"Connected to {self.serial_port} at {self.baudrate} baud")
        
        try:
            if self.continuous:
                self._process_continuous(ser)
            else:
                self._process_single(ser)
        except KeyboardInterrupt:
            print("\n\n⚠️  Monitoring stopped by user")
        finally:
            ser.close()
            self.print_summary()
    
    def _process_single(self, ser):
        """Process a single 10-second recording."""
        # Send trigger
        time.sleep(0.5)
        ser.write(b'G')
        ser.flush()
        self.print_alert("Trigger sent to ESP32...")
        time.sleep(0.1)
        
        # Find and process WAV stream
        self._find_and_process_stream(ser)
    
    def _process_continuous(self, ser):
        """Process continuous recordings in a loop."""
        print("\n" + "=" * 70)
        print("🔄 CONTINUOUS MODE - Monitoring indefinitely")
        print("   Press Ctrl+C to stop")
        print("=" * 70 + "\n")
        
        while True:
            self.recording_count += 1
            
            # Optional: uncomment below to show recording separators between sessions
            # Useful for debugging/tracking when each new 10s recording starts
            # if self.recording_count > 1:
            #     print(f"\n{'─' * 70}")
            #     print(f"▶️  Recording #{self.recording_count}")
            #     print(f"{'─' * 70}\n")
            
            # Send trigger
            time.sleep(0.5)
            ser.write(b'G')
            ser.flush()
            time.sleep(0.1)
            
            # Find and process WAV stream
            try:
                self._find_and_process_stream(ser)
            except Exception as e:
                print(f"\n⚠️  Error in recording #{self.recording_count}: {e}")
                # Wait a bit before retrying
                time.sleep(1)
    
    def _find_and_process_stream(self, ser):
        """Find WAV header and process the audio stream."""
        # Find WAV header
        buffer = b''
        timeout_counter = 0
        
        while timeout_counter < 200:
            available = ser.in_waiting
            if available > 0:
                data = ser.read(min(available, 512))
                buffer += data
                riff_index = buffer.find(b'RIFF')
                if riff_index >= 0:
                    buffer = buffer[riff_index:]
                    break
            else:
                timeout_counter += 1
                time.sleep(0.1)
                # Show progress every 5 seconds (only in single mode)
                if not self.continuous and timeout_counter % 50 == 0:
                    print(f"  ... still waiting ({timeout_counter * 0.1:.0f}s elapsed)")
        
        if len(buffer) < 44:
            if not self.continuous:
                print("\n" + "=" * 70)
                print("❌ ERROR: Failed to find audio stream")
                print("=" * 70)
                print("\n🔧 Troubleshooting:")
                print("  1. Make sure ESP32 is connected:")
                print(f"     ls -la {self.serial_port}")
                print("\n  2. Flash the WAV recorder firmware:")
                print("     just flash")
                print("\n  3. Try running the basic recorder first:")
                print("     just record test.wav")
                print("\n  4. Check if ESP32 is responding:")
                print(f"     screen {self.serial_port} 115200")
                print("     (Press Ctrl+A then K to exit)")
                print("=" * 70)
            return
        
        # Parse header
        header = buffer[:44]
        data_size = struct.unpack('<I', header[40:44])[0]
        
        if not self.continuous or self.recording_count == 1:
            self.print_alert(f"Audio stream found! ({data_size} bytes, {data_size/32000:.1f}s)")
            if not self.continuous:
                print("\n" + "=" * 70)
                print("🎧 MONITORING STARTED - Listening for vocals...")
                print("=" * 70 + "\n")
        
        # Process audio chunks
        remaining_buffer = buffer[44:]
        bytes_read = len(remaining_buffer)
        frame_samples = 512  # Required by Silero VAD
        
        while bytes_read < data_size:
            # Read more data
            chunk_size = min(4096, data_size - bytes_read)
            chunk = ser.read(chunk_size)
            if not chunk:
                break
            
            remaining_buffer += chunk
            bytes_read += len(chunk)
            
            # Process complete frames
            while len(remaining_buffer) >= frame_samples * 2:
                sample_bytes = frame_samples * 2
                samples = np.frombuffer(remaining_buffer[:sample_bytes], dtype=np.int16)
                remaining_buffer = remaining_buffer[sample_bytes:]
                
                # Run VAD
                result = self.vad.process_chunk(samples)
                self.total_chunks += 1
                
                # Get confidence (use a simple speech probability estimate)
                confidence = result.get('confidence', 0.0)
                is_speech = result['speech']
                
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
                    segment_duration = (datetime.now() - self.current_speech_start).total_seconds()
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
    
    def print_summary(self):
        """Print session summary."""
        print("\n\n" + "=" * 70)
        print("📊 SESSION SUMMARY")
        print("=" * 70)
        if self.continuous:
            print(f"Recordings processed:   {self.recording_count}")
        print(f"Total chunks processed: {self.total_chunks}")
        print(f"Speech chunks:          {self.speech_chunks}")
        print(f"Speech percentage:      {(self.speech_chunks/self.total_chunks*100) if self.total_chunks > 0 else 0:.1f}%")
        print(f"Speech segments:        {len(self.speech_segments)}")
        
        if self.speech_segments:
            print(f"Total speech time:      {sum(self.speech_segments):.2f}s")
            print(f"Average segment:        {sum(self.speech_segments)/len(self.speech_segments):.2f}s")
            print(f"Longest segment:        {max(self.speech_segments):.2f}s")
        
        print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description='Real-time VAD Monitor')
    parser.add_argument('port', nargs='?', default='/dev/tty.wchusbserial550D0193611',
                        help='Serial port (default: /dev/tty.wchusbserial550D0193611)')
    parser.add_argument('--baudrate', type=int, default=921600,
                        help='Baud rate (default: 921600)')
    parser.add_argument('--continuous', '-c', action='store_true',
                        help='Continuous monitoring mode (loops indefinitely)')
    
    args = parser.parse_args()
    
    # Create monitor
    monitor = VADMonitor(args.port, args.baudrate, continuous=args.continuous)
    monitor.print_header()
    
    try:
        monitor.process_audio_stream()
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
