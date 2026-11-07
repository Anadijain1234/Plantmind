"""
My machines — the team's register of its machines / equipment / devices / vehicles.

  add      -> fill a machine's details from the maker's PDF manual, its product web page or a photo of its nameplate
              (the AI reads it, a senior checks the form, then saves). The manual's known faults and service tasks are
              saved into Hindsight as "Maker's manual" memories, so answers can say "manual says X, the team found Y".
  profile  -> one page per machine: specs, health light, service due, spare-parts stock, warranty, full fix history,
              who knows it best, its manual memories and a QR sticker.
  sensors  -> a sensor alert opens a half-filled log by itself; normal readings after a fix mark it "sensor-confirmed".
"""
import html as htmllib
import ipaddress
import io
import json
import re
import socket
from datetime import date, datetime, timedelta
from urllib.parse import urljoin, urlparse

import requests

from . import config, llm, packs, store
from .memory import manual_to_memory, memory, record_to_memory

PAGE_WORDS = re.compile(r"alarm|trouble|fault|error|maint|lubric|specif|clean|filter|replac|inspect|warrant|daily|weekly|"
                        r"monthly|pressure|temperature|pilot|thermostat|service|parts? list|capacity|voltage|power", re.I)
MAX_TEXT = 13000


# ---------- reading a source: web page, PDF, photo ----------
def _check_url(url):
    u = urlparse((url or "").strip())
    if u.scheme not in ("http", "https") or not u.hostname:
        raise ValueError("Please paste a full web link that starts with https://")
    try:
        infos = socket.getaddrinfo(u.hostname, None)
    except Exception:
        raise ValueError("Couldn't find that website. Check the link.")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise ValueError("That link points to a private network address, so Ustaad won't open it.")
    return u.geturl()


def fetch_page(url):
    """Open a maker's product page (or a PDF link) safely and return its readable text."""
    url = _check_url(url)
    headers = {"User-Agent": "Mozilla/5.0 (compatible; UstaadBot/1.0; reads product pages a user pasted)",
               "Accept-Language": "en-IN,en;q=0.8"}
    try:
        for _ in range(4):  # follow redirects ourselves, checking every hop
            r = requests.get(url, headers=headers, timeout=20, stream=True, allow_redirects=False)
            if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("location"):
                url = _check_url(urljoin(url, r.headers["location"]))
                continue
            break
        r.raise_for_status()
        raw = r.raw.read(4_000_000, decode_content=True)
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Couldn't open that page ({str(e)[:100]}). Some company sites block servers — "
                         "upload the PDF manual instead.")
    if "pdf" in r.headers.get("content-type", "") or raw[:4] == b"%PDF":
        return pdf_text(raw)
    text = html_to_text(raw.decode(r.encoding or "utf-8", errors="ignore"))
    if len(text) < 200:
        raise ValueError("That page has almost no readable text (it may need JavaScript). Upload the PDF manual instead.")
    return text


def html_to_text(html):
    html = re.sub(r"(?is)<(script|style|noscript|svg|nav|footer|header|form|iframe)[^>]*>.*?</\1>", " ", html)
    html = re.sub(r"(?i)<(br|/p|/li|/tr|/h[1-6]|/div|/td|/th|/dt|/dd)[^>]*>", "\n", html)
    html = re.sub(r"(?i)<(td|th|dd)[^>]*>", " | ", html)
    text = htmllib.unescape(re.sub(r"<[^>]+>", " ", html))
    lines, seen = [], set()
    for line in (re.sub(r"[ \t\r\f\v|]+", " ", x).strip(" |") for x in text.split("\n")):
        if len(line) > 2 and line.lower() not in seen:
            seen.add(line.lower())
            lines.append(line)
    return "\n".join(lines)


