#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <Adafruit_AHTX0.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7735.h>
#include <ArduinoJson.h>

// Replace with your network credentials
const char* ssid = "YOUR_SSID";
const char* password = "YOUR_PASSWORD";
const char* mqtt_server = "YOUR_MQTT_BROKER";

WiFiClient espClient;
PubSubClient client(espClient);
Adafruit_AHTX0 aht;

// Pin Definitions based on Diagram
#define I2C_SDA 27
#define I2C_SCL 33

#define TFT_CS   22
#define TFT_RST  19
#define TFT_DC   21
#define TFT_MOSI 23
#define TFT_SCLK 18
#define TFT_BLK  5

#define BUTTON_PIN 34
#define LED_PIN    2

// Sensors (Mapped to available pins)
// Note: Diagram shows IO34 as Button. We use IO35 for Mic (ADC1) and IO32 for PIR.
const int MIC_PIN = 35; 
const int PIR_PIN = 32;

Adafruit_ST7735 tft = Adafruit_ST7735(TFT_CS, TFT_DC, TFT_RST);

// Global state for display
float last_temp = 0;
float last_hum = 0;
float last_rms = 0;
bool last_motion = false;

void update_display() {
  tft.fillScreen(ST77XX_BLACK);
  tft.setCursor(0, 0);
  tft.setTextColor(ST77XX_WHITE);
  tft.setTextSize(1);
  tft.println("JustNoise Node");
  
  tft.setCursor(0, 20);
  tft.print("Temp: "); tft.print(last_temp, 1); tft.println(" C");
  tft.print("Hum:  "); tft.print(last_hum, 1); tft.println(" %");
  
  tft.setCursor(0, 50);
  tft.print("RMS:  "); tft.print(last_rms, 1); tft.println(" dB");
  
  tft.setCursor(0, 70);
  tft.print("Motion: "); 
  if (last_motion) {
    tft.setTextColor(ST77XX_RED);
    tft.println("YES");
  } else {
    tft.setTextColor(ST77XX_GREEN);
    tft.println("NO");
  }
}

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);

  tft.setCursor(0, 100);
  tft.setTextColor(ST77XX_YELLOW);
  tft.print("Connecting WiFi...");

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connected");
  tft.setCursor(0, 110);
  tft.setTextColor(ST77XX_GREEN);
  tft.println("Connected!");
  delay(1000);
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (client.connect("esp32_node1")) {
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

float read_mic_rms_ms(int ms_window) {
  unsigned long start = millis();
  long sum_sq = 0;
  long n = 0;
  while (millis() - start < ms_window) {
    int v = analogRead(MIC_PIN) - 2048; // ADC range offset for 12-bit
    sum_sq += (long)v * v;
    n++;
    delay(1);
  }
  float mean_sq = (float)sum_sq / (float)max(1L, n);
  float rms = sqrt(mean_sq);
  return rms;
}

void publish_audio_features() {
  float rms = read_mic_rms_ms(100);
  float rms_db = 20.0 * log10(rms + 1e-6);
  last_rms = rms_db;

  char payload[256];
  String topic = "classroom/room1/esp32/node1/audio/features";
  unsigned long ts = millis();
  snprintf(payload, sizeof(payload), "{\"timestamp\": \"%lu\", \"device_id\": \"node1\", \"sample_window_ms\": %d, \"rms_db\": %.2f, \"peak_db\": %.2f}",
           ts, 100, rms_db, rms_db);
  client.publish(topic.c_str(), payload);
}

void publish_env() {
  sensors_event_t humidity, temp;
  aht.getEvent(&humidity, &temp);
  last_temp = temp.temperature;
  last_hum = humidity.relative_humidity;

  char payload[256];
  String topic = "classroom/room1/esp32/node1/env";
  unsigned long ts = millis();
  snprintf(payload, sizeof(payload), "{\"timestamp\": \"%lu\", \"device_id\": \"node1\", \"temperature_c\": %.2f, \"humidity_pct\": %.2f}", ts, temp.temperature, humidity.relative_humidity);
  client.publish(topic.c_str(), payload);
}

void publish_pir() {
  bool motion = digitalRead(PIR_PIN) == HIGH;
  last_motion = motion;
  
  char payload[128];
  String topic = "classroom/room1/esp32/node1/pir";
  unsigned long ts = millis();
  snprintf(payload, sizeof(payload), "{\"timestamp\": \"%lu\", \"device_id\": \"node1\", \"motion\": %s}", ts, motion ? "true" : "false");
  client.publish(topic.c_str(), payload);
}

void setup() {
  Serial.begin(115200);
  
  // Init Pins
  pinMode(PIR_PIN, INPUT);
  pinMode(BUTTON_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);
  pinMode(TFT_BLK, OUTPUT);
  digitalWrite(TFT_BLK, HIGH); // Turn on backlight

  analogReadResolution(12);
  
  // Init I2C with specific pins
  Wire.begin(I2C_SDA, I2C_SCL);
  
  // Init TFT
  tft.initR(INITR_BLACKTAB);
  tft.setRotation(1);
  tft.fillScreen(ST77XX_BLACK);
  
  if (!aht.begin()) {
    Serial.println("Failed to find AHT sensor");
    tft.setCursor(0, 0);
    tft.setTextColor(ST77XX_RED);
    tft.println("AHT Error!");
    // Don't hang, just continue
  }

  setup_wifi();
  client.setServer(mqtt_server, 1883);
}
  if (!aht.begin()) {
    Serial.println("Failed to find AHT sensor");
    while (1) delay(10);
  }

  setup_wifi();
  client.setServer(mqtt_server, 1883);
}

unsigned long last_audio = 0;
unsigned long last_env = 0;
unsigned long last_pir = 0;

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  unsigned long now = millis();
  if (now - last_audio > 5000) {
    publish_audio_features();
    last_audio = now;
    update_display();
  }
  if (now - last_env > 60000) {
    publish_env();
    last_env = now;
    update_display();
  }
  if (now - last_pir > 2000) {
    publish_pir();
    last_pir = now;
    update_display();
  }
}
