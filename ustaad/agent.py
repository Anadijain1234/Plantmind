"""
Ustaad — the AI agent. It combines Hindsight memory (what happened before, who did it, did it work)
with the Groq language model (how to say it clearly) and the exact records (numbers).
Same code for every industry; the industry pack supplies words, people and data.
"""
import re
import statistics
from datetime import datetime, timedelta

from . import insights, llm, packs, store
from .memory import memory, memory_by_key, record_to_memory, tip_to_memory

LANG_NAMES = {"en": "English", "hi": "Hindi (Devanagari script, simple words)", "kn": "Kannada (simple words)",
              "hinglish": "Hinglish (Hindi in Roman script, simple words)"}


def _name(industry, pid):
    p = packs.person(industry, pid)
    return p["name"] if p else (pid or "unknown")


def _fmt_date(d):
    try:
        return datetime.fromisoformat(d[:10]).strftime("%d %b %Y")
    except Exception:
        return d or ""


def _split_steps(action):
    action = re.sub(r"^.*?\bfrom Ustaad\b[^:]*:\s*", "", action or "", flags=re.I)
    parts = re.split(r";\s*|(?<=[a-z0-9])\.\s+| and then | then |,\s+(?=[A-Z])", action)
    out = []
    for p in parts:
        p = p.strip().rstrip(".")
        if len(p) > 3:
            out.append(p[0].upper() + p[1:])
    return out


def _sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z])", text or "") if s.strip()]


def _source_badge(industry, kind, key):
    if kind == "public":
        x = packs.public_record(industry, key) or {}
        return x.get("source", "Public record")
    if kind == "tip":
        return (store.tip(key) or {}).get("source_ref") or ""
    return (store.record(key) or {}).get("source_ref") or ""


def memory_card(industry, r, ref, asked_asset=None):
    kind = r.get("kind") or "record"
    key = r["key"]
    card = {"ref": ref, "key": key, "kind": kind, "origin": r.get("origin"), "fact": r.get("fact") or r["text"],
            "fact_id": r.get("fact_id"), "text": r["text"], "trust": insights.trust_level(industry, kind, key),
            "source": _source_badge(industry, kind, key)}
    if kind == "record":
        src = store.record(key) or {}
        a = packs.asset(industry, src.get("asset_id")) or {}
        card.update({"date": src.get("datetime", "")[:10], "asset_id": src.get("asset_id"), "person": _name(industry, src.get("person_id")),
                     "person_id": src.get("person_id"), "outcome": src.get("outcome"), "problem": src.get("problem"),
                     "action": src.get("action"), "cause": src.get("cause"), "downtime_minutes": src.get("downtime_minutes"),
                     "site": (packs.site(industry, a.get("site")) or {}).get("name"), "site_id": a.get("site")})
    elif kind == "tip":
        src = store.tip(key) or {}
        a = packs.asset(industry, src.get("asset_id")) or {}
        card.update({"date": src.get("date"), "asset_id": src.get("asset_id"), "person": _name(industry, src.get("person_id")),
                     "person_id": src.get("person_id"), "outcome": "expert_tip", "problem": "Expert tip", "action": src.get("text"),
                     "site": (packs.site(industry, a.get("site")) or {}).get("name"), "site_id": a.get("site")})
    else:
        x = packs.public_record(industry, key) or {}
        card.update({"date": x.get("date"), "asset_id": "ALL", "person": x.get("source"), "person_id": None,
                     "outcome": x.get("outcome", "open"), "problem": x.get("title"), "action": x.get("fix") or x.get("text"),
                     "url": x.get("url"), "site": None})
    if asked_asset and card.get("site_id") and asked_asset.get("site") and card["site_id"] != asked_asset["site"]:
        card["cross_site"] = True
    return card


