import serial, serial.tools.list_ports, time, csv, os

DURATION = 5          # seconds per trial
NUM_COLS = 19         # 1 time + 3 sensors x 6
HEADER = ["time_ms"] + [f"S{i}_{c}" for i in range(3) for c in ["ax","ay","az","gx","gy","gz"]]

def find_port():
    for p in serial.tools.list_ports.comports():
        d = (p.description or "").upper()
        if any(k in d for k in ("CP210", "CH340", "CH910", "USB-SERIAL", "USB SERIAL")):
            return p.device
    return None

try:
    import winsound
    def beep(f, ms): winsound.Beep(f, ms)
except ImportError:
    def beep(f, ms): pass

PORT = find_port() or input("COM port (e.g. COM15): ").strip()
print("Using", PORT)
ser = serial.Serial(PORT, 115200, timeout=1)
print("Waiting for ESP32 calibration - keep slipper flat and still.")
print("(If nothing appears after 10 s, press the EN button.)")
while True:
    line = ser.readline().decode(errors="ignore").strip()
    if line: print("  ESP32:", line)
    if line.startswith("time_ms"): break
print("Ready.\n")

label = input("Label (still/heelstrike/toeoff/step): ").strip().lower()
os.makedirs("data", exist_ok=True)
existing = [int(f.split("_")[1].split(".")[0]) for f in os.listdir("data") if f.startswith(label + "_")]
n = max(existing, default=0) + 1

while True:
    cmd = input(f"\nTrial {n} [{label}] - foot flat and still, press Enter (q = quit): ")
    if cmd.strip().lower() == "q": break
    for k in (3, 2, 1):
        print(k, end=" ", flush=True); time.sleep(1)
    ser.reset_input_buffer()
    beep(1200, 300); print("GO!")
    rows, start = [], time.time()
    while time.time() - start < DURATION:
        parts = ser.readline().decode(errors="ignore").strip().split(",")
        if len(parts) == NUM_COLS and parts[0].isdigit():
            rows.append(parts)
    beep(600, 300)
    fname = f"data/{label}_{n:02d}.csv"
    with open(fname, "w", newline="") as f:
        w = csv.writer(f); w.writerow(HEADER); w.writerows(rows)
    print(f"Saved {fname}: {len(rows)} rows" + ("" if len(rows) >= 200 else "  <-- TOO FEW, delete and redo"))
    n += 1