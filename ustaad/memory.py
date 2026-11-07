"""
The memory layer — this is where Hindsight is used. One Hindsight memory bank per industry.

  retain  -> save a work record, a result ("worked / didn't work"), an expert tip or a public record
  recall  -> find past cases similar to a new problem (same asset, same model at other sites, same type)
  reflect -> let Hindsight reason over many memories (used for playbooks)

Without HINDSIGHT_API_KEY (or if Hindsight is unreachable) Ustaad falls back to a small built-in
"practice memory" with the same operations, so the app always runs. The screen shows which one is active.
"""
import math
import re
import threading
from collections import Counter

from . import config, packs, store

OUTCOME_TEXT = {
    "fixed": "WORKED - this fix solved it",
    "failed_again": "DID NOT WORK - the problem came back",
    "temporary": "TEMPORARY - worked only for a while, then the problem returned",
    "open": "OPEN - not solved yet",
}

STOP = set("""a an the is are was were be been to of in on at for with and or but if it its this that these those
by from as into than then so not no yes do does did done has have had i we you he she they them our your their
after before above below over under again very more most less too also just only about up down out off what why how
ka ki ke hai hain tha thi raha rahi mein me se par aur ko bhi nahi kya""".split())


def _tokens(text):
    return [w for w in re.findall(r"[a-z0-9]+", (text or "").lower()) if w not in STOP and len(w) > 1]


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")[:40]


# ---------- turning records into memory text ----------
def record_to_memory(industry, r):
    p = packs.get(industry)
    L = p["labels"]
    a = packs.asset(industry, r["asset_id"]) or {"id": r["asset_id"], "name": r["asset_id"], "model": "", "type": "", "site": ""}
    who = packs.person(industry, r["person_id"]) or {"name": r["person_id"] or "unknown", "role": ""}
    s = packs.site(industry, a.get("site")) or {}
    code = f" ({L.get('code', 'code')} {r['code']})" if r.get("code") else ""
    parts = f" Parts: {r['parts']}." if r.get("parts") and r["parts"] != "None" else ""
    hours = (r.get("downtime_minutes") or 0) / 60
    text = (f"{r['datetime'][:10]}, {s.get('name', '')}: {a['id']} ({a.get('name', '')}, model {a.get('model', '')}) had "
            f"'{r['problem']}'{code}. Symptom: {r.get('symptom', '')}. Cause found: {r.get('cause', '')}. "
            f"Action by {who['name']} ({who.get('role', '')}): {r.get('action', '')}.{parts} "
            f"{L.get('downtime', 'Downtime')} {hours:.1f} h. Result: {OUTCOME_TEXT.get(r['outcome'], r['outcome'])}. "
            f"{r.get('notes') or ''}").strip()
    tags = [f"industry:{industry}", "kind:record", f"asset:{a['id']}", f"model:{a.get('model', '')}",
            f"type:{a.get('type_key', '')}", f"site:{a.get('site', '')}", f"person:{r['person_id']}",
            f"outcome:{r['outcome']}", f"problem:{slug(r['problem'])}"]
    if r.get("code"):
        tags.append(f"code:{r['code']}")
    meta = {"key": r["id"], "kind": "record", "industry": industry, "asset_id": a["id"], "person": str(r["person_id"]),
            "outcome": r["outcome"], "date": r["datetime"][:10]}
    return {"key": r["id"], "kind": "record", "text": text, "tags": tags, "metadata": meta,
            "timestamp": r["datetime"][:16] + ":00", "asset_id": a["id"], "status": r.get("status")}


def tip_to_memory(industry, t):
    who = packs.person(industry, t["person_id"]) or {"name": t["person_id"], "role": ""}
    a = packs.asset(industry, t["asset_id"])
    where = f"{a['id']} ({a.get('name', '')}, model {a.get('model', '')})" if a else "everything"
    src = f" [Source: {t['source_ref']}]" if t.get("source_ref") else ""
    text = f"Expert tip from {who['name']} ({who.get('role', '')}) about {where}, {t['date']}: {t['text']}{src}"
    tags = [f"industry:{industry}", "kind:tip", f"person:{t['person_id']}", f"asset:{t['asset_id']}"]
    if a:
        tags += [f"model:{a.get('model', '')}", f"type:{a.get('type_key', '')}", f"site:{a.get('site', '')}"]
    meta = {"key": t["id"], "kind": "tip", "industry": industry, "asset_id": t["asset_id"], "person": t["person_id"],
            "date": t["date"]}
    return {"key": t["id"], "kind": "tip", "text": text, "tags": tags, "metadata": meta,
            "timestamp": t["date"] + "T12:00:00", "asset_id": t["asset_id"], "status": t.get("status")}