def _overall_trust(cards):
    recs = [c for c in cards if c["kind"] == "record"]
    fixed = [c for c in recs if c.get("outcome") == "fixed"]
    failed = [c for c in recs if c.get("outcome") in ("failed_again", "temporary")]
    tips = [c for c in cards if c["kind"] == "tip"]
    pub = [c for c in cards if c["kind"] == "public"]
    if fixed and (len(fixed) >= 2 or tips):
        level, label = "verified", f"Verified: {len(recs)} past case(s), {len(fixed)} proven fix(es)"
    elif recs or tips:
        level, label = "partial", f"Partly known: {len(recs)} similar case(s) in memory"
    elif pub:
        level, label = "partial", f"Only public records match ({len(pub)}) — nothing from your own team yet"
    else:
        level, label = "new", "New problem: nothing like this in memory yet"
    return {"level": level, "label": label, "cases": len(recs), "fixed": len(fixed), "failed": len(failed),
            "expert_tips": len(tips), "public": len(pub)}


# ---------- rule-based answers (no LLM key) ----------
def _rule_answer(industry, asset, problem, cards):
    recs = [c for c in cards if c["kind"] == "record"]
    tips = [c for c in cards if c["kind"] == "tip"]
    pubs = [c for c in cards if c["kind"] == "public"]
    if not (recs or tips or pubs):
        return None
    if recs:
        fam = recs[0].get("problem")
        recs = [c for c in recs if c.get("problem") == fam] or recs
    fixed = [c for c in recs if c.get("outcome") == "fixed"]
    failed = [c for c in recs if c.get("outcome") in ("failed_again", "temporary")]
    approved = [c for c in fixed if c["trust"]["tier"] in ("verified", "tested")]
    originals = [c for c in approved if "ustaad" not in (c.get("action") or "").lower()]
    best = (originals or approved or fixed or [None])[0]
    causes, seen = [], set()
    for c in fixed + failed:
        if not c.get("cause") or c["cause"] in seen:
            continue
        seen.add(c["cause"])
        worked = c.get("outcome") == "fixed"
        n_same = sum(1 for x in fixed if x.get("cause") == c["cause"])
        causes.append({"cause": c["cause"], "confidence": "high" if worked and (n_same >= 2 or tips) else ("medium" if worked else "low"),
                       "why": (f"Worked on {_fmt_date(c['date'])} — {c['person']}" if worked
                               else f"Tried on {_fmt_date(c['date'])} but the problem came back"), "memory_refs": [c["ref"]]})
    for p in pubs[:2]:
        if p.get("action"):
            causes.append({"cause": p["problem"], "confidence": "low", "why": f"Public record: {p['person']}", "memory_refs": [p["ref"]]})
    avoid = [{"action": c["action"], "why": f"Tried {_fmt_date(c['date'])} by {c['person']}: did not work", "memory_refs": [c["ref"]]}
             for c in failed]
    tip = tips[0]["action"] if tips else ""
    first = ""
    if tip:
        s = _sentences(tip)
        first = next((x for x in s if re.search(r"\b(check|clean|test|verify|confirm|look|measure|spray|run)\b", x, re.I)), s[0])
    elif best:
        first = _split_steps(best["action"])[0]
    steps = _split_steps(best["action"]) if best else (_split_steps(pubs[0]["action"]) if pubs else [])
    times = [c["downtime_minutes"] for c in fixed if c.get("downtime_minutes")]
    summary = ((f"Seen before. On {_fmt_date(best['date'])}, {best['person']} solved it: {best['action'].rstrip('.')}. " if best else
                "No fix from your own team yet; the closest public records are shown. ")
               + (f"{len(failed)} earlier attempt(s) did not work — don't repeat them." if failed else ""))
    return {"summary": summary.strip(), "likely_causes": causes[:4], "check_first": first, "steps": steps,
            "avoid": avoid[:4], "expert_tip": tip, "parts_to_keep_ready": [],
            "estimated_time": f"about {round(statistics.median(times))} minutes" if times else "",
            "safety": packs.get(industry).get("safety_line", "")}


