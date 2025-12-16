/*
  I2S MEMS Microphone Raw PCM Streamer with WiFi TCP Streaming
  Streams raw PCM audio from Fermion I2S MEMS microphone over WiFi TCP.
  No WAV header - just continuous 16-bit PCM samples for efficient VAD processing.

  Features:
  - Configurable microphone gain via TCP commands
  - Real-time gain adjustment without restart
  - Gain range: 0-16x (shift 0-4 bits)
  - WiFi connectivity with automatic reconnection
  - TCP streaming to server at 10.45.232.125:8080
  - Serial protocol: Send "G<gain>" to set gain (e.g., "G2" for 2x, "G4" for 4x)

  Pin Configuration:
  - SCK:  GPIO 25 (Bit Clock)
  - WS:   GPIO 16 (Word Select / LRCLK)
  - SD:   GPIO 26 (Serial Data)
*/

#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClient.h>
#include <driver/i2s.h>

// I2S microphone pin configuration
#define I2S_SCK_PIN   25  // Serial Clock (BCK)
#define I2S_WS_PIN    16  // Word Select (LRCLK)
#define I2S_SD_PIN    26  // Serial Data (DIN/DO)
#define I2S_SEL_PIN   2   // Channel Select (GND=Left, VCC=Right)

// WiFi configuration
#define WIFI_SSID     "yours"
#define WIFI_PASSWORD "yours123"

// TCP server configuration
#define SERVER_IP     "10.45.232.125"
#define SERVER_PORT   8080

// Recording parameters
#define SAMPLE_RATE       16000
#define BITS_PER_SAMPLE   I2S_BITS_PER_SAMPLE_16BIT
#define I2S_PORT          I2S_NUM_0
#define BIT_DEPTH         16
#define NUM_CHANNELS      1

// Buffer configuration
#define DMA_BUF_COUNT     8
#define DMA_BUF_LEN       1024
#define SAMPLE_BUFFER_SIZE 512

// Gain configuration (in bits to shift)
// Shift 0 = 1x, Shift 1 = 2x, Shift 2 = 4x, Shift 3 = 8x, Shift 4 = 16x
volatile uint8_t gainShift = 2;  // Default: 4x gain (calibrated for good quality)
volatile bool streamingActive = false;

int16_t sampleBuffer[SAMPLE_BUFFER_SIZE];

// WiFi and TCP client
WiFiClient tcpClient;
bool wifiConnected = false;
bool tcpConnected = false;

// Function declarations
void i2s_install();
void i2s_setpin();
void handleSerialCommand();
void printGainInfo();
void connectToWiFi();
void connectToServer();
void checkConnections();

void i2s_install() {
  const i2s_config_t i2s_config = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
    .sample_rate = SAMPLE_RATE,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT,
    .channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT,  // Stereo (Right+Left)
    .communication_format = I2S_COMM_FORMAT_STAND_I2S,
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = DMA_BUF_COUNT,
    .dma_buf_len = DMA_BUF_LEN,
    .use_apll = false,
    .tx_desc_auto_clear = false,
    .fixed_mclk = 0
  };

  i2s_driver_install(I2S_PORT, &i2s_config, 0, NULL);
}

void i2s_setpin() {
  const i2s_pin_config_t pin_config = {
    .bck_io_num = I2S_SCK_PIN,
    .ws_io_num = I2S_WS_PIN,
    .data_out_num = I2S_PIN_NO_CHANGE,
    .data_in_num = I2S_SD_PIN
  };

  i2s_set_pin(I2S_PORT, &pin_config);
}

