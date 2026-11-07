"""Restaurant pack: Kaveri Kitchens — two outlets (Indiranagar, Koramangala)."""
from .common import processed, rec, tip


def build():
    assets = [
        {"id": "TND-1", "name": "Tandoor (Indiranagar)", "model": "Charcoal clay tandoor", "type": "Tandoor", "type_key": "tandoor", "site": "ind", "cost_per_hour": 3000},
        {"id": "TND-2", "name": "Tandoor (Koramangala)", "model": "Charcoal clay tandoor", "type": "Tandoor", "type_key": "tandoor", "site": "kor", "cost_per_hour": 3000},
        {"id": "BRY-1", "name": "Dum biryani station (Indiranagar)", "model": "Dum handi", "type": "Biryani", "type_key": "biryani", "site": "ind", "cost_per_hour": 5000},
        {"id": "BRY-2", "name": "Dum biryani station (Koramangala)", "model": "Dum handi", "type": "Biryani", "type_key": "biryani", "site": "kor", "cost_per_hour": 5000},
        {"id": "FRY-1", "name": "Deep fryer 20 L (Indiranagar)", "model": "20 L fryer", "type": "Fryer", "type_key": "fryer", "site": "ind", "cost_per_hour": 2000},
        {"id": "DOS-1", "name": "Dosa tawa (Koramangala)", "model": "Cast-iron tawa", "type": "Tawa", "type_key": "tawa", "site": "kor", "cost_per_hour": 2500},
        {"id": "GRV-1", "name": "Gravy station — makhani & curry base (Indiranagar)", "model": "Gravy station", "type": "Gravy", "type_key": "gravy", "site": "ind", "cost_per_hour": 2500},
        {"id": "COLD-1", "name": "Walk-in cold room (Indiranagar)", "model": "Walk-in cold room", "type": "Cold storage", "type_key": "cold", "site": "ind", "cost_per_hour": 1500},
    ]
    people = [
        {"id": "joseph", "name": "Chef Joseph D'Souza", "short": "Chef Joseph", "role": "Head Chef (both outlets)", "site": "ind",
         "experience_years": 26, "retiring_on": "2027-03-31", "speciality": "Biryani, tandoor, gravies — leaving to open his own place"},
        {"id": "meena", "name": "Meena Shetty", "short": "Meena", "role": "Sous Chef (Koramangala)", "site": "kor",
         "experience_years": 9, "retiring_on": None, "speciality": "South Indian, dosa, cold kitchen"},
        {"id": "ravi", "name": "Ravi Kumar", "short": "Ravi", "role": "Line Cook (joined Aug 2026)", "site": "ind",
         "experience_years": 0.3, "retiring_on": None, "speciality": "Learning — uses Ustaad on every shift"},
    ]
    R = [
        rec("r-001", "2026-05-14T13:10", "BRY-1", "joseph", "Biryani rice mushy", "Rice grains breaking and sticking after dum, new rice bag",
            "New-crop rice absorbs less water than aged rice", "Cut boiling water 10%; soaked only 20 minutes; drained rice at 70% cooked before layering", mins=40),
        rec("r-002", "2026-05-28T13:05", "BRY-2", "meena", "Biryani rice mushy", "Mushy rice on the lunch batch after changing supplier",
            "Assumed overcooking", "Reduced dum time from 25 to 15 minutes", outcome="failed_again", mins=45, notes="Rice still mushy next day."),
        rec("r-003", "2026-05-29T12:40", "BRY-2", "joseph", "Biryani rice mushy", "Same mushy rice, second day",
            "New-crop rice absorbs less water than aged rice", "Cut boiling water 10%; soaked only 20 minutes; drained rice at 70% cooked; kept dum at 25 minutes", mins=30),
        rec("r-004", "2026-06-07T20:15", "TND-1", "joseph", "Naan hard and chewy", "Customers sending back naan as hard; naan not puffing",
            "Tandoor wall not hot enough — charcoal damp in monsoon", "Kept charcoal in a closed dry bin; preheated tandoor 45 minutes; slapped naan only when the wall sizzled with water", mins=50),
        rec("r-005", "2026-06-19T19:50", "TND-2", "meena", "Naan hard and chewy", "Naan dense and chewy on a rainy evening",
            "Dough over-kneaded and not rested", "Rested dough longer", outcome="temporary", mins=35, notes="Better for one day, problem came back with rain."),
        rec("r-006", "2026-07-02T20:05", "FRY-1", "joseph", "Fried items bitter / oil foaming", "Pakoras dark and bitter, oil foaming and smoking early",
            "Oil reused too long — polar compounds high", "Tested oil with TPC meter: 27%. Discarded oil, filtered daily after service, changed oil when TPC near 24%", mins=25,
            source_ref="FSSAI used cooking oil rule (TPC 25%)"),
        rec("r-007", "2026-07-15T21:30", "COLD-1", "joseph", "Cold room above 5 °C", "Cold room showing 8 °C during dinner rush",
            "Door left open during rush; door gasket torn at the bottom", "Replaced door gasket; hung strip curtain; set a 'door closed' check every hour", mins=120, parts="Door gasket, strip curtain", cost=6500),
        rec("r-008", "2026-07-22T08:40", "DOS-1", "meena", "Dosa sticking to tawa", "Dosa tearing and sticking on the morning batch",
            "Tawa too hot and seasoning lost after washing with soap", "Did water-sprinkle test (drops should sizzle and vanish in 2-3 seconds); re-seasoned tawa with half onion and oil; never soap-washed again", mins=30),
        rec("r-009", "2026-08-03T19:20", "GRV-1", "joseph", "Makhani gravy splitting", "Butter-cream gravy separating into oil and water",
            "Cream added to boiling gravy", "Took gravy off flame; whisked in cream at low heat; finished with cold butter cubes", mins=20),
        rec("r-010", "2026-08-12T20:40", "GRV-1", "joseph", "Paneer hard / rubbery", "Paneer tikka masala sent back as rubbery",
            "Paneer added early and boiled in gravy", "Soaked paneer in hot salted water for 10 minutes; added it only in the last 2 minutes", mins=15),
        rec("r-011", "2026-09-06T13:00", "BRY-1", "ravi", "Biryani rice mushy", "Mushy biryani on Saturday lunch, new rice bag opened",
            "New-crop rice absorbs less water than aged rice", "Followed Chef Joseph's fix from Ustaad: cut boiling water 10%; soaked 20 min; drained at 70% cooked", mins=15),
        rec("r-012", "2026-09-20T20:10", "TND-2", "meena", "Naan hard and chewy", "Hard naan on a rainy Friday",
            "Tandoor wall not hot enough — charcoal damp", "Followed Chef Joseph's fix from Ustaad: dry charcoal bin; preheat 45 min; sizzle test on wall", mins=20),
        rec("r-013", "2026-10-04T19:35", "FRY-1", "ravi", "Fried items bitter / oil foaming", "Samosas darkening fast on Thursday dinner",
            "Oil reused too long — polar compounds high", "Tested TPC: 25%. Changed oil; started daily filtering", mins=15),
        rec("r-014", "2026-10-18T21:00", "COLD-1", "ravi", "Cold room above 5 °C", "Cold room at 7 °C after delivery unloading",
            "Door propped open during supplier delivery", "Unloaded into trolleys outside; kept door shut; temperature back to 3 °C in 40 min", mins=40),
        rec("r-015", "2026-10-29T13:20", "BRY-2", "meena", "Biryani bland", "Customers say biryani tastes flat even though masala is same",
            "Rice boiling water not salted enough", "Salted the rice water until it tasted clearly salty, then layered as usual", mins=10),
        rec("r-016", "2026-11-05T20:30", "TND-1", "ravi", "Naan hard and chewy", "Naan hard after a long rain day", "Damp charcoal",
            "Moved charcoal to the dry bin; preheated 45 min", mins=20, status="pending"),
    ]
    T = [
        tip("tr-01", "joseph", "FRY-1", "2026-07-03",
            "Never judge fryer oil by its colour. Test it with a TPC meter at closing. FSSAI says oil above 25% total polar compounds must not be used — "
            "we change it at 24% so we never cross the line.", "FSSAI used cooking oil rule (TPC 25%)"),
        tip("tr-02", "joseph", "COLD-1", "2026-07-16",
            "Hot food must stay at 60 °C or above and cold food at 5 °C or below. Between 5 and 60 °C bacteria grow fast — in NYC inspections of Indian "
            "restaurants, wrong holding temperature is among the most common violations.", "NYC Health inspections (cold ≤41 °F/5 °C, hot ≥140 °F/60 °C)"),
        tip("tr-03", "joseph", "BRY-1", "2026-05-15",
            "When a new bag of rice comes, cook one small test batch first. New-crop rice needs about 10% less water than aged basmati, or the biryani turns mushy."),
        tip("tr-04", "joseph", "TND-1", "2026-06-08",
            "In monsoon keep charcoal in a closed dry bin. Preheat the tandoor 45 minutes; flick water on the wall — if it does not sizzle at once, don't slap the naan yet."),
        tip("tr-05", "meena", "DOS-1", "2026-07-23",
            "Sprinkle water on the tawa before every batch: drops should dance and vanish in 2-3 seconds. Never wash the tawa with soap; wipe and season with half an onion and oil."),
        tip("tr-06", "joseph", "GRV-1", "2026-08-13",
            "Paneer goes rubbery when it boils. Soak it in hot salted water for 10 minutes and add it to gravy only in the last 2 minutes."),
    ]
    insp = processed("restaurant_inspections.json") or {"top_violations": []}
    comp = processed("restaurant_complaints.json") or {"dishes": [], "issues_total": []}
    dishes = processed("restaurant_dishes.json") or {"dishes": []}
    type_for = lambda text: ("cold" if "cold" in text.lower() or "41" in text else "hot" if "140" in text else
                             "hygiene")
    public = [{"id": f"nyc-{i + 1:02d}", "title": f"NYC inspections of Indian restaurants: {v['count']} violations — " + ("CRITICAL" if v["critical"] else "general"),
               "text": v["text"], "fix": "", "source": "NYC Health restaurant inspections", "date": insp.get("date_range", ["2022-01-01"])[1],
               "type_key": "cold" if type_for(v["text"]) == "cold" else "hygiene", "outcome": "open",
               "url": "https://data.cityofnewyork.us/Health/DOHMH-New-York-City-Restaurant-Inspection-Results/43nn-pn8j"}
              for i, v in enumerate(insp["top_violations"])]
    key_for = {"Biryani": "biryani", "Naan / roti": "tandoor", "Dosa": "tawa", "Idli": "tawa", "Vada": "fryer", "Paneer dishes": "gravy",
               "Butter chicken": "gravy", "Tikka": "tandoor", "Kebab": "tandoor", "Dal": "gravy", "Chaat": "fryer"}
    for d in comp["dishes"]:
        if not d["issues"]:
            continue
        iss = ", ".join(f"{x['issue']} ({x['count']})" for x in d["issues"][:3])
        public.append({"id": f"zom-{d['dish'].lower().replace(' / ', '-').replace(' ', '-')}", "title": f"Bengaluru customers on {d['dish']}: {d['low_rated']:,} low-rated reviews",
                       "text": f"{d['mentions']:,} Zomato reviews mention {d['dish']}. Most common complaints in low-rated ones: {iss}.", "fix": "",
                       "source": "Zomato Bangalore reviews (Kaggle)", "date": "2019-03-01", "type_key": key_for.get(d["dish"], "general"), "outcome": "open", "url": ""})
    return {
        "id": "restaurant", "name": "Restaurant", "icon": "🍛", "color": "#C2410C",
        "tagline": "The head chef's tricks, for every cook on every shift",
        "org": {"name": "Kaveri Kitchens (demo)", "note": "Demo restaurant with two outlets in Bengaluru. People are fictional; food-safety facts and data are real.",
                "ustaad_started": "2026-09-01"},
        "labels": {"asset": "Station", "assets": "Stations", "person": "Cook", "record": "Kitchen issue", "problem": "Issue",
                   "code": "Ticket", "downtime": "Time lost"},
        "cost_per_hour": 3000,
        "sites": [{"id": "ind", "name": "Indiranagar outlet"}, {"id": "kor", "name": "Koramangala outlet"}],
        "roles": [
            {"id": "cook", "name": "Line cook", "can_approve": False, "tools": ["ask", "log", "memory", "playbook", "quiz", "passport", "dishes"]},
            {"id": "chef", "name": "Head chef", "can_approve": True, "tools": ["ask", "log", "memory", "approvals", "playbook", "risk", "interview", "shift", "skills", "passport", "stats", "quiz", "dishes"]},
            {"id": "manager", "name": "Outlet manager", "can_approve": True, "tools": ["stats", "risk", "shift", "skills", "passport", "ask", "memory", "approvals", "playbook", "interview", "quiz", "dishes"]},
        ],
        "tools": ["dishes"],
        "safety_line": "Hot food at 60 °C or above, cold food at 5 °C or below. Wash hands before and after handling raw food.",
        "generic": {"default": ["Taste and adjust seasoning", "Check the recipe card", "Check ingredient freshness", "Ask the head chef"],
                    "biryani": ["Check the rice-to-water ratio", "Check dum time", "Check the seal on the handi", "Ask the head chef"],
                    "tandoor": ["Check the tandoor temperature", "Check dough resting time", "Ask the head chef"]},
        "questions": ["Biryani rice is coming out mushy after we opened a new rice bag", "Naan is hard and chewy tonight",
                      "Which station lost the most time?", "Pakoras taste bitter and the oil is foaming"],
        "interview_extra": [
            {"topic": "Signature taste", "question": "Which small step makes our signature dishes taste like yours, that is not on the recipe card?", "why": "Signature taste is the knowledge customers notice first."},
            {"topic": "Suppliers", "question": "How do you judge a new batch of rice, spices or paneer before using it?", "why": "Quality checks on arrival are rarely written down."}],
        "assets": assets, "people": people, "records": R, "tips": T, "public": public,
        "panels": [
            {"id": "complaints", "title": f"What Bengaluru customers complain about (Zomato, {comp.get('reviews_scanned', 0):,} reviews scanned)", "type": "bar",
             "data": {"labels": [x["issue"] for x in comp["issues_total"]], "values": [x["count"] for x in comp["issues_total"]]},
             "source": comp.get("source")},
            {"id": "inspections", "title": f"Most common inspection violations — {insp.get('restaurants', 0)} Indian restaurants in NYC", "type": "list",
             "data": [{"text": v["text"], "count": v["count"], "critical": v["critical"]} for v in insp["top_violations"][:8]],
             "source": insp.get("source")},
        ],
        "lookup": {"type": "dishes", "title": "Dish facts (Indian Food 101)", "source": dishes.get("source"), "items": dishes["dishes"]},
    }