def _generic(industry, asset):
    g = packs.get(industry).get("generic", {})
    steps = g.get(asset.get("type_key", ""), g.get("default", ["Check the basics", "Ask a senior"]))
    return {"summary": "General advice only. Without memory I don't know this team's history.",
            "likely_causes": [{"cause": s, "confidence": "low", "why": "General rule of thumb", "memory_refs": []} for s in steps[:3]],
            "check_first": steps[0], "steps": steps, "avoid": [], "expert_tip": "", "parts_to_keep_ready": [],
            "estimated_time": "unknown", "safety": packs.get(industry).get("safety_line", "")}


ANSWER_SCHEMA = """Return ONLY a JSON object:
{"summary": "2-3 short sentences",
 "likely_causes": [{"cause": "...", "confidence": "high|medium|low", "why": "...", "memory_refs": ["M1"]}],
 "check_first": "the single first thing to check",
 "steps": ["short step", "..."],
 "avoid": [{"action": "what NOT to repeat", "why": "...", "memory_refs": ["M2"]}],
 "expert_tip": "the senior expert's tip in one line, or empty",
 "parts_to_keep_ready": ["..."],
 "estimated_time": "e.g. about 1 hour",
 "safety": "one safety line"}"""


def _llm_answer(industry, asset, problem, cards, language):
    pk = packs.get(industry)
    L = pk["labels"]
    lang = LANG_NAMES.get(language, "English")
    guard = pk.get("llm_guard", "")
    if cards:
        mem = "\n".join(f"[{c['ref']}] ({c['trust']['label']}) {c['text']}" for c in cards)
        system = (f"You are Ustaad, the most experienced {L['person'].lower()} at {pk['org']['name']}. A colleague asks about a "
                  f"problem with a {L['asset'].lower()}. Use ONLY the memories given. Rank causes by what was proven to WORK; "
                  "put attempts that DID NOT WORK in 'avoid'. Memories from another site with the same model count (say so). "
                  "Public records are outside evidence — mention them as such. Cite memories as M1, M2 in memory_refs. "
                  f"Mention dates and names in 'why'. Short and practical. {guard} Write all text in {lang}. "
                  "Keep IDs, codes and numbers as they are.")
        user = f"{L['asset']}: {asset['id']} — {asset['name']} (model {asset.get('model', '')}, {asset.get('type', '')})\nProblem: {problem}\n\nMemories:\n{mem}\n\n{ANSWER_SCHEMA}"
    else:
        system = (f"You are a general assistant with NO knowledge of this team's history. Give generic advice only. {guard} "
                  f"Write all text in {lang}. memory_refs must be empty.")
        user = f"{L['asset']}: {asset['name']} ({asset.get('type', '')})\nProblem: {problem}\n\n{ANSWER_SCHEMA}"
    data = llm.chat_json(system, user)
    if not isinstance(data, dict) or not data.get("summary"):
        return None
    for k in ("likely_causes", "steps", "avoid", "parts_to_keep_ready"):
        data.setdefault(k, [])
    return data


def ask(industry, asset_id, problem, use_memory=True, language="en"):
    asset = packs.asset(industry, asset_id)
    if not asset:
        raise ValueError(f"Unknown {packs.get(industry)['labels']['asset'].lower()}")
    problem = (problem or "").strip()
    if not problem:
        raise ValueError("Please describe the problem")
    if use_memory and insights.is_data_question(problem):
        chart = insights.answer_with_chart(industry, problem)
        return {"mode": "chart", "chart": chart, "problem": problem, "asset": asset, "memory_mode": "records (exact numbers)"}
    cards = []
    if use_memory:
        q = f"{asset['id']} {asset['name']} {asset.get('model', '')} {asset.get('type', '')}: {problem}"
        recalled = memory.recall(industry, q, asset, k=8)
        cards = [memory_card(industry, r, f"M{i}", asset) for i, r in enumerate(recalled, 1)]
    answer = _llm_answer(industry, asset, problem, cards, language) if llm.available() else None
    written_by = "Groq LLM" if answer else "rule-based (no LLM key)"
    if not answer:
        answer = (_rule_answer(industry, asset, problem, cards) if cards else None) or _generic(industry, asset)
    trust = _overall_trust(cards) if use_memory else {"level": "off", "label": "Memory OFF: generic answer", "cases": 0,
                                                       "fixed": 0, "failed": 0, "expert_tips": 0, "public": 0}
    matched = next((c for c in cards if c["kind"] == "record" and c.get("outcome") == "fixed"), None) or \
        next((c for c in cards if c["kind"] in ("record", "tip")), None)
    answer["matched_problem"] = matched["problem"] if matched and matched["kind"] == "record" else None
    ask_id = store.save_ask(industry, asset_id, problem, use_memory, answer,
                            matched.get("person_id") if matched else None, matched["key"] if matched else None)
    return {"mode": "answer", "ask_id": ask_id, "asset": asset, "problem": problem, "use_memory": use_memory,
            "answer": answer, "memories": cards, "trust": trust, "memory_mode": memory.mode if use_memory else "off",
            "written_by": written_by, "memory_error": memory.last_error, "llm_error": llm.last_error}