def public_to_memory(industry, x):
    fix = f" What fixed it: {x['fix']}." if x.get("fix") else ""
    text = f"Public record ({x['source']}, {x.get('date', '')}): {x['title']}. {x['text']}{fix}"
    tags = [f"industry:{industry}", "kind:public", f"type:{x.get('type_key', '')}", "asset:ALL",
            f"source:{slug(x['source'])}", f"outcome:{x.get('outcome', 'open')}"]
    if x.get("model"):
        tags.append(f"model:{x['model']}")
    meta = {"key": x["id"], "kind": "public", "industry": industry, "date": x.get("date", "")}
    ts = (x.get("date") or "2020-01-01")[:10]
    return {"key": x["id"], "kind": "public", "text": text, "tags": tags, "metadata": meta,
            "timestamp": (ts if len(ts) == 10 else "2020-01-01") + "T12:00:00", "asset_id": "ALL"}


def all_memories(industry, include_public=True):
    out = [record_to_memory(industry, r) for r in store.records(industry) if r["status"] != "rejected"]
    out += [tip_to_memory(industry, t) for t in store.tips(industry) if t["status"] != "rejected"]
    if include_public:
        out += [public_to_memory(industry, x) for x in packs.public_records(industry)]
    return out


def memory_by_key(industry, key):
    r = store.record(key)
    if r and r["industry"] == industry:
        return record_to_memory(industry, r)
    t = store.tip(key)
    if t and t["industry"] == industry:
        return tip_to_memory(industry, t)
    x = packs.public_record(industry, key)
    return public_to_memory(industry, x) if x else None


# ---------- practice memory (offline) ----------
class PracticeMemory:
    name = "Practice memory (offline)"

    def recall(self, industry, query, asset=None, k=8):
        items = all_memories(industry)
        docs = [Counter(_tokens(it["text"])) for it in items]
        n = len(docs) or 1
        df = Counter(w for d in docs for w in d)
        q = _tokens(query)
        codes = set(re.findall(r"\b[A-Z]{0,3}\d{3,5}\b", query or ""))
        scored = []
        for it, d in zip(items, docs):
            s = sum(math.log(1 + n / df[w]) for w in set(q) if w in d)
            if asset:
                t = it["tags"]
                if f"asset:{asset['id']}" in t:
                    s *= 1.6
                elif asset.get("model") and f"model:{asset['model']}" in t:
                    s *= 1.3  # twin machine / same model, maybe at another site
                elif asset.get("type_key") and f"type:{asset['type_key']}" in t:
                    s *= 1.0
                elif "asset:ALL" in t:
                    s *= 0.8
                else:
                    s *= 0.35
            if any(f"code:{c}" in it["tags"] or c in it["text"] for c in codes):
                s += 6
            if it["kind"] == "public":
                s *= 0.85
            if it.get("status") == "pending":
                s *= 0.75  # unreviewed memories rank a little lower
            if s > 1.0:
                scored.append((s, it))
        scored.sort(key=lambda x: -x[0])
        if scored:
            top = scored[0][0]
            scored = [(s, it) for s, it in scored if s >= 0.3 * top]
        return [{**it, "score": round(s, 2), "fact": it["text"], "origin": "practice"} for s, it in scored[:k]]

    def retain(self, industry, memory):
        return True

    def reflect(self, industry, query, asset=None, schema=None):
        return None


