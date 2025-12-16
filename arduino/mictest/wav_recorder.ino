/*
  WAV File Recorder for ESP32
  
  Records raw ADC samples from a microphone and streams the WAV file
  over Serial (USB) to a connected computer.
  
  Uses timer interrupt for precise sampling at 16 kHz.
  
  Hardware:
  - MAX4466 mic output on pin 35 (ADC1)
  
  On the computer side:
  - Use a Python script or similar to capture the binary WAV stream from the serial port
  - Example: python capture_wav.py /dev/tty.SLAB_USBtoUART recording.wav
  
  Output format:
  - Binary WAV file streamed over serial at 115200 baud
  - Duration: configurable (default 10 seconds)
  - Sample rate: 16 kHz
  - Bit depth: 16-bit mono
*/

#include <Arduino.h>
#include <driver/i2s.h>

// Pin definitions
#define MIC_PIN 35            // ADC1 channel 7
#define RECORDING_TIME_SEC 10 // Record duration in seconds
#define SAMPLE_RATE 16000     // 16 kHz

// WAV file constants
#define BIT_DEPTH 16
#define NUM_CHANNELS 1

// Global variables
uint32_t samplesRecorded = 0;
bool isRecording = false;
volatile uint16_t adcSample = 0;
volatile bool newSampleReady = false;

// Timer for sampling
hw_timer_t* samplingTimer = NULL;

// ISR for timer - reads ADC sample
void IRAM_ATTR onSamplingTimer() {
  adcSample = analogRead(MIC_PIN);
  newSampleReady = true;
}

// WAV file header structure
struct WAVHeader {
  char chunkID[4] = {'R', 'I', 'F', 'F'};
  uint32_t chunkSize = 0;
  char format[4] = {'W', 'A', 'V', 'E'};
  
  char subchunk1ID[4] = {'f', 'm', 't', ' '};
  uint32_t subchunk1Size = 16;
  uint16_t audioFormat = 1; // PCM
  uint16_t numChannels = NUM_CHANNELS;
  uint32_t sampleRate = SAMPLE_RATE;
  uint32_t byteRate = SAMPLE_RATE * NUM_CHANNELS * (BIT_DEPTH / 8);
  uint16_t blockAlign = NUM_CHANNELS * (BIT_DEPTH / 8);
  uint16_t bitsPerSample = BIT_DEPTH;
  
  char subchunk2ID[4] = {'d', 'a', 't', 'a'};
  uint32_t subchunk2Size = 0;
};

void sendWAVHeader(uint32_t dataSize) {
  WAVHeader header;
  header.subchunk2Size = dataSize;
  header.chunkSize = 36 + dataSize;
  
  // Send WAV header as binary over Serial
  Serial.write((uint8_t*)&header, sizeof(WAVHeader));
  Serial.flush();
}

void setup() {
  Serial.begin(115200);
  delay(500);  // Longer delay for serial to stabilize
  
  // Initialize ADC
  analogReadResolution(12); // 12-bit ADC
  pinMode(MIC_PIN, INPUT);
  
  // Pre-calculate total data size
  uint32_t totalSamples = RECORDING_TIME_SEC * SAMPLE_RATE;
  uint32_t dataSize = totalSamples * 2; // 16-bit samples
  
  // Send WAV header immediately (no text)
  sendWAVHeader(dataSize);
  Serial.flush();
  
  // Set up timer for sampling
  samplingTimer = timerBegin(0, 80, true);
  timerAttachInterrupt(samplingTimer, &onSamplingTimer, true);
  timerAlarmWrite(samplingTimer, 1000000 / SAMPLE_RATE, true);
  timerAlarmEnable(samplingTimer);
  
  isRecording = true;
  samplesRecorded = 0;
}

void loop() {
  unsigned long recordingEndTime = (unsigned long)RECORDING_TIME_SEC * 1000;
  unsigned long currentTime = millis();
  
  // Handle new ADC samples
  if (newSampleReady) {
    newSampleReady = false;
    
    // Write 16-bit sample to Serial
    uint16_t sample16 = adcSample;
    Serial.write((uint8_t*)&sample16, 2);
    
    samplesRecorded++;
    
    // Flush periodically to avoid buffer issues
    if (samplesRecorded % (SAMPLE_RATE / 10) == 0) {
      Serial.flush();
    }
  }
  
  // Stop recording after duration
  if (currentTime >= recordingEndTime && isRecording) {
    isRecording = false;
    timerAlarmDisable(samplingTimer);
    timerDetachInterrupt(samplingTimer);
    timerEnd(samplingTimer);
    
    Serial.flush();
    
    // Halt
    while (1) delay(1000);
  }
}

