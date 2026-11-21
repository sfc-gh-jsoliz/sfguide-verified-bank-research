"""Verified Bank Research: the live research pipeline.

Shared by the Streamlit app and scripts/capture_sample.py so both run exactly the
same Snowflake calls:

1. build_fact_pack  - SQL over BANK_QUARTERLY_METRICS: the only figures the model may cite
2. draft_note       - Cortex AI_COMPLETE writes the note under DATA RULES
3. verify_note      - Cortex AI_COMPLETE (structured output) fact-checks the draft
4. cite_figures     - deterministic check: every figure in the note must match a fact-pack value
5. save_report      - stores the note and the verifier findings in REPORTS
6. ask_agent        - Cortex Agent (Cortex Analyst over the semantic view) via DATA_AGENT_RUN
"""
import json
import re
import time

SCHEMA = "SNOWPACK_BANK_RESEARCH.CORE"
MODEL = "claude-sonnet-4-5"  # any AI_COMPLETE model your account has

# The sentence appended when "inject an unsupported claim" is on (tests the verifier).
INJECTED_CLAIM = (
    "Management commentary suggests return on equity will likely reach around 18.5% next year, "
    "an industry-leading level for its peer group."
)

DATA_RULES = (
    "You are a bank research analyst. Write a concise peer research note on the SUBJECT bank versus its peers "
    "for the reporting quarter, using ONLY the FACTS JSON.\n"
    "DATA RULES (mandatory):\n"
    "1. Use ONLY numbers present in FACTS. Copy them exactly. Never estimate, extrapolate or add outside figures.\n"
    "2. roa_fraction, roe_fraction and equity_to_assets_fraction are fractions (0.015 = 1.50%). Write them as "
    "percentages with exactly two decimals.\n"
    "3. Dollar fields are USD. Write them in $B with one decimal (or $T with two decimals above $1,000B, or $M with "
    "one decimal below $1B).\n"
    "4. No hedging words (likely, approximately, around, could, industry-leading) and no market or consensus claims.\n"
    "5. If a figure is missing, write n/d. Do not invent a row. Do not name any real bank or company.\n"
    "6. Do not calculate anything. Do not state ratios, multiples or relative changes (\"half\", \"twice\", "
    "\"x% decline\"). For year-over-year changes copy the *_change_pp_vs_year_ago fields, written like \"down 0.48 pp\". "
    "For size rankings copy asset_rank_in_group, written like \"3rd of 4 by total assets\".\n"
    "OUTPUT: markdown starting with '# ', then a one-line '**Takeaway.**' paragraph, a peer comparison table "
    "(Bank, Total assets, Deposits, ROA, ROE, Equity/assets) for the reporting quarter, then exactly 3 short bullets "
    "(one on scale, one on profitability with the year-ago change, one on capital). End with a '## Data coverage' "
    "line naming the source (BANK_QUARTERLY_METRICS, synthetic call-report data) and the quarters used."
)

VERIFY_RULES = (
    "You are a fact-checker for bank research notes. Compare the DRAFT against the FACTS JSON, the only allowed "
    "source. Check every number and every claim. A number is supported only if it equals a FACTS value after the "
    "stated unit conversion (fractions to %, USD to $B or $T, rounding to the shown decimals). Year-over-year "
    "changes must equal a *_change_pp_vs_year_ago field. Rankings and comparisons (largest, smallest, 2nd, above, "
    "below, trailing, middle of the range) must hold in FACTS. Hedge words are likely, approximately, "
    "around, could, industry-leading.\n"
    "Return one finding per factual claim you checked, with verdict SUPPORTED, UNSUPPORTED or HEDGED. Decide each "
    "reason first: one short sentence comparing the claim with the FACTS value. Then the verdict, which must agree "
    "with the reason. "
    "status is 'verified' when every verdict is SUPPORTED, else 'needs_review'. residual_hedges counts hedge words."
)

VERIFY_FORMAT = (
    "TYPE OBJECT(status STRING, residual_hedges NUMBER, "
    "findings ARRAY(OBJECT(claim STRING, reason STRING, verdict STRING)))"
)


def _rows(session, sql, params=None):
    return session.sql(sql, params=params or []).collect()


