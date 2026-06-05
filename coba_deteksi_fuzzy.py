"""
Integrasi Fuzzy Logic ke dalam Sistem Deteksi AI
Menambahkan notifikasi berbasis fuzzy logic untuk monitoring status sampah

Usage:
  Jalankan file ini untuk test atau import FuzzyTrashSystem ke deteksi.py
"""

import cv2
import os
import time
import serial
from ultralytics import YOLO
from datetime import datetime
from fuzzy_logic import FuzzyTrashSystem, SensorInput, NotificationLevel
import json

# ==========================================
# KONFIGURASI
# ==========================================
model_path = "D:\\PNJ\\SKRIPSI\\Ai Detection\\runs\\segment\\train\\weights\\best.pt"
model = YOLO(model_path)

target_classes = ['plastik', 'logam', 'carton'] 
base_dir = 'Cropped'
target_width = 640
target_height = 640
VALIDATION_DURATION = 3

# Serial ESP32
SERIAL_PORT = 'COM12'
BAUD_RATE = 115200

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)
    print(f"✅ Terhubung ke ESP32 di {SERIAL_PORT}")
except Exception as e:
    print(f"❌ Error koneksi serial: {e}")
    ser = None

# Fuzzy Logic System
fuzzy_system = FuzzyTrashSystem()

# Variabel tracking
last_sent_class = None
last_sent_time = 0
SEND_COOLDOWN = 5

last_fuzzy_check = 0
FUZZY_CHECK_INTERVAL = 2000  # Check fuzzy logic setiap 2 detik
last_sensor_data = {}  # Cache sensor data dari ESP32

for cls_name in target_classes:
    os.makedirs(os.path.join(base_dir, cls_name), exist_ok=True)

# ==========================================
# FUNGSI FUZZY LOGIC
# ==========================================
def request_sensor_data():
    """Request data sensor dari ESP32"""
    global ser, last_sensor_data
    
    if not ser or not ser.is_open:
        return None
    
    try:
        ser.write(b"sensor_data\n")
        time.sleep(0.5)
        
        if ser.in_waiting > 0:
            data_line = ser.readline().decode().strip()
            
            # Parse JSON response
            try:
                sensor_data = json.loads(data_line)
                last_sensor_data = sensor_data
                return sensor_data
            except json.JSONDecodeError:
                print(f"⚠️  Invalid JSON from ESP32: {data_line}")
                return None
    except Exception as e:
        print(f"❌ Error reading sensor: {e}")
        return None
    
    return None

