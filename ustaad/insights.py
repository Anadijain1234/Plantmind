"""
Exact numbers, no AI needed: incidents, knowledge risk, repeat failures, skill map, skill passport,
trust levels, cross-site learning, before/after stats, data charts and the onboarding quiz.
Works the same for every industry.
"""
import random
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from . import packs, store


def _dt(s):
    return datetime.fromisoformat(s[:16])


def _tokens(text):
    return set(w for w in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(w) > 2)


def _cost_per_hour(industry, asset_id):
    a = packs.asset(industry, asset_id) or {}
    return a.get("cost_per_hour", packs.get(industry).get("cost_per_hour", 0))


def _live(industry):
    return [r for r in store.records(industry) if r["status"] != "rejected"]


# ---------- incidents: one problem, possibly several attempts ----------
def incidents(industry, recs=None):
    recs = recs if recs is not None else _live(industry)
    groups = defaultdict(list)
    for r in sorted(recs, key=lambda x: x["datetime"]):
        groups[(r["asset_id"], r["problem"])].append(r)
    out = []
    for (aid, problem), items in groups.items():
        cur = None
        for r in items:
            if (cur and cur["attempts"][-1]["outcome"] == "failed_again"
                    and _dt(r["datetime"]) - _dt(cur["attempts"][-1]["datetime"]) <= timedelta(days=7)):
                cur["attempts"].append(r)
            else:
                cur = {"asset_id": aid, "problem": problem, "attempts": [r]}
                out.append(cur)
    for inc in out:
        a = inc["attempts"]
        inc["start"] = a[0]["datetime"]
        inc["downtime_minutes"] = sum(x["downtime_minutes"] or 0 for x in a)
        inc["cost"] = sum(x["cost"] or 0 for x in a)
        inc["failed_attempts"] = sum(1 for x in a if x["outcome"] == "failed_again")
        inc["outcome"] = a[-1]["outcome"]
    return sorted(out, key=lambda x: x["start"])


def incident_cost(industry, inc):
    return round(inc["downtime_minutes"] / 60 * _cost_per_hour(industry, inc["asset_id"]) + inc["cost"])


# ---------- trust levels (Verified / Tested once / Unreviewed / Didn't work / Public record) ----------
def trust_level(industry, kind, key):
    if kind == "public":
        return {"tier": "public", "label": "Public record"}
    if kind == "tip":
        t = store.tip(key) or {}
        if t.get("status") == "pending":
            return {"tier": "unreviewed", "label": "Unreviewed — waiting for senior approval"}
        if t.get("source_ref"):
            return {"tier": "verified", "label": f"Verified expert tip · source: {t['source_ref']}"}
        return {"tier": "tested", "label": "Expert tip (approved)"}
    r = store.record(key) or {}
    if r.get("status") == "pending":
        return {"tier": "unreviewed", "label": "Unreviewed — waiting for senior approval"}
    if r.get("outcome") in ("failed_again", "temporary"):
        return {"tier": "failed", "label": "Did not work — don't repeat"}
    if r.get("outcome") != "fixed":
        return {"tier": "unreviewed", "label": "Open — no result yet"}
    a = packs.asset(industry, r["asset_id"]) or {}
    same = [x for x in _live(industry) if x["outcome"] == "fixed" and x["problem"] == r["problem"]
            and (packs.asset(industry, x["asset_id"]) or {}).get("model") == a.get("model")]
    people = {x["person_id"] for x in same}
    if len(same) >= 2 and len(people) >= 2:
        return {"tier": "verified", "label": f"Verified — worked {len(same)} times, confirmed by {len(people)} people"}
    if len(same) >= 2:
        return {"tier": "verified", "label": f"Verified — worked {len(same)} times"}
    return {"tier": "tested", "label": "Tested once — worked 1 time"}


