/* Ustaad frontend — plain JavaScript, no build step. */
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const app = $("#app");
const S = { status: null, industries: null, packs: {}, ind: null, role: null, person: null, lang: "en", prefill: null, charts: [] };

const TOOLS = {
  ask: ["💬", "Ask Ustaad"], log: ["✍️", "I fixed something"], memory: ["🧠", "Memory"], approvals: ["✅", "Approvals"],
  playbook: ["📋", "SOP / playbook"], risk: ["⚠️", "Risk radar"], interview: ["🎤", "Exit interview"], shift: ["🔁", "Shift report"],
  skills: ["🧩", "Skill map"], passport: ["🏅", "Skill passport"], stats: ["📈", "ROI dashboard"], quiz: ["🎓", "Learn (quiz)"],
  sensors: ["📡", "Live sensors"], fleet: ["🔮", "Failure prediction"], check: ["🧮", "Failure check"], dishes: ["🍽️", "Customer & hygiene data"],
  checklist: ["✔️", "OT checklist"], devices: ["🩺", "Device reports"], obd: ["🔧", "OBD codes"], outages: ["🌐", "Outage library"],
  machines: ["🏭", "My machines"], coverage: ["🗺️", "Knowledge coverage"], leaderboard: ["🏆", "Expert leaderboard"],
};
// one plain line on top of every screen: what is this?
const HELP = {
  ask: "Describe a problem. Ustaad finds what your team did before, who did it and whether it worked.",
  log: "Just fixed something? Say it in any language. It becomes a memory for the next person.",
  machines: "Every machine in one place: details, health, service due, spare parts, fix history, who knows it best — and a QR sticker.",
  memory: "Everything Ustaad remembers, with how much to trust each memory.",
  approvals: "New knowledge waits here until a senior checks it.",
  playbook: "One printable standard procedure, built only from fixes that actually worked.",
  risk: "Which know-how leaves the building if a senior person leaves.",
  interview: "Questions for a leaving expert — only about things nobody has written down yet.",
  shift: "A handover note built from real records, sensor alerts and low spare parts.",
  skills: "Who has proven fixes on which machine.",
  passport: "Proof of a person's skills, built from fixes that worked.",
  stats: "ROI dashboard: downtime hours saved, repeat failures avoided, fixed vs failed, ₹ saved — before vs after Ustaad.",
  coverage: "How much of each machine's know-how is captured, and where only one person knows it.",
  leaderboard: "Who shares knowledge that others actually use. Points for fixes that worked and fixes others reused.",
  quiz: "New joiners learn from this team's own past problems.",
  sensors: "Sensors say something is wrong. Ustaad logs it by itself and shows what fixed it last time.",
  fleet: "A model trained on public data guesses which machine may fail next.",
  check: "Enter machine settings — rules from 10,000 public runs say what may fail.",
  dishes: "Real customer-complaint and hygiene data behind the kitchen memories.",
  checklist: "The WHO surgical safety checklist plus this hospital's own additions.",
  devices: "Real FDA reports about ventilators and pumps.",
  obd: "What a car's error code means, plus what our mechanics found.",
  outages: "240 real public outage write-ups next to the team's own incidents.",
};
const GROUPS = [["Daily work", ["ask", "log", "machines"]], ["Team knowledge", ["memory", "approvals", "playbook", "quiz", "interview", "leaderboard"]],
  ["For managers", ["stats", "coverage", "risk", "shift", "skills", "passport"]]];
const OUTCOME = { fixed: "Worked", failed_again: "Didn't work", temporary: "Temporary", open: "Still open" };
const TIER = { verified: ["b-verified", "✔ Verified"], tested: ["b-tested", "Tested once"], unreviewed: ["b-unreviewed", "Unreviewed"],
  failed: ["b-failed", "✖ Didn't work"], public: ["b-public", "Public record"], attested: ["b-attested", "Attested"], self: ["b-self", "Self-declared"],
  manual: ["b-manual", "📘 Maker's manual"], insight: ["b-insight", "🧠 Pattern Hindsight learned"], hfact: ["b-insight", "🧠 From Hindsight"], sensor: ["b-verified", "📡 Sensor-confirmed"] };
const toolName = (t) => (t === "machines" && S.ind && pack() ? `My ${L().assets.toLowerCase()}` : TOOLS[t][1]);
const store = { get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* ignore */ } } };

// ---------- helpers ----------
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmtDate = (d) => { if (!d) return ""; const x = new Date(d.slice(0, 10)); return isNaN(x) ? d : x.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }); };
const rupees = (n) => "₹" + Math.round(n || 0).toLocaleString("en-IN");
const spin = '<span class="spinner"></span>';
function toast(msg, kind = "", ms = 4200) {
  const t = $("#toast"); t.className = "toast " + kind; t.innerHTML = msg; t.classList.remove("hidden");
  clearTimeout(t._h); t._h = setTimeout(() => t.classList.add("hidden"), ms);
}
async function api(path, opts = {}) {
  const o = { ...opts };
  if (o.json) { o.method = o.method || "POST"; o.headers = { "Content-Type": "application/json" }; o.body = JSON.stringify(o.json); delete o.json; }
  const r = await fetch(path, o);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || `Request failed (${r.status})`);
  return data;
}
function tierBadge(t) { const [c, l] = TIER[t?.tier || t] || ["b-src", t?.tier || t]; return `<span class="badge ${c}" title="${esc(t?.label || "")}">${l}</span>`; }
function clearCharts() { S.charts.forEach((c) => c.destroy()); S.charts = []; }
const PALETTE = ["#e8833a", "#16202e", "#0f766e", "#1d4ed8", "#b91c1c", "#7c3aed", "#ca8a04", "#64748b"];
function pack() { return S.packs[S.ind]; }
const nm = (a) => { const n = String(a?.name || ""); return a?.id && n.startsWith(a.id) ? n.slice(a.id.length).replace(/^\s*[·:—-]\s*/, "") || n : n; };
function L() { return pack().labels; }
function assetOptions(selected, includeAll = false, includeAny = false) {
  const p = pack(); const bySite = {};
  p.assets.forEach((a) => { (bySite[a.site] = bySite[a.site] || []).push(a); });
  let h = includeAll ? `<option value="ALL">All ${esc(L().assets.toLowerCase())}</option>` : "";
  if (includeAny) h += `<option value="ANY" ${selected === "ANY" ? "selected" : ""}>🤷 Not sure — search everything</option>`;
  for (const s of p.sites) {
    h += `<optgroup label="${esc(s.name)}">` + (bySite[s.id] || []).map((a) => `<option value="${a.id}" ${a.id === selected ? "selected" : ""}>${esc(a.id)} — ${esc(nm(a))}</option>`).join("") + "</optgroup>";
  }
  return h;
}
function personOptions(selected) { return pack().people.map((p) => `<option value="${p.id}" ${p.id === selected ? "selected" : ""}>${esc(p.name)} — ${esc(p.role)}</option>`).join(""); }
function personName(id) { return (pack().people.find((p) => p.id === id) || {}).name || id; }
function roleObj() { return pack().roles.find((r) => r.id === S.role) || pack().roles[0]; }
function go(hash) { if (location.hash === hash) route(); else location.hash = hash; }

// ---------- voice & photo ----------
let recorder = null;
async function toggleVoice(btn, onText) {
  if (recorder && recorder.state === "recording") { recorder.stop(); return; }
  if (!navigator.mediaDevices?.getUserMedia) { toast("This browser can't record audio."); return; }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const chunks = []; recorder = new MediaRecorder(stream);
    recorder.ondataavailable = (e) => chunks.push(e.data);
    recorder.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop()); btn.classList.remove("rec"); btn.innerHTML = spin;
      try {
        const fd = new FormData(); fd.append("audio", new Blob(chunks, { type: "audio/webm" }), "voice.webm");
        const lang = { hi: "hi", kn: "kn", hinglish: "hi" }[S.lang]; if (lang) fd.append("language", lang);
        const r = await api("/api/voice", { method: "POST", body: fd }); onText(r.text); toast(`🎙️ Got it${r.engine ? " (" + esc(r.engine) + ")" : ""}: ` + esc(r.text.slice(0, 120)));
      } catch (e) { toast(esc(e.message), "alert"); }
      btn.innerHTML = "🎙️";
    };
    recorder.start(); btn.classList.add("rec"); btn.innerHTML = "■"; toast("Recording… tap ■ to stop. Hindi, Kannada or English.");
  } catch (e) { toast("Microphone not allowed: " + esc(e.message), "alert"); }
}
function pickPhoto(assetId, onResult) {
  const inp = document.createElement("input"); inp.type = "file"; inp.accept = "image/*"; inp.capture = "environment";
  inp.onchange = async () => {
    const f = inp.files[0]; if (!f) return; toast(spin + " Reading the photo…", "", 20000);
    try { const fd = new FormData(); fd.append("image", f); if (assetId) fd.append("asset_id", assetId);
      const r = await api(`/api/i/${S.ind}/photo`, { method: "POST", body: fd }); onResult(r); toast("📷 " + esc(r.what_i_see || "Read the photo."));
    } catch (e) { toast(esc(e.message), "alert"); }
  };
  inp.click();
}

// ---------- status ----------
async function loadStatus() {
  try {
    S.status = await api("/api/status");
    const m = $("#chip-mem"), l = $("#chip-llm"); const cloud = S.status.memory.startsWith("Hindsight");
    m.className = "chip " + (cloud ? "on" : "off"); m.lastElementChild.textContent = cloud ? "Hindsight memory" : "Practice memory (offline)";
    m.title = S.status.memory_error || (cloud ? "One Hindsight memory bank per industry" : "Add HINDSIGHT_API_KEY to use Hindsight Cloud");
    l.className = "chip " + (S.status.llm ? "on" : "off");
    l.lastElementChild.textContent = S.status.groq && S.status.sarvam ? "Groq + Sarvam on" : S.status.groq ? "Groq AI on" : S.status.sarvam ? "Sarvam AI on" : "AI off (rule-based)";
    l.title = S.status.llm ? S.status.llm_model : "Add GROQ_API_KEY for AI answers, voice and photos";
    const sv = $("#chip-save"), au = S.status.autosave || {};
    if (au.enabled) { sv.classList.remove("hidden"); sv.className = "chip " + (au.ready && !au.last_error ? "on" : "off");
      sv.lastElementChild.textContent = au.ready && !au.last_error ? "💾 Auto-save on" : "💾 Auto-save paused";
      sv.title = au.last_error || `Everything added here is saved to ${au.where}${au.last_saved ? " · last saved " + au.last_saved.replace("T", " ") : ""} and comes back after a restart.`; }
  } catch (e) { /* ignore */ }
}

// ---------- home ----------
async function renderHome() {
  const d = S.industries || (S.industries = await api("/api/industries"));
  const total = d.industries.reduce((a, i) => a + i.counts.records + i.counts.tips + i.counts.public, 0);
  app.innerHTML = `
  <section class="hero">
    <div>
      <div class="kicker">Expert memory for any industry</div>
      <h1>When your best expert leaves,<br>their know-how shouldn't.</h1>
      <p class="lead">Ustaad remembers what your senior people did and whether it worked, gives it to the next person at the right moment, and gets better every time someone taps <b>worked</b> or <b>didn't work</b>.</p>
      <div class="row" style="margin-top:14px"><button class="btn accent big" id="try30">▶ Try it in 30 seconds</button>
        <span class="small muted">You become a new technician. A machine is whistling. See what Ustaad remembers.</span></div>
      <div id="home-roi" class="home-roi"></div>
    </div>
    <div class="loop">
      <div class="step"><b>1 · Capture</b><span class="small muted">Voice, text or photo — Hindi, Kannada, English</span></div>
      <div class="step"><b>2 · Recall</b><span class="small muted">The right fix, who did it, how often it worked</span></div>
      <div class="step"><b>3 · Learn</b><span class="small muted">Results make good fixes rise and bad ones sink</span></div>
    </div>
  </section>
  <div class="panel-head"><h2>Choose your industry</h2><span class="small muted">${total.toLocaleString("en-IN")} memories across ${d.industries.length} industries · one Hindsight memory bank each</span></div>
  <div class="grid g3">
    ${d.industries.map((i) => `
      <a class="card ind-card" href="#/i/${i.id}" style="--c:${i.color}">
        <span class="ico">${i.icon}</span><h3>${esc(i.name)}</h3><span class="small muted">${esc(i.tagline)}</span>
        <span class="meta"><span class="badge b-src">${i.counts.records + i.counts.tips} team memories</span><span class="badge b-public">${i.counts.public} public records</span><span class="badge b-src">${i.sites.length} sites</span></span>
      </a>`).join("")}
    <div class="card" style="border-top:5px dashed #0e7490"><span class="ico" style="font-size:30px">＋</span><h3>Build your own industry</h3>
      <span class="small muted">Type any industry. Ustaad creates the roles, equipment and starter questions — memory starts empty and learns as people log work.</span>
      <div class="row" style="margin-top:10px"><input class="field" id="cu-name" placeholder="e.g. bakery, textile mill, solar farm" style="flex:1;min-width:140px"><button class="btn primary" id="cu-go">Create</button></div>
      <div class="row" style="margin-top:8px">${d.coming_soon.map((c) => `<span class="badge b-src">${c.icon} ${esc(c.name)}</span>`).join("")}</div></div>
  </div>
  <h2 style="margin-top:28px">What could Ustaad save you?</h2>
  <div class="card"><div class="roi">
    <div><label class="f">Breakdowns / problems per month</label><input class="field" id="roi-n" type="number" value="20"></div>
    <div><label class="f">Hours lost each time</label><input class="field" id="roi-h" type="number" value="2" step="0.5"></div>
    <div><label class="f">Cost of one lost hour (₹)</label><input class="field" id="roi-c" type="number" value="6000"></div>
    <div><label class="f">Time saved with Ustaad (%)</label><input class="field" id="roi-p" type="number" value="40"></div>
    <div class="out"><span class="small">Estimated saving per year</span><b id="roi-out">—</b><span class="tiny" style="opacity:.75">Demo factory data shows repair time falling about 50% after Ustaad started. Your result will differ.</span></div>
  </div></div>
  <p class="tiny muted" style="margin-top:20px">Demo data: people and companies are fictional; facts come from public sources (ISO 10816, FSSAI, WHO checklist, FDA MAUDE, NHTSA, NYC inspections, Zomato reviews, public post-mortems, Microsoft Azure & AI4I datasets).</p>`;
  api("/api/i/factory/stats").then((d) => { const r = d.roi || {}; const box = $("#home-roi"); if (!box) return;
    box.innerHTML = `<span class="tiny muted">In the sample factory since Ustaad started:</span>
      <span><b>${r.hours_saved} h</b> downtime saved</span><span><b>${r.repeat_failures_avoided}</b> repeat failures avoided</span>
      <span><b>${r.fixed_rate}%</b> of fixes worked</span><span><b>${rupees(d.money_saved)}</b> saved</span>`; }).catch(() => {});
  $("#try30").onclick = () => { S.prefill = { asset_id: "CNC-3", problem: "CNC-3 alarm 2041 with a whistling sound at high rpm", auto: true }; go("#/i/factory/technician/ask"); };
  $("#cu-go").onclick = async () => {
    const btn = $("#cu-go"); btn.disabled = true; btn.innerHTML = spin;
    try { const r = await api("/api/packs/custom", { json: { name: $("#cu-name").value } }); S.industries = null; delete S.packs[r.id];
      toast(`✔ Created ${esc(r.name)} (${esc(r.generated_by)}). Memory is empty — log work and watch it learn.`); go(`#/i/${r.id}`); }
    catch (e) { toast(esc(e.message), "alert"); btn.disabled = false; btn.textContent = "Create"; }
  };
  const calc = () => { const n = +$("#roi-n").value, h = +$("#roi-h").value, c = +$("#roi-c").value, p = +$("#roi-p").value;
    $("#roi-out").textContent = rupees(n * 12 * h * c * p / 100); };
  $$(".roi input").forEach((i) => (i.oninput = calc)); calc();
}

