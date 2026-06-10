"""
Uniware Access Resource Auditor  ·  v3 consolidated
=====================================================
Tab 1  — Access Pattern Dump   (1,180 URL patterns joined to resource names)
Tab 2  — Left Sidebar Mapping  (132 sidebar nav items)
Tab 3  — Tools                 (URL Checker · Role Builder · Compare · Gap Report)
"""

import re, glob
from difflib import SequenceMatcher
from email import policy
from email.parser import BytesParser
from pathlib import Path
from collections import Counter

import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Uniware Access Auditor",
    page_icon="🛡️",
    layout="wide",
)

def _find(patterns):
    for p in patterns:
        hits = glob.glob(p)
        if hits: return hits[0]
    return patterns[0]

TXT_FILE = _find(["access_patterns*.txt", "access_pattern*.txt"])
DOC_FILE = _find([
    "Access_resource_associated_with_uniware_layout_left_side_bar.doc",
    "Access+resource+associated+with+uniware+layout+left+side+bar.doc",
    "*sidebar*.doc", "*layout*.doc",
])

# ─────────────────────────────────────────────────────────────────────────────
# STYLES
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.block-container{padding-top:1.3rem;padding-bottom:2rem}
h1{font-size:1.6rem!important;font-weight:700;margin-bottom:0!important}

