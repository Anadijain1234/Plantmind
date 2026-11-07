"""Helpers shared by the pack builders."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"


def processed(name):
    p = PROCESSED / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def rec(id, dt, asset, person, problem, symptom, cause, action, outcome="fixed", mins=60, code="", parts="", cost=0,
        notes="", source_ref="", status="approved"):
    return {"id": id, "datetime": dt, "asset_id": asset, "person_id": person, "problem": problem, "code": code,
            "symptom": symptom, "cause": cause, "action": action, "parts": parts, "cost": cost,
            "downtime_minutes": mins, "outcome": outcome, "notes": notes, "source_ref": source_ref, "status": status}


def tip(id, person, asset, date, text, source_ref="", status="approved"):
    return {"id": id, "person_id": person, "asset_id": asset, "date": date, "text": text, "source_ref": source_ref,
            "status": status}


def add_credits(pack):
    """After Ustaad started, when someone fixes a problem that another person solved first, credit the first solver."""
    start = pack["org"]["ustaad_started"]
    first = {}
    for r in sorted(pack["records"], key=lambda x: x["datetime"]):
        model = next((a.get("model") for a in pack["assets"] if a["id"] == r["asset_id"]), r["asset_id"])
        k = (model, r["problem"])
        if r["outcome"] == "fixed" and k not in first:
            first[k] = r["person_id"]
        elif r["outcome"] == "fixed" and r["datetime"][:10] >= start and first.get(k) and first[k] != r["person_id"]:
            r["credited_to"] = first[k]
    return pack
