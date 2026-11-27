"""
predict_live.py — Real-time movement detection from ESP32 serial.

Two modes:
  DEFAULT:      Event-based — waits for movement, classifies it, shows result
  --continuous: Sliding-window — predicts every second (old behavior)
  --test:       Run on newdata/ files

Unity integration:
  --unity       Also sends predictions via UDP to localhost:5065 for Unity

Usage:
    py predict_live.py                  # event-based, auto-detect port
    py predict_live.py --continuous     # old sliding-window mode
    py predict_live.py --unity          # event-based + send to Unity
    py predict_live.py --test           # test on newdata/ files
    py predict_live.py COM15            # specify port
"""
import sys, time, collections, joblib, numpy as np, pandas as pd
from features import extract_features

# ---------- config ----------
BAUD         = 115200
MODEL_PATH   = "foot_model.joblib"
NUM_COLS     = 19
HEADER = ["time_ms"] + [f"S{i}_{c}" for i in range(3)
          for c in ["ax","ay","az","gx","gy","gz"]]

# Event mode config
GYRO_THRESHOLD   = 25.0    # deg/s — above this = "moving"
QUIET_DURATION   = 0.5     # seconds of low activity to trigger classification
MIN_ACTIVE_ROWS  = 30      # need at least this many active rows (0.6s)
MAX_BUFFER       = 300     # cap buffer at 6 seconds

# Continuous mode config
WINDOW_ROWS  = 150     # 3 seconds at 50 Hz
STEP_ROWS    = 50      # predict every 1 second

CONFIDENCE_THRESHOLD = 0.50

# ---------- load model ----------
bundle  = joblib.load(MODEL_PATH)
model   = bundle["model"]
columns = bundle["columns"]
print(f"Model loaded ({len(columns)} features)")

# ---------- parse args ----------
args = sys.argv[1:]
CONTINUOUS = "--continuous" in args
UNITY      = "--unity" in args
TEST_MODE  = "--test" in args

port_arg = None
for arg in args:
    if not arg.startswith("--"):
        port_arg = arg
        break

def align_and_predict(feats):
    """Align features to training columns and predict with confidence."""
    X = pd.DataFrame([feats])
    for c in columns:
        if c not in X.columns:
            X[c] = 0.0
    X = X[columns]
    try:
        proba = model.predict_proba(X)[0]
        best_idx = proba.argmax()
        label = model.classes_[best_idx]
        conf = proba[best_idx]
    except AttributeError:
        label = model.predict(X)[0]
        conf = 1.0
    return label, conf

def gyro_magnitude(row):
    """Compute total gyro magnitude from a parsed row."""
    # row indices: gx=4,gy=5,gz=6 for S0; 10,11,12 for S1; 16,17,18 for S2
    gx, gy, gz = row[4], row[5], row[6]  # S0 gyro
    return np.sqrt(gx**2 + gy**2 + gz**2)


# ============================================================
# UDP sender for Unity
# ============================================================
udp_sock = None
if UNITY:
    import socket
    UNITY_IP   = "127.0.0.1"
    UNITY_PORT = 5065
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(f"Unity UDP: sending to {UNITY_IP}:{UNITY_PORT}")

def send_to_unity(label, confidence):
    """Send prediction to Unity via UDP as 'label,confidence'."""
    if udp_sock:
        msg = f"{label},{confidence:.2f}"
        udp_sock.sendto(msg.encode(), (UNITY_IP, UNITY_PORT))


# ============================================================
# TEST MODE
# ============================================================
if TEST_MODE:
    import glob, os
    NEWDATA_DIR = "newdata"
    paths = sorted(glob.glob(f"{NEWDATA_DIR}/*.csv"))
    if not paths:
        print(f"No CSV files in {NEWDATA_DIR}/")
        sys.exit(1)

    print(f"\n=== WINDOWED PREDICTION TEST on {NEWDATA_DIR}/ ===")
    print(f"Window: {WINDOW_ROWS} rows ({WINDOW_ROWS/50:.1f}s)\n")

    for p in paths:
        df = pd.read_csv(p)
        name = os.path.basename(p)
        true_label = name.split("_")[0]

        if len(df) < WINDOW_ROWS:
            print(f"  {name:28s}  SKIP (only {len(df)} rows)")
            continue

        preds = []
        for start in range(0, len(df) - WINDOW_ROWS + 1, STEP_ROWS):
            window = df.iloc[start:start + WINDOW_ROWS].reset_index(drop=True)
            feats = extract_features(window)
            pred, conf = align_and_predict(feats)
            if conf >= CONFIDENCE_THRESHOLD:
                preds.append(pred)

        from collections import Counter
        vote = Counter(preds).most_common(1)[0][0] if preds else "?"
        match = "Y" if vote == true_label else "X"
        detail = ", ".join(preds)
        print(f"  {name:28s}  true={true_label:12s}  vote={vote:12s}  [{match}]  windows: {detail}")
    sys.exit(0)


