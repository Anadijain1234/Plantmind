"""
"Build your own industry": type a name (e.g. "bakery") and Ustaad creates a new industry pack —
roles, equipment, starter questions — with an EMPTY memory. Then it learns from zero as people log work.
"""
import json
import re
from datetime import date

from . import config, llm, packs, store
from .memory import memory

ICONS = ["🏢", "🧰", "🛠️", "📦", "⚙️"]


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:24] or "custom"


def _code(name, i):
    letters = re.sub(r"[^A-Za-z]", "", name).upper()[:3] or "EQP"
    return f"{letters}-{i}"


def create(name, description=""):
    name = (name or "").strip()
    if len(name) < 3:
        raise ValueError("Please type an industry name, e.g. bakery, textile mill, solar farm")
    pid = "custom-" + _slug(name)
    data = None
    if llm.available():
        data = llm.chat_json(
            "You design a starter configuration for an expert-knowledge app in a new industry in India. Practical and realistic. "
            'Return ONLY JSON: {"name": "short industry name", "icon": "one emoji", "tagline": "one line: whose know-how it keeps", '
            '"org_name": "a fictional Indian business name + (demo)", "labels": {"asset": "singular word for the things that break or need skill", '
            '"assets": "plural", "person": "worker word", "problem": "Problem", "code": "Code", "downtime": "Time lost"}, '
            '"assets": [{"name": "...", "model": "...", "type": "..."}] (5 items), '
            '"people": [{"name": "Indian name", "role": "...", "experience_years": 0, "senior": true}] (3 items, first is a senior about to retire), '
            '"questions": ["realistic problem a junior would ask"] (4 items), "generic_steps": ["general first steps"] (4 items), '
            '"safety_line": "one safety line", "interview": [{"topic": "...", "question": "...", "why": "..."}] (2 items)}',
            f"Industry: {name}\nDetails: {description or '-'}")
    if not isinstance(data, dict) or not data.get("assets"):
        data = {"name": name.title(), "icon": ICONS[len(name) % len(ICONS)], "tagline": f"The senior expert's know-how for every {name} shift",
                "org_name": f"{name.title()} Co. (demo)",
                "labels": {"asset": "Equipment", "assets": "Equipment", "person": "Worker", "problem": "Problem", "code": "Code", "downtime": "Time lost"},
                "assets": [{"name": f"Main line {i}", "model": "Standard", "type": "Equipment"} for i in (1, 2, 3)],
                "people": [{"name": "Senior expert", "role": "Senior (retiring)", "experience_years": 25, "senior": True},
                           {"name": "Supervisor", "role": "Supervisor", "experience_years": 8, "senior": True},
                           {"name": "New joiner", "role": "Junior", "experience_years": 0.2, "senior": False}],
                "questions": [f"Main line 1 stopped suddenly", "Quality dropped on the morning batch", "What should I check first?", "Which problem took the most time?"],
                "generic_steps": ["Stop safely", "Check power and basics", "Check recent changes", "Ask the senior expert"],
                "safety_line": "Stop and make it safe before you touch anything.", "interview": []}
    labels = {"asset": "Equipment", "assets": "Equipment", "person": "Worker", "record": "Work record", "problem": "Problem", "code": "Code", "downtime": "Time lost"}
    labels.update({k: v for k, v in (data.get("labels") or {}).items() if isinstance(v, str) and v})
    assets = []
    for i, a in enumerate(data["assets"][:6], 1):
        assets.append({"id": _code(data.get("name", name), i), "name": str(a.get("name", f"Item {i}"))[:60], "model": str(a.get("model", "Standard"))[:40],
                       "type": str(a.get("type", labels["asset"]))[:40], "type_key": _slug(a.get("type", "general")), "site": "main", "cost_per_hour": 2000})
    people = []
    for i, p in enumerate((data.get("people") or [])[:4]):
        people.append({"id": _slug(p.get("name", f"person{i}")).replace("-", "")[:12] or f"p{i}", "name": str(p.get("name", f"Person {i + 1}"))[:40],
                       "short": str(p.get("name", "")).split(" ")[0], "role": str(p.get("role", ""))[:60], "site": "main",
                       "experience_years": float(p.get("experience_years") or 1), "retiring_on": "2027-03-31" if i == 0 else None,
                       "speciality": str(p.get("role", ""))[:60]})
    pack = {
        "id": pid, "name": str(data.get("name", name))[:30], "icon": str(data.get("icon", "🏢"))[:4], "color": "#0E7490",
        "tagline": str(data.get("tagline", ""))[:90], "custom": True,
        "org": {"name": str(data.get("org_name", name.title() + " (demo)"))[:60],
                "note": "Created just now with 'Build your own industry'. Memory starts empty — log work and watch Ustaad learn.",
                "ustaad_started": date.today().isoformat()},
        "labels": labels, "cost_per_hour": 2000, "sites": [{"id": "main", "name": "Main site"}],
        "roles": [
            {"id": "worker", "name": labels["person"], "can_approve": False, "tools": ["ask", "log", "memory", "playbook", "quiz", "passport"]},
            {"id": "senior", "name": "Senior / supervisor", "can_approve": True,
             "tools": ["ask", "log", "memory", "approvals", "playbook", "risk", "interview", "shift", "skills", "passport", "stats", "quiz"]}],
        "tools": [], "safety_line": str(data.get("safety_line", ""))[:160],
        "generic": {"default": [str(s)[:120] for s in (data.get("generic_steps") or ["Check the basics"])][:6]},
        "questions": [str(q)[:120] for q in (data.get("questions") or [])][:4] or ["What should I check first?"],
        "interview_extra": [x for x in (data.get("interview") or []) if isinstance(x, dict) and x.get("question")][:3],
        "assets": assets, "people": people, "records": [], "tips": [], "public": [], "panels": [],
    }
    config.CUSTOM_PACKS_DIR.mkdir(parents=True, exist_ok=True)
    (config.CUSTOM_PACKS_DIR / f"{pid}.json").write_text(json.dumps(pack, indent=1, ensure_ascii=False), encoding="utf-8")
    packs.reload()
    store.init()
    if memory.cloud:
        try:
            memory.cloud.setup_bank(pid)
        except Exception as e:  # bank may already exist
            memory.last_error = f"Hindsight bank for {pid}: {e}"
    return {"id": pid, "name": pack["name"], "generated_by": "Groq LLM" if llm.available() else "template (no LLM key)"}
