/*
  I2S MEMS Microphone Raw PCM Streamer with Configurable Gain
  Streams raw PCM audio from Fermion I2S MEMS microphone over serial.
  No WAV header - just continuous 16-bit PCM samples for efficient VAD processing.
  
  Features:
  - Configurable microphone gain via serial commands
  - Real-time gain adjustment without restart
  - Gain range: 0-16x (shift 0-4 bits)
  - Serial protocol: Send "G<gain>" to set gain (e.g., "G2" for 2x, "G4" for 4x)
  
  Pin Configuration:
  - SCK:  GPIO 25 (Bit Clock)
  - WS:   GPIO 16 (Word Select / LRCLK)
  - SD:   GPIO 26 (Serial Data)
*/

#include <Arduino.h>
#include <driver/i2s.h>

// I2S microphone pin configuration
#define I2S_SCK_PIN   25  // Serial Clock (BCK)
#define I2S_WS_PIN    16  // Word Select (LRCLK)
#define I2S_SD_PIN    26  // Serial Data (DIN/DO)
#define I2S_SEL_PIN   2   // Channel Select (GND=Left, VCC=Right)

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
volatile uint8_t gainShift = 4;  // Default: 16x gain (>> 12 equivalent)
volatile bool streamingActive = false;

int16_t sampleBuffer[SAMPLE_BUFFER_SIZE];

// Function declarations
void i2s_install();
void i2s_setpin();
void handleSerialCommand();
void printGainInfo();

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
  Serial.println("I2S MEMS Microphone Raw PCM Streamer");
  Serial.println("========================================");
  Serial.print("Current Gain Shift: ");
  Serial.print(gainShift);
  Serial.print(" bits (");
  Serial.print(1 << gainShift);
  Serial.println("x amplification)");
  Serial.println("\nGain Control Commands:");
  Serial.println("  G0 = 1x   (no amplification)");
  Serial.println("  G1 = 2x   (minimal)");
  Serial.println("  G2 = 4x   (light)");
  Serial.println("  G3 = 8x   (medium)");
  Serial.println("  G4 = 16x  (high - default)");
  Serial.println("\nOther Commands:");
  Serial.println("  I = Print this info");
  Serial.println("  Any other byte = Start streaming PCM");
  Serial.println("========================================\n");
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
    
    // Any other byte starts streaming
    streamingActive = true;
  }
}

void setup() {
  // Initialize Serial for data streaming
  // 921600 baud required for 16kHz 16-bit audio (32kB/s)
  Serial.begin(921600);
  while (!Serial) {
    delay(10);
  }
  
  // Set SEL pin HIGH for right channel
  pinMode(I2S_SEL_PIN, OUTPUT);
  digitalWrite(I2S_SEL_PIN, HIGH);  // Right channel (VCC)
  
  // Initialize I2S
  i2s_install();
  i2s_setpin();
  i2s_zero_dma_buffer(I2S_PORT);
  
  delay(500);  // Wait for serial connection to stabilize
  
  // Print welcome message
  printGainInfo();
}

void loop() {
  // Check for serial commands (gain adjustment, info, etc.)
  handleSerialCommand();
  
  // Wait for streaming trigger if not active
  if (!streamingActive) {
    delay(100);
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
  
  // Stream raw PCM indefinitely with configurable gain
  size_t bytesRead = 0;
  int32_t i2sBuffer[SAMPLE_BUFFER_SIZE];
  
  while (Serial && streamingActive) {
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
      
      // Any other command stops streaming
      streamingActive = false;
      Serial.println("Streaming stopped");
      break;
    }
    
    // Read from I2S DMA buffer (stereo 32-bit samples)
    i2s_read(I2S_PORT, i2sBuffer, sizeof(i2sBuffer), &bytesRead, portMAX_DELAY);
    
    size_t samplesRead = bytesRead / 8;  // 8 bytes per stereo sample (2 x 32-bit)
    
    // Convert stereo to mono and send raw PCM with configurable gain
    for (size_t i = 0; i < samplesRead; i++) {
      // Extract right channel (SEL=HIGH) from second 32-bit word
      // Apply configurable gain shift
      int16_t sample16 = (int16_t)(i2sBuffer[i * 2 + 1] >> (12 - gainShift));
      Serial.write((uint8_t*)&sample16, 2);
    }
    Serial.flush();
  }
}