void printGainInfo() {
  Serial.println("\n========================================");
  Serial.println("I2S MEMS Microphone WiFi TCP Streamer");
  Serial.println("========================================");
  Serial.print("WiFi: ");
  Serial.print(wifiConnected ? "CONNECTED (" : "DISCONNECTED (");
  Serial.print(WIFI_SSID);
  Serial.println(")");
  Serial.print("TCP Server: ");
  Serial.print(tcpConnected ? "CONNECTED (" : "DISCONNECTED (");
  Serial.print(SERVER_IP);
  Serial.print(":");
  Serial.print(SERVER_PORT);
  Serial.println(")");
  Serial.print("Current Gain Shift: ");
  Serial.print(gainShift);
  Serial.print(" bits (");
  Serial.print(1 << gainShift);
  Serial.println("x amplification)");
  Serial.println("\nGain Control Commands:");
  Serial.println("  G0 = 1x   (no amplification)");
  Serial.println("  G1 = 2x   (minimal)");
  Serial.println("  G2 = 4x   (light - recommended)");
  Serial.println("  G3 = 8x   (medium)");
  Serial.println("  G4 = 16x  (high - may cause distortion)");
  Serial.println("\nOther Commands:");
  Serial.println("  I = Print this info");
  Serial.println("  S = Start streaming PCM over TCP");
  Serial.println("  T = Stop streaming");
  Serial.println("========================================\n");
}

void connectToWiFi() {
  if (wifiConnected) return;

  Serial.print("Connecting to WiFi: ");
  Serial.println(WIFI_SSID);

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    wifiConnected = true;
    Serial.println("\nWiFi connected!");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
  } else {
    wifiConnected = false;
    Serial.println("\nWiFi connection failed!");
  }
}

void connectToServer() {
  if (!wifiConnected || tcpConnected) return;

  Serial.print("Connecting to TCP server: ");
  Serial.print(SERVER_IP);
  Serial.print(":");
  Serial.println(SERVER_PORT);

  if (tcpClient.connect(SERVER_IP, SERVER_PORT)) {
    tcpConnected = true;
    Serial.println("TCP connected!");
  } else {
    tcpConnected = false;
    Serial.println("TCP connection failed!");
  }
}

void checkConnections() {
  // Check WiFi connection
  if (WiFi.status() != WL_CONNECTED) {
    wifiConnected = false;
    tcpConnected = false;
    if (tcpClient.connected()) {
      tcpClient.stop();
    }
    Serial.println("WiFi disconnected! Reconnecting...");
    connectToWiFi();
  }

  // Check TCP connection
  if (wifiConnected && !tcpClient.connected()) {
    tcpConnected = false;
    Serial.println("TCP disconnected! Reconnecting...");
    connectToServer();
  }
}

void handleSerialCommand() {
  if (Serial.available() > 0) {
    int cmd = Serial.read();

    // Handle gain commands (G0-G4)
    if (cmd == 'G' && Serial.available() > 0) {
      int gainLevel = Serial.read() - '0';  // Convert ASCII '0'-'4' to 0-4

      if (gainLevel >= 0 && gainLevel <= 4) {
        gainShift = gainLevel;
        Serial.print("Gain set to ");
        Serial.print(1 << gainShift);
        Serial.println("x");
      } else {
        Serial.println("Invalid gain level. Use G0-G4");
      }
      return;
    }

    // Handle info command
    if (cmd == 'I') {
      printGainInfo();
      return;
    }

    // Handle start streaming command
    if (cmd == 'S') {
      if (tcpConnected) {
        streamingActive = true;
        Serial.println("Starting PCM streaming over TCP...");
      } else {
        Serial.println("Cannot start streaming - TCP not connected!");
      }
      return;
    }

    // Handle stop streaming command
    if (cmd == 'T') {
      streamingActive = false;
      Serial.println("Stopping PCM streaming...");
      return;
    }

    // Unknown command
    Serial.print("Unknown command: ");
    Serial.println((char)cmd);
    Serial.println("Available commands: G0-G4, I, S, T");
  }
}

