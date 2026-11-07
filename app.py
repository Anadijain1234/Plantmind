"""
Ustaad — the expert who never leaves.
One expert-memory engine (Hindsight + Groq) with industry packs: factory, restaurant, hospital operations,
car garage and IT on-call. Run locally:  python app.py   →  http://localhost:5000
"""
import base64
import os

from flask import Flask, jsonify, redirect, request, send_from_directory

from ustaad import agent, backup, config, custom, insights, llm, machines, packs, store
from ustaad.memory import memory

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
store.init()


def ok(data):
    return jsonify(data)


def err(msg, code=400):
    return jsonify({"error": str(msg)}), code


@app.errorhandler(ValueError)
def _value_error(e):
    return err(e, 400)


@app.errorhandler(PermissionError)
def _perm_error(e):
    return err(e, 403)


def body():
    return request.get_json(silent=True) or {}


def _ind(industry):
    packs.get(industry)  # raises ValueError if unknown
    return industry


# ---------- pages ----------
@app.get("/")
def index():
    return send_from_directory("static", "index.html")


@app.get("/p/<industry>/<person_id>")
def passport_link(industry, person_id):
    return redirect(f"/#/passport/{industry}/{person_id}")


@app.get("/m/<industry>/<asset_id>")
def machine_link(industry, asset_id):  # the QR sticker on a machine points here
    return redirect(f"/#/m/{industry}/{asset_id}")


@app.get("/health")
def health():
    return ok({"ok": True})


# ---------- general ----------
@app.get("/api/status")
def status():
    return ok({"memory": memory.mode, "memory_error": memory.last_error, "llm": llm.available(),
               "llm_model": config.GROQ_MODEL if llm.groq_available() else (config.SARVAM_CHAT_MODEL if llm.sarvam_available() else None),
               "groq": llm.groq_available(), "sarvam": llm.sarvam_available(), "llm_error": llm.last_error,
               "autosave": backup.status(),
               "banks": {i: config.bank_id(i) for i in packs.ids()}})


@app.get("/api/industries")
def industries():
    return ok({"industries": [packs.summary(i) for i in packs.ids()],
               "coming_soon": [{"name": "Farming", "icon": "🌾"}, {"name": "Hotels", "icon": "🏨"},
                               {"name": "Construction", "icon": "🏗️"}, {"name": "Aviation", "icon": "✈️"}]})


@app.post("/api/packs/custom")
def create_pack():
    b = body()
    out = custom.create(b.get("name"), b.get("description", ""))
    backup.mark_dirty()
    return ok(out)


@app.get("/api/i/<industry>/pack")
def pack(industry):
    p = packs.get(_ind(industry))
    return ok(packs.summary(industry) | {"assets": packs.assets(industry), "people": p["people"], "panels": p.get("panels", []),
                                         "checklists": p.get("checklists", []), "lookup": p.get("lookup")})


@app.post("/api/i/<industry>/ask")
def ask(industry):
    b = body()
    return ok(agent.ask(_ind(industry), b.get("asset_id"), b.get("problem"), bool(b.get("use_memory", True)), b.get("language", "en")))


@app.post("/api/i/<industry>/feedback")
def feedback(industry):
    b = body()
    return ok(agent.feedback(_ind(industry), b.get("ask_id"), b.get("result"), b.get("person_id"), b.get("note", ""),
                             b.get("downtime_minutes"), b.get("action_done", ""), b.get("steps_done"), b.get("asset_id")))


@app.post("/api/i/<industry>/log")
def log(industry):
    return ok(agent.log_record(_ind(industry), body()))


@app.post("/api/i/<industry>/smart-log")
def smart_log(industry):
    b = body()
    return ok(agent.smart_log(_ind(industry), b.get("text"), b.get("person_id")))


@app.post("/api/i/<industry>/tips")
def tips(industry):
    b = body()
    return ok(agent.add_tip(_ind(industry), b.get("person_id"), b.get("asset_id", "ALL"), b.get("text"), b.get("source_ref", "")))


@app.get("/api/i/<industry>/memories")
def memories(industry):
    _ind(industry)
    from ustaad.memory import all_memories
    kind = request.args.get("kind")
    aid = request.args.get("asset_id")
    flagged = store.flagged_keys(industry)
    items = [m for m in all_memories(industry) if (not kind or m["kind"] == kind) and (not aid or m["asset_id"] in (aid, "ALL"))]
    items.sort(key=lambda m: m["timestamp"], reverse=True)
    cards = [agent.memory_card(industry, {**m, "origin": "store"}, "") | {"flagged": m["key"] in flagged} for m in items[:400]]
    return ok({"memories": cards, "total": len(items)})


