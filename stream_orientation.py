"""
stream_orientation.py — Stream slipper orientation + step detection to Unity.

No ML model needed — uses raw IMU data only.
Tilt the slipper to control movement in Unity!

Usage:
    py stream_orientation.py              # auto-detect port
    py stream_orientation.py COM15        # specify port
"""
import sys, time, math, socket
import serial, serial.tools.list_ports

# ---------- config ----------
BAUD       = 115200
NUM_COLS   = 19

# Unity UDP
UNITY_IP   = "127.0.0.1"
UNITY_PORT = 5065

# Complementary filter
ALPHA = 0.96           # gyro trust (0.96 = 96% gyro, 4% accel correction)

# Sign tuning — if an axis moves the WRONG WAY in Unity, flip its sign to -1
SIGN_FWD_TILT  =  1    # forward/backward tilt (toe up/down)
SIGN_SIDE_TILT =  1    # left/right tilt
SIGN_TWIST     =  1    # yaw twist

# Step detection (accelerometer spike — no ML needed!)
STEP_THRESHOLD = 1.8   # g — acceleration above this = step detected
STEP_COOLDOWN  = 0.3   # seconds between step detections

# ---------- find port ----------
def find_port():
    for p in serial.tools.list_ports.comports():
        d = (p.description or "").upper()
        if any(k in d for k in ("CP210", "CH340", "CH910", "USB-SERIAL", "USB SERIAL")):
            return p.device
    return None

port = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else find_port()
if not port:
    port = input("COM port (e.g. COM15): ").strip()

# ---------- UDP socket ----------
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
print(f"UDP: sending to {UNITY_IP}:{UNITY_PORT}")

# ---------- connect to ESP32 ----------
ser = serial.Serial(port, BAUD, timeout=1)
print(f"Connected to {port} at {BAUD} baud")
print("Waiting for ESP32 calibration - keep slipper flat and still...")

while True:
    line = ser.readline().decode(errors="ignore").strip()
    if line:
        print(f"  ESP32: {line}")
    if line.startswith("time_ms"):
        break

print(f"\n=== STREAMING TO UNITY (Game Mode) ===")
print(f"Tilt slipper forward to move!")
print(f"Tilt left/right to steer!")
print(f"Stomp for speed boost!")
print(f"Ctrl+C to stop\n")

# ---------- orientation state ----------
# IMU axes: X = side-to-side, Y = heel-to-toe, Z = up
pitch = 0.0   # rotation around Y axis (left/right tilt)
roll  = 0.0   # rotation around X axis (forward/backward tilt)
yaw   = 0.0   # rotation around Z axis (twist)
last_time_ms = None

# Step detection state
last_step_time = 0.0

def compute_accel_angles(ax, ay, az):
    """Compute tilt angles from accelerometer (gravity direction).

    Returns (pitch, roll) where:
      pitch = rotation around Y axis = atan2(-ax, sqrt(ay^2+az^2))
      roll  = rotation around X axis = atan2(ay, az)
    """
    roll  = math.atan2(ay, az)                              # around X axis
    pitch = math.atan2(-ax, math.sqrt(ay*ay + az*az))       # around Y axis
    return math.degrees(pitch), math.degrees(roll)

try:
    while True:
        raw = ser.readline().decode(errors="ignore").strip()
        if not raw or raw.startswith("#"):
            continue
        parts = raw.split(",")
        if len(parts) != NUM_COLS or not parts[0].isdigit():
            continue

        vals = [float(v) for v in parts]
        time_ms = vals[0]

        # S0 sensor data (indices 1-6)
        ax, ay, az = vals[1], vals[2], vals[3]
        gx, gy, gz = vals[4], vals[5], vals[6]

        # Compute dt
        if last_time_ms is not None:
            dt = (time_ms - last_time_ms) / 1000.0
            if dt <= 0 or dt > 0.5:
                dt = 0.02  # default to 50 Hz
        else:
            dt = 0.02
        last_time_ms = time_ms

        # Accelerometer-based angles
        accel_pitch, accel_roll = compute_accel_angles(ax, ay, az)

        # Complementary filter (correct gyro pairing):
        #   pitch (around Y) ← gy + accel_pitch
        #   roll  (around X) ← gx + accel_roll
        pitch = ALPHA * (pitch + gy * dt) + (1 - ALPHA) * accel_pitch
        roll  = ALPHA * (roll  + gx * dt) + (1 - ALPHA) * accel_roll
        yaw   = yaw + gz * dt  # gyro only (no accel reference for yaw)

        # Clamp yaw drift (reset slowly toward 0 when stationary)
        if abs(gz) < 5.0:
            yaw *= 0.995  # slow drift correction

        # --- Step detection (simple accelerometer spike) ---
        accel_mag = math.sqrt(ax*ax + ay*ay + az*az)
        step = 0
        now = time.time()
        if accel_mag > STEP_THRESHOLD and (now - last_step_time) > STEP_COOLDOWN:
            step = 1
            last_step_time = now

        # Angular velocity magnitude
        ang_vel = math.sqrt(gx*gx + gy*gy + gz*gz)

        # --- Map IMU axes → Unity axes ---
        # IMU: Y=forward, Z=up → Unity: Z=forward, Y=up
        # Unity Euler(x,y,z): x=forward tilt, y=yaw, z=side tilt
        unity_pitch = roll  * SIGN_FWD_TILT    # IMU X-rot → Unity Euler.x
        unity_roll  = pitch * SIGN_SIDE_TILT   # IMU Y-rot → Unity Euler.z
        unity_yaw   = yaw   * SIGN_TWIST       # IMU Z-rot → Unity Euler.y

        # Format: "pitch,roll,yaw,step,angvel"
        msg = f"{unity_pitch:.2f},{unity_roll:.2f},{unity_yaw:.2f},{step},{ang_vel:.1f}"
        sock.sendto(msg.encode(), (UNITY_IP, UNITY_PORT))

        # Print every ~0.5 seconds
        if int(time_ms) % 500 < 25:
            t = time.strftime("%H:%M:%S")
            boost = " >>> STEP!" if step else ""
            print(f"  [{t}]  fwd={unity_pitch:+6.1f}  side={unity_roll:+6.1f}  twist={unity_yaw:+6.1f}  accel={accel_mag:.1f}g{boost}")

except KeyboardInterrupt:
    print("\nStopped.")
finally:
    ser.close()
    sock.close()
