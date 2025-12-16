#!/usr/bin/env python3
"""
Microphone Gain Control Script

Allows real-time adjustment of ESP32 microphone gain without restarting.
Communicates with the ESP32 firmware via serial protocol.

Gain Levels:
  0 = 1x   (no amplification - use for loud sources close to mic)
  1 = 2x   (minimal amplification)
  2 = 4x   (light amplification)
  3 = 8x   (medium amplification)
  4 = 16x  (high amplification - default, use for distant sources)

Usage:
  python mic_gain_control.py /dev/tty.wchusbserial550D0193611
  python mic_gain_control.py /dev/tty.wchusbserial550D0193611 --gain 3
  python mic_gain_control.py /dev/tty.wchusbserial550D0193611 --interactive
"""

import argparse
import sys
import time

import serial


def send_command(ser, command):
    """Send a command to ESP32 and get response."""
    try:
        ser.write(command.encode() + b"\n")
        ser.flush()
        time.sleep(0.2)  # Wait for response

        # Read response
        response = ""
        while ser.in_waiting > 0:
            response += ser.read(1).decode("utf-8", errors="ignore")

        return response
    except Exception as e:
        print(f"Error: {e}")
        return None


def set_gain(ser, gain_level):
    """Set microphone gain (0-4)."""
    if not (0 <= gain_level <= 4):
        print(f"❌ Invalid gain level: {gain_level}. Must be 0-4")
        return False

    gain_names = {0: "1x", 1: "2x", 2: "4x", 3: "8x", 4: "16x"}
    command = f"G{gain_level}"

    print(f"📶 Setting gain to {gain_level} ({gain_names[gain_level]})...")
    response = send_command(ser, command)

    if response:
        print(f"✅ {response.strip()}")
    else:
        print("❌ No response from ESP32")
        return False

    return True


def get_info(ser):
    """Request and display microphone info."""
    print("📋 Requesting microphone info...")
    response = send_command(ser, "I")

    if response:
        print(response)
    else:
        print("❌ No response from ESP32")


def interactive_mode(ser):
    """Interactive mode for real-time gain adjustment."""
    print("\n🎤 Interactive Gain Control Mode")
    print("=" * 50)
    print("Enter gain level (0-4) to adjust:")
    print("  0 = 1x   (loud sources)")
    print("  1 = 2x   (minimal)")
    print("  2 = 4x   (light)")
    print("  3 = 8x   (medium)")
    print("  4 = 16x  (distant sources)")
    print("\nType 'i' for info, 'q' to quit")
    print("=" * 50 + "\n")

    while True:
        try:
            user_input = input("🎙️  Gain> ").strip().lower()

            if user_input == "q":
                print("👋 Goodbye!")
                break
            elif user_input == "i":
                get_info(ser)
            elif user_input in "01234":
                gain_level = int(user_input)
                set_gain(ser, gain_level)
            else:
                print("❓ Invalid input. Enter 0-4, 'i' for info, or 'q' to quit")

        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Control ESP32 microphone gain in real-time"
    )
    parser.add_argument(
        "port",
        nargs="?",
        default="/dev/tty.wchusbserial550D0193611",
        help="Serial port (default: /dev/tty.wchusbserial550D0193611)",
    )
    parser.add_argument("--gain", type=int, help="Set gain level (0-4) and exit")
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Enter interactive mode for real-time adjustment",
    )
    parser.add_argument(
        "--baudrate",
        type=int,
        default=921600,
        help="Serial baud rate (default: 921600)",
    )

    args = parser.parse_args()

    # Open serial connection
    try:
        ser = serial.Serial(args.port, baudrate=args.baudrate, timeout=2)
        print(f"✅ Connected to {args.port} at {args.baudrate} baud\n")
    except Exception as e:
        print(f"❌ Failed to connect to {args.port}: {e}")
        sys.exit(1)

    try:
        # Wait for ESP32 to boot
        time.sleep(0.5)

        # Show welcome message
        response = send_command(ser, "I")
        if response:
            print(response)

        # Handle different modes
        if args.interactive:
            interactive_mode(ser)
        elif args.gain is not None:
            set_gain(ser, args.gain)
        else:
            # Default: show info and enter interactive mode
            interactive_mode(ser)

    finally:
        ser.close()
        print("🔌 Serial connection closed")


if __name__ == "__main__":
    main()