def _code_from(text):
    m = re.search(r"\b(?:alarm|error|code|dtc)\s*[:#-]?\s*([A-Z]{0,3}\d{2,5})\b", text or "", re.I) or \
        re.search(r"\b([PBCU]\d{4})\b", text or "")
    return m.group(1).upper() if m else ""


def feedback(industry, ask_id, result, person_id, note="", downtime_minutes=None, action_done="", steps_done=None):
    a = store.ask(ask_id)
    if not a:
        raise ValueError("Unknown answer id")
    ans = a["answer"]
    fixed = result == "fixed"
    causes = ans.get("likely_causes") or []
    action = action_done.strip() or ((ans.get("check_first") or "") + ("; " + "; ".join(ans.get("steps", [])[:4]) if ans.get("steps") else ""))
    rec = store.add_record(industry, {
        "asset_id": a["asset_id"], "person_id": person_id, "problem": ans.get("matched_problem") or a["problem"][:70],
        "code": _code_from(a["problem"]), "symptom": a["problem"],
        "cause": causes[0]["cause"] if causes and fixed else "Not found yet — the suggested fix did not work",
        "action": action.strip("; ") or "Followed Ustaad's advice", "downtime_minutes": downtime_minutes or 0,
        "outcome": "fixed" if fixed else "failed_again", "status": "approved",  # a real result is its own proof
        "notes": (note or "") + f" (reported through Ustaad, answer {ask_id})",
        "credited_to": a.get("top_person"), "steps_done": ",".join(str(s) for s in (steps_done or [])),
    })
    where = memory.retain(industry, record_to_memory(industry, rec))
    credit = _name(industry, a.get("top_person")) if fixed and a.get("top_person") and a.get("top_person") != person_id else None
    return {"record": rec, "saved_to": where, "credited_to": credit,
            "message": ("Saved. Next time Ustaad will rank this fix higher." if fixed else
                        "Saved. Next time Ustaad will warn that this did not work.")
            + (f" Credit added to {credit}'s skill passport." if credit else "")}


def log_record(industry, data):
    if not packs.asset(industry, data.get("asset_id")):
        raise ValueError("Unknown asset")
    for f in ("problem", "symptom", "action", "outcome", "person_id"):
        if not (data.get(f) or "").strip():
            raise ValueError(f"Please fill '{f}'")
    rec = store.add_record(industry, {**data, "status": "pending", "code": data.get("code") or _code_from(data.get("symptom"))})
    return {"record": rec, "saved_to": memory.retain(industry, record_to_memory(industry, rec)),
            "message": "Saved and sent to a senior for approval. It shows as 'Unreviewed' until approved."}


