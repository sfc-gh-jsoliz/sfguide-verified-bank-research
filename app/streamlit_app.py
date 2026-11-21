"""Verified Bank Research (Streamlit app).

Live mode runs on Snowflake (Streamlit in Snowflake, or locally with key-pair auth through
SNOWFLAKE_ACCOUNT / SNOWFLAKE_USER / SNOWFLAKE_PRIVATE_KEY_PATH). Sample mode replays the
bundled capture in app/sample/ and labels every AI output "Sample AI response".
Live mode never falls back to sample data: a failed call shows the error.
"""
import html
import json
import os
import pathlib
import random
import re
import time

import altair as alt
import pandas as pd
import streamlit as st

import research as R

st.set_page_config(page_title="Verified Bank Research", page_icon="✔", layout="wide")
HERE = pathlib.Path(__file__).parent
SAMPLE_DIR = HERE / "sample"
REPO = "https://github.com/sfc-gh-jsoliz/sfguide-verified-bank-research"

LOGO = ('<svg viewBox="0 0 32 32" width="28" height="28" aria-hidden="true"><path d="M16 2.5 27 6.5v8.6c0 7.1-4.6 '
        '12.2-11 14.4C9.6 27.3 5 22.2 5 15.1V6.5Z" fill="#D9AE55" stroke="#16181D" stroke-width="1.6"/><path d="m10.6 '
        '15.6 3.8 3.8 7.2-8" fill="none" stroke="#16181D" stroke-width="2.6" stroke-linecap="round" stroke-linejoin='
        '"round"/><path d="M11 23.4h10" stroke="#16181D" stroke-width="1.6" stroke-linecap="round"/></svg>')

BRASS, VERIFIED, REVIEW, ASSAY, MUTED = "#7C5A12", "#1B6646", "#9C3F0B", "#5B3970", "#585A60"

st.markdown(f"""<style>
:root {{ --brass:{BRASS}; --verified:{VERIFIED}; --review:{REVIEW}; --assay:{ASSAY}; --muted:{MUTED}; }}
[data-testid="stAppViewContainer"] {{ background:#F1F0EC; }}
[data-testid="stHeader"] {{ background:transparent; }}
.block-container {{ padding-top:1rem; max-width:1360px; }}
h1, h2, h3 {{ font-family: Newsreader, Georgia, serif !important; letter-spacing:-.01em; }}
.aw-bar {{ background:#16181D; color:#ECEAE3; border-radius:12px; padding:10px 16px; display:flex; align-items:center;
  gap:12px; flex-wrap:wrap; margin-bottom:6px; }}
.aw-bar b {{ font:600 19px Newsreader, Georgia, serif; }}
.aw-bar small {{ color:#A9A79F; letter-spacing:.14em; text-transform:uppercase; font-size:10px; }}
.aw-env {{ margin-left:auto; padding:3px 10px; border-radius:999px; font-size:12px; font-weight:700; }}
.aw-env.sample {{ background:#D9AE55; color:#16181D; }} .aw-env.live {{ background:#5CC995; color:#0C0D0F; }}
.aw-role {{ color:#A9A79F; font-size:12px; }}
.pill {{ display:inline-block; padding:1px 9px; border-radius:999px; font-size:12px; font-weight:600; }}
.pill.ok {{ color:var(--verified); background:rgba(27,102,70,.12); }} .pill.bad {{ color:var(--review); background:rgba(156,63,11,.12); }}
.pill.ai {{ color:var(--assay); background:rgba(91,57,112,.10); }} .pill.n {{ color:var(--muted); background:#E8E7E1; }}
.paper {{ background:#fff; border:1px solid #D3D1C8; border-radius:10px; padding:22px 26px; font:17px/1.6 Newsreader, Georgia, serif; color:#1A1C21; }}
.paper table {{ font:13px "Inter Tight", system-ui, sans-serif; }}
mark.cite {{ background:none; color:inherit; border-bottom:1.5px solid rgba(27,102,70,.55); padding:0 1px; }}
mark.cite sup {{ color:var(--verified); font:600 9px ui-monospace, monospace; }}
mark.cite.miss {{ border-bottom-color:var(--review); background:rgba(156,63,11,.12); }}
mark.cite.miss sup {{ color:var(--review); }}
.finding {{ border:1px solid rgba(156,63,11,.4); background:rgba(156,63,11,.07); border-radius:8px; padding:8px 10px; margin:6px 0; font-size:13px; }}
.srcrow {{ font:11px ui-monospace, monospace; color:var(--muted); }}
[data-testid="stMarkdownContainer"] table {{ display:block; overflow-x:auto; max-width:100%; }}
[data-testid="stMetric"] {{ background:#fff; border:1px solid #D3D1C8; border-radius:10px; padding:12px 14px; }}
[data-testid="stMetricValue"] {{ font-family: Newsreader, Georgia, serif; }}
</style>""", unsafe_allow_html=True)


