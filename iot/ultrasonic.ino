#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// ============ DEFINE PIN UNTUK 3 SENSOR ULTRASONIC ============
// LCD tetap menggunakan pin default I2C (21=SDA, 22=SCL)
// Sensor Plastik - TRIG=4, ECHO=16
#define TRIG_PIN_PLASTIK 4
#define ECHO_PIN_PLASTIK 16

// Sensor Kertas - TRIG=17, ECHO=5
#define TRIG_PIN_KERTAS 17
#define ECHO_PIN_KERTAS 5

// Sensor Metal - TRIG=18, ECHO=19
#define TRIG_PIN_METAL 18
#define ECHO_PIN_METAL 19

// Inisialisasi LCD dengan alamat I2C (biasanya 0x27 atau 0x3F)
LiquidCrystal_I2C lcd(0x27, 16, 2);

// ============ KONSTANTA KALIBRASI ============
const float TINGGI_MAX = 60.0;  // Tinggi maksimum tempat sampah (cm) -> volume 0%
const float TINGGI_MIN = 6.0;   // Tinggi minimum (sampah penuh) (cm) -> volume 90%
const float VOLUME_MAX = 90.0;   // Persentase volume maksimum saat penuh
const float VOLUME_MIN = 0.0;    // Persentase volume minimum saat kosong

// ============ STRUKTUR UNTUK SETIAP SENSOR ============
struct SensorData {
  String nama;
  String singkatan;
  int trigPin;
  int echoPin;
  float jarak;
  float volumePersen;
  float tinggiSampah;
  bool status;
};

// Inisialisasi 3 sensor
SensorData sensorPlastik = {"Plastik", "P", TRIG_PIN_PLASTIK, ECHO_PIN_PLASTIK, 0, 0, 0, true};
SensorData sensorKertas = {"Kertas", "K", TRIG_PIN_KERTAS, ECHO_PIN_KERTAS, 0, 0, 0, true};
SensorData sensorMetal = {"Metal", "M", TRIG_PIN_METAL, ECHO_PIN_METAL, 0, 0, 0, true};

// Variabel untuk timing
unsigned long timeNow = 0;
unsigned long timePrev = 0;
const unsigned long interval = 1000; // Mengukur setiap 1 detik

void setup() {
  Serial.begin(115200);
  
  // Inisialisasi semua pin ultrasonic
  initSensor(sensorPlastik);
  initSensor(sensorKertas);
  initSensor(sensorMetal);
  
  // Inisialisasi LCD
  lcd.init();
  lcd.backlight();
  lcd.clear();
  
  // Tampilkan pesan awal
  lcd.setCursor(0, 0);
  lcd.print("3-Way Trash Bin");
  lcd.setCursor(0, 1);
  lcd.print("System Ready...");
  delay(2000);
  lcd.clear();
  
  Serial.println("System Started - 3 Sensor Trash Monitor");
  Serial.println("========================================");
  Serial.println("Pin Configuration:");
  Serial.println("  - LCD: SDA=21, SCL=22");
  Serial.println("  - Plastik: TRIG=4, ECHO=16");
  Serial.println("  - Kertas: TRIG=17, ECHO=5");
  Serial.println("  - Metal: TRIG=18, ECHO=19");
  Serial.println("========================================");
  Serial.println("Monitoring: Plastik | Kertas | Metal");
  Serial.println("========================================");
}

void loop() {
  timeNow = millis();
  
  // Mengukur semua sensor setiap interval waktu
  if (timeNow - timePrev >= interval) {
    timePrev = timeNow;
    
    // Baca semua sensor
    bacaSemuaSensor();
    
    // Hitung volume untuk semua sensor
    hitungVolumeSemua();
    
    // Tampilkan data ke LCD (format sederhana)
    tampilkanVolumeLCD();
    
    // Kirim data lengkap ke Serial Monitor
    tampilkanSerialMonitor();
  }
}

// ============ FUNGSI INISIALISASI SENSOR ============
void initSensor(SensorData &sensor) {
  pinMode(sensor.trigPin, OUTPUT);
  pinMode(sensor.echoPin, INPUT);
}

