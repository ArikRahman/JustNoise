/*
  Simple WAV Header Test
  Just sends a WAV header and dummy audio data over serial.
*/

#include <Arduino.h>

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
}

void loop() {
  // Calculate data size
  uint32_t totalSamples = RECORDING_TIME_SEC * SAMPLE_RATE;
  uint32_t dataSize = totalSamples * 2;
  
  // Send WAV header
  sendWAVHeader(dataSize);
  
  // Send dummy samples
  static unsigned long startTime = millis();
  unsigned long elapsedTime = millis() - startTime;
  
  if (elapsedTime < (RECORDING_TIME_SEC * 1000)) {
    for (int i = 0; i < 100; i++) {
      uint16_t sample = 1024 + (rand() % 512);
      Serial.write((uint8_t*)&sample, 2);
    }
    Serial.flush();
    delay(1);
  } else {
    // Done - halt
    while (1) delay(1000);
  }
}