@app.get("/api/i/<industry>/pending")
def pending(industry):
    return ok({"pending": store.pending(_ind(industry))})


@app.post("/api/i/<industry>/approve")
def approve(industry):
    b = body()
    return ok(agent.approve(_ind(industry), b.get("key"), b.get("role"), b.get("approver_id"), b.get("ok", True)))


@app.post("/api/i/<industry>/flag")
def flag(industry):
    b = body()
    if not b.get("key"):
        raise ValueError("Missing memory key")
    if b.get("unflag"):
        store.remove_flag(b["key"])
        return ok({"ok": True, "message": "Restored."})
    store.add_flag(_ind(industry), b["key"], b.get("reason", "wrong"), b.get("by", ""))
    return ok({"ok": True, "message": "Flagged — Ustaad will not use this memory any more."})


@app.get("/api/i/<industry>/flags")
def flags(industry):
    return ok({"flags": store.flags(_ind(industry))})


@app.get("/api/i/<industry>/problems")
def problems(industry):
    return ok({"problems": agent.problems_for(_ind(industry), request.args.get("asset_id"))})


@app.post("/api/i/<industry>/playbook")
def playbook(industry):
    b = body()
    return ok(agent.playbook(_ind(industry), b.get("asset_id"), b.get("problem"), b.get("language", "en")))


@app.get("/api/i/<industry>/risk")
def risk(industry):
    return ok(insights.knowledge_risk(_ind(industry)))


@app.get("/api/i/<industry>/interview")
def interview(industry):
    return ok(agent.interview(_ind(industry), request.args.get("person_id"), request.args.get("language", "en")))


@app.post("/api/i/<industry>/interview/answer")
def interview_answer(industry):
    b = body()
    return ok(agent.answer_interview(_ind(industry), b.get("person_id"), b.get("asset_id"), b.get("question"), b.get("answer")))


@app.get("/api/i/<industry>/shift-report")
def shift_report(industry):
    return ok(agent.shift_report(_ind(industry), int(request.args.get("hours", 24)), request.args.get("language", "en")))


@app.get("/api/i/<industry>/coverage")
def coverage(industry):
    return ok(insights.coverage(_ind(industry)))


@app.get("/api/i/<industry>/leaderboard")
def leaderboard(industry):
    return ok(insights.leaderboard(_ind(industry)))


@app.get("/api/i/<industry>/skills")
def skills(industry):
    return ok(insights.skill_map(_ind(industry)))


@app.get("/api/i/<industry>/passport/<person_id>")
def passport(industry, person_id):
    return ok(insights.passport(_ind(industry), person_id))


@app.get("/api/i/<industry>/repeat")
def repeat(industry):
    return ok({"repeat": insights.repeat_failures(_ind(industry))})


@app.get("/api/i/<industry>/stats")
def stats(industry):
    return ok(insights.stats(_ind(industry)))


@app.get("/api/i/<industry>/cross-site")
def cross_site(industry):
    return ok({"links": insights.cross_site(_ind(industry))})


@app.get("/api/i/<industry>/quiz")
def quiz(industry):
    return ok(insights.quiz(_ind(industry), seed=request.args.get("seed")))


@app.post("/api/i/<industry>/photo")
def photo(industry):
    f = request.files.get("image")
    if not f:
        raise ValueError("No photo received")
    b64 = base64.b64encode(f.read()).decode()
    return ok(agent.read_photo(_ind(industry), b64, f.mimetype or "image/jpeg", request.form.get("asset_id")))


@app.post("/api/i/<industry>/reset")
def reset(industry):
    store.load_seed(_ind(industry))
    backup.mark_dirty()
    return ok({"ok": True, "message": "Demo data restored for this industry."})


@app.post("/api/translate")
def translate():
    b = body()
    return ok(agent.translate(b.get("texts") or [], b.get("language", "hi")))


@app.post("/api/voice")
def voice():
    f = request.files.get("audio")
    if not f:
        raise ValueError("No audio received")
    text, engine = llm.transcribe(f.read(), f.filename or "voice.webm", request.form.get("language") or None)
    if not text:
        raise ValueError("Voice needs the Sarvam or Groq key" if not llm.available() else f"Could not understand the audio: {llm.last_error}")
    return ok({"text": text, "engine": engine})


@app.post("/api/speak")
def speak():
    b = body()
    audio = llm.speak(b.get("text", ""), b.get("language", "en"))
    if not audio:
        raise ValueError("Speaking needs the Sarvam key" if not llm.sarvam_available() else f"Could not speak: {llm.last_error}")
    return ok({"audio": audio, "mime": "audio/wav"})


