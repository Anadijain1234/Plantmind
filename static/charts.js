/* Tiny SVG charts for Ustaad — no external library, works offline. */
(function () {
  const NS = "http://www.w3.org/2000/svg";
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const fmt = (v) => (Math.abs(v) >= 1000 ? Math.round(v).toLocaleString("en-IN") : Math.round(v * 10) / 10);
  const niceMax = (m) => { if (m <= 0) return 1; const p = Math.pow(10, Math.floor(Math.log10(m))); const n = m / p; return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10) * p; };
  const W = (el) => Math.max(280, el.clientWidth || 600);
  function svg(el, w, h, body) { el.innerHTML = `<svg xmlns="${NS}" width="100%" height="${h}" viewBox="0 0 ${w} ${h}" style="display:block;font-family:Inter,system-ui,sans-serif">${body}</svg>`; }
  function tip(title) { return `<title>${esc(title)}</title>`; }

  function hbar(el, { labels, values, color = "#e8833a", unit = "" }) {
    const w = W(el), rowH = 26, lw = Math.min(220, Math.max(90, w * 0.34)), h = labels.length * rowH + 24, max = niceMax(Math.max(...values, 0));
    let b = "";
    labels.forEach((l, i) => {
      const y = 8 + i * rowH, bw = ((w - lw - 60) * values[i]) / max;
      const lab = l.length > 34 ? l.slice(0, 33) + "…" : l;
      b += `<text x="${lw - 8}" y="${y + 15}" text-anchor="end" font-size="12" fill="#2b3a4f">${esc(lab)}${tip(l)}</text>`;
      b += `<rect x="${lw}" y="${y + 3}" width="${Math.max(2, bw)}" height="${rowH - 9}" rx="5" fill="${color}">${tip(`${l}: ${fmt(values[i])} ${unit}`)}</rect>`;
      b += `<text x="${lw + Math.max(2, bw) + 6}" y="${y + 15}" font-size="12" fill="#16202e" font-weight="600">${fmt(values[i])}</text>`;
    });
    svg(el, w, h, b);
  }

  function axes(w, h, pad, max, steps = 4) {
    let b = "";
    for (let i = 0; i <= steps; i++) {
      const v = (max * i) / steps, y = h - pad.b - ((h - pad.t - pad.b) * i) / steps;
      b += `<line x1="${pad.l}" x2="${w - pad.r}" y1="${y}" y2="${y}" stroke="#f0ebe2"/><text x="${pad.l - 6}" y="${y + 4}" text-anchor="end" font-size="11" fill="#6b7280">${fmt(v)}</text>`;
    }
    return b;
  }
  function xlabels(labels, x0, step, y, every = 1) {
    return labels.map((l, i) => (i % every === 0 ? `<text x="${x0 + step * i + step / 2}" y="${y}" text-anchor="middle" font-size="11" fill="#6b7280">${esc(l)}</text>` : "")).join("");
  }

  function stacked(el, { labels, series, colors }) {
    const w = W(el), h = 280, pad = { l: 44, r: 12, t: 30, b: 28 }, names = Object.keys(series);
    const totals = labels.map((_, i) => names.reduce((a, n) => a + series[n][i], 0)), max = niceMax(Math.max(...totals));
    const step = (w - pad.l - pad.r) / labels.length, bw = Math.max(4, step * 0.65);
    let b = axes(w, h, pad, max);
    labels.forEach((l, i) => {
      let y = h - pad.b;
      names.forEach((n, k) => { const v = series[n][i], bh = ((h - pad.t - pad.b) * v) / max; y -= bh;
        b += `<rect x="${pad.l + step * i + (step - bw) / 2}" y="${y}" width="${bw}" height="${bh}" fill="${colors[k % colors.length]}">${tip(`${l} · ${n}: ${v}`)}</rect>`; });
    });
    b += xlabels(labels.map((l) => l.slice(2)), pad.l, step, h - 8, Math.ceil(labels.length / 8));
    b += names.map((n, k) => `<rect x="${pad.l + k * 80}" y="6" width="10" height="10" rx="2" fill="${colors[k % colors.length]}"/><text x="${pad.l + k * 80 + 14}" y="15" font-size="11" fill="#2b3a4f">${esc(n)}</text>`).join("");
    svg(el, w, h, b);
  }

  function combo(el, { labels, bars, line, barLabel, lineLabel }) {
    const w = W(el), h = 280, pad = { l: 40, r: 44, t: 30, b: 28 };
    const m1 = niceMax(Math.max(...bars, 0)), m2 = niceMax(Math.max(...line, 0));
    const step = (w - pad.l - pad.r) / labels.length, bw = Math.max(6, step * 0.55), ih = h - pad.t - pad.b;
    let b = axes(w, h, pad, m1);
    for (let i = 0; i <= 4; i++) { const y = h - pad.b - (ih * i) / 4; b += `<text x="${w - pad.r + 6}" y="${y + 4}" font-size="11" fill="#e8833a">${fmt((m2 * i) / 4)}</text>`; }
    labels.forEach((l, i) => { const bh = (ih * bars[i]) / m1;
      b += `<rect x="${pad.l + step * i + (step - bw) / 2}" y="${h - pad.b - bh}" width="${bw}" height="${bh}" rx="4" fill="#e8d9c5">${tip(`${l}: ${bars[i]} ${barLabel}`)}</rect>`; });
    const pts = line.map((v, i) => `${pad.l + step * i + step / 2},${h - pad.b - (ih * v) / m2}`);
    b += `<polyline points="${pts.join(" ")}" fill="none" stroke="#e8833a" stroke-width="3" stroke-linejoin="round"/>`;
    b += line.map((v, i) => `<circle cx="${pad.l + step * i + step / 2}" cy="${h - pad.b - (ih * v) / m2}" r="4" fill="#e8833a">${tip(`${labels[i]}: ${v} ${lineLabel}`)}</circle>`).join("");
    b += xlabels(labels, pad.l, step, h - 8, Math.ceil(labels.length / 8));
    b += `<rect x="${pad.l}" y="6" width="10" height="10" rx="2" fill="#e8d9c5"/><text x="${pad.l + 14}" y="15" font-size="11" fill="#2b3a4f">${esc(barLabel)}</text>
          <rect x="${pad.l + 120}" y="10" width="14" height="3" fill="#e8833a"/><text x="${pad.l + 138}" y="15" font-size="11" fill="#2b3a4f">${esc(lineLabel)}</text>`;
    svg(el, w, h, b);
  }

  function vbar(el, { labels, values, color = "#e8833a", unit = "" }) {
    const w = W(el), h = 260, pad = { l: 44, r: 10, t: 14, b: 28 }, max = niceMax(Math.max(...values, 0));
    const step = (w - pad.l - pad.r) / labels.length, bw = Math.max(6, step * 0.6), ih = h - pad.t - pad.b;
    let b = axes(w, h, pad, max);
    labels.forEach((l, i) => { const bh = (ih * values[i]) / max;
      b += `<rect x="${pad.l + step * i + (step - bw) / 2}" y="${h - pad.b - bh}" width="${bw}" height="${bh}" rx="4" fill="${color}">${tip(`${l}: ${fmt(values[i])} ${unit}`)}</rect>`; });
    b += xlabels(labels, pad.l, step, h - 8, Math.ceil(labels.length / 10));
    svg(el, w, h, b);
  }

  function lines(el, { labels, series, hlines = [], ymax, ylabel = "" }) {
    const w = W(el), h = 320, pad = { l: 40, r: 12, t: 12, b: 28 }, n = Math.max(labels.length, 2), ih = h - pad.t - pad.b;
    const max = ymax || niceMax(Math.max(1, ...series.flatMap((s) => s.data)));
    const x = (i) => pad.l + ((w - pad.l - pad.r) * i) / (n - 1), y = (v) => h - pad.b - (ih * Math.min(v, max)) / max;
    let b = axes(w, h, pad, max);
    hlines.forEach((hl) => (b += `<line x1="${pad.l}" x2="${w - pad.r}" y1="${y(hl.y)}" y2="${y(hl.y)}" stroke="${hl.color}" stroke-dasharray="6 4" stroke-width="1.5"/>`));
    series.forEach((s) => { if (s.data.length) b += `<polyline points="${s.data.map((v, i) => `${x(i)},${y(v)}`).join(" ")}" fill="none" stroke="${s.color}" stroke-width="2.2" stroke-linejoin="round"/>`; });
    b += xlabels(labels, pad.l - (w - pad.l - pad.r) / (n - 1) / 2, (w - pad.l - pad.r) / (n - 1), h - 8, Math.ceil(n / 9));
    if (ylabel) b += `<text x="${pad.l + 4}" y="${pad.t + 10}" font-size="11" fill="#6b7280">${esc(ylabel)}</text>`;
    svg(el, w, h, b);
  }

  window.MC = { hbar, vbar, stacked, combo, lines };
})();