def pdf_text(data):
    """Text of a PDF manual. Long manuals: keep the first pages plus the pages that talk about specs, maintenance,
    alarms and faults, up to about 12,000 characters."""
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ValueError("PDF reading needs the 'pypdf' package (it is in requirements.txt).")
    try:
        reader = PdfReader(io.BytesIO(data))
        pages = [re.sub(r"[ \t|]+", " ", (p.extract_text() or "")).strip() for p in reader.pages[:400]]
    except Exception as e:
        raise ValueError(f"Couldn't read that PDF: {str(e)[:100]}")
    pages = [re.sub(r"\n\s*\n+", "\n", p) for p in pages]
    if sum(len(p) for p in pages) < 200:
        raise ValueError("This PDF has no selectable text (it is a scanned picture). Try another manual or the maker's web page.")
    if sum(len(p) for p in pages) <= MAX_TEXT:
        return "\n\n".join(p for p in pages if p)
    keep = {0, 1}
    must = re.compile(r"specification|technical data|alarm list|troubleshoot|trouble shoot|parts? list|parts diagram|"
                      r"maintenance schedule|daily maintenance|warranty|power requirement", re.I)

    def score(i):
        return len(PAGE_WORDS.findall(pages[i])) / (1 + len(pages[i]) / 3000) + (30 if must.search(pages[i]) else 0)
    ranked = sorted(range(len(pages)), key=lambda i: -score(i))
    pages = [x[:2200] for x in pages]  # long pages are cut, so more useful pages fit
    size = len(pages[0]) + len(pages[1] if len(pages) > 1 else "")
    for i in ranked:
        if size > MAX_TEXT:
            break
        if pages[i] and (len(PAGE_WORDS.findall(pages[i])) >= 2 or must.search(pages[i])):
            keep.add(i)
            size += len(pages[i])
    return "\n\n".join(f"[page {i + 1}] {pages[i]}" for i in sorted(keep) if i < len(pages) and pages[i])[:MAX_TEXT + 1000]


EXTRACT_SCHEMA = """Return ONLY JSON:
{"name": "short plain name, e.g. 'Vertical machining centre' or 'Gas fryer'",
 "maker": "", "model": "", "type": "one or two words",
 "summary": "one plain sentence: what it is and what it is used for",
 "specs": [{"label": "e.g. Supply voltage", "value": "e.g. 380 V, 3 phase"}],
 "components": [{"name": "a part that wears out or gets replaced", "part_no": "", "every_days": null}],
 "faults": [{"title": "short fault name", "code": "alarm/error code or empty", "symptoms": "", "cause": "", "fix": "what the manual says to do"}],
 "service": [{"task": "maintenance task", "every_days": 1}],
 "warranty_months": null}"""


def extract(industry, text, source_ref=""):
    """Turn a manual / product page into a draft register entry. A senior checks the form before saving."""
    pk = packs.get(industry)
    text = (text or "").strip()
    if len(text) < 80:
        raise ValueError("Not enough text to read. Paste more, or upload the PDF manual.")
    data = None
    if llm.available():
        data = llm.chat_json(
            f"You read a maker's manual or product page for a {pk['labels']['asset'].lower()} and fill a register entry for a "
            f"{pk['name'].lower()} team. Use ONLY facts written in the text — never invent numbers, codes or part numbers; "
            "leave a field empty if the text doesn't say it. Keep alarm/error codes exactly. specs: up to 10 most useful. "
            "components: up to 10 parts that wear out or are replaced, with part numbers if given. faults: up to 8 — include "
            "alarm codes from any alarm/troubleshooting list. service: up to 8 tasks with every_days (daily 1, weekly 7, "
            "monthly 30, quarterly 90, half-yearly 180, yearly 365). Simple English. If the page covers a range of models, "
            "give the range.", f"Text (from {source_ref or 'the user'}):\n{text[:MAX_TEXT]}\n\n{EXTRACT_SCHEMA}", max_tokens=2600)
    if not isinstance(data, dict):
        specs = [{"label": m.group(1).strip()[:40], "value": m.group(2).strip()[:60]}
                 for m in re.finditer(r"^([A-Za-z][A-Za-z ()/.-]{2,40})\s*[:=]\s*([^\n]{1,60})$", text, re.M)][:10]
        first = re.sub(r"^\[page \d+\]\s*", "", next((ln for ln in text.splitlines() if len(ln.strip()) > 3), "New item")).strip()[:60]
        data = {"name": first, "maker": "", "model": "", "type": "", "summary": "", "specs": specs, "components": [],
                "faults": [], "service": [], "warranty_months": None,
                "note": "Filled without AI (no key) — only simple 'label: value' lines were picked up. Please check."}
    return _clean_draft(industry, data, source_ref)