// ---------- industry: role picker ----------
async function loadPack(ind) { if (!S.packs[ind]) S.packs[ind] = await api(`/api/i/${ind}/pack`); S.ind = ind; return S.packs[ind]; }
async function renderRoles(ind) {
  const p = await loadPack(ind);
  app.innerHTML = `
  <div class="crumbs"><a href="#/">Industries</a> › <span>${esc(p.name)}</span></div>
  <div class="panel-head"><div><h1 style="font-size:34px">${p.icon} ${esc(p.org.name)}</h1><p class="muted">${esc(p.org.note)}</p></div>
    <div class="row">${p.sites.map((s) => `<span class="badge b-site">📍 ${esc(s.name)}</span>`).join("")}</div></div>
  ${p.banner ? `<div class="banner" style="margin-bottom:14px">🛡️ ${esc(p.banner)}</div>` : ""}
  <h2>Who are you today?</h2><p class="muted small" style="margin-top:-4px">Pick one. First time here? Start as the first one — the person on the floor.</p>
  <div class="grid g3">${p.roles.map((r, i) => `
    <button class="role-card ${i === 0 && !r.can_approve ? "rec" : ""}" data-role="${r.id}">${i === 0 && !r.can_approve ? '<span class="badge b-verified" style="float:right">Start here</span>' : ""}<h3>${esc(r.name)}</h3>
      <span class="small">${r.can_approve ? "Senior: uses knowledge, approves new memories, adds machines." : "On the floor: asks Ustaad, tells it what worked."}</span>
      <div class="tools">${r.tools.slice(0, 6).map((t) => `<span class="badge b-src">${TOOLS[t][0]} ${t === "machines" ? "My " + esc(p.labels.assets.toLowerCase()) : TOOLS[t][1]}</span>`).join("")}</div></button>`).join("")}
  </div>
  <h2 style="margin-top:26px">The people</h2>
  <div class="grid g4">${p.people.map((x) => `<div class="card"><b>${esc(x.name)}</b><div class="small muted">${esc(x.role)}</div>
    <div class="small">${x.experience_years} yrs · ${esc(x.speciality)}</div>${x.retiring_on ? `<span class="badge b-high" style="margin-top:6px">Leaving ${fmtDate(x.retiring_on)}</span>` : ""}</div>`).join("")}</div>`;
  $$(".role-card").forEach((b) => (b.onclick = () => { const r = p.roles.find((x) => x.id === b.dataset.role); go(`#/i/${ind}/${r.id}/${r.tools[0]}`); }));
}

// ---------- workspace ----------
function defaultPerson(role) {
  const ppl = pack().people; const r = pack().roles.find((x) => x.id === role);
  if (r?.can_approve) return (ppl.find((p) => !p.retiring_on) || ppl[0]).id;
  return [...ppl].sort((a, b) => a.experience_years - b.experience_years)[0].id;  // workers: the newest joiner
}
function sideLinks(ind, role, tools, tool) {
  const used = new Set(); let h = "";
  const link = (t) => `<a href="#/i/${ind}/${role}/${t}" class="${t === tool ? "on" : ""}"><span>${TOOLS[t][0]}</span><span>${esc(toolName(t))}</span></a>`;
  for (const [name, ids] of GROUPS) {
    const mine = ids.filter((t) => tools.includes(t)); if (!mine.length) continue;
    mine.forEach((t) => used.add(t)); h += `<div class="grp">${name}</div>` + mine.map(link).join("");
  }
  const rest = tools.filter((t) => !used.has(t) && TOOLS[t]);
  if (rest.length) h += `<div class="grp">Data & tools</div>` + rest.map(link).join("");
  return h;
}
async function renderWorkspace(ind, role, tool, sub) {
  const p = await loadPack(ind);
  if (S.role !== role || !S.person || !p.people.find((x) => x.id === S.person)) { S.role = role; S.person = defaultPerson(role); }
  const r = roleObj(); if (!r.tools.includes(tool)) tool = r.tools[0];
  app.innerHTML = `
  <div class="crumbs"><a href="#/">Industries</a> › <a href="#/i/${ind}">${esc(p.name)}</a> › <span>${esc(r.name)}</span> › <b>${esc(toolName(tool))}</b></div>
  <div class="ws">
    <nav class="side">
      <div class="who"><div class="tiny muted">${p.icon} ${esc(p.org.name)}</div><label class="tiny muted" style="display:block;margin-top:6px">You are</label>
        <select id="who" class="field" style="padding:5px 8px;font-size:13px">${personOptions(S.person)}</select></div>
      ${sideLinks(ind, role, r.tools, tool)}
    </nav>
    <section id="panel">${p.banner ? `<div class="banner" style="margin-bottom:12px">🛡️ ${esc(p.banner)}</div>` : ""}
      ${HELP[tool] ? `<div class="help no-print">ⓘ <b>What is this?</b> ${esc(HELP[tool])}</div>` : ""}<div id="tool"></div></section>
  </div>`;
  $("#who").onchange = (e) => { S.person = e.target.value; };
  clearCharts();
  const el = $("#tool");
  try { await (VIEWS[tool] || VIEWS.ask)(el, sub); } catch (e) { el.innerHTML = `<div class="card"><b>Something went wrong.</b><p class="muted">${esc(e.message)}</p></div>`; }
}

// ---------- ask ----------
const VIEWS = {};
VIEWS.ask = async (el) => {
  const p = pack(); const pre = S.prefill || {}; S.prefill = null;
  const aid = pre.asset_id || "ANY";
  el.innerHTML = `
  <div class="panel-head"><div><h2>Ask Ustaad</h2><p class="muted small">Describe the problem like you'd tell a senior. Speak, type or snap a photo.</p></div>
    <div class="toggle" id="memtog"><button class="on" data-v="1">Memory ON</button><button data-v="0">Memory OFF</button></div></div>
  <div class="card stack">
    <div><label class="f">${esc(L().asset)} <span class="muted small">(optional — pick one if you know it)</span></label><select id="a-asset" class="field">${assetOptions(aid, false, true)}</select></div>
    <div><label class="f">Problem</label><textarea id="a-q" class="field" placeholder="e.g. ${esc(p.questions[0])}">${esc(pre.problem || "")}</textarea></div>
    <div class="row">
      <button class="iconbtn" id="a-mic" title="Speak">🎙️</button><button class="iconbtn" id="a-cam" title="Photo of the problem">📷</button>
      <span class="spacer" style="flex:1"></span><button class="btn accent" id="a-go">Ask Ustaad →</button></div>
    <div class="row"><span class="tiny muted">Try:</span>${p.questions.map((q) => `<button class="sample">${esc(q)}</button>`).join("")}</div>
    <div id="a-photo" class="small muted"></div>
  </div>
  ${store.get("ustaad-hints") ? "" : `<div class="hints" id="hints"><b>3 things to know</b>
    <ol><li><b>Ask like you'd ask a senior</b> — type, 🎙️ speak (Hindi/Kannada/English) or 📷 snap the alarm screen.</li>
    <li><b>Memory ON / OFF</b> — OFF is a normal chatbot. ON is your team's real history. Try both.</li>
    <li><b>Tap ✔ Worked or ✖ Didn't work</b> after fixing — that is how Ustaad learns.</li></ol>
    <button class="btn sm" id="hints-x">Got it</button></div>`}
  <div id="a-out" style="margin-top:16px"></div>`;
  if ($("#hints-x")) $("#hints-x").onclick = () => { store.set("ustaad-hints", "1"); $("#hints").remove(); };
  let useMem = true;
  $$("#memtog button").forEach((b) => (b.onclick = () => { useMem = b.dataset.v === "1"; $$("#memtog button").forEach((x) => x.classList.toggle("on", x === b)); b.classList.toggle("off-state", !useMem); }));
  $$(".sample", el).forEach((b) => (b.onclick = () => {
    $("#a-q").value = b.textContent; const m = b.textContent.match(/\b([A-Z]{2,4}-[A-Z0-9]+)\b/);
    if (m && p.assets.find((a) => a.id === m[1])) $("#a-asset").value = m[1];
  }));
  $("#a-mic").onclick = (e) => toggleVoice(e.currentTarget, (t) => ($("#a-q").value = t));
  $("#a-cam").onclick = () => pickPhoto($("#a-asset").value, (r) => { $("#a-q").value = r.suggested_question || r.what_i_see; $("#a-photo").innerHTML = `📷 <b>I see:</b> ${esc(r.what_i_see)} ${(r.codes || []).map((c) => `<span class="badge b-src mono">${esc(c)}</span>`).join(" ")}`; });
  $("#a-go").onclick = async () => {
    const btn = $("#a-go"); btn.disabled = true; $("#a-out").innerHTML = `<div class="card">${spin} Searching ${useMem ? "memory" : "general knowledge"}…</div>`;
    try {
      const res = await api(`/api/i/${S.ind}/ask`, { json: { asset_id: $("#a-asset").value, problem: $("#a-q").value, use_memory: useMem, language: S.lang } });
      S.lastAsk = res; renderAnswer($("#a-out"), res); guideHook("asked", res);
    } catch (e) { $("#a-out").innerHTML = `<div class="card">${esc(e.message)}</div>`; }
    btn.disabled = false;
  };
  if (pre.problem && pre.auto) $("#a-go").click();
};