# ------------------------------------------------------------------ sessions and mode
def _live_session():
    try:
        from snowflake.snowpark.context import get_active_session
        return get_active_session()
    except Exception:
        pass
    if os.environ.get("SNOWFLAKE_ACCOUNT") and os.environ.get("SNOWFLAKE_PRIVATE_KEY_PATH"):
        from snowflake.snowpark import Session
        return Session.builder.configs({
            "account": os.environ["SNOWFLAKE_ACCOUNT"], "user": os.environ["SNOWFLAKE_USER"],
            "authenticator": "SNOWFLAKE_JWT", "private_key_file": os.environ["SNOWFLAKE_PRIVATE_KEY_PATH"],
            "role": "SNOWPACK_BANK_RESEARCH_ROLE", "warehouse": "SNOWPACK_BANK_RESEARCH_WH",
            "database": "SNOWPACK_BANK_RESEARCH", "schema": "CORE"}).create()
    return None


@st.cache_resource
def live_session():
    return _live_session()


session = live_session()
if "mode" not in st.session_state:
    st.session_state.mode = "Live" if session is not None else "Sample"

LIVE = st.session_state.mode == "Live"
st.markdown(f"""<div class="aw-bar">{LOGO}<div><b>Verified Bank Research</b><br><small>Research desk</small></div>
<span class="aw-env {'live' if LIVE else 'sample'}">{'LIVE · Snowflake' if LIVE else 'SAMPLE data'}</span>
<span class="aw-role">Bank research analyst</span></div>""", unsafe_allow_html=True)
st.radio("Data mode", ["Sample", "Live"], key="mode", horizontal=True, label_visibility="collapsed")

if LIVE and session is None:
    st.error("Live mode needs a Snowflake connection, and none is configured.")
    st.markdown(f"""Run `app/setup_synthetic.sql`, then either deploy this app as **Streamlit in Snowflake** or run it
locally with key-pair auth:

```bash
SNOWFLAKE_ACCOUNT=<account> SNOWFLAKE_USER=<user> SNOWFLAKE_PRIVATE_KEY_PATH=<path/to/key.p8> streamlit run app/streamlit_app.py
```
Switch to **Sample** to explore on bundled data. See the [live-mode guide]({REPO}#run-it-live).""")
    st.stop()
if not LIVE:
    st.caption("Sample mode: synthetic, fictional banks. AI output was captured from a live run and is labeled **Sample AI response**.")


# ------------------------------------------------------------------ data access
def _sample(name):
    return json.loads((SAMPLE_DIR / name).read_text())


@st.cache_data(ttl=600, show_spinner=False)
def load_metrics(live):
    rows = R.metrics(session) if live else _sample("metrics.json")
    df = pd.DataFrame(rows)
    df.columns = [c.upper() for c in df.columns]
    for c in ("TOTAL_ASSETS", "TOTAL_DEPOSITS", "NET_INCOME_QTR", "RETURN_ON_ASSETS", "RETURN_ON_EQUITY",
              "EQUITY_TO_ASSETS", "TOTAL_EQUITY_CAPITAL"):
        df[c] = df[c].astype(float)
    df["QUARTER_END"] = df["QUARTER_END"].astype(str)
    return df


