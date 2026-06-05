#include <AccelStepper.h>
#include <ESP32Servo.h>
#include "HX711.h"
#include <MQUnifiedsensor.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// ====== LCD 20x4 ======
LiquidCrystal_I2C lcd(0x27, 20, 4);

// ====== PIN STEPPER MOTOR ======
#define IN1 26
#define IN2 33
#define IN3 25
#define IN4 32

// ====== PIN SERVO ======
#define SERVO_PIN 18

// ====== PIN ULTRASONIC (HCSR-05) ======
#define US_TRIG_1 4
#define US_ECHO_1 16
#define US_TRIG_2 17
#define US_ECHO_2 5
#define US_TRIG_3 2
#define US_ECHO_3 15

// ====== PIN MQ135 ======
#define MQ135_1 36
#define MQ135_2 39
#define MQ135_3 34

// ====== PIN LOADCELL (HX711) ======
#define HX711_DT_1 13
#define HX711_SCK_1 12
#define HX711_DT_2 14
#define HX711_SCK_2 27
#define HX711_DT_3 35
#define HX711_SCK_3 34

// ====== INISIALISASI ======
AccelStepper stepper(AccelStepper::FULL4WIRE, IN1, IN3, IN2, IN4);
Servo myservo;
HX711 loadcell1, loadcell2, loadcell3;

MQUnifiedsensor sensor_mq135[3] = {
  MQUnifiedsensor("ESP-32", 3.3, 12, 36, "MQ-135"),
  MQUnifiedsensor("ESP-32", 3.3, 12, 39, "MQ-135"),
  MQUnifiedsensor("ESP-32", 3.3, 12, 34, "MQ-135")
};

const float STEPS_PER_REV = 2048.0;
const float TINGGI_MAX = 60.0;
const float TINGGI_MIN = 6.0;

// ====== STRUCT DATA SENSOR ======
struct SensorData {
  float distance[3];
  float co2[3];
  float weight[3];
  float volume[3];
} sensor_data;

int state = 0;
unsigned long timer = 0;
float targetAngle = 0;
unsigned long last_sensor_read = 0;
unsigned long last_lcd_update = 0;
const unsigned long SENSOR_READ_INTERVAL = 500;
const unsigned long LCD_UPDATE_INTERVAL = 1000;

String last_command = "STANDBY";
unsigned long command_time = 0;

void setup() {
  // ====== LCD INIT ======
  lcd.init();
  lcd.backlight();
  lcd.clear();
  
  lcd.setCursor(0, 0);
  lcd.print("   TRASH SYSTEM");
  lcd.setCursor(0, 1);
  lcd.print("  Initializing...");
  lcd.setCursor(0, 2);
  lcd.print("   Please Wait");
  lcd.setCursor(0, 3);
  lcd.print("   ");
  
  // ====== STEPPER & SERVO ======
  stepper.setMaxSpeed(1000.0);
  stepper.setAcceleration(300.0);
  myservo.setPeriodHertz(50);
  myservo.attach(SERVO_PIN, 500, 2400);
  myservo.write(0);

  // ====== ULTRASONIC PIN ======
  pinMode(US_TRIG_1, OUTPUT); pinMode(US_ECHO_1, INPUT);
  pinMode(US_TRIG_2, OUTPUT); pinMode(US_ECHO_2, INPUT);
  pinMode(US_TRIG_3, OUTPUT); pinMode(US_ECHO_3, INPUT);

  // ====== LOADCELL (HX711) ======
  loadcell1.begin(HX711_DT_1, HX711_SCK_1);
  loadcell2.begin(HX711_DT_2, HX711_SCK_2);
  loadcell3.begin(HX711_DT_3, HX711_SCK_3);
  
  loadcell1.set_scale(-416.31);
  loadcell2.set_scale(-429.93);
  loadcell3.set_scale(-429.43);
  
  loadcell1.tare();
  loadcell2.tare();
  loadcell3.tare();

  // ====== MQ135 SETUP ======
  for (int i = 0; i < 3; i++) {
    sensor_mq135[i].setRegressionMethod(1);
    sensor_mq135[i].setA(110.47);
    sensor_mq135[i].setB(-2.862);
    sensor_mq135[i].init();
    sensor_mq135[i].setR0(40.0);
  }

  // ====== SERIAL ======
  Serial.begin(115200);
  delay(2000);
  
  lcd.clear();
  Serial.println("\n========================================");
  Serial.println("🚀 ESP32 SIAP - LCD 20x4 Mode");
  Serial.println("📊 Sensor: Ultrasonic, MQ135, LoadCell");
  Serial.println("🎛️  Actuator: Stepper Motor, Servo");
  Serial.println("========================================");
}

