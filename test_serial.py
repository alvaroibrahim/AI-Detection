import serial
import time

try:
    ser = serial.Serial("COM12", 115200, timeout=1)
    time.sleep(2)
    print("✓ Terhubung ke COM12!")
    
    # Read response
    if ser.in_waiting > 0:
        response = ser.readline().decode()
        print(f"Response: {response}")
    
    ser.close()
except Exception as e:
    print(f"✗ Error: {e}")
