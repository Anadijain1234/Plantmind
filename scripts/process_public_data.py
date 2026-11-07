"""
Turn the raw public datasets into the small files the app uses (data/processed/).
The raw files are NOT in this repo (too big, some licences don't allow re-sharing). See data/README.md.

Usage: python scripts/process_public_data.py <raw folder>
The raw folder should contain: sensor_data.csv, ai4i2020.csv, indian_food.csv, nyc_indian.csv,
fda_event_0.json, fda_event_1.json, fda_event_2.json, nhtsa_0.json, nhtsa_1.json,
post-mortems/README.md, loghub/<System>/<System>_2k.log_structured.csv, zomato_summary.json
"""
import collections
import json
import re
import sys
from pathlib import Path

import pandas as pd

RAW = Path(sys.argv[1])
OUT = Path(__file__).resolve().parent.parent / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)


def save(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding="utf-8")
    print("wrote", name, (OUT / name).stat().st_size // 1024, "KB")


def sentence_case(t):
    t = re.sub(r"\s+", " ", t or "").strip()
    if t.isupper() or sum(c.isupper() for c in t) > 0.6 * max(1, sum(c.isalpha() for c in t)):
        t = t.lower()
        t = re.sub(r"(^|[.!?]\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), t)
    return t


def cut(t, n=380):
    t = (t or "").strip()
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + "…"


# ---------- factory: teammate's sensor CSV -> live replay ----------
s = pd.read_csv(RAW / "sensor_data.csv", parse_dates=["timestamp"])
MAP = {"M-001": "CNC-1", "M-002": "CNC-2", "M-003": "CNC-3"}
s["asset"] = s["machine_id"].map(MAP)
end = s[(s.machine_id == "M-003") & (s.vibration_mm_s > 8.0)].timestamp.min()  # stop the replay before values get unrealistic
start = s.timestamp.min()
s = s[(s.timestamp >= start) & (s.timestamp <= end)]
series = {}
for a, g in s.groupby("asset"):
    series[a] = [{"t": int((r.timestamp - start).total_seconds() // 60), "temp": round(r.temperature_c, 1),
                  "vib": round(r.vibration_mm_s, 2), "kw": round(r.power_kw, 1)} for r in g.itertuples()]
save("factory_sensors.json", {
    "source": "Sensor readings shared by the team (3 machines, every 15 min). Machine IDs mapped M-001→CNC-1, M-002→CNC-2, M-003→CNC-3. "
              "Replay stops when vibration passes 8 mm/s, because later values in the file climb to physically impossible levels (900+ °C).",
    "interval_minutes": 15, "points": len(next(iter(series.values()))),
    "thresholds": {"vib_warn": 4.5, "vib_stop": 7.1, "temp_warn": 80,
                   "why": "ISO 10816-1 zone limits: 4.5 mm/s is the 'unsatisfactory' limit for small machines and 7.1 mm/s the 'damage' limit for medium machines (15-75 kW). 80 °C machine temperature is above anything the healthy machines reached in this data (max 78 °C)."},
    "series": series})

# ---------- factory: AI4I 2020 failure rules ----------
a = pd.read_csv(RAW / "ai4i2020.csv")
save("factory_ai4i.json", {
    "source": "AI4I 2020 Predictive Maintenance Dataset (UCI, CC BY 4.0): 10,000 machining runs, 339 failures.",
    "runs": int(len(a)), "failures": int(a["Machine failure"].sum()),
    "modes": [
        {"id": "TWF", "name": "Tool wear failure", "count": int(a.TWF.sum()), "rule": "Tool wear reaches about 200-240 minutes", "check": "tool_wear >= 200"},
        {"id": "HDF", "name": "Heat dissipation failure", "count": int(a.HDF.sum()), "rule": "Process minus air temperature below 8.6 K AND spindle speed below 1380 rpm", "check": "dT < 8.6 and rpm < 1380"},
        {"id": "PWF", "name": "Power failure", "count": int(a.PWF.sum()), "rule": "Power (torque × speed) below 3,500 W or above 9,000 W", "check": "power < 3500 or power > 9000"},
        {"id": "OSF", "name": "Overstrain failure", "count": int(a.OSF.sum()), "rule": "Tool wear × torque above 11,000 (L), 12,000 (M) or 13,000 (H) min·Nm", "check": "strain > limit[type]"},
        {"id": "RNF", "name": "Random failure", "count": int(a.RNF.sum()), "rule": "About 0.1% chance on any run — no warning sign", "check": "none"}],
    "typical": {"air_K": 300.0, "process_K": 310.0, "rpm": 1503, "torque": 40.1, "tool_wear": 108}})

# ---------- restaurant ----------
food = pd.read_csv(RAW / "indian_food.csv").replace({-1: None, "-1": None})
save("restaurant_dishes.json", {"source": "Indian Food 101 (Kaggle): 255 dishes with ingredients, prep/cook time, region.",
                                "dishes": json.loads(food.to_json(orient="records"))})
n = pd.read_csv(RAW / "nyc_indian.csv")
viol = n.dropna(subset=["violation_description"])
top = viol.groupby(["violation_description", "critical_flag"]).size().reset_index(name="count").sort_values("count", ascending=False).head(15)
yrs = n.assign(y=n.inspection_date.str[:4]).groupby("y").camis.nunique()
save("restaurant_inspections.json", {
    "source": "NYC Department of Health restaurant inspection results (NYC Open Data), cuisine = Indian.",
    "rows": int(len(n)), "restaurants": int(n.camis.nunique()),
    "date_range": [n.inspection_date.min()[:10], n.inspection_date.max()[:10]],
    "critical_share": round(float((viol.critical_flag == "Critical").mean()), 3),
    "top_violations": [{"text": r.violation_description, "critical": r.critical_flag == "Critical", "count": int(r["count"])} for _, r in top.iterrows()],
    "hot_hold_violations": int(viol.violation_description.str.contains("Hot TCS food item not held at or above 140", regex=False).sum()),
    "cold_hold_violations": int(viol.violation_description.str.contains("Cold TCS food item held above 41", regex=False).sum()),
    "restaurants_by_year": {k: int(v) for k, v in yrs.items()}})
z = json.loads((RAW / "zomato_summary.json").read_text())
z["source"] = "Zomato Bangalore Restaurants dataset (Kaggle, scraped 2019): reviews scanned for dish names; low-rated = 2.5 stars or less. Only these counts are kept, no review text."
save("restaurant_complaints.json", z)

# ---------- healthcare: FDA device reports ----------
fda = []
for f in ["fda_event_0.json", "fda_event_1.json", "fda_event_2.json"]:
    for r in json.loads((RAW / f).read_text())["results"]:
        if r.get("event_type") != "Malfunction" or not r.get("device"):
            continue
        d = r["device"][0]
        texts = {m.get("text_type_code", ""): m.get("text", "") for m in r.get("mdr_text", [])}
        desc = sentence_case(texts.get("Description of Event or Problem", ""))
        mfr = sentence_case(texts.get("Additional Manufacturer Narrative", ""))
        full = f"{desc} {mfr}"
        fix = re.search(r"(replac\w+[^.]*|resolved[^.]*|returned to service[^.]*|recalibrat\w+[^.]*|repair\w*[^.]*)", full, re.I)
        fda.append({"id": f"fda-{r.get('report_number') or r.get('mdr_report_key')}",
                    "date": (r.get("date_received") or "")[:4] + "-" + (r.get("date_received") or "")[4:6] + "-" + (r.get("date_received") or "")[6:8],
                    "device": sentence_case(d.get("generic_name", "")), "brand": d.get("brand_name", ""),
                    "manufacturer": d.get("manufacturer_d_name", ""), "problems": r.get("product_problems") or [],
                    "what_happened": cut(desc, 420), "resolution": cut(fix.group(1), 220) if fix else "",
                    "url": "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfmaude/search.cfm"})
probs = collections.Counter(p for x in fda for p in x["problems"])
save("healthcare_fda.json", {"source": "U.S. FDA MAUDE device reports via openFDA (public domain). Malfunction reports only; patient details removed.",
                             "reports": fda, "top_problems": [{"problem": k, "count": v} for k, v in probs.most_common(12)],
                             "with_resolution": sum(1 for x in fda if x["resolution"])})

# ---------- garage: NHTSA complaints ----------
cars = []
for f in ["nhtsa_0.json", "nhtsa_1.json"]:
    for r in json.loads((RAW / f).read_text())["results"]:
        p = (r.get("products") or [{}])[0]
        cars.append({"id": f"nhtsa-{r['odiNumber']}", "date": r.get("dateComplaintFiled"),
                     "vehicle": f"{p.get('productMake', '').title()} {p.get('productModel', '').title()} {p.get('productYear', '')}",
                     "components": r.get("components", ""), "crash": r.get("crash"), "fire": r.get("fire"),
                     "summary": cut(r.get("summary", ""), 420)})
comp = collections.Counter(c.strip() for x in cars for c in x["components"].split(","))
save("garage_nhtsa.json", {"source": "U.S. NHTSA vehicle owner complaints (public domain): Honda Civic 2018 and Toyota Corolla 2018. VINs removed.",
                           "complaints": cars, "by_component": [{"component": k, "count": v} for k, v in comp.most_common(12)]})

# ---------- IT on-call: public post-mortems + logs ----------
pm, cat = [], None
for line in (RAW / "post-mortems" / "README.md").read_text(encoding="utf-8").splitlines():
    if line.startswith("## "):
        cat = line[3:].strip()
        continue
    m = re.match(r"^\[([^\]]+)\]\(([^)]+)\)\.?\s*(.*)$", line.strip())
    if m and cat not in (None, "Table of Contents", "Other lists of postmortems", "Analysis", "Contributors"):
        pm.append({"id": f"pm-{len(pm) + 1:03d}", "company": m.group(1), "url": m.group(2), "category": cat, "summary": cut(m.group(3), 520)})
save("it_postmortems.json", {"source": "danluu/post-mortems (GitHub): public incident write-ups from real companies.", "items": pm,
                             "by_category": dict(collections.Counter(x["category"] for x in pm))})
logs = []
for sysdir in sorted((RAW / "loghub").iterdir()):
    f = sysdir / f"{sysdir.name}_2k.log_structured.csv"
    if not f.exists():
        continue
    d = pd.read_csv(f)
    t = d.EventTemplate.value_counts().head(5)
    logs.append({"system": sysdir.name, "lines": int(len(d)), "top_patterns": [{"pattern": k[:160], "count": int(v)} for k, v in t.items()]})
save("it_logs.json", {"source": "Loghub (logpai, GitHub): real system logs, 2,000-line samples per system. Please cite https://github.com/logpai/loghub.", "systems": logs})
