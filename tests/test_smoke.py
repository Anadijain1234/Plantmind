"""Smoke tests: every industry, every main endpoint, offline (no keys needed).  Run:  python -m pytest -q  or  python tests/test_smoke.py"""
import os
import sys
import tempfile
from pathlib import Path

# empty values (not just removed): the app reads .env with setdefault, so this keeps tests offline even if .env has real keys
for _k in ("HINDSIGHT_API_KEY", "GROQ_API_KEY", "SARVAM_API_KEY", "GITHUB_TOKEN", "GITHUB_REPO"):
    os.environ[_k] = ""
os.environ["DB_PATH"] = str(Path(tempfile.mkdtemp()) / "test.db")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import app as A  # noqa: E402

C = A.app.test_client()
ASKS = {"factory": ("CNC-3", "alarm 2041 whistling sound at high rpm"), "restaurant": ("BRY-2", "biryani rice mushy after new rice bag"),
        "healthcare": ("VNT-2", "high blower temperature alarm"), "garage": ("PH-H", "P0171 rough idle"),
        "it": ("PG-2", "too many clients after scaling pods")}


def get(u):
    r = C.get(u)
    assert r.status_code == 200, (u, r.status_code, r.data[:200])
    return r.get_json()


def post(u, b):
    r = C.post(u, json=b)
    assert r.status_code == 200, (u, r.status_code, r.data[:200])
    return r.get_json()


def test_all_industries():
    inds = [i["id"] for i in get("/api/industries")["industries"]]
    assert inds == ["factory", "restaurant", "healthcare", "garage", "it"]
    for ind, (aid, q) in ASKS.items():
        pk = get(f"/api/i/{ind}/pack")
        a = post(f"/api/i/{ind}/ask", {"asset_id": aid, "problem": q})
        assert a["trust"]["level"] == "verified", (ind, a["trust"])
        assert a["memories"] and a["answer"]["steps"]
        off = post(f"/api/i/{ind}/ask", {"asset_id": aid, "problem": q, "use_memory": False})
        assert off["trust"]["level"] == "off" and not off["memories"]
        ch = post(f"/api/i/{ind}/ask", {"asset_id": aid, "problem": "Which one lost the most downtime hours?"})
        assert ch["mode"] == "chart" and ch["chart"]["values"]
        fb = post(f"/api/i/{ind}/feedback", {"ask_id": a["ask_id"], "result": "fixed", "person_id": pk["people"][-1]["id"], "downtime_minutes": 10})
        assert "Saved" in fb["message"]
        for path in ("risk", "stats", "quiz", "pending", "skills", "repeat", "cross-site", "shift-report", "memories"):
            get(f"/api/i/{ind}/{path}")
        get(f"/api/i/{ind}/passport/{pk['people'][0]['id']}")
        get(f"/api/i/{ind}/interview?person_id={pk['people'][0]['id']}")
        probs = get(f"/api/i/{ind}/problems?asset_id={aid}")["problems"]
        assert post(f"/api/i/{ind}/playbook", {"asset_id": aid, "problem": probs[0]["problem"]})["steps"]
        sl = post(f"/api/i/{ind}/smart-log", {"text": f"{aid} problem came again, fixed in 20 min", "person_id": pk["people"][-1]["id"]})
        key = sl["record"]["id"]
        approver = next(r for r in pk["roles"] if r["can_approve"])
        assert post(f"/api/i/{ind}/approve", {"key": key, "role": approver["id"], "approver_id": pk["people"][0]["id"]})["ok"]
        worker = next(r for r in pk["roles"] if not r["can_approve"])
        assert C.post(f"/api/i/{ind}/approve", json={"key": key, "role": worker["id"], "approver_id": "x"}).status_code == 403


def test_factory_extras():
    s = get("/api/factory/sensors")
    assert s["alerts"] and s["alerts"][0]["asset_id"] == "CNC-3"
    assert get("/api/factory/fleet")["model_card"]["test_auc"] > 0.8
    assert len(get("/api/factory/ai4i")["modes"]) == 5


