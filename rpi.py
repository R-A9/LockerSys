import os
import serial
import time
import evdev
import mysql.connector
from dotenv import load_dotenv
from evdev import InputDevice, categorize, ecodes

# === Load .env config ===
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

ARDUINO_PORT = "/dev/ttyUSB0"
BAUD_RATE = 9600
SCANNER_DEVICE = "/dev/input/by-id/usb-TMC_HIDKeyBoard_1234567890abcd-event-kbd"

# === MySQL connection ===
db = mysql.connector.connect(
    host=DB_HOST,
    user=DB_USER,
    password=DB_PASSWORD,
    database=DB_NAME
)
cursor = db.cursor()

# === Arduino serial ===
arduino = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
time.sleep(2)

# === Send command helper ===
def send_command(cmd):
    arduino.write((cmd + "\n").encode())
    print(f"✅ Sent to Arduino: {cmd}")

# === Locker commands ===
def locker_command(locker_num):
    if locker_num == 1:
        return "L1"
    elif locker_num == 2:
        return "L2"
    elif locker_num == 3:
        return "L3"
    elif locker_num == 0:   # special case: ALL locks
        return "ALL"
    return None

# === Log access ===
def log_access(owner_name, locker_num, sec_lvl, qr_code):
    cursor.execute("""
        INSERT INTO access_history (owner_name, locker_num, sec_lvl, qr_code)
        VALUES (%s, %s, %s, %s)
    """, (owner_name, locker_num, sec_lvl, qr_code))
    db.commit()
    print("📝 Access logged.")

# === QR cooldown tracking ===
last_qr_value = None
last_scan_time = 0
cooldown = 5  # seconds

# === Handle scanned QR ===
def process_qr(qr_value):
    global last_qr_value, last_scan_time
    qr_value = qr_value.strip()
    now = time.time()

    # Debounce: ignore duplicate QR within cooldown
    if qr_value == last_qr_value and (now - last_scan_time < cooldown):
        print(f"⏳ Ignored duplicate scan: {qr_value}")
        return

    last_qr_value = qr_value
    last_scan_time = now

    cursor.execute("SELECT locker_num, sec_lvl, owner_name FROM locker_access WHERE qr_code = %s", (qr_value,))
    result = cursor.fetchone()

    if not result:
        print(f"❌ Unknown QR: {qr_value}")
        return

    locker_num, sec_lvl, owner_name = result
    print(f"✅ QR Match: {owner_name} | Locker {locker_num} | Security: {sec_lvl}")

    if sec_lvl == "LOW":
        cmd = locker_command(locker_num)
        if cmd:
            send_command(cmd)
            log_access(owner_name, locker_num, sec_lvl, qr_value)

    elif sec_lvl == "HIGH":
        print("🔐 High security: waiting for user confirmation...")
        user_in = input("Enter CONFIRM to open: ").strip().upper()
        if user_in == "CONFIRM":
            cmd = locker_command(locker_num)
            if cmd:
                send_command(cmd)
                log_access(owner_name, locker_num, sec_lvl, qr_value)
        else:
            print("❌ User confirmation failed")

# === QR scanner listener ===
def listen_scanner():
    device = InputDevice(SCANNER_DEVICE)
    print(f"✅ Scanner ready: {device.name} at {SCANNER_DEVICE}")
    print("System ready. Scan a QR code...")

    qr_buffer = ""
    shift_pressed = False

    for event in device.read_loop():
        if event.type == ecodes.EV_KEY:
            key = categorize(event)

            if key.keycode == "KEY_LEFTSHIFT":
                shift_pressed = key.keystate == key.key_down
                continue

            if key.keystate == key.key_down:
                k = key.keycode.replace("KEY_", "")

                if k == "ENTER":
                    qr_value = qr_buffer.strip()
                    qr_buffer = ""

                    if qr_value:
                        process_qr(qr_value)

                else:
                    if len(k) == 1 and k.isalpha():
                        char = k.upper() if shift_pressed else k.lower()
                        qr_buffer += char
                    elif k.isdigit():
                        qr_buffer += k

# === MAIN ===
if __name__ == "__main__":
    try:
        listen_scanner()
    except KeyboardInterrupt:
        print("\n👋 Exiting system...")
        arduino.close()
        cursor.close()
        db.close()
