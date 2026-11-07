"""
SQLite store — the "scorebook". Exact copies of every work record, expert tip, answer, flag and approval,
for every industry. Hindsight is the memory that understands and searches; this store keeps the exact
numbers for charts, Risk Radar, trust levels and the feedback loop. Fresh start = load the packs' seed data.
"""
import json
import sqlite3
import threading
import uuid
from datetime import datetime

from . import backup, config, packs

_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS records (
    id TEXT PRIMARY KEY, industry TEXT, datetime TEXT, asset_id TEXT, person_id TEXT, problem TEXT, code TEXT,
    symptom TEXT, cause TEXT, action TEXT, parts TEXT, cost REAL, downtime_minutes REAL, outcome TEXT, notes TEXT,
    status TEXT DEFAULT 'approved', approved_by TEXT, source TEXT DEFAULT 'seed', source_ref TEXT,
    credited_to TEXT, steps_done TEXT
);
CREATE TABLE IF NOT EXISTS tips (
    id TEXT PRIMARY KEY, industry TEXT, person_id TEXT, asset_id TEXT, date TEXT, text TEXT, source_ref TEXT,
    status TEXT DEFAULT 'approved', approved_by TEXT, source TEXT DEFAULT 'seed'
);
CREATE TABLE IF NOT EXISTS asks (
    id TEXT PRIMARY KEY, industry TEXT, created TEXT, asset_id TEXT, problem TEXT, use_memory INTEGER, answer TEXT,
    top_person TEXT, top_key TEXT
);
CREATE TABLE IF NOT EXISTS flags (memory_key TEXT PRIMARY KEY, industry TEXT, reason TEXT, flagged_by TEXT, created TEXT);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS machines (industry TEXT, id TEXT, data TEXT, created TEXT, created_by TEXT, PRIMARY KEY (industry, id));
CREATE TABLE IF NOT EXISTS manual_items (
    id TEXT PRIMARY KEY, industry TEXT, asset_id TEXT, kind TEXT, title TEXT, text TEXT, source_ref TEXT, date TEXT
);
"""

REC_FIELDS = ["id", "industry", "datetime", "asset_id", "person_id", "problem", "code", "symptom", "cause", "action",
              "parts", "cost", "downtime_minutes", "outcome", "notes", "status", "approved_by", "source", "source_ref",
              "credited_to", "steps_done"]
TIP_FIELDS = ["id", "industry", "person_id", "asset_id", "date", "text", "source_ref", "status", "approved_by", "source"]


def _conn():
    c = sqlite3.connect(config.DB_PATH, check_same_thread=False, timeout=15)
    c.row_factory = sqlite3.Row
    return c


def init(force=False):
    with _lock, _conn() as c:
        c.executescript(SCHEMA)
        loaded = {r[0] for r in c.execute("SELECT DISTINCT industry FROM records")}
    for ind in packs.ids():
        if force or ind not in loaded:
            load_seed(ind)
        elif not meta_get(f"demo_machines:{ind}"):
            _demo_machines(ind)
    backup.restore()  # bring back what people added before the last restart / deploy
    for ind in packs.ids():  # custom industries that came back with the saved data
        if not records(ind) and packs.get(ind).get("records"):
            load_seed(ind)


def _demo_machines(industry):
    from . import machines  # late import (machines imports store)
    machines.load_demo(industry)
    meta_set(f"demo_machines:{industry}", {"loaded": now()})


def load_seed(industry):
    p = packs.get(industry)
    with _lock, _conn() as c:
        c.execute("DELETE FROM records WHERE industry=?", (industry,))
        c.execute("DELETE FROM tips WHERE industry=?", (industry,))
        for r in p.get("records", []):
            row = {"status": "approved", "source": "seed", **r, "industry": industry}
            c.execute(f"INSERT OR REPLACE INTO records ({','.join(REC_FIELDS)}) VALUES ({','.join('?' * len(REC_FIELDS))})",
                      [row.get(f) for f in REC_FIELDS])
        for t in p.get("tips", []):
            row = {"status": "approved", "source": "seed", **t, "industry": industry}
            c.execute(f"INSERT OR REPLACE INTO tips ({','.join(TIP_FIELDS)}) VALUES ({','.join('?' * len(TIP_FIELDS))})",
                      [row.get(f) for f in TIP_FIELDS])
    _demo_machines(industry)


# ---------- reads ----------
def records(industry, asset_id=None):
    q, a = "SELECT * FROM records WHERE industry=?", [industry]
    if asset_id:
        q += " AND asset_id=?"
        a.append(asset_id)
    with _conn() as c:
        return [dict(r) for r in c.execute(q + " ORDER BY datetime", a)]


def record(key):
    with _conn() as c:
        r = c.execute("SELECT * FROM records WHERE id=?", (key,)).fetchone()
    return dict(r) if r else None


def tips(industry, asset_id=None):
    q, a = "SELECT * FROM tips WHERE industry=?", [industry]
    if asset_id:
        q += " AND (asset_id=? OR asset_id='ALL')"
        a.append(asset_id)
    with _conn() as c:
        return [dict(r) for r in c.execute(q + " ORDER BY date", a)]


def tip(key):
    with _conn() as c:
        r = c.execute("SELECT * FROM tips WHERE id=?", (key,)).fetchone()
    return dict(r) if r else None


def pending(industry):
    with _conn() as c:
        recs = [dict(r) | {"kind": "record"} for r in c.execute(
            "SELECT * FROM records WHERE industry=? AND status='pending' ORDER BY datetime DESC", (industry,))]
        tps = [dict(r) | {"kind": "tip"} for r in c.execute(
            "SELECT * FROM tips WHERE industry=? AND status='pending' ORDER BY date DESC", (industry,))]
    return recs + tps


def ask(ask_id):
    with _conn() as c:
        r = c.execute("SELECT * FROM asks WHERE id=?", (ask_id,)).fetchone()
    if not r:
        return None
    d = dict(r)
    d["answer"] = json.loads(d["answer"] or "{}")
    return d


def flagged_keys(industry=None):
    with _conn() as c:
        if industry:
            return {r[0] for r in c.execute("SELECT memory_key FROM flags WHERE industry=?", (industry,))}
        return {r[0] for r in c.execute("SELECT memory_key FROM flags")}


def flags(industry):
    with _conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM flags WHERE industry=? ORDER BY created DESC", (industry,))]


# ---------- writes ----------
def now():
    return datetime.now().strftime("%Y-%m-%dT%H:%M")


def add_record(industry, data):
    row = {f: data.get(f) for f in REC_FIELDS}
    row["industry"] = industry
    row["id"] = row["id"] or f"rec-{uuid.uuid4().hex[:8]}"
    row["datetime"] = row["datetime"] or now()
    row["source"] = row["source"] or "app"
    row["status"] = row["status"] or "pending"
    row["cost"] = float(row["cost"] or 0)
    row["downtime_minutes"] = float(row["downtime_minutes"] or 0)
    for f in ("problem", "code", "symptom", "cause", "action", "parts", "notes"):
        row[f] = (row[f] or "").strip()
    with _lock, _conn() as c:
        c.execute(f"INSERT INTO records ({','.join(REC_FIELDS)}) VALUES ({','.join('?' * len(REC_FIELDS))})",
                  [row[f] for f in REC_FIELDS])
    backup.mark_dirty()
    return row


def add_tip(industry, person_id, asset_id, text, source_ref="", status="pending"):
    row = {"id": f"tip-{uuid.uuid4().hex[:8]}", "industry": industry, "person_id": person_id, "asset_id": asset_id,
           "date": now()[:10], "text": text.strip(), "source_ref": source_ref, "status": status, "approved_by": None,
           "source": "app"}
    with _lock, _conn() as c:
        c.execute(f"INSERT INTO tips ({','.join(TIP_FIELDS)}) VALUES ({','.join('?' * len(TIP_FIELDS))})",
                  [row[f] for f in TIP_FIELDS])
    backup.mark_dirty()
    return row


def approve(key, approved_by, approve=True):
    status = "approved" if approve else "rejected"
    with _lock, _conn() as c:
        n = c.execute("UPDATE records SET status=?, approved_by=? WHERE id=?", (status, approved_by, key)).rowcount
        n += c.execute("UPDATE tips SET status=?, approved_by=? WHERE id=?", (status, approved_by, key)).rowcount
    backup.mark_dirty()
    return n > 0


def save_ask(industry, asset_id, problem, use_memory, answer, top_person=None, top_key=None):
    ask_id = f"ask-{uuid.uuid4().hex[:8]}"
    with _lock, _conn() as c:
        c.execute("INSERT INTO asks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                  (ask_id, industry, now(), asset_id, problem, 1 if use_memory else 0, json.dumps(answer), top_person, top_key))
    return ask_id


def add_flag(industry, key, reason, flagged_by):
    with _lock, _conn() as c:
        c.execute("INSERT OR REPLACE INTO flags VALUES (?, ?, ?, ?, ?)", (key, industry, reason, flagged_by, now()))
    backup.mark_dirty()


def remove_flag(key):
    with _lock, _conn() as c:
        c.execute("DELETE FROM flags WHERE memory_key=?", (key,))
    backup.mark_dirty()


# ---------- machines added by the team (and details added to existing ones) ----------
_machine_cache = {}


def save_machine(industry, data, created_by=""):
    with _lock, _conn() as c:
        old = c.execute("SELECT created FROM machines WHERE industry=? AND id=?", (industry, data["id"])).fetchone()
        c.execute("INSERT OR REPLACE INTO machines VALUES (?, ?, ?, ?, ?)",
                  (industry, data["id"], json.dumps(data), old[0] if old else now(), created_by))
    _machine_cache.pop(industry, None)
    if created_by != "demo":
        backup.mark_dirty()


def machines(industry):
    if industry in _machine_cache:
        return _machine_cache[industry]
    try:
        with _conn() as c:
            out = [json.loads(r[0]) for r in c.execute("SELECT data FROM machines WHERE industry=? ORDER BY created", (industry,))]
    except sqlite3.OperationalError:  # table not created yet (first start)
        return []
    _machine_cache[industry] = out
    return out


def add_manual_item(industry, asset_id, kind, title, text, source_ref=""):
    row = {"id": f"man-{uuid.uuid4().hex[:8]}", "industry": industry, "asset_id": asset_id, "kind": kind,
           "title": (title or "").strip()[:200], "text": (text or "").strip()[:1500], "source_ref": (source_ref or "")[:300],
           "date": now()[:10]}
    with _lock, _conn() as c:
        c.execute("INSERT INTO manual_items VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                  (row["id"], industry, asset_id, kind, row["title"], row["text"], row["source_ref"], row["date"]))
    backup.mark_dirty()
    return row


def manual_items(industry, asset_id=None):
    q, a = "SELECT * FROM manual_items WHERE industry=?", [industry]
    if asset_id:
        q += " AND asset_id=?"
        a.append(asset_id)
    try:
        with _conn() as c:
            return [dict(r) for r in c.execute(q + " ORDER BY date, id", a)]
    except sqlite3.OperationalError:
        return []


def manual_item(key):
    if not (key or "").startswith("man-"):
        return None
    with _conn() as c:
        r = c.execute("SELECT * FROM manual_items WHERE id=?", (key,)).fetchone()
    return dict(r) if r else None


# ---------- small key/value notes (sensor state, demo flags) ----------
def meta_get(key):
    with _conn() as c:
        r = c.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return json.loads(r[0]) if r else {}


def meta_set(key, value):
    with _lock, _conn() as c:
        c.execute("INSERT OR REPLACE INTO meta VALUES (?, ?)", (key, json.dumps(value)))
    if key.split(":")[0] in ("sensor", "sensorlog", "readings"):
        backup.mark_dirty()


def update_record(key, fields):
    allowed = {k: v for k, v in fields.items() if k in REC_FIELDS and k not in ("id", "industry")}
    if not allowed:
        return
    with _lock, _conn() as c:
        c.execute(f"UPDATE records SET {', '.join(k + '=?' for k in allowed)} WHERE id=?", [*allowed.values(), key])
    backup.mark_dirty()
