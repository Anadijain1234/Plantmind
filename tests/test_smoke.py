"""Smoke tests: every industry, every main endpoint, offline (no keys needed).  Run:  python -m pytest -q  or  python tests/test_smoke.py"""
import os
import sys
import tempfile
from pathlib import Path

os.environ.pop("HINDSIGHT_API_KEY", None)
os.environ.pop("GROQ_API_KEY", None)
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


def test_healthcare_guard():
    pk = get("/api/i/healthcare/pack")
    assert "diagnosis" in pk["banner"].lower()


if __name__ == "__main__":
    test_all_industries(); test_factory_extras(); test_healthcare_guard()
    print("All smoke tests passed.")