def load_signals(live, m):
    if live:
        rows = session.sql(f"SELECT bank_name, signal, detail FROM {R.SCHEMA}.WATCHLIST_SIGNALS ORDER BY bank_name").collect()
        return [(r[0], r[1], r[2]) for r in rows]
    out = []  # same thresholds as the WATCHLIST_SIGNALS view
    latest = m["QUARTER_END"].max()
    ago = sorted(m["QUARTER_END"].unique())[-5]
    for name, g in m.groupby("BANK_NAME"):
        n, a = g[g.QUARTER_END == latest].iloc[0], g[g.QUARTER_END == ago].iloc[0]
        dn, da = n.TOTAL_DEPOSITS / n.TOTAL_ASSETS, a.TOTAL_DEPOSITS / a.TOTAL_ASSETS
        if da - dn > 0.06:
            out.append((name, "Deposit runoff", f"Deposits/assets {da*100:.1f}% -> {dn*100:.1f}% in a year"))
        for _, r in g[g.RETURN_ON_ASSETS < 0].iterrows():
            out.append((name, "Quarterly loss", f"ROA {r.RETURN_ON_ASSETS*100:.2f}% in quarter ending {r.QUARTER_END}"))
        if (n.RETURN_ON_ASSETS - a.RETURN_ON_ASSETS) * 100 < -0.3:
            out.append((name, "ROA compression", f"ROA {(n.RETURN_ON_ASSETS - a.RETURN_ON_ASSETS)*100:+.2f} pp year over year"))
        if n.EQUITY_TO_ASSETS < 0.08:
            out.append((name, "Thin capital", f"Equity/assets {n.EQUITY_TO_ASSETS*100:.2f}% (below 8.00%)"))
    return out


def load_notes(live):
    if live:
        return R.load_reports(session)
    return [dict(n, quarter_end=n["quarter"]) for n in _sample("notes.json")]


try:
    M = load_metrics(LIVE)
    SIGNALS = load_signals(LIVE, M)
except Exception as e:  # no silent fallback
    st.error(f"Live query failed: {e}")
    st.stop()

QUARTERS = sorted(M["QUARTER_END"].unique())
LATEST, YEAR_AGO = QUARTERS[-1], QUARTERS[-5]
BANKS = (M[M.QUARTER_END == LATEST][["BANK_NAME", "PEER_GROUP"]].sort_values("BANK_NAME").to_dict("records"))
GROUP = {b["BANK_NAME"]: b["PEER_GROUP"] for b in BANKS}


def q_label(q):
    y, mth = q[:4], int(q[5:7])
    return f"Q{(mth + 2) // 3} {y}"


def usd(v):
    a = abs(v)
    s = "-" if v < 0 else ""
    return f"{s}${a/1e12:.2f}T" if a >= 1e12 else f"{s}${a/1e9:.1f}B" if a >= 1e9 else f"{s}${a/1e6:.1f}M"


def status_pill(s):
    return ('<span class="pill ok">✔ Verified</span>' if s == "verified"
            else '<span class="pill bad">⚠ Needs review</span>' if s == "needs_review" else '<span class="pill n">No note</span>')


# ------------------------------------------------------------------ note rendering
def note_html(note):
    cites = note.get("citations") or R.cite_figures(note["report_md"], note["fact_pack"])
    it = iter(enumerate(cites, 1))

    def sub(m):
        try:
            n, c = next(it)
        except StopIteration:
            return m.group(0)
        src = f'{c["source"]["bank"]} · {c["source"]["quarter"]} · {c["source"]["column"]}' if c.get("source") else "No matching figure in the fact pack"
        return f'<mark class="cite{"" if c["matched"] else " miss"}" title="{html.escape(src)}">{m.group(0)}<sup>{n}</sup></mark>'

    md = re.sub(r"^## ", "#### ", note["report_md"], flags=re.M)
    md = re.sub(r"^# ", "### ", md, flags=re.M)
    return R._FIG.sub(sub, md), cites