# ---------- knowledge families: who first found the fix that works ----------
def _tip_covers(industry, tip, asset, problem, code):
    if tip["asset_id"] == "ALL":
        return False
    if tip["asset_id"] != asset["id"]:
        twin = packs.asset(industry, tip["asset_id"])
        if not (twin and twin.get("model") == asset.get("model")):
            return False
    text = tip["text"].lower()
    if code and re.search(rf"\b{re.escape(code.lower())}\b", text):
        return True
    return len(_tokens(problem) & _tokens(text)) >= 2


def knowledge_families(industry):
    recs = _live(industry)
    tps = [t for t in store.tips(industry) if t["status"] != "rejected"]
    fams = defaultdict(list)
    for r in recs:
        fams[(r["asset_id"], r["problem"])].append(r)
    out = []
    for (aid, problem), items in fams.items():
        a = packs.asset(industry, aid) or {"id": aid}
        first = next((x for x in items if x["outcome"] == "fixed"), None)
        code = next((x["code"] for x in items if x.get("code")), "")
        covered = [t for t in tps if _tip_covers(industry, t, a, problem, code)]
        out.append({"asset_id": aid, "problem": problem, "code": code, "attempts": len(items),
                    "failed_attempts": sum(1 for x in items if x["outcome"] in ("failed_again", "temporary")),
                    "owner": first["person_id"] if first else None,
                    "first_fix_date": first["datetime"][:10] if first else None,
                    "first_fix_action": first["action"] if first else None,
                    "captured": bool(covered), "tips": [t["id"] for t in covered]})
    return out


def knowledge_risk(industry):
    ppl = {p["id"]: p for p in packs.people(industry)}
    retiring = {pid for pid, p in ppl.items() if p.get("retiring_on")}
    fams = knowledge_families(industry)
    rows = []
    for a in packs.assets(industry):
        af = [f for f in fams if f["asset_id"] == a["id"] and f["owner"]]
        if not af:
            continue
        owners = Counter(f["owner"] for f in af)
        top, cnt = owners.most_common(1)[0]
        share = cnt / len(af)
        ret_owned = [f for f in af if f["owner"] in retiring]
        unc = [f for f in ret_owned if not f["captured"]]
        rs = len(ret_owned) / len(af)
        level = "high" if rs >= 0.5 and unc else ("medium" if rs >= 0.5 or (share >= 0.7 and len(af) >= 2) or unc else "low")
        rows.append({"asset_id": a["id"], "asset": a["name"], "site": a.get("site"), "families": len(af),
                     "top_owner": ppl.get(top, {}).get("name", top), "top_owner_share": round(share * 100),
                     "retiring_share": round(rs * 100), "level": level,
                     "uncaptured": [{"problem": f["problem"], "code": f["code"], "owner": ppl.get(f["owner"], {}).get("name")}
                                    for f in unc]})
    order = {"high": 0, "medium": 1, "low": 2}
    rows.sort(key=lambda x: (order[x["level"]], -x["retiring_share"]))
    owned_total = len([f for f in fams if f["owner"]]) or 1
    experts = []
    for pid in retiring:
        owned = [f for f in fams if f["owner"] == pid]
        experts.append({"person_id": pid, "name": ppl[pid]["name"], "retiring_on": ppl[pid]["retiring_on"],
                        "fixes_owned": len(owned), "captured": sum(1 for f in owned if f["captured"]),
                        "share_of_all_known_fixes": round(100 * len(owned) / owned_total),
                        "only_in_their_head": [f"{f['asset_id']}: {f['problem']}" for f in owned if not f["captured"]][:8]})
    return {"assets": rows, "retiring_experts": experts}