function renderAnswer(out, res) {
  if (res.mode === "chart") {
    out.innerHTML = `<div class="card"><div class="trust verified">📊 Answered from exact records</div><h3 style="margin-top:12px">${esc(res.chart.title)}</h3>
      <div id="ans-chart"></div><p>${esc(res.chart.summary)}</p></div>`;
    (res.chart.dimension === "month" ? MC.vbar : MC.hbar)($("#ans-chart"), { labels: res.chart.labels, values: res.chart.values, unit: res.chart.unit });
    return;
  }
  const a = res.answer, t = res.trust;
  if (t.level === "offtopic") {
    out.innerHTML = `<div class="card answer"><div class="trust offtopic">🛑 ${esc(t.label)}</div>
      <p style="font-size:16px;margin-top:12px">${esc(a.summary)}</p>
      <p class="small muted">Ustaad answers work problems at ${esc(pack().org.name)}. Try one of these:</p>
      <div class="row">${pack().questions.map((q) => `<button class="sample" data-q="${esc(q)}">${esc(q)}</button>`).join("")}</div>
      <p class="tiny muted" style="margin-top:10px">Written by ${esc(res.written_by)}</p></div>`;
    $$("[data-q]", out).forEach((b) => (b.onclick = () => { $("#a-q").value = b.dataset.q; window.scrollTo({ top: 0, behavior: "smooth" }); }));
    return;
  }
  const refs = (arr) => (arr || []).map((r) => `<span class="ref" data-ref="${esc(r)}">${esc(r)}</span>`).join("");
  const used = res.memories.filter((m) => m.used), other = res.memories.filter((m) => !m.used);
  const icon = { verified: "✔", off: "○", new: "✚" }[t.level] || "◐";
  const parts = a.parts_status || [];
  out.innerHTML = `
  <div class="grid" style="grid-template-columns:minmax(0,1.5fr) minmax(0,1fr)" id="ans-grid">
    <div class="card answer">
      <div class="trust ${t.level}">${icon} ${esc(t.label)}</div>
      <p style="font-size:16px;margin-top:12px" data-tr>${esc(a.summary)}</p>
      ${a.manual_vs_team ? `<div class="mvt">📘 vs 🧑‍🔧 <b>Manual says vs. team found:</b> <span data-tr>${esc(a.manual_vs_team)}</span></div>` : ""}
      ${a.check_first ? `<div class="first">👉 Check first: <span data-tr>${esc(a.check_first)}</span></div>` : ""}
      ${a.steps?.length ? `<h3>Steps</h3><ol id="steps">${a.steps.map((s) => `<li data-tr>${esc(s)}</li>`).join("")}</ol>
        <button class="btn sm" id="btn-guided">▶ Guided mode (tick each step)</button><ul class="guided hidden" id="guided"></ul>` : ""}
      ${parts.length ? `<div class="partsbox">📦 <b>Spare parts:</b> ${parts.map((x) => `<span class="badge ${x.status === "out" ? "b-failed" : x.status === "low" ? "b-unreviewed" : "b-verified"}">${esc(x.name)}${x.part_no ? " · " + esc(x.part_no) : ""} — ${x.status === "out" ? "0 in store, order now" : x.status === "low" ? `only ${x.stock} left` : x.status === "ok" ? `${x.stock} in store` : "stock unknown"}</span>`).join(" ")}</div>` : ""}
      ${res.use_memory ? `<div class="card" style="margin-top:14px;background:#fbf8f3" id="fb">
        <b>Did it work?</b> <span class="small muted">Your answer becomes a new memory — this is how Ustaad learns.</span>
        ${res.asset.id === "ANY" ? `<div style="margin-top:8px"><label class="f">Which ${esc(L().asset.toLowerCase())} was it?</label><select id="fb-asset" class="field">${assetOptions(guessAsset(res))}</select></div>` : ""}
        <div class="row" style="margin-top:8px"><select id="fb-who" class="field" style="max-width:260px">${personOptions(S.person)}</select>
          <input id="fb-min" class="field" type="number" placeholder="Minutes it took" style="max-width:150px">
          <input id="fb-note" class="field" placeholder="What you actually did (optional)" style="flex:1;min-width:180px"></div>
        <div class="row" style="margin-top:8px"><button class="btn ok" id="fb-ok">✔ Worked</button><button class="btn bad" id="fb-no">✖ Didn't work</button></div></div>` : ""}
      <details class="why" ${a.steps?.length ? "" : "open"}><summary>Show why — causes, what not to repeat, expert tip</summary>
        ${a.likely_causes?.length ? `<h3>Likely causes</h3><ul>${a.likely_causes.map((c) => `<li><b data-tr>${esc(c.cause)}</b> <span class="badge ${c.confidence === "high" ? "b-verified" : c.confidence === "medium" ? "b-tested" : "b-self"}">${esc(c.confidence)}</span>${refs(c.memory_refs)}<div class="small muted" data-tr>${esc(c.why)}</div></li>`).join("")}</ul>` : ""}
        ${a.avoid?.length ? `<h3>Don't repeat</h3><ul class="avoid">${a.avoid.map((x) => `<li><span data-tr>${esc(x.action)}</span>${refs(x.memory_refs)}<div class="small muted" data-tr>${esc(x.why)}</div></li>`).join("")}</ul>` : ""}
        ${a.expert_tip ? `<div class="tipbox" style="margin-top:12px">💡 <b>Expert tip:</b> <span data-tr>${esc(a.expert_tip)}</span></div>` : ""}
        ${!a.likely_causes?.length && !a.avoid?.length && !a.expert_tip ? '<p class="small muted">Nothing more to show.</p>' : ""}
      </details>
      <p class="small muted" style="margin-top:10px">${a.estimated_time ? `⏱ ${esc(a.estimated_time)} · ` : ""}${a.safety ? `🦺 <span data-tr>${esc(a.safety)}</span>` : ""}</p>
      <div class="row no-print" style="margin-top:6px">${S.status?.sarvam ? '<button class="btn sm accent" id="btn-listen">🔊 Listen</button>' : ""}<span class="small muted">Translate:</span>
        <button class="btn sm" data-tl="hi">हिन्दी</button><button class="btn sm" data-tl="kn">ಕನ್ನಡ</button><button class="btn sm" data-tl="en">English</button>
        <span class="tiny muted" style="margin-left:auto">Written by ${esc(res.written_by)} · memory: ${esc(res.memory_mode)}</span></div>
    </div>
    <div><div class="panel-head" style="margin-bottom:8px"><h3 style="margin:0">What I used from memory</h3><span class="small muted">${used.length} used${other.length ? ` · ${other.length} more searched` : ""}</span></div>
      <div id="mems">${used.length ? used.map(memCard).join("") : `<div class="card small muted">${res.use_memory ? "No memory matched this exact problem — the advice is general. When you fix it, tap Worked so the next person gets your fix." : "Memory is OFF — this is what a generic chatbot knows."}</div>`}
      ${other.length ? `<details class="also"><summary>Also searched — not about this problem (${other.length})</summary>${other.map(memCard).join("")}</details>` : ""}</div></div>
  </div>`;
  if (window.innerWidth < 900) $("#ans-grid").style.gridTemplateColumns = "1fr";
  $$(".ref", out).forEach((r) => (r.onclick = () => { const m = $(`#mems [data-ref="${r.dataset.ref}"]`); if (m) { const d = m.closest("details"); if (d) d.open = true; $$("#mems .mem").forEach((x) => x.classList.remove("hl")); m.classList.add("hl"); m.scrollIntoView({ behavior: "smooth", block: "center" }); } }));
  bindMemButtons(out);
  $$("[data-tl]", out).forEach((b) => (b.onclick = () => { out.dataset.lang = b.dataset.tl; const w = $("details.why", out); if (w && b.dataset.tl !== "en") w.open = true; translateBlock(out, b.dataset.tl, b); }));
  const lb = $("#btn-listen");
  if (lb) lb.onclick = async () => {
    const parts2 = $$("[data-tr]", out).slice(0, 8).map((n) => n.textContent);
    const lang = out.dataset.lang || (S.lang === "hinglish" ? "hi" : S.lang);
    lb.disabled = true; lb.innerHTML = spin;
    try { const r = await api("/api/speak", { json: { text: parts2.join(". "), language: lang } });
      const au = new Audio(`data:${r.mime};base64,${r.audio}`); au.play(); }
    catch (e) { toast(esc(e.message), "alert"); }
    lb.disabled = false; lb.textContent = "🔊 Listen";
  };
  const gb = $("#btn-guided");
  if (gb) gb.onclick = () => {
    const g = $("#guided"); g.classList.remove("hidden"); $("#steps").classList.add("hidden"); gb.classList.add("hidden");
    g.innerHTML = a.steps.map((s2, i) => `<li><input type="checkbox" data-i="${i + 1}"><span>${esc(s2)}</span></li>`).join("");
    $$("input", g).forEach((c) => (c.onchange = () => { c.parentElement.classList.toggle("done", c.checked);
      if ($$("input", g).every((x) => x.checked)) { toast("All steps done — tell Ustaad if it worked 👇"); $("#fb").scrollIntoView({ behavior: "smooth" }); } }));
  };
  const send = async (result) => {
    const steps = $$("#guided input:checked").map((c) => +c.dataset.i);
    try {
      const r = await api(`/api/i/${S.ind}/feedback`, { json: { ask_id: res.ask_id, result, person_id: $("#fb-who").value, downtime_minutes: +$("#fb-min").value || 0, action_done: $("#fb-note").value, steps_done: steps, asset_id: $("#fb-asset")?.value } });
      const ex = r.expert;
      $("#fb").innerHTML = `<b>${result === "fixed" ? "✔ Saved as WORKED" : "✖ Saved as DID NOT WORK"}</b><p class="small">${esc(r.message)}</p><p class="tiny muted">Saved to: ${esc(r.saved_to)}</p>
        ${ex ? `<div class="expertbox">📞 <b>Ask the expert:</b> ${esc(ex.name)} (${esc(ex.role)}) has fixed ${esc(ex.about)} ${ex.fixes} time(s).${ex.failed_times >= 2 ? ` This has now failed ${ex.failed_times} times — time to call.` : ""}
          <div class="row" style="margin-top:8px"><a class="btn ok sm" target="_blank" rel="noopener" href="https://wa.me/?text=${encodeURIComponent(ex.message)}">💬 Send on WhatsApp</a>
          <span class="tiny muted">Opens WhatsApp with the message ready — you choose ${esc(ex.name.split(" ")[0])} from your contacts.</span></div></div>` : ""}`;
      guideHook("feedback", r);
    } catch (e) { toast(esc(e.message), "alert"); }
  };
  if ($("#fb-ok")) { $("#fb-ok").onclick = () => send("fixed"); $("#fb-no").onclick = () => send("failed_again"); }
}
function guessAsset(res) {  // the worker's own site first, then the best match, then the first item
  const me = pack().people.find((p) => p.id === S.person) || {};
  const real = res.memories.filter((m) => m.asset_id && m.asset_id !== "ALL" && pack().assets.find((a) => a.id === m.asset_id));
  const mine = real.find((m) => (pack().assets.find((a) => a.id === m.asset_id) || {}).site === me.site);
  return (mine || real[0] || {}).asset_id || pack().assets[0].id;
}
function memCard(m) {
  const tier = m.trust || { tier: m.kind === "public" ? "public" : "tested" };
  return `<div class="mem ${m.kind === "insight" ? "insight" : ""}" data-ref="${esc(m.ref)}" data-key="${esc(m.key)}">
    <div class="top">${m.ref ? `<span class="ref">${esc(m.ref)}</span>` : ""}${tierBadge(tier)}
      ${m.kind === "tip" ? '<span class="badge b-src">💡 Expert tip</span>' : ""}
      ${m.cross_site ? `<span class="badge b-site">🌐 Learned at ${esc(m.site)}</span>` : m.site ? `<span class="badge b-src">📍 ${esc(m.site)}</span>` : ""}
      ${m.other_asset ? `<span class="badge b-unreviewed">↪ Found on ${esc(m.other_asset)}</span>` : ""}
      ${m.source && !/^public record$/i.test(m.source) ? `<span class="badge b-src" title="Source">📚 ${esc(m.source.slice(0, 48))}</span>` : ""}
      ${m.flagged ? '<span class="badge b-failed">Flagged</span>' : ""}</div>
    <div class="who">${esc(m.problem || (m.fact || m.text || "").slice(0, 80))}</div>
    ${m.kind === "insight" ? `<div class="tiny muted">${m.trust?.tier === "hfact" ? "Saved in Hindsight earlier." : "Hindsight noticed this pattern across many memories by itself."}</div>` : `<div class="small">${esc((m.action || "").slice(0, 260))}</div>`}
    <div class="tiny muted">${esc(m.person || "")}${m.date ? " · " + fmtDate(m.date) : ""}${m.asset_id && m.asset_id !== "ALL" ? " · " + esc(m.asset_id) : ""}${m.origin ? " · from " + esc(m.origin) : ""}</div>
    <details><summary>Show source text</summary><p class="small">${esc(m.text)}</p>${m.url ? `<a class="small" href="${esc(m.url)}" target="_blank" rel="noopener">Open public source ↗</a>` : ""}
      <div class="row" style="margin-top:6px"><button class="btn sm" data-flag="${esc(m.key)}" data-un="${m.flagged ? 1 : 0}">${m.flagged ? "Restore" : "⚑ Flag as wrong"}</button></div></details>
  </div>`;
}
function bindMemButtons(root) {
  $$("[data-flag]", root).forEach((b) => (b.onclick = async () => {
    const un = b.dataset.un === "1";
    try { const r = await api(`/api/i/${S.ind}/flag`, { json: { key: b.dataset.flag, reason: "wrong", by: S.person, unflag: un } }); toast(esc(r.message)); b.textContent = un ? "⚑ Flag as wrong" : "Restore"; b.dataset.un = un ? "0" : "1"; }
    catch (e) { toast(esc(e.message), "alert"); }
  }));
}
async function translateBlock(root, lang, btn) {
  const nodes = $$("[data-tr]", root); if (!nodes.length) return;
  nodes.forEach((n) => { if (!n.dataset.orig) n.dataset.orig = n.textContent; });
  if (lang === "en") { nodes.forEach((n) => (n.textContent = n.dataset.orig)); return; }
  btn.disabled = true;
  try { const r = await api("/api/translate", { json: { texts: nodes.map((n) => n.dataset.orig), language: lang } });
    nodes.forEach((n, i) => (n.textContent = r.texts[i])); if (r.note) toast(esc(r.note)); }
  catch (e) { toast(esc(e.message), "alert"); }
  btn.disabled = false;
}

// ---------- log work ----------
VIEWS.log = async (el) => {
  el.innerHTML = `
  <div class="panel-head"><div><h2>Log work</h2><p class="muted small">Just say what happened. Ustaad tags the right ${esc(L().asset.toLowerCase())} and problem by itself.</p></div></div>
  <div class="card stack">
    <label class="f">Speak or type, any language</label>
    <textarea id="l-text" class="field" placeholder="e.g. ${esc(pack().assets[0].id)} ka problem phir aaya, filter saaf kiya, 20 minute mein theek ho gaya"></textarea>
    <div class="row"><button class="iconbtn" id="l-mic">🎙️</button><button class="btn accent" id="l-go">Save to memory</button>
      <span class="small muted">New memories show as <span class="badge b-unreviewed">Unreviewed</span> until a senior approves.</span></div>
    <div id="l-out"></div>
  </div>
  <div class="grid g2" style="margin-top:16px">
    <div class="card stack"><h3>💡 Add an expert tip</h3>
      <select id="t-asset" class="field">${assetOptions("", true)}</select>
      <textarea id="t-text" class="field" placeholder="A trick, a check, a warning — in your own words"></textarea>
      <input id="t-src" class="field" placeholder="Source, if any (manual, standard, regulation)">
      <div class="row"><button class="iconbtn" id="t-mic">🎙️</button><button class="btn primary" id="t-go">Save tip</button></div><div id="t-out" class="small"></div></div>
    <div class="card stack"><h3>📝 Detailed form</h3>
      <select id="f-asset" class="field">${assetOptions()}</select>
      <input id="f-problem" class="field" placeholder="${esc(L().problem)} (short name)"><input id="f-symptom" class="field" placeholder="What you saw">
      <input id="f-cause" class="field" placeholder="Cause found"><input id="f-action" class="field" placeholder="What you did">
      <div class="row"><select id="f-outcome" class="field" style="max-width:200px"><option value="fixed">Worked</option><option value="failed_again">Didn't work</option><option value="temporary">Temporary</option><option value="open">Still open</option></select>
        <input id="f-min" class="field" type="number" placeholder="Minutes" style="max-width:120px"><button class="btn primary" id="f-go">Save</button></div><div id="f-out" class="small"></div></div>
  </div>`;
  $("#l-mic").onclick = (e) => toggleVoice(e.currentTarget, (t) => ($("#l-text").value = t));
  $("#t-mic").onclick = (e) => toggleVoice(e.currentTarget, (t) => ($("#t-text").value = t));
  $("#l-go").onclick = async () => {
    $("#l-out").innerHTML = spin;
    try { const r = await api(`/api/i/${S.ind}/smart-log`, { json: { text: $("#l-text").value, person_id: S.person } }); const x = r.extracted || {};
      $("#l-out").innerHTML = `<div class="card" style="background:#fbf8f3"><b>✔ ${esc(r.message)}</b>
        <table class="t" style="margin-top:8px"><tr><td class="muted">${esc(L().asset)}</td><td><b>${esc(x.asset_id)}</b></td></tr><tr><td class="muted">${esc(L().problem)}</td><td>${esc(x.problem)}</td></tr>
        <tr><td class="muted">Cause</td><td>${esc(x.cause || "—")}</td></tr><tr><td class="muted">Action</td><td>${esc(x.action || "—")}</td></tr><tr><td class="muted">Result</td><td>${esc(OUTCOME[x.outcome] || x.outcome)}</td></tr>
        ${x.code ? `<tr><td class="muted">${esc(L().code)}</td><td class="mono">${esc(x.code)}</td></tr>` : ""}</table><p class="tiny muted">Saved to: ${esc(r.saved_to)}</p></div>`;
      guideHook("logged", r);
    } catch (e) { $("#l-out").innerHTML = `<span class="small" style="color:var(--bad)">${esc(e.message)}</span>`; }
  };
  $("#t-go").onclick = async () => {
    try { const r = await api(`/api/i/${S.ind}/tips`, { json: { person_id: S.person, asset_id: $("#t-asset").value, text: $("#t-text").value, source_ref: $("#t-src").value } }); $("#t-out").textContent = "✔ " + r.message; }
    catch (e) { $("#t-out").textContent = e.message; }
  };
  $("#f-go").onclick = async () => {
    try { const r = await api(`/api/i/${S.ind}/log`, { json: { asset_id: $("#f-asset").value, person_id: S.person, problem: $("#f-problem").value, symptom: $("#f-symptom").value, cause: $("#f-cause").value, action: $("#f-action").value, outcome: $("#f-outcome").value, downtime_minutes: +$("#f-min").value || 0 } });
      $("#f-out").textContent = "✔ " + r.message; } catch (e) { $("#f-out").textContent = e.message; }
  };
};