def smart_log(industry, text, person_id):
    """Free speech/text -> a structured record, auto-tagged to the right asset and problem."""
    pk = packs.get(industry)
    text = (text or "").strip()
    if len(text) < 8:
        raise ValueError("Please say or type a bit more")
    assets = pk["assets"]
    data = None
    if llm.available():
        listing = "\n".join(f"- {a['id']}: {a['name']} (model {a.get('model', '')})" for a in assets)
        data = llm.chat_json(
            f"Extract a work record from what a {pk['labels']['person'].lower()} said (may be Hindi, Kannada, English or mixed). "
            "Pick asset_id ONLY from the list. Translate values to simple English. outcome is one of fixed, failed_again, temporary, open. "
            'Return ONLY JSON: {"asset_id": "...", "problem": "short name", "code": "", "symptom": "...", "cause": "...", '
            '"action": "...", "outcome": "...", "downtime_minutes": 0, "is_tip": false}',
            f"Assets:\n{listing}\n\nThey said: {text}")
    if not isinstance(data, dict) or not packs.asset(industry, data.get("asset_id")):
        tl = text.lower()
        hit = next((a for a in assets if a["id"].lower() in tl), None) or \
            next((a for a in assets if any(w in tl for w in a["name"].lower().split()[:2] if len(w) > 3)), None) or assets[0]
        outcome = "fixed" if re.search(r"\b(fixed|worked|solved|ok now|theek|sahi|resolved|chal gaya)\b", tl) else (
            "failed_again" if re.search(r"\b(again|not work|didn't|did not|nahi|failed)\b", tl) else "open")
        mins = re.search(r"(\d+)\s*(min|minute|mins)", tl)
        hrs = re.search(r"(\d+(?:\.\d+)?)\s*(hour|hr|ghanta)", tl)
        known = [r["problem"] for r in store.records(industry, hit["id"])]
        words = set(re.findall(r"[a-z0-9]+", tl))
        best_known = max(known, key=lambda k: len(words & set(re.findall(r"[a-z0-9]+", k.lower()))), default="")
        if best_known and not (words & set(re.findall(r"[a-z0-9]+", best_known.lower())) - {hit["id"].lower()}):
            best_known = ""
        data = {"asset_id": hit["id"], "problem": best_known or " ".join(text.split()[:8])[:60], "code": _code_from(text), "symptom": text,
                "cause": "", "action": text, "outcome": outcome,
                "downtime_minutes": int(mins.group(1)) if mins else (float(hrs.group(1)) * 60 if hrs else 0), "is_tip": False}
    if data.get("is_tip"):
        t = store.add_tip(industry, person_id, data["asset_id"], text)
        return {"kind": "tip", "tip": t, "extracted": data, "saved_to": memory.retain(industry, tip_to_memory(industry, t)),
                "message": f"Saved as an expert tip for {data['asset_id']} — waiting for senior approval."}
    rec = store.add_record(industry, {"asset_id": data["asset_id"], "person_id": person_id, "problem": data.get("problem") or text[:60],
                                      "code": data.get("code") or _code_from(text), "symptom": data.get("symptom") or text,
                                      "cause": data.get("cause") or "", "action": data.get("action") or text,
                                      "outcome": data.get("outcome") or "open", "downtime_minutes": data.get("downtime_minutes") or 0,
                                      "status": "pending", "notes": f"Said: {text[:300]}"})
    return {"kind": "record", "record": rec, "extracted": data,
            "saved_to": memory.retain(industry, record_to_memory(industry, rec)),
            "message": f"Auto-tagged to {data['asset_id']} · '{rec['problem']}'. Waiting for senior approval."}


def add_tip(industry, person_id, asset_id, text, source_ref=""):
    if not packs.person(industry, person_id):
        raise ValueError("Unknown person")
    if asset_id != "ALL" and not packs.asset(industry, asset_id):
        raise ValueError("Unknown asset")
    if len((text or "").strip()) < 10:
        raise ValueError("Please write the tip in at least one full sentence")
    t = store.add_tip(industry, person_id, asset_id, text, source_ref)
    return {"tip": t, "saved_to": memory.retain(industry, tip_to_memory(industry, t)),
            "message": "Saved. It shows as 'Unreviewed' until a senior approves it."}