def process_fuzzy_logic():
    """Process sensor data dengan fuzzy logic"""
    global fuzzy_system, last_fuzzy_check, last_sensor_data
    
    current_time = time.time() * 1000
    
    if current_time - last_fuzzy_check < FUZZY_CHECK_INTERVAL:
        return
    
    # Request sensor data dari ESP32
    sensor_data = request_sensor_data()
    if not sensor_data:
        return
    
    print("\n" + "="*70)
    print(f"🔍 FUZZY LOGIC ANALYSIS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    try:
        # Process untuk setiap box (plastik, kertas/carton, logam)
        box_names = ["PLASTIK", "KERTAS", "LOGAM"]
        fuzzy_results = {}
        
        for box_id, box_name in enumerate(box_names, 1):
            # Ambil data sensor untuk box ini
            volume = sensor_data["volume"][box_id - 1]
            weight = sensor_data["weight"][box_id - 1]
            co2 = sensor_data["co2"][box_id - 1]
            
            # Create sensor input
            sensor_input = SensorInput(
                volume=volume,
                weight=weight,
                co2=co2
            )
            
            # Process dengan fuzzy logic
            fuzzy_output = fuzzy_system.process_box(box_id, sensor_input)
            fuzzy_results[box_id] = fuzzy_output
            
            # Print hasil
            print(f"\n📦 BOX {box_id}: {box_name}")
            print(f"   ├─ Volume: {volume:.1f}% | Berat: {weight:.2f} kg | CO2: {co2:.0f} ppm")
            print(f"   ├─ Level: {fuzzy_output.notification_level.value} (Confidence: {fuzzy_output.confidence:.1%})")
            print(f"   ├─ Reason: {fuzzy_output.reason}")
            print(f"   └─ Action: {fuzzy_output.recommended_action}")
            
            # Alert jika CRITICAL atau HIGH
            if fuzzy_output.notification_level in [NotificationLevel.CRITICAL, NotificationLevel.HIGH]:
                send_alert_to_serial(box_id, box_name, fuzzy_output)
        
        print("\n" + "="*70)
        last_fuzzy_check = current_time
        
    except Exception as e:
        print(f"❌ Error processing fuzzy logic: {e}")

def send_alert_to_serial(box_id: int, box_name: str, fuzzy_output):
    """Kirim alert ke ESP32 untuk kontrol LED/buzzer"""
    global ser
    
    if not ser or not ser.is_open:
        return
    
    try:
        # Format: ALERT,box_id,level
        alert_command = f"ALERT,{box_id},{fuzzy_output.notification_level.value}\n"
        ser.write(alert_command.encode())
        print(f"📤 Alert dikirim ke ESP32: {fuzzy_output.notification_level.value}")
    except Exception as e:
        print(f"❌ Error sending alert: {e}")

def send_to_esp32(class_name):
    """Mengirim perintah ke ESP32 berdasarkan kelas yang terdeteksi"""
    global last_sent_class, last_sent_time, ser
    
    current_time = time.time()
    
    if class_name == last_sent_class and (current_time - last_sent_time) < SEND_COOLDOWN:
        return
    
    if ser and ser.is_open:
        try:
            command = f"{class_name}\n"
            ser.write(command.encode())
            print(f"📤 Perintah terkirim ke ESP32: {class_name.upper()}")
            last_sent_class = class_name
            last_sent_time = current_time
        except Exception as e:
            print(f"❌ Error pengiriman: {e}")

# ==========================================
# MAIN LOOP DETEKSI
# ==========================================
track_state = {}
class_counters = {cls: 0 for cls in target_classes}

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

print(f"Memulai deteksi... Objek wajib berada di frame selama {VALIDATION_DURATION} detik untuk divalidasi.")
print("Tekan 'q' pada window video untuk keluar.")
print("="*70)

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    results = model.track(frame, persist=True, verbose=False, conf=0.5, iou=0.45)
    current_time = time.time()

    # ====== FUZZY LOGIC CHECK (SETIAP 2 DETIK) ======
    process_fuzzy_logic()

    if results[0].boxes.id is not None:
        boxes = results[0].boxes.xyxy.cpu().numpy()
        yolo_track_ids = results[0].boxes.id.int().cpu().numpy()
        class_ids = results[0].boxes.cls.int().cpu().numpy()
        confs = results[0].boxes.conf.cpu().numpy()

        for box, yolo_id, class_id, conf in zip(boxes, yolo_track_ids, class_ids, confs):
            cls_name_raw = model.names[class_id]
            cls_name = cls_name_raw.lower().strip()

            if cls_name not in target_classes:
                continue

            if yolo_id not in track_state:
                track_state[yolo_id] = {
                    'class_name': cls_name,
                    'start_time': current_time,
                    'last_print_time': current_time,
                    'saved': False,
                    'custom_id': None
                }
                elapsed_time = 0
            else:
                if track_state[yolo_id]['class_name'] == cls_name:
                    elapsed_time = current_time - track_state[yolo_id]['start_time']
                else:
                    track_state[yolo_id] = {
                        'class_name': cls_name,
                        'start_time': current_time,
                        'last_print_time': current_time,
                        'saved': False,
                        'custom_id': None
                    }
                    elapsed_time = 0

            if elapsed_time >= VALIDATION_DURATION:
                if track_state[yolo_id]['custom_id'] is None:
                    class_counters[cls_name] += 1
                    track_state[yolo_id]['custom_id'] = class_counters[cls_name]
                
                current_class_id = track_state[yolo_id]['custom_id']

                if not track_state[yolo_id]['saved']:
                    x1, y1, x2, y2 = map(int, box)
                    padding = 10
                    h, w, _ = frame.shape
                    x1, y1 = max(0, x1 - padding), max(0, y1 - padding)
                    x2, y2 = min(w, x2 + padding), min(h, y2 + padding)
                    
                    cropped_img = frame[y1:y2, x1:x2]

                    if cropped_img.size != 0:
                        resized_img = cv2.resize(cropped_img, (target_width, target_height))
                        filename = f"obj_{current_class_id}_{cls_name}.jpg"
                        save_path = os.path.join(base_dir, cls_name, filename)
                        cv2.imwrite(save_path, resized_img)
                        
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        print(f"[{timestamp}] OBJECT VALIDATED & SAVED")
                        print(f" ↳ ID Objek : {current_class_id}")
                        print(f" ↳ Class    : {cls_name.upper()}")
                        print(f" ↳ Score    : {conf:.2f} ({(conf*100):.1f}%)")
                        print(f" ↳ Path     : {save_path}")
                        print("-"*60)
                        
                        send_to_esp32(cls_name)
                        track_state[yolo_id]['saved'] = True

                if current_time - track_state[yolo_id]['last_print_time'] >= 1.0:
                    t_track = datetime.now().strftime("%H:%M:%S")
                    print(f"[{t_track}] Melacak... {cls_name.upper()} | ID: {current_class_id} | Score: {conf:.2f} | Durasi: {elapsed_time:.1f}s")
                    track_state[yolo_id]['last_print_time'] = current_time

    annotated_frame = results[0].plot()
    cv2.imshow("Sistem Deteksi Sampah - Skripsi", annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        print("\nSistem dihentikan oleh pengguna.")
        print("Total Objek Tersimpan:", class_counters)
        print("\n📊 Exporting notification history...")
        fuzzy_system.notification_manager.export_to_json("trash_notifications_log.json")
        break

cap.release()
cv2.destroyAllWindows()

if ser and ser.is_open:
    ser.close()
    print("Serial connection closed")

print("\n✓ Program selesai")
