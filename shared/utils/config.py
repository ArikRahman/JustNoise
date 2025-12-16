import os
from dotenv import load_dotenv

# Load .env from project root (assuming script is run from project root or subfolder)
# We'll try to find .env by walking up directories
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
load_dotenv(os.path.join(project_root, '.env'))

class Config:
    MQTT_BROKER = os.getenv('MQTT_BROKER', 'localhost')
    MQTT_PORT = int(os.getenv('MQTT_PORT', 1883))
    ROOM_ID = os.getenv('ROOM_ID', 'room1')
    
    # Topics
    TOPIC_PREFIX = f"classroom/{ROOM_ID}"
    TOPIC_AUDIO_FEATURES = f"{TOPIC_PREFIX}/esp32/+/audio/features"
    TOPIC_PIR = f"{TOPIC_PREFIX}/esp32/+/pir"
    TOPIC_ENV = f"{TOPIC_PREFIX}/esp32/+/env"
    TOPIC_NOISE_PROFILE = f"{TOPIC_PREFIX}/pi/aggregator/noise_profile"
    TOPIC_ACTUATION_SPEAKER = f"{TOPIC_PREFIX}/pi/decision/actuation/speaker"
    TOPIC_ACTUATION_DISPLAY = f"{TOPIC_PREFIX}/pi/decision/actuation/display"

    # Aggregator settings
    AGGREGATION_WINDOW_SEC = int(os.getenv('AGGREGATION_WINDOW_SEC', 60))