def show_note(note, sample):
    body, cites = note_html(note)
    matched = sum(1 for c in cites if c["matched"])
    st.markdown(
        f'{status_pill(note["status"])} &nbsp; <span style="color:{MUTED}">{note.get("claims_checked") or 0} claims checked · '
        f'{len(note["findings"])} rejected · {matched}/{len(cites)} figures traced'
        + (f' · draft {note["draft_ms"]/1000:.1f} s · verify {note["verify_ms"]/1000:.1f} s' if note.get("draft_ms") else "")
        + '</span>'
        + (' &nbsp; <span class="pill ai">✦ Sample AI response</span>' if sample else ""), unsafe_allow_html=True)
    left, right = st.columns([2.2, 1], gap="medium")
    with left:
        with st.container(border=True):
            st.markdown(body, unsafe_allow_html=True)
    with right:
        st.markdown("**Verifier findings**")
        if note["findings"]:
            for f in note["findings"]:
                st.markdown(f'<div class="finding"><b style="color:{REVIEW}">{html.escape(str(f.get("verdict","")).upper())}</b><br>'
                            f'“{html.escape(f.get("claim",""))}”<br><span style="color:{MUTED}">{html.escape(f.get("reason",""))}</span></div>',
                            unsafe_allow_html=True)
        else:
            st.markdown(f'<span style="color:{VERIFIED};font-weight:600">✔ Every claim supported by the fact pack.</span>', unsafe_allow_html=True)
        st.markdown("**Sources, figure by figure**")
        rows = "".join(
            f'<div style="margin:3px 0"><b style="color:{VERIFIED if c["matched"] else REVIEW}">{i}</b> <code>{html.escape(c["text"])}</code> '
            f'{"✓" if c["matched"] else "✗ not in fact pack"}<div class="srcrow">'
            f'{html.escape(c["source"]["bank"] + " · " + c["source"]["quarter"] + " · " + c["source"]["column"]) if c.get("source") else "—"}</div></div>'
            for i, c in enumerate(cites, 1))
        st.markdown(f'<div style="max-height:520px;overflow-y:auto">{rows}</div>', unsafe_allow_html=True)
    with st.expander(f'Fact pack sent to the model ({len(note["fact_pack"])} rows)'):
        st.json(note["fact_pack"], expanded=False)


@st.dialog("Research note", width="large")
def note_dialog(note, sample):
    st.markdown(f"### {html.escape(note['subject'])} · {q_label(str(note['quarter_end']))}")
    show_note(note, sample)


@st.dialog("Bank profile", width="large")
def bank_dialog(name):
    g = M[M.BANK_NAME == name].sort_values("QUARTER_END")
    n, a = g.iloc[-1], g[g.QUARTER_END == YEAR_AGO].iloc[0]
    st.markdown(f"### {name}  \n<span class='pill n'>{n.PEER_GROUP} peer group</span>", unsafe_allow_html=True)
    c = st.columns(3)
    c[0].metric("Total assets", usd(n.TOTAL_ASSETS), f"{(n.TOTAL_ASSETS/a.TOTAL_ASSETS-1)*100:+.1f}% vs yr ago")
    c[1].metric("Return on assets", f"{n.RETURN_ON_ASSETS*100:.2f}%", f"{(n.RETURN_ON_ASSETS-a.RETURN_ON_ASSETS)*100:+.2f} pp")
    c[2].metric("Equity / assets", f"{n.EQUITY_TO_ASSETS*100:.2f}%", f"{(n.EQUITY_TO_ASSETS-a.EQUITY_TO_ASSETS)*100:+.2f} pp")
    g = g.assign(DEP_RATIO=g.TOTAL_DEPOSITS / g.TOTAL_ASSETS)
    long = g.melt("QUARTER_END", ["RETURN_ON_ASSETS", "EQUITY_TO_ASSETS", "DEP_RATIO"], "metric", "value")
    long["metric"] = long.metric.map({"RETURN_ON_ASSETS": "ROA", "EQUITY_TO_ASSETS": "Equity/assets", "DEP_RATIO": "Deposits/assets"})
    st.altair_chart(alt.Chart(long).mark_line(point=True).encode(
        x=alt.X("QUARTER_END:N", title=None), y=alt.Y("value:Q", axis=alt.Axis(format="%"), title=None),
        color=alt.Color("metric:N", scale=alt.Scale(range=[ASSAY, VERIFIED, BRASS]), legend=alt.Legend(orient="top", title=None)),
        tooltip=["metric", "QUARTER_END", alt.Tooltip("value:Q", format=".2%")]).facet(row=alt.Row("metric:N", title=None)).resolve_scale(y="independent").properties(),
        use_container_width=True)
    sig = [s for s in SIGNALS if s[0] == name]
    for s in sig:
        st.warning(f"**{s[1]}** · {s[2]}")
    if not sig:
        st.caption("No watchlist rule fires for this bank.")


