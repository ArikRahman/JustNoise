#!/usr/bin/env python3
"""Decision node: subscribes to noise_profile and issues actuation decisions."""
import json
import time
from datetime import datetime

import paho.mqtt.client as mqtt
import numpy as np
from sklearn.ensemble import RandomForestRegressor
import joblib

BROKER = "localhost"
ROOM = "room1"
PROFILE_TOPIC = f"classroom/{ROOM}/pi/aggregator/noise_profile"
ACTUATION_TOPIC = f"classroom/{ROOM}/pi/decision/actuation/speaker"
MODEL_PATH = "model.joblib"

class DecisionAgent:
    def __init__(self):
        self.model = None
        try:
            self.model = joblib.load(MODEL_PATH)
            print("Loaded model", MODEL_PATH)
        except Exception:
            print("No model found; running with heuristic rules")

    def decide(self, profile_summary):
        # profile_summary is dict with mean_rms_db
        mean = profile_summary.get("mean_rms_db", 0.0)
        if self.model is not None:
            X = np.array([[mean]])
            score = float(self.model.predict(X)[0])
        else:
            # simple heuristic
            score = max(0.0, min(1.0, (mean + 60) / 60.0))
        # Map score to volume factor (0.0-1.0)
        cmd = {"timestamp": datetime.utcnow().isoformat(), "action": "set_volume", "level": round(float(1.0 - score), 2), "confidence": 1.0}
        return cmd


agent = DecisionAgent()


def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT", rc)
    client.subscribe(PROFILE_TOPIC)


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        profile = payload.get("profile", {})
        cmd = agent.decide(profile)
        client.publish(ACTUATION_TOPIC, json.dumps(cmd))
        print("Published actuation:", cmd)
    except Exception as e:
        print("Error processing profile:", e)


if __name__ == "__main__":
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, 1883, 60)
    client.loop_forever()
