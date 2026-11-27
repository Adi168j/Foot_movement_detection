"""
reject.py — Scan data/*.csv for bad trials and move them to rejected/.
Criteria: fewer than 200 rows OR time gap > 100 ms.
"""
import glob, os, shutil, pandas as pd

DATA_DIR   = "data"
REJECT_DIR = "rejected"
MIN_ROWS   = 200
MAX_GAP_MS = 100

os.makedirs(REJECT_DIR, exist_ok=True)

kept, moved = 0, 0
for f in sorted(glob.glob(f"{DATA_DIR}/*.csv")):
    name = os.path.basename(f)
    try:
        d = pd.read_csv(f)
    except Exception as e:
        print(f"  UNREADABLE  {name}: {e}")
        shutil.move(f, os.path.join(REJECT_DIR, name))
        moved += 1
        continue

    problems = []
    if len(d) < MIN_ROWS:
        problems.append(f"only {len(d)} rows (need {MIN_ROWS})")
    if len(d) >= 2:
        gap = d["time_ms"].diff().max()
        if gap > MAX_GAP_MS:
            idx = d["time_ms"].diff().idxmax()
            at_sec = (d["time_ms"].iloc[idx] - d["time_ms"].iloc[0]) / 1000
            problems.append(f"gap {gap:.0f} ms at {at_sec:.1f}s")

    if problems:
        print(f"  REJECTED    {name:24s} — {', '.join(problems)}")
        shutil.move(f, os.path.join(REJECT_DIR, name))
        moved += 1
    else:
        rows = len(d)
        gap = d["time_ms"].diff().max() if len(d) >= 2 else 0
        print(f"  OK          {name:24s}   rows={rows:4d}  max_gap={gap:3.0f} ms")
        kept += 1

print(f"\nDone. Kept {kept}, rejected {moved} -> ./{REJECT_DIR}/")
if moved > 0:
    print("Re-run train.py to retrain without rejected files.")