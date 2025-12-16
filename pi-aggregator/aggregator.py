#!/usr/bin/env python3
"""Simple aggregator that consumes audio feature messages and produces a rolling noise profile."""
import json
import time
from collections import deque
from datetime import datetime
from datetime import timedelta

import paho.mqtt.client as mqtt
import numpy as np

BROKER = "localhost"
ROOM = "room1"
AUDIO_TOPIC = f"classroom/{ROOM}/esp32/+/audio/features"
PROFILE_TOPIC = f"classroom/{ROOM}/pi/aggregator/noise_profile"

WINDOW_SEC = 60

class NoiseProfile:
    def __init__(self, window_s=WINDOW_SEC):
        self.window_s = window_s
        self.samples = deque()

    def add(self, timestamp, rms_db):
        ts = datetime.fromisoformat(timestamp) if timestamp else datetime.utcnow()
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


profile = NoiseProfile()


def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT", rc)
    client.subscribe(AUDIO_TOPIC)


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        rms = float(payload.get("rms_db", 0.0))
        profile.add(payload.get("timestamp"), rms)
        summary = profile.summary()
        summary_payload = json.dumps({"timestamp": datetime.utcnow().isoformat(), "profile": summary})
        client.publish(PROFILE_TOPIC, summary_payload)
        print("Published profile:", summary_payload)
    except Exception as e:
        print("Error handling message:", e)


if __name__ == "__main__":
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, 1883, 60)
    client.loop_forever()
