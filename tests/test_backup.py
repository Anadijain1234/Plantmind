"""Auto-save test with a fake GitHub: save on one server, 'redeploy' to a fresh one, check everything comes back,
and check that a GitHub outage never overwrites good data.  Run:  python tests/test_backup.py"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STEP = r'''
import os, sys, time
sys.path.insert(0, {root!r}); sys.path.insert(0, {tests!r})
import fake_github
fake_github.DOWN["v"] = {down}
from ustaad import backup
backup._api = fake_github.api
import app as A
C = A.app.test_client()
if {first}:
    assert C.post("/api/i/factory/machines", json={{"machine": {{"id": "CNC-4", "is_new": True, "name": "VMC 1050", "site": "blr",
        "components": [{{"name": "Way cover wiper", "stock": 3}}]}}, "role": "supervisor", "person_id": "imran"}}).status_code == 200
    assert C.post("/api/i/factory/machines/CNC-3/stock", json={{"part": "Coupling spider", "stock": 5}}).status_code == 200
    assert backup.save_now() and backup.status()["saves"] >= 1
else:
    ids = [m["id"] for m in C.get("/api/i/factory/machines").get_json()["machines"]]
    if {down}:
        assert "CNC-4" not in ids and backup.save_now() is False  # paused: never overwrite good data
    else:
        assert "CNC-4" in ids, ids
        assert [c["stock"] for c in C.get("/api/i/factory/machines/CNC-3").get_json()["parts"] if c["name"] == "Coupling spider"] == [5]
print("ok")
'''


def run(tmp, name, first=False, down=False):
    env = {**os.environ, "GITHUB_TOKEN": "fake", "GITHUB_REPO": "me/repo", "DB_PATH": str(tmp / f"{name}.db"),
           "CUSTOM_PACKS_DIR": str(tmp / f"packs_{name}"), "FAKE_GITHUB_FILE": str(tmp / "github.json"),
           "HINDSIGHT_API_KEY": "", "GROQ_API_KEY": "", "SARVAM_API_KEY": ""}
    code = STEP.format(root=str(ROOT), tests=str(ROOT / "tests"), first=first, down=down)
    out = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=120)
    assert out.returncode == 0 and "ok" in out.stdout, out.stderr[-1500:]


def test_backup_roundtrip():
    tmp = Path(tempfile.mkdtemp())
    run(tmp, "server1", first=True)
    run(tmp, "server2")             # a fresh server after a redeploy gets everything back
    run(tmp, "server3", down=True)  # GitHub down at start: saving pauses, nothing is overwritten


if __name__ == "__main__":
    test_backup_roundtrip()
    print("Backup test passed.")
