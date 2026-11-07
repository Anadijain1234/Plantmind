"""
Auto-save: keeps everything people add on the live site (machines, work logs, tips, approvals, spare-part stock,
flags, sensor states, custom industries) in one JSON file in your GitHub repo — on a separate branch, so the code
stays clean — and loads it back when the server restarts or is redeployed.

Why: on free hosting the server's disk is wiped on every deploy. Knowledge also goes to Hindsight (permanent), but
exact lists and numbers (which machines exist, stock = 2, approved or not) need a notebook that survives.

Needs two environment variables on the server (never in code):
  GITHUB_TOKEN  a fine-grained token for this one repo with "Contents: Read and write"
  GITHUB_REPO   e.g. Anadijain1234/Plantmind
Optional: BACKUP_BRANCH (default ustaad-data), BACKUP_PATH (default ustaad-backup.json).
If they are missing, or GitHub can't be reached, the app works normally and the status shows why.
"""
import base64
import json
import os
import threading
from datetime import datetime

import requests

from . import config

API = "https://api.github.com"
TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
REPO = os.getenv("GITHUB_REPO", "").strip().strip("/")
BRANCH = os.getenv("BACKUP_BRANCH", "ustaad-data").strip() or "ustaad-data"
PATH = os.getenv("BACKUP_PATH", "ustaad-backup.json").strip() or "ustaad-backup.json"
DELAY = 4  # seconds: many saves close together become one GitHub commit

state = {"enabled": bool(TOKEN and REPO), "ready": False, "restored": None, "last_saved": None, "last_error": None,
         "saves": 0}
_lock = threading.Lock()   # one save at a time
_tlock = threading.Lock()  # scheduling
_timer = None
_sha = None


def _api(method, url, **kw):
    """One GitHub API call. Tests replace this function."""
    headers = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28", **kw.pop("headers", {})}
    return requests.request(method, API + url, headers=headers, timeout=20, **kw)


def status():
    return {k: state[k] for k in ("enabled", "ready", "restored", "last_saved", "last_error", "saves")} | {
        "where": f"github.com/{REPO} · branch {BRANCH} · {PATH}" if state["enabled"] else None}


# ---------- what is saved ----------
def export():
    from . import store
    with store._conn() as c:
        rows = lambda q: [dict(r) for r in c.execute(q)]  # noqa: E731
        data = {
            "version": 1, "saved_at": datetime.now().isoformat(timespec="seconds"),
            "records": rows("SELECT * FROM records WHERE COALESCE(source, 'seed') != 'seed'"),
            "tips": rows("SELECT * FROM tips WHERE COALESCE(source, 'seed') != 'seed'"),
            "machines": rows("SELECT * FROM machines"),
            "manual_items": rows("SELECT * FROM manual_items"),
            "flags": rows("SELECT * FROM flags"),
            "meta": [r for r in rows("SELECT * FROM meta") if r["key"].split(":")[0] in ("sensor", "sensorlog", "readings")],
        }
    d = config.CUSTOM_PACKS_DIR
    data["custom_packs"] = {p.name: p.read_text(encoding="utf-8") for p in sorted(d.glob("custom-*.json"))} if d.exists() else {}
    return data