// ---------- memory browser ----------
VIEWS.memory = async (el) => {
  el.innerHTML = `<div class="panel-head"><div><h2>Memory</h2><p class="muted small">Everything Ustaad knows here, with how much to trust it.</p></div></div>
  <div class="card row"><input id="m-q" class="field" placeholder="Search…" style="flex:1;min-width:160px">
    <select id="m-kind" class="field" style="max-width:170px"><option value="">All kinds</option><option value="record">Team records</option><option value="tip">Expert tips</option><option value="manual">Maker's manual</option><option value="public">Public records</option></select>
    <select id="m-tier" class="field" style="max-width:170px"><option value="">All trust levels</option>${Object.keys(TIER).slice(0, 5).map((k) => `<option value="${k}">${TIER[k][1]}</option>`).join("")}</select>
    <select id="m-asset" class="field" style="max-width:220px"><option value="">All ${esc(L().assets.toLowerCase())}</option>${pack().assets.map((a) => `<option value="${a.id}">${esc(a.id)}</option>`).join("")}</select></div>
  <div id="m-sum" class="small muted" style="margin:10px 2px"></div><div id="m-list">${spin}</div>`;
  const d = await api(`/api/i/${S.ind}/memories`);
  const counts = {}; d.memories.forEach((m) => (counts[m.trust.tier] = (counts[m.trust.tier] || 0) + 1));
  const draw = () => {
    const q = $("#m-q").value.toLowerCase(), k = $("#m-kind").value, t = $("#m-tier").value, a = $("#m-asset").value;
    const list = d.memories.filter((m) => (!k || m.kind === k) && (!t || m.trust.tier === t) && (!a || m.asset_id === a) && (!q || m.text.toLowerCase().includes(q)));
    $("#m-sum").innerHTML = `${list.length} of ${d.total} memories · ` + Object.entries(counts).map(([k2, v]) => `${tierBadge(k2)} ${v}`).join(" ");
    $("#m-list").innerHTML = list.slice(0, 120).map(memCard).join("") || '<div class="empty">Nothing matches.</div>';
    bindMemButtons($("#m-list"));
  };
  $$("#m-q, #m-kind, #m-tier, #m-asset").forEach((x) => (x.oninput = draw)); draw();
};

// ---------- approvals ----------
VIEWS.approvals = async (el) => {
  const d = await api(`/api/i/${S.ind}/pending`); const r = roleObj();
  el.innerHTML = `<div class="panel-head"><div><h2>Approvals</h2><p class="muted small">New knowledge waits here until a senior checks it. Approved memories count as trusted.</p></div><span class="badge b-unreviewed">${d.pending.length} waiting</span></div>
  ${r.can_approve ? "" : '<div class="card small">Only a senior role can approve.</div>'}
  <div class="stack">${d.pending.map((x) => `<div class="card" data-k="${x.id}"><div class="row"><span class="badge b-unreviewed">Unreviewed</span><span class="badge b-src">${x.kind === "tip" ? "💡 Tip" : "📝 Record"}</span>
    <b>${esc(x.asset_id)}</b><span class="small muted">${esc(personName(x.person_id))} · ${fmtDate(x.datetime || x.date)}</span></div>
    <p style="margin:8px 0">${x.kind === "tip" ? esc(x.text) : `<b>${esc(x.problem)}</b> — ${esc(x.symptom)}<br><span class="small">Did: ${esc(x.action)} · Result: ${esc(OUTCOME[x.outcome] || x.outcome)}</span>`}</p>
    ${r.can_approve ? `<div class="row"><button class="btn ok sm" data-ok="1">Approve</button><button class="btn bad sm" data-ok="0">Reject</button></div>` : ""}</div>`).join("") || '<div class="card empty">Nothing waiting. 🎉</div>'}</div>`;
  $$("[data-ok]", el).forEach((b) => (b.onclick = async () => {
    const card = b.closest("[data-k]");
    try { const res = await api(`/api/i/${S.ind}/approve`, { json: { key: card.dataset.k, role: S.role, approver_id: S.person, ok: b.dataset.ok === "1" } });
      card.innerHTML = `<b>${esc(res.message)}</b>`; guideHook("approved"); } catch (e) { toast(esc(e.message), "alert"); }
  }));
};

// ---------- playbook / SOP ----------
VIEWS.playbook = async (el) => {
  el.innerHTML = `<div class="panel-head no-print"><div><h2>SOP / playbook</h2><p class="muted small">One standard card built from what actually worked — print it or save as PDF.</p></div></div>
  <div class="card row no-print"><select id="p-asset" class="field" style="max-width:320px">${assetOptions()}</select><select id="p-prob" class="field" style="max-width:320px"></select><button class="btn accent" id="p-go">Build SOP</button></div>
  <div id="p-out" style="margin-top:16px"></div>`;
  const loadProbs = async () => { const d = await api(`/api/i/${S.ind}/problems?asset_id=${$("#p-asset").value}`);
    $("#p-prob").innerHTML = d.problems.map((x) => `<option>${esc(x.problem)}</option>`).join("") || "<option value=''>No history yet</option>"; };
  $("#p-asset").onchange = loadProbs; await loadProbs();
  $("#p-go").onclick = async () => {
    $("#p-out").innerHTML = `<div class="card">${spin} Writing the SOP…</div>`;
    try { const c = await api(`/api/i/${S.ind}/playbook`, { json: { asset_id: $("#p-asset").value, problem: $("#p-prob").value, language: S.lang } });
      const li = (a) => (a || []).map((x) => `<li>${esc(x)}</li>`).join("");
      $("#p-out").innerHTML = `<div class="card"><div class="row" style="justify-content:space-between"><div><div class="tiny muted">${esc(c.org)} · SOP · ${esc(c.generated)}</div><h2>${esc(c.title)}</h2></div>
        <button class="btn no-print" onclick="window.print()">🖨 Print / Save PDF</button></div>
        <p><b>When to use:</b> ${esc(c.when_to_use)}</p>
        <div class="grid g2"><div><h3>Symptoms</h3><ul>${li(c.symptoms)}</ul><h3>First checks</h3><ul>${li(c.first_checks)}</ul></div>
        <div><h3>Steps</h3><ol>${li(c.steps)}</ol>${c.parts?.length ? `<h3>Parts</h3><ul>${li(c.parts)}</ul>` : ""}</div></div>
        ${c.do_not?.length ? `<h3>Do NOT</h3><ul class="avoid">${li(c.do_not)}</ul>` : ""}
        <p>🦺 ${esc(c.safety)} · ⏱ ${esc(c.typical_time)}</p>
        <h3>Proof — verified by</h3><ul class="small">${li(c.verified_by)}</ul>
        ${c.expert_tips_used?.length ? `<h3>Expert tips used</h3><ul class="small">${li(c.expert_tips_used)}</ul>` : ""}
        ${c.hindsight_insight ? `<div class="tipbox"><b>Hindsight reflect:</b> ${esc(c.hindsight_insight)}</div>` : ""}
        <p class="tiny muted">Based on ${c.based_on_records} records in Ustaad memory.</p></div>`;
      guideHook("sop");
    } catch (e) { $("#p-out").innerHTML = `<div class="card">${esc(e.message)}</div>`; }
  };
};

// ---------- risk radar ----------
VIEWS.risk = async (el) => {
  const d = await api(`/api/i/${S.ind}/risk`);
  el.innerHTML = `<div class="panel-head"><div><h2>Knowledge risk radar</h2><p class="muted small">What leaves the building when someone leaves.</p></div></div>
  <div class="grid g2">${d.retiring_experts.map((x) => `<div class="card" style="border-left:5px solid var(--bad)">
    <div class="row" style="justify-content:space-between"><h3 style="margin:0">${esc(x.name)}</h3><span class="badge b-high">Leaving ${fmtDate(x.retiring_on)}</span></div>
    <p><b style="font-size:26px;font-family:var(--serif)">${x.share_of_all_known_fixes}%</b> of all known fixes here were first solved by ${esc(x.name.split(" ")[0])}.<br>
    <span class="small">${x.fixes_owned} fixes · only ${x.captured} written down as tips.</span></p>
    ${x.only_in_their_head.length ? `<div class="small"><b>Only in their head:</b><ul>${x.only_in_their_head.map((y) => `<li>${esc(y)}</li>`).join("")}</ul></div>` : ""}
    <button class="btn accent sm" data-iv="${x.person_id}">🎤 Start exit interview</button></div>`).join("") || '<div class="card">No one is leaving soon.</div>'}</div>
  <div class="card scroll" style="margin-top:16px"><table class="t"><tr><th>${esc(L().asset)}</th><th>Risk</th><th>Known fixes</th><th>Top expert</th><th>Leaving share</th><th>Not written down</th></tr>
  ${d.assets.map((a) => `<tr><td><b>${esc(a.asset_id)}</b><div class="tiny muted">${esc(a.asset)}</div></td><td><span class="badge b-${a.level}">${a.level}</span></td><td>${a.families}</td>
    <td>${esc(a.top_owner)} (${a.top_owner_share}%)</td><td>${a.retiring_share}%</td><td class="small">${a.uncaptured.map((u) => esc(u.problem)).join(", ") || "—"}</td></tr>`).join("")}</table></div>`;
  $$("[data-iv]", el).forEach((b) => (b.onclick = () => { S.ivPerson = b.dataset.iv; go(`#/i/${S.ind}/${S.role}/interview`); }));
};

// ---------- interview ----------
VIEWS.interview = async (el) => {
  const leaving = pack().people.find((p) => p.retiring_on); const pid = S.ivPerson || leaving?.id || pack().people[0].id; S.ivPerson = null;
  el.innerHTML = `<div class="panel-head"><div><h2>Before-you-leave interview</h2><p class="muted small">Questions aimed only at knowledge that is not written down yet. Answer by voice — it becomes an expert tip.</p></div></div>
  <div class="card row"><select id="iv-p" class="field" style="max-width:360px">${personOptions(pid)}</select></div><div id="iv-out" style="margin-top:14px">${spin}</div>`;
  const load = async () => {
    const d = await api(`/api/i/${S.ind}/interview?person_id=${$("#iv-p").value}&language=${S.lang}`);
    $("#iv-out").innerHTML = `<p class="small">${esc(d.person.name)}: ${d.fixes_owned} fixes owned, ${d.captured} written down.</p>
    <div class="stack">${d.questions.map((q, i) => `<div class="card" data-i="${i}"><div class="row"><span class="badge ${q.priority === "high" ? "b-high" : "b-medium"}">${esc(q.priority)}</span><span class="badge b-src">${esc(q.asset_id)}</span></div>
      <p style="margin:8px 0"><b>${esc(q.question)}</b></p><p class="small muted">${esc(q.why)}</p>
      <textarea class="field" placeholder="${esc(d.person.short || d.person.name)}'s answer…"></textarea>
      <div class="row" style="margin-top:6px"><button class="iconbtn" data-mic>🎙️</button><button class="btn primary sm" data-save>Save as expert tip</button><span class="small" data-msg></span></div></div>`).join("")}</div>`;
    $$("[data-i]", $("#iv-out")).forEach((card) => {
      const q = d.questions[+card.dataset.i]; const ta = $("textarea", card);
      $("[data-mic]", card).onclick = (e) => toggleVoice(e.currentTarget, (t) => (ta.value = t));
      $("[data-save]", card).onclick = async () => {
        try { const r = await api(`/api/i/${S.ind}/interview/answer`, { json: { person_id: $("#iv-p").value, asset_id: q.asset_id, question: q.question, answer: ta.value } });
          $("[data-msg]", card).textContent = "✔ " + r.message; guideHook("interview"); } catch (e) { $("[data-msg]", card).textContent = e.message; }
      };
    });
  };
  $("#iv-p").onchange = load; await load();
};

// ---------- shift report ----------
VIEWS.shift = async (el) => {
  el.innerHTML = `<div class="panel-head"><div><h2>Shift report</h2><p class="muted small">Built from real data: work records, sensor alerts, repeat failures and pending approvals.</p></div>
    <select id="sh-h" class="field" style="max-width:160px"><option value="24">Last 24 hours</option><option value="72">Last 3 days</option><option value="168">Last 7 days</option></select></div><div id="sh-out">${spin}</div>`;
  const load = async () => {
    const d = await api(`/api/i/${S.ind}/shift-report?hours=${$("#sh-h").value}&language=${S.lang}`);
    $("#sh-out").innerHTML = `<div class="card">${d.note ? `<p class="small muted">${esc(d.note)}</p>` : ""}<div style="white-space:pre-wrap;font-size:15px">${esc(d.summary)}</div></div>
    ${d.parts_out?.length ? `<div class="card" style="margin-top:14px"><h3>📦 Out of stock</h3><div class="row">${d.parts_out.map((x) => `<a class="badge b-failed" href="#/i/${S.ind}/${S.role}/machines/${x.asset_id}">${esc(x.part)} · ${esc(x.asset_id)}</a>`).join("")}</div></div>` : ""}
    ${d.events?.length ? `<div class="card scroll" style="margin-top:14px"><table class="t"><tr><th>Time</th><th>${esc(L().asset)}</th><th>${esc(L().problem)}</th><th>Result</th><th>By</th><th>Min</th></tr>
      ${d.events.map((e) => `<tr><td class="small">${esc(e.time)}</td><td><b>${esc(e.asset_id)}</b></td><td>${esc(e.problem)}</td><td>${e.outcome === "fixed" ? '<span class="badge b-verified">Worked</span>' : `<span class="badge b-failed">${esc(OUTCOME[e.outcome] || e.outcome)}</span>`}${e.status === "pending" ? ' <span class="badge b-unreviewed">Unreviewed</span>' : ""}</td><td>${esc(e.person)}</td><td>${Math.round(e.downtime_minutes || 0)}</td></tr>`).join("")}</table></div>` : ""}`;
  };
  $("#sh-h").onchange = load; await load();
};

// ---------- skills ----------
VIEWS.skills = async (el) => {
  const d = await api(`/api/i/${S.ind}/skills`);
  const max = Math.max(1, ...Object.values(d.grid).flatMap((r) => Object.values(r)));
  el.innerHTML = `<div class="panel-head"><div><h2>Skill map</h2><p class="muted small">Who has proven fixes on what. Darker = more proven fixes.</p></div></div>
  <div class="card scroll"><table class="t heat"><tr><th></th>${d.assets.map((a) => `<th class="mono">${esc(a)}</th>`).join("")}</tr>
  ${d.people.map((p) => `<tr><td><b>${esc(p.name)}</b><div class="tiny muted">${esc(p.role)}</div></td>${d.assets.map((a) => { const v = d.grid[p.id][a];
    return `<td class="c" style="background:rgba(232,131,58,${v ? 0.15 + 0.75 * v / max : 0});color:${v / max > 0.6 ? "#fff" : "inherit"}">${v || ""}</td>`; }).join("")}</tr>`).join("")}</table></div>
  <p class="small muted">Tip: open <b>Skill passport</b> to see each person's proven skills with proof levels.</p>`;
};

