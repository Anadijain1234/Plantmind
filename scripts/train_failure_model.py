"""
Train Ustaad's failure-prediction model on the public Microsoft Azure Predictive Maintenance dataset
(100 machines, hourly telemetry for 2015, error logs, maintenance and failure records).

Question it answers: "Will this machine have a component failure in the next 24 hours?"
Features (per machine, per day at 06:00): last-24h mean/std of volt, rotation, pressure, vibration;
error counts in the last 24h; days since each component was last replaced; machine model and age.
Train on Jan-Aug 2015, test on Sep-Dec 2015 (time split, no peeking into the future).

Usage:  python scripts/train_failure_model.py <folder with PdM_*.csv>
Output: data/processed/factory_fleet.json (risk per machine on a demo day + model card)
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, roc_auc_score

src = Path(sys.argv[1])
out_path = Path(__file__).resolve().parent.parent / "data" / "processed" / "factory_fleet.json"
tel = pd.read_csv(src / "PdM_telemetry.csv", parse_dates=["datetime"])
err = pd.read_csv(src / "PdM_errors.csv", parse_dates=["datetime"])
mnt = pd.read_csv(src / "PdM_maint.csv", parse_dates=["datetime"])
fail = pd.read_csv(src / "PdM_failures.csv", parse_dates=["datetime"])
mac = pd.read_csv(src / "PdM_machines.csv")
SIG = ["volt", "rotate", "pressure", "vibration"]

# 24h rolling stats, sampled once a day at 06:00
tel = tel.sort_values(["machineID", "datetime"])
roll = (tel.set_index("datetime").groupby("machineID")[SIG].rolling("24h").agg(["mean", "std"]))
roll.columns = [f"{a}_{b}24" for a, b in roll.columns]
roll = roll.reset_index()
roll = roll[roll["datetime"].dt.hour == 6].copy()

# errors in the last 24h
err["n"] = 1
ep = err.pivot_table(index=["machineID", "datetime"], columns="errorID", values="n", aggfunc="sum", fill_value=0).reset_index()
feats = roll.copy()
for e in ["error1", "error2", "error3", "error4", "error5"]:
    feats[e] = 0
for mid, g in feats.groupby("machineID"):
    eg = ep[ep.machineID == mid]
    for e in ["error1", "error2", "error3", "error4", "error5"]:
        if e not in eg:
            continue
        s = eg.set_index("datetime")[e]
        vals = [s[(s.index > t - pd.Timedelta(hours=24)) & (s.index <= t)].sum() for t in g["datetime"]]
        feats.loc[g.index, e] = vals

# days since each component was last replaced (maintenance or failure)
rep = pd.concat([mnt.rename(columns={"comp": "c"}), fail.rename(columns={"failure": "c"})])
for c in ["comp1", "comp2", "comp3", "comp4"]:
    col = f"days_since_{c}"
    feats[col] = np.nan
    for mid, g in feats.groupby("machineID"):
        r = rep[(rep.machineID == mid) & (rep.c == c)]["datetime"].sort_values().values
        idx = np.searchsorted(r, g["datetime"].values, side="right") - 1
        d = [(t - r[i]) / np.timedelta64(1, "D") if i >= 0 else 365.0 for t, i in zip(g["datetime"].values, idx)]
        feats.loc[g.index, col] = d

feats = feats.merge(mac, on="machineID")
feats["model_n"] = feats["model"].str.replace("model", "").astype(int)

# label: any failure in the next 24h
feats["label"] = 0
feats["fails_comp"] = ""
for mid, g in feats.groupby("machineID"):
    fg = fail[fail.machineID == mid]
    for i, t in zip(g.index, g["datetime"]):
        hit = fg[(fg.datetime > t) & (fg.datetime <= t + pd.Timedelta(hours=24))]
        if len(hit):
            feats.loc[i, "label"] = 1
            feats.loc[i, "fails_comp"] = ",".join(sorted(hit.failure.unique()))

X_COLS = [c for c in feats.columns if c.endswith("24")] + ["error1", "error2", "error3", "error4", "error5",
          "days_since_comp1", "days_since_comp2", "days_since_comp3", "days_since_comp4", "model_n", "age"]
feats = feats.dropna(subset=X_COLS)
train = feats[feats.datetime < "2015-09-01"]
test = feats[feats.datetime >= "2015-09-01"]
clf = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.06, max_leaf_nodes=31, random_state=7)
clf.fit(train[X_COLS], train["label"])
p = clf.predict_proba(test[X_COLS])[:, 1]
auc = roc_auc_score(test["label"], p)
ap = average_precision_score(test["label"], p)
test = test.assign(risk=p)
# precision in the top 5% riskiest machine-days
k = max(1, int(0.05 * len(test)))
top = test.sort_values("risk", ascending=False).head(k)
prec_top = top["label"].mean()
recall_top = top["label"].sum() / max(1, test["label"].sum())
base = test["label"].mean()

# demo day: the test day with the most real failures in the next 24h
day_counts = test.groupby(test.datetime.dt.date)["label"].sum().sort_values(ascending=False)
demo_day = str(day_counts.index[0])
snap = test[test.datetime.dt.date.astype(str) == demo_day].copy()
med = train[X_COLS].median()


def drivers(row):
    out = []
    if row["vibration_mean24"] > med["vibration_mean24"] * 1.12:
        out.append(f"vibration {row['vibration_mean24']:.0f} vs usual {med['vibration_mean24']:.0f}")
    if row["pressure_mean24"] > med["pressure_mean24"] * 1.12:
        out.append(f"pressure {row['pressure_mean24']:.0f} vs usual {med['pressure_mean24']:.0f}")
    if row["volt_mean24"] > med["volt_mean24"] * 1.08:
        out.append(f"voltage {row['volt_mean24']:.0f} vs usual {med['volt_mean24']:.0f}")
    if row["rotate_mean24"] < med["rotate_mean24"] * 0.9:
        out.append(f"rotation {row['rotate_mean24']:.0f} vs usual {med['rotate_mean24']:.0f}")
    errs = [f"{e} x{int(row[e])}" for e in ["error1", "error2", "error3", "error4", "error5"] if row[e] > 0]
    if errs:
        out.append("errors in last 24h: " + ", ".join(errs))
    old = [c for c in ["comp1", "comp2", "comp3", "comp4"] if row[f"days_since_{c}"] > 60]
    if old:
        out.append("not replaced for 60+ days: " + ", ".join(old))
    return out[:4]


fleet = []
for _, r in snap.sort_values("risk", ascending=False).iterrows():
    fleet.append({"machine": f"AZ-{int(r.machineID):03d}", "model": r["model"], "age_years": int(r["age"]),
                  "risk": round(float(r["risk"]), 3), "drivers": drivers(r),
                  "actually_failed_next_24h": bool(r["label"]), "failed_component": r["fails_comp"] or None})
comp_month = fail.assign(month=fail.datetime.dt.strftime("%Y-%m")).groupby(["month", "failure"]).size().unstack(fill_value=0)
result = {
    "source": "Microsoft Azure Predictive Maintenance dataset (public, 100 machines, 2015). Component and error names are anonymised by Microsoft (comp1-4, error1-5).",
    "model_card": {"type": "Gradient boosted trees (scikit-learn HistGradientBoosting)",
                   "question": "Will this machine have a component failure in the next 24 hours?",
                   "train_period": "Jan-Aug 2015", "test_period": "Sep-Dec 2015",
                   "train_rows": int(len(train)), "test_rows": int(len(test)), "features": X_COLS,
                   "test_auc": round(float(auc), 3), "test_average_precision": round(float(ap), 3),
                   "base_failure_rate": round(float(base), 4),
                   "precision_top5pct": round(float(prec_top), 3), "recall_top5pct": round(float(recall_top), 3)},
    "demo_day": demo_day, "fleet": fleet,
    "failures_by_month": {"months": list(comp_month.index), "series": {c: comp_month[c].tolist() for c in comp_month.columns}},
    "totals": {"machines": int(mac.shape[0]), "telemetry_rows": int(tel.shape[0]), "errors": int(err.shape[0]),
               "maintenance": int(mnt.shape[0]), "failures": int(fail.shape[0])},
}
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(result, indent=1), encoding="utf-8")
print(json.dumps(result["model_card"], indent=1))
print("demo day", demo_day, "real failures that day:", int(snap["label"].sum()), "top10:", [(f["machine"], f["risk"], f["actually_failed_next_24h"]) for f in fleet[:10]])
