#!/usr/bin/env python3
"""Publish simulated ESP32 messages to MQTT for testing."""
import json
import time
import random
from datetime import datetime

import paho.mqtt.client as mqtt

BROKER = "localhost"
ROOM = "room1"
CLIENT = mqtt.Client()
CLIENT.connect(BROKER, 1883, 60)

NODE = "node1"

try:
    while True:
        rms = random.uniform(-60, -20)
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "device_id": NODE,
            "sample_window_ms": 100,
            "rms_db": rms,
            "peak_db": rms + random.uniform(0, 3)
        }
        topic = f"classroom/{ROOM}/esp32/{NODE}/audio/features"
        CLIENT.publish(topic, json.dumps(payload))
        # PIR
        pir_payload = {"timestamp": datetime.utcnow().isoformat(), "device_id": NODE, "motion": random.choice([True, False])}
        CLIENT.publish(f"classroom/{ROOM}/esp32/{NODE}/pir", json.dumps(pir_payload))
        time.sleep(2)
except KeyboardInterrupt:
    pass
