#!/usr/bin/env python3
"""Simple aggregator that consumes audio feature messages and produces a rolling noise profile."""
import json
import time
import sys
import os
import logging
from collections import deque
from datetime import datetime, timedelta

import paho.mqtt.client as mqtt
import numpy as np

# Add shared/utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../shared'))
try:
    from utils.config import Config
except ImportError:
    # Fallback if running from root
    sys.path.append(os.path.join(os.getcwd(), 'shared'))
    from utils.config import Config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NoiseProfile:
    def __init__(self, window_s=Config.AGGREGATION_WINDOW_SEC):
        self.window_s = window_s
        self.samples = deque()

    def add(self, timestamp, rms_db):
        # Handle timestamp parsing (ISO format)
        try:
            ts = datetime.fromisoformat(timestamp) if timestamp else datetime.utcnow()
        except ValueError:
            ts = datetime.utcnow()
            
        self.samples.append((ts, rms_db))
        self._expire()

    def _expire(self):
        cutoff = datetime.utcnow() - timedelta(seconds=self.window_s)
        while self.samples and self.samples[0][0] < cutoff:
            self.samples.popleft()

    def summary(self):
        if not self.samples:
            return {"count": 0}
        vals = [v for _, v in self.samples]
        return {
            "count": len(vals),
            "mean_rms_db": float(np.mean(vals)),
            "max_rms_db": float(np.max(vals)),
            "min_rms_db": float(np.min(vals)),
        }

class AggregatorService:
    def __init__(self):
        self.profile = NoiseProfile()
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, rc):
        logger.info(f"Connected to MQTT broker with result code {rc}")
        client.subscribe(Config.TOPIC_AUDIO_FEATURES)
        logger.info(f"Subscribed to {Config.TOPIC_AUDIO_FEATURES}")

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            rms = float(payload.get("rms_db", 0.0))
            timestamp = payload.get("timestamp")
            
            self.profile.add(timestamp, rms)
            summary = self.profile.summary()
            
            summary_payload = json.dumps({
                "timestamp": datetime.utcnow().isoformat(),
                "profile": summary
            })
            
            client.publish(Config.TOPIC_NOISE_PROFILE, summary_payload)
            logger.debug(f"Published profile: {summary_payload}")
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")

    def run(self):
        logger.info(f"Connecting to {Config.MQTT_BROKER}:{Config.MQTT_PORT}")
        try:
            self.client.connect(Config.MQTT_BROKER, Config.MQTT_PORT, 60)
            self.client.loop_forever()
        except KeyboardInterrupt:
            logger.info("Stopping aggregator service")
        except Exception as e:
            logger.error(f"Connection error: {e}")

if __name__ == "__main__":
    service = AggregatorService()
    service.run()

