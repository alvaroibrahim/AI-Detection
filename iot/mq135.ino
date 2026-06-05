#include <MQUnifiedsensor.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

LiquidCrystal_I2C lcd(0x27, 16, 2);

// Konfigurasi
#define placa "ESP-32"
#define Voltage_Resolution 3.3
#define ADC_Bit_Resolution 12
#define RatioMQ135CleanAir 3.6
const int NUM_SENSORS = 3;
const int FILTER_SIZE = 10;
const int MQ_PINS[] = {36, 39, 34}; 
const float R0_MANUAL[] = {53.27, 31.65, 43.09}; 
const int THRESHOLD = 30;

MQUnifiedsensor* sensor[NUM_SENSORS];
float ppmBuffer[NUM_SENSORS][FILTER_SIZE];
int bufferIndex[NUM_SENSORS] = {0, 0, 0};

// Variabel Running Text
String message = "Semua Tong Aman Masih Bersih";
int scrollPos = 16;
unsigned long lastScrollTime = 0;

void setup() {
  Serial.begin(115200);
  lcd.init();
  lcd.backlight();

  for (int i = 0; i < NUM_SENSORS; i++) {
    sensor[i] = new MQUnifiedsensor(placa, Voltage_Resolution, ADC_Bit_Resolution, MQ_PINS[i], "MQ-135");
    sensor[i]->setRegressionMethod(1); 
    sensor[i]->setA(110.47); sensor[i]->setB(-2.862);
    sensor[i]->init();
    sensor[i]->setR0(R0_MANUAL[i]);
  }
}

float getMovingAverage(int i, float val) {
  ppmBuffer[i][bufferIndex[i]] = val;
  bufferIndex[i] = (bufferIndex[i] + 1) % FILTER_SIZE;
  float sum = 0;
  for(int j=0; j<FILTER_SIZE; j++) sum += ppmBuffer[i][j];
  return sum/FILTER_SIZE;
}

void loop() {
  float currentPpm[3];
  bool adaBau = false;
  String bauTong = "";

  // Update & hitung PPM
  for (int i = 0; i < NUM_SENSORS; i++) {
    sensor[i]->update();
    currentPpm[i] = getMovingAverage(i, sensor[i]->readSensor());
    if (currentPpm[i] > THRESHOLD) {
      adaBau = true;
      bauTong = String(i + 1);
    }
  }

  // Tampilan Baris 1: Status PPM (T1:XX T2:XX T3:XX)
  lcd.setCursor(0, 0);
  lcd.print("T1:" + String((int)currentPpm[0]) + " T2:" + String((int)currentPpm[1]) + " T3:" + String((int)currentPpm[2]));

  // Logika Running Text
  if (adaBau) {
    message = "Tong " + bauTong + " Bau Banget, segera bersihkan!";
  } else {
    message = "Semua Tong Aman Masih Bersih";
  }

  // Efek Running Text
  if (millis() - lastScrollTime > 300) { // Kecepatan scroll
    lcd.setCursor(0, 1);
    String displayMsg = "";
    for (int i = 0; i < 16; i++) {
      int charIdx = (scrollPos + i) % message.length();
      displayMsg += message[charIdx];
    }
    lcd.print(displayMsg);
    scrollPos++;
    if (scrollPos >= message.length()) scrollPos = 0;
    lastScrollTime = millis();
  }
}