def from_photo(industry, image_b64, mime):
    """Photo of a nameplate / rating plate -> draft register entry."""
    pk = packs.get(industry)
    data = llm.vision_json(
        f"This is a photo of a {pk['labels']['asset'].lower()}'s nameplate / rating plate / label. Read the visible text "
        "exactly. Return ONLY JSON: {\"name\": \"plain name of the item\", \"maker\": \"\", \"model\": \"\", \"serial\": \"\", "
        "\"year\": \"\", \"type\": \"\", \"specs\": [{\"label\": \"\", \"value\": \"\"}]}. Leave unknown fields empty.",
        image_b64, mime)
    if not isinstance(data, dict):
        raise ValueError("Couldn't read the nameplate" + (" (needs the Groq key)" if not llm.groq_available() else f": {llm.last_error}"))
    specs = list(data.get("specs") or [])
    for k in ("serial", "year"):
        if data.get(k):
            specs.insert(0, {"label": "Serial number" if k == "serial" else "Year", "value": str(data[k])})
    data["specs"] = specs
    return _clean_draft(industry, data, "Nameplate photo")


def _type_key(industry, typ):
    t = (typ or "").lower()
    known = {a.get("type_key"): a.get("type", "") for a in packs.assets(industry) if a.get("type_key")}
    for k, label in known.items():
        if k and (k in t or (label and label.lower() in t) or (t and t in k)):
            return k
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:20] or "general"


def _clean_draft(industry, d, source_ref):
    def lst(x, n):
        return [i for i in (x or []) if isinstance(i, dict)][:n]
    out = {"name": str(d.get("name") or "").strip()[:60], "maker": str(d.get("maker") or "").strip()[:60],
           "model": str(d.get("model") or "").strip()[:40], "type": str(d.get("type") or "").strip()[:30],
           "summary": str(d.get("summary") or "").strip()[:300],
           "specs": [{"label": str(s.get("label", ""))[:40], "value": str(s.get("value", ""))[:80]} for s in lst(d.get("specs"), 12)
                     if s.get("label") and s.get("value")],
           "components": [{"name": str(c.get("name", ""))[:60], "part_no": str(c.get("part_no") or "")[:30],
                           "every_days": _int(c.get("every_days"))} for c in lst(d.get("components"), 12) if c.get("name")],
           "faults": [{k: str(f.get(k) or "")[:300] for k in ("title", "code", "symptoms", "cause", "fix")}
                      for f in lst(d.get("faults"), 10) if f.get("title")],
           "service": [{"task": str(s.get("task", ""))[:160], "every_days": _int(s.get("every_days"))}
                       for s in lst(d.get("service"), 10) if s.get("task")],
           "warranty_months": _int(d.get("warranty_months")), "source_ref": source_ref[:300], "note": d.get("note", "")}
    out["type_key"] = _type_key(industry, out["type"])
    return out


def _int(x):
    try:
        return int(float(x)) if x not in (None, "") else None
    except Exception:
        return None


# ---------- saving ----------
def _can_edit(industry, role_id):
    r = packs.role(industry, role_id)
    if not r or not r.get("can_approve"):
        raise PermissionError("Only a senior role can add or change machines. Workers can view them and use the QR sticker.")