def test_machines_parts_sensors():
    ms = get("/api/i/factory/machines")["machines"]
    assert any(m["id"] == "CNC-3" for m in ms)
    prof = get("/api/i/factory/machines/CNC-3")
    assert prof["parts"] and prof["service_due"] and prof["health"]["level"] in ("green", "amber", "red")
    # worker cannot add, senior can (typed in, no AI needed)
    assert C.post("/api/i/factory/machines", json={"machine": {"id": "CNC-9", "name": "Test VMC"}, "role": "technician"}).status_code == 403
    draft = post("/api/i/factory/machines/read", {"text": "Vertical machining centre VMC 1050\nSupply voltage: 380 V\nSpindle speed: 8000 rpm\nTable size: 1200 x 500 mm"})
    assert draft["specs"]
    r = post("/api/i/factory/machines", {"machine": {**draft, "id": "CNC-9", "is_new": True, "name": "Test VMC", "site": "blr",
             "components": [{"name": "Way cover wiper", "every_days": 90, "stock": 2}],
             "faults": [{"title": "Air pressure low", "code": "7000002", "fix": "Check the air supply is above 6 bar"}]},
             "role": "supervisor", "person_id": "imran"})
    assert r["asset"]["id"] == "CNC-9" and r["manual_memories"] >= 2
    a = post("/api/i/factory/ask", {"asset_id": "CNC-9", "problem": "alarm 7000002 air pressure low"})
    assert any(m["kind"] == "manual" for m in a["memories"]), a["memories"]
    # spare parts warning in the answer
    a = post("/api/i/factory/ask", {"asset_id": "CNC-3", "problem": "alarm 2041 whistling sound at high rpm"})
    assert any(x["status"] == "out" for x in a["answer"]["parts_status"])
    # sensor auto-log -> feedback finishes it -> normal readings confirm it
    al = post("/api/i/factory/sensors/alert", {"asset_id": "CNC-3", "reading": {"vib": 7.8, "temp": 60}})
    a = post("/api/i/factory/ask", {"asset_id": "CNC-3", "problem": "spindle vibration rising"})
    fb = post("/api/i/factory/feedback", {"ask_id": a["ask_id"], "result": "fixed", "person_id": "arjun", "action_done": "realigned coupling"})
    assert fb["record"]["id"] == al["record"]["id"]
    for v in (2.0, 2.1, 1.9):
        rd = post("/api/i/factory/sensors/reading", {"asset_id": "CNC-3", "vib": v, "temp": 40})
    assert rd["confirmed_record"] == al["record"]["id"]
    # didn't work -> expert suggestion
    a = post("/api/i/factory/ask", {"asset_id": "HYD-1", "problem": "ram slow, oil hot"})
    fb = post("/api/i/factory/feedback", {"ask_id": a["ask_id"], "result": "failed_again", "person_id": "arjun"})
    assert fb["expert"] and fb["expert"]["name"]


def test_teammate_features():
    for ind in ("factory", "restaurant", "healthcare", "garage", "it"):
        roi = get(f"/api/i/{ind}/stats")["roi"]
        assert {"hours_saved", "repeat_failures_avoided", "fixed_rate", "money_saved"} <= set(roi)
        cov = get(f"/api/i/{ind}/coverage")
        assert cov["machines"] and all(0 <= m["score"] <= 100 for m in cov["machines"])
        lb = get(f"/api/i/{ind}/leaderboard")
        assert lb["people"] and lb["people"][0]["rank"] == 1 and any(p["badges"] for p in lb["people"])
    assert any("Only" in f for m in get("/api/i/factory/coverage")["machines"] for f in m["flags"])


def test_relevance_cross_machine():
    a = post("/api/i/factory/ask", {"asset_id": "CNC-1", "problem": "low pallet clamp pressure"})
    used = [m for m in a["memories"] if m["used"]]
    assert used and all("pallet" in (m["problem"] or "").lower() or m["kind"] == "tip" for m in used[:3]), [m["problem"] for m in used]


def test_healthcare_guard():
    pk = get("/api/i/healthcare/pack")
    assert "diagnosis" in pk["banner"].lower()


if __name__ == "__main__":
    test_all_industries(); test_factory_extras(); test_machines_parts_sensors(); test_teammate_features(); test_relevance_cross_machine(); test_healthcare_guard()
    print("All smoke tests passed.")