def approve(industry, key, role_id, approver_id, ok=True):
    r = packs.role(industry, role_id)
    if not r or not r.get("can_approve"):
        raise PermissionError("Only a senior role can approve memories")
    if not store.approve(key, approver_id, ok):
        raise ValueError("Unknown memory")
    m = memory_by_key(industry, key)
    if ok and m:
        memory.retain(industry, m)  # re-save so the memory carries its approved status
    return {"ok": True, "message": "Approved — now counts as trusted knowledge." if ok else "Rejected — hidden from answers."}


# ---------- playbook / SOP ----------
def problems_for(industry, asset_id):
    a = packs.asset(industry, asset_id)
    twins = {x["id"] for x in packs.assets(industry) if x.get("model") == a.get("model")}
    seen = {}
    for r in store.records(industry):
        if r["asset_id"] in twins and r["status"] != "rejected":
            seen[r["problem"]] = seen.get(r["problem"], 0) + 1
    return [{"problem": p, "count": c} for p, c in sorted(seen.items(), key=lambda kv: -kv[1])]


def playbook(industry, asset_id, problem, language="en"):
    pk = packs.get(industry)
    a = packs.asset(industry, asset_id)
    if not a:
        raise ValueError("Unknown asset")
    twins = {x["id"] for x in packs.assets(industry) if x.get("model") == a.get("model")}
    recs = [r for r in store.records(industry) if r["asset_id"] in twins and r["problem"] == problem and r["status"] != "rejected"]
    if not recs:
        raise ValueError("No history for this problem yet")
    code = next((r["code"] for r in recs if r["code"]), "")
    ptoks = set(re.findall(r"[a-z0-9]+", problem.lower()))
    tps = [t for t in store.tips(industry) if t["asset_id"] in twins and t["status"] != "rejected" and (
        (code and code in t["text"]) or len(ptoks & set(re.findall(r"[a-z0-9]+", t["text"].lower()))) >= 2)]
    fixed = [r for r in recs if r["outcome"] == "fixed"]
    failed = [r for r in recs if r["outcome"] != "fixed"]
    verified = [f"{_fmt_date(r['datetime'])} · {_name(industry, r['person_id'])} · {r['asset_id']} · WORKED" for r in fixed]
    times = [r["downtime_minutes"] for r in fixed if r["downtime_minutes"]]
    insight = memory.reflect(industry, f"What is the proven way to handle '{problem}' on {a['id']} ({a.get('model')}), and what failed before?", a)
    card = None
    if llm.available():
        rtext = "\n".join("- " + record_to_memory(industry, r)["text"] for r in recs)
        ttext = "\n".join("- " + tip_to_memory(industry, t)["text"] for t in tps)
        card = llm.chat_json(
            f"You write standard operating procedures (SOP) for {pk['org']['name']} — a McDonald's-style checklist anyone on any shift "
            f"can follow. Use ONLY the records given. Proven WORKED steps become the steps; DID NOT WORK goes into do_not. "
            f"{pk.get('llm_guard', '')} Write in {LANG_NAMES.get(language, 'English')}.",
            f"{pk['labels']['asset']}: {a['name']}\nProblem: {problem}\n\nRecords:\n{rtext}\n\nExpert tips:\n{ttext or '- none'}\n\n"
            'Return ONLY JSON: {"title": "...", "when_to_use": "...", "symptoms": ["..."], "first_checks": ["..."], '
            '"steps": ["..."], "parts": ["..."], "tools": ["..."], "do_not": ["..."], "safety": "...", "typical_time": "..."}')
    if not isinstance(card, dict) or not card.get("steps"):
        best = fixed[-1] if fixed else recs[-1]
        card = {"title": f"{problem} — {a.get('model') or a['name']} SOP",
                "when_to_use": f"When {', '.join(sorted(twins))} shows: {recs[-1]['symptom']}",
                "symptoms": list(dict.fromkeys(r["symptom"] for r in recs))[:3],
                "first_checks": [(_sentences(t["text"]) or [t["text"]])[0] for t in tps][:2] or _split_steps(best["action"])[:1],
                "steps": _split_steps(best["action"]),
                "parts": list(dict.fromkeys(r["parts"] for r in fixed if r["parts"] and r["parts"] != "None")),
                "tools": [], "do_not": [f"{r['action']} (tried {_fmt_date(r['datetime'])}, did not last)" for r in failed],
                "safety": pk.get("safety_line", ""),
                "typical_time": f"about {round(statistics.median(times))} minutes" if times else "unknown"}
    card.update({"verified_by": verified, "based_on_records": len(recs), "asset_id": asset_id, "problem": problem,
                 "expert_tips_used": [tip_to_memory(industry, t)["text"] for t in tps],
                 "hindsight_insight": insight["text"] if insight else None, "org": pk["org"]["name"],
                 "generated": datetime.now().strftime("%d %b %Y")})
    return card


