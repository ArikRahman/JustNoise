#include <WiFi.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <Adafruit_AHT10.h>

// WiFi credentials
const char* ssid = "eset456wifi2";
const char* password = "14410970";

// MQTT broker
const char* mqtt_server = "192.168.0.77";
WiFiClient espClient;
PubSubClient client(espClient);

// Sensor
Adafruit_AHT10 aht;

// MQTT setup
void setup_wifi() {
  delay(50);
  Serial.begin(115200);
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
  // Loop until reconnected
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (client.connect("ESP32_Publisher")) { // Unique client ID!
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      delay(2000);
    }
  }
}

void setup() {
  setup_wifi();

  // Init sensor (I2C pins may be 27/33 on some ESP32 devkits—adjust if needed!)
  Wire.begin(27, 33);
  if (!aht.begin()) {
    Serial.println("Failed to find AHT10 sensor! Check wiring.");
    while (1) delay(10);
  }
  Serial.println("AHT10 sensor initialized.");

  client.setServer(mqtt_server, 1883);
}

void loop() {
  if (!client.connected()) reconnect();
  client.loop();

  // Read sensor
  sensors_event_t humidity, temp;
  aht.getEvent(&humidity, &temp);
  Serial.print("Temperature: ");
  Serial.print(temp.temperature, 1);
  Serial.print(" °C, Humidity: ");
  Serial.print(humidity.relative_humidity, 1);
  Serial.println(" %");

  // Publish to MQTT
  char payload[32];
  snprintf(payload, sizeof(payload), "%.2f,%.2f", temp.temperature, humidity.relative_humidity);
  client.publish("esp32/sensorData", payload);

  delay(2000); // Adjust speed if needed
}
