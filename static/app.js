/* Ustaad frontend — plain JavaScript, no build step. */
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const app = $("#app");
const S = { status: null, industries: null, packs: {}, ind: null, role: null, person: null, lang: "en", prefill: null, charts: [] };

const TOOLS = {
  ask: ["💬", "Ask Ustaad"], log: ["🎙️", "Log work"], memory: ["🧠", "Memory"], approvals: ["✅", "Approvals"],
  playbook: ["📋", "SOP / playbook"], risk: ["⚠️", "Risk radar"], interview: ["🎤", "Exit interview"], shift: ["🔁", "Shift report"],
  skills: ["🧩", "Skill map"], passport: ["🪪", "Skill passport"], stats: ["📈", "Impact & ₹"], quiz: ["🎓", "Onboarding quiz"],
  sensors: ["📡", "Live sensors"], fleet: ["🔮", "Failure prediction"], check: ["🧮", "Failure check"], dishes: ["🍽️", "Customer & hygiene data"],
  checklist: ["✔️", "OT checklist"], devices: ["🩺", "Device reports"], obd: ["🔧", "OBD codes"], outages: ["🌐", "Outage library"],
};
const TIER = { verified: ["b-verified", "✔ Verified"], tested: ["b-tested", "Tested once"], unreviewed: ["b-unreviewed", "Unreviewed"],
  failed: ["b-failed", "✖ Didn't work"], public: ["b-public", "Public record"], attested: ["b-attested", "Attested"], self: ["b-self", "Self-declared"] };

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
function L() { return pack().labels; }
function assetOptions(selected, includeAll = false) {
  const p = pack(); const bySite = {};
  p.assets.forEach((a) => { (bySite[a.site] = bySite[a.site] || []).push(a); });
  let h = includeAll ? `<option value="ALL">All ${esc(L().assets.toLowerCase())}</option>` : "";
  for (const s of p.sites) {
    h += `<optgroup label="${esc(s.name)}">` + (bySite[s.id] || []).map((a) => `<option value="${a.id}" ${a.id === selected ? "selected" : ""}>${esc(a.id)} — ${esc(a.name)}</option>`).join("") + "</optgroup>";
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
        const r = await api("/api/voice", { method: "POST", body: fd }); onText(r.text); toast("🎙️ Got it: " + esc(r.text.slice(0, 120)));
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
    l.className = "chip " + (S.status.llm ? "on" : "off"); l.lastElementChild.textContent = S.status.llm ? "Groq AI on" : "AI off (rule-based)";
    l.title = S.status.llm ? S.status.llm_model : "Add GROQ_API_KEY for AI answers, voice and photos";
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
  <h2>Who are you today?</h2><p class="muted small" style="margin-top:-4px">Each role sees its own tools. Seniors can approve new knowledge.</p>
  <div class="grid g3">${p.roles.map((r) => `
    <button class="role-card" data-role="${r.id}"><h3>${esc(r.name)}</h3>
      <span class="small muted">${r.can_approve ? "✅ Can approve new memories" : "Uses and adds knowledge"}</span>
      <div class="tools">${r.tools.slice(0, 9).map((t) => `<span class="badge b-src">${TOOLS[t][0]} ${TOOLS[t][1]}</span>`).join("")}</div></button>`).join("")}
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
async function renderWorkspace(ind, role, tool) {
  const p = await loadPack(ind);
  if (S.role !== role || !S.person || !p.people.find((x) => x.id === S.person)) { S.role = role; S.person = defaultPerson(role); }
  const r = roleObj(); if (!r.tools.includes(tool)) tool = r.tools[0];
  app.innerHTML = `
  <div class="crumbs"><a href="#/">Industries</a> › <a href="#/i/${ind}">${esc(p.name)}</a> › <span>${esc(r.name)}</span> › <b>${TOOLS[tool][1]}</b></div>
  <div class="ws">
    <nav class="side">
      <div class="who"><div class="tiny muted">${p.icon} ${esc(p.org.name)}</div><label class="tiny muted" style="display:block;margin-top:6px">You are</label>
        <select id="who" class="field" style="padding:5px 8px;font-size:13px">${personOptions(S.person)}</select></div>
      ${r.tools.map((t) => `<a href="#/i/${ind}/${role}/${t}" class="${t === tool ? "on" : ""}"><span>${TOOLS[t][0]}</span><span>${TOOLS[t][1]}</span></a>`).join("")}
    </nav>
    <section id="panel">${p.banner ? `<div class="banner" style="margin-bottom:12px">🛡️ ${esc(p.banner)}</div>` : ""}<div id="tool"></div></section>
  </div>`;
  $("#who").onchange = (e) => { S.person = e.target.value; };
  clearCharts();
  const el = $("#tool");
  try { await (VIEWS[tool] || VIEWS.ask)(el); } catch (e) { el.innerHTML = `<div class="card"><b>Something went wrong.</b><p class="muted">${esc(e.message)}</p></div>`; }
}

// ---------- ask ----------
const VIEWS = {};
VIEWS.ask = async (el) => {
  const p = pack(); const pre = S.prefill || {}; S.prefill = null;
  const aid = pre.asset_id || p.assets[0].id;
  el.innerHTML = `
  <div class="panel-head"><div><h2>Ask Ustaad</h2><p class="muted small">Describe the problem like you'd tell a senior. Speak, type or snap a photo.</p></div>
    <div class="toggle" id="memtog"><button class="on" data-v="1">Memory ON</button><button data-v="0">Memory OFF</button></div></div>
  <div class="card stack">
    <div><label class="f">${esc(L().asset)}</label><select id="a-asset" class="field">${assetOptions(aid)}</select></div>
    <div><label class="f">Problem</label><textarea id="a-q" class="field" placeholder="e.g. ${esc(p.questions[0])}">${esc(pre.problem || "")}</textarea></div>
    <div class="row">
      <button class="iconbtn" id="a-mic" title="Speak">🎙️</button><button class="iconbtn" id="a-cam" title="Photo of the problem">📷</button>
      <span class="spacer" style="flex:1"></span><button class="btn accent" id="a-go">Ask Ustaad →</button></div>
    <div class="row">${p.questions.map((q) => `<button class="sample">${esc(q)}</button>`).join("")}</div>
    <div id="a-photo" class="small muted"></div>
  </div>
  <div id="a-out" style="margin-top:16px"></div>`;
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
  const refs = (arr) => (arr || []).map((r) => `<span class="ref" data-ref="${esc(r)}">${esc(r)}</span>`).join("");
  out.innerHTML = `
  <div class="grid" style="grid-template-columns:minmax(0,1.5fr) minmax(0,1fr)" id="ans-grid">
    <div class="card answer">
      <div class="trust ${t.level}">${t.level === "verified" ? "✔" : t.level === "off" ? "○" : "◐"} ${esc(t.label)}</div>
      <p style="font-size:16px;margin-top:12px" data-tr>${esc(a.summary)}</p>
      ${a.check_first ? `<div class="first">👉 Check first: <span data-tr>${esc(a.check_first)}</span></div>` : ""}
      ${a.likely_causes?.length ? `<h3>Likely causes</h3><ul>${a.likely_causes.map((c) => `<li><b data-tr>${esc(c.cause)}</b> <span class="badge ${c.confidence === "high" ? "b-verified" : c.confidence === "medium" ? "b-tested" : "b-self"}">${esc(c.confidence)}</span>${refs(c.memory_refs)}<div class="small muted" data-tr>${esc(c.why)}</div></li>`).join("")}</ul>` : ""}
      ${a.steps?.length ? `<h3>Steps</h3><ol id="steps">${a.steps.map((s) => `<li data-tr>${esc(s)}</li>`).join("")}</ol>
        <button class="btn sm" id="btn-guided">▶ Start guided mode (tick each step)</button><ul class="guided hidden" id="guided"></ul>` : ""}
      ${a.avoid?.length ? `<h3>Don't repeat</h3><ul class="avoid">${a.avoid.map((x) => `<li><span data-tr>${esc(x.action)}</span>${refs(x.memory_refs)}<div class="small muted" data-tr>${esc(x.why)}</div></li>`).join("")}</ul>` : ""}
      ${a.expert_tip ? `<div class="tipbox" style="margin-top:12px">💡 <b>Expert tip:</b> <span data-tr>${esc(a.expert_tip)}</span></div>` : ""}
      <p class="small muted" style="margin-top:10px">${a.estimated_time ? `⏱ ${esc(a.estimated_time)} · ` : ""}${a.safety ? `🦺 <span data-tr>${esc(a.safety)}</span>` : ""}</p>
      <div class="row no-print" style="margin-top:6px"><span class="small muted">Translate:</span>
        <button class="btn sm" data-tl="hi">हिन्दी</button><button class="btn sm" data-tl="kn">ಕನ್ನಡ</button><button class="btn sm" data-tl="en">English</button>
        <span class="tiny muted" style="margin-left:auto">Written by ${esc(res.written_by)} · memory: ${esc(res.memory_mode)}</span></div>
      ${res.use_memory ? `<div class="card" style="margin-top:14px;background:#fbf8f3" id="fb">
        <b>Did it work?</b> <span class="small muted">Your answer becomes a new memory — this is how Ustaad learns.</span>
        <div class="row" style="margin-top:8px"><select id="fb-who" class="field" style="max-width:260px">${personOptions(S.person)}</select>
          <input id="fb-min" class="field" type="number" placeholder="Minutes it took" style="max-width:150px">
          <input id="fb-note" class="field" placeholder="What you actually did (optional)" style="flex:1;min-width:180px"></div>
        <div class="row" style="margin-top:8px"><button class="btn ok" id="fb-ok">✔ Worked</button><button class="btn bad" id="fb-no">✖ Didn't work</button></div></div>` : ""}
    </div>
    <div><div class="panel-head" style="margin-bottom:8px"><h3 style="margin:0">What I remember</h3><span class="small muted">${res.memories.length} memories</span></div>
      <div id="mems">${res.memories.length ? res.memories.map(memCard).join("") : `<div class="card small muted">${res.use_memory ? "Nothing similar in memory yet." : "Memory is OFF — this is what a generic chatbot knows."}</div>`}</div></div>
  </div>`;
  if (window.innerWidth < 900) $("#ans-grid").style.gridTemplateColumns = "1fr";
  $$(".ref", out).forEach((r) => (r.onclick = () => { const m = $(`#mems [data-ref="${r.dataset.ref}"]`); if (m) { $$("#mems .mem").forEach((x) => x.classList.remove("hl")); m.classList.add("hl"); m.scrollIntoView({ behavior: "smooth", block: "center" }); } }));
  bindMemButtons(out);
  $$("[data-tl]", out).forEach((b) => (b.onclick = () => translateBlock(out, b.dataset.tl, b)));
  const gb = $("#btn-guided");
  if (gb) gb.onclick = () => {
    const g = $("#guided"); g.classList.remove("hidden"); $("#steps").classList.add("hidden"); gb.classList.add("hidden");
    g.innerHTML = a.steps.map((s, i) => `<li><input type="checkbox" data-i="${i + 1}"><span>${esc(s)}</span></li>`).join("");
    $$("input", g).forEach((c) => (c.onchange = () => { c.parentElement.classList.toggle("done", c.checked);
      if ($$("input", g).every((x) => x.checked)) { toast("All steps done — tell Ustaad if it worked 👇"); $("#fb").scrollIntoView({ behavior: "smooth" }); } }));
  };
  const send = async (result) => {
    const steps = $$("#guided input:checked").map((c) => +c.dataset.i);
    try {
      const r = await api(`/api/i/${S.ind}/feedback`, { json: { ask_id: res.ask_id, result, person_id: $("#fb-who").value, downtime_minutes: +$("#fb-min").value || 0, action_done: $("#fb-note").value, steps_done: steps } });
      $("#fb").innerHTML = `<b>${result === "fixed" ? "✔ Saved as WORKED" : "✖ Saved as DID NOT WORK"}</b><p class="small">${esc(r.message)}</p><p class="tiny muted">Saved to: ${esc(r.saved_to)}</p>`;
      guideHook("feedback", r);
    } catch (e) { toast(esc(e.message), "alert"); }
  };
  if ($("#fb-ok")) { $("#fb-ok").onclick = () => send("fixed"); $("#fb-no").onclick = () => send("failed_again"); }
}
function memCard(m) {
  const tier = m.trust || { tier: m.kind === "public" ? "public" : "tested" };
  return `<div class="mem" data-ref="${esc(m.ref)}" data-key="${esc(m.key)}">
    <div class="top">${m.ref ? `<span class="ref">${esc(m.ref)}</span>` : ""}${tierBadge(tier)}
      ${m.kind === "tip" ? '<span class="badge b-src">💡 Expert tip</span>' : ""}
      ${m.cross_site ? `<span class="badge b-site">🌐 Learned at ${esc(m.site)}</span>` : m.site ? `<span class="badge b-src">📍 ${esc(m.site)}</span>` : ""}
      ${m.source ? `<span class="badge b-src" title="Source">📚 ${esc(m.source.slice(0, 48))}</span>` : ""}
      ${m.flagged ? '<span class="badge b-failed">Flagged</span>' : ""}</div>
    <div class="who">${esc(m.problem || "")}</div>
    <div class="small">${esc((m.action || "").slice(0, 260))}</div>
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
        <tr><td class="muted">Cause</td><td>${esc(x.cause || "—")}</td></tr><tr><td class="muted">Action</td><td>${esc(x.action || "—")}</td></tr><tr><td class="muted">Result</td><td>${esc(x.outcome)}</td></tr>
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
    <select id="m-kind" class="field" style="max-width:170px"><option value="">All kinds</option><option value="record">Team records</option><option value="tip">Expert tips</option><option value="public">Public records</option></select>
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
    <p style="margin:8px 0">${x.kind === "tip" ? esc(x.text) : `<b>${esc(x.problem)}</b> — ${esc(x.symptom)}<br><span class="small">Did: ${esc(x.action)} · Result: ${esc(x.outcome)}</span>`}</p>
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
    ${d.events?.length ? `<div class="card scroll" style="margin-top:14px"><table class="t"><tr><th>Time</th><th>${esc(L().asset)}</th><th>${esc(L().problem)}</th><th>Result</th><th>By</th><th>Min</th></tr>
      ${d.events.map((e) => `<tr><td class="small">${esc(e.time)}</td><td><b>${esc(e.asset_id)}</b></td><td>${esc(e.problem)}</td><td>${e.outcome === "fixed" ? '<span class="badge b-verified">Worked</span>' : `<span class="badge b-failed">${esc(e.outcome)}</span>`}${e.status === "pending" ? ' <span class="badge b-unreviewed">Unreviewed</span>' : ""}</td><td>${esc(e.person)}</td><td>${Math.round(e.downtime_minutes || 0)}</td></tr>`).join("")}</table></div>` : ""}`;
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
  el.innerHTML = `<div class="panel-head"><div><h2>Impact & ₹</h2><p class="muted small">Before vs after Ustaad started (${fmtDate(d.ustaad_started)}).</p></div></div>
  <div class="grid g4">
    <div class="kpi"><span class="small muted">Avg time to fix</span><b>${b.mttr_minutes} → ${a.mttr_minutes} min</b><span class="delta">↓ ${pct(b.mttr_minutes, a.mttr_minutes)}%</span></div>
    <div class="kpi"><span class="small muted">Fixes that failed</span><b>${b.failed_fix_rate}% → ${a.failed_fix_rate}%</b><span class="delta">↓ ${b.failed_fix_rate - a.failed_fix_rate} pts</span></div>
    <div class="kpi"><span class="small muted">Avg cost per problem</span><b>${rupees(b.avg_cost)} → ${rupees(a.avg_cost)}</b><span class="delta">↓ ${pct(b.avg_cost, a.avg_cost)}%</span></div>
    <div class="kpi" style="background:var(--ink);color:#fff"><span class="small" style="opacity:.8">Saved since Ustaad started</span><b style="color:var(--accent)">${rupees(d.money_saved)}</b><span class="tiny" style="opacity:.75">${a.incidents} problems × lower cost each</span></div></div>
  <div class="card" style="margin-top:14px"><h3>Month by month</h3><div id="st-c"></div></div>
  <div class="grid g2" style="margin-top:14px">
    <div class="card"><h3>🔁 Repeat problems</h3>${rep.repeat.map((r) => `<div style="padding:6px 0;border-bottom:1px solid #f1ece3"><b>${esc(r.asset_id)}</b> · ${esc(r.problem)} <span class="badge b-src">${r.times}×</span>
      <div class="small muted">Every ~${r.avg_gap_days} days${r.next_expected ? ` · next due <b>${fmtDate(r.next_expected)}</b>` : ""} · ${r.total_downtime_hours} h lost · ${rupees(r.total_cost)}</div></div>`).join("") || '<p class="small muted">No repeat pattern yet.</p>'}</div>
    <div class="card"><h3>🌐 Cross-site learning</h3>${cs.links.map((l) => `<div style="padding:6px 0;border-bottom:1px solid #f1ece3"><b>${esc(l.asset_id)}</b> <span class="small muted">(${esc(l.site)}, model ${esc(l.model)})</span>
      <div class="small">learns from: ${l.learns_from.map((x) => `${esc(x.problem)} — ${esc(x.person)}, ${esc(x.site)}`).join("; ")}</div></div>`).join("") || '<p class="small muted">Only one site.</p>'}</div></div>`;
  MC.combo($("#st-c"), { labels: d.monthly.map((m) => m.month), bars: d.monthly.map((m) => m.incidents), line: d.monthly.map((m) => m.mttr_minutes), barLabel: "Problems", lineLabel: "Avg minutes to fix" });
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
      <button class="btn accent" id="sn-ask">💬 Ask Ustaad what fixed this before</button></div>`;
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

// ---------- demo guide (5 stories) ----------
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
    { t: "Try a 📷 photo question in <b>Ask Ustaad</b> (needs the Groq key). That's the tour!", go: "#/i/it/oncall/ask" } ] },
];
const G = { open: false, s: 0, k: 0 };
function drawGuide() {
  const g = $("#guide"); if (!G.open) { g.classList.add("hidden"); return; } g.classList.remove("hidden");
  const st = STORIES[G.s], step = st.steps[G.k];
  g.innerHTML = `<div class="row" style="justify-content:space-between"><h3 style="margin:0">Demo guide</h3><button class="btn ghost sm" id="g-x">✕</button></div>
  <p class="tiny muted">5 short stories cover every feature. Follow the dark box.</p>
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
    if (parts[0] === "i" && parts.length >= 4) await renderWorkspace(parts[1], parts[2], parts[3]);
    else if (parts[0] === "i" && parts[1]) await renderRoles(parts[1]);
    else if (parts[0] === "passport") await renderPassportPage(parts[1], parts[2]);
    else await renderHome();
  } catch (e) { app.innerHTML = `<div class="card"><b>Couldn't load.</b><p class="muted">${esc(e.message)}</p><a href="#/">Back home</a></div>`; }
  window.scrollTo(0, 0);
}
window.addEventListener("hashchange", route);
loadStatus(); route();
