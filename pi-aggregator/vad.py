#!/usr/bin/env python3
"""
Real-time Voice Activity Detection using Silero VAD.

Processes audio from serial stream (ESP32) or WAV files and publishes
speech detection events to MQTT.

Usage:
  # Live from ESP32
  python vad.py --serial /dev/tty.wchusbserial550D0193611
  
  # From WAV file (for testing)
  python vad.py --file recording.wav
"""

import sys
import os
import json
import time
import argparse
import struct
from datetime import datetime
from collections import deque
import logging

import numpy as np
import paho.mqtt.client as mqtt

# Import PyTorch and Silero VAD
try:
    import torch
    import torchaudio
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    print("ERROR: torch/torchaudio not installed. Install with: uv pip install -e '.[vad]'")
    sys.exit(1)

# Add shared/utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../shared'))
try:
    from utils.config import Config
except ImportError:
    sys.path.append(os.path.join(os.getcwd(), 'shared'))
    from utils.config import Config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SileroVAD:
    """Wrapper for Silero VAD model with streaming support."""
    
    def __init__(self, sample_rate=16000, device='cpu'):
        """
        Initialize Silero VAD.
        
        Args:
            sample_rate: Audio sample rate (default 16000 Hz)
            device: 'cpu' or 'cuda'
        """
        self.sample_rate = sample_rate
        self.device = device
        
        logger.info("Loading Silero VAD model...")
        self.model, utils = torch.hub.load(
            repo_or_dir='snakers4/silero-vad',
            model='silero_vad',
            force_reload=False,
            onnx=False
        )
        
        self.model.to(device)
        
        # Extract utility functions
        (self.get_speech_timestamps,
         self.save_audio,
         self.read_audio,
         self.VADIterator,
         self.collect_chunks) = utils
        
        # Initialize VAD iterator for streaming
        self.vad_iterator = self.VADIterator(
            self.model,
            threshold=0.5,
            sampling_rate=sample_rate,
            min_silence_duration_ms=300,
            speech_pad_ms=30
        )
        
        logger.info("✓ Silero VAD loaded")
    
    def process_chunk(self, audio_chunk):
        """
        Process a single audio chunk and return speech probability.
        
        Args:
            audio_chunk: numpy array of int16 samples or float32 normalized [-1, 1]
                        Must be 512 samples for 16kHz (or 256 for 8kHz)
            
        Returns:
            dict with 'speech' (bool), 'confidence' (float), 'timestamp' (ms or None)
        """
        # Silero VAD requires exactly 512 samples for 16kHz
        required_samples = 512 if self.sample_rate == 16000 else 256
        
        if len(audio_chunk) != required_samples:
            # Pad or truncate to required size
            if len(audio_chunk) < required_samples:
                # Pad with zeros
                padding = np.zeros(required_samples - len(audio_chunk), dtype=audio_chunk.dtype)
                audio_chunk = np.concatenate([audio_chunk, padding])
            else:
                # Truncate
                audio_chunk = audio_chunk[:required_samples]
        
        # Convert to float32 tensor normalized to [-1, 1]
        if audio_chunk.dtype == np.int16:
            audio_float = audio_chunk.astype(np.float32) / 32768.0
        else:
            audio_float = audio_chunk.astype(np.float32)
        
        # Convert to torch tensor
        audio_tensor = torch.from_numpy(audio_float)
        
        # Process with VAD iterator
        speech_dict = self.vad_iterator(audio_tensor, return_seconds=False)
        
        if speech_dict:
            # Speech detected
            return {
                'speech': True,
                'confidence': float(speech_dict.get('confidence', 0.0)),
                'start_ms': speech_dict.get('start'),
                'end_ms': speech_dict.get('end')
            }
        else:
            # No speech or continuing
            return {'speech': False, 'confidence': 0.0}
    
    def reset(self):
        """Reset VAD iterator state."""
        self.vad_iterator.reset_states()


