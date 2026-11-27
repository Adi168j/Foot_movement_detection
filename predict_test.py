"""
predict_test.py — Evaluate the saved model on fresh data in newdata/.
Prints per-trial predictions, accuracy, and a confusion matrix.
"""
import glob, os, joblib, numpy as np, pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import ConfusionMatrixDisplay, classification_report
from features import extract_features

NEWDATA_DIR = "newdata"
MODEL_PATH  = "foot_model.joblib"
MIN_ROWS    = 200

# ---------- load model ----------
if not os.path.exists(MODEL_PATH):
    print(f"ERROR: {MODEL_PATH} not found. Run train.py first.")
    exit(1)
bundle  = joblib.load(MODEL_PATH)
model   = bundle["model"]
columns = bundle["columns"]
print(f"Loaded model from {MODEL_PATH}  ({len(columns)} features)")

# ---------- load new data ----------
paths = sorted(glob.glob(f"{NEWDATA_DIR}/*.csv"))
if not paths:
    print(f"ERROR: No CSV files in {NEWDATA_DIR}/. Record fresh data first.")
    exit(1)

rows, y_true, names = [], [], []
skipped = 0
for p in paths:
    df = pd.read_csv(p)
    name = os.path.basename(p)
    if len(df) < MIN_ROWS:
        print(f"  SKIP  {name} — only {len(df)} rows")
        skipped += 1
        continue
    label = name.split("_")[0]
    # Map old class names to merged ones
    LABEL_MAP = {"faststep": "step", "slowstep": "step"}
    label = LABEL_MAP.get(label, label)
    feats = extract_features(df)
    rows.append(feats)
    y_true.append(label)
    names.append(name)

X_new = pd.DataFrame(rows)

# Align columns to training set (handles missing/extra sensors gracefully)
for c in columns:
    if c not in X_new.columns:
        X_new[c] = 0.0
X_new = X_new[columns]

y_true = np.array(y_true)

# ---------- predict ----------
y_pred = model.predict(X_new)

print(f"\n{'File':28s}  {'True':12s}  {'Predicted':12s}  Match")
print("-" * 68)
correct = 0
for name, yt, yp in zip(names, y_true, y_pred):
    ok = "✓" if yt == yp else "✗"
    if yt == yp:
        correct += 1
    print(f"{name:28s}  {yt:12s}  {yp:12s}  {ok}")

acc = correct / len(y_true) if y_true.size else 0
print(f"\nAccuracy: {correct}/{len(y_true)} = {acc:.2%}")
if skipped:
    print(f"({skipped} files skipped for too few rows)")

# ---------- report & confusion matrix ----------
print("\n" + classification_report(y_true, y_pred, zero_division=0))

ConfusionMatrixDisplay.from_predictions(y_true, y_pred, xticks_rotation=45)
plt.title("Fresh-Session Confusion Matrix")
plt.tight_layout()
plt.savefig("confusion_fresh.png")
print("Saved confusion_fresh.png")
plt.show()