// ---------- passport ----------
function passportHTML(d, ind) {
  return `<div class="passport"><div class="row" style="justify-content:space-between"><div><div class="seal">Ustaad · Skill passport</div><h2 style="margin:4px 0 0">${esc(d.person.name)}</h2>
    <div class="muted">${esc(d.person.role)} · ${esc(d.org)} · ${esc(d.industry)}</div></div>
    <div class="row no-print"><button class="btn sm" id="pp-share">🔗 Copy share link</button><button class="btn sm" onclick="window.print()">🖨 Print</button></div></div>
  <div class="grid g4" style="margin:16px 0">
    <div class="kpi"><b>${d.totals.fixes}</b><span class="small muted">proven fixes</span></div><div class="kpi"><b>${d.totals.verified}</b><span class="small muted">verified skills</span></div>
    <div class="kpi"><b>${d.totals.reused_by_others}</b><span class="small muted">times others reused their fix</span></div><div class="kpi"><b>${d.totals.hours_saved}</b><span class="small muted">hours saved for others</span></div></div>
  <table class="t"><tr><th>Skill</th><th>Proof level</th><th>Fixes</th><th>Confirmed by others</th><th>Where</th></tr>
  ${d.skills.map((s) => `<tr><td><b>${esc(s.skill)}</b></td><td>${tierBadge(s.tier)}<div class="tiny muted">${esc(s.label)}</div></td><td>${s.fixes}</td><td>${s.confirmed_by_others}</td><td class="mono">${esc(s.assets.join(", "))}</td></tr>`).join("")}</table>
  <p class="tiny muted" style="margin-top:10px">Verified = proven more than once or reused successfully by a colleague. Attested = proven once. Self-declared = a tip not yet proven by a fix. Built from ${esc(d.org)} records in Ustaad.</p></div>`;
}
VIEWS.passport = async (el) => {
  el.innerHTML = `<div class="panel-head no-print"><div><h2>Skill passport</h2><p class="muted small">Credit for experts — proof of skill a worker can carry anywhere.</p></div>
    <select id="pp-p" class="field" style="max-width:360px">${personOptions(pack().people[0].id)}</select></div><div id="pp-out">${spin}</div>`;
  const load = async () => { const d = await api(`/api/i/${S.ind}/passport/${$("#pp-p").value}`); $("#pp-out").innerHTML = passportHTML(d, S.ind);
    $("#pp-share").onclick = () => { const u = `${location.origin}/p/${S.ind}/${$("#pp-p").value}`; navigator.clipboard?.writeText(u); toast("Link copied: " + esc(u)); }; };
  $("#pp-p").onchange = load; await load();
};
async function renderPassportPage(ind, pid) {
  await loadPack(ind); const d = await api(`/api/i/${ind}/passport/${pid}`);
  app.innerHTML = `<div class="crumbs no-print"><a href="#/">Ustaad</a> › <a href="#/i/${ind}">${esc(pack().name)}</a> › Skill passport</div>${passportHTML(d, ind)}`;
  $("#pp-share").onclick = () => { navigator.clipboard?.writeText(location.href); toast("Link copied"); };
}

// ---------- stats ----------
VIEWS.stats = async (el) => {
  const [d, rep, cs] = await Promise.all([api(`/api/i/${S.ind}/stats`), api(`/api/i/${S.ind}/repeat`), api(`/api/i/${S.ind}/cross-site`)]);
  const b = d.before, a = d.after; const pct = (x, y) => (x ? Math.round(100 * (x - y) / x) : 0);
  const roi = d.roi || {};
  el.innerHTML = `<div class="panel-head"><div><h2>ROI dashboard</h2><p class="muted small">What Ustaad changed since it started (${fmtDate(d.ustaad_started)}).</p></div></div>
  <div class="grid g4 roi-tiles">
    <div class="kpi big"><span class="small muted">Downtime hours saved</span><b>${roi.hours_saved ?? 0} h</b><span class="tiny muted">faster fixes × problems since start</span></div>
    <div class="kpi big"><span class="small muted">Repeat failures avoided</span><b>${roi.repeat_failures_avoided ?? 0}</b><span class="tiny muted">failed fixes not repeated</span></div>
    <div class="kpi big"><span class="small muted">Fixed vs failed</span><b>${roi.fixed_rate ?? 0}% worked</b><span class="tiny muted">${roi.fixed ?? 0} worked · ${roi.failed ?? 0} didn't</span></div>
    <div class="kpi big" style="background:var(--ink);color:#fff"><span class="small" style="opacity:.8">₹ saved</span><b style="color:var(--accent)">${rupees(d.money_saved)}</b><span class="tiny" style="opacity:.75">lower cost per problem × problems since start</span></div></div>
  <h3 style="margin-top:18px">Before vs after</h3>
  <div class="grid g4">
    <div class="kpi"><span class="small muted">Avg time to fix</span><b>${b.mttr_minutes} → ${a.mttr_minutes} min</b><span class="delta">↓ ${pct(b.mttr_minutes, a.mttr_minutes)}%</span></div>
    <div class="kpi"><span class="small muted">Fixes that failed</span><b>${b.failed_fix_rate}% → ${a.failed_fix_rate}%</b><span class="delta">↓ ${b.failed_fix_rate - a.failed_fix_rate} pts</span></div>
    <div class="kpi"><span class="small muted">Avg cost per problem</span><b>${rupees(b.avg_cost)} → ${rupees(a.avg_cost)}</b><span class="delta">↓ ${pct(b.avg_cost, a.avg_cost)}%</span></div>
    <div class="kpi"><span class="small muted">Problems handled since start</span><b>${a.incidents}</b><span class="tiny muted">${d.records} records · ${d.tips} expert tips in memory</span></div></div>
  <div class="card" style="margin-top:14px"><h3>Month by month</h3><div id="st-c"></div></div>
  <div class="grid g2" style="margin-top:14px">
    <div class="card"><h3>🔁 Repeat problems</h3>${rep.repeat.map((r) => `<div style="padding:6px 0;border-bottom:1px solid #f1ece3"><b>${esc(r.asset_id)}</b> · ${esc(r.problem)} <span class="badge b-src">${r.times}×</span>
      <div class="small muted">Every ~${r.avg_gap_days} days${r.next_expected ? ` · next due <b>${fmtDate(r.next_expected)}</b>` : ""} · ${r.total_downtime_hours} h lost · ${rupees(r.total_cost)}</div></div>`).join("") || '<p class="small muted">No repeat pattern yet.</p>'}</div>
    <div class="card"><h3>🌐 Cross-site learning</h3>${cs.links.map((l) => `<div style="padding:6px 0;border-bottom:1px solid #f1ece3"><b>${esc(l.asset_id)}</b> <span class="small muted">(${esc(l.site)}, model ${esc(l.model)})</span>
      <div class="small">learns from: ${l.learns_from.map((x) => `${esc(x.problem)} — ${esc(x.person)}, ${esc(x.site)}`).join("; ")}</div></div>`).join("") || '<p class="small muted">Only one site.</p>'}</div></div>`;
  MC.combo($("#st-c"), { labels: d.monthly.map((m) => m.month), bars: d.monthly.map((m) => m.incidents), line: d.monthly.map((m) => m.mttr_minutes), barLabel: "Problems", lineLabel: "Avg minutes to fix" });
};

// ---------- knowledge coverage map ----------
VIEWS.coverage = async (el) => {
  const d = await api(`/api/i/${S.ind}/coverage`); const sm = d.summary; const sites = Object.fromEntries((pack().sites || []).map((x) => [x.id, x.name]));
  const col = { good: "var(--ok)", ok: "var(--warn)", low: "var(--bad)" };
  el.innerHTML = `<div class="panel-head"><div><h2>Knowledge coverage</h2><p class="muted small">Score out of 100: proven fixes for its problems, written-down tips, how many people can fix it, and its manual. Weakest first.</p></div></div>
  <div class="grid g4">
    <div class="kpi big"><span class="small muted">Average coverage</span><b>${sm.average}/100</b></div>
    <div class="kpi big"><span class="small muted">Only one person knows it</span><b style="color:var(--bad)">${sm.single_expert}</b><span class="tiny muted">of ${sm.machines} ${esc(L().assets.toLowerCase())}</span></div>
    <div class="kpi big"><span class="small muted">No maker's manual</span><b>${sm.no_manual}</b></div>
    <div class="kpi"><span class="small muted">What to do</span><span class="small">Run the exit interview for every 🚩 expert; add manuals in My ${esc(L().assets.toLowerCase())}.</span></div></div>
  <div class="grid g3" style="margin-top:14px">${d.machines.map((m) => `
    <a class="card mcard" href="#/i/${S.ind}/${S.role}/machines/${encodeURIComponent(m.asset_id)}" style="border-top:4px solid ${col[m.level]}">
      <div class="row" style="justify-content:space-between"><b class="mono">${esc(m.asset_id)}</b><b style="font-size:22px;color:${col[m.level]}">${m.score}<span class="tiny muted">/100</span></b></div>
      <div class="small">${esc(nm({ id: m.asset_id, name: m.asset }))}</div><div class="tiny muted">${esc(sites[m.site] || "")}</div>
      <div class="bar" style="height:6px;background:#eee;border-radius:4px;margin:8px 0"><div style="height:6px;border-radius:4px;width:${m.score}%;background:${col[m.level]}"></div></div>
      <div class="tiny">${m.proven}/${m.problem_types} problem types with a proven fix · ${m.written_down} written down · ${m.experts.length} expert(s)${m.manual_facts ? " · 📘 manual" : ""}</div>
      ${m.flags.length ? `<div style="margin-top:6px">${m.flags.map((f) => `<div class="tiny" style="color:var(--bad)">🚩 ${esc(f)}</div>`).join("")}</div>` : '<div class="tiny" style="color:var(--ok);margin-top:6px">✔ Well covered</div>'}
    </a>`).join("")}</div>`;
};

// ---------- expert leaderboard ----------
VIEWS.leaderboard = async (el) => {
  const d = await api(`/api/i/${S.ind}/leaderboard`); const medal = ["🥇", "🥈", "🥉"];
  el.innerHTML = `<div class="panel-head"><div><h2>Expert leaderboard</h2><p class="muted small">${esc(d.how)}</p></div></div>
  <div class="grid g3">${d.people.slice(0, 3).map((p, i) => `<div class="card" style="text-align:center"><div style="font-size:34px">${medal[i]}</div><h3 style="margin:4px 0">${esc(p.name)}</h3>
    <div class="tiny muted">${esc(p.role)}</div><div style="font-size:24px;font-weight:800;margin:6px 0">${p.points} pts</div>
    <div class="row" style="justify-content:center;gap:4px">${p.badges.map((b) => `<span class="badge b-verified">${esc(b)}</span>`).join("")}</div></div>`).join("")}</div>
  <div class="card" style="margin-top:14px;overflow-x:auto"><table class="t"><tr><th>#</th><th>Person</th><th>Fixes that worked</th><th>Success rate</th><th>Reused by others</th><th>Hours saved for others</th><th>Tips</th><th>Points</th></tr>
  ${d.people.map((p) => `<tr><td><b>${p.rank <= 3 ? medal[p.rank - 1] : p.rank}</b></td>
    <td><a href="#/passport/${S.ind}/${p.person_id}"><b>${esc(p.name)}</b></a> <span class="tiny muted">${esc(p.role)}</span>${p.leaving ? ` <span class="badge b-high">Leaving ${fmtDate(p.leaving)}</span>` : ""}
      <div>${p.badges.map((b) => `<span class="badge b-src">${esc(b)}</span>`).join(" ")}</div></td>
    <td>${p.worked}</td><td>${p.success_rate == null ? "—" : p.success_rate + "%"}</td><td>${p.reused_by_others}</td><td>${p.hours_saved_for_others} h</td><td>${p.tips}</td><td><b>${p.points}</b></td></tr>`).join("")}</table></div>`;
};

// ---------- quiz ----------
VIEWS.quiz = async (el) => {
  const d = await api(`/api/i/${S.ind}/quiz`); let i = 0, score = 0;
  el.innerHTML = `<div class="panel-head"><div><h2>Onboarding quiz</h2><p class="muted small">New joiners learn from this team's own past problems — not generic manuals.</p></div><span id="qz-s" class="badge b-src"></span></div><div class="card" id="qz"></div>`;
  const draw = () => {
    $("#qz-s").textContent = `Score ${score}/${d.questions.length}`;
    if (i >= d.questions.length) { $("#qz").innerHTML = `<h3>Done! ${score}/${d.questions.length}</h3><p class="muted">Every question came from a real record in memory.</p><button class="btn" id="qz-r">Try again</button>`; $("#qz-r").onclick = () => VIEWS.quiz(el); return; }
    const q = d.questions[i];
    $("#qz").innerHTML = `<div class="tiny muted">Question ${i + 1} of ${d.questions.length}</div><h3>${esc(q.question)}</h3>${q.options.map((o, k) => `<button class="btn quiz-opt" data-k="${k}">${esc(o)}</button>`).join("")}<div id="qz-x"></div>`;
    $$(".quiz-opt").forEach((b) => (b.onclick = () => { const k = +b.dataset.k; if (k === q.answer) score++;
      $$(".quiz-opt").forEach((x) => { x.disabled = true; if (+x.dataset.k === q.answer) x.classList.add("right"); else if (x === b) x.classList.add("wrong"); });
      $("#qz-x").innerHTML = `<p class="small">${k === q.answer ? "✔ Right." : "✖ Not quite."} ${esc(q.explain)}</p><button class="btn primary" id="qz-n">Next →</button>`; $("#qz-n").onclick = () => { i++; draw(); }; }));
  };
  draw();
};