def bank_directory(session):
    rows = _rows(session, f"""
        SELECT id_rssd, bank_name, city, state, federal_regulator, peer_group
        FROM {SCHEMA}.BANK_QUARTERLY_METRICS
        QUALIFY ROW_NUMBER() OVER (PARTITION BY id_rssd ORDER BY quarter_end DESC) = 1
        ORDER BY id_rssd""")
    return [r.as_dict() for r in rows]


def metrics(session):
    rows = _rows(session, f"""
        SELECT id_rssd, bank_name, peer_group, quarter_end::STRING AS quarter_end,
               total_assets, total_deposits, net_income_qtr, return_on_assets,
               return_on_equity, equity_to_assets, total_equity_capital
        FROM {SCHEMA}.BANK_QUARTERLY_METRICS ORDER BY id_rssd, quarter_end""")
    return [r.as_dict() for r in rows]


def build_fact_pack(session, names, quarter):
    """Reporting-quarter and year-ago rows for the chosen banks. The reporting-quarter rows also carry the
    year-over-year changes (percentage points) and the asset rank within the group, so the model copies
    them instead of calculating."""
    row = _rows(session, f"""
        WITH m AS (
          SELECT * FROM {SCHEMA}.BANK_QUARTERLY_METRICS
          WHERE ARRAY_CONTAINS(bank_name::VARIANT, PARSE_JSON(?))
            AND quarter_end IN (?::DATE, DATEADD(year, -1, ?::DATE))
        ), x AS (
          SELECT m.*,
                 LEAD(return_on_assets) OVER (PARTITION BY id_rssd ORDER BY quarter_end DESC) AS roa_prev,
                 LEAD(return_on_equity) OVER (PARTITION BY id_rssd ORDER BY quarter_end DESC) AS roe_prev,
                 LEAD(equity_to_assets) OVER (PARTITION BY id_rssd ORDER BY quarter_end DESC) AS eqta_prev,
                 RANK() OVER (PARTITION BY quarter_end ORDER BY total_assets DESC) AS asset_rank,
                 COUNT(*) OVER (PARTITION BY quarter_end) AS group_size
          FROM m
        )
        SELECT ARRAY_AGG(OBJECT_CONSTRUCT_KEEP_NULL(
                 'bank', bank_name, 'peer_group', peer_group, 'quarter_end', quarter_end::STRING,
                 'total_assets_usd', total_assets, 'total_deposits_usd', total_deposits,
                 'net_income_qtr_usd', net_income_qtr,
                 'roa_fraction', return_on_assets, 'roe_fraction', return_on_equity,
                 'equity_to_assets_fraction', equity_to_assets,
                 'asset_rank_in_group', asset_rank || ' of ' || group_size,
                 'roa_change_pp_vs_year_ago', IFF(roa_prev IS NULL, NULL, ROUND((return_on_assets - roa_prev) * 100, 2)),
                 'roe_change_pp_vs_year_ago', IFF(roe_prev IS NULL, NULL, ROUND((return_on_equity - roe_prev) * 100, 2)),
                 'equity_to_assets_change_pp_vs_year_ago', IFF(eqta_prev IS NULL, NULL, ROUND((equity_to_assets - eqta_prev) * 100, 2))))
                 WITHIN GROUP (ORDER BY quarter_end DESC, total_assets DESC) AS pack
        FROM x""",
        [json.dumps(names), quarter, quarter])
    pack = json.loads(row[0][0])
    # year-ago rows only need the levels
    for r in pack:
        if r["quarter_end"] != quarter:
            for k in ("roa_change_pp_vs_year_ago", "roe_change_pp_vs_year_ago",
                      "equity_to_assets_change_pp_vs_year_ago"):
                r.pop(k, None)
    return pack


def _complete(session, prompt, response_format=None):
    if response_format:
        sql = f"SELECT AI_COMPLETE(model => ?, prompt => ?, response_format => {response_format})"
    else:
        sql = "SELECT AI_COMPLETE(?, ?)"
    t = time.time()
    out = _rows(session, sql, [MODEL, prompt])[0][0]
    return out, int((time.time() - t) * 1000)


