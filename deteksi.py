import cv2
import os
import time
import threading
try:
    import serial
except ImportError:
    serial = None
    print("⚠️ Modul 'pyserial' tidak ditemukan; jalankan 'pip install pyserial' jika ingin koneksi ESP32. Menggunakan mode tanpa serial.")
from ultralytics import YOLO
from datetime import datetime

# ==========================================
# 1. KONFIGURASI MODEL & SERIAL ESP32
# ==========================================
model_path = "D:\\PNJ\\SKRIPSI\\Ai Detection\\runs\\segment\\train\\weights\\best.pt"
model = YOLO(model_path)

target_classes = ['plastik', 'logam', 'carton'] 
base_dir = 'Cropped'
target_width = 640
target_height = 640
VALIDATION_DURATION = 3

# --- KONFIGURASI SERIAL ESP32 ---
SERIAL_PORT = 'COM12'  # Ganti dengan port ESP32 Anda (cek di Arduino IDE)
BAUD_RATE = 115200

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)  # Tunggu ESP32 siap
    print(f"✅ Terhubung ke ESP32 di {SERIAL_PORT}")
except Exception as e:
    print(f"❌ Error koneksi serial: {e}")
    ser = None

# Variabel untuk menghindari pengiriman berulang
last_sent_class = None
last_sent_time = 0
SEND_COOLDOWN = 5  # Jangan kirim perintah lebih dari 1x per 5 detik

# Variabel untuk pause/resume camera
camera_paused = False
esp32_busy = False
pause_start_time = 0
PAUSE_TIMEOUT = 15  # Timeout 15 detik jika ESP32 tidak respond

for cls_name in target_classes:
    os.makedirs(os.path.join(base_dir, cls_name), exist_ok=True)

# ==========================================
# 2. FUNGSI UNTUK MENGIRIM PERINTAH KE ESP32
# ==========================================
def send_to_esp32(class_name):
    """Mengirim perintah ke ESP32 berdasarkan kelas yang terdeteksi"""
    global last_sent_class, last_sent_time, camera_paused, esp32_busy, pause_start_time
    
    current_time = time.time()
    
    # Cegah pengiriman berulang dalam waktu singkat
    if class_name == last_sent_class and (current_time - last_sent_time) < SEND_COOLDOWN:
        return
    
    if ser and ser.is_open:
        try:
            # ====== PAUSE CAMERA ======
            camera_paused = True
            esp32_busy = True
            pause_start_time = time.time()
            
            command = f"{class_name}\n"
            ser.write(command.encode())
            print(f"📤 Perintah terkirim ke ESP32: {class_name.upper()}")
            print(f"⏸️  Kamera PAUSED - Menunggu ESP32 selesai...")
            
            last_sent_class = class_name
            last_sent_time = current_time
        except Exception as e:
            print(f"❌ Error pengiriman: {e}")
            camera_paused = False
            esp32_busy = False

def check_esp32_status():
    """Check apakah ESP32 sudah selesai"""
    global esp32_busy, camera_paused, pause_start_time
    
    if not esp32_busy or not ser or not ser.is_open:
        return
    
    current_time = time.time()
    elapsed_time = current_time - pause_start_time
    
    # Cek timeout (15 detik)
    if elapsed_time > PAUSE_TIMEOUT:
        print(f"⏱️  TIMEOUT! ESP32 tidak respond dalam {PAUSE_TIMEOUT}s. Resume camera.")
        esp32_busy = False
        camera_paused = False
        return
    
    # Cek response dari ESP32 (jika ada serial response)
    try:
        if ser.in_waiting > 0:
            response = ser.readline().decode().strip()
            if "selesai" in response.lower() or "ready" in response.lower():
                print(f"✅ ESP32 selesai! Response: {response}")
                esp32_busy = False
                camera_paused = False
                print(f"▶️  Kamera RESUME")
    except Exception as e:
        print(f"⚠️  Error checking ESP32: {e}")

# ==========================================
# 3. MAIN LOOP DETEKSI (MODIFIKASI YANG ADA)
# ==========================================
track_state = {}
class_counters = {cls: 0 for cls in target_classes} 

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720) 

print(f"Memulai deteksi... Objek wajib berada di frame selama {VALIDATION_DURATION} detik untuk divalidasi.")
print("Tekan 'q' pada window video untuk keluar.")
print("=" * 60)

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    results = model.track(frame, persist=True, verbose=False, conf=0.5, iou=0.45)
    current_time = time.time()

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

            # --- JIKA VALIDASI SELESAI ---
            if elapsed_time >= VALIDATION_DURATION:
                
                if track_state[yolo_id]['custom_id'] is None:
                    class_counters[cls_name] += 1
                    track_state[yolo_id]['custom_id'] = class_counters[cls_name]
                
                current_class_id = track_state[yolo_id]['custom_id']

                # CROP & SAVE
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
                        print("-" * 60)
                        
                        # 🔴 KIRIM PERINTAH KE ESP32
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
        break

cap.release()
cv2.destroyAllWindows()

if ser and ser.is_open:
    ser.close()
    print("Serial connection closed")