def repeat_failures(industry, today=None):
    today = today or datetime.now()
    groups = defaultdict(list)
    for inc in incidents(industry):
        groups[(inc["asset_id"], inc["problem"])].append(inc)
    out = []
    for (aid, problem), incs in groups.items():
        if len(incs) < 3:
            continue
        starts = [_dt(i["start"]) for i in incs]
        gaps = [(b - a).days for a, b in zip(starts, starts[1:])]
        avg = statistics.mean(gaps) or 1
        cv = statistics.pstdev(gaps) / avg
        regular = cv < 0.25
        nxt = (starts[-1] + timedelta(days=round(avg))).date().isoformat() if regular else None
        a = packs.asset(industry, aid) or {"name": aid}
        causes = [x["cause"] for i in incs for x in i["attempts"] if x["outcome"] == "fixed"]
        out.append({"asset_id": aid, "asset": a["name"], "problem": problem, "times": len(incs),
                    "dates": [s.date().isoformat() for s in starts], "avg_gap_days": round(avg), "regular": regular,
                    "next_expected": nxt, "days_until_next": (datetime.fromisoformat(nxt) - today).days if nxt else None,
                    "total_downtime_hours": round(sum(i["downtime_minutes"] for i in incs) / 60, 1),
                    "total_cost": sum(incident_cost(industry, i) for i in incs),
                    "common_cause": max(set(causes), key=causes.count) if causes else ""})
    out.sort(key=lambda x: (not x["regular"], -x["times"]))
    return out


def skill_map(industry):
    ppl = packs.people(industry)
    assets = packs.assets(industry)
    counts = Counter((r["person_id"], r["asset_id"]) for r in _live(industry) if r["outcome"] == "fixed")
    return {"people": [{"id": p["id"], "name": p["name"], "role": p.get("role")} for p in ppl],
            "assets": [a["id"] for a in assets],
            "grid": {p["id"]: {a["id"]: counts[(p["id"], a["id"])] for a in assets} for p in ppl}}


# ---------- skill passport: credit for experts, with proof levels ----------
def passport(industry, person_id):
    p = packs.person(industry, person_id)
    if not p:
        raise ValueError("Unknown person")
    pk = packs.get(industry)
    started = pk["org"].get("ustaad_started", "2026-09-01")
    recs = _live(industry)
    mine = [r for r in recs if r["person_id"] == person_id]
    fixed = [r for r in mine if r["outcome"] == "fixed"]
    tips = [t for t in store.tips(industry) if t["person_id"] == person_id and t["status"] != "rejected"]
    skills = defaultdict(lambda: {"fixed": 0, "assets": set(), "confirmed_by_others": 0, "tips": 0})
    for r in fixed:
        key = r["problem"]
        skills[key]["fixed"] += 1
        skills[key]["assets"].add(r["asset_id"])
    for r in recs:  # others who fixed the same problem after this person, crediting them through Ustaad
        if r["credited_to"] == person_id and r["person_id"] != person_id and r["outcome"] == "fixed":
            skills[r["problem"]]["confirmed_by_others"] += 1
    for t in tips:
        a = packs.asset(industry, t["asset_id"])
        for prob in list(skills.keys()):
            if len(_tokens(prob) & _tokens(t["text"])) >= 2:
                skills[prob]["tips"] += 1
                break
        else:
            skills[f"Tip: {t['text'][:60]}…"]["tips"] += 1
            if a:
                skills[f"Tip: {t['text'][:60]}…"]["assets"].add(a["id"])
    out = []
    for name, s in skills.items():
        if s["fixed"] >= 2 or s["confirmed_by_others"] >= 1:
            tier, label = "verified", "Verified — proven more than once"
        elif s["fixed"] == 1:
            tier, label = "attested", "Attested — proven once"
        else:
            tier, label = "self", "Self-declared — tip, not yet proven by a fix"
        out.append({"skill": name, "tier": tier, "label": label, "fixes": s["fixed"], "assets": sorted(s["assets"]),
                    "confirmed_by_others": s["confirmed_by_others"], "tips": s["tips"]})
    order = {"verified": 0, "attested": 1, "self": 2}
    out.sort(key=lambda x: (order[x["tier"]], -x["fixes"]))
    # hours saved: others reused this person's fix through Ustaad, faster than the old average
    before = [r["downtime_minutes"] for r in recs if r["datetime"][:10] < started and r["downtime_minutes"]]
    base = statistics.median(before) if before else 0
    reused = [r for r in recs if r["credited_to"] == person_id and r["person_id"] != person_id and r["outcome"] == "fixed"]
    saved_h = round(sum(max(0, base - (r["downtime_minutes"] or 0)) for r in reused) / 60, 1)
    return {"person": p, "industry": pk["name"], "org": pk["org"]["name"], "skills": out,
            "totals": {"fixes": len(fixed), "attempts": len(mine), "tips": len(tips),
                       "reused_by_others": len(reused), "hours_saved": saved_h,
                       "verified": sum(1 for s in out if s["tier"] == "verified")}}