# ---------- before-you-leave interview ----------
def interview(industry, person_id, language="en"):
    p = packs.person(industry, person_id)
    if not p:
        raise ValueError("Unknown person")
    L = packs.get(industry)["labels"]
    fams = [f for f in insights.knowledge_families(industry) if f["owner"] == person_id]
    qs = []
    for f in fams:
        label = f["problem"] + (f" ({L.get('code', 'code')} {f['code']})" if f["code"] else "")
        if not f["captured"]:
            qs.append({"priority": "high", "asset_id": f["asset_id"], "problem": f["problem"],
                       "question": f"On {f['asset_id']}, how do you recognise '{label}'? What do you check first, and what sign tells you the real cause?",
                       "why": f"Only {p['name']} has solved this ({_fmt_date(f['first_fix_date'])}) and nothing is written down yet."})
        if f["failed_attempts"]:
            qs.append({"priority": "high" if not f["captured"] else "medium", "asset_id": f["asset_id"], "problem": f["problem"],
                       "question": f"Others' attempts at '{label}' on {f['asset_id']} failed {f['failed_attempts']} time(s) before yours. How did you know?",
                       "why": "This judgement is the knowledge most likely to be lost."})
    for extra in packs.get(industry).get("interview_extra", []):
        qs.append({"priority": "medium", "asset_id": "ALL", "problem": extra["topic"], "question": extra["question"], "why": extra["why"]})
    if llm.available() and language != "en":
        data = llm.chat_json("Translate the 'question' and 'why' fields to " + LANG_NAMES.get(language, "English")
                             + ". Keep IDs and codes. Return JSON {\"items\": [...]} with the same keys.", str({"items": qs}))
        if isinstance(data, dict) and isinstance(data.get("items"), list) and len(data["items"]) == len(qs):
            qs = data["items"]
    order = {"high": 0, "medium": 1, "low": 2}
    qs.sort(key=lambda q: order.get(q.get("priority"), 2))
    return {"person": p, "fixes_owned": len(fams), "captured": sum(1 for f in fams if f["captured"]), "questions": qs}


def answer_interview(industry, person_id, asset_id, question, answer_text):
    if len((answer_text or "").strip()) < 10:
        raise ValueError("Please answer in at least one full sentence")
    text = f"Q: {question} A: {answer_text.strip()}"
    return add_tip(industry, person_id, asset_id if packs.asset(industry, asset_id) else "ALL", text, "Exit interview")


# ---------- shift report (built from real data) ----------
def sensor_alerts():
    s = packs.processed("factory_sensors.json")
    if not s:
        return []
    th = s["thresholds"]
    out = []
    for aid, pts in s["series"].items():
        first = next((p for p in pts if p["vib"] >= th["vib_warn"] or p["temp"] >= th["temp_warn"]), None)
        if first:
            peak = max(pts, key=lambda p: p["vib"])
            out.append({"asset_id": aid, "first_at_minute": first["t"], "first": first, "peak": peak,
                        "level": "stop" if peak["vib"] >= th["vib_stop"] else "warning"})
    return out


