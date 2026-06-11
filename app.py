"""
Uniware Access Resource Auditor  ·  v5
=====================================================
Tabs: Search All · Pattern Dump · Sidebar Mapping · Tools
Features: Search history · Did you mean · Bookmarks · Who else · Permission Audit
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
st.set_page_config(page_title="Uniware Access Auditor", page_icon="🛡️", layout="wide")

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
# SESSION STATE INITIALISATION  (must happen before any widget)
# ─────────────────────────────────────────────────────────────────────────────
for _k, _v in {
    "bookmarks":     set(),
    "hist_pat":      [],
    "hist_side":     [],
    "hist_all":      [],
}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ─────────────────────────────────────────────────────────────────────────────
# STYLES
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.block-container{padding-top:1.2rem;padding-bottom:2rem}
h1{font-size:1.5rem!important;font-weight:700;margin-bottom:0!important}
.stTabs [data-baseweb="tab-list"]{gap:0;border-bottom:2px solid #e0e4ea;background:transparent}
.stTabs [data-baseweb="tab"]{font-size:.91rem;font-weight:600;padding:.42rem 1.2rem;
  border-radius:0;color:#666;border-bottom:3px solid transparent;
  margin-bottom:-2px;background:transparent!important}
.stTabs [aria-selected="true"]{color:#1a73e8!important;
  border-bottom:3px solid #1a73e8!important;background:transparent!important}
.stTextInput>div>div>input{font-size:.95rem;border-radius:8px;
  padding:.45rem .85rem;border:1.5px solid #c8d0dc}
.stTextInput>div>div>input:focus{border-color:#1a73e8;
  box-shadow:0 0 0 3px rgba(26,115,232,.1)}
[data-testid="metric-container"]{background:#f7f9fc;border:1px solid #e4e8ef;
  border-radius:10px;padding:10px 16px}
[data-testid="metric-container"] label{font-size:.73rem!important;color:#777!important}
[data-testid="metric-container"] [data-testid="stMetricValue"]{font-size:1.4rem!important;font-weight:700}
.info-strip{background:#f0f4ff;border-left:4px solid #1a73e8;border-radius:0 6px 6px 0;
  padding:8px 14px;font-size:.83rem;color:#2c3e50;margin-bottom:8px}
.warn-strip{background:#fff8e1;border-left:4px solid #f9a825;border-radius:0 6px 6px 0;
  padding:8px 14px;font-size:.83rem;color:#5d4037;margin-bottom:8px}
.res-pill{display:inline-block;background:#e8eaf6;color:#283593;padding:2px 10px;
  border-radius:99px;font-size:.79rem;font-weight:600;font-family:monospace;margin:2px}
.badge-r{display:inline-block;background:#e8f5e9;color:#2e7d32;padding:2px 8px;
  border-radius:99px;font-size:.73rem;font-weight:700}
.badge-w{display:inline-block;background:#fff3e0;color:#e65100;padding:2px 8px;
  border-radius:99px;font-size:.73rem;font-weight:700}
.sec-lbl{font-size:.71rem;font-weight:700;text-transform:uppercase;
  letter-spacing:.07em;color:#888;margin-bottom:3px}
.grp-hdr{font-size:.88rem;font-weight:700;color:#1a1a2e;
  background:#f4f6fa;border-radius:8px;padding:7px 13px;
  margin-top:12px;margin-bottom:3px;border:1px solid #e4e8ef;display:flex;align-items:center;gap:8px}
.hist-chip{display:inline-block;background:#f0f4ff;color:#1a73e8;padding:2px 10px;
  border-radius:99px;font-size:.77rem;cursor:pointer;margin:2px;border:1px solid #c5d8ff}
.bm-bar{background:#fffde7;border:1px solid #ffe082;border-radius:8px;
  padding:8px 14px;margin-bottom:10px}
.url-card{background:#fff;border:1.5px solid #1a73e8;border-radius:12px;
  padding:16px 20px;margin-bottom:8px}
.url-field-lbl{font-size:.69rem;font-weight:700;text-transform:uppercase;
  letter-spacing:.06em;color:#888;margin-bottom:2px}
.url-field-val{font-family:monospace;font-size:.9rem;color:#1a1a2e;
  background:#f7f9fc;border:1px solid #e0e6f0;border-radius:6px;
  padding:6px 10px;word-break:break-all;margin-bottom:10px}
.match-exact{background:#e8f5e9;border:1.5px solid #43a047;border-radius:8px;
  padding:3px 12px;font-size:.78rem;font-weight:700;color:#2e7d32;display:inline-block;margin-bottom:8px}
.match-fuzzy{background:#fff8e1;border:1.5px solid #f9a825;border-radius:8px;
  padding:3px 12px;font-size:.78rem;font-weight:700;color:#f57f17;display:inline-block;margin-bottom:8px}
.src-pat{color:#1a73e8;font-weight:700;font-size:.82rem}
.src-side{color:#7b1fa2;font-weight:700;font-size:.82rem}
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
    'import','export','amend','confirm','dispatch','mark','merge','reset','split','scan',
}
IGNORE_POOL = {
    'data','admin','get','oms','api','wap','the','and','for','not','all',
    'its','was','but','can','had','how','our','out','who','did','let',
    'put','say','too','use','way','you','com','www','null','none','meta',
}
LEVEL_MAP = {"FACILITY":"Facility","TENANT":"Tenant","BOTH":"Tenant (Both)","":"—"}

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def split_camel(s):
    return re.sub(r'([a-z])([A-Z])',r'\1 \2',s).replace('-',' ').replace('_',' ').strip()

def prettify(s): return split_camel(s).title().strip()

def extract_activity(url):
    segs=[s for s in url.strip('/').split('/') if s and s!='*']
    if not segs: return 'Root'
    for i in range(len(segs)-1,-1,-1):
        sw=split_camel(segs[i]).lower()
        if sw in VERBS:
            verb=sw.title()
            for j in range(i+1,len(segs)):
                obj=split_camel(segs[j]).lower()
                if obj not in SKIP_SEGS and not obj.isdigit(): return f"{verb} {prettify(segs[j])}"
            for j in range(i-1,-1,-1):
                obj=split_camel(segs[j]).lower()
                if obj not in SKIP_SEGS and not obj.isdigit(): return f"{verb} {prettify(segs[j])}"
            return verb
        for verb in sorted(VERBS,key=len,reverse=True):
            if sw.startswith(verb) and len(sw)>len(verb):
                tail=split_camel(segs[i])[len(verb):].strip()
                if tail: return f"{verb.title()} {tail.title()}"
    for i in range(len(segs)-1,-1,-1):
        sw=split_camel(segs[i]).lower()
        if sw not in SKIP_SEGS: return prettify(segs[i])
    return prettify(segs[-1])

def access_type_label(url):
    return "WRITE" if any(w in url.lower() for w in WRITE_WORDS) else "READ"

def fmt_level(raw):
    return LEVEL_MAP.get(raw.upper().strip(), raw)

def smart_suggest(query, pool, limit=60):
    q=query.strip().lower()
    if not q: return []
    tokens=q.split()
    scored=[]
    for s in pool:
        sl=s.lower(); score=0.0
        if sl==q:                 score=100
        elif sl.startswith(q):    score=85
        elif f" {q}" in f" {sl}": score=75
        elif q in sl:             score=55
        else:
            hit=sum(1 for t in tokens if t in sl)
            if hit: score=30+hit*10
        if score:
            score+=SequenceMatcher(None,q,sl).ratio()*5
            scored.append((score,s))
    scored.sort(key=lambda x:-x[0])
    return [s for _,s in scored[:limit]]

def score_row(q, activity, resource, url, tab="", group=""):
    if not q: return 0.0
    q=q.lower(); a,r,u,t,g=(x.lower() for x in (activity,resource,url,tab,group))
    sc=0.0
    if q==r: sc+=100
    if q in r: sc+=55
    if q in u: sc+=50
    if q in a: sc+=45
    if q in t: sc+=35
    if q in g: sc+=30
    for tok in q.split():
        if tok in r: sc+=9
        if tok in u: sc+=8
        if tok in a: sc+=8
        if tok in t: sc+=5
        if tok in g: sc+=5
    sc+=SequenceMatcher(None,q,r).ratio()*10
    sc+=SequenceMatcher(None,q,u).ratio()*8
    sc+=SequenceMatcher(None,q,a).ratio()*7
    return sc

@st.cache_data(show_spinner=False)
def build_pool(df, url_col, act_col, extra=None):
    seen=set()
    def add(w):
        w=w.strip().lower()
        if len(w)>2 and w not in seen and w not in IGNORE_POOL: seen.add(w)
    for url in df[url_col].dropna():
        for s in url.strip('/').split('/'):
            if s and s!='*': add(split_camel(s).lower())
    for act in df[act_col].dropna(): add(act.lower())
    for col in (extra or []):
        if col in df.columns:
            for v in df[col].dropna(): add(str(v).lower())
    return sorted(seen)

@st.cache_data(show_spinner=False)
def calc_pat_quick(df):
    counts=Counter()
    for url in df["URL Pattern"]:
        for s in url.strip('/').split('/'):
            if s and s!='*':
                w=split_camel(s).lower()
                if w not in IGNORE_POOL and w not in SKIP_SEGS and len(w)>3: counts[w]+=1
    return [t for t,_ in counts.most_common(16)]

@st.cache_data(show_spinner=False)
def calc_side_quick(df):
    return [g for g in df["Side Tab Group"].value_counts().index.tolist() if g][:16]

# ─────────────────────────────────────────────────────────────────────────────
# PARSERS
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_patterns(fp):
    path=Path(fp)
    if not path.exists(): return pd.DataFrame()
    raw=path.read_text(encoding="utf-8",errors="ignore"); lines=raw.splitlines()
    t2=next((i for i,l in enumerate(lines)
              if "name" in l and "access_resource_group_id" in l and "level" in l),len(lines))
    url_rows=[]
    for line in lines[:t2]:
        line=line.strip()
        if not line or line.startswith("+---") or "|" not in line: continue
        p=[x.strip() for x in line.strip("|").split("|")]
        if len(p)<5 or p[0].lower()=="id": continue
        if not p[0].isdigit() or not p[1].isdigit(): continue
        url=p[2].strip()
        if not url.startswith("/"): continue
        url_rows.append({"pattern_id":int(p[0]),"access_resource_id":int(p[1]),
                         "url_pattern":url,"updated":p[4].strip() if len(p)>4 else ""})
    res_map={}
    for line in lines[t2:]:
        line=line.strip()
        if not line or line.startswith("+---") or "|" not in line: continue
        p=[x.strip() for x in line.strip("|").split("|")]
        if len(p)<4 or p[0].lower()=="id" or not p[0].isdigit(): continue
        name=p[1].strip()
        if not name or not re.match(r'^[A-Z][A-Z0-9_]+$',name): continue
        rid=int(p[0])
        if rid not in res_map:
            res_map[rid]={"name":name,"level":fmt_level(p[3].strip() if len(p)>3 else "")}
    rows=[]
    for r in url_rows:
        rid=r["access_resource_id"]; res=res_map.get(rid,{}); url=r["url_pattern"]
        rows.append({"Resource ID":rid,"Access Resource":res.get("name",f"ID_{rid}"),
                     "Scope":res.get("level","—"),"Activity":extract_activity(url),
                     "Type":access_type_label(url),"URL Pattern":url,"Last Updated":r["updated"]})
    return pd.DataFrame(rows)

@st.cache_data(show_spinner=False)
def load_sidebar(fp):
    path=Path(fp)
    if not path.exists(): return pd.DataFrame()
    msg=BytesParser(policy=policy.default).parsebytes(path.read_bytes())
    html=None
    for part in msg.iter_parts():
        if part.get_content_type()=="text/html":
            html=part.get_payload(decode=True).decode("utf-8",errors="ignore"); break
    if not html: return pd.DataFrame()
    soup=BeautifulSoup(html,"html.parser"); table=soup.find("table")
    if table is None: return pd.DataFrame()
    rows=[]
    for tr in table.find_all("tr")[1:]:
        cells=[c.get_text(" ",strip=True) for c in tr.find_all(["td","th"])]
        if len(cells)<4 or not cells[0] or not cells[2]: continue
        url=cells[2].strip()
        rows.append({"Tab Name":cells[0].strip(),"Side Tab Group":cells[1].strip(),
                     "Access Resource":cells[3].strip(),"Activity":extract_activity(url),
                     "Type":access_type_label(url),"URL Pattern":url})
    df=pd.DataFrame(rows)
    return df.drop_duplicates(subset=["URL Pattern"]).reset_index(drop=True)

# ─────────────────────────────────────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────────────────────────────────────
with st.spinner("Loading data…"):
    pat_df  = load_patterns(TXT_FILE)
    side_df = load_sidebar(DOC_FILE)

for label,df in [("Access Pattern file",pat_df),("Sidebar mapping file",side_df)]:
    if df.empty:
        st.error(f"❌ {label} not found — place it next to app.py"); st.stop()

pat_pool   = build_pool(pat_df,  "URL Pattern","Activity",["Access Resource"])
side_pool  = build_pool(side_df, "URL Pattern","Activity",["Access Resource","Tab Name","Side Tab Group"])
all_pool   = sorted(set(pat_pool) | set(side_pool))
pat_quick  = calc_pat_quick(pat_df)
side_quick = calc_side_quick(side_df)

@st.cache_data(show_spinner=False)
def build_sidebar_lookup(df):
    return {r["URL Pattern"]:r for r in df.to_dict("records")}
sidebar_lookup = build_sidebar_lookup(side_df)

# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("# 🛡️ Uniware Access Resource Auditor")
st.markdown(
    f'<p style="color:#777;font-size:.81rem;margin-top:2px;margin-bottom:.5rem">'
    f'Pattern Dump — <b>{len(pat_df):,} URL patterns</b> · <b>{pat_df["Access Resource"].nunique()} resources</b>'
    f'&ensp;|&ensp;'
    f'Left Sidebar — <b>{len(side_df)} items</b> · <b>{side_df["Access Resource"].nunique()} resources</b>'
    f'</p>',
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# COLUMN CONFIG
# ─────────────────────────────────────────────────────────────────────────────
COL_CFG = {
    "Activity":        st.column_config.TextColumn("Activity",        width=210),
    "Access Resource": st.column_config.TextColumn("Access Resource", width=230),
    "Resource ID":     st.column_config.NumberColumn("Res. ID",       width=75),
    "Scope":           st.column_config.TextColumn("Scope",           width=110,
                           help="Facility=per facility.  Tenant=whole tenant.  Tenant (Both)=both levels."),
    "Type":            st.column_config.TextColumn("Type",            width=80,
                           help="READ=view/search/get.  WRITE=create/edit/delete/approve/cancel."),
    "URL Pattern":     st.column_config.TextColumn("URL Pattern",     width=360),
    "Last Updated":    st.column_config.TextColumn("Updated",         width=145),
    "Tab Name":        st.column_config.TextColumn("Sidebar Tab",     width=190),
    "Side Tab Group":  st.column_config.TextColumn("Group",           width=165),
    "Source":          st.column_config.TextColumn("Source",          width=130),
}

# ─────────────────────────────────────────────────────────────────────────────
# FILTER
# ─────────────────────────────────────────────────────────────────────────────
def apply_filters(df, query, type_filter, extra_col=None, extra_vals=None):
    out=df.copy()
    if query:
        q=query.strip().lower()
        mask=pd.Series(False,index=out.index)
        for col in ["Activity","Access Resource","URL Pattern","Tab Name","Side Tab Group","Scope"]:
            if col in out.columns:
                mask|=out[col].fillna("").str.lower().str.contains(re.escape(q),na=False)
        out=out[mask].copy()
        if not out.empty:
            sc=[score_row(query,str(r.get("Activity","")),str(r.get("Access Resource","")),
                          str(r.get("URL Pattern","")),str(r.get("Tab Name","")),
                          str(r.get("Side Tab Group",""))) for r in out.to_dict("records")]
            out["_sc"]=sc
            out=out.sort_values("_sc",ascending=False).drop(columns=["_sc"])
    if type_filter: out=out[out["Type"].isin(type_filter)]
    if extra_col and extra_vals: out=out[out[extra_col].isin(extra_vals)]
    return out.reset_index(drop=True)

# ─────────────────────────────────────────────────────────────────────────────
# SEARCH HISTORY HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def add_to_history(sk, query):
    key = f"hist_{sk}"
    hist = st.session_state.get(key, [])
    if query and query not in hist:
        hist.insert(0, query)
        st.session_state[key] = hist[:10]

def render_history(sk):
    hist = st.session_state.get(f"hist_{sk}", [])
    if not hist: return
    st.markdown('<p class="sec-lbl">Recent searches</p>', unsafe_allow_html=True)
    cols = st.columns(min(len(hist), 10))
    for i, term in enumerate(hist):
        if cols[i].button(term, key=f"hist_btn_{sk}_{i}",
                          help=f"Re-run search: {term}"):
            st.session_state[f"{sk}_pending_q"] = term
            st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# BOOKMARK HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def toggle_bookmark(res_name):
    bm = st.session_state.bookmarks
    if res_name in bm: bm.discard(res_name)
    else:              bm.add(res_name)

def render_bookmark_bar(sk, df):
    bm = st.session_state.bookmarks
    if not bm: return
    st.markdown(
        f'<div class="bm-bar"><span style="font-size:.78rem;font-weight:700;color:#f57f17">⭐ Bookmarked Resources</span></div>',
        unsafe_allow_html=True,
    )
    cols = st.columns(min(len(bm), 8))
    for i, res in enumerate(sorted(bm)):
        with cols[i % 8]:
            if st.button(res, key=f"bm_go_{sk}_{res}", use_container_width=True,
                         help=f"Search for {res}"):
                st.session_state[f"{sk}_pending_q"] = res
                st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# WHO ELSE USES THIS RESOURCE
# ─────────────────────────────────────────────────────────────────────────────
def render_who_else(res_name, current_urls, pat_df, side_df):
    with st.expander(f"👥 Who else uses  {res_name}?", expanded=False):
        st.caption(
            f"All activities across the entire dataset that share the **{res_name}** resource — "
            f"not just those matching the current search."
        )
        full_pat  = pat_df[pat_df["Access Resource"] == res_name]
        full_side = side_df[side_df["Access Resource"] == res_name]

        c1, c2, c3 = st.columns(3)
        c1.metric("Total URL patterns", len(full_pat))
        c2.metric("Sidebar tabs",        len(full_side))
        c3.metric("Type breakdown",
                  f'{int((full_pat["Type"]=="READ").sum())} R / {int((full_pat["Type"]=="WRITE").sum())} W')

        if not full_pat.empty:
            st.markdown("**All URL patterns for this resource:**")
            st.dataframe(
                full_pat[["Activity","Type","Scope","URL Pattern"]].reset_index(drop=True),
                use_container_width=True, hide_index=True,
                height=min(55+len(full_pat)*35, 340), column_config=COL_CFG,
            )
        if not full_side.empty:
            st.markdown("**Sidebar tabs that require this resource:**")
            st.dataframe(
                full_side[["Tab Name","Side Tab Group","Activity","Type"]].reset_index(drop=True),
                use_container_width=True, hide_index=True, column_config=COL_CFG,
            )

# ─────────────────────────────────────────────────────────────────────────────
# GROUPED VIEW  (no expanders — all visible)
# ─────────────────────────────────────────────────────────────────────────────
def render_grouped(result, show_cols, sk, pat_df, side_df):
    groups = sorted(result.groupby("Access Resource"), key=lambda x: -len(x[1]))
    bm = st.session_state.bookmarks
    for res_name, gdf in groups:
        rc = int((gdf["Type"]=="READ").sum())
        wc = int((gdf["Type"]=="WRITE").sum())
        badges = (f'<span class="badge-r">👁 {rc} READ</span>'
                  + (f'&nbsp;<span class="badge-w">✏️ {wc} WRITE</span>' if wc else ""))
        hdr_col, bm_col = st.columns([11, 1])
        with hdr_col:
            st.markdown(
                f'<div class="grp-hdr">'
                f'<span class="res-pill">{res_name}</span>'
                f'<span style="font-size:.78rem;color:#666">{len(gdf)} URL{"s" if len(gdf)>1 else ""}</span>'
                f'&ensp;{badges}</div>',
                unsafe_allow_html=True,
            )
        with bm_col:
            is_bm = res_name in bm
            if st.button("★" if is_bm else "☆", key=f"bm_{sk}_{res_name}",
                         help="Remove bookmark" if is_bm else "Bookmark this resource"):
                toggle_bookmark(res_name)
                st.rerun()
        st.code(res_name, language="text")
        cols = [c for c in show_cols if c in gdf.columns]
        st.dataframe(gdf[cols].reset_index(drop=True), use_container_width=True,
                     hide_index=True, height=min(55+len(gdf)*35,380), column_config=COL_CFG)
        render_who_else(res_name, set(gdf["URL Pattern"]), pat_df, side_df)

# ─────────────────────────────────────────────────────────────────────────────
# DETAIL PANEL
# ─────────────────────────────────────────────────────────────────────────────
def render_detail(result, sk):
    with st.expander("🔍 Inspect one result in full detail", expanded=False):
        labels=[
            f"{r['Activity']}  ·  {r['Access Resource']}"
            +(f"  ·  {int(r['Resource ID'])}" if "Resource ID" in r and pd.notna(r.get("Resource ID")) else "")
            +f"  ·  {r['URL Pattern']}"
            for r in result.to_dict("records")
        ]
        pick=st.selectbox("Select a result",["— pick —"]+labels,key=f"{sk}_det",
                          help="Pick any row to see all its fields clearly laid out.")
        if pick=="— pick —": return
        row=result.iloc[labels.index(pick)]
        def field(lbl,val):
            st.markdown(f'<p class="url-field-lbl">{lbl}</p><div class="url-field-val">{val}</div>',
                        unsafe_allow_html=True)
        c1,c2=st.columns(2)
        with c1:
            field("Access Resource",row.get("Access Resource","—"))
            if "Resource ID" in row and pd.notna(row.get("Resource ID")):
                field("Resource ID",int(row["Resource ID"]))
            if str(row.get("Scope","")).strip() not in ("","—"):
                field("Scope",row["Scope"])
            atype=row.get("Type","")
            b='<span class="badge-w">✏️ WRITE</span>' if atype=="WRITE" else '<span class="badge-r">👁️ READ</span>'
            st.markdown(f'<p class="url-field-lbl">Access Type</p>{b}<br><br>',unsafe_allow_html=True)
            st.caption("Copy resource name ↓")
            st.code(str(row.get("Access Resource","")),language="text")
        with c2:
            field("Activity",row.get("Activity","—"))
            field("URL Pattern",row.get("URL Pattern","—"))
            if str(row.get("Tab Name","")).strip(): field("Sidebar Tab",row["Tab Name"])
            if str(row.get("Side Tab Group","")).strip(): field("Side Tab Group",row["Side Tab Group"])
            if str(row.get("Last Updated","")).strip(): field("Last Updated",row["Last Updated"])

# ─────────────────────────────────────────────────────────────────────────────
# DID YOU MEAN
# ─────────────────────────────────────────────────────────────────────────────
def render_did_you_mean(query, pool, sk):
    suggestions = smart_suggest(query, pool, limit=5)
    if not suggestions:
        st.warning(f"No results found for **{query}**. Try a different keyword.")
        return
    st.markdown(
        f'<div class="warn-strip">No results for <b>{query}</b>. Did you mean one of these?</div>',
        unsafe_allow_html=True,
    )
    cols = st.columns(min(len(suggestions), 5))
    for i, s in enumerate(suggestions):
        if cols[i].button(s, key=f"dym_{sk}_{i}",
                          help=f"Search for '{s}' instead"):
            st.session_state[f"{sk}_pending_q"] = s
            st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# MAIN TAB RENDERER  (Pattern Dump tab + Sidebar tab)
# ─────────────────────────────────────────────────────────────────────────────
def render_tab(df, pool, quick_terms, sk, flat_cols, group_cols,
               extra_col=None, extra_label="", extra_opts=None, src_label="",
               pat_df_ref=None, side_df_ref=None):

    # ── Process pending state BEFORE any widget renders ───────────────────
    if st.session_state.pop(f"{sk}_do_clear", False):
        st.session_state[f"{sk}_q"] = ""
    pending = st.session_state.pop(f"{sk}_pending_q", None)
    if pending is not None:
        st.session_state[f"{sk}_q"] = pending

    # ── Bookmarks bar ─────────────────────────────────────────────────────
    render_bookmark_bar(sk, df)

    # ── Quick search chips ────────────────────────────────────────────────
    st.markdown('<p class="sec-lbl">Quick search</p>', unsafe_allow_html=True)
    ql = st.columns(8)
    for i, term in enumerate(quick_terms[:16]):
        if ql[i%8].button(term, key=f"ql_{sk}_{i}", use_container_width=True,
                          help=f"Search for '{term}'"):
            st.session_state[f"{sk}_pending_q"] = term
            st.rerun()

    # ── Recent searches ───────────────────────────────────────────────────
    render_history(sk)
    st.markdown("<br>", unsafe_allow_html=True)

    # ── Search bar ────────────────────────────────────────────────────────
    sc1, sc2, sc3 = st.columns([5,1.2,0.9], gap="small")
    with sc1:
        st.markdown('<p class="sec-lbl">Search — activity · URL · access resource name</p>',
                    unsafe_allow_html=True)
        typed = st.text_input("q", label_visibility="collapsed",
                              placeholder="e.g.  gatepass  ·  MATERIAL_MANAGEMENT  ·  /data/oms",
                              key=f"{sk}_q",
                              help="Searches across: Activity · Access resource name · URL path · Tab name · Group")
    with sc2:
        st.markdown('<p class="sec-lbl">Access type</p>', unsafe_allow_html=True)
        type_filter = st.multiselect("t", label_visibility="collapsed",
                                     options=["READ","WRITE"], default=["READ","WRITE"],
                                     key=f"{sk}_type",
                                     help="READ=view/search/get.  WRITE=create/edit/cancel/approve.")
    with sc3:
        st.markdown('<p class="sec-lbl">&nbsp;</p>', unsafe_allow_html=True)
        if st.button("✕ Clear", key=f"{sk}_clr", use_container_width=True,
                     help="Clear search and show all results"):
            st.session_state[f"{sk}_do_clear"] = True
            st.rerun()

    # ── Extra filter ──────────────────────────────────────────────────────
    chosen_extra: list[str] = []
    if extra_col:
        st.markdown(f'<p class="sec-lbl">Filter by {extra_label}</p>', unsafe_allow_html=True)
        chosen_extra = st.multiselect(extra_label, label_visibility="collapsed",
                                      options=extra_opts or [], default=[],
                                      placeholder=f"All {extra_label}s (optional)",
                                      key=f"{sk}_extra",
                                      help=f"Narrow results to a specific {extra_label}.")

    # ── Suggestions ───────────────────────────────────────────────────────
    effective_query = typed.strip()
    if typed.strip():
        sugg = smart_suggest(typed.strip(), pool)
        if sugg:
            st.markdown('<p class="sec-lbl">Suggestions</p>', unsafe_allow_html=True)
            chosen = st.selectbox("sg", label_visibility="collapsed",
                                  options=["— use my text as-is —"]+sugg,
                                  key=f"{sk}_sg",
                                  help="Ranked by relevance. Pick one to filter exactly on that term.")
            if chosen != "— use my text as-is —":
                effective_query = chosen

    st.divider()

    # ── Filter ────────────────────────────────────────────────────────────
    result = apply_filters(df, effective_query, type_filter, extra_col, chosen_extra)

    # ── Save to history ───────────────────────────────────────────────────
    if effective_query and not result.empty:
        add_to_history(sk, effective_query)

    # ── Metrics ───────────────────────────────────────────────────────────
    m1,m2,m3,m4 = st.columns(4)
    m1.metric("Results",           f"{len(result):,}", help="Total rows matching your filters.")
    m2.metric("Unique Resources",  result["Access Resource"].nunique(),
              help="Distinct access resources in these results.")
    m3.metric("READ",              int((result["Type"]=="READ").sum()),
              help="View / search / get actions.")
    m4.metric("WRITE",             int((result["Type"]=="WRITE").sum()),
              help="Create / edit / cancel / approve and similar change actions.")

    if result.empty:
        render_did_you_mean(effective_query or "your search", pool, sk)
        return

    # ── Resource pills ────────────────────────────────────────────────────
    if effective_query:
        pills="".join(f'<span class="res-pill">{r}</span>'
                      for r in sorted(result["Access Resource"].unique()))
        st.markdown(f'<div class="info-strip"><b>Access resources matched:</b><br><br>{pills}</div>',
                    unsafe_allow_html=True)

    # ── View selector ─────────────────────────────────────────────────────
    n_res = result["Access Resource"].nunique()
    is_res_q = bool(effective_query) and effective_query.upper() in \
               [r.upper() for r in result["Access Resource"].unique()]
    auto_flat = n_res <= 1 or is_res_q or len(result) <= 8

    view = st.radio("View as", ["Flat table","Grouped by resource"],
                    index=0 if auto_flat else 1, horizontal=True, key=f"{sk}_view",
                    help="Flat table: all rows together, sortable by any column.  "
                         "Grouped: rows under each resource — best when results span many resources.")

    if "Grouped" in view:
        render_grouped(result, group_cols, sk,
                       pat_df_ref if pat_df_ref is not None else pat_df,
                       side_df_ref if side_df_ref is not None else side_df)
    else:
        st.dataframe(result[[c for c in flat_cols if c in result.columns]],
                     use_container_width=True, hide_index=True,
                     height=min(80+len(result)*35,580), column_config=COL_CFG)

    # ── Detail + Summary + Download ───────────────────────────────────────
    render_detail(result, sk)

    with st.expander("📊 Summary — one row per resource", expanded=False):
        gdf = (result.groupby(["Access Resource","Type"],as_index=False)
               .agg(URLs=("URL Pattern","nunique"),
                    Sample_Activities=("Activity",lambda s:"  ·  ".join(sorted(set(s))[:5])))
               .sort_values("URLs",ascending=False).reset_index(drop=True))
        st.dataframe(gdf, use_container_width=True, hide_index=True,
                     column_config={"Access Resource":st.column_config.TextColumn(width=240),
                                    "Type":st.column_config.TextColumn(width=80),
                                    "URLs":st.column_config.NumberColumn("URL Count",width=90),
                                    "Sample_Activities":st.column_config.TextColumn("Sample Activities",width=400)})
        st.download_button("⬇️ Download summary (CSV)", gdf.to_csv(index=False).encode("utf-8"),
                           f"summary_{src_label}.csv","text/csv")

    st.download_button(
        f"⬇️ Download all {len(result):,} results (CSV)",
        data=result.to_csv(index=False).encode("utf-8"),
        file_name=f"{'_'.join(effective_query.split()[:3]) if effective_query else 'all'}_{src_label}.csv",
        mime="text/csv",
    )

# ─────────────────────────────────────────────────────────────────────────────
# SEARCH ALL TAB
# ─────────────────────────────────────────────────────────────────────────────
def render_search_all():
    # ── Process pending state ─────────────────────────────────────────────
    if st.session_state.pop("all_do_clear", False):
        st.session_state["all_q"] = ""
    pending = st.session_state.pop("all_pending_q", None)
    if pending is not None:
        st.session_state["all_q"] = pending

    render_bookmark_bar("all", pat_df)

    st.markdown(
        '<div class="info-strip">'
        'Search across <b>both sources at once</b> — results are shown separately so they stay distinct and easy to read.'
        '</div>', unsafe_allow_html=True,
    )

    render_history("all")
    st.markdown("<br>", unsafe_allow_html=True)

    sa1, sa2, sa3 = st.columns([5,1.2,0.9], gap="small")
    with sa1:
        st.markdown('<p class="sec-lbl">Search across Pattern Dump + Sidebar Mapping</p>',
                    unsafe_allow_html=True)
        typed = st.text_input("q", label_visibility="collapsed",
                              placeholder="e.g.  gatepass  ·  MATERIAL_MANAGEMENT  ·  invoice",
                              key="all_q",
                              help="Searches Activity · Access resource name · URL path · Tab name · Group — across both sources.")
    with sa2:
        st.markdown('<p class="sec-lbl">Access type</p>', unsafe_allow_html=True)
        type_filter = st.multiselect("t", label_visibility="collapsed",
                                     options=["READ","WRITE"], default=["READ","WRITE"],
                                     key="all_type",
                                     help="READ=view/search/get.  WRITE=create/edit/cancel/approve.")
    with sa3:
        st.markdown('<p class="sec-lbl">&nbsp;</p>', unsafe_allow_html=True)
        if st.button("✕ Clear", key="all_clr", use_container_width=True,
                     help="Clear search"):
            st.session_state["all_do_clear"] = True
            st.rerun()

    effective_query = typed.strip()
    if typed.strip():
        sugg = smart_suggest(typed.strip(), all_pool)
        if sugg:
            st.markdown('<p class="sec-lbl">Suggestions</p>', unsafe_allow_html=True)
            chosen = st.selectbox("sg", label_visibility="collapsed",
                                  options=["— use my text as-is —"]+sugg, key="all_sg",
                                  help="Ranked by relevance.")
            if chosen != "— use my text as-is —":
                effective_query = chosen

    st.divider()

    pat_res  = apply_filters(pat_df,  effective_query, type_filter)
    side_res = apply_filters(side_df, effective_query, type_filter)

    if effective_query and (not pat_res.empty or not side_res.empty):
        add_to_history("all", effective_query)

    # ── Combined metrics ──────────────────────────────────────────────────
    m1,m2,m3,m4 = st.columns(4)
    all_res = sorted(set(pat_res["Access Resource"].unique()) |
                     set(side_res["Access Resource"].unique()))
    m1.metric("Pattern results",   f"{len(pat_res):,}")
    m2.metric("Sidebar results",   f"{len(side_res):,}")
    m3.metric("Unique resources",  len(all_res))
    m4.metric("Total matched",     f"{len(pat_res)+len(side_res):,}")

    if pat_res.empty and side_res.empty:
        render_did_you_mean(effective_query or "your search", all_pool, "all")
        return

    # ── Resource pills ────────────────────────────────────────────────────
    if effective_query and all_res:
        pills="".join(f'<span class="res-pill">{r}</span>' for r in all_res)
        st.markdown(f'<div class="info-strip"><b>Access resources matched:</b><br><br>{pills}</div>',
                    unsafe_allow_html=True)

    # ── Pattern Dump results ──────────────────────────────────────────────
    st.markdown(
        f'<p class="src-pat">📋 Pattern Dump — {len(pat_res):,} result{"s" if len(pat_res)!=1 else ""}</p>',
        unsafe_allow_html=True,
    )
    if pat_res.empty:
        st.caption("No pattern dump results for this search.")
    else:
        pat_show = ["Activity","Access Resource","Resource ID","Scope","Type","URL Pattern"]
        st.dataframe(pat_res[[c for c in pat_show if c in pat_res.columns]],
                     use_container_width=True, hide_index=True,
                     height=min(80+len(pat_res)*35,440), column_config=COL_CFG)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Sidebar results ───────────────────────────────────────────────────
    st.markdown(
        f'<p class="src-side">🗂️ Sidebar Mapping — {len(side_res):,} result{"s" if len(side_res)!=1 else ""}</p>',
        unsafe_allow_html=True,
    )
    if side_res.empty:
        st.caption("No sidebar mapping results for this search.")
    else:
        side_show = ["Tab Name","Side Tab Group","Activity","Access Resource","Type","URL Pattern"]
        st.dataframe(side_res[[c for c in side_show if c in side_res.columns]],
                     use_container_width=True, hide_index=True,
                     height=min(80+len(side_res)*35,380), column_config=COL_CFG)

    # ── Combined export ───────────────────────────────────────────────────
    if not pat_res.empty or not side_res.empty:
        combined = pd.concat([
            pat_res.assign(Source="Pattern Dump"),
            side_res.assign(Source="Sidebar Mapping"),
        ], ignore_index=True)
        st.download_button(
            f"⬇️ Download combined results (CSV)",
            data=combined.to_csv(index=False).encode("utf-8"),
            file_name=f"search_all_{effective_query.replace(' ','_') if effective_query else 'results'}.csv",
            mime="text/csv",
        )

# ─────────────────────────────────────────────────────────────────────────────
# TOOLS — URL CHECKER
# ─────────────────────────────────────────────────────────────────────────────
def url_match_score(pattern, url):
    pat_re="^"+re.escape(pattern).replace(r"\*","[^/]+")+("$" if not pattern.endswith("*") else "")
    try:
        if re.match(pat_re, url): return 1.0
    except Exception: pass
    return SequenceMatcher(None, url.lower(), pattern.lower()).ratio()

def lookup_url(url, pat_df, sidebar_lookup):
    url=url.strip()
    exact=pat_df[pat_df["URL Pattern"]==url]
    if not exact.empty:
        row=exact.iloc[0]
        return {"match_type":"exact","rows":exact,
                "resource":row["Access Resource"],"type":row["Type"],
                "activity":row["Activity"],"scope":row.get("Scope","—"),
                "resource_id":row.get("Resource ID"),"sidebar":sidebar_lookup.get(url)}
    scores=pat_df["URL Pattern"].apply(lambda p: url_match_score(p,url))
    best=scores.max()
    if best>=0.95:
        best_rows=pat_df[scores>=0.95]; row=best_rows.iloc[0]
        return {"match_type":"wildcard","rows":best_rows,
                "resource":row["Access Resource"],"type":row["Type"],
                "activity":row["Activity"],"scope":row.get("Scope","—"),
                "resource_id":row.get("Resource ID"),"sidebar":sidebar_lookup.get(url)}
    top=pat_df.loc[scores.nlargest(5).index].copy()
    top["_score"]=scores[top.index]; top=top.sort_values("_score",ascending=False)
    row=top.iloc[0]
    return {"match_type":"fuzzy","rows":top,
            "resource":row["Access Resource"],"type":row["Type"],
            "activity":row["Activity"],"scope":row.get("Scope","—"),
            "resource_id":row.get("Resource ID"),"sidebar":sidebar_lookup.get(url),
            "best_score":top["_score"].iloc[0]}

def render_url_result(info, url):
    badge_map={"exact":'<span class="match-exact">✅ Exact match</span>',
               "wildcard":'<span class="match-exact">✅ Wildcard match</span>',
               "fuzzy":'<span class="match-fuzzy">⚠️ Closest match</span>'}
    st.markdown(badge_map[info["match_type"]], unsafe_allow_html=True)
    c1,c2,c3=st.columns(3)
    atype=info["type"]
    badge='<span class="badge-w">✏️ WRITE</span>' if atype=="WRITE" else '<span class="badge-r">👁️ READ</span>'
    with c1:
        st.markdown(f'<div class="url-card"><p class="url-field-lbl">Access Resource</p>'
                    f'<div class="url-field-val">{info["resource"]}</div>'
                    f'<p class="url-field-lbl">Access Type</p>{badge}</div>',
                    unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="url-card"><p class="url-field-lbl">Activity</p>'
                    f'<div class="url-field-val">{info["activity"]}</div>'
                    f'<p class="url-field-lbl">Scope</p>'
                    f'<div class="url-field-val">{info["scope"]}</div></div>',
                    unsafe_allow_html=True)
    with c3:
        sb=info.get("sidebar")
        if sb:
            st.markdown(f'<div class="url-card" style="border-color:#43a047">'
                        f'<p class="url-field-lbl">🗂️ Sidebar Tab</p>'
                        f'<div class="url-field-val">{sb["Tab Name"]}</div>'
                        f'<p class="url-field-lbl">Side Tab Group</p>'
                        f'<div class="url-field-val">{sb["Side Tab Group"]}</div></div>',
                        unsafe_allow_html=True)
        else:
            rid=info.get("resource_id")
            st.markdown(f'<div class="url-card" style="border-color:#e0e4ea">'
                        f'<p class="url-field-lbl">Resource ID</p>'
                        f'<div class="url-field-val">{int(rid) if rid and pd.notna(rid) else "—"}</div>'
                        f'<p class="url-field-lbl" style="color:#aaa">Sidebar</p>'
                        f'<div style="color:#aaa;font-size:.81rem;margin-top:2px">Not in sidebar mapping</div>'
                        f'</div>', unsafe_allow_html=True)
    st.caption("Copy resource name ↓"); st.code(info["resource"], language="text")
    if info["match_type"]=="fuzzy":
        st.warning(f"No exact match found. Best similarity: {info['best_score']:.0%}. Showing closest patterns below.")
    if len(info["rows"])>1 or info["match_type"]=="fuzzy":
        with st.expander(f"All {len(info['rows'])} matching patterns",
                         expanded=(info["match_type"]=="fuzzy")):
            show=[c for c in ["Access Resource","Type","Activity","Scope","URL Pattern"] if c in info["rows"].columns]
            st.dataframe(info["rows"][show].reset_index(drop=True),
                         use_container_width=True, hide_index=True, column_config=COL_CFG)

def render_url_checker(pat_df, sidebar_lookup):
    st.markdown("#### 🔗 URL Checker — paste a URL, get its access resource instantly")
    st.caption("Supports exact match, wildcard patterns, and fuzzy similarity for single or bulk URLs.")
    mode=st.radio("Mode",["Single URL","Bulk (multiple URLs)"],horizontal=True,
                  help="Single: paste one URL → full detail card.  Bulk: paste many → results table.")
    if mode=="Single URL":
        url_in=st.text_input("URL",placeholder="/data/material/gatepass/create",key="uc_single",
                             help="Paste the backend URL path. Include the leading slash.")
        if url_in.strip():
            render_url_result(lookup_url(url_in.strip(),pat_df,sidebar_lookup), url_in.strip())
    else:
        urls_text=st.text_area("Paste URLs (one per line)",
                               placeholder="/data/material/gatepass/create\n/data/oms/saleOrder/cancel",
                               height=150,key="uc_bulk",
                               help="One URL per line. Paste from code, logs, or a spreadsheet.")
        if st.button("Look up all URLs",key="uc_go"):
            urls=[u.strip() for u in urls_text.strip().splitlines() if u.strip()]
            if not urls:
                st.warning("No URLs detected.")
            else:
                results=[]; prog=st.progress(0,text="Looking up URLs…")
                for i,url in enumerate(urls):
                    prog.progress((i+1)/len(urls),text=f"Checking {url}")
                    info=lookup_url(url,pat_df,sidebar_lookup)
                    sb=info.get("sidebar") or {}
                    results.append({"URL":url,"Match":info["match_type"].title(),
                                    "Access Resource":info["resource"],"Type":info["type"],
                                    "Activity":info["activity"],"Scope":info["scope"],
                                    "Sidebar Tab":sb.get("Tab Name","—"),
                                    "Side Tab Group":sb.get("Side Tab Group","—")})
                prog.empty()
                res_df=pd.DataFrame(results)
                st.success(f"✅ {len(res_df)} URLs checked — {res_df['Access Resource'].nunique()} unique resources.")
                st.dataframe(res_df,use_container_width=True,hide_index=True,height=400)
                st.download_button("⬇️ Download bulk results (CSV)",
                                   res_df.to_csv(index=False).encode("utf-8"),
                                   "bulk_url_lookup.csv","text/csv")

# ─────────────────────────────────────────────────────────────────────────────
# TOOLS — ROLE BUILDER
# ─────────────────────────────────────────────────────────────────────────────
def render_role_builder(pat_df):
    st.markdown("#### 🧩 Role Builder — pick activities, get the exact permission list")
    st.caption("Select every activity this role needs. Required access resources are calculated automatically.")
    srch=st.text_input("Filter activity list",placeholder="gatepass, invoice, grn…",key="rb_srch",
                       help="Type to narrow the activity options below.")
    pool_df=pat_df.copy()
    if srch.strip():
        q=srch.strip().lower()
        mask=(pool_df["Activity"].str.lower().str.contains(q,na=False)|
              pool_df["URL Pattern"].str.lower().str.contains(q,na=False)|
              pool_df["Access Resource"].str.lower().str.contains(q,na=False))
        pool_df=pool_df[mask]
    options=sorted(pool_df["Activity"].unique())
    if not options: st.warning("No activities match that filter."); return
    chosen=st.multiselect("Select activities for this role",options=options,key="rb_acts",
                          help="Select as many as needed. Required resources update instantly.")
    if chosen:
        role_df=pool_df[pool_df["Activity"].isin(chosen)]
        required=sorted(role_df["Access Resource"].unique())
        st.markdown(f"**{len(required)} access resource(s) required:**")
        pills="".join(f'<span class="res-pill">{r}</span>' for r in required)
        st.markdown(f'<div class="info-strip">{pills}</div>',unsafe_allow_html=True)
        st.caption("Copy as comma-separated list ↓")
        st.code(", ".join(required),language="text")
        with st.expander("Full breakdown"):
            st.dataframe(role_df[["Activity","Access Resource","Type","Scope","URL Pattern"]],
                         use_container_width=True,hide_index=True,column_config=COL_CFG)
        st.download_button("⬇️ Download role definition (CSV)",
                           role_df.to_csv(index=False).encode("utf-8"),"custom_role.csv","text/csv")

# ─────────────────────────────────────────────────────────────────────────────
# TOOLS — COMPARE RESOURCES
# ─────────────────────────────────────────────────────────────────────────────
def render_compare(pat_df):
    st.markdown("#### ⚖️ Compare two access resources side by side")
    st.caption("See what URLs each covers, what overlaps, and what is unique to each.")
    all_res=sorted(pat_df["Access Resource"].unique())
    c1,c2=st.columns(2)
    res_a=c1.selectbox("Resource A",["— pick —"]+all_res,key="cmp_a",
                        help="First resource to compare.")
    res_b=c2.selectbox("Resource B",["— pick —"]+all_res,key="cmp_b",
                        help="Second resource to compare.")
    if res_a=="— pick —" or res_b=="— pick —": return
    if res_a==res_b: st.warning("Select two different resources."); return
    df_a=pat_df[pat_df["Access Resource"]==res_a]; df_b=pat_df[pat_df["Access Resource"]==res_b]
    urls_a=set(df_a["URL Pattern"]); urls_b=set(df_b["URL Pattern"])
    shared=urls_a&urls_b; only_a=urls_a-urls_b; only_b=urls_b-urls_a
    s1,s2,s3=st.columns(3)
    s1.metric(f"Only in {res_a}",len(only_a))
    s2.metric("Shared",len(shared))
    s3.metric(f"Only in {res_b}",len(only_b))
    def _show(tab,subset,base):
        with tab:
            rows=base[base["URL Pattern"].isin(subset)]
            if rows.empty: st.info("None.")
            else: st.dataframe(rows[["Activity","Type","Scope","URL Pattern"]].reset_index(drop=True),
                               use_container_width=True,hide_index=True,column_config=COL_CFG)
    ta,ts,tb=st.tabs([f"Only {res_a} ({len(only_a)})",f"Shared ({len(shared)})",f"Only {res_b} ({len(only_b)})"])
    _show(ta,only_a,df_a); _show(ts,shared,pd.concat([df_a,df_b]).drop_duplicates("URL Pattern")); _show(tb,only_b,df_b)

# ─────────────────────────────────────────────────────────────────────────────
# TOOLS — PERMISSION AUDIT
# ─────────────────────────────────────────────────────────────────────────────
def render_permission_audit(pat_df, side_df):
    st.markdown("#### 🔐 Permission Audit — paste a user's resource list, see what they can do")
    st.caption(
        "Paste the access resource names assigned to a user or role "
        "(comma-separated or one per line). The tool shows every action they can perform, "
        "which sidebar tabs they can access, and flags any unrecognised resources."
    )
    raw_input = st.text_area(
        "Access resources for this user / role",
        placeholder="MATERIAL_MANAGEMENT\nPROCUREMENT\nADMIN_CATALOG\nor: MATERIAL_MANAGEMENT, PROCUREMENT, ADMIN_CATALOG",
        height=130, key="pa_input",
        help="Paste from Uniware role config. One per line or comma-separated.",
    )
    if not raw_input.strip(): return
    # Parse input — handle comma-separated or newline-separated
    raw_resources = [r.strip() for r in re.split(r'[,\n]', raw_input) if r.strip()]
    all_known = set(pat_df["Access Resource"].unique()) | set(side_df["Access Resource"].unique())
    valid   = [r for r in raw_resources if r.upper() in {x.upper() for x in all_known}]
    invalid = [r for r in raw_resources if r.upper() not in {x.upper() for x in all_known}]
    # Normalise case
    res_map_lower = {x.upper(): x for x in all_known}
    valid_normalised = [res_map_lower[r.upper()] for r in valid]

    # Summary metrics
    pat_allowed  = pat_df[pat_df["Access Resource"].isin(valid_normalised)]
    side_allowed = side_df[side_df["Access Resource"].isin(valid_normalised)]

    m1,m2,m3,m4 = st.columns(4)
    m1.metric("Resources given",    len(raw_resources))
    m2.metric("Recognised",         len(valid),
              help="Resources found in the access pattern dump or sidebar mapping.")
    m3.metric("URLs accessible",    len(pat_allowed),
              help="Total backend URL patterns this permission set covers.")
    m4.metric("Sidebar tabs",       len(side_allowed),
              help="Number of sidebar navigation items accessible.")

    if invalid:
        st.markdown(
            f'<div class="warn-strip"><b>⚠️ {len(invalid)} unrecognised resource(s) — '
            f'not found in either data source:</b><br>'
            + "  ".join(f'<span class="res-pill" style="background:#fff3e0;color:#e65100">{r}</span>'
                        for r in invalid)
            + '</div>', unsafe_allow_html=True,
        )

    if not valid_normalised:
        st.error("None of the provided resources were recognised. Check spelling.")
        return

    st.divider()

    # READ / WRITE breakdown
    rc = int((pat_allowed["Type"]=="READ").sum())
    wc = int((pat_allowed["Type"]=="WRITE").sum())
    st.markdown(
        f'<div class="info-strip">'
        f'This permission set allows <b>{rc} READ</b> and <b>{wc} WRITE</b> actions '
        f'across <b>{pat_allowed["Access Resource"].nunique()} resources</b>.'
        f'</div>', unsafe_allow_html=True,
    )

    audit_tab1, audit_tab2, audit_tab3 = st.tabs([
        f"📋 URL Patterns ({len(pat_allowed)})",
        f"🗂️ Sidebar Tabs ({len(side_allowed)})",
        f"📊 Per-Resource Breakdown ({len(valid_normalised)})",
    ])

    with audit_tab1:
        if pat_allowed.empty:
            st.info("No URL patterns found for these resources.")
        else:
            st.dataframe(
                pat_allowed[["Access Resource","Activity","Type","Scope","URL Pattern"]].reset_index(drop=True),
                use_container_width=True, hide_index=True, height=480, column_config=COL_CFG,
            )
            st.download_button("⬇️ Download accessible URLs (CSV)",
                               pat_allowed.to_csv(index=False).encode("utf-8"),
                               "permission_audit_urls.csv","text/csv")

    with audit_tab2:
        if side_allowed.empty:
            st.info("No sidebar tabs match these resources.")
        else:
            st.dataframe(
                side_allowed[["Tab Name","Side Tab Group","Access Resource","Type","Activity"]].reset_index(drop=True),
                use_container_width=True, hide_index=True, height=400, column_config=COL_CFG,
            )

    with audit_tab3:
        breakdown = (pat_allowed.groupby(["Access Resource","Type"], as_index=False)
                     .agg(URLs=("URL Pattern","nunique"),
                          Activities=("Activity",lambda s:"  ·  ".join(sorted(set(s))[:4])))
                     .sort_values("URLs",ascending=False))
        st.dataframe(breakdown, use_container_width=True, hide_index=True,
                     column_config={"Access Resource":st.column_config.TextColumn(width=240),
                                    "Type":st.column_config.TextColumn(width=80),
                                    "URLs":st.column_config.NumberColumn("URL Count",width=90),
                                    "Activities":st.column_config.TextColumn("Sample Activities",width=400)})

# ─────────────────────────────────────────────────────────────────────────────
# TOOLS TAB
# ─────────────────────────────────────────────────────────────────────────────
def render_tools(pat_df, side_df, sidebar_lookup):
    tool = st.radio(
        "Choose a tool",
        ["🔗 URL Checker","🧩 Role Builder","⚖️ Compare Resources","🔐 Permission Audit"],
        horizontal=True,
        help=("URL Checker: paste any URL → resource instantly, bulk mode available.  "
              "Role Builder: pick activities → get exact permission list.  "
              "Compare: side-by-side diff of two resources.  "
              "Permission Audit: paste a user's resources → see everything they can do.")
    )
    st.divider()
    if "URL"        in tool: render_url_checker(pat_df, sidebar_lookup)
    elif "Role"     in tool: render_role_builder(pat_df)
    elif "Compare"  in tool: render_compare(pat_df)
    else:                    render_permission_audit(pat_df, side_df)

# ─────────────────────────────────────────────────────────────────────────────
# MAIN TABS
# ─────────────────────────────────────────────────────────────────────────────
tab_all, tab_pat, tab_side, tab_tools = st.tabs([
    "🔍  Search All",
    "📋  Pattern Dump",
    "🗂️  Sidebar Mapping",
    "🛠️  Tools",
])

with tab_all:
    render_search_all()

with tab_pat:
    render_tab(
        df=pat_df, pool=pat_pool, quick_terms=pat_quick, sk="pat",
        flat_cols=["Activity","Access Resource","Resource ID","Scope","Type","URL Pattern","Last Updated"],
        group_cols=["Activity","Type","Scope","URL Pattern","Last Updated"],
        src_label="access_patterns", pat_df_ref=pat_df, side_df_ref=side_df,
    )

with tab_side:
    render_tab(
        df=side_df, pool=side_pool, quick_terms=side_quick, sk="side",
        flat_cols=["Tab Name","Side Tab Group","Activity","Access Resource","Type","URL Pattern"],
        group_cols=["Tab Name","Side Tab Group","Activity","Type","URL Pattern"],
        extra_col="Side Tab Group", extra_label="Side Tab Group",
        extra_opts=sorted(g for g in side_df["Side Tab Group"].dropna().unique() if g),
        src_label="sidebar_mapping", pat_df_ref=pat_df, side_df_ref=side_df,
    )

with tab_tools:
    render_tools(pat_df, side_df, sidebar_lookup)

# ─────────────────────────────────────────────────────────────────────────────
st.divider()
st.caption(f"🛡️ Uniware Access Resource Auditor  ·  {TXT_FILE}  ·  {Path(DOC_FILE).name}")
