import glob, os, numpy as np, pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score
from features import extract_features

MIN_ROWS = 200

paths = sorted(glob.glob("data/*.csv"))
dfs, labels = [], []
for p in paths:
    d = pd.read_csv(p)
    if len(d) < MIN_ROWS:
        print(f"  SKIP {os.path.basename(p)} ({len(d)} rows)")
        continue
    dfs.append(d)
    labels.append(os.path.basename(p).split("_")[0])
y = np.array(labels)
print(f"Loaded {len(y)} trials (skipped {len(paths) - len(y)} short files)\n")

cv = StratifiedKFold(5, shuffle=True, random_state=0)
def score(X, y):
    return cross_val_score(RandomForestClassifier(300, random_state=0), X, y, cv=cv).mean()

X = pd.DataFrame([extract_features(d) for d in dfs])

# Test 1: shuffled labels (should collapse to about chance)
print("1. Shuffled labels:", round(score(X, np.random.default_rng(0).permutation(y)), 2))

# Test 2: how many sensors are needed
for s in [(0,), (1,), (2,), (0, 1), (0, 2), (1, 2), (0, 1, 2)]:
    Xs = pd.DataFrame([extract_features(d, sensors=s) for d in dfs])
    print("2. Sensors", s, round(score(Xs, y), 2))

# Test 3: remove resting-tilt features (grip/posture clues)
keep = [c for c in X.columns if not (c.endswith("_mean") and c.split("_")[1] in ("ax", "ay", "az"))]
print("3. Without resting tilt:", round(score(X[keep], y), 2))

# Test 4: which features does the model rely on?
rf = RandomForestClassifier(300, random_state=0).fit(X, y)
top = pd.Series(rf.feature_importances_, X.columns).sort_values(ascending=False).head(10)
print("4. Top features:\n", top.round(3))

# Test 5: gyro and timing only (drop ALL accelerometer features)
gyro_timing = [c for c in X.columns if not any(c.startswith(f"S{s}_a") for s in range(3))]
print(f"\n5. Gyro + timing only ({len(gyro_timing)} features):", round(score(X[gyro_timing], y), 2))