def save(industry, d, person_id=None, role_id=None):
    _can_edit(industry, role_id)
    pk = packs.get(industry)
    aid = re.sub(r"[^A-Z0-9-]", "", str(d.get("id") or "").upper())[:14]
    if len(aid) < 2:
        raise ValueError(f"Give the {pk['labels']['asset'].lower()} a short ID, e.g. CNC-4 or FRY-2")
    if not (d.get("name") or "").strip():
        raise ValueError("Please give it a name")
    site_ids = [s["id"] for s in pk.get("sites", [])]
    site = d.get("site") if d.get("site") in site_ids else (site_ids[0] if site_ids else "")
    existing = packs.asset(industry, aid)
    is_new = existing is None
    new_service = [x for x in (d.get("service") or []) if isinstance(x, dict) and x.get("task")][:12]
    if not is_new and d.get("is_new"):
        raise ValueError(f"{aid} already exists — pick another ID, or open {aid} and edit it")
    install = (d.get("install_date") or "")[:10]
    warranty_until = (d.get("warranty_until") or "")[:10]
    if not warranty_until and install and _int(d.get("warranty_months")):
        try:
            w = datetime.fromisoformat(install) + timedelta(days=round(_int(d["warranty_months"]) * 30.44))
            warranty_until = w.date().isoformat()
        except Exception:
            pass
    comps = []
    for c in d.get("components") or []:
        if isinstance(c, dict) and c.get("name"):
            comps.append({"name": str(c["name"])[:60], "part_no": str(c.get("part_no") or "")[:30],
                          "every_days": _int(c.get("every_days")), "stock": _int(c.get("stock")),
                          "min_stock": _int(c.get("min_stock")) if c.get("min_stock") not in (None, "") else 1})
    row = {"id": aid, "name": d["name"].strip()[:60], "model": (d.get("model") or "").strip()[:40] or (existing or {}).get("model", ""),
           "type": (d.get("type") or "").strip()[:30] or (existing or {}).get("type", ""),
           "type_key": d.get("type_key") or (existing or {}).get("type_key") or _type_key(industry, d.get("type")),
           "site": site if is_new else (d.get("site") or existing.get("site")), "maker": (d.get("maker") or "").strip()[:60],
           "install_date": install, "warranty_until": warranty_until, "vendor": (d.get("vendor") or "").strip()[:80],
           "vendor_phone": re.sub(r"[^0-9+ ]", "", d.get("vendor_phone") or "")[:20],
           "summary": (d.get("summary") or "").strip()[:300],
           "specs": [s for s in (d.get("specs") or []) if isinstance(s, dict) and s.get("label")][:15],
           "components": comps, "service": _merge_service((existing or {}).get("service"), new_service),
           "source_ref": (d.get("source_ref") or "")[:300], "custom": is_new or bool((existing or {}).get("custom")),
           "added_by": person_id or ""}
    store.save_machine(industry, row, person_id or "")
    # the manual's knowledge goes into memory (and Hindsight)
    mems = []
    src = row["source_ref"] or "Maker's manual"
    for f in d.get("faults") or []:
        if isinstance(f, dict) and f.get("title"):
            title = f["title"] + (f" (code {f['code']})" if f.get("code") and f["code"] not in f["title"] else "")
            text = ". ".join(x for x in [f"Symptoms: {f['symptoms']}" if f.get("symptoms") else "",
                                         f"Cause: {f['cause']}" if f.get("cause") else "",
                                         f"Manual says: {f['fix']}" if f.get("fix") else ""] if x)
            mems.append(store.add_manual_item(industry, aid, "fault", title, text or title, src))
    for s in new_service:
        every = _int(s.get("every_days"))
        mems.append(store.add_manual_item(industry, aid, "service", s["task"],
                                          f"Do this every {every} days." if every else "Regular maintenance task.", src))
    new_source = row["source_ref"] and row["source_ref"] != (existing or {}).get("source_ref")
    if row["specs"] and (is_new or new_source):
        mems.append(store.add_manual_item(industry, aid, "spec", f"{row['name']} spec sheet",
                                          "; ".join(f"{s['label']}: {s['value']}" for s in row["specs"]), src))
    where = memory.retain_many(industry, [manual_to_memory(industry, m) for m in mems]) if mems else "—"
    return {"asset": packs.asset(industry, aid), "manual_memories": len(mems), "saved_to": where,
            "message": (f"✔ {aid} added." if is_new else f"✔ {aid} updated.")
            + (f" {len(mems)} manual facts saved to memory." if mems else "")}


