#include <Arduino.h>
// #include <WiFi.h>
// #include <PubSubClient.h>
// #include <Wire.h>
// #include <Adafruit_AHT10.h>

// // WiFi credentials
// const char* ssid = "yours";
// const char* password = "yours123";

// // MQTT broker
// const char* mqtt_server = "192.168.0.191";
// WiFiClient espClient;
// PubSubClient client(espClient);

// Microphone ADC pin
const int micPin = 32;

// // Sensor
// Adafruit_AHT10 aht;

void setup() {
  Serial.begin(115200);
  Serial.println("Raw ADC Stream - Serial Mode");
  Serial.println("timestamp_ms,adc_value");
  
  analogReadResolution(12);  // 12-bit ADC for ESP32
}

void loop() {
  unsigned long ts = millis();
  int micValue = analogRead(micPin);
  
  // CSV format: timestamp_ms,adc_value
  Serial.printf("%lu,%d\n", ts, micValue);
  
  delay(10);  // ~100 Hz sampling
}

// MQTT functions (commented out for now)
/*
void setup_wifi() {
  delay(50);
  Serial.print("Connecting to ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected!");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (client.connect("ESP32_Publisher")) {
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      delay(2000);
    }
  }
}

void setup_mqtt() {
  Wire.begin(27, 33);
  if (!aht.begin()) {
    Serial.println("Failed to find AHT10 sensor! Check wiring.");
    while (1) delay(10);
  }
  Serial.println("AHT10 sensor initialized.");
  client.setServer(mqtt_server, 1883);
}

void loop_mqtt() {
  if (!client.connected()) reconnect();
  client.loop();

  sensors_event_t humidity, temp;
  aht.getEvent(&humidity, &temp);
  
  char payload[32];
  snprintf(payload, sizeof(payload), "%.2f", temp.temperature);
  client.publish("sensor/temperature", payload);
  snprintf(payload, sizeof(payload), "%.2f", humidity.relative_humidity);
  client.publish("sensor/humidity", payload);
}
*/

