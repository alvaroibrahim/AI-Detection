#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include "HX711.h"

// Definisi pin unik untuk masing-masing sensor
const int DOUT_1 = 13; const int SCK_1 = 12;
const int DOUT_2 = 14; const int SCK_2 = 27;
const int DOUT_3 = 35; const int SCK_3 = 34;

HX711 scale1, scale2, scale3;
LiquidCrystal_I2C lcd(0x27, 16, 2);

// Faktor kalibrasi masing-masing (silakan sesuaikan)
float cal1 = -416.31;
float cal2 = -429.93;
float cal3 = -429.43;

void setup() {
  Serial.begin(115200);
  lcd.init();
  lcd.backlight();

  // Inisialisasi setiap sensor dengan pin masing-masing
  scale1.begin(DOUT_1, SCK_1);
  scale2.begin(DOUT_2, SCK_2);
  scale3.begin(DOUT_3, SCK_3);

  scale1.set_scale(cal1); scale1.tare();
  scale2.set_scale(cal2); scale2.tare();
  scale3.set_scale(cal3); scale3.tare();

  lcd.print("Sistem Multi-LC");
  delay(2000);
  lcd.clear();
}

void loop() {
  // Membaca data dari ketiga sensor
  float b1 = (scale1.get_units(5) < 5) ? 0 : scale1.get_units(5);
  float b2 = (scale2.get_units(5) < 5) ? 0 : scale2.get_units(5);
  float b3 = (scale3.get_units(5) < 5) ? 0 : scale3.get_units(5);

  // Tampilan LCD
  lcd.setCursor(0, 0);
  lcd.print("T1:"); lcd.print((int)b1); lcd.print("g ");
  lcd.print("T2:"); lcd.print((int)b2); lcd.print("g ");

  lcd.setCursor(0, 1);
  lcd.print("T3:"); lcd.print((int)b3); lcd.print("g        ");

  delay(200);
}