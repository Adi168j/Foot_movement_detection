import glob, os, joblib, numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import StratifiedKFold, cross_val_score, cross_val_predict
from sklearn.metrics import ConfusionMatrixDisplay, classification_report
from features import extract_features

MIN_ROWS = 200
rows, y = [], []
for path in sorted(glob.glob("data/*.csv")):
    df = pd.read_csv(path)
    if len(df) < MIN_ROWS:
        print(f"  SKIP {os.path.basename(path)} ({len(df)} rows)")
        continue
    rows.append(extract_features(df))
    y.append(os.path.basename(path).split("_")[0])
X, y = pd.DataFrame(rows), np.array(y)
print("Trials:", len(y), dict(zip(*np.unique(y, return_counts=True))))

models = {
    "LogReg": make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)),
    "SVM": make_pipeline(StandardScaler(), SVC(kernel="rbf", C=10)),
    "RandomForest": RandomForestClassifier(n_estimators=300, random_state=0),
}
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
best_name, best_score = None, -1
for name, m in models.items():
    s = cross_val_score(m, X, y, cv=cv)
    print(f"{name:13s} accuracy {s.mean():.2f} +/- {s.std():.2f}")
    if s.mean() > best_score: best_name, best_score = name, s.mean()
print("Best:", best_name)

best = models[best_name]
pred = cross_val_predict(best, X, y, cv=cv)
print(classification_report(y, pred))
ConfusionMatrixDisplay.from_predictions(y, pred, xticks_rotation=45)
plt.tight_layout(); plt.savefig("confusion.png")
print("Saved confusion.png")

best.fit(X, y)
joblib.dump({"model": best, "columns": list(X.columns)}, "foot_model.joblib")
print("Saved foot_model.joblib")