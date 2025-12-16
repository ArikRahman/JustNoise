/*
  I2S MEMS Microphone Raw PCM Streamer
  Streams raw PCM audio from Fermion I2S MEMS microphone over serial.
  No WAV header - just continuous 16-bit PCM samples for efficient VAD processing.
  
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

int16_t sampleBuffer[SAMPLE_BUFFER_SIZE];

// Function declarations
void i2s_install();
void i2s_setpin();

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
  
  delay(2000);  // Wait 2s for serial connection to stabilize
}

void loop() {
  // Wait for serial connection to send any byte to trigger streaming
  while (Serial.available() == 0) {
    delay(10);
  }
  // Clear the trigger byte
  while (Serial.available() > 0) {
    Serial.read();
  }
  
  // CRITICAL: Clear I2S DMA buffers to avoid stale data
  i2s_zero_dma_buffer(I2S_PORT);
  
  // Discard first batch of samples (warm-up period)
  int32_t dummyBuffer[SAMPLE_BUFFER_SIZE];
  size_t dummyBytesRead;
  for (int i = 0; i < 3; i++) {  // Discard 3 buffers worth
    i2s_read(I2S_PORT, dummyBuffer, sizeof(dummyBuffer), &dummyBytesRead, portMAX_DELAY);
  }
  
  // Stream raw PCM indefinitely (no header, no size limit)
  // This allows for true continuous streaming without WAV overhead
  size_t bytesRead = 0;
  int32_t i2sBuffer[SAMPLE_BUFFER_SIZE];
  
  while (Serial) {  // Continue until serial connection is lost
    // Read from I2S DMA buffer (stereo 32-bit samples)
    i2s_read(I2S_PORT, i2sBuffer, sizeof(i2sBuffer), &bytesRead, portMAX_DELAY);
    
    size_t samplesRead = bytesRead / 8;  // 8 bytes per stereo sample (2 x 32-bit)
    
    // Convert stereo to mono and send raw PCM
    for (size_t i = 0; i < samplesRead; i++) {
      // Extract right channel (SEL=HIGH) from second 32-bit word
      // Using >> 12 for 16x gain boost
      int16_t sample16 = (int16_t)(i2sBuffer[i * 2 + 1] >> 12);
      Serial.write((uint8_t*)&sample16, 2);
    }
    Serial.flush();
  }
}