void loop() {
  // ====== BACA SENSOR PERIODIK ======
  if (millis() - last_sensor_read >= SENSOR_READ_INTERVAL) {
    readAllSensors();
    last_sensor_read = millis();
  }

  // ====== UPDATE LCD ======
  if (millis() - last_lcd_update >= LCD_UPDATE_INTERVAL) {
    updateLCD();
    last_lcd_update = millis();
  }

  // ====== TERIMA PERINTAH DARI PYTHON ======
  if (state == 0 && Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    
    Serial.print("📥 Perintah diterima: ");
    Serial.println(command);
    
    if (command == "sensor_data") {
      sendSensorDataJSON();
      return;
    }
    
    if (command == "plastik") {
      targetAngle = 60.0;
      last_command = "PLASTIK -> 60°";
      state = 1;
    } 
    else if (command == "logam") {
      targetAngle = 180.0;
      last_command = "LOGAM -> 180°";
      state = 1;
    } 
    else if (command == "carton") {
      targetAngle = 300.0;
      last_command = "CARTON -> 300°";
      state = 1;
    }
    
    if (state == 1) {
      stepper.moveTo((targetAngle / 360.0) * STEPS_PER_REV);
      command_time = millis();
      Serial.print("🔄 Stepper bergerak ke: ");
      Serial.println(targetAngle);
    }
  }

  // ====== STATE MACHINE STEPPER & SERVO ======
  // STATE 1: STEPPER BERGERAK
  if (state == 1) {
    stepper.run();
    if (stepper.distanceToGo() == 0) {
      myservo.write(90);
      timer = millis();
      state = 2;
      Serial.println("✅ Servo ke 90 derajat");
    }
  } 
  // STATE 2: TUNGGU 1.5 DETIK
  else if (state == 2) {
    if (millis() - timer >= 1500) {
      myservo.write(0);
      delay(500);
      stepper.moveTo(0);
      state = 3;
      Serial.println("↩️  Servo kembali ke 0, Stepper reset");
    }
  }
  // STATE 3: STEPPER KEMBALI KE 0
  else if (state == 3) {
    stepper.run();
    if (stepper.distanceToGo() == 0) {
      state = 0;
      last_command = "STANDBY";
      Serial.println("✅ Sequence selesai - Siap perintah berikutnya");
    }
  }
}

// ====== FUNGSI BACA SEMUA SENSOR ======
void readAllSensors() {
  // ====== ULTRASONIC ======
  sensor_data.distance[0] = readUltrasonic(US_TRIG_1, US_ECHO_1);
  sensor_data.distance[1] = readUltrasonic(US_TRIG_2, US_ECHO_2);
  sensor_data.distance[2] = readUltrasonic(US_TRIG_3, US_ECHO_3);

  // ====== HITUNG VOLUME ======
  for (int i = 0; i < 3; i++) {
    if (sensor_data.distance[i] >= TINGGI_MAX) {
      sensor_data.volume[i] = 0;
    } else if (sensor_data.distance[i] <= TINGGI_MIN) {
      sensor_data.volume[i] = 90;
    } else {
      sensor_data.volume[i] = ((TINGGI_MAX - sensor_data.distance[i]) / (TINGGI_MAX - TINGGI_MIN)) * 90;
    }
  }

  // ====== MQ135 (CO2) ======
  for (int i = 0; i < 3; i++) {
    sensor_mq135[i].update();
    sensor_data.co2[i] = sensor_mq135[i].readSensor();
  }

  // ====== LOADCELL ======
  sensor_data.weight[0] = abs(loadcell1.get_units(5));
  sensor_data.weight[1] = abs(loadcell2.get_units(5));
  sensor_data.weight[2] = abs(loadcell3.get_units(5));
}