// ---------- panels (industry data) ----------
function renderPanels(el, ids) {
  const panels = (pack().panels || []).filter((p) => !ids || ids.includes(p.id));
  el.innerHTML = panels.map((p, k) => `<div class="card" style="margin-top:14px"><h3>${esc(p.title)}</h3><div id="pn-${k}"></div><p class="tiny muted">Source: ${esc(p.source || "")}</p></div>`).join("");
  panels.forEach((p, k) => {
    const box = $(`#pn-${k}`);
    if (p.type === "bar") MC.hbar(box, { labels: p.data.labels, values: p.data.values });
    else if (p.type === "stacked" && p.data) MC.stacked(box, { labels: p.data.months, series: p.data.series, colors: PALETTE });
    else if (p.type === "list") box.innerHTML = p.data.map((x) => `<div style="padding:6px 0;border-bottom:1px solid #f1ece3"><span class="badge ${x.critical ? "b-high" : "b-src"}">${x.critical ? "Critical" : "General"}</span> <b>${x.count}</b> · <span class="small">${esc(x.text)}</span></div>`).join("");
    else if (p.type === "logs") box.innerHTML = `<div class="scroll"><table class="t">${p.data.map((s) => `<tr><td><b>${esc(s.system)}</b></td><td>${s.top.map((t) => `<div class="mono" style="font-size:12px">${t.count}× ${esc(t.pattern)}</div>`).join("")}</td></tr>`).join("")}</table></div>`;
  });
}
async function publicSearch(el, placeholder, filterFn) {
  el.innerHTML = `<div class="card" style="margin-top:14px"><div class="row"><input class="field" id="ps-q" placeholder="${esc(placeholder)}" style="flex:1"></div><div id="ps-l" style="margin-top:10px">${spin}</div></div>`;
  const d = await api(`/api/i/${S.ind}/memories?kind=public`); let items = d.memories.filter(filterFn || (() => true));
  const draw = () => { const q = $("#ps-q").value.toLowerCase(); const l = items.filter((m) => !q || m.text.toLowerCase().includes(q));
    $("#ps-l").innerHTML = `<p class="small muted">${l.length} public records</p>` + l.slice(0, 40).map(memCard).join(""); bindMemButtons($("#ps-l")); };
  $("#ps-q").oninput = draw; draw();
}
VIEWS.dishes = async (el) => {
  const lk = pack().lookup;
  el.innerHTML = `<div class="panel-head"><div><h2>Customer & hygiene data</h2><p class="muted small">Real data behind the kitchen memories.</p></div></div><div id="pnl"></div>
  <div class="card" style="margin-top:14px"><h3>${esc(lk.title)}</h3><input class="field" id="dl-q" placeholder="Search a dish, e.g. biryani, dosa, rasgulla"><div id="dl-out" style="margin-top:8px"></div><p class="tiny muted">Source: ${esc(lk.source)}</p></div>`;
  renderPanels($("#pnl"));
  const draw = () => { const q = $("#dl-q").value.toLowerCase(); const l = lk.items.filter((x) => !q || (x.name + " " + x.ingredients).toLowerCase().includes(q)).slice(0, 12);
    $("#dl-out").innerHTML = `<table class="t"><tr><th>Dish</th><th>Ingredients</th><th>Prep</th><th>Cook</th><th>Region</th></tr>${l.map((x) => `<tr><td><b>${esc(x.name)}</b><div class="tiny muted">${esc(x.diet || "")} · ${esc(x.course || "")}</div></td><td class="small">${esc(x.ingredients)}</td><td>${x.prep_time ?? "—"}</td><td>${x.cook_time ?? "—"}</td><td class="small">${esc(x.state || "")}</td></tr>`).join("")}</table>`; };
  $("#dl-q").oninput = draw; draw();
};
VIEWS.devices = async (el) => {
  el.innerHTML = `<div class="panel-head"><div><h2>Device reports</h2><p class="muted small">Real FDA reports for ventilators and infusion pumps — many say what fixed the problem.</p></div></div><div id="pnl"></div><div id="ps"></div>`;
  renderPanels($("#pnl")); await publicSearch($("#ps"), "Search reports, e.g. battery, blower, filter, occlusion", (m) => (m.action || "").length > 3);
};
VIEWS.outages = async (el) => {
  el.innerHTML = `<div class="panel-head"><div><h2>Outage library</h2><p class="muted small">${pack().panels[0].title}. Ustaad uses these as outside evidence next to your team's own incidents.</p></div></div><div id="pnl"></div><div id="ps"></div>`;
  renderPanels($("#pnl")); await publicSearch($("#ps"), "Search outages, e.g. DNS, certificate, database, config");
};
VIEWS.obd = async (el) => {
  const lk = pack().lookup;
  el.innerHTML = `<div class="panel-head"><div><h2>OBD codes</h2><p class="muted small">What the code means (same for all cars) + what our mechanics found.</p></div></div>
  <div class="card"><div class="row"><input class="field mono" id="ob-q" placeholder="Type a code, e.g. P0171" style="max-width:220px"><button class="btn accent" id="ob-go">Look up</button></div><div id="ob-out" style="margin-top:10px"></div><p class="tiny muted">Source: ${esc(lk.source)}</p></div><div id="pnl"></div>`;
  renderPanels($("#pnl"));
  const mems = await api(`/api/i/${S.ind}/memories`);
  $("#ob-go").onclick = () => {
    const c = $("#ob-q").value.trim().toUpperCase(); const hit = lk.items.find((x) => x.code === c);
    const ours = mems.memories.filter((m) => m.kind !== "public" && m.text.toUpperCase().includes(c));
    $("#ob-out").innerHTML = `<h3 class="mono">${esc(c)}</h3><p>${hit ? `<b>${esc(hit.meaning)}</b>` : "Not in the generic list — may be a maker-specific code."}</p>
      ${ours.length ? `<h3>Our team's memory (${ours.length})</h3>${ours.map(memCard).join("")}` : '<p class="small muted">Our team has no memory of this code yet.</p>'}
      <button class="btn sm" id="ob-ask">💬 Ask Ustaad about ${esc(c)}</button>`;
    bindMemButtons($("#ob-out"));
    $("#ob-ask").onclick = () => { S.prefill = { asset_id: pack().assets[0].id, problem: `Check-engine light with code ${c}${hit ? " (" + hit.meaning + ")" : ""}`, auto: true }; go(`#/i/${S.ind}/${S.role}/ask`); };
  };
  $("#ob-q").onkeydown = (e) => { if (e.key === "Enter") $("#ob-go").click(); };
  $("#ob-q").value = "P0171"; $("#ob-go").click();
};
VIEWS.checklist = async (el) => {
  const cl = pack().checklists[0];
  el.innerHTML = `<div class="panel-head"><div><h2>${esc(cl.title)}</h2><p class="muted small">${esc(cl.source)}</p></div><button class="btn sm no-print" onclick="window.print()">🖨 Print</button></div>
  <div class="grid g3 checklist">${cl.phases.map((ph, k) => `<div class="phase"><h3>${esc(ph.name)}</h3><div class="tiny muted" data-prog="${k}"></div>
    ${ph.items.map((it) => `<label class="${it.startsWith("Neuro OT") ? "local" : ""}"><input type="checkbox" data-ph="${k}"><span>${esc(it)}</span></label>`).join("")}</div>`).join("")}</div>
  <p class="small muted">Lines in green are the demo hospital's own additions, learned from its incidents (e.g. navigation registration). Ustaad never gives clinical advice.</p>`;
  const upd = () => cl.phases.forEach((ph, k) => { const n = $$(`input[data-ph="${k}"]:checked`).length; $(`[data-prog="${k}"]`).textContent = `${n}/${ph.items.length} done${n === ph.items.length ? " ✔" : ""}`; });
  $$(".checklist input").forEach((c) => (c.onchange = upd)); upd();
};

// ---------- factory extras ----------
VIEWS.sensors = async (el) => {
  const d = await api("/api/factory/sensors"); const th = d.thresholds; const ids = Object.keys(d.series);
  el.innerHTML = `<div class="panel-head"><div><h2>Live sensors</h2><p class="muted small">Replay of the team's sensor file (every 15 min). Sensors say <i>something is wrong</i>; Ustaad says <i>what fixed it last time</i>.</p></div>
    <div class="row" style="flex-wrap:nowrap"><button class="btn accent" id="sn-play">▶ Play</button><select id="sn-speed" class="field" style="max-width:120px"><option value="120">Fast</option><option value="300" selected>Normal</option><option value="700">Slow</option></select></div></div>
  <div class="grid g3" id="sn-now">${ids.map((a) => `<div class="kpi" data-a="${a}"><span class="small muted">${a}</span><b>— mm/s</b><span class="small">— °C · — kW</span></div>`).join("")}</div>
  <div class="card" style="margin-top:14px"><div class="sensor-legend">${ids.map((a, k) => `<span><i style="background:${PALETTE[k]}"></i>${a} vibration</span>`).join("")}<span><i style="background:#ca8a04"></i>${th.vib_warn} plan a stop</span><span><i style="background:#b91c1c"></i>${th.vib_stop} stop now</span></div>
    <div id="sn-c"></div><p class="tiny muted">${esc(th.why)} · ${esc(d.source)}</p></div>
  <div id="sn-alert"></div>`;
  const labels = d.series[ids[0]].map((p) => `${String(Math.floor(p.t / 60)).padStart(2, "0")}:${String(p.t % 60).padStart(2, "0")}`);
  const draw = (n) => MC.lines($("#sn-c"), { labels: labels.slice(0, Math.max(n, 2)), ymax: 10, ylabel: "vibration mm/s",
    series: ids.map((a, k) => ({ color: PALETTE[k], data: d.series[a].slice(0, n).map((p) => p.vib) })),
    hlines: [{ y: th.vib_warn, color: "#ca8a04" }, { y: th.vib_stop, color: "#b91c1c" }] });
  let i = 0, timer = null, alerted = false; draw(0);
  const step = () => {
    if (i >= labels.length) { clearInterval(timer); timer = null; $("#sn-play").textContent = "↺ Replay"; return; }
    draw(i + 1);
    ids.forEach((a) => { const p = d.series[a][i]; const k = $(`[data-a="${a}"]`); const bad = p.vib >= th.vib_warn || p.temp >= th.temp_warn;
      k.style.borderColor = p.vib >= th.vib_stop ? "var(--bad)" : bad ? "#ca8a04" : "var(--line)";
      k.innerHTML = `<span class="small muted">${a} · ${labels[i]}</span><b>${p.vib.toFixed(2)} mm/s</b><span class="small">${p.temp} °C · ${p.kw} kW</span>`;
      if (bad && !alerted) { alerted = true; showAlert(a, p); } });
    i++;
  };
  const showAlert = (a, p) => {
    toast(`⚠️ ${a}: vibration ${p.vib} mm/s, ${p.temp} °C`, "alert", 6000);
    const asset = pack().assets.find((x) => x.id === a);
    $("#sn-alert").innerHTML = `<div class="card" style="margin-top:14px;border-left:5px solid var(--bad)"><h3>⚠️ ${a} needs attention</h3>
      <p>Vibration <b>${p.vib} mm/s</b> and temperature <b>${p.temp} °C</b> — above this machine's normal. ${asset ? esc(asset.name) : ""}</p>
      <p class="small" id="sn-log">${spin} Writing the log by itself…</p>
      <div class="row"><button class="btn accent" id="sn-ask">💬 Ask Ustaad what fixed this before</button><a class="btn sm" href="#/i/${S.ind}/${S.role}/machines/${a}">🏭 Open ${a}'s page</a></div></div>`;
    api(`/api/i/${S.ind}/sensors/alert`, { json: { asset_id: a, reading: { vib: p.vib, temp: p.temp, time: labels[i] } } })
      .then((r) => { const el2 = $("#sn-log"); if (el2) el2.innerHTML = `📝 <b>${esc(r.message)}</b> When the technician taps <i>Worked</i>, this log is finished automatically.`; })
      .catch((e) => { const el2 = $("#sn-log"); if (el2) el2.textContent = e.message; });
    $("#sn-ask").onclick = () => { S.prefill = { asset_id: a, problem: `${a} spindle vibration rising to ${p.vib} mm/s and temperature ${p.temp} °C`, auto: true }; go(`#/i/${S.ind}/${S.role}/ask`); };
    guideHook("alert");
  };
  $("#sn-play").onclick = () => {
    if (timer) { clearInterval(timer); timer = null; $("#sn-play").textContent = "▶ Play"; return; }
    if (i >= labels.length) { i = 0; alerted = false; draw(0); $("#sn-alert").innerHTML = ""; }
    timer = setInterval(step, +$("#sn-speed").value); $("#sn-play").textContent = "⏸ Pause";
  };
  S.charts.push({ destroy: () => clearInterval(timer) });
};
VIEWS.fleet = async (el) => {
  const d = await api("/api/factory/fleet"); const m = d.model_card;
  el.innerHTML = `<div class="panel-head"><div><h2>Failure prediction</h2><p class="muted small">${esc(m.question)} Trained on the public Microsoft Azure dataset: ${d.totals.machines} machines, ${d.totals.telemetry_rows.toLocaleString("en-IN")} sensor readings.</p></div></div>
  <div class="grid g4"><div class="kpi"><span class="small muted">Test AUC (Sep–Dec)</span><b>${m.test_auc}</b></div><div class="kpi"><span class="small muted">Failures caught in top 5% alerts</span><b>${Math.round(m.recall_top5pct * 100)}%</b></div>
    <div class="kpi"><span class="small muted">Alerts that were real</span><b>${Math.round(m.precision_top5pct * 100)}%</b></div><div class="kpi"><span class="small muted">Normal failure rate</span><b>${(m.base_failure_rate * 100).toFixed(1)}%</b></div></div>
  <div class="tipbox" style="margin-top:12px">⚖️ <b>Honest note:</b> Microsoft generated this dataset for a tutorial, so failure signals are much cleaner than in a real plant — expect lower accuracy on real data. We checked for data leakage (none found). The model says <i>when</i>; Ustaad's memory says <i>what to do</i>.</div>
  <div class="card scroll" style="margin-top:14px"><h3>Riskiest machines on ${fmtDate(d.demo_day)} (a test day)</h3><table class="t"><tr><th>Machine</th><th>Risk (24 h)</th><th>Why</th><th>What really happened</th></tr>
  ${d.fleet.slice(0, 14).map((f) => `<tr><td class="mono"><b>${esc(f.machine)}</b><div class="tiny muted">${esc(f.model)} · ${f.age_years} yrs</div></td><td><span class="badge ${f.risk > 0.5 ? "b-high" : f.risk > 0.1 ? "b-medium" : "b-low"}">${Math.min(99, Math.round(f.risk * 100))}%</span></td>
    <td class="small">${f.drivers.map(esc).join("<br>") || "—"}</td><td class="small">${f.actually_failed_next_24h ? `<span class="badge b-failed">Failed: ${esc(f.failed_component)}</span>` : '<span class="badge b-verified">No failure</span>'}</td></tr>`).join("")}</table></div>
  <div id="pnl"></div>`;
  renderPanels($("#pnl"), ["fleet-failures"]);
};
VIEWS.check = async (el) => {
  const d = await api("/api/factory/ai4i"); const t = d.typical;
  el.innerHTML = `<div class="panel-head"><div><h2>Failure check</h2><p class="muted small">Enter the machining settings. Rules learned from ${d.runs.toLocaleString("en-IN")} public runs (${d.failures} failures).</p></div></div>
  <div class="card grid g3">
    <div><label class="f">Product quality</label><select id="ck-type" class="field"><option value="L">L (low)</option><option value="M">M (medium)</option><option value="H">H (high)</option></select></div>
    <div><label class="f">Air temperature (K)</label><input id="ck-air" class="field" type="number" step="0.1" value="${t.air_K}"></div>
    <div><label class="f">Process temperature (K)</label><input id="ck-proc" class="field" type="number" step="0.1" value="${t.process_K}"></div>
    <div><label class="f">Spindle speed (rpm)</label><input id="ck-rpm" class="field" type="number" value="${t.rpm}"></div>
    <div><label class="f">Torque (Nm)</label><input id="ck-tq" class="field" type="number" step="0.1" value="${t.torque}"></div>
    <div><label class="f">Tool wear (min)</label><input id="ck-w" class="field" type="number" value="${t.tool_wear}"></div></div>
  <div id="ck-out" style="margin-top:14px"></div><p class="tiny muted">Source: ${esc(d.source)}</p>`;
  const run = () => {
    const ty = $("#ck-type").value, air = +$("#ck-air").value, proc = +$("#ck-proc").value, rpm = +$("#ck-rpm").value, tq = +$("#ck-tq").value, w = +$("#ck-w").value;
    const power = tq * rpm * 2 * Math.PI / 60, strain = w * tq, lim = { L: 11000, M: 12000, H: 13000 }[ty];
    const hits = { TWF: w >= 200, HDF: proc - air < 8.6 && rpm < 1380, PWF: power < 3500 || power > 9000, OSF: strain > lim };
    $("#ck-out").innerHTML = `<div class="grid g2">${d.modes.filter((m) => m.id !== "RNF").map((m) => `<div class="card" style="border-left:5px solid ${hits[m.id] ? "var(--bad)" : "var(--ok)"}">
      <div class="row" style="justify-content:space-between"><b>${esc(m.name)}</b>${hits[m.id] ? '<span class="badge b-high">RISK</span>' : '<span class="badge b-low">OK</span>'}</div>
      <p class="small">${esc(m.rule)}</p><p class="tiny muted">${m.count} such failures in the data.${m.id === "PWF" ? ` Now: ${Math.round(power)} W.` : m.id === "OSF" ? ` Now: ${Math.round(strain)} (limit ${lim}).` : m.id === "HDF" ? ` Now: ΔT ${(proc - air).toFixed(1)} K.` : ""}</p></div>`).join("")}</div>`;
  };
  $$("#tool input, #tool select").forEach((x) => (x.oninput = run)); run();
};