# ---------- My machines ----------
@app.get("/api/i/<industry>/machines")
def machine_list(industry):
    return ok({"machines": machines.summary_list(_ind(industry))})


@app.get("/api/i/<industry>/machines/<asset_id>")
def machine_profile(industry, asset_id):
    return ok(machines.profile(_ind(industry), asset_id))


@app.post("/api/i/<industry>/machines")
def machine_save(industry):
    b = body()
    return ok(machines.save(_ind(industry), b.get("machine") or {}, b.get("person_id"), b.get("role")))


@app.post("/api/i/<industry>/machines/read")
def machine_read(industry):
    """Fill the 'add machine' form from a PDF manual, a product web page, a nameplate photo or pasted text."""
    _ind(industry)
    f = request.files.get("file")
    if f:
        data = f.read()
        name = f.filename or "upload"
        if (f.mimetype or "").startswith("image/"):
            return ok(machines.from_photo(industry, base64.b64encode(data).decode(), f.mimetype))
        if data[:4] != b"%PDF":
            raise ValueError("Please upload a PDF manual or a photo")
        return ok(machines.extract(industry, machines.pdf_text(data), f"PDF manual: {name}"))
    b = body()
    if b.get("url"):
        return ok(machines.extract(industry, machines.fetch_page(b["url"]), b["url"]))
    return ok(machines.extract(industry, b.get("text", ""), "Typed in by the team"))


@app.post("/api/i/<industry>/machines/<asset_id>/stock")
def machine_stock(industry, asset_id):
    b = body()
    return ok(machines.set_stock(_ind(industry), asset_id, b.get("part"), b.get("stock")))


@app.post("/api/i/<industry>/sensors/alert")
def sensor_alert(industry):
    b = body()
    return ok(machines.sensor_alert(_ind(industry), b.get("asset_id"), b.get("reading") or {}))


@app.post("/api/i/<industry>/sensors/reading")
def sensor_reading(industry):
    """For a real sensor gateway: {"asset_id": "CNC-3", "vib": 2.1, "temp": 41}"""
    b = body()
    return ok(machines.sensor_reading(_ind(industry), b.get("asset_id"), b.get("vib", 0), b.get("temp", 0)))


# ---------- one-time Hindsight seeding from the deployed app (protected by SEED_TOKEN) ----------
SEED = {"running": False, "log": []}


@app.route("/api/admin/seed", methods=["GET", "POST"])
def admin_seed():
    token = os.getenv("SEED_TOKEN", "")
    if not token or request.args.get("token") != token:
        return err("Set SEED_TOKEN in Render and open /api/admin/seed?token=<your token>", 403)
    if not memory.cloud:
        return err("HINDSIGHT_API_KEY is not set on the server", 400)
    if SEED["running"]:
        return ok({"running": True, "log": SEED["log"][-20:]})
    import threading
    from ustaad.memory import all_memories
    only = request.args.get("industry")

    def _run():
        SEED.update(running=True, log=[])
        for ind in ([only] if only else packs.ids()):
            try:
                memory.cloud.setup_bank(ind)
                SEED["log"].append(f"{ind}: bank created")
            except Exception as e:
                SEED["log"].append(f"{ind}: bank — {str(e)[:100]}")
            mems = all_memories(ind)
            for i in range(0, len(mems), 25):
                try:
                    memory.cloud.retain_batch(ind, mems[i:i + 25])
                    SEED["log"].append(f"{ind}: saved {min(i + 25, len(mems))}/{len(mems)}")
                except Exception as e:
                    SEED["log"].append(f"{ind}: FAILED at {i} — {str(e)[:150]}")
        SEED["log"].append("DONE")
        SEED["running"] = False
    if config.ON_VERCEL or request.args.get("sync") == "1":  # serverless: finish inside this request
        _run()
        return ok({"done": True, "log": SEED["log"]})
    threading.Thread(target=_run, daemon=True).start()
    return ok({"started": True, "message": "Seeding started. Refresh this page to see progress."})


# ---------- factory extras ----------
@app.get("/api/factory/sensors")
def sensors():
    return ok(packs.processed("factory_sensors.json") | {"alerts": agent.sensor_alerts()})


@app.get("/api/factory/fleet")
def fleet():
    return ok(packs.processed("factory_fleet.json"))


@app.get("/api/factory/ai4i")
def ai4i():
    return ok(packs.processed("factory_ai4i.json"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=False)