def draft_note(session, subject, quarter, fact_pack):
    prompt = f"{DATA_RULES}\n\nSUBJECT: {subject}\nREPORTING QUARTER: {quarter}\nFACTS: {json.dumps(fact_pack)}"
    text, ms = _complete(session, prompt)
    # AI_COMPLETE returns a JSON string literal for plain prompts
    try:
        text = json.loads(text)
    except Exception:
        pass
    return text.strip(), ms


def inject_claim(draft):
    """Insert the unsupported claim after the takeaway paragraph."""
    parts = draft.split("\n\n")
    idx = next((i for i, p in enumerate(parts) if p.startswith("**Takeaway")), 0) + 1
    parts.insert(idx, INJECTED_CLAIM)
    return "\n\n".join(parts)


def verify_note(session, fact_pack, draft):
    prompt = f"{VERIFY_RULES}\n\nFACTS: {json.dumps(fact_pack)}\n\nDRAFT:\n{draft}"
    raw, ms = _complete(session, prompt, VERIFY_FORMAT)
    try:
        v = json.loads(raw)
    except Exception:
        v = {"status": "needs_review", "residual_hedges": None,
             "findings": [{"claim": "(verifier output)", "verdict": "unparseable", "reason": raw[:300]}]}
    checked = v.get("findings") or []
    findings = [f for f in checked if str(f.get("verdict", "")).upper() != "SUPPORTED"]
    v["findings"] = findings
    v["claims_checked"] = len(checked)
    v["status"] = "verified" if v.get("status") == "verified" and not findings else "needs_review"
    return v, ms


# ---------------------------------------------------------------- citations
_FIG = re.compile(r"(-?\$-?[\d,]+(?:\.\d+)?\s?[BMT]\b)|(-?\d+(?:\.\d+)?(?:%| ?pp\b))")

_LABELS = {
    "total_assets_usd": "TOTAL_ASSETS", "total_deposits_usd": "TOTAL_DEPOSITS",
    "net_income_qtr_usd": "NET_INCOME_QTR", "roa_fraction": "RETURN_ON_ASSETS",
    "roe_fraction": "RETURN_ON_EQUITY", "equity_to_assets_fraction": "EQUITY_TO_ASSETS",
}


def _candidates(fact_pack):
    out = []
    for r in fact_pack:
        for k, v in r.items():
            if v is None:
                continue
            src = {"bank": r["bank"], "quarter": r["quarter_end"], "column": _LABELS.get(k, k.upper()), "value": v}
            if k.endswith("_usd"):
                out.append(("usd", float(v), src))
            elif k.endswith("_fraction"):
                out.append(("pct", float(v) * 100, src))
            elif k.endswith("_pp_vs_year_ago"):
                out.append(("pp", float(v), src))
                out.append(("pp", abs(float(v)), src))
    return out


def cite_figures(note, fact_pack):
    """Match every $B/$T and % figure in the note to a fact-pack value (within display rounding)."""
    cands = _candidates(fact_pack)
    cites = []
    for m in _FIG.finditer(note):
        tok = m.group(0)
        num = float(re.sub(r"[^\d.\-]", "", tok) or 0)
        if not tok.startswith("$") and not tok.startswith("-$"):
            digits = re.sub(r"[^\d.]", "", tok)
            decimals = len(digits.split(".")[1]) if "." in digits else 0
            tol = 0.5 * 10 ** -decimals + 1e-9
            kind = "pp" if tok.endswith("pp") else "pct"
            hits = [c for c in cands if c[0] == kind and abs(c[1] - num) <= tol]
        else:
            unit = {"T": 1e12, "B": 1e9, "M": 1e6}[tok.rstrip()[-1]]
            body = tok.replace("$", "").rstrip("BMT ").replace(",", "")
            decimals = len(body.split(".")[1]) if "." in body else 0
            tol = 0.5 * 10 ** -decimals * unit + 1
            hits = [c for c in cands if c[0] == "usd" and abs(c[1] - num * unit) <= tol]
        cites.append({"text": tok, "start": m.start(), "matched": bool(hits),
                      "source": hits[0][2] if hits else None})
    return cites


