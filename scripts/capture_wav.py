#!/usr/bin/env python3
"""
Capture WAV stream from ESP32 over serial and save to file.

Usage:
  python capture_wav.py /dev/tty.SLAB_USBtoUART output.wav
  
The ESP32 sends a binary WAV stream over serial (header first, then samples).
This script reads the binary data and writes it to a file.
"""

import sys
import serial
import struct

def capture_wav(port, output_file, timeout=30):
    """Capture WAV stream from ESP32 and save to file."""
    try:
        import time
        
        # Open serial connection
        ser = serial.Serial(port, baudrate=115200, timeout=5)
        print(f"Connected to {port} at 115200 baud")
        
        # Send trigger byte to ESP32 to start recording
        time.sleep(0.5)  # Wait for ESP32 to be ready
        ser.write(b'G')  # Send 'G' for "Go"
        ser.flush()
        print("Sent trigger to ESP32...")
        time.sleep(0.1)
        
        # Look for binary RIFF header (0x52 0x49 0x46 0x46)
        print("Searching for WAV header...")
        buffer = b''
        found_header = False
        timeout_counter = 0
        max_timeout = 200  # Wait up to 20 seconds
        
        while not found_header and timeout_counter < max_timeout:
            # Read any available data
            available = ser.in_waiting
            if available > 0:
                data = ser.read(min(available, 512))
                buffer += data
                
                # Look for RIFF signature in the buffer
                riff_index = buffer.find(b'RIFF')
                if riff_index >= 0:
                    print(f"✓ Found RIFF header (skipped {riff_index} bytes)")
                    buffer = buffer[riff_index:]  # Keep from RIFF onwards
                    found_header = True
                    break
                
                # Debug: show what we're getting
                if len(buffer) > 0 and len(buffer) % 200 == 0:
                    print(f"  ... received {len(buffer)} bytes, searching...")
            else:
                timeout_counter += 1
                time.sleep(0.1)
                if timeout_counter % 30 == 0:
                    print(f"  ... waiting ({timeout_counter * 0.1:.1f}s elapsed)")
        if not found_header:
            print(f"ERROR: Timeout waiting for RIFF header")
            print(f"Read {len(buffer)} bytes total")
            if buffer:
                print(f"First 50 bytes: {buffer[:50]}")
                print(f"As hex: {buffer[:50].hex()}")
            return False
        
        # Now read the rest of the header (44 bytes total)
        # We already have 'RIFF' (4 bytes), need 40 more
        header = buffer[:44]  # Take first 44 bytes from buffer
        
        # If we don't have enough, keep reading
        while len(header) < 44:
            chunk = ser.read(44 - len(header))
            if chunk:
                header += chunk
            else:
                time.sleep(0.05)
        
        print(f"✓ WAV header received ({len(header)} bytes)")
        
        # Validate header starts with RIFF
        if header[:4] != b'RIFF':
            print(f"ERROR: Header doesn't start with RIFF: {header[:10].hex()}")
            return False
        
        # Parse header to get data size
        try:
            data_size = struct.unpack('<I', header[40:44])[0]
        except Exception as e:
            print(f"ERROR: Failed to parse header: {e}")
            print(f"Header hex: {header.hex()}")
            return False
            
        print(f"Expected data size: {data_size} bytes")
        print(f"Expected duration: {data_size / 32000:.1f} seconds at 16kHz 16-bit mono")
        
        # Read audio data
        print("Reading audio samples...")
        audio_data = b''
        bytes_read = 0
        
        while bytes_read < data_size:
            chunk_size = min(4096, data_size - bytes_read)
            chunk = ser.read(chunk_size)
            if not chunk:
                print(f"WARNING: Unexpected end of data. Read {bytes_read} of {data_size} bytes")
                break
            audio_data += chunk
            bytes_read += len(chunk)
            
            # Print progress
            percent = (bytes_read / data_size) * 100
            print(f"  Progress: {percent:.1f}% ({bytes_read}/{data_size} bytes)", end='\r')
        
        print()  # Newline after progress
        
        # Write to file
        print(f"Writing to {output_file}...")
        with open(output_file, 'wb') as f:
            f.write(header)
            f.write(audio_data)
        
        file_size = 44 + len(audio_data)
        print(f"✓ WAV file saved: {output_file}")
        print(f"  File size: {file_size} bytes")
        print(f"  Duration: {len(audio_data) / 32000:.1f} seconds")
        
        ser.close()
        return True
        
    except serial.SerialException as e:
        print(f"ERROR: Serial error - {e}")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python capture_wav.py <serial_port> <output_file>")
        print("Example: python capture_wav.py /dev/tty.SLAB_USBtoUART recording.wav")
        sys.exit(1)
    
    port = sys.argv[1]
    output = sys.argv[2]
    
    success = capture_wav(port, output)
    sys.exit(0 if success else 1)