def _merge_service(old, new):
    out, seen = [], set()
    for x in list(old or []) + list(new or []):
        if isinstance(x, dict) and x.get("task") and x["task"].lower() not in seen:
            seen.add(x["task"].lower())
            out.append({"task": x["task"][:160], "every_days": _int(x.get("every_days"))})
    return out[:15]


def set_stock(industry, aid, part, stock):
    a = packs.asset(industry, aid)
    if not a:
        raise ValueError("Unknown item")
    row = next((m for m in store.machines(industry) if m["id"] == aid), None) or {"id": aid}
    comps = [dict(c) for c in (row.get("components") or a.get("components") or [])]
    hit = next((c for c in comps if c["name"] == part), None)
    if not hit:
        raise ValueError("Unknown part")
    hit["stock"] = max(0, _int(stock) or 0)
    store.save_machine(industry, {**row, "components": comps})
    return {"ok": True, "part": hit}


def use_parts(industry, aid, text):
    """When a repair log says a part was replaced, take one off the store's stock."""
    a = packs.asset(industry, aid)
    t = (text or "").lower()
    if not a or not a.get("components") or not re.search(r"replac|chang|new |fitted|install|swap|refill|topped|added", t):
        return []
    row = next((m for m in store.machines(industry) if m["id"] == aid), None) or {"id": aid}
    comps = [dict(c) for c in (row.get("components") or a.get("components"))]
    used = []
    for c in comps:
        words = [w for w in re.findall(r"[a-z0-9]+", c["name"].lower()) if len(w) > 3][:2]
        if words and all(w in t for w in words) and c.get("stock") not in (None, ""):
            was = int(c["stock"])
            c["stock"] = max(0, was - 1)
            used.append({"name": c["name"], "stock": c["stock"], "was_zero": was <= 0})
    if used:
        store.save_machine(industry, {**row, "components": comps})
    return used


# ---------- profile ----------
OUTCOME = {"fixed": "Worked", "failed_again": "Didn't work", "temporary": "Temporary", "open": "Open"}


def _last_done(recs, name):
    words = [w for w in re.findall(r"[a-z0-9]+", (name or "").lower()) if len(w) > 3][:2]
    if not words:
        return None
    hits = [r for r in recs if all(w in f"{r.get('action', '')} {r.get('parts', '')}".lower() for w in words)]
    return hits[-1]["datetime"][:10] if hits else None