def shift_report(industry, hours=24, language="en"):
    pk = packs.get(industry)
    recs = [r for r in store.records(industry) if r["status"] != "rejected"]
    if not recs:
        return {"summary": "No activity yet.", "events": []}
    now = datetime.now()
    start = now - timedelta(hours=hours)
    recent = [r for r in recs if datetime.fromisoformat(r["datetime"][:16]) >= start]
    note = None
    if not recent:
        last = datetime.fromisoformat(recs[-1]["datetime"][:16])
        start = last - timedelta(hours=hours)
        recent = [r for r in recs if datetime.fromisoformat(r["datetime"][:16]) >= start]
        note = f"Nothing in the last {hours} h — showing the last active day ({_fmt_date(recs[-1]['datetime'])})."
    events = [{"time": r["datetime"].replace("T", " "), "asset_id": r["asset_id"], "problem": r["problem"],
               "outcome": r["outcome"], "person": _name(industry, r["person_id"]), "action": r["action"],
               "downtime_minutes": r["downtime_minutes"], "status": r["status"]} for r in recent]
    open_issues = [e for e in events if e["outcome"] in ("failed_again", "open")]
    upcoming = [x for x in insights.repeat_failures(industry) if x["regular"] and x["days_until_next"] is not None and x["days_until_next"] <= 14]
    alerts = sensor_alerts() if "sensors" in pk.get("tools", []) else []
    waiting = len(store.pending(industry))
    summary = None
    if llm.available():
        d = llm.chat_json(f"You write a short shift handover note for a {pk['name'].lower()} team. Plain words, 3-6 bullets. "
                          f"Write in {LANG_NAMES.get(language, 'English')}. Return JSON {{\"summary\": \"text with '\\n- ' bullets\"}}.",
                          f"Events: {events}\nOpen: {open_issues}\nDue soon: {upcoming}\nSensor alerts: {alerts}\nWaiting approval: {waiting}")
        if isinstance(d, dict):
            summary = d.get("summary")
    if not summary:
        lines = [f"- {e['time'][11:]} {e['asset_id']}: {e['problem']} → {'WORKED' if e['outcome'] == 'fixed' else 'NOT solved'} "
                 f"by {e['person']} ({int(e['downtime_minutes'] or 0)} min)" for e in events]
        for a in alerts:
            lines.append(f"- 📈 Sensor: {a['asset_id']} vibration reached {a['peak']['vib']} mm/s, temperature {a['peak']['temp']} °C — check it first.")
        if open_issues:
            lines.append(f"- ⚠️ {len(open_issues)} problem(s) still open.")
        for u in upcoming:
            lines.append(f"- 🔁 {u['asset_id']} '{u['problem']}' returns every ~{u['avg_gap_days']} days — due around {_fmt_date(u['next_expected'])}.")
        if waiting:
            lines.append(f"- 🕒 {waiting} new memory/memories waiting for senior approval.")
        summary = "\n".join(lines) or "- Quiet shift."
    return {"summary": summary, "events": events, "open_issues": len(open_issues), "upcoming": upcoming,
            "sensor_alerts": alerts, "waiting_approval": waiting, "window_hours": hours, "note": note}


# ---------- translate / photo ----------
def translate(texts, language):
    if language not in LANG_NAMES:
        raise ValueError("Unknown language")
    if not llm.available():
        return {"texts": texts, "note": "Translation needs the Groq key."}
    d = llm.chat_json(f"Translate each string to {LANG_NAMES[language]}. Keep IDs, codes and numbers. "
                      'Return JSON {"texts": [...]} with the same number of items, same order.', str({"texts": texts}))
    if isinstance(d, dict) and isinstance(d.get("texts"), list) and len(d["texts"]) == len(texts):
        return {"texts": d["texts"]}
    return {"texts": texts, "note": "Translation failed, showing the original."}


def read_photo(industry, image_b64, mime, asset_id=None):
    a = packs.asset(industry, asset_id) if asset_id else None
    hint = f"{packs.get(industry)['name']} — {a['name']}" if a else packs.get(industry)["name"]
    data = llm.read_photo(image_b64, mime, hint)
    if not data:
        raise ValueError("Couldn't read the photo" + (" (needs the Groq key)" if not llm.available() else f": {llm.last_error}"))
    return data