# ---------- Hindsight Cloud ----------
class HindsightMemory:
    name = "Hindsight Cloud"

    def __init__(self):
        from concurrent.futures import ThreadPoolExecutor
        from hindsight_client import Hindsight  # pip install hindsight-client
        # The client runs its own event loop and only works on the thread that created it, but the web server
        # answers each request on a different thread. So every Hindsight call goes through a small pool of
        # long-lived worker threads, each with its own client.
        self._cls = Hindsight
        self._local = threading.local()
        self._pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="hindsight")

    def _client(self):
        c = getattr(self._local, "client", None)
        if c is None:
            c = self._cls(base_url=config.HINDSIGHT_BASE_URL, api_key=config.HINDSIGHT_API_KEY, timeout=60)
            self._local.client = c
        return c

    def _run(self, fn, timeout=120):
        return self._pool.submit(lambda: fn(self._client())).result(timeout=timeout)

    @staticmethod
    def _tags_for(asset):
        if not asset:
            return None
        tags = [f"asset:{asset['id']}", "asset:ALL"]
        if asset.get("model"):
            tags.append(f"model:{asset['model']}")
        if asset.get("type_key"):
            tags.append(f"type:{asset['type_key']}")
        return tags

    def recall(self, industry, query, asset=None, k=8):
        res = self._run(lambda c: c.recall(bank_id=config.bank_id(industry), query=query, tags=self._tags_for(asset),
                                           tags_match="any", budget="mid", max_tokens=3000))
        by_key = {}
        for r in getattr(res, "results", []) or []:
            meta = getattr(r, "metadata", None) or {}
            key = meta.get("key") or getattr(r, "document_id", None) or f"fact:{r.id}"
            if key not in by_key:
                by_key[key] = {"key": key, "fact": r.text, "fact_id": r.id, "tags": getattr(r, "tags", None) or [],
                               "metadata": meta, "origin": "hindsight", "score": None}
        out = []
        for key, item in list(by_key.items())[:k]:
            full = memory_by_key(industry, key)
            if full:
                item = {**full, **item, "text": full["text"], "kind": full["kind"], "asset_id": full["asset_id"]}
            else:
                item.update({"text": item["fact"], "kind": "public", "asset_id": "ALL"})
            out.append(item)
        return out

    def retain(self, industry, m):
        self._run(lambda c: c.retain(bank_id=config.bank_id(industry), content=m["text"], timestamp=m["timestamp"],
                                     context=f"{industry} expert knowledge", document_id=m["key"],
                                     metadata={k: str(v) for k, v in m["metadata"].items()}, tags=m["tags"]))
        return True

    def retain_batch(self, industry, memories):
        items = [{"content": m["text"], "timestamp": m["timestamp"], "context": f"{industry} expert knowledge",
                  "document_id": m["key"], "metadata": {k: str(v) for k, v in m["metadata"].items()},
                  "tags": m["tags"]} for m in memories]
        self._run(lambda c: c.retain_batch(bank_id=config.bank_id(industry), items=items), timeout=300)

    def reflect(self, industry, query, asset=None, schema=None):
        r = self._run(lambda c: c.reflect(bank_id=config.bank_id(industry), query=query, budget="low", tags=self._tags_for(asset),
                                          tags_match="any", include_facts=True, response_schema=schema,
                                          context="Answer for a working team. Be specific and practical."))
        used = []
        based = getattr(r, "based_on", None)
        for f in (getattr(based, "memories", None) or []) if based else []:
            used.append(getattr(f, "text", str(f)))
        return {"text": r.text, "structured": getattr(r, "structured_output", None), "facts": used}

    def setup_bank(self, industry):
        p = packs.get(industry)
        self._run(lambda c: c.create_bank(
            bank_id=config.bank_id(industry),
            retain_mission=(f"{p['name']} expert memory for {p['org']['name']}. Keep {p['labels']['asset'].lower()} IDs, "
                            "models, codes, symptoms, causes, the exact steps, who did it, dates and above all whether "
                            "it WORKED or DID NOT WORK. Keep expert tips and their sources word for word."),
            reflect_mission=(f"You are Ustaad, the most experienced {p['labels']['person'].lower()} here. Prefer fixes "
                             "verified as WORKED, warn about ones that DID NOT WORK, always mention dates and who did it.")))


# ---------- the service the rest of the app uses ----------
class MemoryService:
    def __init__(self):
        self.practice = PracticeMemory()
        self.cloud = None
        self.last_error = None
        if config.HINDSIGHT_API_KEY:
            try:
                self.cloud = HindsightMemory()
            except Exception as e:
                self.last_error = f"Hindsight client could not start: {e}"

    @property
    def mode(self):
        return self.cloud.name if self.cloud else self.practice.name

    def recall(self, industry, query, asset=None, k=8):
        flagged = store.flagged_keys(industry)
        results = []
        used_cloud = False
        if self.cloud:
            try:
                results = self.cloud.recall(industry, query, asset, k)
                used_cloud = True
                self.last_error = None
            except Exception as e:
                self.last_error = f"Hindsight recall failed, used practice memory: {e}"
        if not used_cloud:
            results = self.practice.recall(industry, query, asset, k)
        else:
            # things saved in the last few seconds may still be processing inside Hindsight
            seen = {r["key"] for r in results}
            fresh = [r for r in self.practice.recall(industry, query, asset, k)
                     if r["key"] not in seen and _is_app_item(r["key"])]
            for r in fresh[:2]:
                results.append({**r, "origin": "just saved (syncing to Hindsight)"})
        return [r for r in results if r["key"] not in flagged and r.get("fact_id", "") not in flagged]

    def retain(self, industry, m):
        if not self.cloud:
            return "practice"

        def _go():
            try:
                self.cloud.retain(industry, m)
            except Exception as e:
                self.last_error = f"Hindsight retain failed: {e}"
        if config.SYNC_RETAIN:  # serverless hosts may stop background threads after the reply
            _go()
        else:
            threading.Thread(target=_go, daemon=True).start()
        return "hindsight"

    def reflect(self, industry, query, asset=None, schema=None):
        if not self.cloud:
            return None
        try:
            return self.cloud.reflect(industry, query, asset, schema)
        except Exception as e:
            self.last_error = f"Hindsight reflect failed: {e}"
            return None


def _is_app_item(key):
    src = store.record(key) or store.tip(key)
    return bool(src and src.get("source") == "app")


memory = MemoryService()