def save_report(session, rec):
    _rows(session, f"""
        INSERT INTO {SCHEMA}.REPORTS (run_id, subject, peers, quarter_end, injected_claim, fact_pack, draft_md,
               report_md, status, claims_checked, edits_applied, residual_hedges, findings, model, draft_ms, verify_ms)
        SELECT ?, ?, PARSE_JSON(?), ?::DATE, ?, PARSE_JSON(?), ?, ?, ?, ?, ?, ?, PARSE_JSON(?), ?, ?, ?""",
        [rec["run_id"], rec["subject"], json.dumps(rec["peers"]), rec["quarter"], rec["injected"],
         json.dumps(rec["fact_pack"]), rec["draft_md"], rec["report_md"], rec["status"], rec["claims_checked"],
         len(rec["findings"]), rec.get("residual_hedges"), json.dumps(rec["findings"]),
         MODEL, rec["draft_ms"], rec["verify_ms"]])


def run_workflow(session, subject, peers, quarter, inject=False, on_step=None):
    """The whole verified workflow. on_step(name) is called as each stage starts."""
    import uuid
    step = on_step or (lambda *_: None)
    t0 = time.time()
    step("fact_pack")
    fp = build_fact_pack(session, [subject] + list(peers), quarter)
    step("draft")
    draft, draft_ms = draft_note(session, subject, quarter, fp)
    note = inject_claim(draft) if inject else draft
    step("verify")
    v, verify_ms = verify_note(session, fp, note)
    rec = {
        "run_id": str(uuid.uuid4()), "subject": subject, "peers": list(peers), "quarter": quarter,
        "injected": bool(inject), "fact_pack": fp, "draft_md": draft, "report_md": note,
        "status": v["status"], "claims_checked": v["claims_checked"], "residual_hedges": v.get("residual_hedges"), "findings": v["findings"],
        "draft_ms": draft_ms, "verify_ms": verify_ms, "citations": cite_figures(note, fp),
    }
    step("save")
    save_report(session, rec)
    rec["total_ms"] = int((time.time() - t0) * 1000)
    return rec


def load_reports(session):
    rows = _rows(session, f"""
        SELECT run_id, subject, peers, quarter_end::STRING AS quarter_end, injected_claim, fact_pack,
               report_md, status, claims_checked, edits_applied, residual_hedges, findings, model, draft_ms, verify_ms,
               TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI') AS created_at
        FROM {SCHEMA}.REPORTS ORDER BY created_at DESC""")
    out = []
    for r in rows:
        d = {k.lower(): v for k, v in r.as_dict().items()}
        for k in ("peers", "fact_pack", "findings"):
            d[k] = json.loads(d[k]) if isinstance(d[k], str) else (d[k] or [])
        d["citations"] = cite_figures(d["report_md"], d["fact_pack"])
        out.append(d)
    return out


# ---------------------------------------------------------------- agent
def ask_agent(session, question):
    body = json.dumps({"messages": [{"role": "user", "content": [{"type": "text", "text": question}]}]})
    t = time.time()
    raw = _rows(session, f"SELECT SNOWFLAKE.CORTEX.DATA_AGENT_RUN('{SCHEMA}.BANK_RESEARCH_AGENT', ?)", [body])[0][0]
    ms = int((time.time() - t) * 1000)
    resp = json.loads(raw)
    content = resp.get("content") or []
    last_tool = max([i for i, c in enumerate(content) if c.get("type") in ("tool_use", "tool_result")], default=-1)
    parts, sql, table = [], None, None
    for i, c in enumerate(content):
        if c.get("type") == "tool_result":
            for item in (c.get("tool_result") or {}).get("content") or []:
                j = item.get("json") or {}
                sql = j.get("sql") or sql
                rs = j.get("result_set")
                if rs and rs.get("data"):
                    cols = [m["name"] for m in rs["resultSetMetaData"]["rowType"]]
                    table = {"columns": cols, "rows": rs["data"][:20]}
        if i > last_tool and c.get("type") == "text":
            parts.append(c.get("text", ""))
    return {"question": question, "answer": "\n\n".join(p for p in parts if p).strip(),
            "sql": sql, "table": table, "ms": ms}
