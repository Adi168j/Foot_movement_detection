"""
Check if sensor S2 axes are flipped relative to S0/S1.

The lab_log.md notes that S2 is mounted upside-down with firmware sign corrections.
This script checks if the corrections are actually applied by comparing the
resting accelerometer values (gravity direction) across all 3 sensors.

If az is positive for all sensors at rest → firmware correction is working.
If S2_az is NEGATIVE at rest → axes are still flipped in the data.
"""
import glob, os
import pandas as pd
import numpy as np

DATA_DIR = "data"

print("=" * 70)
print("AXIS FLIP CHECK — Comparing resting values across S0, S1, S2")
print("=" * 70)

# Use 'still' trials for cleanest comparison
still_files = sorted(glob.glob(f"{DATA_DIR}/still_*.csv"))
if not still_files:
    print("No still_*.csv files found. Using all files instead.")
    still_files = sorted(glob.glob(f"{DATA_DIR}/*.csv"))

print(f"\nAnalyzing {len(still_files)} files...\n")

# Collect mean values per sensor across all still trials
results = []
for path in still_files:
    df = pd.read_csv(path)
    row = {"file": os.path.basename(path)}
    for s in range(3):
        for axis in ["ax", "ay", "az", "gx", "gy", "gz"]:
            col = f"S{s}_{axis}"
            row[col] = df[col].mean()
    results.append(row)

rdf = pd.DataFrame(results)

# --- Accelerometer check (gravity direction) ---
print("ACCELEROMETER MEANS (should see az ≈ +1.0g for all sensors if upright)")
print("-" * 70)
print(f"{'':12s}  {'S0_ax':>7s} {'S0_ay':>7s} {'S0_az':>7s}  |  {'S1_ax':>7s} {'S1_ay':>7s} {'S1_az':>7s}  |  {'S2_ax':>7s} {'S2_ay':>7s} {'S2_az':>7s}")
print("-" * 70)

for s in range(3):
    ax_mean = rdf[f"S{s}_ax"].mean()
    ay_mean = rdf[f"S{s}_ay"].mean()
    az_mean = rdf[f"S{s}_az"].mean()

avg_row = "  AVERAGE:  "
for s in range(3):
    ax_m = rdf[f"S{s}_ax"].mean()
    ay_m = rdf[f"S{s}_ay"].mean()
    az_m = rdf[f"S{s}_az"].mean()
    avg_row += f"  {ax_m:+7.3f} {ay_m:+7.3f} {az_m:+7.3f}  |"
print(avg_row)

print()

# --- Check for flipped axes ---
print("DIAGNOSIS:")
print("-" * 70)

for s in range(3):
    az_mean = rdf[f"S{s}_az"].mean()
    ax_mean = rdf[f"S{s}_ax"].mean()
    ay_mean = rdf[f"S{s}_ay"].mean()
    
    gravity_mag = np.sqrt(ax_mean**2 + ay_mean**2 + az_mean**2)
    
    if az_mean > 0.8:
        status = "OK — az positive, sensor is right-side-up (or firmware-corrected)"
    elif az_mean < -0.8:
        status = "FLIPPED! — az is NEGATIVE, sensor axes are upside-down in data!"
    else:
        status = f"UNUSUAL — az={az_mean:.3f}, gravity not clearly on Z axis"
    
    print(f"  S{s}: az_mean = {az_mean:+.3f}g  (gravity magnitude = {gravity_mag:.3f}g)  →  {status}")

print()

# --- Gyroscope check (should be near zero at rest) ---
print("GYROSCOPE MEANS (should be near 0 for all sensors at rest)")
print("-" * 70)
for s in range(3):
    gx_m = rdf[f"S{s}_gx"].mean()
    gy_m = rdf[f"S{s}_gy"].mean()
    gz_m = rdf[f"S{s}_gz"].mean()
    gyro_offset = np.sqrt(gx_m**2 + gy_m**2 + gz_m**2)
    status = "OK" if gyro_offset < 3.0 else f"OFFSET ({gyro_offset:.1f} deg/s drift)"
    print(f"  S{s}: gx={gx_m:+6.2f}  gy={gy_m:+6.2f}  gz={gz_m:+6.2f}  →  {status}")

print()

# --- Cross-sensor correlation on a movement trial ---
print("CROSS-SENSOR CORRELATION CHECK (using heelstrike data)")
print("-" * 70)
hs_files = sorted(glob.glob(f"{DATA_DIR}/heelstrike_*.csv"))
if hs_files:
    df = pd.read_csv(hs_files[0])
    print(f"  File: {os.path.basename(hs_files[0])}")
    print()
    
    for axis in ["az", "gx"]:
        s0 = df[f"S0_{axis}"].values
        s1 = df[f"S1_{axis}"].values
        s2 = df[f"S2_{axis}"].values
        
        corr_01 = np.corrcoef(s0, s1)[0, 1]
        corr_02 = np.corrcoef(s0, s2)[0, 1]
        corr_12 = np.corrcoef(s1, s2)[0, 1]
        
        print(f"  {axis}: S0↔S1 corr={corr_01:+.3f}  S0↔S2 corr={corr_02:+.3f}  S1↔S2 corr={corr_12:+.3f}")
        
        # If S2 is flipped, its correlation with S0/S1 would be NEGATIVE
        if corr_02 < -0.3:
            print(f"       ⚠️  S0↔S2 is NEGATIVELY correlated for {axis} — S2 {axis} axis may be FLIPPED!")
        if corr_12 < -0.3:
            print(f"       ⚠️  S1↔S2 is NEGATIVELY correlated for {axis} — S2 {axis} axis may be FLIPPED!")
    
    print()

print("=" * 70)
print("SUMMARY:")
print("  - If all sensors show az ≈ +1.0g → firmware sign correction is working")
print("  - If S2 shows az ≈ -1.0g → S2 axes are FLIPPED in recorded data")
print("  - Negative cross-sensor correlations → that specific axis is inverted")
print("=" * 70)
