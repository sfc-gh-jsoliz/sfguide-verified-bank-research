import json
import streamlit as st
from snowflake.snowpark.context import get_active_session

st.set_page_config(page_title="Verified Bank Research", layout="wide")

SCHEMA = "SNOWPACK_BANK_RESEARCH.CORE"
MODEL = "claude-sonnet-4-5"
session = get_active_session()

# version-safe rerun (SiS runtimes vary)
_rerun = getattr(st, "rerun", getattr(st, "experimental_rerun", lambda: None))

BADGE = {"verified": "✅ Verified", "needs_review": "⚠️ Needs review"}


def sql_df(q, params=None):
    df = session.sql(q, params=params or []).to_pandas()
    df.columns = [c.lower() for c in df.columns]
    return df


@st.cache_data(ttl=600)
def bank_options():
    df = sql_df(
        f"""SELECT DISTINCT bank_name
            FROM {SCHEMA}.BANK_QUARTERLY_METRICS
            WHERE quarter_end = (SELECT MAX(quarter_end) FROM {SCHEMA}.BANK_QUARTERLY_METRICS)
            ORDER BY bank_name"""
    )
    return df["bank_name"].tolist()


@st.cache_data(ttl=600)
def quarter_options():
    df = sql_df(f"SELECT DISTINCT quarter_end FROM {SCHEMA}.BANK_QUARTERLY_METRICS ORDER BY quarter_end DESC LIMIT 12")
    return [str(d) for d in df["quarter_end"].tolist()]


def load_reports():
    return sql_df(
        f"""SELECT run_id, subject, status, edits_applied, residual_hedges, report_md, created_at
            FROM {SCHEMA}.REPORTS ORDER BY created_at DESC"""
    )


def data_mode():
    try:
        r = session.sql(f"SELECT mode, note FROM {SCHEMA}.DATA_SOURCE_INFO").collect()[0]
        return r[0], r[1]
    except Exception:
        return "unknown", ""


def build_fact_pack(names, quarter):
    inlist = "', '".join(n.replace("'", "''") for n in names)
    row = session.sql(
        f"""SELECT ARRAY_AGG(OBJECT_CONSTRUCT(
               'bank', bank_name, 'quarter_end', quarter_end::string,
               'total_assets_usd', total_assets, 'total_deposits_usd', total_deposits,
               'net_income_qtr_usd', net_income_qtr,
               'roa_fraction', return_on_assets, 'roe_fraction', return_on_equity,
               'equity_to_assets_fraction', equity_to_assets)) AS pack
           FROM {SCHEMA}.BANK_QUARTERLY_METRICS
           WHERE bank_name IN ('{inlist}')
             AND quarter_end IN ('{quarter}', DATEADD(year, -1, '{quarter}')::date)"""
    ).collect()
    return row[0][0]


def draft_note(subject, quarter, fact_pack):
    rules = (
        "You are a buy-side bank analyst. Write a concise peer research note on the SUBJECT bank versus its peers "
        "for the reporting quarter, using ONLY the FACTS JSON.\n"
        "DATA RULES: use only numbers present in FACTS, copy exactly; never estimate or add outside figures; "
        "roa/roe/equity fractions are fractions (0.015 = 1.5%); dollar fields are USD, express in $B/$T; "
        "no hedging words (likely, approximately, around, could, industry-leading); missing = n/d.\n"
        "OUTPUT markdown starting with '# ', a one-line takeaway, a peer comparison table, then 3 bullets, "
        "ending with a '## Data Coverage' line (FFIEC/FDIC call reports; quarter)."
    )
    prompt = f"{rules}\n\nSUBJECT: {subject}\nREPORTING QUARTER: {quarter}\nFACTS: {fact_pack}"
    return session.sql("SELECT AI_COMPLETE(?, ?)", params=[MODEL, prompt]).collect()[0][0]