// ============ FUNGSI BACA SEMUA SENSOR ============
void bacaSemuaSensor() {
  bacaJarak(sensorPlastik);
  delay(50); // Delay antar sensor untuk menghindari interferensi
  bacaJarak(sensorKertas);
  delay(50);
  bacaJarak(sensorMetal);
}

// ============ FUNGSI BACA JARAK SENSOR ============
void bacaJarak(SensorData &sensor) {
  digitalWrite(sensor.trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(sensor.trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(sensor.trigPin, LOW);
  
  long duration = pulseIn(sensor.echoPin, HIGH, 30000); // Timeout 30ms
  
  if (duration == 0) {
    sensor.status = false;
    sensor.jarak = -1;
    Serial.print("Warning: No echo from ");
    Serial.println(sensor.nama);
    return;
  }
  
  sensor.status = true;
  // Hitung jarak dalam cm (kecepatan suara 343 m/s = 0.0343 cm/us)
  sensor.jarak = duration * 0.0343 / 2;
}

// ============ FUNGSI HITUNG VOLUME SEMUA SENSOR ============
void hitungVolumeSemua() {
  hitungVolume(sensorPlastik);
  hitungVolume(sensorKertas);
  hitungVolume(sensorMetal);
}

void hitungVolume(SensorData &sensor) {
  if (!sensor.status || sensor.jarak < 0) {
    sensor.volumePersen = 0;
    sensor.tinggiSampah = 0;
    return;
  }
  
  // Validasi data
  if (sensor.jarak >= 0 && sensor.jarak <= TINGGI_MAX + 10) {
    // Hitung tinggi sampah (semakin kecil jarak, semakin penuh)
    sensor.tinggiSampah = TINGGI_MAX - sensor.jarak;
    
    // Batasi nilai tinggi sampah
    if (sensor.tinggiSampah < 0) sensor.tinggiSampah = 0;
    if (sensor.tinggiSampah > TINGGI_MAX) sensor.tinggiSampah = TINGGI_MAX;
    
    // Hitung persentase volume
    if (sensor.jarak >= TINGGI_MAX) {
      sensor.volumePersen = 0.0;
    } else if (sensor.jarak <= TINGGI_MIN) {
      sensor.volumePersen = VOLUME_MAX;
    } else {
      float rangeJarak = TINGGI_MAX - TINGGI_MIN;
      float rangeVolume = VOLUME_MAX - VOLUME_MIN;
      sensor.volumePersen = VOLUME_MIN + ((TINGGI_MAX - sensor.jarak) / rangeJarak) * rangeVolume;
      
      if (sensor.volumePersen < 0) sensor.volumePersen = 0;
      if (sensor.volumePersen > VOLUME_MAX) sensor.volumePersen = VOLUME_MAX;
    }
  } else {
    sensor.status = false;
    sensor.volumePersen = 0;
  }
}

// ============ TAMPILAN LCD SEDERHANA ============
void tampilkanVolumeLCD() {
  // Baris 1: P=--% K=--%
  lcd.setCursor(0, 0);
  
  // Plastik
  lcd.print("P=");
  if (!sensorPlastik.status) {
    lcd.print("--");
  } else {
    if (sensorPlastik.volumePersen >= 100) {
      lcd.print("99");
    } else if (sensorPlastik.volumePersen >= 10) {
      lcd.print((int)sensorPlastik.volumePersen);
    } else {
      lcd.print((int)sensorPlastik.volumePersen);
      lcd.print(" ");
    }
  }
  lcd.print("% ");
  
  // Kertas
  lcd.print("K=");
  if (!sensorKertas.status) {
    lcd.print("--");
  } else {
    if (sensorKertas.volumePersen >= 100) {
      lcd.print("99");
    } else if (sensorKertas.volumePersen >= 10) {
      lcd.print((int)sensorKertas.volumePersen);
    } else {
      lcd.print((int)sensorKertas.volumePersen);
      lcd.print(" ");
    }
  }
  lcd.print("%");
  
  // Baris 2: M=--%
  lcd.setCursor(0, 1);
  
  // Metal
  lcd.print("M=");
  if (!sensorMetal.status) {
    lcd.print("--");
  } else {
    if (sensorMetal.volumePersen >= 100) {
      lcd.print("99");
    } else if (sensorMetal.volumePersen >= 10) {
      lcd.print((int)sensorMetal.volumePersen);
    } else {
      lcd.print((int)sensorMetal.volumePersen);
    }
  }
  lcd.print("%");
  
  // Tambahan indikator bar progress sederhana di sebelah kanan
  lcd.setCursor(6, 1);
  lcd.print(" [");
  tampilkanBarProgress(sensorMetal.volumePersen, 4);
  lcd.print("]");
  
  // Tambahan indikator jika ada yang penuh
  if (sensorPlastik.volumePersen >= 80 || sensorKertas.volumePersen >= 80 || sensorMetal.volumePersen >= 80) {
    lcd.setCursor(14, 0);
    lcd.print("!");
  } else {
    lcd.setCursor(14, 0);
    lcd.print(" ");
  }
}

void tampilkanBarProgress(float volume, int maxLength) {
  int barLength = map(volume, 0, VOLUME_MAX, 0, maxLength);
  for (int i = 0; i < maxLength; i++) {
    if (i < barLength) {
      lcd.print("#");
    } else {
      lcd.print(".");
    }
  }
}

// ============ FUNGSI UNTUK MENAMPILKAN KE SERIAL MONITOR ============
void tampilkanSerialMonitor() {
  Serial.println("========================================");
  Serial.println("        TRASH LEVEL MONITORING          ");
  Serial.println("========================================");
  
  tampilkanDataSensor(sensorPlastik, "PLASTIK");
  tampilkanDataSensor(sensorKertas, "KERTAS");
  tampilkanDataSensor(sensorMetal, "METAL");
  
  Serial.println("========================================");
  Serial.println();
}

void tampilkanDataSensor(SensorData &sensor, String jenis) {
  Serial.print(jenis);
  Serial.println(" Waste:");
  Serial.print("  - Jarak sensor: ");
  
  if (!sensor.status || sensor.jarak < 0) {
    Serial.println("Error / No signal");
    Serial.print("  - Volume: --%");
  } else {
    Serial.print(sensor.jarak, 1);
    Serial.println(" cm");
    Serial.print("  - Tinggi sampah: ");
    Serial.print(sensor.tinggiSampah, 1);
    Serial.println(" cm");
    Serial.print("  - Volume: ");
    Serial.print(sensor.volumePersen, 1);
    Serial.println("%");
    
    // Status rekomendasi
    if (sensor.volumePersen >= 80) {
      Serial.println("  - Status: [FULL] Segera kosongkan!");
    } else if (sensor.volumePersen >= 60) {
      Serial.println("  - Status: [WARNING] Hampir penuh");
    } else if (sensor.volumePersen >= 30) {
      Serial.println("  - Status: [OK] Terisi sedang");
    } else {
      Serial.println("  - Status: [GOOD] Masih banyak ruang");
    }
  }
  Serial.println();
}

// ============ FUNGSI TAMBAHAN UNTUK MENDAPATKAN DATA ============
float getVolumePlastik() {
  return sensorPlastik.volumePersen;
}

float getVolumeKertas() {
  return sensorKertas.volumePersen;
}

float getVolumeMetal() {
  return sensorMetal.volumePersen;
}

String getStatusKeseluruhan() {
  if (sensorPlastik.volumePersen >= 80 || sensorKertas.volumePersen >= 80 || sensorMetal.volumePersen >= 80) {
    return "PERLU Dikosongkan";
  } else if (sensorPlastik.volumePersen >= 60 || sensorKertas.volumePersen >= 60 || sensorMetal.volumePersen >= 60) {
    return "Hampir penuh";
  } else {
    return "Masih aman";
  }
}