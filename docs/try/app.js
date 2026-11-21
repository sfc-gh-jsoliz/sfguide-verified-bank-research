/* Assaywell Research — no-account example (Sample mode).
   Every number and AI text here was captured from a Live run of the pack on
   SNOWPACK_BANK_RESEARCH (scripts/capture_sample.py). Nothing is generated in the browser
   except formatting, the deterministic watchlist rules and the citation matcher. */
(() => {
  "use strict";
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const jitter = (a, b) => a + Math.random() * (b - a);
  const REDUCED = matchMedia("(prefers-reduced-motion: reduce)").matches;

  const REPO = "https://github.com/sfc-gh-jsoliz/sfguide-verified-bank-research";
  const MODEL = "claude-sonnet-4-5";
  const LOGO = `<svg viewBox="0 0 32 32" aria-hidden="true"><path d="M16 2.5 27 6.5v8.6c0 7.1-4.6 12.2-11 14.4C9.6 27.3 5 22.2 5 15.1V6.5Z" fill="#D9AE55" stroke="#16181D" stroke-width="1.6"/><path d="m10.6 15.6 3.8 3.8 7.2-8" fill="none" stroke="#16181D" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/><path d="M11 23.4h10" stroke="#16181D" stroke-width="1.6" stroke-linecap="round"/></svg>`;
  const ICON = {
    check: `<svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path d="m3.5 8.5 3 3 6-7" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
    warn: `<svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path d="M8 2 15 14H1Z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><path d="M8 6.5v3.5M8 12v.1" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>`,
    spark: `<svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path d="M8 1.5 9.6 6.4 14.5 8 9.6 9.6 8 14.5 6.4 9.6 1.5 8 6.4 6.4Z" fill="currentColor"/></svg>`,
    moon: `<svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path d="M13.5 10.2A6 6 0 0 1 5.8 2.5a6 6 0 1 0 7.7 7.7Z" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>`,
  };
  const hallmark = (ok) => `<svg class="hallmark stamp" viewBox="0 0 100 100" role="img" aria-label="${ok ? "Verified hallmark" : "Needs review mark"}">
    <circle cx="50" cy="50" r="44" fill="none" stroke="${ok ? "var(--verified)" : "var(--review)"}" stroke-width="3"/>
    <circle cx="50" cy="50" r="37" fill="none" stroke="${ok ? "var(--verified)" : "var(--review)"}" stroke-width="1" stroke-dasharray="2 3"/>
    <text x="50" y="44" text-anchor="middle" font-family="Inter Tight, sans-serif" font-size="8.5" font-weight="700" letter-spacing="1.6" fill="${ok ? "var(--verified)" : "var(--review)"}">ASSAYWELL</text>
    <text x="50" y="60" text-anchor="middle" font-family="Newsreader, serif" font-size="${ok ? 14 : 9.2}" font-weight="700" fill="${ok ? "var(--verified)" : "var(--review)"}">${ok ? "VERIFIED" : "NEEDS REVIEW"}</text>
    <path d="M30 68h40" stroke="${ok ? "var(--verified)" : "var(--review)"}" stroke-width="1.5"/></svg>`;

  // ------------------------------------------------------------------ data
  const S = { banks: [], metrics: [], notes: [], agent: [], tab: "desk", groupChart: "Regional" };
  const fmtUSD = (v) => {
    if (v == null) return "n/d";
    const a = Math.abs(v), s = v < 0 ? "-" : "";
    if (a >= 1e12) return `${s}$${(a / 1e12).toFixed(2)}T`;
    if (a >= 1e9) return `${s}$${(a / 1e9).toFixed(1)}B`;
    return `${s}$${(a / 1e6).toFixed(1)}M`;
  };
  const fmtPct = (f, d = 2) => (f == null ? "n/d" : `${(f * 100).toFixed(d)}%`);
  const fmtPP = (pp) => { const r = Math.round(pp * 100) / 100; return `${r > 0 ? "+" : r < 0 ? "-" : ""}${Math.abs(r).toFixed(2)} pp`; };
  const qLabel = (q) => { const [y, m] = q.split("-"); return `Q${Math.ceil(+m / 3)} ${y}`; };

  async function load() {
    const get = (f) => fetch(`data/${f}`).then((r) => { if (!r.ok) throw new Error(`${f}: HTTP ${r.status}`); return r.json(); });
    const [banks, metrics, notes, agent] = await Promise.all(["banks.json", "metrics.json", "notes.json", "agent.json"].map(get));
    S.banks = banks.map((b) => ({ id: b.ID_RSSD, name: b.BANK_NAME, city: b.CITY, state: b.STATE, reg: b.FEDERAL_REGULATOR, group: b.PEER_GROUP }));
    S.metrics = metrics.map((m) => ({ id: m.ID_RSSD, name: m.BANK_NAME, group: m.PEER_GROUP, q: m.QUARTER_END, assets: +m.TOTAL_ASSETS, deposits: +m.TOTAL_DEPOSITS, ni: +m.NET_INCOME_QTR, roa: +m.RETURN_ON_ASSETS, roe: +m.RETURN_ON_EQUITY, eqta: +m.EQUITY_TO_ASSETS }));
    S.notes = notes;
    S.agent = agent;
    S.quarters = [...new Set(S.metrics.map((m) => m.q))].sort();
    S.latest = S.quarters.at(-1);
  }
  const series = (id, key) => S.quarters.map((q) => S.metrics.find((m) => m.id === id && m.q === q)?.[key] ?? null);
  const at = (id, q) => S.metrics.find((m) => m.id === id && m.q === q);
  const yearAgo = (q) => S.quarters[S.quarters.indexOf(q) - 4];
  const median = (a) => { const s = [...a].sort((x, y) => x - y); const n = s.length; return n ? (n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2) : null; };
  const latestNote = (name) => S.notes.find((n) => n.subject === name && !n.injected);

  /* Watchlist rules (deterministic; the same thresholds the Streamlit app runs in SQL). */
  function signals(id) {
    const out = [];
    const now = at(id, S.latest), ago = at(id, yearAgo(S.latest));
    const dNow = now.deposits / now.assets, dAgo = ago.deposits / ago.assets;
    if (dAgo - dNow > 0.06) out.push({ k: "Deposit runoff", t: `Deposits/assets ${fmtPct(dAgo, 1)} → ${fmtPct(dNow, 1)} in a year` });
    const roaS = series(id, "roa");
    const neg = roaS.findIndex((v) => v < 0);
    if (neg >= 0) out.push({ k: "Quarterly loss", t: `ROA ${fmtPct(roaS[neg])} in ${qLabel(S.quarters[neg])}` });
    if ((now.roa - ago.roa) * 100 < -0.3) out.push({ k: "ROA compression", t: `ROA ${fmtPP((now.roa - ago.roa) * 100)} year over year` });
    if (now.eqta < 0.08) out.push({ k: "Thin capital", t: `Equity/assets ${fmtPct(now.eqta)} (below 8.00%)` });
    return out;
  }

  // ------------------------------------------------------------------ shell
  function shell() {
    document.body.innerHTML = `
      <a class="sr" href="#main">Skip to content</a>
      <header class="topbar"><div class="row">
        <a class="brand" href="./" aria-label="Assaywell Research home">${LOGO}<span><b>Assaywell</b><small>Research desk</small></span></a>
        <nav class="tabs" role="tablist" aria-label="Sections">
          ${[["desk", "Desk"], ["compose", "Compose"], ["notes", "Notes"], ["ask", "Ask the desk"], ["data", "Data"]].map(([k, l]) => `<button class="tab" role="tab" data-tab="${k}" aria-selected="false">${l}</button>`).join("")}
        </nav>
        <span class="spacer"></span>
        <div class="env" role="group" aria-label="Data mode"><button aria-pressed="true" data-env="sample">Sample</button><button aria-pressed="false" data-env="live">Live</button></div>
        <button class="iconbtn" id="theme" aria-label="Toggle dark mode">${ICON.moon}</button>
        <div class="chip-role"><div class="avatar" aria-hidden="true">BA</div><span>Bank research analyst</span></div>
      </div></header>
      <div class="banner">Sample mode: synthetic, fictional banks. AI output was captured from a live Snowflake run and is labeled <b>Sample AI response</b>. <a href="${REPO}#run-it-live">Run it live in your account</a></div>
      <main id="main" tabindex="-1"></main>
      <footer class="disc">Illustrative example on synthetic data. Not investment, credit or regulatory advice, not an official Snowflake product, and not supported by Snowflake Support. <a href="../">About this pack</a> · <a href="${REPO}">Repository</a></footer>`;
    $$(".tab").forEach((b) => b.addEventListener("click", () => go(b.dataset.tab)));
    $$(".env button").forEach((b) => b.addEventListener("click", () => { if (b.dataset.env === "live") liveModal(); }));
    $("#theme").addEventListener("click", () => {
      const cur = document.documentElement.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
      document.documentElement.dataset.theme = cur === "dark" ? "light" : "dark";
      render();
    });
  }
  function go(tab, arg) {
    S.tab = tab; S.arg = arg;
    history.replaceState(null, "", `#${tab}`);
    render();
    window.scrollTo({ top: 0 });
  }
  function render() {
    $$(".tab").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.tab === S.tab)));
    const m = $("main");
    m.innerHTML = "";
    const v = document.createElement("div");
    v.className = "view";
    m.append(v);
    ({ desk, compose, notes, ask, data })[S.tab](v, S.arg);
    S.arg = undefined;
  }
  function liveModal() {
    const scrim = document.createElement("div");
    scrim.className = "scrim";
    const m = document.createElement("div");
    m.className = "modal"; m.setAttribute("role", "dialog"); m.setAttribute("aria-modal", "true"); m.setAttribute("aria-labelledby", "lm-t");
    m.innerHTML = `<h2 id="lm-t">Live mode runs in your Snowflake account</h2>
      <p>This hosted example is always Sample mode and never asks for credentials. To run the same screens live:</p>
      <ol><li>Run <code>app/setup_synthetic.sql</code> in a worksheet (about 15 seconds).</li>
      <li>Deploy <code>app/streamlit_app.py</code> as Streamlit in Snowflake, or run it locally with key-pair auth.</li>
      <li>Switch the app header to <b>Live</b>.</li></ol>
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:12px"><a class="btn primary" href="${REPO}#run-it-live">Open the live-mode guide</a><button class="btn" id="lm-close">Stay in Sample</button></div>`;
    const close = () => { scrim.remove(); m.remove(); };
    scrim.addEventListener("click", close);
    document.body.append(scrim, m);
    $("#lm-close", m).addEventListener("click", close);
    $("#lm-close", m).focus();
    m.addEventListener("keydown", (e) => { if (e.key === "Escape") close(); });
  }

  // ------------------------------------------------------------------ charts
  function sparkline(vals, color = "var(--brass)") {
    const v = vals.filter((x) => x != null);
    const lo = Math.min(...v), hi = Math.max(...v), w = 84, h = 30;
    const pts = vals.map((x, i) => `${(i / (vals.length - 1)) * w},${h - 3 - ((x - lo) / (hi - lo || 1)) * (h - 6)}`).join(" ");
    return `<svg class="spark" viewBox="0 0 ${w} ${h}" aria-hidden="true"><polyline points="${pts}" fill="none" stroke="${color}" stroke-width="1.8" stroke-linejoin="round"/></svg>`;
  }

  /* Line chart: series [{name, values, color, width, dash, emph}] over labels. fmt formats values. */
  function lineChart(el, { labels, series: ser, fmt, title }) {
    const W = 720, H = 280, P = { l: 56, r: 16, t: 14, b: 30 };
    const all = ser.flatMap((s) => s.values).filter((v) => v != null);
    let lo = Math.min(...all, 0), hi = Math.max(...all);
    const pad = (hi - lo) * 0.08; lo -= lo < 0 ? pad : 0; hi += pad;
    const x = (i) => P.l + (i / (labels.length - 1)) * (W - P.l - P.r);
    const y = (v) => P.t + (1 - (v - lo) / (hi - lo)) * (H - P.t - P.b);
    const ticks = Array.from({ length: 5 }, (_, i) => lo + ((hi - lo) * i) / 4);
    el.classList.add("chart");
    el.innerHTML = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(title)}">
      <g class="grid">${ticks.map((t) => `<line x1="${P.l}" x2="${W - P.r}" y1="${y(t)}" y2="${y(t)}"/>`).join("")}</g>
      ${lo < 0 ? `<line x1="${P.l}" x2="${W - P.r}" y1="${y(0)}" y2="${y(0)}" stroke="var(--muted)" stroke-width="1"/>` : ""}
      <g class="axis">${ticks.map((t) => `<text x="${P.l - 8}" y="${y(t) + 4}" text-anchor="end">${fmt(t)}</text>`).join("")}
        ${labels.map((l, i) => `<text x="${x(i)}" y="${H - 8}" text-anchor="middle">${esc(l)}</text>`).join("")}</g>
      ${ser.map((s) => `<polyline class="${REDUCED ? "" : "line-draw"}" points="${s.values.map((v, i) => (v == null ? "" : `${x(i)},${y(v)}`)).join(" ")}" fill="none" stroke="${s.color}" stroke-width="${s.width || 1.6}" ${s.dash ? `stroke-dasharray="${s.dash}"` : ""} stroke-linejoin="round" stroke-linecap="round"/>`).join("")}
      ${ser.filter((s) => s.emph).map((s) => s.values.map((v, i) => (v == null ? "" : `<circle cx="${x(i)}" cy="${y(v)}" r="3.2" fill="${s.color}"/>`)).join("")).join("")}
      <line class="hover" x1="0" x2="0" y1="${P.t}" y2="${H - P.b}" stroke="var(--muted)" stroke-dasharray="3 3" opacity="0"/>
      <rect x="${P.l}" y="${P.t}" width="${W - P.l - P.r}" height="${H - P.t - P.b}" fill="transparent" tabindex="0" aria-label="Chart data, use arrow keys"/>
    </svg><div class="tip" role="status"></div>
    <div class="legend">${ser.map((s) => `<span><i style="background:${s.color};${s.dash ? "background:repeating-linear-gradient(90deg," + s.color + " 0 3px,transparent 3px 6px)" : ""}"></i>${esc(s.name)}</span>`).join("")}</div>`;
    const svg = $("svg", el), tip = $(".tip", el), hl = $(".hover", el), rect = $("rect", el);
    let cur = -1;
    const show = (i) => {
      cur = Math.max(0, Math.min(labels.length - 1, i));
      const box = svg.getBoundingClientRect(), sx = box.width / W;
      hl.setAttribute("x1", x(cur)); hl.setAttribute("x2", x(cur)); hl.setAttribute("opacity", 1);
      const rows = ser.map((s) => ({ n: s.name, v: s.values[cur], c: s.color })).filter((r) => r.v != null).sort((a, b) => b.v - a.v);
      tip.innerHTML = `<b>${esc(labels[cur])}</b>${rows.map((r) => `<div><span><i style="display:inline-block;width:8px;height:8px;border-radius:2px;background:${r.c};margin-right:6px"></i>${esc(r.n)}</span><span class="mono">${fmt(r.v)}</span></div>`).join("")}`;
      tip.style.left = `${Math.min(Math.max(x(cur) * sx, 95), box.width - 95)}px`;
      tip.style.top = `${P.t * sx + 10}px`;
      tip.classList.add("on");
    };
    const hide = () => { tip.classList.remove("on"); hl.setAttribute("opacity", 0); };
    rect.addEventListener("mousemove", (e) => { const b = svg.getBoundingClientRect(); show(Math.round((((e.clientX - b.left) / b.width) * W - P.l) / ((W - P.l - P.r) / (labels.length - 1)))); });
    rect.addEventListener("mouseleave", hide);
    rect.addEventListener("blur", hide);
    rect.addEventListener("keydown", (e) => { if (e.key === "ArrowRight") show(cur + 1); if (e.key === "ArrowLeft") show(cur < 0 ? labels.length - 1 : cur - 1); });
    rect.addEventListener("focus", () => show(labels.length - 1));
  }

  // ------------------------------------------------------------------ counters
  function countUp(el, to, fmt) {
    if (REDUCED) { el.textContent = fmt(to); return; }
    const t0 = performance.now(), d = 900;
    const step = (t) => { const p = Math.min(1, (t - t0) / d); el.textContent = fmt(to * (1 - Math.pow(1 - p, 3))); if (p < 1) requestAnimationFrame(step); };
    requestAnimationFrame(step);
  }

  // ------------------------------------------------------------------ DESK
  function desk(v) {
    const L = S.latest, A = yearAgo(L);
    const now = S.metrics.filter((m) => m.q === L), ago = S.metrics.filter((m) => m.q === A);
    const sum = (a, k) => a.reduce((s, m) => s + m[k], 0);
    const assetsNow = sum(now, "assets"), assetsAgo = sum(ago, "assets");
    const roaNow = median(now.map((m) => m.roa)), roaAgo = median(ago.map((m) => m.roa));
    const clean = S.notes.filter((n) => !n.injected), inj = S.notes.filter((n) => n.injected);
    const cleanOk = clean.filter((n) => n.status === "verified").length, caught = inj.filter((n) => n.status === "needs_review").length;
    const flagged = S.banks.filter((b) => signals(b.id).length);
    v.innerHTML = `
      <div class="pagehead"><div><h1>Research desk</h1><p>Coverage of ${S.banks.length} fictional banks across three peer groups, ${qLabel(S.quarters[0])} to ${qLabel(L)}. Every note on this desk was drafted and fact-checked by Cortex AI_COMPLETE against governed call-report figures.</p></div>
        <div class="actions"><button class="btn primary" data-go="compose">${ICON.spark} Compose a note</button></div></div>
      <section class="grid g-kpi" aria-label="Key figures">
        <div class="panel kpi"><div class="label">Assets under coverage</div><div class="value" data-k="assets">–</div><div class="delta ${assetsNow >= assetsAgo ? "up" : "down"}">${assetsNow >= assetsAgo ? "▲" : "▼"} ${(((assetsNow - assetsAgo) / assetsAgo) * 100).toFixed(1)}% vs ${qLabel(A)}</div>${sparkline(S.quarters.map((q) => sum(S.metrics.filter((m) => m.q === q), "assets")))}</div>
        <div class="panel kpi"><div class="label">Median return on assets</div><div class="value" data-k="roa">–</div><div class="delta ${roaNow >= roaAgo ? "up" : "down"}">${roaNow >= roaAgo ? "▲" : "▼"} ${fmtPP((roaNow - roaAgo) * 100)} vs ${qLabel(A)}</div>${sparkline(S.quarters.map((q) => median(S.metrics.filter((m) => m.q === q).map((m) => m.roa))))}</div>
        <div class="panel kpi"><div class="label">Clean drafts verified</div><div class="value"><span data-k="ok">–</span><span class="muted" style="font-size:16px"> / ${clean.length}</span></div><div class="delta flat">${clean.reduce((s, n) => s + (n.claims_checked || 0), 0)} claims checked by the verifier</div></div>
        <div class="panel kpi"><div class="label">Planted claims caught</div><div class="value"><span data-k="caught">–</span><span class="muted" style="font-size:16px"> / ${inj.length}</span></div><div class="delta ${caught === inj.length ? "up" : "down"}">Hedged forecast injected into each test draft</div></div>
      </section>
      <section class="grid g-2" style="margin-top:16px">
        <div class="panel"><header><h2>Return on assets, last 8 quarters</h2><span class="sub">by peer group</span>
          <div class="seg" role="group" aria-label="Peer group" style="margin-left:auto">${["Large", "Regional", "Community"].map((g) => `<button aria-pressed="${g === S.groupChart}" data-g="${g}">${g}</button>`).join("")}</div></header>
          <div class="body"><div id="roaChart"></div></div></div>
        <div class="panel"><header><h2>Watchlist signals</h2><span class="sub">${flagged.length} banks flagged</span><span class="powered">Rules over BANK_QUARTERLY_METRICS</span></header>
          <div class="body">${flagged.map((b) => `<button class="btn" style="width:100%;justify-content:flex-start;margin-bottom:8px;text-align:left;display:block" data-bank="${b.id}">
              <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap"><b>${esc(b.name)}</b><span class="pill neutral">${b.group}</span></div>
              ${signals(b.id).map((s) => `<div style="font-weight:400;margin-top:4px"><span class="pill review">${ICON.warn}${s.k}</span> <span class="muted">${esc(s.t)}</span></div>`).join("")}</button>`).join("")}
            <p class="hint" style="margin:6px 0 0">Thresholds: deposits/assets down more than 6 pp in a year, any quarterly loss, ROA down more than 0.30 pp, equity/assets below 8%.</p></div></div>
      </section>
      <section class="panel" style="margin-top:16px"><header><h2>Coverage</h2><span class="sub">${qLabel(L)} · click a bank for its profile</span></header>
        <div class="toolbar"><label class="sr" for="f-q">Search banks</label><input id="f-q" class="input" placeholder="Search banks or states" style="flex:1;min-width:160px">
          <label class="sr" for="f-g">Peer group</label><select id="f-g" class="input"><option value="">All peer groups</option><option>Large</option><option>Regional</option><option>Community</option></select>
          <label class="sr" for="f-s">Note status</label><select id="f-s" class="input"><option value="">Any note status</option><option value="verified">Verified</option><option value="needs_review">Needs review</option></select></div>
        <div class="tablewrap"><table class="data" id="cov"></table></div></section>`;
    $("[data-k=assets]", v) && countUp($("[data-k=assets]", v), assetsNow, fmtUSD);
    countUp($("[data-k=roa]", v), roaNow, (x) => fmtPct(x));
    countUp($("[data-k=ok]", v), cleanOk, (x) => Math.round(x));
    countUp($("[data-k=caught]", v), caught, (x) => Math.round(x));
    $$("[data-go]", v).forEach((b) => b.addEventListener("click", () => go(b.dataset.go)));
    $$("[data-bank]", v).forEach((b) => b.addEventListener("click", () => bankDrawer(+b.dataset.bank)));
    const drawChart = () => {
      const banks = S.banks.filter((b) => b.group === S.groupChart);
      const palette = ["var(--brass)", "var(--assay)", "var(--verified)", "var(--review)"];
      lineChart($("#roaChart", v), {
        title: `Return on assets by quarter, ${S.groupChart} peer group`, labels: S.quarters.map(qLabel), fmt: (x) => fmtPct(x),
        series: [...banks.map((b, i) => ({ name: b.name, values: series(b.id, "roa"), color: palette[i % 4], width: 2, emph: true })),
          { name: "Peer median", values: S.quarters.map((q) => median(S.metrics.filter((m) => m.q === q && m.group === S.groupChart).map((m) => m.roa))), color: "var(--muted)", dash: "4 4" }],
      });
    };
    drawChart();
    $$(".seg button", v).forEach((b) => b.addEventListener("click", () => { S.groupChart = b.dataset.g; $$(".seg button", v).forEach((x) => x.setAttribute("aria-pressed", String(x === b))); drawChart(); }));
    // table
    const rows = S.banks.map((b) => { const n = at(b.id, L), o = at(b.id, A), note = latestNote(b.name); return { b, n, dRoa: (n.roa - o.roa) * 100, status: note?.status, sig: signals(b.id).length }; });
    const cols = [
      ["Bank", (r) => r.b.name, (r) => `<b>${esc(r.b.name)}</b><div class="muted" style="font-size:12px">${esc(r.b.city)}, ${r.b.state} · ${r.b.reg}</div>`],
      ["Peer group", (r) => r.b.group, (r) => `<span class="pill neutral">${r.b.group}</span>`],
      ["Total assets", (r) => r.n.assets, (r) => fmtUSD(r.n.assets), "num"],
      ["Deposits", (r) => r.n.deposits, (r) => fmtUSD(r.n.deposits), "num"],
      ["ROA", (r) => r.n.roa, (r) => fmtPct(r.n.roa), "num"],
      ["ROA vs yr ago", (r) => r.dRoa, (r) => `<span class="${r.dRoa >= 0 ? "delta-up" : "delta-down"}">${fmtPP(r.dRoa)}</span>`, "num"],
      ["ROE", (r) => r.n.roe, (r) => fmtPct(r.n.roe), "num"],
      ["Equity/assets", (r) => r.n.eqta, (r) => fmtPct(r.n.eqta), "num"],
      ["Latest note", (r) => r.status || "", (r) => statusPill(r.status) + (r.sig ? ` <span class="pill review" title="Watchlist signals">${ICON.warn}${r.sig}</span>` : "")],
    ];
    sortableTable($("#cov", v), cols, rows, { sort: 2, dir: -1, filter: (r) => {
      const q = $("#f-q", v).value.toLowerCase(), g = $("#f-g", v).value, s = $("#f-s", v).value;
      return (!q || `${r.b.name} ${r.b.state} ${r.b.city}`.toLowerCase().includes(q)) && (!g || r.b.group === g) && (!s || r.status === s);
    }, onRow: (r) => bankDrawer(r.b.id), empty: "No banks match these filters" });
    ["#f-q", "#f-g", "#f-s"].forEach((s) => $(s, v).addEventListener("input", () => $("#cov", v).refresh()));
  }
  const statusPill = (s) => (s === "verified" ? `<span class="pill verified">${ICON.check}Verified</span>` : s === "needs_review" ? `<span class="pill review">${ICON.warn}Needs review</span>` : `<span class="pill neutral">No note</span>`);

  function sortableTable(tbl, cols, rows, opt) {
    let sort = opt.sort, dir = opt.dir;
    tbl.refresh = () => {
      const data = rows.filter(opt.filter || (() => true)).sort((a, b) => { const x = cols[sort][1](a), y = cols[sort][1](b); return (x > y ? 1 : x < y ? -1 : 0) * dir; });
      tbl.innerHTML = `<thead><tr>${cols.map((c, i) => `<th class="${c[3] || ""}" aria-sort="${i === sort ? (dir > 0 ? "ascending" : "descending") : "none"}"><button data-i="${i}">${c[0]} <span aria-hidden="true">${i === sort ? (dir > 0 ? "▲" : "▼") : "↕"}</span></button></th>`).join("")}</tr></thead>
        <tbody>${data.length ? data.map((r, i) => `<tr data-i="${rows.indexOf(r)}" tabindex="0">${cols.map((c) => `<td class="${c[3] || ""}">${c[2](r)}</td>`).join("")}</tr>`).join("") : `<tr><td colspan="${cols.length}"><div class="empty"><b>${opt.empty}</b>Clear a filter to see more.</div></td></tr>`}</tbody>`;
      $$("th button", tbl).forEach((b) => b.addEventListener("click", () => { const i = +b.dataset.i; dir = i === sort ? -dir : cols[i][3] === "num" ? -1 : 1; sort = i; tbl.refresh(); }));
      $$("tbody tr[data-i]", tbl).forEach((tr) => { const go = () => opt.onRow(rows[+tr.dataset.i]); tr.addEventListener("click", go); tr.addEventListener("keydown", (e) => { if (e.key === "Enter") go(); }); });
    };
    tbl.refresh();
  }

  function drawer(title, sub, html, wide) {
    const scrim = document.createElement("div"); scrim.className = "scrim";
    const d = document.createElement("aside"); d.className = `drawer${wide ? " wide" : ""}`; d.setAttribute("role", "dialog"); d.setAttribute("aria-modal", "true"); d.setAttribute("aria-label", title);
    d.innerHTML = `<header><div>${sub}<h2>${esc(title)}</h2></div><button class="close" aria-label="Close">✕</button></header><div class="scroll">${html}</div>`;
    const prev = document.activeElement;
    const close = () => { scrim.remove(); d.remove(); prev?.focus?.(); };
    scrim.addEventListener("click", close); $(".close", d).addEventListener("click", close);
    d.addEventListener("keydown", (e) => { if (e.key === "Escape") close(); });
    document.body.append(scrim, d);
    $(".close", d).focus();
    return { el: d, close };
  }

  function bankDrawer(id) {
    const b = S.banks.find((x) => x.id === id), n = at(id, S.latest), o = at(id, yearAgo(S.latest)), note = latestNote(b.name), sig = signals(id);
    const stat = (l, val, ser, c) => `<div class="stat"><div class="l">${l}</div><div class="v">${val}</div>${sparkline(ser, c).replace('class="spark"', "")}</div>`;
    const dz = drawer(b.name, `<span class="pill neutral">${b.group} peer group</span> <span class="muted" style="font-size:12px">${esc(b.city)}, ${b.state} · ${b.reg} · RSSD ${b.id}</span>`, `
      <p class="muted" style="margin-top:0">${qLabel(S.latest)} call-report figures (synthetic). Sparklines show 8 quarters.</p>
      <div class="statgrid">
        ${stat("Total assets", fmtUSD(n.assets), series(id, "assets"))}
        ${stat("Deposits / assets", fmtPct(n.deposits / n.assets, 1), S.quarters.map((q) => { const m = at(id, q); return m.deposits / m.assets; }))}
        ${stat("Return on assets", `${fmtPct(n.roa)} <span class="${n.roa >= o.roa ? "delta-up" : "delta-down"}" style="font:600 12px var(--sans)">${fmtPP((n.roa - o.roa) * 100)}</span>`, series(id, "roa"), "var(--assay)")}
        ${stat("Equity / assets", fmtPct(n.eqta), series(id, "eqta"), "var(--verified)")}
        ${stat("Return on equity", fmtPct(n.roe), series(id, "roe"), "var(--assay)")}
        ${stat("Net income, quarter", fmtUSD(n.ni), series(id, "ni"))}
      </div>
      <h3 style="font:600 16px var(--serif);margin:18px 0 4px">Watchlist</h3>
      ${sig.length ? sig.map((s) => `<div class="signal"><span style="color:var(--review)">${ICON.warn}</span><div><b>${s.k}</b><div>${esc(s.t)}</div></div></div>`).join("") : `<p class="muted">No watchlist rule fires for this bank.</p>`}
      <h3 style="font:600 16px var(--serif);margin:18px 0 6px">Latest research note</h3>
      ${note ? `<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">${statusPill(note.status)}<span class="muted">${note.claims_checked} claims checked · ${note.peers.length} peers · ${qLabel(note.quarter)}</span></div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:12px"><button class="btn primary" data-open>Open note</button><button class="btn" data-compose>Compose a new note</button></div>` : `<p class="muted">No note yet.</p>`}`);
    $("[data-open]", dz.el)?.addEventListener("click", () => { dz.close(); noteDrawer(note); });
    $("[data-compose]", dz.el)?.addEventListener("click", () => { dz.close(); go("compose", { subject: b.name }); });
  }

  // ------------------------------------------------------------------ markdown + citations
  const FIG = /(-?\$-?[\d,]+(?:\.\d+)?\s?[BMT]\b)|(-?\d+(?:\.\d+)?(?:%| ?pp\b))/g;
  function inline(text, ctx) {
    let out = "", last = 0;
    const t = text.replace(/\*\*(.+?)\*\*/g, "\u0001$1\u0002");
    if (ctx.plain) return esc(t).replace(/\u0001/g, "<strong>").replace(/\u0002/g, "</strong>");
    t.replace(FIG, (m, a, b, off) => {
      out += esc(t.slice(last, off));
      const c = ctx.cites[ctx.i++] || { matched: false };
      const n = ctx.i;
      const src = c.source ? `${c.source.bank} · ${c.source.quarter} · ${c.source.column}` : "No matching figure in the fact pack";
      out += `<mark class="cite${c.matched ? "" : " miss"}" data-n="${n}" title="${esc(src)}">${esc(m)}<sup>${n}</sup></mark>`;
      last = off + m.length;
      return m;
    });
    out += esc(t.slice(last));
    return out.replace(/\u0001/g, "<strong>").replace(/\u0002/g, "</strong>");
  }
  function md(src, ctx, rejected = []) {
    const lines = src.replace(/\r/g, "").split("\n");
    let html = "", i = 0;
    const rej = (h, raw) => (rejected.some((r) => r && raw.toLowerCase().includes(r.toLowerCase().slice(0, 40))) ? `<span class="rejected">${h}</span>` : h);
    while (i < lines.length) {
      const l = lines[i];
      if (/^\s*$/.test(l)) { i++; continue; }
      if (/^#\s/.test(l)) { html += `<h1>${inline(l.slice(2), ctx)}</h1>`; i++; continue; }
      if (/^#{2,3}\s/.test(l)) { html += `<h2>${inline(l.replace(/^#+\s/, ""), ctx)}</h2>`; i++; continue; }
      if (/^\|/.test(l)) {
        const rows = [];
        while (i < lines.length && /^\|/.test(lines[i])) rows.push(lines[i++]);
        const cells = (r) => r.replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
        const body = rows.filter((r, k) => k > 0 && !/^\|\s*:?-/.test(r));
        html += `<div class="tablewrap"><table><thead><tr>${cells(rows[0]).map((c) => `<th>${inline(c, ctx)}</th>`).join("")}</tr></thead><tbody>${body.map((r) => `<tr>${cells(r).map((c) => `<td>${inline(c, ctx)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
        continue;
      }
      if (/^\s*[-*]\s/.test(l)) {
        const items = [];
        while (i < lines.length && /^\s*[-*]\s/.test(lines[i])) { items.push(lines[i].replace(/^\s*[-*]\s/, "")); i++; while (i < lines.length && /^\s*$/.test(lines[i]) && /^\s*[-*]\s/.test(lines[i + 1] || "")) i++; }
        html += `<ul>${items.map((t) => `<li>${rej(inline(t, ctx), t)}</li>`).join("")}</ul>`;
        continue;
      }
      if (/^\s*\d+\.\s/.test(l)) {
        const items = [];
        while (i < lines.length && (/^\s*\d+\.\s/.test(lines[i]) || (/^\s*$/.test(lines[i]) && /^\s*\d+\.\s/.test(lines[i + 1] || "")))) { if (!/^\s*$/.test(lines[i])) items.push(lines[i].replace(/^\s*\d+\.\s/, "")); i++; }
        html += `<ol>${items.map((t) => `<li>${rej(inline(t, ctx), t)}</li>`).join("")}</ol>`;
        continue;
      }
      const para = [];
      while (i < lines.length && !/^\s*$/.test(lines[i]) && !/^(#|\||\s*[-*]\s|\s*\d+\.\s)/.test(lines[i])) para.push(lines[i++]);
      const raw = para.join(" ");
      html += `<p>${rej(inline(raw, ctx), raw)}</p>`;
    }
    return html;
  }

  function noteView(n, { stream = false, sample = true } = {}) {
    const ctx = { cites: n.citations || [], i: 0 };
    const rejected = n.findings.map((f) => f.claim);
    const body = md(n.report_md, ctx, rejected);
    const ok = n.status === "verified";
    const matched = ctx.cites.filter((c) => c.matched).length;
    const wrap = document.createElement("div");
    wrap.className = "panel";
    wrap.innerHTML = `
      <div class="verdict">${statusPill(n.status)}
        <span class="muted">${n.claims_checked} claims checked · ${n.findings.length} rejected · ${matched}/${ctx.cites.length} figures traced to source rows</span>
        <span class="muted mono" style="font-size:12px">draft ${(n.draft_ms / 1000).toFixed(1)} s · verify ${(n.verify_ms / 1000).toFixed(1)} s</span>
        ${sample ? `<span class="pill ai" style="margin-left:auto">${ICON.spark}Sample AI response</span>` : ""}</div>
      <div class="reader">
        <article class="paper">${body}</article>
        <aside class="margin" aria-label="Assay margin: sources and verifier findings">
          <h3>Verifier findings</h3>
          ${n.findings.length ? n.findings.map((f) => `<div class="finding"><b>${esc(String(f.verdict).toUpperCase())}</b><div style="margin:2px 0 4px;font-weight:600">“${esc(f.claim)}”</div><div class="muted">${esc(f.reason)}</div></div>`).join("") : `<p style="color:var(--verified);font-weight:600;margin:0 0 12px">${ICON.check} Every claim supported by the fact pack.</p>`}
          <h3 style="margin-top:16px">Sources, figure by figure</h3>
          <ol>${ctx.cites.map((c, k) => `<li class="${c.matched ? "" : "miss"}" data-n="${k + 1}"><span class="n">${k + 1}</span><div><span class="mono">${esc(c.text)}</span> ${c.matched ? `<span style="color:var(--verified)">✓</span>` : `<span style="color:var(--review)">✗ not in fact pack</span>`}<div class="src">${c.source ? `${esc(c.source.bank)} · ${esc(c.source.quarter)} · ${esc(c.source.column)}` : "—"}</div></div></li>`).join("")}</ol>
          <p class="hint" style="margin-top:12px">Sources come from a deterministic match of each figure to a BANK_QUARTERLY_METRICS value in the fact pack (within display rounding).</p>
        </aside>
      </div>`;
    const paper = $(".paper", wrap);
    const link = (n2, on) => $$(`[data-n="${n2}"]`, wrap).forEach((e) => e.classList.toggle("hl", on));
    wrap.addEventListener("mouseover", (e) => { const t = e.target.closest("[data-n]"); if (t) link(t.dataset.n, true); });
    wrap.addEventListener("mouseout", (e) => { const t = e.target.closest("[data-n]"); if (t) link(t.dataset.n, false); });
    const stamp = () => paper.insertAdjacentHTML("afterbegin", hallmark(ok));
    if (stream && !REDUCED) {
      const words = [];
      const walk = (node) => node.childNodes.forEach((c) => {
        if (c.nodeType === 3 && c.textContent.trim()) {
          const frag = document.createDocumentFragment();
          c.textContent.split(/(\s+)/).forEach((p) => { if (!p) return; if (/^\s+$/.test(p)) frag.append(p); else { const s = document.createElement("span"); s.className = "w"; s.textContent = p; frag.append(s); words.push(s); } });
          c.replaceWith(frag);
        } else if (c.nodeType === 1 && c.tagName !== "SUP") walk(c);
      });
      walk(paper);
      $$("sup", paper).forEach((s) => s.classList.add("w"));
      const all = $$(".w", paper);
      const per = Math.max(6, 2600 / all.length);
      wrap.done = (async () => { for (let k = 0; k < all.length; k += 3) { all.slice(k, k + 3).forEach((s) => s.classList.add("on")); await sleep(per * 3); } stamp(); })();
    } else { stamp(); wrap.done = Promise.resolve(); }
    return wrap;
  }

  function noteDrawer(n) {
    const d = drawer(n.report_md.split("\n")[0].replace(/^#\s*/, ""), `<span class="muted" style="font-size:12px">${esc(n.subject)} vs ${n.peers.length} peers · ${qLabel(n.quarter)}${n.injected ? " · test draft with a planted claim" : ""}</span>`, "", true);
    $(".scroll", d.el).append(noteView(n));
    $(".scroll", d.el).insertAdjacentHTML("beforeend", `<details class="src" style="margin-top:14px"><summary>Fact pack sent to the model (${n.fact_pack.length} rows)</summary><pre class="code">${esc(JSON.stringify(n.fact_pack, null, 1))}</pre></details>`);
  }

  // ------------------------------------------------------------------ COMPOSE
  function compose(v, arg) {
    const subjDefault = arg?.subject || "Ombrel National Bank";
    v.innerHTML = `
      <div class="pagehead"><div><h1>Compose a verified note</h1><p>Pick a subject bank. The fact pack holds the only figures the model may cite; a second AI_COMPLETE pass fact-checks every claim before the note gets its hallmark.</p></div></div>
      <div class="compose">
        <div class="panel"><div class="body form">
          <label class="field" for="c-s">Subject bank<select id="c-s" class="input">${S.banks.map((b) => `<option ${b.name === subjDefault ? "selected" : ""}>${esc(b.name)}</option>`).join("")}</select></label>
          <div class="field"><span>Peers</span><div class="peerchips" id="c-p"></div><span class="hint" style="font-weight:400">Sample mode replays captured runs, so peers are the subject's peer group. Live mode lets you pick any peers.</span></div>
          <label class="field" for="c-q">Reporting quarter<select id="c-q" class="input"><option>${S.latest}</option></select></label>
          <label class="toggle"><input type="checkbox" id="c-i"><span><b>Plant an unsupported claim</b><br><span class="hint">Adds a hedged ROE forecast to the draft, to watch the verifier reject it.</span></span></label>
          <button class="btn primary" id="c-run" style="justify-content:center">${ICON.spark} Run verified workflow</button>
          <div class="panel" style="box-shadow:none"><div class="body"><div class="ailabel" style="margin-bottom:8px">${ICON.spark} Pipeline</div><ol class="steps" id="c-steps">
            <li data-s="fp"><span class="ico"></span><span>Build fact pack from BANK_QUARTERLY_METRICS</span><small></small></li>
            <li data-s="draft"><span class="ico"></span><span>Draft under DATA RULES with Cortex AI_COMPLETE (${MODEL})</span><small></small></li>
            <li data-s="verify"><span class="ico"></span><span>Fact-check each claim with AI_COMPLETE structured output</span><small></small></li>
            <li data-s="cite"><span class="ico"></span><span>Trace every figure to its source row</span><small></small></li>
            <li data-s="save"><span class="ico"></span><span>Store the note in REPORTS</span><small></small></li></ol></div></div>
        </div></div>
        <div id="c-out"><div class="panel"><div class="empty"><b>No note yet</b>Choose a subject and run the workflow. A run takes about 20 seconds live; Sample mode replays the captured run in about 6 seconds.</div></div></div>
      </div>`;
    const peers = () => { const b = S.banks.find((x) => x.name === $("#c-s", v).value); return S.banks.filter((x) => x.group === b.group && x.id !== b.id); };
    const drawPeers = () => { $("#c-p", v).innerHTML = peers().map((p) => `<button aria-pressed="true" disabled>${esc(p.name)}</button>`).join(""); };
    drawPeers();
    $("#c-s", v).addEventListener("change", drawPeers);
    $("#c-run", v).addEventListener("click", async () => {
      const btn = $("#c-run", v);
      const n = S.notes.find((x) => x.subject === $("#c-s", v).value && x.injected === $("#c-i", v).checked);
      btn.disabled = true;
      const out = $("#c-out", v);
      out.innerHTML = `<div class="panel"><div class="body"><div class="skeleton" style="height:28px;width:60%;margin-bottom:14px"></div>${'<div class="skeleton" style="height:14px;margin:8px 0"></div>'.repeat(6)}<div class="skeleton" style="height:120px;margin-top:16px"></div></div></div>`;
      const steps = $$("#c-steps li", v);
      steps.forEach((s) => { s.className = ""; $("small", s).textContent = ""; });
      const total = jitter(4600, 7200);
      const plan = [["fp", 0.12, `${n.fact_pack.length} rows`], ["draft", 0.36, `${(n.draft_ms / 1000).toFixed(1)} s live`], ["verify", 0.36, `${n.claims_checked} claims · ${(n.verify_ms / 1000).toFixed(1)} s live`], ["cite", 0.08, `${(n.citations || []).filter((c) => c.matched).length}/${(n.citations || []).length} traced`], ["save", 0.08, "1 row"]];
      for (const [k, f, label] of plan) {
        const li = steps.find((s) => s.dataset.s === k);
        li.className = "active";
        await sleep(total * f);
        li.className = "done"; $("small", li).textContent = label;
      }
      out.innerHTML = "";
      const view = noteView(n, { stream: true });
      out.append(view);
      await view.done;
      btn.disabled = false;
    });
  }

  // ------------------------------------------------------------------ NOTES
  function notes(v) {
    v.innerHTML = `
      <div class="pagehead"><div><h1>Notes library</h1><p>${S.notes.length} notes stored in REPORTS: a clean draft and a test draft with a planted claim for each bank in ${qLabel(S.latest)}.</p></div></div>
      <section class="panel"><div class="toolbar">
        <label class="sr" for="n-q">Search notes</label><input id="n-q" class="input" placeholder="Search subject" style="flex:1;min-width:160px">
        <div class="seg" role="group" aria-label="Status">${[["", "All"], ["verified", "Verified"], ["needs_review", "Needs review"]].map(([k, l], i) => `<button data-st="${k}" aria-pressed="${i === 0}">${l}</button>`).join("")}</div>
        <label class="toggle" style="padding:5px 10px"><input type="checkbox" id="n-i" checked><span class="hint">Include test drafts</span></label></div>
        <div class="tablewrap"><table class="data" id="nt"></table></div></section>`;
    let st = "";
    const cols = [
      ["Status", (r) => r.status, (r) => statusPill(r.status)],
      ["Subject", (r) => r.subject, (r) => `<b>${esc(r.subject)}</b>${r.injected ? ` <span class="pill brass">test draft</span>` : ""}`],
      ["Peer group", (r) => r.fact_pack[0]?.peer_group, (r) => `<span class="pill neutral">${esc(r.fact_pack.find((f) => f.bank === r.subject)?.peer_group)}</span>`],
      ["Quarter", (r) => r.quarter, (r) => qLabel(r.quarter)],
      ["Claims checked", (r) => r.claims_checked, (r) => r.claims_checked, "num"],
      ["Rejected", (r) => r.findings.length, (r) => (r.findings.length ? `<span class="delta-down">${r.findings.length}</span>` : "0"), "num"],
      ["Figures traced", (r) => (r.citations || []).filter((c) => c.matched).length / ((r.citations || []).length || 1), (r) => `${(r.citations || []).filter((c) => c.matched).length}/${(r.citations || []).length}`, "num"],
      ["Run time", (r) => r.draft_ms + r.verify_ms, (r) => `${((r.draft_ms + r.verify_ms) / 1000).toFixed(1)} s`, "num"],
    ];
    sortableTable($("#nt", v), cols, S.notes, { sort: 1, dir: 1, filter: (r) => (!st || r.status === st) && ($("#n-i", v).checked || !r.injected) && r.subject.toLowerCase().includes($("#n-q", v).value.toLowerCase()), onRow: noteDrawer, empty: "No notes match" });
    $("#n-q", v).addEventListener("input", () => $("#nt", v).refresh());
    $("#n-i", v).addEventListener("change", () => $("#nt", v).refresh());
    $$("[data-st]", v).forEach((b) => b.addEventListener("click", () => { st = b.dataset.st; $$("[data-st]", v).forEach((x) => x.setAttribute("aria-pressed", String(x === b))); $("#nt", v).refresh(); }));
  }

  // ------------------------------------------------------------------ ASK
  function ask(v) {
    v.innerHTML = `
      <div class="pagehead"><div><h1>Ask the desk</h1><p>A Cortex Agent with one tool: Cortex Analyst over the BANK_RESEARCH_SV semantic view. It answers only with figures the generated SQL returns.</p></div></div>
      <div class="chat">
        <section class="panel"><header><h2>Conversation</h2><span class="powered">Cortex Agents · Cortex Analyst</span></header>
          <div class="thread" id="a-t" aria-live="polite"><div class="empty"><b>Ask about the coverage universe</b>Pick a suggested question. Sample mode replays the four questions captured from a live run.</div></div>
          <form class="composer" id="a-f"><label class="sr" for="a-in">Question</label><input id="a-in" class="input" placeholder="Live mode only: type any question" disabled><button class="btn" disabled>Send</button></form></section>
        <aside class="panel"><header><h2>Suggested</h2></header><div class="body suggest">${S.agent.map((a, i) => `<button data-q="${i}">${esc(a.question)}</button>`).join("")}</div></aside>
      </div>`;
    const t = $("#a-t", v);
    $$("[data-q]", v).forEach((b) => b.addEventListener("click", async () => {
      $$("[data-q]", v).forEach((x) => (x.disabled = true));
      const a = S.agent[+b.dataset.q];
      if ($(".empty", t)) t.innerHTML = "";
      t.insertAdjacentHTML("beforeend", `<div class="msg user">${esc(a.question)}</div>`);
      const bot = document.createElement("div"); bot.className = "msg bot";
      bot.innerHTML = `<ol class="steps">${["Planning with the BankMetrics tool", "Cortex Analyst writes SQL over BANK_RESEARCH_SV", "Running the SQL on SNOWPACK_BANK_RESEARCH_WH", "Writing the answer from returned rows"].map((s) => `<li><span class="ico"></span><span style="font-family:var(--sans);font-size:13px">${s}</span><small></small></li>`).join("")}</ol>`;
      t.append(bot);
      const lis = $$("li", bot), total = jitter(4800, 7600);
      for (const li of lis) { li.className = "active"; await sleep(total / lis.length); li.className = "done"; }
      $("small", lis.at(-1)).textContent = `${(a.ms / 1000).toFixed(1)} s live`;
      const html = md(a.answer, { plain: true });
      const body = document.createElement("div");
      body.innerHTML = `<div class="ailabel" style="margin:10px 0 6px">${ICON.spark} Sample AI response</div><div class="ans">${html}</div>
        ${a.table ? `<details class="src" open><summary>Rows returned (${a.table.rows.length})</summary><div class="tablewrap"><table class="data"><thead><tr>${a.table.columns.map((c) => `<th>${esc(c)}</th>`).join("")}</tr></thead><tbody>${a.table.rows.map((r) => `<tr>${r.map((c) => `<td class="${isNaN(+c) ? "" : "num"}">${esc(isNaN(+c) ? c : (+c).toLocaleString(undefined, { maximumFractionDigits: 6 }))}</td>`).join("")}</tr>`).join("")}</tbody></table></div></details>` : ""}
        ${a.sql ? `<details class="src"><summary>SQL generated by Cortex Analyst</summary><pre class="code">${esc(a.sql)}</pre></details>` : ""}`;
      bot.append(body);
      const words = [];
      const walk = (node) => node.childNodes.forEach((c) => { if (c.nodeType === 3 && c.textContent.trim()) { const f = document.createDocumentFragment(); c.textContent.split(/(\s+)/).forEach((p) => { if (/^\s+$/.test(p)) f.append(p); else if (p) { const s = document.createElement("span"); s.className = "w"; s.textContent = p; f.append(s); words.push(s); } }); c.replaceWith(f); } else if (c.nodeType === 1) walk(c); });
      if (!REDUCED) { walk($(".ans", body)); for (const w of words) { w.classList.add("on"); await sleep(28); } }
      $$("[data-q]", v).forEach((x) => (x.disabled = false));
    }));
  }

  // ------------------------------------------------------------------ DATA
  function data(v) {
    v.innerHTML = `
      <div class="pagehead"><div><h1>Data and governance</h1><p>What the desk is allowed to know, and where each piece lives in Snowflake.</p></div></div>
      <section class="grid g-2">
        <div class="panel"><header><h2>Objects in SNOWPACK_BANK_RESEARCH.CORE</h2></header><div class="tablewrap"><table class="data" style="cursor:default"><thead><tr><th>Object</th><th>Type</th><th>Role in the workflow</th></tr></thead><tbody>
          ${[["BANK_QUARTERLY_METRICS", "Table", `${S.metrics.length} rows: ${S.banks.length} banks × ${S.quarters.length} quarters, seeded generator`], ["BANKS", "Table", "Bank directory and peer groups"], ["BANK_RESEARCH_SV", "Semantic view", "Business meaning for Cortex Analyst"], ["BANK_RESEARCH_AGENT", "Cortex Agent", "Ask the desk; Analyst tool over the semantic view"], ["REPORTS", "Table", "Notes, fact packs and verifier findings"], ["DATA_SOURCE_INFO", "View", "Synthetic vs real-data marker"], ["SNOWPACK_BANK_RESEARCH_WH", "Warehouse", "XSMALL, auto-suspend 60 s"], ["SNOWPACK_BANK_RESEARCH_ROLE", "Role", "Owns the pack; CORTEX_USER database role"]]
            .map((r) => `<tr><td class="mono" style="white-space:normal">${r[0]}</td><td><span class="pill neutral">${r[1]}</span></td><td style="white-space:normal">${r[2]}</td></tr>`).join("")}</tbody></table></div></div>
        <div class="panel"><header><h2>Semantic view</h2><span class="powered">Cortex Analyst</span></header><div class="body">
          <p class="muted" style="margin-top:0">Dimensions</p><div style="display:flex;flex-wrap:wrap;gap:6px">${["bank_name", "peer_group", "state", "city", "federal_regulator", "quarter_end", "report_year"].map((d) => `<span class="pill neutral mono">${d}</span>`).join("")}</div>
          <p class="muted">Metrics</p><div style="display:flex;flex-wrap:wrap;gap:6px">${["total_assets_usd", "total_deposits_usd", "net_income_qtr_usd", "avg_return_on_assets", "avg_return_on_equity", "avg_equity_to_assets", "bank_count"].map((d) => `<span class="pill brass mono">${d}</span>`).join("")}</div>
          <pre class="code">SELECT * FROM SEMANTIC_VIEW(BANK_RESEARCH_SV
  METRICS avg_return_on_assets
  DIMENSIONS peer_group, quarter_end)
ORDER BY quarter_end;</pre></div></div>
      </section>
      <section class="panel" style="margin-top:16px"><header><h2>The DATA RULES contract</h2><span class="sub">what the drafting model is told</span></header><div class="body">
        <ol style="margin:0;padding-left:20px;line-height:1.7"><li>Use only numbers present in the fact pack, copied exactly. No estimates or outside figures.</li><li>Fractions become percentages with two decimals; dollars become $B (or $T, $M).</li><li>No hedging words (likely, approximately, around, could, industry-leading).</li><li>Missing figures are written n/d. No real bank or company names.</li><li>No calculations: year-over-year changes and size ranks are copied from precomputed fact-pack fields.</li></ol>
        <p class="hint">The verifier is a second AI_COMPLETE call that returns structured output (status, residual_hedges, findings[claim, reason, verdict]). A note is Verified only when every checked claim is SUPPORTED.</p></div></section>`;
  }

  // ------------------------------------------------------------------ boot
  shell();
  const TABS = ["desk", "compose", "notes", "ask", "data"];
  addEventListener("hashchange", () => { const h = location.hash.slice(1); if (TABS.includes(h) && h !== S.tab) { $$(".scrim, .drawer, .modal").forEach((e) => e.remove()); go(h); } });
  load().then(() => { const h = location.hash.slice(1); go(TABS.includes(h) ? h : "desk"); })
    .catch((e) => { $("main").innerHTML = `<div class="panel"><div class="empty"><b>Couldn't load the sample data</b>${esc(e.message)}</div></div>`; });
})();