// ====== UPDATE LCD 20x4 ======
void updateLCD() {
  // BARIS 1: VOLUME SAMPAH
  lcd.setCursor(0, 0);
  lcd.print("VOL:");
  lcd.print((int)sensor_data.volume[0]);
  lcd.print("% ");
  lcd.print((int)sensor_data.volume[1]);
  lcd.print("% ");
  lcd.print((int)sensor_data.volume[2]);
  lcd.print("%      ");

  // BARIS 2: BERAT SAMPAH (kg)
  lcd.setCursor(0, 1);
  lcd.print("W:");
  lcd.print(sensor_data.weight[0]/1000, 1);
  lcd.print("kg ");
  lcd.print(sensor_data.weight[1]/1000, 1);
  lcd.print("kg ");
  lcd.print(sensor_data.weight[2]/1000, 1);
  lcd.print("kg  ");

  // BARIS 3: CO2 (ppm)
  lcd.setCursor(0, 2);
  lcd.print("CO2:");
  lcd.print((int)sensor_data.co2[0]);
  lcd.print("p ");
  lcd.print((int)sensor_data.co2[1]);
  lcd.print("p ");
  lcd.print((int)sensor_data.co2[2]);
  lcd.print("p   ");

  // BARIS 4: STATUS / PERINTAH TERAKHIR
  lcd.setCursor(0, 3);
  
  // Cek status keseluruhan
  bool ada_penuh = false;
  int box_penuh = -1;
  for (int i = 0; i < 3; i++) {
    if (sensor_data.volume[i] >= 80) {
      ada_penuh = true;
      box_penuh = i + 1;
      break;
    }
  }
  
  if (ada_penuh) {
    lcd.print("!BOX");
    lcd.print(box_penuh);
    lcd.print(" PENUH!    ");
  } else if (state > 0) {
    // Tampilkan perintah yang sedang dijalankan
    lcd.print(last_command);
    lcd.print("         ");
  } else {
    // Status normal
    lcd.print("NORMAL - STANDBY");
    lcd.print("    ");
  }
}

// ====== FUNGSI BACA ULTRASONIC ======
float readUltrasonic(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  
  long duration = pulseIn(echoPin, HIGH, 30000);
  if (duration == 0) return 999;
  
  float distance = (duration * 0.0343) / 2;
  return distance;
}

// ====== KIRIM DATA KE PYTHON (JSON) ======
void sendSensorDataJSON() {
  String json = "{";
  json += "\"distance\":[" + String(sensor_data.distance[0], 2) + "," + String(sensor_data.distance[1], 2) + "," + String(sensor_data.distance[2], 2) + "],";
  json += "\"volume\":[" + String((int)sensor_data.volume[0]) + "," + String((int)sensor_data.volume[1]) + "," + String((int)sensor_data.volume[2]) + "],";
  json += "\"weight\":[" + String(sensor_data.weight[0]/1000, 2) + "," + String(sensor_data.weight[1]/1000, 2) + "," + String(sensor_data.weight[2]/1000, 2) + "],";
  json += "\"co2\":[" + String((int)sensor_data.co2[0]) + "," + String((int)sensor_data.co2[1]) + "," + String((int)sensor_data.co2[2]) + "]";
  json += "}";
  
  Serial.println(json);
}

// ====== FUNGSI HELPER PROGRESS BAR ======
String getProgressBar(float volume, int width) {
  int filled = map(volume, 0, 90, 0, width);
  String bar = "[";
  for (int i = 0; i < width; i++) {
    if (i < filled) bar += "=";
    else bar += "-";
  }
  bar += "]";
  return bar;
}