def _due(base, every, today, from_history):
    """Next due date. From repair history: last time + interval (can be overdue).
    From the install date only: the next cycle from today (we don't know if earlier cycles were done)."""
    if not base or not every:
        return None
    try:
        b = date.fromisoformat(base[:10])
    except Exception:
        return None
    if from_history or b >= today:
        return b + timedelta(days=every)
    n = -(-(today - b).days // every)
    return b + timedelta(days=every * max(n, 1))


def service_due(industry, a, recs=None, today=None):
    today = today or date.today()
    recs = recs if recs is not None else [r for r in store.records(industry, a["id"]) if r["status"] != "rejected"]
    items = []
    for c in a.get("components") or []:
        if not c.get("every_days"):
            continue
        last = _last_done(recs, c["name"])
        base = last or a.get("install_date")
        nxt = _due(base, c["every_days"], today, bool(last))
        if nxt:
            left = (nxt - today).days
            items.append({"what": f"Replace / check {c['name']}", "every_days": c["every_days"], "last_done": last,
                          "last_from": "repair history" if last else ("install date" if base else ""),
                          "next": nxt.isoformat(), "days_left": left,
                          "status": "overdue" if left < 0 else ("soon" if left <= 7 else "ok")})
    for s in a.get("service") or []:
        every = _int(s.get("every_days"))
        if every and every >= 7 and a.get("install_date"):
            nxt = _due(a["install_date"], every, today, False)
            if nxt:
                left = (nxt - today).days
                items.append({"what": s["task"], "every_days": every, "last_done": None, "last_from": "install date",
                              "next": nxt.isoformat(), "days_left": left, "status": "soon" if left <= 7 else "ok"})
    return sorted(items, key=lambda x: x["days_left"])


def parts(a):
    out = []
    for c in a.get("components") or []:
        st = c.get("stock")
        status = "unknown" if st in (None, "") else ("out" if int(st) <= 0 else ("low" if int(st) <= int(c.get("min_stock") or 1) else "ok"))
        out.append({**c, "status": status})
    return out


def health(industry, a, recs=None, today=None):
    """Green / amber / red with plain reasons."""
    today = today or date.today()
    recs = recs if recs is not None else [r for r in store.records(industry, a["id"]) if r["status"] != "rejected"]
    reasons, level = [], 0
    if recs and recs[-1]["outcome"] in ("open", "failed_again"):
        level = 2
        reasons.append(f"Last problem not solved yet: {recs[-1]['problem']}")
    recent = [r for r in recs if (today - date.fromisoformat(r["datetime"][:10])).days <= 90]
    if len(recent) >= 3:
        level = max(level, 1)
        reasons.append(f"{len(recent)} problems in the last 90 days")
    due = service_due(industry, a, recs, today)
    over = [x for x in due if x["status"] == "overdue"]
    if over:
        level = max(level, 1 if len(over) == 1 else 2)
        reasons.append(f"{len(over)} service item(s) overdue")
    out = [p for p in parts(a) if p["status"] == "out"]
    if out:
        level = max(level, 1)
        reasons.append(f"Out of stock: {', '.join(p['name'] for p in out[:2])}")
    if a.get("warranty_until"):
        try:
            left = (date.fromisoformat(a["warranty_until"]) - today).days
            if 0 <= left <= 45:
                reasons.append(f"Warranty ends in {left} days")
        except Exception:
            pass
    return {"level": ["green", "amber", "red"][level], "label": ["Healthy", "Needs attention", "Problem now"][level],
            "reasons": reasons or ["No open problems, nothing overdue"]}


def _experts(industry, a, recs_all):
    twins = {x["id"] for x in packs.assets(industry) if x.get("model") and x.get("model") == a.get("model")} | {a["id"]}
    count = {}
    for r in recs_all:
        if r["asset_id"] in twins and r["outcome"] == "fixed" and r["status"] != "rejected" and packs.person(industry, r["person_id"]):
            count[r["person_id"]] = count.get(r["person_id"], 0) + 1
    out = []
    for pid, n in sorted(count.items(), key=lambda kv: -kv[1])[:3]:
        p = packs.person(industry, pid)
        out.append({"person_id": pid, "name": p["name"], "role": p.get("role", ""), "fixes": n, "leaving": p.get("retiring_on")})
    return out


def best_expert(industry, aid, problem="", exclude=None):
    a = packs.asset(industry, aid)
    if not a:
        return None
    recs = [r for r in store.records(industry) if r["status"] != "rejected"]
    same = [r for r in recs if r["problem"] == problem and r["outcome"] == "fixed"]
    count = {}
    for r in same:
        if r["person_id"] != exclude and packs.person(industry, r["person_id"]):
            count[r["person_id"]] = count.get(r["person_id"], 0) + 1
    if count:
        pid = max(count, key=count.get)
        p = packs.person(industry, pid)
        return {"person_id": pid, "name": p["name"], "role": p.get("role", ""), "fixes": count[pid], "about": problem}
    ex = [e for e in _experts(industry, a, recs) if e["person_id"] != exclude]
    return ({**ex[0], "about": a["id"]} if ex else None)


def summary_list(industry):
    today = date.today()
    out = []
    for a in packs.assets(industry):
        recs = [r for r in store.records(industry, a["id"]) if r["status"] != "rejected"]
        due = service_due(industry, a, recs, today)
        out.append({**{k: a.get(k) for k in ("id", "name", "model", "type", "site", "maker", "custom")},
                    "health": health(industry, a, recs, today), "problems": len(recs),
                    "fixed": sum(1 for r in recs if r["outcome"] == "fixed"),
                    "due_soon": sum(1 for x in due if x["status"] in ("soon", "overdue")),
                    "parts_low": sum(1 for p in parts(a) if p["status"] in ("low", "out")),
                    "manual": len(store.manual_items(industry, a["id"]))})
    return out


def profile(industry, aid):
    a = packs.asset(industry, aid)
    if not a:
        raise ValueError("Unknown item")
    today = date.today()
    recs_all = [r for r in store.records(industry) if r["status"] != "rejected"]
    recs = [r for r in recs_all if r["asset_id"] == aid]
    site = packs.site(industry, a.get("site")) or {}
    twins = [x["id"] for x in packs.assets(industry) if x.get("model") and x.get("model") == a.get("model") and x["id"] != aid]
    history = [{"key": r["id"], "date": r["datetime"][:10], "problem": r["problem"], "action": r["action"], "cause": r["cause"],
                "outcome": r["outcome"], "outcome_label": OUTCOME.get(r["outcome"], r["outcome"]),
                "person": (packs.person(industry, r["person_id"]) or {}).get("name") or r["person_id"] or "",
                "minutes": r["downtime_minutes"], "status": r["status"], "source": r.get("source"),
                "sensor": store.meta_get(f"sensor:{r['id']}")} for r in reversed(recs)][:40]
    warranty = None
    if a.get("warranty_until"):
        try:
            left = (date.fromisoformat(a["warranty_until"]) - today).days
            warranty = {"until": a["warranty_until"], "days_left": left, "active": left >= 0}
        except Exception:
            pass
    return {"asset": a, "site": site.get("name", ""), "twins": twins, "health": health(industry, a, recs, today),
            "service_due": service_due(industry, a, recs, today), "parts": parts(a), "warranty": warranty,
            "history": history, "experts": _experts(industry, a, recs_all),
            "manual": [{"key": m["id"], "kind": m["kind"], "title": m["title"], "text": m["text"], "source": m["source_ref"]}
                       for m in store.manual_items(industry, aid)],
            "stats": {"problems": len(recs), "fixed": sum(1 for r in recs if r["outcome"] == "fixed"),
                      "hours_lost": round(sum(r["downtime_minutes"] or 0 for r in recs) / 60, 1),
                      "last_problem": recs[-1]["datetime"][:10] if recs else None},
            "sensor": sensor_state(industry, aid)}


# ---------- sensors: auto-log and sensor-confirmed fixes ----------
def _thresholds():
    s = packs.processed("factory_sensors.json") or {}
    th = s.get("thresholds") or {}
    return {"vib_warn": th.get("vib_warn", 4.5), "temp_warn": th.get("temp_warn", 80)}


def _open_sensor_log(industry, aid, hours=24):
    for r in reversed(store.records(industry, aid)):
        if r.get("source") == "sensor" and r["outcome"] == "open":
            try:
                if datetime.now() - datetime.fromisoformat(store.meta_get(f"sensorlog:{r['id']}").get("created", "2000-01-01T00:00")) \
                        <= timedelta(hours=hours):
                    return r
            except Exception:
                return r
    return None


def sensor_alert(industry, aid, reading):
    """A sensor crossed its limit: open a half-filled log by itself (once per few hours per machine)."""
    a = packs.asset(industry, aid)
    if not a:
        raise ValueError("Unknown item")
    existing = _open_sensor_log(industry, aid, hours=6)
    if existing:
        return {"record": existing, "new": False, "message": f"Already logged as open issue {existing['id']}."}
    vib, temp = reading.get("vib"), reading.get("temp")
    th = _thresholds()
    what = "High vibration" if vib is not None and float(vib) >= th["vib_warn"] else "High temperature"
    rec = store.add_record(industry, {
        "asset_id": aid, "person_id": "sensor", "problem": f"Sensor alert: {what.lower()}", "code": "",
        "symptom": f"Sensor reading: vibration {vib} mm/s, temperature {temp} °C" + (f" at {reading['time']}" if reading.get("time") else ""),
        "cause": "", "action": "Auto-logged by the sensor — waiting for a technician", "outcome": "open",
        "status": "approved", "source": "sensor", "notes": "Created automatically when the sensor crossed its limit."})
    store.meta_set(f"sensorlog:{rec['id']}", {"created": datetime.now().isoformat(timespec="minutes"), "reading": reading})
    memory.retain(industry, record_to_memory(industry, rec))
    return {"record": rec, "new": True, "message": f"📝 Auto-logged as open issue {rec['id']} — the technician only adds what they did."}


def close_sensor_log(industry, aid, outcome, person_id, action, cause, minutes, problem=None):
    """When a worker reports the result for a machine with an open sensor log, finish that log instead of making a new one."""
    r = _open_sensor_log(industry, aid)
    if not r:
        return None
    store.update_record(r["id"], {"outcome": outcome, "person_id": person_id, "action": action, "cause": cause,
                                  "problem": problem or r["problem"],
                                  "downtime_minutes": float(minutes or 0),
                                  "notes": (r.get("notes") or "") + " Finished by the technician through Ustaad."})
    if outcome == "fixed":
        store.meta_set(f"sensor:{r['id']}", {"awaiting": True, "since": datetime.now().isoformat(timespec="minutes")})
    rec = store.record(r["id"])
    memory.retain(industry, record_to_memory(industry, rec))
    return rec


def sensor_reading(industry, aid, vib, temp):
    """Live readings API (a factory's sensor gateway can post here). Three normal readings after a fix -> sensor-confirmed."""
    if not packs.asset(industry, aid):
        raise ValueError("Unknown item")
    th = _thresholds()
    key = f"readings:{industry}:{aid}"
    hist = (store.meta_get(key).get("last") or [])[-9:] + [{"vib": float(vib), "temp": float(temp),
                                                            "at": datetime.now().isoformat(timespec="seconds")}]
    store.meta_set(key, {"last": hist})
    normal = len(hist) >= 3 and all(h["vib"] < th["vib_warn"] and h["temp"] < th["temp_warn"] for h in hist[-3:])
    confirmed = None
    if normal:
        for r in reversed(store.records(industry, aid)):
            st = store.meta_get(f"sensor:{r['id']}")
            if st.get("awaiting") and not st.get("confirmed"):
                st.update(confirmed=True, confirmed_at=datetime.now().isoformat(timespec="minutes"))
                store.meta_set(f"sensor:{r['id']}", st)
                confirmed = r["id"]
                break
    alert = None
    if hist[-1]["vib"] >= th["vib_warn"] or hist[-1]["temp"] >= th["temp_warn"]:
        alert = sensor_alert(industry, aid, {"vib": vib, "temp": temp})
    return {"ok": True, "normal": normal, "confirmed_record": confirmed, "alert": alert}


def sensor_state(industry, aid):
    recs = [r for r in store.records(industry, aid) if r.get("source") == "sensor"]
    if not recs:
        return None
    r = recs[-1]
    st = store.meta_get(f"sensor:{r['id']}")
    state = ("confirmed" if st.get("confirmed") else "waiting" if st.get("awaiting") else
             "open" if r["outcome"] == "open" else "closed")
    text = {"confirmed": "✔ Sensor-confirmed: readings went back to normal after the fix.",
            "waiting": "Fix reported. Waiting for normal readings from the sensor to confirm it.",
            "open": "Open: the sensor logged this problem. Waiting for a technician.",
            "closed": "Closed by the technician."}[state]
    return {"record": r["id"], "problem": r["problem"], "state": state, "text": text, "symptom": r["symptom"]}


# ---------- demo data for the built-in industries ----------
def load_demo(industry):
    path = config.ROOT / "data" / "demo_machines.json"
    if not path.exists():
        return 0
    rows = json.loads(path.read_text(encoding="utf-8")).get(industry, [])
    for row in rows:
        if packs.asset(industry, row["id"]) or row.get("custom"):
            store.save_machine(industry, {**row, "demo": True}, "demo")
    return len(rows)