def verify_note(fact_pack, draft):
    vp = (
        "You are a fact-checker. Compare the DRAFT against the FACTS JSON (the only allowed source). "
        "Return ONLY a JSON object with keys: status ('verified' if every number and claim is supported and there "
        "are no hedge words like likely/approximately/around/could/industry-leading, else 'needs_review'), "
        "residual_hedges (integer), edits (array of short strings naming each unsupported or hedged claim).\n\n"
        f"FACTS: {fact_pack}\n\nDRAFT:\n{draft}"
    )
    raw = session.sql("SELECT AI_COMPLETE(?, ?)", params=[MODEL, vp]).collect()[0][0]
    s, e = raw.find("{"), raw.rfind("}")
    try:
        return json.loads(raw[s:e + 1])
    except Exception:
        return {"status": "needs_review", "residual_hedges": None, "edits": ["unparseable verifier output"]}


# ---------------- UI ----------------
st.title("Verified Bank Research")
st.caption("Grounded, self-verifying research notes on free Snowflake public financial data (FFIEC/FDIC call reports).")

_mode, _note = data_mode()
if _mode == "synthetic":
    st.warning("Sample mode — synthetic data. " + _note)
elif _mode == "marketplace":
    st.info("Live data — " + _note)

if "view" not in st.session_state:
    st.session_state["view"] = "gallery"

with st.sidebar:
    st.subheader("Generate a note")
    banks = bank_options()
    default_subject = "JPMorgan Chase Bank, National Association"
    subject = st.selectbox("Subject bank", banks, index=banks.index(default_subject) if default_subject in banks else 0)
    peers = st.multiselect(
        "Peers",
        [b for b in banks if b != subject],
        default=[b for b in ["Bank of America, National Association",
                             "Wells Fargo Bank, National Association",
                             "Citibank, National Association"] if b in banks and b != subject],
    )
    quarter = st.selectbox("Reporting quarter", quarter_options())
    if st.button("Run verified workflow", type="primary", use_container_width=True):
        with st.spinner("Running grounded + verified workflow (about 20-40s)..."):
            fp = build_fact_pack([subject] + peers, quarter)
            draft = draft_note(subject, quarter, fp)
            v = verify_note(fp, draft)
            status = "verified" if v.get("status") == "verified" else "needs_review"
            session.sql(
                f"INSERT INTO {SCHEMA}.REPORTS (subject, draft_md, report_md, status, edits_applied, residual_hedges) "
                f"SELECT ?, ?, ?, ?, ?, ?",
                params=[subject, draft, draft, status, len(v.get("edits", [])), v.get("residual_hedges")],
            ).collect()
        st.success(f"Done — {BADGE[status]}")
        st.session_state["view"] = "gallery"
        _rerun()

if st.session_state["view"].startswith("report:"):
    run_id = st.session_state["view"].split(":", 1)[1]
    rpt = load_reports()
    row = rpt[rpt["run_id"] == run_id]
    if st.button("← Back to gallery"):
        st.session_state["view"] = "gallery"
        _rerun()
    if not row.empty:
        r = row.iloc[0]
        st.markdown(f"**{BADGE.get(r['status'], r['status'])}**  &nbsp; residual hedges: {r['residual_hedges']}  |  flagged claims: {r['edits_applied']}")
        st.divider()
        st.markdown(r["report_md"])
else:
    reports = load_reports()
    if reports.empty:
        st.info("No notes yet. Use the sidebar to generate one.")
    else:
        cols = st.columns(3)
        for i, (_, r) in enumerate(reports.iterrows()):
            with cols[i % 3]:
                c = st.container()
                c.markdown(f"**{BADGE.get(r['status'], r['status'])}**")
                c.markdown(f"**{r['subject']}**")
                c.caption(f"{str(r['created_at'])[:16]} · {r['edits_applied']} flagged")
                if c.button("Open report", key=f"open_{r['run_id']}", use_container_width=True):
                    st.session_state["view"] = f"report:{r['run_id']}"
                    _rerun()
                c.markdown("---")
