import glob, os, pandas as pd
rows = {}
for f in glob.glob("data/*.csv"):
    d = pd.read_csv(f); lab = os.path.basename(f).split("_")[0]
    rows.setdefault(lab, []).append(d[[f"S0_{a}" for a in ["ax","ay","az","gx","gy","gz"]]].std())
print(pd.DataFrame({k: pd.concat(v, axis=1).mean(axis=1) for k, v in rows.items()}).round(2))