class VADService:
    """Service that runs VAD on audio stream and publishes to MQTT."""
    
    def __init__(self, mqtt_broker=Config.MQTT_BROKER, mqtt_port=Config.MQTT_PORT, device_id='aggregator1'):
        self.device_id = device_id
        self.vad = SileroVAD(sample_rate=16000, device='cpu')
        
        # MQTT setup
        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.connect(mqtt_broker, mqtt_port, 60)
        self.client.loop_start()
        
        # Stats
        self.total_chunks = 0
        self.speech_chunks = 0
        
        logger.info(f"VAD service initialized (device_id={device_id})")
    
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("✓ Connected to MQTT broker")
        else:
            logger.error(f"Failed to connect to MQTT broker: {rc}")
    
    def publish_vad_event(self, event_type, confidence=None, start_ms=None, end_ms=None):
        """Publish VAD event to MQTT."""
        timestamp = datetime.utcnow().isoformat() + 'Z'
        
        if event_type in ['speech_start', 'speech_end']:
            # Discrete event
            payload = {
                'timestamp': timestamp,
                'device_id': self.device_id,
                'event': event_type,
                'source': 'silero_vad_v0'
            }
            topic = Config.TOPIC_VAD_EVENT
        else:
            # Segment summary
            payload = {
                'timestamp': timestamp,
                'device_id': self.device_id,
                'speech': event_type == 'speech',
                'start_ms': start_ms,
                'end_ms': end_ms,
                'confidence': confidence,
                'sample_rate': 16000,
                'source': 'silero_vad_v0'
            }
            topic = Config.TOPIC_VAD
        
        self.client.publish(topic, json.dumps(payload))
        logger.debug(f"Published VAD event: {event_type}")
    
    def process_audio_stream(self, audio_generator, frame_ms=32):
        """
        Process streaming audio and publish VAD events.
        
        Args:
            audio_generator: Generator yielding numpy arrays of int16 samples
            frame_ms: Frame size in milliseconds (default 32ms = 512 samples at 16kHz)
        """
        # Silero VAD requires 512 samples for 16kHz (32ms) or 256 for 8kHz
        frame_samples = 512 if self.vad.sample_rate == 16000 else 256
        buffer = np.array([], dtype=np.int16)
        
        last_speech_state = False
        current_segment_start = None
        
        logger.info(f"Processing audio stream (frame_ms={frame_ms}, frame_samples={frame_samples})...")
        
        for chunk in audio_generator:
            # Add to buffer
            buffer = np.concatenate([buffer, chunk])
            
            # Process complete frames
            while len(buffer) >= frame_samples:
                frame = buffer[:frame_samples]
                buffer = buffer[frame_samples:]
                
                # Run VAD
                result = self.vad.process_chunk(frame)
                self.total_chunks += 1
                
                # Detect state changes
                if result['speech'] and not last_speech_state:
                    # Speech started
                    self.publish_vad_event('speech_start', confidence=result['confidence'])
                    current_segment_start = self.total_chunks * frame_ms
                    last_speech_state = True
                    self.speech_chunks += 1
                    logger.info(f"🎤 Speech detected (confidence={result['confidence']:.2f})")
                    
                elif not result['speech'] and last_speech_state:
                    # Speech ended
                    current_segment_end = self.total_chunks * frame_ms
                    self.publish_vad_event(
                        'speech_end',
                        confidence=result.get('confidence', 0.0)
                    )
                    # Publish segment summary
                    self.publish_vad_event(
                        'speech',
                        confidence=result.get('confidence', 0.8),
                        start_ms=current_segment_start,
                        end_ms=current_segment_end
                    )
                    last_speech_state = False
                    logger.info(f"🔇 Speech ended (duration={(current_segment_end - current_segment_start)/1000:.1f}s)")
                    
                elif result['speech']:
                    # Continuing speech
                    self.speech_chunks += 1
                
                # Log progress periodically
                if self.total_chunks % 100 == 0:
                    speech_pct = (self.speech_chunks / self.total_chunks) * 100
                    logger.info(f"Processed {self.total_chunks} chunks ({speech_pct:.1f}% speech)")
        
        logger.info(f"✓ Stream processing complete ({self.total_chunks} chunks, {self.speech_chunks} speech)")
    
    def stop(self):
        """Stop the service."""
        self.client.loop_stop()
        self.client.disconnect()


