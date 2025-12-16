#!/usr/bin/env python3
"""Decision node: subscribes to noise_profile and issues actuation decisions."""
import json
import time
import sys
import os
import logging
from datetime import datetime

import paho.mqtt.client as mqtt
import numpy as np
from sklearn.ensemble import RandomForestRegressor
import joblib

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

MODEL_PATH = "model.joblib"

class DecisionAgent:
    def __init__(self):
        self.model = None
        try:
            if os.path.exists(MODEL_PATH):
                self.model = joblib.load(MODEL_PATH)
                logger.info(f"Loaded model from {MODEL_PATH}")
            else:
                logger.warning(f"Model file {MODEL_PATH} not found")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            logger.info("Running with heuristic rules")

    def decide(self, profile_summary):
        # profile_summary is dict with mean_rms_db
        mean = profile_summary.get("mean_rms_db", 0.0)
        if self.model is not None:
            try:
                X = np.array([[mean]])
                score = float(self.model.predict(X)[0])
                source = "random_forest"
            except Exception as e:
                logger.error(f"Prediction error: {e}")
                score = self._heuristic(mean)
                source = "heuristic_fallback"
        else:
            score = self._heuristic(mean)
            source = "heuristic"
            
        # Map score to volume factor (0.0-1.0)
        # Assuming score is "noisiness" 0..1, we want volume to be inverse?
        # Or if score is "target volume", we use it directly.
        # Let's assume model predicts "target volume reduction" or similar.
        # For now, let's stick to the original logic:
        # score = max(0.0, min(1.0, (mean + 60) / 60.0)) -> noisiness
        # volume = 1.0 - score
        
        level = round(float(1.0 - score), 2)
        
        cmd = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": "set_volume",
            "level": level,
            "confidence": 1.0,
            "source": source
        }
        return cmd

    def _heuristic(self, mean_rms):
        # simple heuristic: -60dB is quiet (0), 0dB is loud (1)
        return max(0.0, min(1.0, (mean_rms + 60) / 60.0))

class DecisionService:
    def __init__(self):
        self.agent = DecisionAgent()
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, rc):
        logger.info(f"Connected to MQTT broker with result code {rc}")
        client.subscribe(Config.TOPIC_NOISE_PROFILE)
        logger.info(f"Subscribed to {Config.TOPIC_NOISE_PROFILE}")

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            profile = payload.get("profile", {})
            cmd = self.agent.decide(profile)
            
            client.publish(Config.TOPIC_ACTUATION_SPEAKER, json.dumps(cmd))
            logger.info(f"Published actuation: {cmd}")
            
        except Exception as e:
            logger.error(f"Error processing profile: {e}")

    def run(self):
        logger.info(f"Connecting to {Config.MQTT_BROKER}:{Config.MQTT_PORT}")
        try:
            self.client.connect(Config.MQTT_BROKER, Config.MQTT_PORT, 60)
            self.client.loop_forever()
        except KeyboardInterrupt:
            logger.info("Stopping decision service")
        except Exception as e:
            logger.error(f"Connection error: {e}")

if __name__ == "__main__":
    service = DecisionService()
    service.run()

