"""
Industry packs. One engine, many industries: each industry is just a JSON file in data/packs/.
A pack says what the "things" are (machines, kitchen stations, ICU devices, cars, services), who the
people and roles are, the starting memories, public records, checklists and insight panels.
Adding an industry = adding one file. No code change.
"""
import json
from functools import lru_cache

from . import config

ORDER = ["factory", "restaurant", "healthcare", "garage", "it"]


def _dirs():
    return [config.PACKS_DIR] + ([config.CUSTOM_PACKS_DIR] if config.CUSTOM_PACKS_DIR != config.PACKS_DIR else [])


@lru_cache(maxsize=None)
def _load(industry):
    for d in _dirs():
        path = d / f"{industry}.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    return None


def reload():
    _load.cache_clear()


def ids():
    found = sorted({p.stem for d in _dirs() if d.exists() for p in d.glob("*.json")})
    return [i for i in ORDER if i in found] + [i for i in found if i not in ORDER]


def get(industry):
    p = _load(industry)
    if not p:
        raise ValueError(f"Unknown industry '{industry}'")
    return p


def summary(industry):
    p = get(industry)
    return {k: p.get(k) for k in ("id", "name", "icon", "color", "tagline", "labels", "org", "banner", "sites", "roles",
                                  "tools", "questions", "cost_per_hour", "coming_soon")} | {
        "counts": {"assets": len(p.get("assets", [])), "people": len(p.get("people", [])),
                   "records": len(p.get("records", [])), "tips": len(p.get("tips", [])),
                   "public": len(p.get("public", []))}}


def assets(industry):
    return get(industry).get("assets", [])


def asset(industry, aid):
    return next((a for a in assets(industry) if a["id"] == aid), None)


def people(industry):
    return get(industry).get("people", [])


def person(industry, pid):
    return next((x for x in people(industry) if x["id"] == pid), None)


def role(industry, rid):
    return next((r for r in get(industry).get("roles", []) if r["id"] == rid), None)


def site(industry, sid):
    return next((s for s in get(industry).get("sites", []) if s["id"] == sid), None)


def public_records(industry):
    return get(industry).get("public", [])


def public_record(industry, key):
    return next((x for x in public_records(industry) if x["id"] == key), None)


def processed(name):
    path = config.PROCESSED_DIR / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
