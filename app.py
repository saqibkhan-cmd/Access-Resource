"""
Uniware Access Resource Auditor  —  consolidated final build
=============================================================
Source A  ·  Access Pattern Dump   (1,180 URL patterns joined to resource names)
Source B  ·  Left Sidebar Mapping  (132 sidebar nav items from Confluence doc)

How the txt file is parsed
  Table 1  id | access_resource_id | url_pattern | created | updated
  Table 2  id | name (UPPER_SNAKE) | group_id    | level
  Joined on access_resource_id = Table2.id  →  every URL gets its resource name.
"""

import re
import glob
from difflib import SequenceMatcher
from email import policy
from email.parser import BytesParser
from pathlib import Path

import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Uniware Access Auditor",
    page_icon="🛡️",
    layout="wide",
)

# Auto-locate files (works regardless of exact filename variant)
def _find_file(patterns: list[str]) -> str:
    for pat in patterns:
        hits = glob.glob(pat, recursive=False)
        if hits:
            return hits[0]
    return patterns[0]          # return first pattern as fallback (will show error)

TXT_FILE = _find_file(["access_patterns*.txt", "access_pattern*.txt"])
DOC_FILE = _find_file([
    "Access_resource_associated_with_uniware_layout_left_side_bar.doc",
    "Access+resource+associated+with+uniware+layout+left+side+bar.doc",
    "*sidebar*.doc", "*layout*.doc",
])

# ─────────────────────────────────────────────────────────────────────────────
# STYLES
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.block-container { padding-top: 1.4rem; padding-bottom: 2rem; }
h1  { font-size: 1.6rem !important; font-weight: 700; margin-bottom: 0 !important; }
h3  { font-size: 1.05rem !important; font-weight: 600; margin-top: 1rem; }

.stTabs [data-baseweb="tab-list"] {
    gap: 0; border-bottom: 2px solid #e0e4ea; background: transparent;
}
.stTabs [data-baseweb="tab"] {
    font-size: 0.95rem; font-weight: 600; padding: 0.5rem 1.4rem;
    border-radius: 0; color: #555;
    border-bottom: 3px solid transparent; margin-bottom: -2px;
    background: transparent !important;
}
.stTabs [aria-selected="true"] {
    color: #1a73e8 !important;
    border-bottom: 3px solid #1a73e8 !important;
    background: transparent !important;
}

.stTextInput > div > div > input {
    font-size: 1rem; border-radius: 8px;
    padding: 0.5rem 0.9rem; border: 1.5px solid #c8d0dc;
}
.stTextInput > div > div > input:focus {
    border-color: #1a73e8;
    box-shadow: 0 0 0 3px rgba(26,115,232,0.12);
}