# ------------------------------------------------------------------ screens
tab_desk, tab_compose, tab_notes, tab_ask, tab_data = st.tabs(["Desk", "Compose", "Notes", "Ask the desk", "Data"])

with tab_desk:
    st.markdown("## Research desk")
    now, ago = M[M.QUARTER_END == LATEST], M[M.QUARTER_END == YEAR_AGO]
    notes_all = load_notes(LIVE)
    clean = [n for n in notes_all if not n.get("injected_claim", n.get("injected"))]
    inj = [n for n in notes_all if n.get("injected_claim", n.get("injected"))]
    k = st.columns(4)
    k[0].metric("Assets under coverage", usd(now.TOTAL_ASSETS.sum()), f"{(now.TOTAL_ASSETS.sum()/ago.TOTAL_ASSETS.sum()-1)*100:+.1f}% vs {q_label(YEAR_AGO)}")
    k[1].metric("Median return on assets", f"{now.RETURN_ON_ASSETS.median()*100:.2f}%",
                f"{(now.RETURN_ON_ASSETS.median()-ago.RETURN_ON_ASSETS.median())*100:+.2f} pp")
    k[2].metric("Clean drafts verified", f"{sum(n['status']=='verified' for n in clean)} / {len(clean)}")
    k[3].metric("Planted claims caught", f"{sum(n['status']=='needs_review' for n in inj)} / {len(inj)}")

    c1, c2 = st.columns([1.6, 1], gap="medium")
    with c1, st.container(border=True):
        grp = st.radio("Peer group", ["Large", "Regional", "Community"], index=1, horizontal=True, key="grp")
        d = M[M.PEER_GROUP == grp][["QUARTER_END", "BANK_NAME", "RETURN_ON_ASSETS"]]
        med = d.groupby("QUARTER_END", as_index=False).RETURN_ON_ASSETS.median().assign(BANK_NAME="Peer median")
        both = pd.concat([d, med]).assign(KIND=lambda x: (x.BANK_NAME == "Peer median").map({True: "median", False: "bank"}))
        names = sorted(d.BANK_NAME.unique()) + ["Peer median"]
        chart = alt.Chart(both).mark_line(point=True, strokeWidth=2).encode(
            x=alt.X("QUARTER_END:N", title=None, axis=alt.Axis(labelAngle=0, labelExpr="slice(datum.value, 0, 7)")),
            y=alt.Y("RETURN_ON_ASSETS:Q", title="Return on assets", axis=alt.Axis(format=".2%", labelLimit=90, labelPadding=6)),
            color=alt.Color("BANK_NAME:N", title=None, sort=names,
                            scale=alt.Scale(domain=names, range=[BRASS, ASSAY, VERIFIED, REVIEW, MUTED]), legend=alt.Legend(orient="bottom", columns=3)),
            strokeDash=alt.StrokeDash("KIND:N", scale=alt.Scale(domain=["bank", "median"], range=[[1, 0], [4, 4]]), legend=None),
            tooltip=[alt.Tooltip("BANK_NAME", title="Bank"), alt.Tooltip("QUARTER_END", title="Quarter"),
                     alt.Tooltip("RETURN_ON_ASSETS:Q", format=".2%", title="ROA")])
        st.markdown("**Return on assets, last 8 quarters**")
        st.altair_chart(chart.properties(height=300, padding={"left": 8}), use_container_width=True)
    with c2, st.container(border=True):
        st.markdown(f"**Watchlist signals** &nbsp; <span class='pill ai'>Rules in WATCHLIST_SIGNALS</span>", unsafe_allow_html=True)
        for name in sorted({s[0] for s in SIGNALS}):
            st.markdown(f"**{name}** <span class='pill n'>{GROUP.get(name,'')}</span>", unsafe_allow_html=True)
            for s in SIGNALS:
                if s[0] == name:
                    st.markdown(f"<span class='pill bad'>⚠ {s[1]}</span> <span style='color:{MUTED}'>{html.escape(s[2])}</span>", unsafe_allow_html=True)
        st.caption("Deposits/assets down more than 6 pp in a year, any quarterly loss, ROA down more than 0.30 pp, equity/assets below 8%.")

    st.markdown(f"#### Coverage · {q_label(LATEST)}")
    latest_status = {}
    for n in clean:
        latest_status.setdefault(n["subject"], n["status"])
    cov = now.merge(ago[["BANK_NAME", "RETURN_ON_ASSETS"]], on="BANK_NAME", suffixes=("", "_AGO"))
    cov = pd.DataFrame({
        "Bank": cov.BANK_NAME, "Peer group": cov.PEER_GROUP, "Total assets ($B)": cov.TOTAL_ASSETS / 1e9,
        "Deposits ($B)": cov.TOTAL_DEPOSITS / 1e9, "ROA %": cov.RETURN_ON_ASSETS * 100,
        "ROA vs yr ago (pp)": (cov.RETURN_ON_ASSETS - cov.RETURN_ON_ASSETS_AGO) * 100, "ROE %": cov.RETURN_ON_EQUITY * 100,
        "Equity/assets %": cov.EQUITY_TO_ASSETS * 100,
        "Latest note": cov.BANK_NAME.map(lambda b: {"verified": "✔ Verified", "needs_review": "⚠ Needs review"}.get(latest_status.get(b), "No note")),
        "Signals": cov.BANK_NAME.map(lambda b: sum(1 for s in SIGNALS if s[0] == b)),
    }).sort_values("Total assets ($B)", ascending=False)
    f1, f2 = st.columns([2, 1])
    q = f1.text_input("Search banks", placeholder="Search banks", label_visibility="collapsed")
    gsel = f2.selectbox("Peer group filter", ["All peer groups", "Large", "Regional", "Community"], label_visibility="collapsed")
    view = cov[cov.Bank.str.contains(q, case=False)] if q else cov
    view = view if gsel.startswith("All") else view[view["Peer group"] == gsel]
    ev = st.dataframe(view, hide_index=True, use_container_width=True, on_select="rerun", selection_mode="single-row",
                      column_config={c: st.column_config.NumberColumn(format="%.2f") for c in view.columns if c.endswith(("%", "(pp)"))}
                      | {c: st.column_config.NumberColumn(format="%.1f") for c in view.columns if c.endswith("($B)")})
    st.caption("Select a row to open the bank profile. Click a column header to sort.")
    if ev.selection.rows:
        bank_dialog(view.iloc[ev.selection.rows[0]]["Bank"])