# ---------- cross-site learning ----------
def cross_site(industry):
    sites = {s["id"]: s["name"] for s in packs.get(industry).get("sites", [])}
    if len(sites) < 2:
        return []
    by_model = defaultdict(list)
    for a in packs.assets(industry):
        if a.get("model"):
            by_model[a["model"]].append(a)
    out = []
    for model, items in by_model.items():
        msites = {a.get("site") for a in items}
        if len(msites) < 2:
            continue
        for a in items:
            others = [b for b in items if b.get("site") != a.get("site")]
            learned = [r for r in _live(industry) if r["outcome"] == "fixed" and r["asset_id"] in {b["id"] for b in others}]
            if learned:
                out.append({"asset_id": a["id"], "site": sites.get(a.get("site")), "model": model,
                            "learns_from": [{"asset_id": r["asset_id"], "site": sites.get((packs.asset(industry, r["asset_id"]) or {}).get("site")),
                                             "problem": r["problem"], "date": r["datetime"][:10],
                                             "person": (packs.person(industry, r["person_id"]) or {}).get("name")} for r in learned][-5:]})
    return out


# ---------- before / after and money ----------
def stats(industry):
    pk = packs.get(industry)
    started = pk["org"].get("ustaad_started", "2026-09-01")
    incs = incidents(industry)
    monthly = defaultdict(lambda: {"incidents": 0, "downtime": 0, "failed": 0, "cost": 0})
    for i in incs:
        k = i["start"][:7]
        monthly[k]["incidents"] += 1
        monthly[k]["downtime"] += i["downtime_minutes"]
        monthly[k]["failed"] += i["failed_attempts"]
        monthly[k]["cost"] += incident_cost(industry, i)
    series = [{"month": k, "incidents": v["incidents"], "mttr_minutes": round(v["downtime"] / v["incidents"]),
               "failed_attempts": v["failed"], "cost": v["cost"]} for k, v in sorted(monthly.items())]

    def block(items):
        if not items:
            return {"incidents": 0, "mttr_minutes": 0, "failed_fix_rate": 0, "avg_cost": 0}
        att = sum(len(i["attempts"]) for i in items)
        return {"incidents": len(items), "mttr_minutes": round(sum(i["downtime_minutes"] for i in items) / len(items)),
                "failed_fix_rate": round(100 * sum(i["failed_attempts"] for i in items) / att),
                "avg_cost": round(sum(incident_cost(industry, i) for i in items) / len(items))}

    before = block([i for i in incs if i["start"][:10] < started])
    after = block([i for i in incs if i["start"][:10] >= started])
    saved = max(0, (before["avg_cost"] - after["avg_cost"]) * after["incidents"]) if after["incidents"] else 0
    return {"monthly": series, "before": before, "after": after, "ustaad_started": started,
            "money_saved": saved, "total_incidents": len(incs), "records": len(_live(industry)),
            "tips": len(store.tips(industry)), "public_records": len(packs.public_records(industry)),
            "cost_per_hour": pk.get("cost_per_hour", 0), "currency": "₹"}


# ---------- "answers with charts" for number questions ----------
DATA_Q = re.compile(r"\b(which|how many|how much|most|least|top|compare|chart|graph|trend|total|average|per month|"
                    r"kitn[ae]|sabse|zyada|kam)\b", re.I)
DATA_W = re.compile(r"\b(downtime|hours?|time|breakdowns?|failures?|times|cost|money|records?|problems?|incidents?|"
                    r"faults?|complaints?|issues?|fixes|month|people|who)\b", re.I)


