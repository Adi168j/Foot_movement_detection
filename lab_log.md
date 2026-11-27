# Lab Log — Foot Movement Detection

## Hardware Configuration

| Component | Detail |
|-----------|--------|
| MCU | ESP32 DevKit (ESP32-D0WD-V3), USB-C |
| Multiplexer | PCA9548A at 0x70, SDA=GPIO21, SCL=GPIO22 |
| Sensors | 3× MPU6050 (GY-521/HW-123), each at 0x68 |
| I2C speed | 100 kHz |
| Serial baud | 115200 |
| Sample rate | 50 Hz |
| Power | All from ESP32 3V3 rail |

## Sensor-to-Channel Mapping

| Mux Channel | Label | Physical Position | Notes |
|-------------|-------|-------------------|-------|
| 0 (S0) | | _TODO: write position_ | |
| 1 (S1) | | _TODO: write position_ | |
| 2 (S2) | | _TODO: write position_ | Mounted upside-down (header soldered on chip side) |

## Sign Correction Table (firmware)

The upside-down sensor has its signs flipped in firmware:

| Sensor | ax | ay | az | gx | gy | gz |
|--------|----|----|----|----|----|----|
| Normal | +1 | +1 | +1 | +1 | +1 | +1 |
| Flipped (S?) | -1 | +1 | -1 | -1 | +1 | -1 |

_TODO: confirm which sensor index is flipped_

## Axis Conventions

- **Y axis (S0):** Confirmed as heel-to-toe direction
- **S1, S2:** _TODO: confirm heel-to-toe axis_
- Gravity on still sensor: az ≈ +1.0 g (total 1.04–1.15 g)

---

## Session Log

### Session 1 — 24 Oct 2026
- **Operator:** _TODO_
- **Slipper worn on foot:** No (hand-moved)
- **Calibration:** Gyro only (accel calibration disabled — wrong offsets)
- **Classes recorded:** still, heelstrike, toeoff, step, slowstep, faststep, rollleft, rollright, twist
- **Total trials:** 93
- **Notes:** Data collected in blocks by label (not randomized). Connection dropouts on some trials.

### Session 2 — _TODO: date_
- **Purpose:** Fresh-session validation (mixed-order recording)
- **Slipper removed and reattached:** Yes / No
- **Classes recorded:** _TODO_
- **Total trials:** _TODO_
- **Notes:** _TODO_

---

## Rejected Files

| Filename | Reason | Date |
|----------|--------|------|
| _Run reject.py to populate_ | | |

---

## Model Versions

| Date | Script | Classes | Trials | CV Accuracy | Notes |
|------|--------|---------|--------|-------------|-------|
| 24 Oct 2026 | train.py | 9 | 93 | ~1.00 | Random Forest, no gap rejection yet |
| _TODO_ | | | | | After gap rejection |
| _TODO_ | | | | | Fresh-session test |