with tab_compose:
    st.markdown("## Compose a verified note")
    c1, c2 = st.columns([1, 2.2], gap="medium")
    with c1, st.container(border=True):
        names = [b["BANK_NAME"] for b in BANKS]
        subject = st.selectbox("Subject bank", names, index=names.index("Ombrel National Bank") if "Ombrel National Bank" in names else 0)
        group_peers = [b for b in names if GROUP[b] == GROUP[subject] and b != subject]
        if LIVE:
            peers = st.multiselect("Peers", [b for b in names if b != subject], default=group_peers)
            quarter = st.selectbox("Reporting quarter", QUARTERS[::-1][:4])
        else:
            st.multiselect("Peers", group_peers, default=group_peers, disabled=True,
                           help="Sample mode replays captured runs with the subject's peer group.")
            peers, quarter = group_peers, LATEST
            st.selectbox("Reporting quarter", [LATEST], disabled=True)
        inject = st.toggle("Plant an unsupported claim", help="Adds a hedged ROE forecast to the draft.")
        run = st.button("✦ Run verified workflow", type="primary", use_container_width=True)
    with c2:
        if run:
            labels = {"fact_pack": "Building fact pack from BANK_QUARTERLY_METRICS",
                      "draft": f"Drafting under DATA RULES with Cortex AI_COMPLETE ({R.MODEL})",
                      "verify": "Fact-checking each claim with AI_COMPLETE structured output",
                      "save": "Tracing figures to source rows and storing the note in REPORTS"}
            with st.status("Running the verified workflow…", expanded=True) as status:
                if LIVE:
                    try:
                        rec = R.run_workflow(session, subject, peers, quarter, inject=inject, on_step=lambda k: st.write(labels[k]))
                    except Exception as e:
                        status.update(label="Workflow failed", state="error")
                        st.error(f"Live call failed: {e}")
                        st.stop()
                    status.update(label=f"Done in {rec['total_ms']/1000:.1f} s (live)", state="complete")
                else:
                    rec = next(n for n in _sample("notes.json") if n["subject"] == subject and n["injected"] == inject)
                    total = random.uniform(4.6, 7.2)
                    for k, f in (("fact_pack", .12), ("draft", .38), ("verify", .38), ("save", .12)):
                        st.write(labels[k])
                        time.sleep(total * f)
                    status.update(label="Done (Sample AI response, replayed from a live run)", state="complete")
            rec.setdefault("quarter_end", rec.get("quarter"))
            body, _ = note_html(rec)
            words = re.split(r"(\s+)", rec["report_md"])

            def stream():
                for w in words:
                    yield w
                    time.sleep(0.008)
            placeholder = st.empty()
            with placeholder.container(border=True):
                st.write_stream(stream())
            placeholder.empty()
            show_note(rec, sample=not LIVE)
            load_metrics.clear()
        else:
            st.info("Choose a subject and run the workflow. Live runs take about 20 seconds (two AI_COMPLETE calls).")