/* Tabs */
.stTabs [data-baseweb="tab-list"]{gap:0;border-bottom:2px solid #e0e4ea;background:transparent}
.stTabs [data-baseweb="tab"]{font-size:.95rem;font-weight:600;padding:.5rem 1.4rem;border-radius:0;
    color:#555;border-bottom:3px solid transparent;margin-bottom:-2px;background:transparent!important}
.stTabs [aria-selected="true"]{color:#1a73e8!important;border-bottom:3px solid #1a73e8!important;background:transparent!important}

/* Search */
.stTextInput>div>div>input{font-size:1rem;border-radius:8px;padding:.5rem .9rem;border:1.5px solid #c8d0dc}
.stTextInput>div>div>input:focus{border-color:#1a73e8;box-shadow:0 0 0 3px rgba(26,115,232,.12)}

/* Metrics */
[data-testid="metric-container"]{background:#f7f9fc;border:1px solid #e4e8ef;border-radius:10px;padding:10px 16px}
[data-testid="metric-container"] label{font-size:.75rem!important;color:#666!important}
[data-testid="metric-container"] [data-testid="stMetricValue"]{font-size:1.5rem!important;font-weight:700}

/* Cards */
.info-box{background:#f0f4ff;border-left:4px solid #1a73e8;border-radius:0 8px 8px 0;
    padding:10px 16px;font-size:.87rem;color:#2c3e50;margin-bottom:10px}
.group-card{background:#fff;border:1px solid #e4e8ef;border-radius:10px;
    padding:14px 18px;margin-bottom:10px}
.group-header{font-size:1rem;font-weight:700;color:#1a1a2e;margin-bottom:4px}
.group-sub{font-size:.8rem;color:#666;margin-bottom:8px}
.res-pill{display:inline-block;background:#e8eaf6;color:#283593;padding:2px 10px;
    border-radius:99px;font-size:.8rem;font-weight:600;font-family:monospace;margin:2px}
.badge-r{display:inline-block;background:#e8f5e9;color:#2e7d32;padding:2px 8px;
    border-radius:99px;font-size:.75rem;font-weight:700}
.badge-w{display:inline-block;background:#fff3e0;color:#e65100;padding:2px 8px;
    border-radius:99px;font-size:.75rem;font-weight:700}
.detail-label{font-size:.7rem;font-weight:700;text-transform:uppercase;
    letter-spacing:.07em;color:#888;margin-bottom:2px}
.detail-val{font-family:monospace;background:#f7f9fc;border:1px solid #e0e6f0;
    border-radius:6px;padding:6px 10px;font-size:.9rem;color:#1a1a2e;
    word-break:break-all;margin-bottom:10px}
.sec-lbl{font-size:.73rem;font-weight:700;text-transform:uppercase;
    letter-spacing:.07em;color:#888;margin-bottom:4px}
.ql-label{font-size:.78rem;color:#555;font-weight:600;margin-bottom:5px;margin-top:4px}
div[data-testid="stDataFrame"]{border-radius:10px;overflow:hidden;border:1px solid #e4e8ef}
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
IGNORE_SUGGESTIONS = {
    'data','admin','get','oms','api','wap','the','and','for','not','all',
    'its','was','but','can','had','how','our','out','who','did','let',
    'put','say','too','use','way','you','com','www','null','none',
}

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def split_camel(s: str) -> str:
    s = re.sub(r'([a-z])([A-Z])', r'\1 \2', s)
    return s.replace('-',' ').replace('_',' ').strip()

def prettify(s: str) -> str:
    return split_camel(s).title().strip()

def extract_activity(url: str) -> str:
    segs = [s for s in url.strip('/').split('/') if s and s != '*']
    if not segs: return 'Root'
    for i in range(len(segs)-1, -1, -1):
        sw = split_camel(segs[i]).lower()
        if sw in VERBS:
            verb = sw.title()
            for j in range(i+1, len(segs)):
                obj = split_camel(segs[j]).lower()
                if obj not in SKIP_SEGS and not obj.isdigit():
                    return f"{verb} {prettify(segs[j])}"
            for j in range(i-1, -1, -1):
                obj = split_camel(segs[j]).lower()
                if obj not in SKIP_SEGS and not obj.isdigit():
                    return f"{verb} {prettify(segs[j])}"
            return verb
        for verb in sorted(VERBS, key=len, reverse=True):
            if sw.startswith(verb) and len(sw) > len(verb):
                tail = split_camel(segs[i])[len(verb):].strip()
                if tail: return f"{verb.title()} {tail.title()}"
    for i in range(len(segs)-1, -1, -1):
        sw = split_camel(segs[i]).lower()
        if sw not in SKIP_SEGS: return prettify(segs[i])
    return prettify(segs[-1])

def access_type_label(url: str) -> str:
    return "WRITE" if any(w in url.lower() for w in WRITE_WORDS) else "READ"

def smart_suggest(query: str, pool: list[str], limit: int = 60) -> list[str]:
    """Score suggestions: prefix > word-start > contains. Also match access resource names."""
    q = query.strip().lower()
    if not q: return []
    scored: list[tuple[float, str]] = []
    tokens = q.split()
    for s in pool:
        sl = s.lower()
        score = 0.0
        if sl == q:               score = 100
        elif sl.startswith(q):    score = 85
        elif f" {q}" in f" {sl}": score = 75   # word-boundary
        elif q in sl:             score = 55
        else:
            hit = sum(1 for t in tokens if t in sl)
            if hit: score = 30 + hit * 10
        if score:
            score += SequenceMatcher(None, q, sl).ratio() * 5
            scored.append((score, s))
    scored.sort(key=lambda x: -x[0])
    return [s for _, s in scored[:limit]]

def score_row(q: str, activity: str, resource: str, url: str,
              tab: str = "", group: str = "") -> float:
    if not q: return 0.0
    q  = q.lower()
    a, r, u, t, g = (x.lower() for x in (activity, resource, url, tab, group))
    sc = 0.0
    if q == r:    sc += 100
    if q in r:    sc += 55
    if q in u:    sc += 50
    if q in a:    sc += 45
    if q in t:    sc += 35
    if q in g:    sc += 30
    for tok in q.split():
        if tok in r: sc += 9
        if tok in u: sc += 8
        if tok in a: sc += 8
        if tok in t: sc += 5
        if tok in g: sc += 5
    sc += SequenceMatcher(None, q, r).ratio() * 10
    sc += SequenceMatcher(None, q, u).ratio() * 8
    sc += SequenceMatcher(None, q, a).ratio() * 7
    return sc

@st.cache_data(show_spinner=False)
def build_suggestion_pool(df: pd.DataFrame, url_col: str, activity_col: str,
                           extra_cols: list[str] | None = None) -> list[str]:
    seen: set[str] = set()
    def add(w: str):
        w = w.strip().lower()
        if len(w) > 2 and w not in seen and w not in IGNORE_SUGGESTIONS:
            seen.add(w)
    for url in df[url_col].dropna():
        for s in url.strip('/').split('/'):
            if s and s != '*': add(split_camel(s).lower())
    for act in df[activity_col].dropna():
        add(act.lower())
    for col in (extra_cols or []):
        if col in df.columns:
            for v in df[col].dropna():
                add(str(v).lower())
    return sorted(seen)

@st.cache_data(show_spinner=False)
def pat_quick_terms(df: pd.DataFrame) -> list[str]:
    counts: Counter = Counter()
    for url in df["URL Pattern"]:
        for s in url.strip('/').split('/'):
            if s and s != '*':
                w = split_camel(s).lower()
                if w not in IGNORE_SUGGESTIONS and w not in SKIP_SEGS and len(w) > 3:
                    counts[w] += 1
    return [t for t, _ in counts.most_common(16)]

@st.cache_data(show_spinner=False)
def side_quick_terms(df: pd.DataFrame) -> list[str]:
    gc = df["Side Tab Group"].value_counts()
    return [g for g in gc.index.tolist() if g][:16]

# ─────────────────────────────────────────────────────────────────────────────
# PARSERS
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_pattern_data(fp: str) -> pd.DataFrame:
    path = Path(fp)
    if not path.exists(): return pd.DataFrame()
    raw   = path.read_text(encoding="utf-8", errors="ignore")
    lines = raw.splitlines()

    t2 = None
    for i, line in enumerate(lines):
        if "name" in line and "access_resource_group_id" in line and "level" in line:
            t2 = i; break
    if t2 is None: t2 = len(lines)

    url_rows = []
    for line in lines[:t2]:
        line = line.strip()
        if not line or line.startswith("+---") or "|" not in line: continue
        p = [x.strip() for x in line.strip("|").split("|")]
        if len(p) < 5 or p[0].lower() == "id": continue
        if not p[0].isdigit() or not p[1].isdigit(): continue
        url = p[2].strip()
        if not url.startswith("/"): continue
        url_rows.append({"pattern_id": int(p[0]), "access_resource_id": int(p[1]),
                         "url_pattern": url, "updated": p[4].strip() if len(p)>4 else ""})

    res_map: dict[int, dict] = {}
    for line in lines[t2:]:
        line = line.strip()
        if not line or line.startswith("+---") or "|" not in line: continue
        p = [x.strip() for x in line.strip("|").split("|")]
        if len(p) < 4 or p[0].lower() == "id": continue
        if not p[0].isdigit(): continue
        name = p[1].strip()
        if not name or not re.match(r'^[A-Z][A-Z0-9_]+$', name): continue
        rid = int(p[0])
        if rid not in res_map:
            res_map[rid] = {"name": name, "level": p[3].strip() if len(p)>3 else ""}

    rows = []
    for r in url_rows:
        rid = r["access_resource_id"]
        res = res_map.get(rid, {})
        url = r["url_pattern"]
        rows.append({
            "Resource ID":     rid,
            "Access Resource": res.get("name", f"ID_{rid}"),
            "Level":           res.get("level", ""),
            "Activity":        extract_activity(url),
            "Type":            access_type_label(url),
            "URL Pattern":     url,
            "Last Updated":    r["updated"],
        })
    return pd.DataFrame(rows)

@st.cache_data(show_spinner=False)
def load_sidebar_data(fp: str) -> pd.DataFrame:
    path = Path(fp)
    if not path.exists(): return pd.DataFrame()
    msg = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
    html = None
    for part in msg.iter_parts():
        if part.get_content_type() == "text/html":
            html = part.get_payload(decode=True).decode("utf-8", errors="ignore"); break
    if not html: return pd.DataFrame()
    soup  = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if table is None: return pd.DataFrame()
    rows = []
    for tr in table.find_all("tr")[1:]:
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td","th"])]
        if len(cells) < 4 or not cells[0] or not cells[2]: continue
        url = cells[2].strip()
        rows.append({"Tab Name": cells[0].strip(), "Side Tab Group": cells[1].strip(),
                     "Access Resource": cells[3].strip(), "Activity": extract_activity(url),
                     "Type": access_type_label(url), "URL Pattern": url})
    df = pd.DataFrame(rows)
    return df.drop_duplicates(subset=["URL Pattern"]).reset_index(drop=True)

# ─────────────────────────────────────────────────────────────────────────────
# LOAD
# ─────────────────────────────────────────────────────────────────────────────
with st.spinner("Loading data…"):
    pat_df  = load_pattern_data(TXT_FILE)
    side_df = load_sidebar_data(DOC_FILE)

errs = []
if pat_df.empty:  errs.append(f"❌ `{TXT_FILE}` not found or empty — place it next to `app.py`.")
if side_df.empty: errs.append(f"❌ `{DOC_FILE}` not found or empty — place it next to `app.py`.")
if errs:
    for e in errs: st.error(e)
    st.stop()

pat_pool   = build_suggestion_pool(pat_df,  "URL Pattern", "Activity", ["Access Resource"])
side_pool  = build_suggestion_pool(side_df, "URL Pattern", "Activity",
                                   ["Access Resource", "Tab Name", "Side Tab Group"])
pat_quick  = pat_quick_terms(pat_df)
side_quick = side_quick_terms(side_df)

# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("# 🛡️ Uniware Access Resource Auditor")
st.markdown(
    f'<p style="color:#666;font-size:.84rem;margin-top:2px;margin-bottom:.8rem">'
    f'Pattern Dump — <b>{len(pat_df):,} URL patterns</b> · '
    f'<b>{pat_df["Access Resource"].nunique()} resources</b>'
    f'&ensp;|&ensp;'
    f'Left Sidebar — <b>{len(side_df)} items</b> · '
    f'<b>{side_df["Access Resource"].nunique()} resources</b>'
    f'</p>',
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# SHARED FILTER + RENDER
# ─────────────────────────────────────────────────────────────────────────────
def apply_filters(df, query, type_filter, extra_col=None, extra_vals=None):
    out = df.copy()
    if query:
        q = query.strip().lower()
        mask = pd.Series(False, index=out.index)
        for col in ["Activity","Access Resource","URL Pattern","Tab Name","Side Tab Group","Level"]:
            if col in out.columns:
                mask |= out[col].fillna("").str.lower().str.contains(re.escape(q), na=False)
        out = out[mask].copy()
        if not out.empty:
            scores = [score_row(query,
                                str(r.get("Activity","")),
                                str(r.get("Access Resource","")),
                                str(r.get("URL Pattern","")),
                                str(r.get("Tab Name","")),
                                str(r.get("Side Tab Group","")))
                      for r in out.to_dict("records")]
            out["_score"] = scores
            out = out.sort_values("_score", ascending=False).drop(columns=["_score"])
    if type_filter:
        out = out[out["Type"].isin(type_filter)]
    if extra_col and extra_vals:
        out = out[out[extra_col].isin(extra_vals)]
    return out.reset_index(drop=True)


def render_grouped(result: pd.DataFrame, res_col_extra: list[str]):
    """
    Grouped-by-resource sections — NO expanders, everything visible immediately.
    Each resource is a labelled section with its table shown directly below it.
    """
    col_cfg = {
        "Activity":       st.column_config.TextColumn("Activity",       width=200),
        "Type":           st.column_config.TextColumn("Type",           width=80),
        "URL Pattern":    st.column_config.TextColumn("URL Pattern",    width=360),
        "Level":          st.column_config.TextColumn("Level",          width=80),
        "Last Updated":   st.column_config.TextColumn("Last Updated",   width=150),
        "Tab Name":       st.column_config.TextColumn("Tab Name",       width=180),
        "Side Tab Group": st.column_config.TextColumn("Group",          width=160),
    }
    groups = sorted(result.groupby("Access Resource"), key=lambda x: -len(x[1]))
    for res_name, gdf in groups:
        rc = int((gdf["Type"] == "READ").sum())
        wc = int((gdf["Type"] == "WRITE").sum())
        badge_r = f'<span class="badge-r">👁 {rc} READ</span>'
        badge_w = f'<span class="badge-w">✏️ {wc} WRITE</span>' if wc else ""
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:8px;margin-top:18px;margin-bottom:4px">'
            f'<span class="res-pill" style="font-size:.85rem;padding:3px 12px">{res_name}</span>'
            f'<span style="font-size:.8rem;color:#555">{len(gdf)} URL{"s" if len(gdf)>1 else ""}</span>'
            f'{badge_r}&nbsp;{badge_w}'
            f'<span style="margin-left:auto;font-size:.75rem;color:#999">copy ↓</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.code(res_name, language="text")
        show_cols = [c for c in res_col_extra if c in gdf.columns]
        st.dataframe(
            gdf[show_cols].reset_index(drop=True),
            use_container_width=True,
            hide_index=True,
            height=min(55 + len(gdf) * 35, 380),
            column_config=col_cfg,
        )
        st.divider()


def render_detail_panel(result: pd.DataFrame, sk: str):
    with st.expander("🔍 Inspect a single result in full detail", expanded=False):
        labels = [
            f"{r['Activity']}  ·  {r['Access Resource']}"
            + (f"  ·  {int(r['Resource ID'])}" if "Resource ID" in r and pd.notna(r.get("Resource ID")) else "")
            + f"  ·  {r['URL Pattern']}"
            for r in result.to_dict("records")
        ]
        pick = st.selectbox("Select result to inspect", ["— pick a result —"] + labels,
                            key=f"{sk}_focus",
                            help="Pick any result row to see all its fields laid out clearly.")
        if pick == "— pick a result —": return
        row = result.iloc[labels.index(pick)]

        def field(label, val):
            st.markdown(f'<p class="detail-label">{label}</p><div class="detail-val">{val}</div>',
                        unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            field("Access Resource", row.get("Access Resource","—"))
            if "Resource ID" in row and pd.notna(row.get("Resource ID")):
                field("Resource ID", int(row["Resource ID"]))
            if str(row.get("Level","")).strip():
                field("Level", row["Level"])
            atype = row.get("Type","")
            b = '<span class="badge-w">✏️ WRITE</span>' if atype=="WRITE" else '<span class="badge-r">👁️ READ</span>'
            st.markdown(f'<p class="detail-label">Access Type</p>{b}<br><br>', unsafe_allow_html=True)
            st.caption("Copy resource name 👇")
            st.code(str(row.get("Access Resource","")), language="text")
        with c2:
            field("Activity",    row.get("Activity","—"))
            field("URL Pattern", row.get("URL Pattern","—"))
            if str(row.get("Tab Name","")).strip():
                field("Sidebar Tab Name",  row["Tab Name"])
            if str(row.get("Side Tab Group","")).strip():
                field("Side Tab Group", row["Side Tab Group"])
            if str(row.get("Last Updated","")).strip():
                field("Last Updated",   row["Last Updated"])


def render_tab(
    df:           pd.DataFrame,
    pool:         list[str],
    quick_terms:  list[str],
    sk:           str,
    flat_cols:    list[str],
    group_cols:   list[str],
    extra_col:    str | None     = None,
    extra_label:  str            = "",
    extra_opts:   list[str]      = [],
    src_label:    str            = "",
    tab_desc:     str            = "",
):
    # ── Description ──────────────────────────────────────────────────────
    st.markdown(f'<div class="info-box">{tab_desc}</div>', unsafe_allow_html=True)

    # ── Quick search chips ────────────────────────────────────────────────
    st.markdown('<p class="ql-label">Quick search</p>', unsafe_allow_html=True)
    ql_cols = st.columns(8)
    for i, term in enumerate(quick_terms[:16]):
        if ql_cols[i % 8].button(term, key=f"ql_{sk}_{i}", use_container_width=True,
                                  help=f"Click to search for '{term}'"):
            st.session_state[f"{sk}_q"] = term
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Search bar + clear ────────────────────────────────────────────────
    sc1, sc2, sc3 = st.columns([5, 1, 1], gap="small")
    with sc1:
        st.markdown('<p class="sec-lbl">Search — by activity, URL segment, or access resource name</p>',
                    unsafe_allow_html=True)
        typed = st.text_input(
            "q", label_visibility="collapsed",
            placeholder="e.g.  gatepass  ·  MATERIAL_MANAGEMENT  ·  /data/oms/saleOrder",
            key=f"{sk}_q",
            help="Searches across: Activity name · Access resource name · URL path · Tab name (sidebar) · Group name (sidebar)"
        )
    with sc2:
        st.markdown('<p class="sec-lbl">Type</p>', unsafe_allow_html=True)
        type_filter = st.multiselect(
            "type", label_visibility="collapsed",
            options=["READ","WRITE"], default=["READ","WRITE"],
            key=f"{sk}_type",
            help="READ = view/search/get actions.  WRITE = create/edit/cancel/approve/allocate and similar."
        )
    with sc3:
        st.markdown('<p class="sec-lbl">&nbsp;</p>', unsafe_allow_html=True)
        if st.button("✕ Clear", key=f"{sk}_clear", use_container_width=True,
                     help="Clear the search field and show all results"):
            st.session_state[f"{sk}_q"] = ""
            st.rerun()

    # ── Extra filter (sidebar: Side Tab Group) ────────────────────────────
    chosen_extra: list[str] = []
    if extra_col:
        st.markdown(f'<p class="sec-lbl">{extra_label}</p>', unsafe_allow_html=True)
        chosen_extra = st.multiselect(
            extra_label, label_visibility="collapsed",
            options=extra_opts, default=[],
            placeholder=f"Filter by {extra_label} (optional)",
            key=f"{sk}_extra",
            help=f"Narrow results to items belonging to a specific {extra_label}."
        )

    # ── Smart suggestion dropdown ─────────────────────────────────────────
    effective_query = typed.strip()
    if typed.strip():
        suggestions = smart_suggest(typed.strip(), pool)
        if suggestions:
            st.markdown('<p class="sec-lbl">Suggestions — pick one to sharpen results, or keep typing</p>',
                        unsafe_allow_html=True)
            chosen = st.selectbox(
                "sg", label_visibility="collapsed",
                options=["— use my text as-is —"] + suggestions,
                key=f"{sk}_sg",
                help="Suggestions are ranked by relevance. Picking one focuses the results exactly on that term."
            )
            if chosen != "— use my text as-is —":
                effective_query = chosen

    st.divider()

    # ── Apply filters ─────────────────────────────────────────────────────
    result = apply_filters(df, effective_query, type_filter, extra_col, chosen_extra)

    # ── Metrics ───────────────────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Results",          f"{len(result):,}",
              help="Total URL patterns / sidebar items matching your search.")
    m2.metric("Unique Resources", result["Access Resource"].nunique(),
              help="How many distinct access resources cover these results.")
    m3.metric("READ",             int((result["Type"]=="READ").sum()),
              help="View / search / get actions.")
    m4.metric("WRITE",            int((result["Type"]=="WRITE").sum()),
              help="Create / edit / cancel / approve and similar change actions.")

    if result.empty:
        st.warning("No results. Try a different keyword or clear the type filter.")
        return

    # ── Resource pills summary ────────────────────────────────────────────
    if effective_query:
        pills = "".join(f'<span class="res-pill">{r}</span>'
                        for r in sorted(result["Access Resource"].unique()))
        st.markdown(
            f'<div class="info-box"><b>Access resources required for this search:</b><br><br>{pills}</div>',
            unsafe_allow_html=True,
        )

    # ── Smart view: auto-pick flat vs grouped ────────────────────────────
    # Flat is better when: query is a resource name, or only 1 resource, or few results.
    # Grouped is better when: query is a module/activity spanning multiple resources.
    n_resources     = result["Access Resource"].nunique()
    query_is_res    = bool(effective_query) and (
        effective_query.upper() in [r.upper() for r in result["Access Resource"].unique()]
    )
    auto_flat       = (n_resources <= 1) or query_is_res or (len(result) <= 8)
    auto_msg        = (
        "Flat table auto-selected — your search matched a single resource."
        if auto_flat else
        f"Grouped view auto-selected — results span {n_resources} resources."
    )
    st.caption(f"ℹ️ {auto_msg}  Change below if needed.")

    view = st.radio(
        "View",
        options=["Flat table", "Grouped by resource"],
        index=0 if auto_flat else 1,
        horizontal=True,
        key=f"{sk}_view",
        help=(
            "Flat table: all rows in one sortable table — best when you searched by resource name.  "
            "Grouped: rows under each resource header with copy buttons — best when searching by module or activity."
        ),
    )

    if "Grouped" in view:
        render_grouped(result, group_cols)
    else:
        show = [c for c in flat_cols if c in result.columns]
        st.dataframe(
            result[show],
            use_container_width=True,
            hide_index=True,
            height=min(80 + len(result)*35, 560),
            column_config={
                "Activity":       st.column_config.TextColumn("Activity",       width=200),
                "Access Resource":st.column_config.TextColumn("Access Resource",width=220),
                "Resource ID":    st.column_config.NumberColumn("Res. ID",      width=80),
                "Type":           st.column_config.TextColumn("Type",           width=80),
                "URL Pattern":    st.column_config.TextColumn("URL Pattern",    width=360),
                "Level":          st.column_config.TextColumn("Level",          width=80),
                "Last Updated":   st.column_config.TextColumn("Last Updated",   width=150),
                "Tab Name":       st.column_config.TextColumn("Tab Name",       width=180),
                "Side Tab Group": st.column_config.TextColumn("Group",          width=160),
            },
        )

    # ── Grouped summary + Detail + Download (always shown below) ─────────
    with st.expander("📊 Grouped summary — one row per resource", expanded=False):
        gdf = (result.groupby(["Access Resource","Type"], as_index=False)
               .agg(URL_Count=("URL Pattern","nunique"),
                    Activities=("Activity", lambda s: "  ·  ".join(sorted(set(s))[:6])))
               .sort_values("URL_Count", ascending=False).reset_index(drop=True))
        st.dataframe(
            gdf, use_container_width=True, hide_index=True,
            column_config={
                "Access Resource": st.column_config.TextColumn("Access Resource", width=240),
                "Type":            st.column_config.TextColumn("Type",            width=80),
                "URL_Count":       st.column_config.NumberColumn("URLs",          width=70),
                "Activities":      st.column_config.TextColumn("Sample Activities", width=420),
            },
        )
        st.download_button(
            "⬇️ Download grouped summary (CSV)",
            data=gdf.to_csv(index=False).encode("utf-8"),
            file_name=f"grouped_{src_label}.csv", mime="text/csv",
        )

    render_detail_panel(result, sk)

    st.download_button(
        f"⬇️ Download all {len(result):,} results as CSV",
        data=result.to_csv(index=False).encode("utf-8"),
        file_name=f"{'_'.join(effective_query.split()[:3]) if effective_query else 'all'}_{src_label}.csv",
        mime="text/csv",
    )


# ─────────────────────────────────────────────────────────────────────────────
# TOOLS
# ─────────────────────────────────────────────────────────────────────────────
def render_tools(pat_df: pd.DataFrame, side_df: pd.DataFrame):

    tool = st.radio(
        "Choose a tool",
        ["🔗 URL Checker", "🧩 Role Builder", "⚖️ Compare Resources", "🕳️ Gap Report"],
        horizontal=True,
        help="URL Checker — paste any URL and get its resource instantly.  Role Builder — pick activities and get the permission list.  Compare — side-by-side resource diff.  Gap Report — URLs with no sidebar mapping."
    )
    st.divider()

    # ── TOOL 1: URL Checker ───────────────────────────────────────────────
    if tool == "🔗 URL Checker":
        st.markdown("#### Paste a URL — get its access resource instantly")
        st.caption("Paste any backend URL from the browser address bar or from code.")
        url_in = st.text_input("URL", placeholder="/data/material/gatepass/create",
                               help="Paste the exact URL path. Wildcards (*) are handled automatically.")
        if url_in.strip():
            u = url_in.strip()
            # Exact match first
            exact = pat_df[pat_df["URL Pattern"] == u]
            # Wildcard / partial match
            if exact.empty:
                exact = pat_df[pat_df["URL Pattern"].apply(
                    lambda p: bool(re.fullmatch(p.replace("*",".*"), u))
                )]
            # Fuzzy fallback
            if exact.empty:
                scores = pat_df["URL Pattern"].apply(
                    lambda p: SequenceMatcher(None, u.lower(), p.lower()).ratio())
                top = scores.nlargest(5).index
                exact = pat_df.loc[top]
                st.info("No exact match found — showing closest results by similarity.")

            if exact.empty:
                st.warning("No match found for this URL.")
            else:
                row = exact.iloc[0]
                c1, c2, c3 = st.columns(3)
                c1.success(f"**Access Resource**\n\n`{row['Access Resource']}`")
                c2.info(   f"**Type**\n\n`{row['Type']}`")
                c3.info(   f"**Activity**\n\n`{row['Activity']}`")
                st.caption("Copy resource name 👇")
                st.code(str(row["Access Resource"]), language="text")
                if len(exact) > 1:
                    st.markdown("**All matching patterns:**")
                    st.dataframe(exact[["Activity","Access Resource","Type","URL Pattern"]],
                                 use_container_width=True, hide_index=True)
                # Check if it has a sidebar tab
                sb_match = side_df[side_df["URL Pattern"] == u]
                if not sb_match.empty:
                    sb = sb_match.iloc[0]
                    st.success(f"🗂️ This URL is also in the **Left Sidebar** — "
                               f"Tab: **{sb['Tab Name']}** · Group: **{sb['Side Tab Group']}**")
                else:
                    st.caption("ℹ️ This URL is not directly listed in the sidebar mapping doc.")

    # ── TOOL 2: Role Builder ──────────────────────────────────────────────
    elif tool == "🧩 Role Builder":
        st.markdown("#### Build a custom role — pick activities, get the permission list")
        st.caption("Tick every activity this role needs. The tool will calculate the exact set of access resources to enable.")

        rb_search = st.text_input("Filter activities", placeholder="gatepass, invoice…",
                                   help="Type to filter the activity list below.")
        pool_df = pat_df.copy()
        if rb_search.strip():
            q = rb_search.strip().lower()
            mask = (pool_df["Activity"].str.lower().str.contains(q, na=False) |
                    pool_df["URL Pattern"].str.lower().str.contains(q, na=False) |
                    pool_df["Access Resource"].str.lower().str.contains(q, na=False))
            pool_df = pool_df[mask]

        activity_options = sorted(pool_df["Activity"].unique().tolist())
        if not activity_options:
            st.warning("No activities match that filter.")
        else:
            chosen_acts = st.multiselect(
                "Select activities for this role",
                options=activity_options,
                help="You can select as many as needed. The required resources update instantly.",
            )
            if chosen_acts:
                role_rows = pool_df[pool_df["Activity"].isin(chosen_acts)]
                required  = sorted(role_rows["Access Resource"].unique())
                st.markdown(f"**{len(required)} access resource(s) required:**")
                pills = "".join(f'<span class="res-pill">{r}</span>' for r in required)
                st.markdown(f'<div class="info-box">{pills}</div>', unsafe_allow_html=True)
                st.caption("Copy as comma-separated list 👇")
                st.code(", ".join(required), language="text")
                with st.expander("Show full breakdown", expanded=False):
                    st.dataframe(
                        role_rows[["Activity","Access Resource","Type","URL Pattern"]],
                        use_container_width=True, hide_index=True,
                    )
                st.download_button(
                    "⬇️ Download role definition (CSV)",
                    data=role_rows.to_csv(index=False).encode("utf-8"),
                    file_name="custom_role.csv", mime="text/csv",
                )

    # ── TOOL 3: Compare Resources ─────────────────────────────────────────
    elif tool == "⚖️ Compare Resources":
        st.markdown("#### Compare two access resources side by side")
        st.caption("Useful when deciding which resource to assign, or checking overlap between two permissions.")
        all_res = sorted(pat_df["Access Resource"].unique())
        c1, c2 = st.columns(2)
        res_a = c1.selectbox("Resource A", ["— pick —"] + all_res, key="cmp_a",
                              help="Select the first resource to compare.")
        res_b = c2.selectbox("Resource B", ["— pick —"] + all_res, key="cmp_b",
                              help="Select the second resource to compare.")
        if res_a != "— pick —" and res_b != "— pick —" and res_a != res_b:
            df_a = pat_df[pat_df["Access Resource"]==res_a]
            df_b = pat_df[pat_df["Access Resource"]==res_b]
            urls_a = set(df_a["URL Pattern"])
            urls_b = set(df_b["URL Pattern"])
            shared = urls_a & urls_b
            only_a = urls_a - urls_b
            only_b = urls_b - urls_a

            s1, s2, s3 = st.columns(3)
            s1.metric(f"Only in {res_a}",  len(only_a))
            s2.metric("Shared URLs",       len(shared))
            s3.metric(f"Only in {res_b}",  len(only_b))

            tab_a, tab_sh, tab_b = st.tabs([
                f"Only {res_a} ({len(only_a)})",
                f"Shared ({len(shared)})",
                f"Only {res_b} ({len(only_b)})",
            ])
            def _show(tab, subset_urls, base_df):
                with tab:
                    rows = base_df[base_df["URL Pattern"].isin(subset_urls)]
                    if rows.empty: st.info("None.")
                    else: st.dataframe(rows[["Activity","Type","URL Pattern"]],
                                       use_container_width=True, hide_index=True)
            _show(tab_a,  only_a, df_a)
            _show(tab_sh, shared, pd.concat([df_a,df_b]).drop_duplicates(subset=["URL Pattern"]))
            _show(tab_b,  only_b, df_b)
        elif res_a != "— pick —" and res_b != "— pick —" and res_a == res_b:
            st.warning("Please select two different resources.")

    # ── TOOL 4: Gap Report ────────────────────────────────────────────────
    elif tool == "🕳️ Gap Report":
        st.markdown("#### URLs in the pattern dump that have no sidebar mapping")
        st.caption(
            "These are backend endpoints that exist in the system but are NOT listed "
            "in the sidebar UI doc. They may be API-only, internal, or simply undocumented."
        )
        sidebar_urls = set(side_df["URL Pattern"])
        gap_df = pat_df[~pat_df["URL Pattern"].isin(sidebar_urls)].copy()

        g1, g2, g3 = st.columns(3)
        g1.metric("URLs not in sidebar", f"{len(gap_df):,}")
        g2.metric("Unique resources",     gap_df["Access Resource"].nunique())
        g3.metric("WRITE actions",        int((gap_df["Type"]=="WRITE").sum()),
                  help="WRITE gaps are the most important to review — these are change actions with no sidebar entry.")

        gap_res_filter = st.multiselect(
            "Filter by resource", sorted(gap_df["Access Resource"].unique()),
            placeholder="All resources", key="gap_res",
            help="Narrow the gap report to a specific access resource.",
        )
        if gap_res_filter:
            gap_df = gap_df[gap_df["Access Resource"].isin(gap_res_filter)]

        st.dataframe(
            gap_df[["Activity","Access Resource","Type","URL Pattern","Last Updated"]],
            use_container_width=True, hide_index=True, height=500,
        )
        st.download_button(
            "⬇️ Download gap report (CSV)",
            data=gap_df.to_csv(index=False).encode("utf-8"),
            file_name="gap_report.csv", mime="text/csv",
        )


# ─────────────────────────────────────────────────────────────────────────────
# MAIN TABS
# ─────────────────────────────────────────────────────────────────────────────
tab_pat, tab_side, tab_tools = st.tabs([
    "📋  Access Pattern Dump",
    "🗂️  Left Sidebar Mapping",
    "🛠️  Tools",
])

with tab_pat:
    render_tab(
        df          = pat_df,
        pool        = pat_pool,
        quick_terms = pat_quick,
        sk          = "pat",
        flat_cols   = ["Activity","Access Resource","Resource ID","Level","Type","URL Pattern","Last Updated"],
        group_cols  = ["Activity","Type","URL Pattern","Level","Last Updated"],
        src_label   = "access_patterns",
        tab_desc    = (
            "<b>Source A — Access Pattern Dump.</b> "
            "1,180 backend URL patterns joined to their exact resource names from the database. "
            "Search by module name, action, URL segment, or access resource name. "
            "Results are grouped by access resource so you can see the full scope of each permission at a glance."
        ),
    )

with tab_side:
    render_tab(
        df          = side_df,
        pool        = side_pool,
        quick_terms = side_quick,
        sk          = "side",
        flat_cols   = ["Tab Name","Side Tab Group","Activity","Access Resource","Type","URL Pattern"],
        group_cols  = ["Tab Name","Side Tab Group","Activity","Type","URL Pattern"],
        extra_col   = "Side Tab Group",
        extra_label = "Side Tab Group",
        extra_opts  = sorted(g for g in side_df["Side Tab Group"].dropna().unique() if g),
        src_label   = "sidebar_mapping",
        tab_desc    = (
            "<b>Source B — Left Sidebar Mapping.</b> "
            "132 sidebar navigation items from the Confluence UI doc. "
            "Each row maps a sidebar tab to the access resource it requires. "
            "Use the Side Tab Group filter to narrow to a specific menu section."
        ),
    )

with tab_tools:
    render_tools(pat_df, side_df)

# ─────────────────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "🛡️ Uniware Access Resource Auditor  ·  "
    f"Source A: {TXT_FILE}  ·  Source B: {Path(DOC_FILE).name}"
)
