## WAV Recorder for ESP32

Records audio from a microphone and streams the WAV file over the serial port to your computer.

### Hardware Setup

- **Microphone**: MAX4466 output connected to ESP32 pin 35 (ADC1)
- **USB**: ESP32 connected to computer via USB for serial communication

### Firmware

Upload `wav_recorder.ino` to the ESP32 using Arduino IDE or PlatformIO.

### Recording

1. **On ESP32**: The firmware will automatically begin recording after you open the serial monitor (or it connects to power). It records for 10 seconds at 16 kHz by default.

2. **On Computer**: Use the `capture_wav.py` script to capture the binary stream:

```bash
# Sync dependencies first
uv sync

# Capture the WAV file
uv run scripts/capture_wav.py /dev/tty.SLAB_USBtoUART recording.wav
```

Replace `/dev/tty.SLAB_USBtoUART` with your actual serial port:
- **macOS**: `/dev/tty.SLAB_USBtoUART` or `/dev/tty.usbserial-*`
- **Linux**: `/dev/ttyUSB0` or `/dev/ttyACM0`
- **Windows**: `COM3` or similar

3. **Output**: The script will save a standard 16-bit mono WAV file at 16 kHz to `recording.wav`

### Notes

- The recording duration is configurable in the firmware (`RECORDING_TIME_SEC`)
- The WAV header is sent first, then samples are streamed continuously
- Do not disconnect the USB cable during recording
- The firmware halts after recording completes

### Troubleshooting

- If the script fails to connect, check the serial port name
- If the WAV file is incomplete, the ESP32 may have lost sync with the serial port. Try again with a shorter recording duration.
- The serial connection runs at 115200 baud, which is about 14 KB/s. A 10-second recording is ~320 KB and should take ~30 seconds to transfer.
