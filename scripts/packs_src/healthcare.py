"""Hospital operations pack: equipment, checklists and handover only — never diagnosis or treatment."""
from .common import processed, rec, tip


def build():
    assets = [
        {"id": "VNT-1", "name": "ICU ventilator, bed 4 (Bengaluru)", "model": "ICU-Vent A", "type": "Ventilator", "type_key": "ventilator", "site": "blr", "cost_per_hour": 4000},
        {"id": "VNT-2", "name": "ICU ventilator, bed 7 (Bengaluru)", "model": "ICU-Vent A", "type": "Ventilator", "type_key": "ventilator", "site": "blr", "cost_per_hour": 4000},
        {"id": "VNT-M1", "name": "ICU ventilator, bed 2 (Mysuru)", "model": "ICU-Vent A", "type": "Ventilator", "type_key": "ventilator", "site": "mys", "cost_per_hour": 4000},
        {"id": "IP-1", "name": "Infusion pump pool, ICU (Bengaluru)", "model": "Pump-B", "type": "Infusion pump", "type_key": "infusion-pump", "site": "blr", "cost_per_hour": 1500},
        {"id": "NAV-1", "name": "Neuronavigation system, Neuro OT 1", "model": "Optical navigation", "type": "Surgical navigation", "type_key": "navigation", "site": "blr", "cost_per_hour": 25000},
        {"id": "MIC-1", "name": "Operating microscope, Neuro OT 1", "model": "Neuro microscope", "type": "Operating microscope", "type_key": "microscope", "site": "blr", "cost_per_hour": 25000},
        {"id": "ESU-1", "name": "Electrosurgical unit (bipolar), Neuro OT 1", "model": "ESU bipolar", "type": "Electrosurgery", "type_key": "electrosurgery", "site": "blr", "cost_per_hour": 25000},
        {"id": "AUT-1", "name": "Pre-vacuum steam autoclave, CSSD", "model": "Pre-vac autoclave", "type": "Steriliser", "type_key": "autoclave", "site": "blr", "cost_per_hour": 8000},
        {"id": "HND-ICU", "name": "ICU shift handover (process)", "model": "Handover", "type": "Process", "type_key": "handover", "site": "blr", "cost_per_hour": 0},
    ]
    people = [
        {"id": "prakash", "name": "Prakash Hegde", "short": "Prakash", "role": "Senior Biomedical Engineer", "site": "blr", "experience_years": 24,
         "retiring_on": "2027-01-31", "speciality": "Ventilators, OT equipment, autoclaves"},
        {"id": "mary", "name": "Sister Mary Thomas", "short": "Sister Mary", "role": "ICU Nursing In-charge", "site": "blr", "experience_years": 21,
         "retiring_on": None, "speciality": "ICU workflow, handover, infusion safety"},
        {"id": "lakshmi", "name": "Lakshmi R", "short": "Lakshmi", "role": "Neuro OT Nurse", "site": "blr", "experience_years": 8,
         "retiring_on": None, "speciality": "Neuro OT setup, navigation, microscope"},
        {"id": "nikhil", "name": "Nikhil S", "short": "Nikhil", "role": "Biomedical Engineer (joined Jul 2026)", "site": "mys", "experience_years": 0.4,
         "retiring_on": None, "speciality": "Learning — Mysuru branch"},
    ]
    R = [
        rec("h-001", "2026-05-11T02:30", "VNT-1", "prakash", "High blower temperature alarm", "Ventilator alarming 'high blower temperature' at night; backup ventilator connected by ICU team",
            "Inlet air filter clogged with dust", "Swapped in backup ventilator; replaced the inlet filter; ran the manufacturer's self-test before return to service", mins=60,
            source_ref="Matches FDA MAUDE reports: 'replacement of the filter resolved' high blower temperature"),
        rec("h-002", "2026-06-02T11:15", "VNT-2", "prakash", "Battery not charging", "Battery icon not charging; internal battery under 20% after a power cut",
            "Internal battery at end of life (3 years)", "Replaced internal battery; logged battery date on the asset sticker; set a 30-month replacement reminder", mins=90, parts="Internal battery", cost=18000),
        rec("h-003", "2026-06-20T15:40", "VNT-1", "nikhil", "Flow sensor calibration failed", "Pre-use check fails at flow sensor calibration",
            "Assumed software fault", "Restarted ventilator", outcome="failed_again", mins=30),
        rec("h-004", "2026-06-20T17:10", "VNT-1", "prakash", "Flow sensor calibration failed", "Same calibration failure after restart",
            "Moisture inside the expiratory flow sensor", "Replaced the expiratory flow sensor; recalibrated; pre-use check passed", mins=45, parts="Flow sensor", cost=9000),
        rec("h-005", "2026-07-08T09:20", "IP-1", "mary", "Repeated occlusion alarm", "Pump keeps alarming 'downstream occlusion'",
            "Roller clamp partly closed and line kinked under the patient's arm", "Opened roller clamp fully; re-routed the line; checked line from bag to cannula", mins=10),
        rec("h-006", "2026-07-19T14:05", "NAV-1", "lakshmi", "Navigation registration inaccurate", "Accuracy check on a landmark shows about 4 mm error",
            "Patient reference array bumped while draping", "Stopped; re-registered; re-checked accuracy on two landmarks before the surgeon continued", mins=20),
        rec("h-007", "2026-08-04T10:00", "MIC-1", "lakshmi", "Microscope light dim", "Light output low mid-case",
            "Main lamp past its rated hours", "Switched to the backup lamp from the panel; replaced main lamp after the case; logged lamp hours", mins=5, parts="Xenon lamp", cost=22000),
        rec("h-008", "2026-08-11T12:30", "ESU-1", "prakash", "Bipolar not coagulating", "Bipolar forceps not coagulating, unit shows no fault",
            "Bipolar cable broken inside the insulation near the connector", "Swapped the bipolar cable with a spare; tested with a continuity check; condemned the old cable", mins=10, parts="Bipolar cable", cost=4500),
        rec("h-009", "2026-08-25T07:10", "AUT-1", "prakash", "Bowie-Dick test failed", "Morning Bowie-Dick test sheet shows uneven colour change",
            "Air leak — door gasket worn", "Stopped loads; replaced door gasket; ran leak test and repeated Bowie-Dick test — passed", mins=150, parts="Door gasket", cost=7000),
        rec("h-010", "2026-08-30T16:45", "AUT-1", "nikhil", "Wet packs after sterilisation", "Instrument packs coming out wet",
            "Chamber overloaded; packs touching the walls", "Loaded fewer packs; kept gaps between them; used full drying time", mins=40),
        rec("h-011", "2026-09-12T20:05", "HND-ICU", "mary", "Information missed at handover", "Night shift did not know a pump had been changed in the evening",
            "Free-form verbal handover", "Started bedside SBAR handover (Situation, Background, Assessment, Recommendation) with an equipment line", mins=0),
        rec("h-012", "2026-09-27T03:15", "VNT-M1", "nikhil", "High blower temperature alarm", "Mysuru ventilator alarming high blower temperature",
            "Inlet air filter clogged", "Followed Prakash's fix from Ustaad (Bengaluru): replaced the inlet filter; self-test passed", mins=25),
        rec("h-013", "2026-10-10T08:00", "AUT-1", "nikhil", "Bowie-Dick test failed", "Bowie-Dick sheet uneven again",
            "Air leak — door gasket worn", "Followed Prakash's fix from Ustaad: checked door gasket, replaced, repeated test — passed", mins=70),
        rec("h-014", "2026-10-21T13:30", "NAV-1", "lakshmi", "Navigation registration inaccurate", "Landmark check off by about 3 mm after repositioning the camera",
            "Reference array bumped", "Re-registered and re-checked two landmarks", mins=12),
        rec("h-015", "2026-11-04T02:40", "VNT-2", "nikhil", "High blower temperature alarm", "Blower temperature alarm on bed 7", "Inlet filter clogged",
            "Replaced inlet filter", mins=20, status="pending"),
    ]
    T = [
        tip("th-01", "prakash", "VNT-1", "2026-05-12",
            "High blower temperature alarm on our ICU ventilators: first look at the inlet air filter — dust-blocked filters are the usual cause. "
            "Replace it and run the self-test before blaming the blower.", "FDA MAUDE ventilator reports"),
        tip("th-02", "prakash", "AUT-1", "2026-08-26",
            "Run the Bowie-Dick test every morning in the first empty cycle of a pre-vacuum autoclave. If the colour change is uneven, there is air in the "
            "chamber — check the door gasket before running any load.", "Sterilisation practice (Bowie-Dick air-removal test)"),
        tip("th-03", "prakash", "AUT-1", "2026-08-31",
            "Steam sterilisation needs at least 121 °C for 15 minutes or 134 °C for 3 minutes at the right pressure. Never shorten the drying time to "
            "save a cycle — wet packs are not sterile.", "WHO decontamination & reprocessing guidance"),
        tip("th-04", "lakshmi", "NAV-1", "2026-07-20",
            "After draping or moving the camera, always do a landmark accuracy check. If the reference array was touched, re-register — "
            "don't let the case continue on an old registration.", ""),
        tip("th-05", "mary", "HND-ICU", "2026-09-13",
            "Use SBAR at the bedside for every handover and add one equipment line: which pumps or ventilators were changed, alarms seen, and what is pending with biomedical.",
            "SBAR handover (WHO / IHI patient-safety practice)"),
        tip("th-06", "lakshmi", "ALL", "2026-07-25",
            "WHO Time Out before skin incision: everyone says name and role; confirm patient, procedure and side on the displayed images; antibiotic within 60 minutes; "
            "anticipated critical events; confirm sterility indicators.", "WHO Surgical Safety Checklist"),
    ]
    fda = processed("healthcare_fda.json") or {"reports": [], "top_problems": []}
    public = []
    for r in fda["reports"]:
        if not r["resolution"] and len(public) > 60:
            continue
        tk = "ventilator" if "ventilator" in r["device"].lower() else "infusion-pump"
        public.append({"id": r["id"], "title": f"{r['device']} — {', '.join(dict.fromkeys(r['problems']))[:90] or 'malfunction'}",
                       "text": r["what_happened"], "fix": r["resolution"], "source": "FDA MAUDE device report", "date": r["date"],
                       "type_key": tk, "outcome": "fixed" if r["resolution"] else "open", "url": r["url"]})
    return {
        "id": "healthcare", "name": "Hospital operations", "icon": "🏥", "color": "#0F766E",
        "tagline": "Equipment, checklists and handover know-how — never diagnosis",
        "org": {"name": "Sahyadri Neuro & Trauma Hospital (demo)", "note": "Demo hospital, Bengaluru + Mysuru. People are fictional; device reports and checklists are real.",
                "ustaad_started": "2026-09-01"},
        "banner": "Operations only: equipment, checklists, sterilisation and handover. Ustaad never gives diagnosis or treatment advice — ask the treating doctor.",
        "llm_guard": "NEVER give medical diagnosis, drug doses or treatment advice. If asked, say this must come from the treating doctor. Only equipment, process, checklist and handover knowledge.",
        "labels": {"asset": "Equipment", "assets": "Equipment", "person": "Staff member", "record": "Equipment issue", "problem": "Issue",
                   "code": "Alarm", "downtime": "Out of service"},
        "cost_per_hour": 4000,
        "sites": [{"id": "blr", "name": "Bengaluru main hospital"}, {"id": "mys", "name": "Mysuru branch"}],
        "roles": [
            {"id": "nurse", "name": "ICU nurse", "can_approve": False, "tools": ["ask", "log", "quiz", "checklist"]},
            {"id": "ot", "name": "Neurosurgery OT team", "can_approve": False, "tools": ["checklist", "ask", "log", "quiz"]},
            {"id": "biomed", "name": "Biomedical engineer (senior)", "can_approve": True, "tools": ["ask", "log", "memory", "approvals", "playbook", "risk", "interview", "shift", "skills", "passport", "stats", "devices", "checklist", "quiz"]},
            {"id": "incharge", "name": "Nursing in-charge", "can_approve": True, "tools": ["ask", "memory", "approvals", "shift", "risk", "interview", "skills", "passport", "stats", "checklist", "quiz", "log", "playbook", "devices"]},
        ],
        "tools": ["checklist", "devices"],
        "safety_line": "Patient safety first: switch to the backup device before troubleshooting, and follow the manufacturer's instructions.",
        "generic": {"default": ["Switch to the backup device", "Run the device self-test", "Check power, cables and consumables", "Call biomedical engineering"],
                    "ventilator": ["Connect the backup ventilator first", "Check filters and tubing", "Run the self-test", "Call biomedical engineering"]},
        "questions": ["VNT-2 shows high blower temperature alarm at night", "Bowie-Dick test sheet shows uneven colour this morning",
                      "Which equipment was out of service the longest?", "Navigation accuracy is off after draping"],
        "interview_extra": [
            {"topic": "Early warnings", "question": "Which small signs tell you a device is about to fail, before it alarms?", "why": "These habits are rarely written down."},
            {"topic": "Vendors", "question": "Which vendor engineer or part number do you call for each device, and what do you check before calling?", "why": "Contacts and pre-checks leave with the person."}],
        "assets": assets, "people": people, "records": R, "tips": T, "public": public,
        "panels": [
            {"id": "fda-problems", "title": f"Most reported device problems (FDA, {len(fda['reports'])} ventilator & infusion pump reports)", "type": "bar",
             "data": {"labels": [x["problem"] for x in fda["top_problems"][:10]], "values": [x["count"] for x in fda["top_problems"][:10]]},
             "source": fda.get("source")},
        ],
        "checklists": [{
            "title": "WHO Surgical Safety Checklist + Neuro OT additions", "source": "WHO Surgical Safety Checklist (2009). Lines marked 'Neuro OT' are this demo hospital's own additions.",
            "phases": [
                {"name": "Sign In — before anaesthesia", "items": ["Patient has confirmed identity, site, procedure and consent", "Site marked", "Anaesthesia safety check completed",
                                                                  "Pulse oximeter on the patient and working", "Known allergy?", "Difficult airway or aspiration risk?",
                                                                  "Risk of >500 ml blood loss (7 ml/kg in children)?"]},
                {"name": "Time Out — before skin incision", "items": ["All team members introduced by name and role", "Confirm patient name, procedure and where the incision will be made",
                                                                     "Antibiotic prophylaxis given within the last 60 minutes?", "Anticipated critical events reviewed (surgeon, anaesthetist, nursing)",
                                                                     "Sterility (including indicator results) confirmed; any equipment issues?", "Essential imaging displayed",
                                                                     "Neuro OT: side confirmed on the displayed scan", "Neuro OT: navigation accuracy checked on a landmark", "Neuro OT: microscope draped, balanced, backup lamp OK"]},
                {"name": "Sign Out — before the patient leaves the OT", "items": ["Name of the procedure recorded", "Instrument, sponge and needle counts complete",
                                                                                 "Specimen labelled (with patient name)", "Equipment problems to be addressed",
                                                                                 "Key concerns for recovery handed over", "Neuro OT: any equipment issue logged in Ustaad"]},
            ]}],
    }