def _apply(data):
    """Put a saved file back into the local database (no new save is triggered)."""
    from . import packs, store
    n = 0
    for name, text in (data.get("custom_packs") or {}).items():
        if name.startswith("custom-") and name.endswith(".json") and "/" not in name:
            config.CUSTOM_PACKS_DIR.mkdir(parents=True, exist_ok=True)
            (config.CUSTOM_PACKS_DIR / name).write_text(text, encoding="utf-8")
            n += 1
    packs.reload()
    tables = {"records": store.REC_FIELDS, "tips": store.TIP_FIELDS,
              "machines": ["industry", "id", "data", "created", "created_by"],
              "manual_items": ["id", "industry", "asset_id", "kind", "title", "text", "source_ref", "date"],
              "flags": ["memory_key", "industry", "reason", "flagged_by", "created"], "meta": ["key", "value"]}
    with store._lock, store._conn() as c:
        for table, cols in tables.items():
            for r in data.get(table) or []:
                c.execute(f"INSERT OR REPLACE INTO {table} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                          [r.get(k) for k in cols])
                n += 1
    store._machine_cache.clear()
    return n


# ---------- GitHub ----------
def _ensure_branch():
    r = _api("GET", f"/repos/{REPO}/branches/{BRANCH}")
    if r.status_code == 200:
        return
    if r.status_code != 404:
        raise RuntimeError(f"GitHub {r.status_code}: {r.text[:150]}")
    repo = _api("GET", f"/repos/{REPO}")
    repo.raise_for_status()
    base = repo.json()["default_branch"]
    ref = _api("GET", f"/repos/{REPO}/git/ref/heads/{base}")
    ref.raise_for_status()
    made = _api("POST", f"/repos/{REPO}/git/refs", json={"ref": f"refs/heads/{BRANCH}", "sha": ref.json()["object"]["sha"]})
    if made.status_code not in (201, 422):  # 422 = it already exists
        raise RuntimeError(f"Couldn't create branch {BRANCH}: GitHub {made.status_code}")


def restore():
    """At start: load the saved file back. Saving stays switched off until this succeeds (or there is no file yet),
    so a network hiccup can never overwrite good data with an empty copy."""
    global _sha
    if not state["enabled"] or state["ready"]:
        return state["restored"]
    try:
        r = _api("GET", f"/repos/{REPO}/contents/{PATH}", params={"ref": BRANCH})
        if r.status_code == 404:  # no backup yet (first run) — that's fine
            state.update(ready=True, restored=0, last_error=None)
            return 0
        r.raise_for_status()
        meta = r.json()
        _sha = meta.get("sha")
        raw = base64.b64decode(meta["content"]) if meta.get("content") else _api(
            "GET", f"/repos/{REPO}/contents/{PATH}", params={"ref": BRANCH},
            headers={"Accept": "application/vnd.github.raw+json"}).content
        n = _apply(json.loads(raw.decode("utf-8")))
        state.update(ready=True, restored=n, last_error=None)
        return n
    except Exception as e:
        state["last_error"] = f"Couldn't load the saved data from GitHub (saving paused): {str(e)[:160]}"
        return None


def save_now():
    global _sha
    if not state["enabled"]:
        return False
    with _lock:
        if not state["ready"] and restore() is None:
            return False
        try:
            body = json.dumps(export(), ensure_ascii=False, indent=1).encode("utf-8")
            for attempt in range(2):
                payload = {"message": f"Ustaad auto-save {datetime.now():%d %b %H:%M}", "branch": BRANCH,
                           "content": base64.b64encode(body).decode()}
                if _sha:
                    payload["sha"] = _sha
                r = _api("PUT", f"/repos/{REPO}/contents/{PATH}", json=payload)
                if r.status_code == 404 and attempt == 0:  # branch missing
                    _ensure_branch()
                    continue
                if r.status_code in (409, 422) and attempt == 0:  # our copy of the file version is old
                    g = _api("GET", f"/repos/{REPO}/contents/{PATH}", params={"ref": BRANCH})
                    _sha = g.json().get("sha") if g.status_code == 200 else None
                    continue
                r.raise_for_status()
                _sha = r.json()["content"]["sha"]
                state.update(last_saved=datetime.now().isoformat(timespec="seconds"), last_error=None,
                             saves=state["saves"] + 1)
                return True
        except Exception as e:
            state["last_error"] = f"Auto-save to GitHub failed: {str(e)[:160]}"
        return False


def mark_dirty():
    """Called after every change. Waits a few seconds so a burst of saves becomes one commit.
    A change that arrives while a save is running schedules the next save, so nothing is missed."""
    global _timer
    if not state["enabled"]:
        return
    with _tlock:
        if _timer is None:
            _timer = threading.Timer(DELAY, _run)
            _timer.daemon = True
            _timer.start()


def _run():
    global _timer
    with _tlock:
        _timer = None
    save_now()