def is_data_question(q):
    return bool(DATA_Q.search(q or "") and DATA_W.search(q or ""))


def answer_with_chart(industry, q):
    L = packs.get(industry)["labels"]
    recs = _live(industry)
    ql = q.lower()
    metric = "downtime" if re.search(r"downtime|hours?|time|lost|band", ql) else ("cost" if re.search(r"cost|money|₹|rs", ql) else "count")
    if re.search(r"\bwho\b|people|person|technician|chef|nurse|mechanic|engineer|best|expert", ql):
        dim, key = "person", lambda r: (packs.person(industry, r["person_id"]) or {}).get("name", r["person_id"])
        recs = [r for r in recs if r["outcome"] == "fixed"]
        metric = "count" if metric == "downtime" and "fix" in ql else metric
    elif re.search(r"month|trend|over time", ql):
        dim, key = "month", lambda r: r["datetime"][:7]
    elif re.search(r"problem|fault|issue|type|kind|complaint", ql):
        dim, key = "problem", lambda r: r["problem"]
    else:
        dim, key = "asset", lambda r: r["asset_id"]
    agg = defaultdict(float)
    for r in recs:
        if metric == "downtime":
            agg[key(r)] += (r["downtime_minutes"] or 0) / 60
        elif metric == "cost":
            agg[key(r)] += (r["downtime_minutes"] or 0) / 60 * _cost_per_hour(industry, r["asset_id"]) + (r["cost"] or 0)
        else:
            agg[key(r)] += 1
    items = sorted(agg.items(), key=(lambda kv: kv[0]) if dim == "month" else (lambda kv: -kv[1]))
    if dim != "month":
        items = items[:10]
    unit = {"downtime": "hours", "cost": "₹", "count": "records" if dim != "person" else "fixes"}[metric]
    dim_name = {"person": L["person"] + "s", "month": "Month", "problem": L["problem"], "asset": L["asset"]}[dim]
    title = f"{ {'downtime': L['downtime'] + ' (hours)', 'cost': 'Cost (₹)', 'count': 'Number of ' + unit}[metric] } by {dim_name.lower()}"
    if not items:
        return {"title": title, "labels": [], "values": [], "summary": "No data yet."}
    top = items[0] if dim != "month" else max(items, key=lambda kv: kv[1])
    fmt = (lambda v: f"₹{v:,.0f}") if metric == "cost" else (lambda v: f"{v:.1f} h" if metric == "downtime" else f"{v:.0f}")
    summary = f"Top: {top[0]} with {fmt(top[1])}. Based on {len(recs)} records in memory."
    return {"title": title.strip(), "labels": [str(k) for k, _ in items], "values": [round(v, 1) for _, v in items],
            "unit": unit, "summary": summary, "metric": metric, "dimension": dim}


# ---------- onboarding quiz from real past incidents ----------
def quiz(industry, n=6, seed=None):
    rnd = random.Random(seed or datetime.now().strftime("%Y%m%d%H"))
    fixed = [r for r in _live(industry) if r["outcome"] == "fixed" and r["cause"] and r["source"] == "seed"]
    by_cause = {}
    for r in fixed:
        by_cause.setdefault(r["cause"], r)
    pool = list(by_cause.values())
    rnd.shuffle(pool)
    causes = list(by_cause.keys())
    qs = []
    for r in pool[:n]:
        a = packs.asset(industry, r["asset_id"]) or {"id": r["asset_id"], "name": ""}
        wrong = rnd.sample([c for c in causes if c != r["cause"]], k=min(3, len(causes) - 1))
        opts = wrong + [r["cause"]]
        rnd.shuffle(opts)
        who = (packs.person(industry, r["person_id"]) or {}).get("name", "")
        qs.append({"id": r["id"], "question": f"{a['id']} ({a['name']}): {r['symptom']} What was the real cause?",
                   "options": opts, "answer": opts.index(r["cause"]),
                   "explain": f"{who} found this on {r['datetime'][:10]}: {r['action']}"})
    return {"questions": qs}