with tab_notes:
    st.markdown("## Notes library")
    try:
        notes_all = load_notes(LIVE)
    except Exception as e:
        st.error(f"Live query failed: {e}")
        notes_all = []
    if not notes_all:
        st.info("No notes yet. Compose one to see it here.")
    else:
        f1, f2 = st.columns([2, 1])
        stsel = f1.radio("Status", ["All", "Verified", "Needs review"], horizontal=True)
        show_tests = f2.toggle("Include test drafts", value=True)
        rows = [n for n in notes_all if (stsel == "All" or n["status"] == {"Verified": "verified", "Needs review": "needs_review"}[stsel])
                and (show_tests or not n.get("injected_claim", n.get("injected")))]
        df = pd.DataFrame([{
            "Status": "✔ Verified" if n["status"] == "verified" else "⚠ Needs review", "Subject": n["subject"],
            "Test draft": bool(n.get("injected_claim", n.get("injected"))), "Quarter": str(n["quarter_end"]),
            "Claims checked": n.get("claims_checked"), "Rejected": len(n["findings"]),
            "Run time (s)": round(((n.get("draft_ms") or 0) + (n.get("verify_ms") or 0)) / 1000, 1) or None} for n in rows])
        ev = st.dataframe(df, hide_index=True, use_container_width=True, on_select="rerun", selection_mode="single-row")
        st.caption("Select a row to read the note with its assay margin.")
        if ev.selection.rows:
            note_dialog(rows[ev.selection.rows[0]], sample=not LIVE)

