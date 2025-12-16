#!/usr/bin/env python3
"""Publish simulated ESP32 messages to MQTT for testing."""
import json
import time
import random
import sys
import os
from datetime import datetime

import paho.mqtt.client as mqtt

# Add shared/utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../shared'))
try:
    from utils.config import Config
except ImportError:
    # Fallback if running from root
    sys.path.append(os.path.join(os.getcwd(), 'shared'))
    from utils.config import Config

CLIENT = mqtt.Client()
CLIENT.connect(Config.MQTT_BROKER, Config.MQTT_PORT, 60)

NODE = "node1"

# Helper to construct topic from pattern
# Config.TOPIC_AUDIO_FEATURES is "classroom/{ROOM_ID}/esp32/+/audio/features"
# We need to replace + with NODE
def get_topic(pattern, node_id):
    return pattern.replace('+', node_id)

try:
    print(f"Publishing to {Config.MQTT_BROKER} for room {Config.ROOM_ID}...")
    while True:
        rms = random.uniform(-60, -20)
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "device_id": NODE,
            "sample_window_ms": 100,
            "rms_db": rms,
            "peak_db": rms + random.uniform(0, 3)
        }
        
        topic_audio = get_topic(Config.TOPIC_AUDIO_FEATURES, NODE)
        CLIENT.publish(topic_audio, json.dumps(payload))
        
        # PIR
        pir_payload = {
            "timestamp": datetime.utcnow().isoformat(), 
            "device_id": NODE, 
            "motion": random.choice([True, False])
        }
        topic_pir = get_topic(Config.TOPIC_PIR, NODE)
        CLIENT.publish(topic_pir, json.dumps(pir_payload))
        
        # Env (occasional)
        if random.random() < 0.1:
            env_payload = {
                "timestamp": datetime.utcnow().isoformat(),
                "device_id": NODE,
                "temperature_c": random.uniform(20, 25),
                "humidity_pct": random.uniform(40, 60)
            }
            topic_env = get_topic(Config.TOPIC_ENV, NODE)
            CLIENT.publish(topic_env, json.dumps(env_payload))
            print("Published env")

        print(f"Published audio/pir for {NODE}")
        time.sleep(2)
except KeyboardInterrupt:
    print("\nStopping simulator")