// ---------- My machines ----------
const HEALTH = { green: ["🟢", "Healthy"], amber: ["🟠", "Needs attention"], red: ["🔴", "Problem now"] };
VIEWS.machines = async (el, sub) => {
  if (sub) return machineProfile(el, decodeURIComponent(sub));
  const d = await api(`/api/i/${S.ind}/machines`); const canEdit = roleObj().can_approve; const p = pack();
  const bySite = {}; d.machines.forEach((m) => (bySite[m.site] = bySite[m.site] || []).push(m));
  el.innerHTML = `<div class="panel-head"><div><h2>My ${esc(L().assets.toLowerCase())}</h2><p class="muted small">Tap one to see everything about it.</p></div>
    ${canEdit ? `<button class="btn accent" id="mc-add">＋ Add ${esc(L().asset.toLowerCase())}</button>` : '<span class="small muted">Seniors can add new ones.</span>'}</div>
    <div id="mc-form"></div>
    ${p.sites.map((st) => (bySite[st.id] || []).length ? `<h3 style="margin-top:14px">📍 ${esc(st.name)}</h3><div class="grid g3">${bySite[st.id].map((m) => `
      <a class="card mcard" href="#/i/${S.ind}/${S.role}/machines/${encodeURIComponent(m.id)}">
        <div class="row" style="justify-content:space-between"><b class="mono" style="font-size:15px">${esc(m.id)}</b><span title="${esc(m.health.reasons.join(" · "))}">${HEALTH[m.health.level][0]} <span class="small">${HEALTH[m.health.level][1]}</span></span></div>
        <div>${esc(nm(m))}${m.custom ? ' <span class="badge b-tested">New</span>' : ""}</div><div class="tiny muted">${esc([m.maker, m.model].filter(Boolean).join(" · "))}</div>
        <div class="row" style="gap:6px;margin-top:6px"><span class="badge b-src">${m.fixed}/${m.problems} fixed</span>${m.due_soon ? `<span class="badge b-unreviewed">🔧 ${m.due_soon} due</span>` : ""}${m.parts_low ? `<span class="badge b-failed">📦 ${m.parts_low} low</span>` : ""}${m.manual ? `<span class="badge b-manual">📘 manual</span>` : ""}</div></a>`).join("")}</div>` : "").join("")}`;
  if ($("#mc-add")) $("#mc-add").onclick = () => machineForm($("#mc-form"));
};

function machineForm(box, existing) {
  const p = pack(); const e = existing || {};
  const lines = (arr, f) => (arr || []).map(f).join("\n");
  box.innerHTML = `<div class="card stack" style="margin-bottom:16px;border-top:4px solid var(--accent)">
    <h3>${existing ? "Edit " + esc(e.id) : "Add a new " + esc(L().asset.toLowerCase())}</h3>
    ${existing ? "" : `<div><b>1 · Let Ustaad fill the form</b> <span class="small muted">— or skip and type it yourself</span>
      <div class="grid g3" style="margin-top:8px">
        <label class="card src"><b>📄 PDF manual</b><span class="tiny muted">The maker's manual. Ustaad picks the useful pages.</span><input type="file" id="mf-pdf" accept="application/pdf"></label>
        <div class="card src"><b>🌐 Maker's web page</b><span class="tiny muted">Paste the product page link.</span><div class="row" style="flex-wrap:nowrap"><input class="field" id="mf-url" placeholder="https://…"><button class="btn sm" id="mf-url-go">Read</button></div></div>
        <label class="card src"><b>📷 Nameplate photo</b><span class="tiny muted">Snap the metal label on the machine.</span><input type="file" id="mf-photo" accept="image/*" capture="environment"></label>
      </div><div id="mf-status" class="small" style="margin-top:6px"></div></div>
    <b>2 · Check and save</b>`}
    <div class="grid g3">
      <div><label class="f">ID (short)</label><input class="field mono" id="mf-id" value="${esc(e.id || "")}" ${existing ? "disabled" : ""} placeholder="e.g. CNC-4"></div>
      <div><label class="f">Name</label><input class="field" id="mf-name" value="${esc(e.name || "")}"></div>
      <div><label class="f">Site</label><select class="field" id="mf-site">${p.sites.map((st) => `<option value="${st.id}" ${st.id === e.site ? "selected" : ""}>${esc(st.name)}</option>`).join("")}</select></div>
      <div><label class="f">Maker</label><input class="field" id="mf-maker" value="${esc(e.maker || "")}"></div>
      <div><label class="f">Model</label><input class="field" id="mf-model" value="${esc(e.model || "")}"></div>
      <div><label class="f">Type</label><input class="field" id="mf-type" value="${esc(e.type || "")}"></div>
      <div><label class="f">Installed on</label><input class="field" type="date" id="mf-install" value="${esc(e.install_date || "")}"></div>
      <div><label class="f">Warranty until</label><input class="field" type="date" id="mf-warranty" value="${esc(e.warranty_until || "")}"></div>
      <div><label class="f">Service vendor</label><input class="field" id="mf-vendor" value="${esc(e.vendor || "")}" placeholder="Name"></div>
    </div>
    <div class="grid g2">
      <div><label class="f">Specs <span class="muted small">— one per line: label: value</span></label><textarea class="field mono" id="mf-specs" style="min-height:120px">${esc(lines(e.specs, (x) => `${x.label}: ${x.value}`))}</textarea></div>
      <div><label class="f">Parts <span class="muted small">— name | part no | replace every N days | in store</span></label><textarea class="field mono" id="mf-parts" style="min-height:120px">${esc(lines(e.components, (c) => `${c.name} | ${c.part_no || ""} | ${c.every_days || ""} | ${c.stock ?? ""}`))}</textarea></div>
    </div>
    <div id="mf-extra"></div>
    <div class="row"><button class="btn accent" id="mf-save">Save ${existing ? "changes" : ""}</button><button class="btn ghost" id="mf-cancel">Cancel</button><span id="mf-out" class="small"></span></div></div>`;
  let draft = { faults: [], service: [], source_ref: "", summary: e.summary || "" };
  const fill = (d) => {
    draft = d; const set = (id, v) => { if (v && !$(id).value) $(id).value = v; };
    set("#mf-name", d.name); set("#mf-maker", d.maker); set("#mf-model", d.model); set("#mf-type", d.type);
    if (!$("#mf-id").value && d.name) $("#mf-id").value = (L().asset.slice(0, 3) + "-" + Math.floor(Math.random() * 90 + 10)).toUpperCase().replace(/[^A-Z0-9-]/g, "");
    if (d.specs?.length) $("#mf-specs").value = d.specs.map((x) => `${x.label}: ${x.value}`).join("\n");
    if (d.components?.length) $("#mf-parts").value = d.components.map((c) => `${c.name} | ${c.part_no || ""} | ${c.every_days || ""} | `).join("\n");
    if (d.warranty_months && $("#mf-install").value === "") $("#mf-extra").dataset.wm = d.warranty_months;
    $("#mf-extra").innerHTML = `<div class="card" style="background:#f7f5ff"><b>📘 From the manual — saved into memory when you save:</b>
      ${d.summary ? `<p class="small">${esc(d.summary)}</p>` : ""}
      ${d.faults?.length ? `<div class="small"><b>${d.faults.length} known faults:</b> ${d.faults.map((f) => esc(f.title + (f.code ? ` (${f.code})` : ""))).join(" · ")}</div>` : ""}
      ${d.service?.length ? `<div class="small" style="margin-top:4px"><b>${d.service.length} service tasks:</b> ${d.service.map((x) => esc(x.task) + (x.every_days ? ` (every ${x.every_days} d)` : "")).join(" · ")}</div>` : ""}
      ${d.warranty_months ? `<div class="small" style="margin-top:4px"><b>Warranty:</b> ${d.warranty_months} months from install date</div>` : ""}
      ${d.note ? `<p class="tiny muted">${esc(d.note)}</p>` : ""}<p class="tiny muted">Source: ${esc(d.source_ref)}</p></div>`;
    $("#mf-status").innerHTML = "✔ Read it. Check the form, give it an ID, then save.";
  };
  const read = async (opts, what) => {
    $("#mf-status").innerHTML = `${spin} Reading the ${what}… (a big manual takes ~20 seconds)`;
    try { fill(await api(`/api/i/${S.ind}/machines/read`, opts)); } catch (err) { $("#mf-status").innerHTML = `<span style="color:var(--bad)">${esc(err.message)}</span>`; }
  };
  const up = (inp, what) => { const f = inp.files[0]; if (!f) return; const fd = new FormData(); fd.append("file", f); read({ method: "POST", body: fd }, what); };
  if ($("#mf-pdf")) { $("#mf-pdf").onchange = (ev) => up(ev.target, "manual"); $("#mf-photo").onchange = (ev) => up(ev.target, "nameplate");
    $("#mf-url-go").onclick = () => read({ json: { url: $("#mf-url").value } }, "web page"); }
  $("#mf-cancel").onclick = () => { box.innerHTML = ""; };
  $("#mf-save").onclick = async () => {
    const specs = $("#mf-specs").value.split("\n").map((l) => l.split(/:(.+)/)).filter((x) => x[0]?.trim() && x[1]?.trim()).map((x) => ({ label: x[0].trim(), value: x[1].trim() }));
    const components = $("#mf-parts").value.split("\n").map((l) => l.split("|").map((x) => x.trim())).filter((x) => x[0])
      .map((x) => ({ name: x[0], part_no: x[1] || "", every_days: +x[2] || null, stock: x[3] === "" || x[3] === undefined ? null : +x[3] }));
    const m = { id: existing ? e.id : $("#mf-id").value, is_new: !existing, name: $("#mf-name").value, site: $("#mf-site").value, maker: $("#mf-maker").value,
      model: $("#mf-model").value, type: $("#mf-type").value, install_date: $("#mf-install").value, warranty_until: $("#mf-warranty").value,
      warranty_months: draft.warranty_months, vendor: $("#mf-vendor").value, specs, components, faults: draft.faults || [], service: draft.service || [],
      summary: draft.summary, source_ref: draft.source_ref || e.source_ref || "" };
    $("#mf-save").disabled = true;
    try { const r = await api(`/api/i/${S.ind}/machines`, { json: { machine: m, person_id: S.person, role: S.role } });
      delete S.packs[S.ind]; await loadPack(S.ind); toast(esc(r.message)); guideHook("machine"); go(`#/i/${S.ind}/${S.role}/machines/${encodeURIComponent(r.asset.id)}`); }
    catch (err) { $("#mf-out").innerHTML = `<span style="color:var(--bad)">${esc(err.message)}</span>`; $("#mf-save").disabled = false; }
  };
}

