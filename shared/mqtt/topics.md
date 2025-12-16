MQTT topics and payload conventions

Prefix: classroom/<room_id>

Topics:
- classroom/<room_id>/esp32/<node_id>/audio/features
- classroom/<room_id>/esp32/<node_id>/pir
- classroom/<room_id>/esp32/<node_id>/env
- classroom/<room_id>/pi/aggregator/noise_profile
- classroom/<room_id>/pi/decision/actuation/speaker
- classroom/<room_id>/pi/decision/actuation/display

Payload guidelines:
- Include `timestamp`, `device_id`, and `sample_window_ms` for time-windowed acoustic features.
- Avoid raw waveform transport whenever possible.
