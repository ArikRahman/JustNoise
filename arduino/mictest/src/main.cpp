/*
  Simple WAV Header Test
  Just sends a WAV header and dummy audio data over serial.
*/

#include <Arduino.h>

#define MIC_PIN 35                // ADC pin for MAX4466 microphone
#define RECORDING_TIME_SEC 10
#define SAMPLE_RATE 16000
#define BIT_DEPTH 16
#define NUM_CHANNELS 1

// Function declarations

void sendWAVHeader(uint32_t dataSize) {
  // Build WAV header manually byte by byte to ensure correctness
  uint8_t header[44];
  uint32_t idx = 0;
  
  // RIFF chunk descriptor
  header[idx++] = 'R';
  header[idx++] = 'I';
  header[idx++] = 'F';
  header[idx++] = 'F';
  
  uint32_t chunkSize = 36 + dataSize;
  header[idx++] = (chunkSize >>  0) & 0xFF;
  header[idx++] = (chunkSize >>  8) & 0xFF;
  header[idx++] = (chunkSize >> 16) & 0xFF;
  header[idx++] = (chunkSize >> 24) & 0xFF;
  
  header[idx++] = 'W';
  header[idx++] = 'A';
  header[idx++] = 'V';
  header[idx++] = 'E';
  
  // fmt subchunk
  header[idx++] = 'f';
  header[idx++] = 'm';
  header[idx++] = 't';
  header[idx++] = ' ';
  
  uint32_t subchunk1Size = 16;
  header[idx++] = (subchunk1Size >>  0) & 0xFF;
  header[idx++] = (subchunk1Size >>  8) & 0xFF;
  header[idx++] = (subchunk1Size >> 16) & 0xFF;
  header[idx++] = (subchunk1Size >> 24) & 0xFF;
  
  uint16_t audioFormat = 1; // PCM
  header[idx++] = (audioFormat >>  0) & 0xFF;
  header[idx++] = (audioFormat >>  8) & 0xFF;
  
  uint16_t numChannels = NUM_CHANNELS;
  header[idx++] = (numChannels >>  0) & 0xFF;
  header[idx++] = (numChannels >>  8) & 0xFF;
  
  uint32_t sampleRate = SAMPLE_RATE;
  header[idx++] = (sampleRate >>  0) & 0xFF;
  header[idx++] = (sampleRate >>  8) & 0xFF;
  header[idx++] = (sampleRate >> 16) & 0xFF;
  header[idx++] = (sampleRate >> 24) & 0xFF;
  
  uint32_t byteRate = SAMPLE_RATE * NUM_CHANNELS * (BIT_DEPTH / 8);
  header[idx++] = (byteRate >>  0) & 0xFF;
  header[idx++] = (byteRate >>  8) & 0xFF;
  header[idx++] = (byteRate >> 16) & 0xFF;
  header[idx++] = (byteRate >> 24) & 0xFF;
  
  uint16_t blockAlign = NUM_CHANNELS * (BIT_DEPTH / 8);
  header[idx++] = (blockAlign >>  0) & 0xFF;
  header[idx++] = (blockAlign >>  8) & 0xFF;
  
  uint16_t bitsPerSample = BIT_DEPTH;
  header[idx++] = (bitsPerSample >>  0) & 0xFF;
  header[idx++] = (bitsPerSample >>  8) & 0xFF;
  
  // data subchunk
  header[idx++] = 'd';
  header[idx++] = 'a';
  header[idx++] = 't';
  header[idx++] = 'a';
  
  header[idx++] = (dataSize >>  0) & 0xFF;
  header[idx++] = (dataSize >>  8) & 0xFF;
  header[idx++] = (dataSize >> 16) & 0xFF;
  header[idx++] = (dataSize >> 24) & 0xFF;
  
  // Send the header
  Serial.write(header, 44);
  Serial.flush();
}

void setup() {
  Serial.begin(115200);
  delay(500);
  
  // Initialize ADC for microphone
  analogReadResolution(12);  // 12-bit ADC (0-4095)
  pinMode(MIC_PIN, INPUT);
}

void loop() {
  // Calculate data size
  uint32_t totalSamples = RECORDING_TIME_SEC * SAMPLE_RATE;
  uint32_t dataSize = totalSamples * 2;
  
  // Send WAV header
  sendWAVHeader(dataSize);
  
  // Record and send real audio samples from microphone
  unsigned long startTime = millis();
  unsigned long sampleDelay = 1000000 / SAMPLE_RATE;  // microseconds between samples
  
  for (uint32_t i = 0; i < totalSamples; i++) {
    unsigned long sampleStart = micros();
    
    // Read ADC value from microphone (12-bit: 0-4095)
    uint16_t adcValue = analogRead(MIC_PIN);
    
    // Convert 12-bit ADC to 16-bit sample (scale up)
    uint16_t sample16 = adcValue << 4;  // Shift left by 4 bits (12-bit -> 16-bit)
    
    // Send sample as little-endian 16-bit
    Serial.write((uint8_t*)&sample16, 2);
    
    // Flush periodically to avoid buffer overflow
    if (i % 1600 == 0) {  // Every 0.1 seconds at 16kHz
      Serial.flush();
    }
    
    // Maintain precise sample rate timing
    while ((micros() - sampleStart) < sampleDelay) {
      // Busy wait to maintain timing
    }
  }
  
  Serial.flush();
  
  // Wait before next recording
  delay(2000);
}