async function machineProfile(el, aid) {
  const d = await api(`/api/i/${S.ind}/machines/${encodeURIComponent(aid)}`); const a = d.asset; const canEdit = roleObj().can_approve;
  const qrUrl = `${location.origin}/m/${S.ind}/${encodeURIComponent(a.id)}`;
  const qrImg = `https://api.qrserver.com/v1/create-qr-code/?size=220x220&margin=6&data=${encodeURIComponent(qrUrl)}`;
  const h = HEALTH[d.health.level];
  el.innerHTML = `<div class="crumbs no-print"><a href="#/i/${S.ind}/${S.role}/machines">← All ${esc(L().assets.toLowerCase())}</a></div>
  <div class="card mhead"><div><div class="tiny muted">${esc(d.site)}${a.demo ? ' · <span class="badge b-src">dates & stock are demo data</span>' : ""}</div>
      <h2 style="margin:2px 0"><span class="mono">${esc(a.id)}</span> · ${esc(nm(a))}</h2>
      <div class="small muted">${esc([a.maker, a.model && "model " + a.model, a.type].filter(Boolean).join(" · "))}</div>
      ${a.summary ? `<p class="small" style="margin:6px 0 0">${esc(a.summary)}</p>` : ""}</div>
    <div class="health ${d.health.level}"><b>${h[0]} ${h[1]}</b><div class="tiny">${d.health.reasons.map(esc).join("<br>")}</div></div></div>
  <div class="row no-print" style="margin:12px 0"><button class="btn accent" id="mp-ask">💬 Ask about ${esc(a.id)}</button><button class="btn" id="mp-log">✍️ I fixed something</button>${canEdit ? '<button class="btn" id="mp-edit">✏️ Edit details</button>' : ""}</div>
  <div id="mp-form"></div>
  <div class="tabs no-print">${["Overview", "History", "Experts", "Manual", "QR sticker"].map((t, i) => `<button data-tab="${i}" class="${i === 0 ? "on" : ""}">${t}</button>`).join("")}</div>
  <div id="mp-tab"></div>`;
  const kpi = (b, l) => `<div class="kpi"><b>${b}</b><span class="small muted">${l}</span></div>`;
  const tabs = [
    () => `<div class="grid g4">${kpi(d.stats.problems, "problems logged")}${kpi(d.stats.fixed, "fixed")}${kpi(d.stats.hours_lost + " h", "time lost")}${kpi(d.stats.last_problem ? fmtDate(d.stats.last_problem) : "—", "last problem")}</div>
      ${d.sensor ? `<div class="card" style="margin-top:12px;border-left:5px solid ${d.sensor.state === "confirmed" ? "var(--ok)" : "var(--warn)"}"><b>📡 Sensor</b><p class="small" style="margin:4px 0">${esc(d.sensor.text)}</p><div class="tiny muted">${esc(d.sensor.symptom)}</div></div>` : ""}
      <div class="grid g2" style="margin-top:12px">
        <div class="card"><h3>🔧 Service due</h3>${d.service_due.length ? d.service_due.map((x) => `<div class="li"><span class="badge ${x.status === "overdue" ? "b-failed" : x.status === "soon" ? "b-unreviewed" : "b-verified"}">${x.status === "overdue" ? `${-x.days_left} days overdue` : `in ${x.days_left} days`}</span> <b>${esc(x.what)}</b>
          <div class="tiny muted">Every ${x.every_days} days · ${x.last_done ? `last done ${fmtDate(x.last_done)} (found in repair history)` : x.last_from === "install date" ? "counted from install date" : ""}</div></div>`).join("") : '<p class="small muted">No service intervals yet. Add parts with "replace every N days".</p>'}</div>
        <div class="card"><h3>📦 Spare parts in store</h3>${d.parts.length ? d.parts.map((c) => `<div class="li row" style="justify-content:space-between"><div><b>${esc(c.name)}</b> <span class="tiny muted mono">${esc(c.part_no || "")}</span>
            <div class="tiny muted">${c.status === "out" ? "⛔ none left — order now" : c.status === "low" ? "⚠️ low" : c.status === "ok" ? "ok" : "stock not set"}</div></div>
            <div class="row" style="gap:4px"><button class="btn sm" data-st="${esc(c.name)}" data-d="-1">−</button><b class="mono" style="min-width:22px;text-align:center">${c.stock ?? "?"}</b><button class="btn sm" data-st="${esc(c.name)}" data-d="1">+</button></div></div>`).join("") : '<p class="small muted">No parts listed yet.</p>'}
          <p class="tiny muted">Repair logs that say a part was replaced take one off automatically.</p></div>
        <div class="card"><h3>🧾 Warranty & service</h3>${d.warranty ? `<p><span class="badge ${d.warranty.active ? (d.warranty.days_left <= 45 ? "b-unreviewed" : "b-verified") : "b-failed"}">${d.warranty.active ? `Under warranty — ${d.warranty.days_left} days left` : "Warranty ended"}</span> <span class="small">until ${fmtDate(d.warranty.until)}</span></p>` : '<p class="small muted">No warranty date.</p>'}
          <p class="small">Installed: <b>${a.install_date ? fmtDate(a.install_date) : "—"}</b><br>Service vendor: <b>${esc(a.vendor || "—")}</b></p>
          ${d.twins.length ? `<p class="small">🌐 Same model: ${d.twins.map((t) => `<a href="#/i/${S.ind}/${S.role}/machines/${t}">${esc(t)}</a>`).join(", ")} — their fixes count here too.</p>` : ""}</div>
        <div class="card"><h3>📋 Specs</h3>${(a.specs || []).length ? `<table class="t">${a.specs.map((x) => `<tr><td class="muted small">${esc(x.label)}</td><td class="small">${esc(x.value)}</td></tr>`).join("")}</table>` : '<p class="small muted">No specs yet.' + (canEdit ? " Use ✏️ Edit details." : "") + "</p>"}</div>
      </div>`,
    () => `<div class="card">${d.history.length ? `<table class="t"><tr><th>Date</th><th>Problem</th><th>What was done</th><th>Result</th><th>By</th></tr>${d.history.map((r) => `<tr><td class="small">${fmtDate(r.date)}</td><td><b>${esc(r.problem)}</b>${r.source === "sensor" ? ' <span class="badge b-site">📡 auto-logged</span>' : ""}</td><td class="small">${esc(r.action)}</td>
        <td><span class="badge ${r.outcome === "fixed" ? "b-verified" : r.outcome === "open" ? "b-unreviewed" : "b-failed"}">${esc(r.outcome_label)}</span>${r.sensor?.confirmed ? ' <span class="badge b-verified">📡 confirmed</span>' : ""}${r.status === "pending" ? ' <span class="badge b-unreviewed">Unreviewed</span>' : ""}</td><td class="small">${esc(r.person)}</td></tr>`).join("")}</table>` : '<p class="muted">No problems logged yet — memory starts here.</p>'}</div>`,
    () => `<div class="grid g3">${d.experts.map((x, i) => `<div class="card"><div class="tiny muted">#${i + 1} on this ${esc(L().asset.toLowerCase())}${d.twins.length ? " and its twins" : ""}</div><h3>${esc(x.name)}</h3><div class="small muted">${esc(x.role)}</div>
        <p><b>${x.fixes}</b> proven fix(es)${x.leaving ? ` · <span class="badge b-high">Leaving ${fmtDate(x.leaving)}</span>` : ""}</p>
        <div class="row"><a class="btn sm" href="#/passport/${S.ind}/${x.person_id}">🏅 Skill passport</a><a class="btn sm ok" target="_blank" rel="noopener" href="https://wa.me/?text=${encodeURIComponent(`${x.name.split(" ")[0]} ji, need your help with ${a.id} (${nm(a)}).`)}">💬 WhatsApp</a></div></div>`).join("") || '<div class="card muted">No proven fixes yet.</div>'}</div>
      ${d.experts.some((x) => x.leaving) ? '<p class="small" style="margin-top:10px">⚠️ An expert here is leaving — run the <b>Exit interview</b> before they go.</p>' : ""}`,
    () => `<div class="card">${d.manual.length ? `<p class="small muted">From ${esc(a.source_ref || "the maker's manual")}. These are in Ustaad's memory as "📘 Maker's manual", so answers can compare the manual with what your team found.</p>${d.manual.map((m) => `<div class="li"><span class="badge b-manual">${{ fault: "Known fault", service: "Service", spec: "Specs" }[m.kind] || m.kind}</span> <b>${esc(m.title)}</b><div class="small">${esc(m.text)}</div></div>`).join("")}` : `<p class="muted">No manual added yet.${canEdit ? " Use ＋ Add (or ✏️ Edit details) and upload the maker's PDF manual or web page." : ""}</p>`}</div>`,
    () => `<div class="card sticker"><div class="qr"><img src="${qrImg}" alt="QR code for ${esc(a.id)}" width="200" height="200"></div>
        <div><div class="tiny" style="letter-spacing:.12em;text-transform:uppercase;color:var(--accent);font-weight:700">Ustaad · scan me</div><h2 class="mono" style="margin:4px 0">${esc(a.id)}</h2><div>${esc(nm(a))}</div><div class="small muted">${esc(d.site)}</div>
        <p class="small">Problem with this ${esc(L().asset.toLowerCase())}? Scan with your phone camera — Ustaad opens with it already chosen.</p><div class="tiny muted mono">${esc(qrUrl)}</div></div></div>
      <div class="row no-print" style="margin-top:10px"><button class="btn primary" onclick="window.print()">🖨 Print sticker</button><span class="small muted">Like a barcode at a shop — it tells Ustaad which ${esc(L().asset.toLowerCase())} this is.</span></div>`,
  ];
  const show = (i) => { $$(".tabs button", el).forEach((b) => b.classList.toggle("on", +b.dataset.tab === i)); $("#mp-tab").innerHTML = tabs[i]();
    $$("[data-st]", el).forEach((b) => (b.onclick = async () => { const c = d.parts.find((x) => x.name === b.dataset.st); const v = Math.max(0, (+c.stock || 0) + +b.dataset.d);
      try { await api(`/api/i/${S.ind}/machines/${encodeURIComponent(a.id)}/stock`, { json: { part: c.name, stock: v } }); machineProfile(el, aid); } catch (err) { toast(esc(err.message), "alert"); } })); };
  $$(".tabs button", el).forEach((b) => (b.onclick = () => show(+b.dataset.tab))); show(S.mpTab || 0); S.mpTab = 0;
  $("#mp-ask").onclick = () => { S.prefill = { asset_id: a.id }; go(`#/i/${S.ind}/${S.role}/ask`); };
  $("#mp-log").onclick = () => go(`#/i/${S.ind}/${S.role}/log`);
  if ($("#mp-edit")) $("#mp-edit").onclick = () => machineForm($("#mp-form"), a);
  guideHook("profile");
}
function openFromQR(ind, aid) {  // the QR sticker: open Ask as a worker with this item already chosen
  return loadPack(ind).then((p) => { const r = p.roles.find((x) => !x.can_approve && x.tools.includes("ask")) || p.roles[0];
    S.prefill = { asset_id: aid }; toast(`📷 Scanned ${esc(aid)} — what's the problem?`); location.replace(`#/i/${ind}/${r.id}/ask`); });
}

// ---------- demo guide (6 stories) ----------
const STORIES = [
  { title: "1 · New technician's first breakdown", ind: "factory", steps: [
    { t: "You are Arjun, a junior technician. Open <b>Live sensors</b> and press ▶ Play. Watch CNC-3.", go: "#/i/factory/technician/sensors", until: "alert" },
    { t: "CNC-3 crosses the limit. Press <b>Ask Ustaad what fixed this before</b>.", until: "asked" },
    { t: "First switch <b>Memory OFF</b> and ask again — generic chatbot advice. Then switch <b>Memory ON</b>: the proven fix, who did it, how much to trust it, sources — even from Pune's twin machine (🌐)." },
    { t: "Press <b>▶ Start guided mode</b>, tick each step, then tap <b>✔ Worked</b>. Ustaad learns and credits Ramesh." } ] },
  { title: "2 · Ramesh retires", ind: "factory", steps: [
    { t: "You are the supervisor. Open <b>Risk radar</b>: see what is only in Ramesh's head.", go: "#/i/factory/supervisor/risk" },
    { t: "Press <b>Start exit interview</b>. Answer one question (🎙️ voice works in Hindi) and save it." },
    { t: "Open <b>Approvals</b> and approve the new tip — it becomes trusted knowledge.", go: "#/i/factory/supervisor/approvals" },
    { t: "Open <b>Skill passport</b> for Ramesh: verified skills and how often others reused his fixes.", go: "#/i/factory/supervisor/passport" } ] },
  { title: "3 · Manager's Monday", ind: "factory", steps: [
    { t: "You are the plant head. Open <b>Impact & ₹</b>: time to fix, failed fixes and money, before vs after.", go: "#/i/factory/manager/stats" },
    { t: "In <b>Ask Ustaad</b>, ask: <i>Which machine lost the most downtime hours?</i> — you get a chart.", go: "#/i/factory/manager/ask", prefill: { asset_id: "CNC-1", problem: "Which machine lost the most downtime hours?", auto: true } },
    { t: "Open <b>Shift report</b> — built from records, sensor alerts and pending approvals.", go: "#/i/factory/manager/shift" },
    { t: "Open <b>Failure prediction</b> — trained on Microsoft's 100-machine dataset, with an honest note.", go: "#/i/factory/manager/fleet" },
    { t: "Open <b>SOP / playbook</b>, build one and press 🖨 Print / Save PDF.", go: "#/i/factory/manager/playbook" } ] },
  { title: "4 · Pune helps Bengaluru", ind: "factory", steps: [
    { t: "Ask about CNC-1's spindle orientation fault. Look for the 🌐 badge: Kavya fixed it at the Pune plant on the same model.", go: "#/i/factory/technician/ask", prefill: { asset_id: "CNC-1", problem: "CNC-1 spindle does not stop at orientation position on tool change", auto: true } },
    { t: "Press <b>ಕನ್ನಡ</b> to translate the answer to Kannada (needs the Groq key)." } ] },
  { title: "5 · Same engine, other industries", ind: "restaurant", steps: [
    { t: "Restaurant: ask why biryani rice turns mushy — Chef Joseph's fix, a failed attempt to avoid, Zomato evidence.", go: "#/i/restaurant/cook/ask", prefill: { asset_id: "BRY-2", problem: "Biryani rice is coming out mushy after we opened a new rice bag", auto: true } },
    { t: "Hospital: note the <b>no diagnosis</b> banner. Open the WHO <b>OT checklist</b>.", go: "#/i/healthcare/ot/checklist" },
    { t: "Hospital: ask about a ventilator alarm — Bengaluru's fix reaches Mysuru, plus real FDA reports.", go: "#/i/healthcare/nurse/ask", prefill: { asset_id: "VNT-M1", problem: "High blower temperature alarm on the ventilator at night", auto: true } },
    { t: "Garage: look up <b>P0171</b> — code meaning + Venki-anna's spray test.", go: "#/i/garage/mechanic/obd" },
    { t: "IT on-call: open the <b>Outage library</b> — 240 real public outages next to the team's own incidents.", go: "#/i/it/oncall/outages" },
    { t: "Try a 📷 photo question in <b>Ask Ustaad</b> (needs the Groq key).", go: "#/i/it/oncall/ask" } ] },
  { title: "6 · A new machine arrives", ind: "factory", steps: [
    { t: "You are the supervisor. Open <b>My machines</b> and press <b>＋ Add machine</b>.", go: "#/i/factory/supervisor/machines" },
    { t: "Upload the maker's <b>PDF manual</b> (or paste its web page, or snap the nameplate). Ustaad fills the form: specs, parts, known faults, service tasks. Give it an ID like <b>CNC-4</b> and press <b>Save</b>.", until: "machine" },
    { t: "This is the machine's page: health light, service due, spare parts, history, experts, manual — and a <b>QR sticker</b> to print and stick on it.", until: "profile" },
    { t: "Press <b>💬 Ask about CNC-4</b> and ask about an alarm from its manual — the answer comes from the 📘 maker's manual." },
    { t: "Tap <b>✖ Didn't work</b> or <b>✔ Worked</b> with what you really did. Ask again: now it says <b>Manual says … / team found …</b>. That's the whole idea." } ] },
];
const G = { open: false, s: 0, k: 0 };
function drawGuide() {
  const g = $("#guide"); if (!G.open) { g.classList.add("hidden"); return; } g.classList.remove("hidden");
  const st = STORIES[G.s], step = st.steps[G.k];
  g.innerHTML = `<div class="row" style="justify-content:space-between"><h3 style="margin:0">Demo guide</h3><button class="btn ghost sm" id="g-x">✕</button></div>
  <p class="tiny muted">6 short stories cover every feature. Follow the dark box.</p>
  ${STORIES.map((s, i) => `<div class="story ${i === G.s ? "on" : ""}" data-s="${i}"><b>${esc(s.title)}</b><div class="tiny muted">${s.steps.length} steps</div></div>`).join("")}
  <div class="stepnow"><div class="tiny" style="opacity:.7">Step ${G.k + 1} of ${st.steps.length}</div><p style="margin:6px 0 10px">${step.t}</p>
    <div class="row">${step.go ? '<button class="btn accent sm" id="g-go">Take me there</button>' : ""}<span style="flex:1"></span>
    <button class="btn sm" id="g-prev" ${G.k === 0 && G.s === 0 ? "disabled" : ""}>←</button><button class="btn sm" id="g-next">Next →</button></div></div>`;
  $("#g-x").onclick = () => { G.open = false; drawGuide(); };
  $$(".story", g).forEach((s) => (s.onclick = () => { G.s = +s.dataset.s; G.k = 0; drawGuide(); doStep(); }));
  if ($("#g-go")) $("#g-go").onclick = doStep;
  $("#g-prev").onclick = () => { if (G.k > 0) G.k--; else if (G.s > 0) { G.s--; G.k = STORIES[G.s].steps.length - 1; } drawGuide(); };
  $("#g-next").onclick = () => { if (G.k < st.steps.length - 1) G.k++; else if (G.s < STORIES.length - 1) { G.s++; G.k = 0; } else { toast("That's the whole tour 🎉"); } drawGuide(); doStep(); };
}
function doStep() { const step = STORIES[G.s].steps[G.k]; if (!step.go) return; if (step.prefill) S.prefill = { ...step.prefill }; go(step.go); }
function guideHook(event) {
  if (!G.open) return; const st = STORIES[G.s]; const step = st.steps[G.k];
  if (step.until === event && G.k < st.steps.length - 1) { G.k++; drawGuide(); }
}
$("#btn-guide").onclick = () => { G.open = !G.open; drawGuide(); };
$("#lang").onchange = (e) => { S.lang = e.target.value; toast("Answers will come in " + e.target.selectedOptions[0].text + (S.status?.llm ? "" : " (needs the Groq key)")); };

// ---------- router ----------
async function route() {
  clearCharts();
  const h = location.hash.replace(/^#\/?/, ""); const parts = h.split("/").filter(Boolean);
  try {
    if (parts[0] === "m" && parts[2]) { await openFromQR(parts[1], decodeURIComponent(parts[2])); return; }
    if (parts[0] === "i" && parts.length >= 4) await renderWorkspace(parts[1], parts[2], parts[3], parts[4]);
    else if (parts[0] === "i" && parts[1]) await renderRoles(parts[1]);
    else if (parts[0] === "passport") await renderPassportPage(parts[1], parts[2]);
    else await renderHome();
  } catch (e) { app.innerHTML = `<div class="card"><b>Couldn't load.</b><p class="muted">${esc(e.message)}</p><a href="#/">Back home</a></div>`; }
  window.scrollTo(0, 0);
}
window.addEventListener("hashchange", route);
loadStatus(); route();