[data-testid="metric-container"] {
    background: #f7f9fc; border: 1px solid #e4e8ef;
    border-radius: 10px; padding: 10px 16px;
}
[data-testid="metric-container"] label            { font-size: 0.75rem !important; color: #666 !important; }
[data-testid="metric-container"] [data-testid="stMetricValue"] { font-size: 1.5rem !important; font-weight: 700; }

.stDataFrame { border-radius: 10px; overflow: hidden; border: 1px solid #e4e8ef; }

.info-box {
    background: #f0f4ff; border-left: 4px solid #1a73e8;
    border-radius: 0 8px 8px 0; padding: 10px 16px;
    font-size: 0.87rem; color: #2c3e50; margin-bottom: 10px;
}
.res-pill {
    display: inline-block; background: #e8eaf6; color: #283593;
    padding: 2px 10px; border-radius: 99px;
    font-size: 0.8rem; font-weight: 600; font-family: monospace; margin: 2px 2px;
}
.detail-card {
    background: #f7f9fc; border: 1px solid #dce3ef;
    border-radius: 10px; padding: 16px 20px; margin-top: 8px;
}
.detail-label {
    font-size: 0.72rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.07em; color: #888; margin-bottom: 3px;
}
.detail-value {
    font-size: 0.93rem; font-family: monospace;
    background: #fff; border: 1px solid #e0e6f0;
    border-radius: 6px; padding: 6px 10px;
    color: #1a1a2e; word-break: break-all;
}
.badge-read  { display:inline-block; background:#e8f5e9; color:#2e7d32; padding:2px 9px; border-radius:99px; font-size:0.78rem; font-weight:700; }
.badge-write { display:inline-block; background:#fff3e0; color:#e65100; padding:2px 9px; border-radius:99px; font-size:0.78rem; font-weight:700; }
.sec-label {
    font-size: 0.74rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.07em; color: #888; margin-bottom: 4px;
}
.quick-label { font-size: 0.78rem; color: #888; font-weight: 600; margin-bottom: 4px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
VERBS = {
    'create','add','edit','update','remove','delete','cancel','approve',
    'search','fetch','get','view','show','print','preview','export',
    'import','assign','allocate','open','close','complete','receive',
    'reject','hold','unhold','upload','download','discard','save',
    'submit','split','amend','confirm','dispatch','mark','merge','reset',
    'scan','lookup','find','list','generate','process',
}
SKIP_SEGS = {
    'data','admin','oms','catalog','reports','procure','shipping','returns',
    'tasks','putaway','inflow','material','system','layout','printing',
    'picklogic','picker','packer','channel','orders','meta','lookup',
    'configure','dashboard','staging','customers','grns','vendor',
    'batching','bill','materials','services','wap','api','myaccount','po',
}
WRITE_WORDS = {
    'create','add','edit','update','remove','delete','cancel','approve',
    'allocate','discard','assign','close','open','complete','receive',
    'reject','hold','unhold','upload','download','save','submit',
    'import','export','amend','confirm','dispatch','mark','merge',
    'reset','split','scan',
}
QUICK_TERMS = [
    "gatepass","invoice","picklist","shipping","catalog","channel",
    "returns","putaway","manifest","cyclecount","vendor","inflow",
    "procurement","sale order","grn","dispatch",
]

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def split_camel(s: str) -> str:
    s = re.sub(r'([a-z])([A-Z])', r'\1 \2', s)
    return s.replace('-', ' ').replace('_', ' ').strip()

def prettify(s: str) -> str:
    return split_camel(s).title().strip()

def extract_activity(url: str) -> str:
    segs = [s for s in url.strip('/').split('/') if s and s != '*']
    if not segs:
        return 'Root'
    for i in range(len(segs) - 1, -1, -1):
        sw = split_camel(segs[i]).lower()
        if sw in VERBS:
            verb = sw.title()
            for j in range(i + 1, len(segs)):
                obj = split_camel(segs[j]).lower()
                if obj not in SKIP_SEGS and not obj.isdigit():
                    return f"{verb} {prettify(segs[j])}"
            for j in range(i - 1, -1, -1):
                obj = split_camel(segs[j]).lower()
                if obj not in SKIP_SEGS and not obj.isdigit():
                    return f"{verb} {prettify(segs[j])}"
            return verb
        for verb in sorted(VERBS, key=len, reverse=True):
            if sw.startswith(verb) and len(sw) > len(verb):
                tail = split_camel(segs[i])[len(verb):].strip()
                if tail:
                    return f"{verb.title()} {tail.title()}"
    for i in range(len(segs) - 1, -1, -1):
        sw = split_camel(segs[i]).lower()
        if sw not in SKIP_SEGS:
            return prettify(segs[i])
    return prettify(segs[-1])

def access_type_label(url: str) -> str:
    u = url.lower()
    return "WRITE" if any(w in u for w in WRITE_WORDS) else "READ"

def score_row(query: str, activity: str, resource: str, url: str, tab: str = "", group: str = "") -> float:
    q = query.strip().lower()
    if not q:
        return 0.0
    a, r, u, t, g = (x.lower() for x in (activity, resource, url, tab, group))
    score = 0.0
    if q == r:           score += 100
    if q in r:           score += 50
    if q in u:           score += 55
    if q in a:           score += 45
    if q in t:           score += 35
    if q in g:           score += 30
    for token in q.split():
        if token in r:   score += 8
        if token in u:   score += 8
        if token in a:   score += 8
        if token in t:   score += 5
        if token in g:   score += 5
    score += SequenceMatcher(None, q, r).ratio() * 10
    score += SequenceMatcher(None, q, u).ratio() * 10
    score += SequenceMatcher(None, q, a).ratio() * 8
    return score

def build_suggestions(df: pd.DataFrame, url_col: str, activity_col: str,
                      extra_cols: list[str] | None = None) -> list[str]:
    seen: set[str] = set()
    IGNORE = {
        'data','admin','get','oms','api','wap','the','and','for','not',
        'all','its','are','was','but','can','had','her','him','his',
        'how','our','out','who','did','let','put','say','she','too',
        'use','way','you','com','www','null',
    }
    def add(w: str):
        w = w.strip().lower()
        if len(w) > 2 and w not in seen and w not in IGNORE:
            seen.add(w)

    for url in df[url_col].dropna():
        for s in url.strip('/').split('/'):
            if s and s != '*':
                add(split_camel(s).lower())
    for act in df[activity_col].dropna():
        add(act.lower())
    for col in (extra_cols or []):
        if col in df.columns:
            for v in df[col].dropna():
                add(str(v).lower())
    return sorted(seen)

# ─────────────────────────────────────────────────────────────────────────────
# PARSERS
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_pattern_data(filepath: str) -> pd.DataFrame:
    path = Path(filepath)
    if not path.exists():
        return pd.DataFrame()

    raw   = path.read_text(encoding="utf-8", errors="ignore")
    lines = raw.splitlines()

    # Locate Table 2 header (resource definitions)
    t2_start = None
    for i, line in enumerate(lines):
        if "name" in line and "access_resource_group_id" in line and "level" in line:
            t2_start = i
            break
    if t2_start is None:
        t2_start = len(lines)

    # ── Parse Table 1 : URL patterns ─────────────────────────────────────
    url_rows = []
    for line in lines[:t2_start]:
        line = line.strip()
        if not line or line.startswith("+---") or "|" not in line:
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) < 5 or parts[0].lower() == "id":
            continue
        if not parts[0].isdigit() or not parts[1].isdigit():
            continue
        url = parts[2].strip()
        if not url.startswith("/"):
            continue
        url_rows.append({
            "pattern_id":        int(parts[0]),
            "access_resource_id": int(parts[1]),
            "url_pattern":        url,
            "updated":            parts[4].strip() if len(parts) > 4 else "",
        })

    # ── Parse Table 2 : Resource definitions ─────────────────────────────
    res_map: dict[int, dict] = {}
    for line in lines[t2_start:]:
        line = line.strip()
        if not line or line.startswith("+---") or "|" not in line:
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) < 4 or parts[0].lower() == "id":
            continue
        if not parts[0].isdigit():
            continue
        name = parts[1].strip()
        if not name or not re.match(r'^[A-Z][A-Z0-9_]+$', name):
            continue
        rid = int(parts[0])
        if rid not in res_map:      # keep first occurrence per id
            res_map[rid] = {
                "name":  name,
                "level": parts[3].strip() if len(parts) > 3 else "",
            }

    # ── Join & enrich ─────────────────────────────────────────────────────
    rows = []
    for row in url_rows:
        rid = row["access_resource_id"]
        res = res_map.get(rid, {})
        url = row["url_pattern"]
        rows.append({
            "Resource ID":     rid,
            "Access Resource": res.get("name", f"ID_{rid}"),
            "Level":           res.get("level", ""),
            "Activity":        extract_activity(url),
            "Type":            access_type_label(url),
            "URL Pattern":     url,
            "Last Updated":    row["updated"],
        })

    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False)
def load_sidebar_data(filepath: str) -> pd.DataFrame:
    path = Path(filepath)
    if not path.exists():
        return pd.DataFrame()

    msg = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
    html_payload = None
    for part in msg.iter_parts():
        if part.get_content_type() == "text/html":
            html_payload = part.get_payload(decode=True).decode("utf-8", errors="ignore")
            break
    if not html_payload:
        return pd.DataFrame()

    soup  = BeautifulSoup(html_payload, "html.parser")
    table = soup.find("table")
    if table is None:
        return pd.DataFrame()

    rows = []
    for tr in table.find_all("tr")[1:]:
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        if len(cells) < 4 or not cells[0] or not cells[2]:
            continue
        url = cells[2].strip()
        rows.append({
            "Tab Name":        cells[0].strip(),
            "Side Tab Group":  cells[1].strip(),
            "Access Resource": cells[3].strip(),
            "Activity":        extract_activity(url),
            "Type":            access_type_label(url),
            "URL Pattern":     url,
        })

    df = pd.DataFrame(rows)
    return df.drop_duplicates(subset=["URL Pattern"]).reset_index(drop=True)

# ─────────────────────────────────────────────────────────────────────────────
# LOAD
# ─────────────────────────────────────────────────────────────────────────────
with st.spinner("Loading data…"):
    pat_df  = load_pattern_data(TXT_FILE)
    side_df = load_sidebar_data(DOC_FILE)

errors = []
if pat_df.empty:
    errors.append(f"❌ `{TXT_FILE}` — not found or empty. Place it next to `app.py`.")
if side_df.empty:
    errors.append(f"❌ `{DOC_FILE}` — not found or empty. Place it next to `app.py`.")
if errors:
    for e in errors:
        st.error(e)
    st.stop()

@st.cache_data(show_spinner=False)
def get_pat_suggestions(df: pd.DataFrame) -> list[str]:
    return build_suggestions(df, "URL Pattern", "Activity",
                             extra_cols=["Access Resource"])

@st.cache_data(show_spinner=False)
def get_side_suggestions(df: pd.DataFrame) -> list[str]:
    return build_suggestions(df, "URL Pattern", "Activity",
                             extra_cols=["Access Resource", "Tab Name", "Side Tab Group"])

pat_suggestions  = get_pat_suggestions(pat_df)
side_suggestions = get_side_suggestions(side_df)

# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("# 🛡️ Uniware Access Resource Auditor")
st.markdown(
    f'<p style="color:#666;font-size:0.85rem;margin-top:2px;margin-bottom:1rem;">'
    f'Pattern Dump: <b>{len(pat_df):,} URLs</b> · <b>{pat_df["Access Resource"].nunique()} resources</b>'
    f'&ensp;|&ensp;'
    f'Left Sidebar: <b>{len(side_df)} items</b> · <b>{side_df["Access Resource"].nunique()} resources</b>'
    f'</p>',
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# SEARCH  +  FILTER  +  RESULTS  (shared logic for both tabs)
# ─────────────────────────────────────────────────────────────────────────────
def apply_filters(df: pd.DataFrame, query: str,
                  type_filter: list[str],
                  extra_col: str | None, extra_vals: list[str]) -> pd.DataFrame:
    out = df.copy()

    if query:
        q = query.strip().lower()
        mask = pd.Series(False, index=out.index)
        for col in ["Activity", "Access Resource", "URL Pattern",
                    "Tab Name", "Side Tab Group", "Level"]:
            if col in out.columns:
                mask |= out[col].fillna("").str.lower().str.contains(re.escape(q), na=False)
        out = out[mask].copy()

        # Score and sort
        scores = []
        for row in out.itertuples(index=False):
            scores.append(score_row(
                query,
                getattr(row, "Activity", ""),
                getattr(row, "Access Resource", ""),
                getattr(row, "URL Pattern", ""),
                getattr(row, "Tab Name", ""),
                getattr(row, "Side Tab Group", ""),
            ))
        out["_score"] = scores
        out = out.sort_values("_score", ascending=False).drop(columns=["_score"])

    if type_filter:
        out = out[out["Type"].isin(type_filter)]

    if extra_col and extra_vals:
        out = out[out[extra_col].isin(extra_vals)]

    return out.reset_index(drop=True)


def grouped_summary(df: pd.DataFrame, res_col: str = "Access Resource") -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    agg = (
        df.groupby([res_col, "Type"], as_index=False)
        .agg(
            URLs       = ("URL Pattern", "nunique"),
            Activities = ("Activity",    lambda s: " · ".join(sorted(set(s))[:8])),
        )
        .sort_values("URLs", ascending=False)
        .reset_index(drop=True)
    )
    return agg


def render_tab(
    df:              pd.DataFrame,
    suggestions:     list[str],
    sk:              str,               # session-state key prefix
    result_cols:     list[str],
    extra_col:       str | None = None,
    extra_label:     str        = "",
    extra_options:   list[str]  | None = None,
    source_label:    str        = "",
):
    # ── Quick search chips ────────────────────────────────────────────────
    st.markdown('<p class="quick-label">Quick search</p>', unsafe_allow_html=True)
    qcols = st.columns(8)
    for i, term in enumerate(QUICK_TERMS):
        if qcols[i % 8].button(term, key=f"quick_{sk}_{term}", use_container_width=True):
            st.session_state[f"{sk}_typed"] = term

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Search + type filter row ──────────────────────────────────────────
    c_search, c_type = st.columns([4, 1], gap="medium")
    with c_search:
        st.markdown('<p class="sec-label">Search</p>', unsafe_allow_html=True)
        typed = st.text_input(
            "s", label_visibility="collapsed",
            placeholder="Type anything — gatepass, invoice, /data/oms/…, MATERIAL_MANAGEMENT",
            key=f"{sk}_typed",
        )
    with c_type:
        st.markdown('<p class="sec-label">Access type</p>', unsafe_allow_html=True)
        type_filter = st.multiselect(
            "t", label_visibility="collapsed",
            options=["READ", "WRITE"], default=["READ", "WRITE"],
            key=f"{sk}_type",
        )

    # ── Optional extra filter (Side Tab Group for sidebar tab) ───────────
    chosen_extra: list[str] = []
    if extra_col:
        st.markdown(f'<p class="sec-label">{extra_label}</p>', unsafe_allow_html=True)
        chosen_extra = st.multiselect(
            extra_label, label_visibility="collapsed",
            options=extra_options or [], default=[],
            placeholder=f"All {extra_label}s",
            key=f"{sk}_extra",
        )

    # ── Suggestion dropdown ───────────────────────────────────────────────
    chosen_suggestion = None
    if typed.strip():
        q_low   = typed.strip().lower()
        matched = [s for s in suggestions if q_low in s][:80]
        if matched:
            st.markdown('<p class="sec-label">Suggestions — pick one to narrow results</p>',
                        unsafe_allow_html=True)
            chosen_suggestion = st.selectbox(
                "sg", label_visibility="collapsed",
                options=["— show all matches —"] + matched,
                key=f"{sk}_suggest",
            )
            if chosen_suggestion == "— show all matches —":
                chosen_suggestion = None
        else:
            st.caption("No keyword suggestions matched — showing all results for your text.")

    st.divider()

    effective_query = chosen_suggestion if chosen_suggestion else typed.strip()
    result = apply_filters(df, effective_query, type_filter, extra_col, chosen_extra)

    # ── Metrics ───────────────────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Results",          f"{len(result):,}")
    m2.metric("Unique Resources", result["Access Resource"].nunique())
    m3.metric("READ",             int((result["Type"] == "READ").sum()))
    m4.metric("WRITE",            int((result["Type"] == "WRITE").sum()))

    if result.empty:
        st.warning("No results. Try a different keyword or clear the filters.")
        return

    # ── Resource pills ────────────────────────────────────────────────────
    if effective_query:
        unique_res  = sorted(result["Access Resource"].unique())
        pills_html  = "".join(f'<span class="res-pill">{r}</span>' for r in unique_res)
        st.markdown(
            f'<div class="info-box"><b>Access resources required:</b><br>{pills_html}</div>',
            unsafe_allow_html=True,
        )

    # ── Results table ─────────────────────────────────────────────────────
    display_df = result[[c for c in result_cols if c in result.columns]].copy()
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=min(80 + len(display_df) * 35, 560),
        column_config={
            "Activity":        st.column_config.TextColumn("Activity",        width=200),
            "Access Resource": st.column_config.TextColumn("Access Resource", width=220),
            "Resource ID":     st.column_config.NumberColumn("Res. ID",       width=80),
            "Type":            st.column_config.TextColumn("Type",            width=85),
            "URL Pattern":     st.column_config.TextColumn("URL Pattern",     width=360),
            "Level":           st.column_config.TextColumn("Level",           width=80),
            "Last Updated":    st.column_config.TextColumn("Last Updated",    width=160),
            "Tab Name":        st.column_config.TextColumn("Tab Name",        width=180),
            "Side Tab Group":  st.column_config.TextColumn("Group",           width=160),
        },
    )

    # ── Focus on one result ───────────────────────────────────────────────
    with st.expander("🔍 Focus on one result — full detail", expanded=False):
        labels = result.apply(
            lambda r: (
                f"{r['Activity']}  ·  {r['Access Resource']}"
                + (f"  ·  {int(r['Resource ID'])}" if "Resource ID" in r and pd.notna(r.get("Resource ID")) else "")
                + f"  ·  {r['URL Pattern']}"
            ),
            axis=1,
        ).tolist()
        chosen_row = st.selectbox(
            "Select a row to inspect",
            options=["— pick a result —"] + labels,
            key=f"{sk}_focus",
        )
        if chosen_row != "— pick a result —":
            idx = labels.index(chosen_row)
            row = result.iloc[idx]

            left, right = st.columns(2)
            def field(col, label, val):
                col.markdown(f'<p class="detail-label">{label}</p>', unsafe_allow_html=True)
                col.markdown(f'<div class="detail-value">{val}</div>', unsafe_allow_html=True)
                col.markdown("<br>", unsafe_allow_html=True)

            with left:
                field(left, "Access Resource", row.get("Access Resource", "—"))
                if "Resource ID" in row and pd.notna(row.get("Resource ID")):
                    field(left, "Resource ID", int(row["Resource ID"]))
                if "Level" in row and str(row.get("Level","")).strip():
                    field(left, "Level", row["Level"])
                atype = row.get("Type","")
                badge_html = (
                    '<span class="badge-write">✏️ WRITE</span>'
                    if atype == "WRITE"
                    else '<span class="badge-read">👁️ READ</span>'
                )
                left.markdown(f'<p class="detail-label">Access Type</p>{badge_html}',
                              unsafe_allow_html=True)

            with right:
                field(right, "Activity",    row.get("Activity",    "—"))
                field(right, "URL Pattern", row.get("URL Pattern", "—"))
                if "Tab Name" in row and str(row.get("Tab Name","")).strip():
                    field(right, "Tab Name", row["Tab Name"])
                if "Side Tab Group" in row and str(row.get("Side Tab Group","")).strip():
                    field(right, "Side Tab Group", row["Side Tab Group"])
                if "Last Updated" in row and str(row.get("Last Updated","")).strip():
                    field(right, "Last Updated", row["Last Updated"])

    # ── Grouped summary ───────────────────────────────────────────────────
    with st.expander("📊 Grouped summary — one row per resource", expanded=False):
        gdf = grouped_summary(result)
        if not gdf.empty:
            st.dataframe(
                gdf,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Access Resource": st.column_config.TextColumn("Access Resource", width=240),
                    "Type":            st.column_config.TextColumn("Type",            width=80),
                    "URLs":            st.column_config.NumberColumn("URL Count",     width=90),
                    "Activities":      st.column_config.TextColumn("Activities (sample)", width=400),
                },
            )
            csv_g = gdf.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Download grouped summary (CSV)",
                data=csv_g,
                file_name=f"grouped_{source_label}.csv",
                mime="text/csv",
            )

    # ── Download full results ─────────────────────────────────────────────
    csv_full = result.to_csv(index=False).encode("utf-8")
    q_slug   = "_".join(effective_query.split()[:3]) if effective_query else "all"
    st.download_button(
        f"⬇️ Download all {len(result):,} results (CSV)",
        data=csv_full,
        file_name=f"{q_slug}_{source_label}.csv",
        mime="text/csv",
    )


# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────
tab_pat, tab_side = st.tabs([
    "📋  Access Pattern Dump",
    "🗂️  Left Sidebar Mapping",
])

with tab_pat:
    st.markdown(
        '<div class="info-box">'
        '<b>Source A — Access Pattern Dump.</b>  '
        '1,180 backend URL patterns joined to their exact resource names from the database. '
        'Type any keyword (module, action, URL segment, resource name) and pick a suggestion '
        'to see every matching URL and the access resource it requires.'
        '</div>',
        unsafe_allow_html=True,
    )
    render_tab(
        df           = pat_df,
        suggestions  = pat_suggestions,
        sk           = "pat",
        result_cols  = ["Activity", "Access Resource", "Resource ID", "Level",
                        "Type", "URL Pattern", "Last Updated"],
        source_label = "access_patterns",
    )

with tab_side:
    st.markdown(
        '<div class="info-box">'
        '<b>Source B — Left Sidebar Mapping.</b>  '
        '132 sidebar navigation items from the Confluence UI doc. '
        'Each row maps a sidebar tab to its access resource. '
        'Filter by Side Tab Group to see all items under a menu section.'
        '</div>',
        unsafe_allow_html=True,
    )
    render_tab(
        df             = side_df,
        suggestions    = side_suggestions,
        sk             = "side",
        result_cols    = ["Tab Name", "Side Tab Group", "Activity",
                          "Access Resource", "Type", "URL Pattern"],
        extra_col      = "Side Tab Group",
        extra_label    = "Side Tab Group",
        extra_options  = sorted(g for g in side_df["Side Tab Group"].dropna().unique() if g),
        source_label   = "sidebar_mapping",
    )

# ─────────────────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "🛡️ Uniware Access Resource Auditor  ·  "
    f"Source A: {TXT_FILE}  ·  Source B: {Path(DOC_FILE).name}"
)
