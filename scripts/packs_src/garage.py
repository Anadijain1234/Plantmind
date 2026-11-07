"""Car garage pack: Kaveri Motors Service — Whitefield & Hebbal workshops."""
from .common import processed, rec, tip

OBD = [  # generic SAE J2012 / ISO 15031-6 code meanings (same for all cars)
    ("P0101", "Mass air flow (MAF) circuit range/performance"), ("P0113", "Intake air temperature sensor 1 circuit high"),
    ("P0128", "Coolant temperature below thermostat regulating temperature"), ("P0171", "System too lean (bank 1)"),
    ("P0172", "System too rich (bank 1)"), ("P0300", "Random/multiple cylinder misfire detected"),
    ("P0301", "Cylinder 1 misfire detected"), ("P0302", "Cylinder 2 misfire detected"), ("P0335", "Crankshaft position sensor A circuit"),
    ("P0420", "Catalyst system efficiency below threshold (bank 1)"), ("P0442", "Evaporative emission system small leak detected"),
    ("P0455", "Evaporative emission system large leak detected"), ("P0500", "Vehicle speed sensor A"), ("P0562", "System voltage low"),
    ("P0700", "Transmission control system (MIL request)")]


def build():
    assets = [
        {"id": "PH-W", "name": "Petrol hatchback 1.2 L (Whitefield bay)", "model": "1.2L petrol hatchback", "type": "Petrol hatchback", "type_key": "petrol", "site": "wf", "cost_per_hour": 800},
        {"id": "PH-H", "name": "Petrol hatchback 1.2 L (Hebbal bay)", "model": "1.2L petrol hatchback", "type": "Petrol hatchback", "type_key": "petrol", "site": "hb", "cost_per_hour": 800},
        {"id": "DS-W", "name": "Diesel SUV 2.2 L (Whitefield)", "model": "2.2L diesel SUV", "type": "Diesel SUV", "type_key": "diesel", "site": "wf", "cost_per_hour": 1200},
        {"id": "CIV-18", "name": "Honda Civic 2018 (customer cars)", "model": "Honda Civic 2018", "type": "Sedan", "type_key": "civic", "site": "wf", "cost_per_hour": 1000},
        {"id": "COR-18", "name": "Toyota Corolla 2018 (customer cars)", "model": "Toyota Corolla 2018", "type": "Sedan", "type_key": "corolla", "site": "hb", "cost_per_hour": 1000},
        {"id": "EV-H", "name": "Electric scooter (Hebbal)", "model": "EV scooter", "type": "EV two-wheeler", "type_key": "ev", "site": "hb", "cost_per_hour": 400},
    ]
    people = [
        {"id": "venki", "name": "Venkatesh 'Venki' Murthy", "short": "Venki-anna", "role": "Senior Mechanic", "site": "wf", "experience_years": 30,
         "retiring_on": "2027-01-15", "speciality": "Engines, diagnosis by sound and smell"},
        {"id": "salim", "name": "Salim Khan", "short": "Salim", "role": "Electrical & Diagnostics", "site": "hb", "experience_years": 11,
         "retiring_on": None, "speciality": "OBD scanning, wiring, EVs"},
        {"id": "karthik", "name": "Karthik Gowda", "short": "Karthik", "role": "Junior Mechanic (ITI, joined Aug 2026)", "site": "hb", "experience_years": 0.3,
         "retiring_on": None, "speciality": "Learning — uses Ustaad on every job"},
    ]
    R = [
        rec("g-001", "2026-05-09T11:00", "PH-W", "salim", "Check-engine light P0171", "Engine light on, code P0171, rough idle",
            "Assumed bad oxygen sensor", "Replaced upstream O2 sensor", outcome="failed_again", mins=120, code="P0171", parts="O2 sensor", cost=4200),
        rec("g-002", "2026-05-12T10:30", "PH-W", "venki", "Check-engine light P0171", "Code P0171 came back three days after the sensor change",
            "Cracked intake hose after the throttle body (vacuum leak)", "Sprayed carb cleaner around intake hoses at idle — RPM jumped at the cracked hose; replaced hose; cleared code; road test",
            mins=60, code="P0171", parts="Intake hose", cost=650),
        rec("g-003", "2026-06-03T15:20", "PH-H", "venki", "Misfire P0300", "Shaking at idle, code P0300", "One ignition coil weak",
            "Swapped coils between cylinders — misfire moved with coil 2; replaced that coil; checked plugs", mins=50, code="P0300", parts="Ignition coil", cost=2800),
        rec("g-004", "2026-06-18T12:10", "DS-W", "venki", "Hard start on cold mornings", "SUV cranks long on cold mornings, starts with white smoke",
            "Two glow plugs failed", "Tested glow plug resistance; replaced the two open ones; checked glow relay", mins=90, parts="Glow plugs x2", cost=3600),
        rec("g-005", "2026-07-01T16:40", "PH-W", "salim", "Battery drains overnight", "Car dead every morning, new battery fitted 2 months ago",
            "Aftermarket music system drawing current when off", "Measured parasitic draw with ammeter after modules slept: 380 mA; pulled fuses one by one; rewired amp to ignition-switched supply",
            mins=110),
        rec("g-006", "2026-07-15T11:30", "COR-18", "salim", "Check-engine light P0420", "Code P0420 on a high-mileage Corolla",
            "Small exhaust leak before the rear O2 sensor", "Checked O2 sensor readings and smoke-tested exhaust before quoting a new catalytic converter; fixed the leaking flange gasket", mins=80, code="P0420", parts="Flange gasket", cost=450),
        rec("g-007", "2026-08-05T13:00", "CIV-18", "venki", "Steering heavy / jerky", "Steering heavy and jerky at low speed",
            "Electric power steering rack fault (matches many NHTSA owner complaints for this model)", "Checked EPS warning codes; sent to the dealer for rack inspection under warranty", mins=45,
            source_ref="NHTSA owner complaints, Honda Civic 2018"),
        rec("g-008", "2026-08-21T10:10", "EV-H", "salim", "Range dropped suddenly", "Scooter range down from 90 km to 55 km",
            "One weak cell group after deep discharge", "Read cell voltages via service tool; balanced pack with slow charge; advised not to leave below 10%", mins=70),
        rec("g-009", "2026-09-10T12:00", "PH-H", "karthik", "Check-engine light P0171", "P0171 with rough idle",
            "Vacuum leak at the intake hose", "Followed Venki-anna's fix from Ustaad: spray test at idle; found cracked hose; replaced; cleared code", mins=35, code="P0171", parts="Intake hose", cost=650),
        rec("g-010", "2026-09-24T15:30", "PH-H", "karthik", "Misfire P0300", "Shaking at idle, P0300", "Weak ignition coil",
            "Followed Venki-anna's fix from Ustaad: swapped coils, misfire moved; replaced coil", mins=30, code="P0300", parts="Ignition coil", cost=2800),
        rec("g-011", "2026-10-07T11:45", "DS-W", "karthik", "Hard start on cold mornings", "Long cranking on a cold morning", "Glow plugs",
            "Tested resistance; replaced one open glow plug", mins=45, parts="Glow plug", cost=1800),
        rec("g-012", "2026-10-28T17:00", "PH-W", "karthik", "AC not cooling in traffic", "AC cool on highway, warm in traffic",
            "Condenser fins blocked with dust and the fan relay weak", "Washed condenser gently; replaced fan relay; checked fan runs when AC is on", mins=60, parts="Fan relay", cost=350, status="pending"),
    ]
    T = [
        tip("tg-01", "venki", "PH-W", "2026-05-13",
            "P0171 means the engine is running lean (too much air). Before buying an O2 sensor, spray carb cleaner around the intake hoses at idle — if RPM jumps, you found a vacuum leak. Saves a ₹4,000 sensor.",
            "OBD-II code P0171 (SAE J2012)"),
        tip("tg-02", "venki", "PH-H", "2026-06-04",
            "For a misfire, swap the ignition coil with the next cylinder and re-scan. If the misfire code moves with the coil, it's the coil. If it stays, check plug and injector."),
        tip("tg-03", "salim", "COR-18", "2026-07-16",
            "P0420 does not always mean a dead catalytic converter. Check for exhaust leaks and compare front and rear O2 sensor readings first — a converter costs 50 times more than a gasket.",
            "OBD-II code P0420 (SAE J2012)"),
        tip("tg-04", "salim", "PH-W", "2026-07-02",
            "Battery drain: wait for the modules to sleep (about 20-30 minutes), then measure. More than about 50 mA is suspicious — pull fuses one by one until the current drops."),
        tip("tg-05", "venki", "DS-W", "2026-06-19",
            "Diesel that starts hard only on cold mornings with white smoke — test glow plugs before touching the injectors."),
    ]
    n = processed("garage_nhtsa.json") or {"complaints": [], "by_component": []}
    public = []
    for c in n["complaints"]:
        if len(c["summary"]) < 120:
            continue
        model = "Honda Civic 2018" if "Civic" in c["vehicle"] else "Toyota Corolla 2018"
        public.append({"id": c["id"], "title": f"{c['vehicle']} — {c['components'].title()}", "text": c["summary"], "fix": "",
                       "source": "NHTSA owner complaint", "date": _iso(c["date"]), "type_key": "civic" if "Civic" in model else "corolla",
                       "model": model, "outcome": "open", "url": "https://www.nhtsa.gov/recalls"})
        if len(public) >= 220:
            break
    return {
        "id": "garage", "name": "Car garage", "icon": "🚗", "color": "#1D4ED8",
        "tagline": "The senior mechanic's diagnosis order, for every new mechanic",
        "org": {"name": "Kaveri Motors Service (demo)", "note": "Demo workshops in Bengaluru. People are fictional; OBD code meanings and NHTSA complaints are real.",
                "ustaad_started": "2026-09-01"},
        "labels": {"asset": "Vehicle type", "assets": "Vehicle types", "person": "Mechanic", "record": "Job card", "problem": "Problem",
                   "code": "OBD code", "downtime": "Time in bay"},
        "cost_per_hour": 800,
        "sites": [{"id": "wf", "name": "Whitefield workshop"}, {"id": "hb", "name": "Hebbal workshop"}],
        "roles": [
            {"id": "mechanic", "name": "Mechanic", "can_approve": False, "tools": ["ask", "log", "quiz", "obd"]},
            {"id": "advisor", "name": "Service advisor", "can_approve": False, "tools": ["ask", "memory", "stats", "shift", "obd", "quiz", "passport"]},
            {"id": "head", "name": "Workshop head", "can_approve": True, "tools": ["ask", "log", "memory", "approvals", "playbook", "risk", "interview", "shift", "skills", "passport", "stats", "obd", "quiz"]},
        ],
        "tools": ["obd"],
        "safety_line": "Engine off, key out and handbrake on before working; let the exhaust and engine cool.",
        "generic": {"default": ["Scan for OBD codes", "Check battery voltage", "Check fluids", "Road test", "Call the brand's dealer"]},
        "questions": ["Petrol hatchback shows P0171 and idles rough", "Car battery is dead every morning",
                      "Which problem took the most time in the bay?", "Corolla shows P0420"],
        "interview_extra": [
            {"topic": "By ear", "question": "Which sounds tell you the problem before you scan the car?", "why": "Diagnosis by sound is pure experience."},
            {"topic": "Parts", "question": "Which spare parts are often fake or low quality, and how do you spot them?", "why": "This protects customers and margins."}],
        "assets": assets, "people": people, "records": R, "tips": T, "public": public,
        "panels": [{"id": "nhtsa", "title": f"Owner complaints by part — Civic & Corolla 2018 (NHTSA, {len(n['complaints'])} complaints)", "type": "bar",
                    "data": {"labels": [x["component"].title() for x in n["by_component"][:10]], "values": [x["count"] for x in n["by_component"][:10]]},
                    "source": n.get("source")}],
        "lookup": {"type": "obd", "title": "OBD-II code meanings (generic, all cars)", "source": "SAE J2012 / ISO 15031-6 generic codes",
                   "items": [{"code": c, "meaning": m} for c, m in OBD]},
    }


def _iso(d):
    try:
        m, dd, y = d.split("/")
        return f"{y}-{m}-{dd}"
    except Exception:
        return "2020-01-01"
