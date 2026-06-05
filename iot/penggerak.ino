#include <AccelStepper.h>
#include <ESP32Servo.h>

#define IN1 26
#define IN2 33
#define IN3 25
#define IN4 32
#define SERVO_PIN 18

AccelStepper stepper(AccelStepper::FULL4WIRE, IN1, IN3, IN2, IN4);
Servo myservo;

const float STEPS_PER_REV = 2048.0;

int state = 0; 
unsigned long timer = 0;
float targetAngle = 0;

void setup() {
  stepper.setMaxSpeed(1000.0);
  stepper.setAcceleration(300.0);
  
  myservo.setPeriodHertz(50);
  myservo.attach(SERVO_PIN, 500, 2400);
  myservo.write(0);

  Serial.begin(115200);
  Serial.println("ESP32 SIAP - Menunggu perintah dari Python");
}

void loop() {
  // TERIMA PERINTAH DARI PYTHON
  if (state == 0 && Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    
    Serial.print("Perintah diterima: ");
    Serial.println(command);
    
    // PARSING PERINTAH: "plastik", "logam", atau "carton"
    if (command == "plastik") {
      targetAngle = 60.0;
      state = 1;
    } 
    else if (command == "logam") {
      targetAngle = 180.0;
      state = 1;
    } 
    else if (command == "carton") {
      targetAngle = 300.0;
      state = 1;
    }
    
    if (state == 1) {
      stepper.moveTo((targetAngle / 360.0) * STEPS_PER_REV);
      Serial.print("Bergerak ke sudut: ");
      Serial.println(targetAngle);
    }
  }

  // STATE 1: STEPPER BERGERAK
  if (state == 1) {
    stepper.run();
    if (stepper.distanceToGo() == 0) {
      myservo.write(90);
      timer = millis();
      state = 2;
      Serial.println("Servo ke 90 derajat");
    }
  } 
  // STATE 2: TUNGGU 1.5 DETIK
  else if (state == 2) {
    if (millis() - timer >= 1500) {
      myservo.write(0);
      delay(500);
      stepper.moveTo(0);
      state = 3;
      Serial.println("Servo kembali ke 0, Stepper reset");
    }
  }
  // STATE 3: STEPPER KEMBALI KE 0
  else if (state == 3) {
    stepper.run();
    if (stepper.distanceToGo() == 0) {
      state = 0;
      Serial.println("Sequence selesai - Siap perintah berikutnya");
    }
  }
}