# ============================================================
# SERIAL CONNECTION
# ============================================================
import serial, serial.tools.list_ports

def find_port():
    for p in serial.tools.list_ports.comports():
        d = (p.description or "").upper()
        if any(k in d for k in ("CP210", "CH340", "CH910", "USB-SERIAL", "USB SERIAL")):
            return p.device
    return None

port = port_arg or find_port()
if not port:
    port = input("COM port (e.g. COM15): ").strip()

ser = serial.Serial(port, BAUD, timeout=1)
print(f"Connected to {port} at {BAUD} baud")
print("Waiting for ESP32 calibration - keep slipper flat and still...")

while True:
    line = ser.readline().decode(errors="ignore").strip()
    if line:
        print(f"  ESP32: {line}")
    if line.startswith("time_ms"):
        break

def parse_row(raw):
    """Parse a serial line into float values. Returns None if invalid."""
    parts = raw.split(",")
    if len(parts) != NUM_COLS or not parts[0].isdigit():
        return None
    return [float(v) for v in parts]


# ============================================================
# EVENT-BASED MODE (default)
# ============================================================
if not CONTINUOUS:
    print(f"\n=== EVENT-BASED PREDICTION ===")
    print(f"Gyro threshold: {GYRO_THRESHOLD} deg/s")
    print(f"Do a movement, then hold still. I'll classify it.")
    print(f"Ctrl+C to stop\n")

    state = "IDLE"  # IDLE -> MOVING -> CLASSIFYING
    active_buffer = []
    quiet_start = None
    last_label = ""

    try:
        while True:
            raw = ser.readline().decode(errors="ignore").strip()
            if not raw or raw.startswith("#"):
                continue
            row = parse_row(raw)
            if row is None:
                continue

            gmag = gyro_magnitude(row)

            if state == "IDLE":
                if gmag > GYRO_THRESHOLD:
                    state = "MOVING"
                    active_buffer = [row]
                    quiet_start = None
                    print("  ... movement detected, recording...", end="", flush=True)

            elif state == "MOVING":
                active_buffer.append(row)

                # Cap buffer size
                if len(active_buffer) > MAX_BUFFER:
                    active_buffer = active_buffer[-MAX_BUFFER:]

                if gmag > GYRO_THRESHOLD:
                    quiet_start = None
                else:
                    if quiet_start is None:
                        quiet_start = time.time()
                    elif time.time() - quiet_start >= QUIET_DURATION:
                        # Movement ended — classify
                        state = "CLASSIFYING"

            if state == "CLASSIFYING":
                if len(active_buffer) >= MIN_ACTIVE_ROWS:
                    df = pd.DataFrame(active_buffer, columns=HEADER)
                    feats = extract_features(df)
                    label, conf = align_and_predict(feats)

                    t = time.strftime("%H:%M:%S")
                    marker = " << CHANGED" if label != last_label and last_label else ""
                    print(f"\r  [{t}]  >>> {label.upper():12s}  ({conf:.0%} confidence, {len(active_buffer)} samples){marker}")
                    last_label = label
                    send_to_unity(label, conf)
                else:
                    print(f"\r  ... too brief ({len(active_buffer)} samples), ignored")

                active_buffer = []
                quiet_start = None
                state = "IDLE"

    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        ser.close()
    sys.exit(0)


# ============================================================
# CONTINUOUS MODE (--continuous)
# ============================================================
print(f"\n=== CONTINUOUS PREDICTION ===")
print(f"Window: {WINDOW_ROWS} rows ({WINDOW_ROWS/50:.1f}s), predict every {STEP_ROWS/50:.1f}s")
print(f"Ctrl+C to stop\n")

buffer = collections.deque(maxlen=WINDOW_ROWS)
rows_since_predict = 0
last_label = ""
vote_history = collections.deque(maxlen=3)

try:
    while True:
        raw = ser.readline().decode(errors="ignore").strip()
        if not raw or raw.startswith("#"):
            continue
        row = parse_row(raw)
        if row is None:
            continue

        buffer.append(row)
        rows_since_predict += 1

        if len(buffer) >= WINDOW_ROWS and rows_since_predict >= STEP_ROWS:
            rows_since_predict = 0
            df = pd.DataFrame(list(buffer), columns=HEADER)
            feats = extract_features(df)
            pred, conf = align_and_predict(feats)

            if conf < CONFIDENCE_THRESHOLD:
                t = time.strftime("%H:%M:%S")
                print(f"  [{t}]  {'...':12s}  (raw: {pred} {conf:.0%})")
                continue

            vote_history.append(pred)
            from collections import Counter
            smoothed = Counter(vote_history).most_common(1)[0][0]

            marker = " << CHANGED" if smoothed != last_label and last_label else ""
            t = time.strftime("%H:%M:%S")
            print(f"  [{t}]  {smoothed:12s}  (raw: {pred} {conf:.0%}){marker}")
            last_label = smoothed
            send_to_unity(smoothed, conf)

except KeyboardInterrupt:
    print("\nStopped.")
finally:
    ser.close()