with tab_ask:
    st.markdown("## Ask the desk")
    st.caption("A Cortex Agent with one tool: Cortex Analyst over the BANK_RESEARCH_SV semantic view.")
    sample_answers = _sample("agent.json") if (SAMPLE_DIR / "agent.json").exists() else []
    qs = [a["question"] for a in sample_answers]
    cols = st.columns(2)
    picked = None
    for i, qtext in enumerate(qs):
        if cols[i % 2].button(qtext, key=f"q{i}", use_container_width=True):
            picked = qtext
    typed = st.chat_input("Ask about the coverage universe" if LIVE else "Live mode only: type any question", disabled=not LIVE)
    question = typed or picked
    if question:
        with st.chat_message("user"):
            st.write(question)
        with st.chat_message("assistant"):
            with st.status("Cortex Agent working…", expanded=True) as status:
                for s in ("Planning with the BankMetrics tool", "Cortex Analyst writes SQL over BANK_RESEARCH_SV",
                          "Running the SQL on SNOWPACK_BANK_RESEARCH_WH", "Writing the answer from returned rows"):
                    st.write(s)
                    if not LIVE:
                        time.sleep(random.uniform(1.2, 1.9))
                    elif s.startswith("Planning"):
                        try:
                            ans = R.ask_agent(session, question)
                        except Exception as e:
                            status.update(label="Agent call failed", state="error")
                            st.error(f"Live call failed: {e}")
                            st.stop()
                if not LIVE:
                    ans = next(a for a in sample_answers if a["question"] == question)
                status.update(label=f"Answered in {ans['ms']/1000:.1f} s{' (live)' if LIVE else ' (live run, replayed)'}", state="complete")
            if not LIVE:
                st.markdown('<span class="pill ai">✦ Sample AI response</span>', unsafe_allow_html=True)
            st.write_stream((w for w in re.split(r"(\s+)", ans["answer"]) if not time.sleep(0.02)))
            if ans.get("table"):
                st.dataframe(pd.DataFrame(ans["table"]["rows"], columns=ans["table"]["columns"]), hide_index=True)
            if ans.get("sql"):
                with st.expander("SQL generated by Cortex Analyst"):
                    st.code(ans["sql"], language="sql")

with tab_data:
    st.markdown("## Data and governance")
    st.dataframe(pd.DataFrame([
        ["BANK_QUARTERLY_METRICS", "Table", f"{len(M)} rows: {M.BANK_NAME.nunique()} banks × {len(QUARTERS)} quarters, seeded generator"],
        ["BANKS", "Table", "Bank directory and peer groups"],
        ["WATCHLIST_SIGNALS", "View", "Deterministic watchlist rules for the Desk"],
        ["BANK_RESEARCH_SV", "Semantic view", "Business meaning for Cortex Analyst"],
        ["BANK_RESEARCH_AGENT", "Cortex Agent", "Ask the desk"],
        ["REPORTS", "Table", "Notes, fact packs and verifier findings"],
        ["SNOWPACK_BANK_RESEARCH_WH", "Warehouse", "XSMALL, auto-suspend 60 s"],
        ["SNOWPACK_BANK_RESEARCH_ROLE", "Role", "Owns the pack; SNOWFLAKE.CORTEX_USER"],
    ], columns=["Object", "Type", "Purpose"]), hide_index=True, use_container_width=True)
    st.markdown("**DATA RULES given to the drafting model**")
    st.code(R.DATA_RULES, language=None)
    st.markdown("**Verifier output schema (AI_COMPLETE structured output)**")
    st.code(R.VERIFY_FORMAT, language="sql")

st.caption("Illustrative example on synthetic data. Not investment, credit or regulatory advice, not an official Snowflake "
           "product, and not supported by Snowflake Support.")