def serial_audio_generator(port, baudrate=921600):
    """
    Generator that yields audio chunks from ESP32 serial stream.
    
    Reads WAV stream from ESP32 and yields raw PCM samples.
    """
    import serial
    
    ser = serial.Serial(port, baudrate=baudrate, timeout=5)
    logger.info(f"Connected to {port} at {baudrate} baud")
    
    # Send trigger
    time.sleep(0.5)
    ser.write(b'G')
    ser.flush()
    logger.info("Sent trigger to ESP32...")
    time.sleep(0.1)
    
    # Find and read WAV header
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
    
    if len(buffer) < 44:
        logger.error("Failed to read WAV header")
        return
    
    header = buffer[:44]
    data_size = struct.unpack('<I', header[40:44])[0]
    logger.info(f"WAV stream detected: {data_size} bytes expected")
    
    # Yield audio in chunks
    bytes_read = len(buffer) - 44
    remaining_buffer = buffer[44:]
    
    while bytes_read < data_size:
        # Read more data
        chunk_size = min(4096, data_size - bytes_read)
        chunk = ser.read(chunk_size)
        if not chunk:
            break
        
        # Add to buffer
        remaining_buffer += chunk
        bytes_read += len(chunk)
        
        # Yield complete samples (2 bytes per sample)
        # Yield in 512-sample chunks (required by Silero VAD for 16kHz)
        samples_to_yield = 512
        
        while len(remaining_buffer) >= samples_to_yield * 2:
            sample_bytes = samples_to_yield * 2
            
            # Convert bytes to int16 array
            samples = np.frombuffer(remaining_buffer[:sample_bytes], dtype=np.int16)
            remaining_buffer = remaining_buffer[sample_bytes:]
            
            yield samples
    
    ser.close()
    logger.info("Serial stream complete")


def wav_file_generator(filepath, chunk_samples=512):
    """
    Generator that yields audio chunks from a WAV file.
    
    Args:
        filepath: Path to WAV file
        chunk_samples: Number of samples per chunk (default 512 = 32ms at 16kHz, required by Silero)
    """
    import wave
    
    with wave.open(filepath, 'rb') as wav:
        sample_rate = wav.getframerate()
        n_channels = wav.getnchannels()
        
        logger.info(f"Reading WAV file: {filepath}")
        logger.info(f"  Sample rate: {sample_rate} Hz, Channels: {n_channels}")
        
        while True:
            frames = wav.readframes(chunk_samples)
            if not frames:
                break
            
            # Convert to int16 array
            samples = np.frombuffer(frames, dtype=np.int16)
            
            # If stereo, take only one channel
            if n_channels == 2:
                samples = samples[::2]
            
            yield samples
    
    logger.info("WAV file processing complete")


def main():
    parser = argparse.ArgumentParser(description='Real-time Voice Activity Detection')
    parser.add_argument('--serial', help='Serial port for ESP32 (e.g., /dev/tty.wchusbserial550D0193611)')
    parser.add_argument('--file', help='WAV file to process (for testing)')
    parser.add_argument('--device-id', default='aggregator1', help='Device ID for MQTT')
    parser.add_argument('--broker', default=Config.MQTT_BROKER, help='MQTT broker address')
    parser.add_argument('--port', type=int, default=Config.MQTT_PORT, help='MQTT port')
    
    args = parser.parse_args()
    
    if not args.serial and not args.file:
        parser.error("Must specify either --serial or --file")
    
    # Initialize VAD service
    service = VADService(mqtt_broker=args.broker, mqtt_port=args.port, device_id=args.device_id)
    
    try:
        if args.serial:
            # Process serial stream
            logger.info(f"Starting live VAD from serial port: {args.serial}")
            audio_gen = serial_audio_generator(args.serial)
            service.process_audio_stream(audio_gen)
        else:
            # Process WAV file
            logger.info(f"Processing WAV file: {args.file}")
            audio_gen = wav_file_generator(args.file)
            service.process_audio_stream(audio_gen)
    
    except KeyboardInterrupt:
        logger.info("\nStopping VAD service...")
    finally:
        service.stop()
        logger.info("VAD service stopped")


if __name__ == '__main__':
    main()
