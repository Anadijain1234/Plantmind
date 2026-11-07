"""Factory pack: Kaveri Precision Components — Bengaluru (Peenya) plant + Pune (Chakan) plant."""
import json
from pathlib import Path

from .common import processed, rec, tip

BASE = json.loads((Path(__file__).parent / "factory_base.json").read_text(encoding="utf-8"))

TYPE_KEY = {"CNC machining centre": "cnc", "Hydraulic press": "press", "Air compressor (feeds the whole plant)": "compressor",
            "Steam boiler (parts washing & heat treatment)": "boiler"}


def build():
    assets = []
    for m in BASE["machines"]:
        assets.append({"id": m["id"], "name": m["name"], "model": m["model"], "type": m["type"], "type_key": TYPE_KEY[m["type"]],
                       "site": "blr", "line": m["line"], "cost_per_hour": m["downtime_cost_per_hour"]})
    assets += [
        {"id": "CNC-P1", "name": "CNC-P1 · VMC-850 Vertical Machining Centre", "model": "VMC-850", "type": "CNC machining centre",
         "type_key": "cnc", "site": "pune", "line": "Cell 1", "cost_per_hour": 6000},
        {"id": "CNC-P2", "name": "CNC-P2 · HMC-500 Horizontal Machining Centre", "model": "HMC-500", "type": "CNC machining centre",
         "type_key": "cnc", "site": "pune", "line": "Cell 2", "cost_per_hour": 9000},
        {"id": "HYD-P1", "name": "HYD-P1 · 200-tonne Hydraulic Press", "model": "HP-200T", "type": "Hydraulic press",
         "type_key": "press", "site": "pune", "line": "Press shop", "cost_per_hour": 5000},
    ]
    people = [{"id": t["id"], "name": t["name"], "short": t["short"], "role": t["role"], "site": "blr",
               "experience_years": t["experience_years"], "retiring_on": t["retiring_on"], "speciality": t["speciality"]}
              for t in BASE["technicians"]]
    people += [
        {"id": "sunil", "name": "Sunil Patil", "short": "Sunil", "role": "Senior Maintenance Technician (Pune)", "site": "pune",
         "experience_years": 18, "retiring_on": None, "speciality": "HMC spindles, hydraulics"},
        {"id": "kavya", "name": "Kavya Kulkarni", "short": "Kavya", "role": "Maintenance Engineer (Pune)", "site": "pune",
         "experience_years": 4, "retiring_on": None, "speciality": "Condition monitoring, data"},
    ]
    records = []
    for l in BASE["logs"]:
        records.append({"id": l["id"], "datetime": l["datetime"], "asset_id": l["machine_id"], "person_id": l["fixed_by"],
                        "problem": l["fault"], "code": l["alarm_code"], "symptom": l["symptom"], "cause": l["root_cause"],
                        "action": l["action"], "parts": l["parts"], "cost": l["parts_cost"], "downtime_minutes": l["downtime_minutes"],
                        "outcome": l["outcome"], "notes": l["notes"], "source_ref": "", "status": "approved"})
    records += [
        rec("pune-001", "2026-06-12T10:20", "CNC-P2", "sunil", "Spindle vibration",
            "Vibration rising with a whistling sound above 4000 rpm, spindle nose warm but below 70 °C",
            "Motor-to-spindle coupling misaligned (0.06 mm)", "Checked coupling alignment with a dial gauge; realigned to under 0.02 mm; ran up to 6000 rpm and re-checked vibration",
            mins=150, code="2041", notes="Bearings were NOT changed — saved about ₹38,000."),
        rec("pune-002", "2026-07-30T15:05", "HYD-P1", "sunil", "Ram slow / oil hot",
            "Ram slow on return stroke, oil at 62 °C after one hour", "Pump suction strainer choked with sludge",
            "Cleaned the suction strainer; topped up oil to the mark; checked return-line filter", mins=95),
        rec("pune-003", "2026-08-21T09:40", "CNC-P1", "kavya", "Spindle orientation fault",
            "Alarm on tool change: spindle does not stop at the orientation position", "Chips and coolant film on the orientation proximity sensor",
            "Cleaned the proximity sensor face; set the sensor gap to 1 mm; tested 20 tool changes", mins=55, code="1026"),
        rec("pune-004", "2026-09-18T11:10", "CNC-P2", "kavya", "Spindle vibration",
            "Vibration 5.2 mm/s at 4500 rpm after a heavy roughing job", "Coupling bolts loosened",
            "Followed Sunil's fix from Ustaad: dial-gauge alignment check; torqued coupling bolts; re-checked under 0.02 mm", mins=70, code="2041"),
        rec("pune-005", "2026-10-09T14:00", "CNC-P1", "kavya", "Tool changer (ATC) stuck",
            "ATC arm stops halfway, alarm 1012", "Air pressure at the ATC regulator only 4.8 bar", "Set the ATC regulator to 6 bar; drained water from the FRL unit", mins=35, code="1012"),
    ]
    tips = [{"id": n["id"], "person_id": n["technician_id"], "asset_id": n["machine_id"], "date": n["date"], "text": n["text"],
             "source_ref": "", "status": "approved"} for n in BASE["notes"]]
    tips += [
        tip("tip-f101", "ramesh", "ALL", "2026-08-02",
            "Don't wait for the machine to trip on vibration. On our CNC spindles, above 4.5 mm/s I plan a stop for the same day; "
            "above 7.1 mm/s I stop the machine at once — that is the 'damage' zone for a machine this size.",
            "ISO 10816-1 vibration zones (4.5 / 7.1 mm/s)"),
        tip("tip-f102", "kavya", "CNC-P1", "2026-09-25",
            "In 10,000 public machining runs, tool-wear failures started at about 200 minutes of tool life. We change cutting tools at 180 minutes "
            "on the VMC-850 instead of waiting for a broken tool.", "AI4I 2020 dataset (UCI)"),
        tip("tip-f103", "kavya", "CNC-P2", "2026-10-02",
            "Heat failures in the public machining data happened only when the process ran less than 8.6 K hotter than the air AND the spindle was "
            "below 1380 rpm. So at low speed in the afternoon heat, check coolant flow before blaming the spindle.", "AI4I 2020 dataset (UCI)"),
        tip("tip-f104", "imran", "CNC-2", "2026-11-03",
            "Servo overload 401 on CNC-2 came back twice in the same week — check the way-lube pump timer too, not only the tank.",
            status="pending"),
    ]
    ai = processed("factory_ai4i.json") or {"modes": []}
    public = [{"id": f"ai4i-{m['id']}", "title": f"{m['name']} — {m['count']} cases in 10,000 machining runs",
               "text": f"Rule seen in the data: {m['rule']}.", "fix": "", "source": "AI4I 2020 dataset (UCI)", "date": "2020-01-01",
               "type_key": "cnc", "outcome": "open", "url": "https://archive.ics.uci.edu/dataset/601/ai4i+2020+predictive+maintenance+dataset"}
              for m in ai["modes"]]
    public.append({"id": "iso-10816", "title": "ISO 10816-1 vibration zones for machines",
                   "text": "For medium machines (15-75 kW): up to 1.12 mm/s good, 1.12-2.8 acceptable, 2.8-7.1 unsatisfactory (plan repair), above 7.1 mm/s damage likely. Small machines: limits 0.71 / 1.8 / 4.5 mm/s.",
                   "fix": "Plan a stop in the 'unsatisfactory' zone; stop at once in the 'damage' zone.", "source": "ISO 10816-1", "date": "2020-01-01",
                   "type_key": "cnc", "outcome": "open", "url": ""})
    fleet = processed("factory_fleet.json") or {}
    return {
        "id": "factory", "name": "Factory", "icon": "🏭", "color": "#E8833A",
        "tagline": "Machine fixes that only the senior technician knows",
        "org": {"name": "Kaveri Precision Components (demo)", "note": "Demo factory with two plants. People are fictional; machine facts are real.",
                "ustaad_started": "2026-09-01"},
        "labels": {"asset": "Machine", "assets": "Machines", "person": "Technician", "record": "Breakdown", "problem": "Fault",
                   "code": "Alarm", "downtime": "Downtime"},
        "cost_per_hour": 6000,
        "sites": [{"id": "blr", "name": "Bengaluru plant (Peenya)"}, {"id": "pune", "name": "Pune plant (Chakan)"}],
        "roles": [
            {"id": "technician", "name": "Maintenance technician", "can_approve": False, "tools": ["ask", "log", "quiz", "sensors"]},
            {"id": "supervisor", "name": "Maintenance supervisor", "can_approve": True, "tools": ["ask", "log", "memory", "approvals", "playbook", "risk", "interview", "shift", "skills", "passport", "stats", "sensors", "fleet", "check", "quiz"]},
            {"id": "manager", "name": "Plant head", "can_approve": True, "tools": ["stats", "risk", "shift", "skills", "passport", "fleet", "sensors", "ask", "memory", "approvals", "playbook", "interview", "quiz", "check"]},
        ],
        "tools": ["sensors", "fleet", "check"],
        "safety_line": "Switch off and lock out (LOTO) the machine before opening any guard.",
        "generic": {"cnc": ["Check spindle bearings for wear and noise", "Check lubrication and the auto-lube pump", "Check tool holder and clamping",
                            "Check machine levelling", "Call the machine maker's service engineer"],
                    "press": ["Check hydraulic oil level and temperature", "Look for leaks at seals and hoses", "Check pump and relief valve pressure", "Call the press maker"],
                    "compressor": ["Check oil level", "Check air and oil filters", "Check room ventilation", "Call the compressor service team"],
                    "boiler": ["Check water level in the gauge glass", "Check the feed pump", "Test the level switch", "Call the boiler engineer"],
                    "default": ["Check the basics", "Call the maker's service engineer"]},
        "questions": ["CNC-3 alarm 2041 with a whistling sound at high rpm", "HYD-1 ram is slow and the oil is hot",
                      "Which machine lost the most downtime hours?", "CMP-1 tripped on high temperature in the afternoon"],
        "interview_extra": [
            {"topic": "Daily checks", "question": "Which sounds, smells or readings do you check every day that nobody else does?", "why": "Early-warning habits are rarely written down."},
            {"topic": "Spare parts", "question": "Which spares must always be in stock, and which fail most in monsoon or summer?", "why": "Seasonal patterns live in experience, not in logs."}],
        "assets": assets, "people": people, "records": records, "tips": tips, "public": public,
        "panels": [
            {"id": "fleet-failures", "title": "Fleet failures by month (Microsoft Azure dataset, 100 machines)", "type": "stacked",
             "data": fleet.get("failures_by_month"), "source": fleet.get("source")},
        ],
    }