void setup() {
  // Initialize Serial for commands and debugging
  Serial.begin(921600);
  while (!Serial) {
    delay(10);
  }

  Serial.println("\nESP32 I2S MEMS Microphone WiFi TCP Streamer");
  Serial.println("==========================================");

  // Set SEL pin HIGH for right channel
  pinMode(I2S_SEL_PIN, OUTPUT);
  digitalWrite(I2S_SEL_PIN, HIGH);  // Right channel (VCC)

  // Initialize I2S
  i2s_install();
  i2s_setpin();
  i2s_zero_dma_buffer(I2S_PORT);

  // Connect to WiFi
  connectToWiFi();

  // Connect to TCP server
  if (wifiConnected) {
    connectToServer();
  }

  delay(500);  // Wait for connections to stabilize

  // Print welcome message
  printGainInfo();
}

void loop() {
  // Check connections periodically
  static unsigned long lastCheck = 0;
  if (millis() - lastCheck > 5000) {  // Check every 5 seconds
    checkConnections();
    lastCheck = millis();
  }

  // Check for serial commands (gain adjustment, info, etc.)
  handleSerialCommand();

  // Wait for streaming trigger if not active
  if (!streamingActive) {
    delay(100);
    return;
  }

  // Check if we can stream (need TCP connection)
  if (!tcpConnected) {
    Serial.println("Cannot stream - TCP not connected!");
    streamingActive = false;
    return;
  }

  // CRITICAL: Clear I2S DMA buffers to avoid stale data
  i2s_zero_dma_buffer(I2S_PORT);

  // Discard first batch of samples (warm-up period)
  int32_t dummyBuffer[SAMPLE_BUFFER_SIZE];
  size_t dummyBytesRead;
  for (int i = 0; i < 3; i++) {  // Discard 3 buffers worth
    i2s_read(I2S_PORT, dummyBuffer, sizeof(dummyBuffer), &dummyBytesRead, portMAX_DELAY);
  }

  Serial.println("Starting PCM streaming over TCP...");

  // Stream raw PCM indefinitely with configurable gain
  size_t bytesRead = 0;
  int32_t i2sBuffer[SAMPLE_BUFFER_SIZE];
  unsigned long lastHeartbeat = millis();

  while (streamingActive && tcpConnected) {
    // Check for serial commands during streaming (allow gain adjustment on-the-fly)
    if (Serial.available() > 0) {
      int cmd = Serial.read();

      // Handle gain commands during streaming
      if (cmd == 'G' && Serial.available() > 0) {
        int gainLevel = Serial.read() - '0';
        if (gainLevel >= 0 && gainLevel <= 4) {
          gainShift = gainLevel;
          Serial.print("Gain adjusted to ");
          Serial.print(1 << gainShift);
          Serial.println("x");
        }
        continue;  // Skip this iteration, continue streaming
      }

      // Handle stop command
      if (cmd == 'T') {
        streamingActive = false;
        Serial.println("Streaming stopped by command");
        break;
      }
    }

    // Check TCP connection
    if (!tcpClient.connected()) {
      tcpConnected = false;
      streamingActive = false;
      Serial.println("TCP connection lost! Stopping stream.");
      break;
    }

    // Send heartbeat every 10 seconds
    if (millis() - lastHeartbeat > 10000) {
      Serial.print("Streaming... (");
      Serial.print(millis() / 1000);
      Serial.println("s elapsed)");
      lastHeartbeat = millis();
    }

    // Read from I2S DMA buffer (stereo 32-bit samples)
    i2s_read(I2S_PORT, i2sBuffer, sizeof(i2sBuffer), &bytesRead, portMAX_DELAY);

    size_t samplesRead = bytesRead / 8;  // 8 bytes per stereo sample (2 x 32-bit)

    // Convert stereo to mono and send raw PCM with configurable gain
    for (size_t i = 0; i < samplesRead; i++) {
      // Extract right channel (SEL=HIGH) from second 32-bit word
      // Apply configurable gain shift
      int16_t sample16 = (int16_t)(i2sBuffer[i * 2 + 1] >> (12 - gainShift));

      // Send over TCP
      tcpClient.write((uint8_t*)&sample16, 2);
    }

    // Small delay to prevent overwhelming the network
    delay(1);
  }

  Serial.println("PCM streaming stopped.");
}