#include <WiFi.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <Adafruit_ST7735.h>
#include <ArduinoJson.h> // Install ArduinoJson v6

// WiFi credentials
const char* ssid = "eset456wifi2";
const char* password = "14410970";

// MQTT broker
const char* mqtt_server = "192.168.0.77";
WiFiClient espClient;
PubSubClient client(espClient);

// TFT display pins
#define TFT_CS   17
#define TFT_RST  4
#define TFT_DC   21
Adafruit_ST7735 tft = Adafruit_ST7735(TFT_CS, TFT_DC, TFT_RST);

// Device/topic configuration
const char* ROOM = "room1";
const char* NODE_ID = "node1";

String topic_env = String("classroom/") + ROOM + "/esp32/" + NODE_ID + "/env";
String topic_pir = String("classroom/") + ROOM + "/esp32/" + NODE_ID + "/pir";
String topic_audio = String("classroom/") + ROOM + "/esp32/" + NODE_ID + "/audio/features";

// For received sensor data
float temp = 0.0, humidity = 0.0;
float rms_db = -100.0, peak_db = -100.0;
bool motion = false;

void displayValues() {
  tft.fillScreen(ST77XX_BLACK);
  tft.setCursor(10, 10);
  tft.setTextColor(ST77XX_WHITE);
  tft.setTextSize(2);
  tft.print("Temp: ");
  tft.print(temp, 1);
  tft.println(" C");

  tft.setCursor(10, 40);
  tft.print("Hum:  ");
  tft.print(humidity, 1);
  tft.println(" %");

  tft.setCursor(10, 70);
  tft.print("RMS:  ");
  tft.print(rms_db, 1);
  tft.println(" dB");

  tft.setCursor(10, 100);
  tft.print("Peak: ");
  tft.print(peak_db, 1);
  tft.println(" dB");

  tft.setCursor(10, 130);
  tft.print("Motion:");
  tft.setTextColor(motion ? ST77XX_RED : ST77XX_GREEN);
  tft.print(motion ? " YES" : " NO ");
}

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

// When a message is received
void callback(char* topic, byte* message, unsigned int length) {
  Serial.print("MQTT topic: ");
  Serial.println(topic);

  // Copy payload into String
  String payload;
  for (unsigned int i = 0; i < length; i++) payload += (char)message[i];
  Serial.print("payload: ");
  Serial.println(payload);

  // Parse JSON using ArduinoJson
  StaticJsonDocument<256> doc;
  DeserializationError err = deserializeJson(doc, payload);
  if (err) {
    Serial.print("Failed to parse JSON: ");
    Serial.println(err.c_str());
    return;
  }

  if (String(topic) == topic_env) {
    if (doc.containsKey("temperature_c")) temp = doc["temperature_c"].as<float>();
    if (doc.containsKey("humidity_pct")) humidity = doc["humidity_pct"].as<float>();
    displayValues();
  } else if (String(topic) == topic_pir) {
    if (doc.containsKey("motion")) motion = doc["motion"].as<bool>();
    displayValues();
  } else if (String(topic) == topic_audio) {
    if (doc.containsKey("rms_db")) rms_db = doc["rms_db"].as<float>();
    if (doc.containsKey("peak_db")) peak_db = doc["peak_db"].as<float>();
    displayValues();
  } else {
    Serial.println("Unhandled topic");
  }
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (client.connect("ESP32_Subscriber")) { // Unique client ID!
      Serial.println("connected");
      // Subscribe to project topics
      client.subscribe(topic_env.c_str());
      client.subscribe(topic_pir.c_str());
      client.subscribe(topic_audio.c_str());
      Serial.println("Subscribed to env/pir/audio topics");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      delay(2000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  setup_wifi();

  // Initialize TFT
  tft.initR(INITR_BLACKTAB);
  tft.setRotation(1);
  tft.fillScreen(ST77XX_BLACK);

  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);

  // show initial placeholder
  displayValues();
}

void loop() {
  if (!client.connected()) reconnect();
  client.loop();
  // The display updates automatically on message receive
}
