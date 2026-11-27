import glob, os, numpy as np, pandas as pd, matplotlib.pyplot as plt

examples = {}
for f in sorted(glob.glob("data/*.csv")):
    df = pd.read_csv(f); name = os.path.basename(f); problems = []
    if len(df) < 200: problems.append("few rows")
    if df.drop(columns="time_ms").duplicated().mean() > 0.2: problems.append("frozen values")
    if df["time_ms"].diff().max() > 100: problems.append("time gap")
    print(f"{name:22s} rows={len(df):4d}", ("  <-- " + ", ".join(problems)) if problems else "")
    examples.setdefault(name.split("_")[0], df)

fig, axes = plt.subplots(len(examples), 1, figsize=(9, 3 * len(examples)), squeeze=False)
for ax, (label, df) in zip(axes[:, 0], examples.items()):
    for s in range(3):
        g = np.sqrt(df[f"S{s}_gx"]**2 + df[f"S{s}_gy"]**2 + df[f"S{s}_gz"]**2)
        ax.plot((df.time_ms - df.time_ms.iloc[0]) / 1000, g, label=f"S{s}")
    ax.set_title(label); ax.set_ylabel("gyro magnitude"); ax.legend()
plt.tight_layout(); plt.show()