"""
record_fresh.py — Record a fresh-session validation dataset.

The script generates a RANDOMIZED list of trials (N per class),
tells you which movement to perform, counts down, records, and saves
into newdata/. No need to restart between classes.

Usage:
    py record_fresh.py              # default 5 trials per class
    py record_fresh.py --trials 3   # 3 trials per class
"""
import serial, serial.tools.list_ports, time, csv, os, random, argparse

# ---------- config ----------
DURATION  = 5       # seconds per trial
NUM_COLS  = 19      # 1 time + 3 sensors x 6
BAUD      = 115200
OUT_DIR   = "newdata"
HEADER    = ["time_ms"] + [f"S{i}_{c}" for i in range(3)
             for c in ["ax","ay","az","gx","gy","gz"]]

CLASSES = [
    ("still",      "Hold flat, NO movement"),
    ("heelstrike", "Toe up, heel lands, flatten"),
    ("toeoff",     "Roll onto toe, heel up, lower"),
    ("slowstep",   "Step at ~30 BPM (slow)"),
    ("faststep",   "Step at ~60-75 BPM (fast)"),
    ("rollleft",   "Lift left edge, lower"),
    ("rollright",  "Lift right edge, lower"),
    ("twist",      "Rotate left and right on table"),
]

# ---------- args ----------
parser = argparse.ArgumentParser()
parser.add_argument("--trials", type=int, default=5, help="Trials per class")
args = parser.parse_args()

# ---------- build randomized trial list ----------
trials = []
for label, desc in CLASSES:
    for i in range(args.trials):
        trials.append((label, desc, i + 1))
random.shuffle(trials)

print(f"\n=== FRESH-SESSION RECORDING ===")
print(f"Classes: {len(CLASSES)}, Trials per class: {args.trials}")
print(f"Total trials: {len(trials)} (randomized order)")
print(f"Output: {OUT_DIR}/\n")

# ---------- port ----------
def find_port():
    for p in serial.tools.list_ports.comports():
        d = (p.description or "").upper()
        if any(k in d for k in ("CP210", "CH340", "CH910", "USB-SERIAL", "USB SERIAL")):
            return p.device
    return None

PORT = find_port() or input("COM port (e.g. COM15): ").strip()
print("Using", PORT)
ser = serial.Serial(PORT, BAUD, timeout=1)
print("Waiting for ESP32 calibration - keep slipper flat and still.")
print("(If nothing appears after 10 s, press the EN button.)")
while True:
    line = ser.readline().decode(errors="ignore").strip()
    if line: print(f"  ESP32: {line}")
    if line.startswith("time_ms"): break
print("Ready!\n")

# ---------- beep ----------
try:
    import winsound
    def beep(f, ms): winsound.Beep(f, ms)
except ImportError:
    def beep(f, ms): pass

# ---------- create output dir ----------
os.makedirs(OUT_DIR, exist_ok=True)

# ---------- figure out next file number per class ----------
def next_number(label):
    existing = [int(f.split("_")[1].split(".")[0])
                for f in os.listdir(OUT_DIR) if f.startswith(label + "_")]
    return max(existing, default=0) + 1

counters = {label: next_number(label) for label, _, _ in trials}

# ---------- record loop ----------
done = 0
for label, desc, trial_of_class in trials:
    remaining = len(trials) - done
    print("=" * 55)
    print(f"  Trial {done + 1}/{len(trials)}  |  {remaining} remaining")
    print(f"  Movement:  {label.upper()}")
    print(f"  How:       {desc}")
    print("=" * 55)
    cmd = input("  Press Enter to record (s = skip, q = quit): ").strip().lower()
    if cmd == "q":
        print("Quitting early.")
        break
    if cmd == "s":
        print("  Skipped.\n")
        done += 1
        continue

    # Countdown
    for k in (3, 2, 1):
        print(f"  {k}...", end=" ", flush=True)
        time.sleep(1)

    ser.reset_input_buffer()
    beep(1200, 300)
    print("GO!")

    rows, start = [], time.time()
    while time.time() - start < DURATION:
        parts = ser.readline().decode(errors="ignore").strip().split(",")
        if len(parts) == NUM_COLS and parts[0].isdigit():
            rows.append(parts)
    beep(600, 300)

    n = counters[label]
    counters[label] = n + 1
    fname = os.path.join(OUT_DIR, f"{label}_{n:02d}.csv")
    with open(fname, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(rows)

    status = "OK" if len(rows) >= 200 else "TOO FEW ROWS - redo!"
    print(f"  Saved {fname}: {len(rows)} rows  [{status}]\n")
    done += 1

# ---------- summary ----------
print(f"\n=== DONE: {done}/{len(trials)} trials recorded ===")
print(f"Files saved in: {OUT_DIR}/")
print(f"\nNext step: run  py predict_test.py  to evaluate the model.")
