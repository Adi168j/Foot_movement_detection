import numpy as np

AXES = ["ax", "ay", "az", "gx", "gy", "gz"]

def extract_features(df, sensors=(0, 1, 2)):
    f, peaks = {}, {}
    for s in sensors:
        for a in AXES:
            x = df[f"S{s}_{a}"].values
            f[f"S{s}_{a}_mean"] = x.mean()
            f[f"S{s}_{a}_std"] = x.std()
            f[f"S{s}_{a}_min"] = x.min()
            f[f"S{s}_{a}_max"] = x.max()
        g = np.sqrt(df[f"S{s}_gx"]**2 + df[f"S{s}_gy"]**2 + df[f"S{s}_gz"]**2).values
        am = np.sqrt(df[f"S{s}_ax"]**2 + df[f"S{s}_ay"]**2 + df[f"S{s}_az"]**2).values
        f[f"S{s}_gmag_max"] = g.max()
        f[f"S{s}_gmag_mean"] = g.mean()
        f[f"S{s}_amag_std"] = am.std()
        peaks[s] = df["time_ms"].values[g.argmax()] / 1000.0
    for i in sensors:
        for j in sensors:
            if i < j:
                f[f"peak_gap_S{i}_S{j}"] = peaks[i] - peaks[j]
    return f