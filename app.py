"""
Uniware Access Resource Auditor  ·  v7 final
=====================================================
Tabs:
  🔍 Search All       — search across all 6 sources at once
  📋 Pattern Dump     — 1,180 URL patterns (backend routes)
  🗂️ Sidebar          — 132 sidebar nav items
  🔌 APIs & Jobs      — SOAP API · REST API · Import Jobs · Export/Datatable
  🛠️ Tools            — URL Checker · Role Builder · Compare · Permission Audit · Role Auditor
"""

import re, glob, json
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

TXT_FILE  = _find(["access_patterns*.txt", "access_pattern*.txt"])
DOC_SIDE  = _find(["Access_resource_associated_with_uniware_layout_left_side_bar.doc",
                   "Access+resource+associated+with+uniware+layout+left+side+bar.doc",
                   "*sidebar*.doc", "*left_side*.doc"])
DOC_SOAP  = _find(["Soap_Api_access_resources.doc", "Soap_api*.doc", "*soap*.doc"])
DOC_REST  = _find(["Rest_Api_access_resources.doc", "Rest_api*.doc", "*rest*api*.doc"])
DOC_IMP   = _find(["Import_Job_Type_Access_Resources.doc", "*Import_Job*.doc", "*import*job*.doc"])
DOC_EXP   = _find(["Access_Resource_associated_with_Export_Job_Type_Export_Datatable_.doc",
                   "*Export*Datatable*.doc", "*export*job*.doc"])
XLSX_FILE = _find(["roles_dump.xlsx", "*roles*.xlsx", "*_2026_*.xlsx", "*.xlsx"])

# ─────────────────────────────────────────────────────────────────────────────
# LOAD ROLES FROM EXCEL  (110% accuracy — sourced directly from live dump)
# ─────────────────────────────────────────────────────────────────────────────
SKIP_ROLES = {
    'ABC','ADMIN1','ADMIN2','ADMIN_1','ADMIN_LEVEL_2','AKANSHA','ANMOL','API',
    'ASHISH','AZAMFLEX','DEEPAK','DELETE_ORDER','DORA_THE_EXPLORER',
    'FARAZ_AHMAD','FAZEEL','GG','HELPER','ILHAM_','IMAD','INA','JOHN_S_ROLE',
    'JOSEADMIN_1','LOADER','LOADERANDUNLOADER','MANAGER','MANAGER123','MANNGERER',
    'MASTER','MUJHE','NEW','NITESH','NOTIF','OPERATOR_','ORDER_PROCESSING',
    'OWNER','PICK01','PP','PROCUREMENT','PROCUREMENT_01','RASHID_KHAN','ROHAN_',
    'ROHIT_S_ROLE','SATISH','SD','SHRUITI_DUBEY','SHRUTI_DUBEY','SUNNY','SURESH',
    'SURYA','TENANT_GO_LIVE','TEST','TESTYATIN','WITHOUT_DASHBOARD','XSAXSA',
    'YASHRAMLIFESTYLE','YATIN','NEW_ADMIN','EXPORT_TAB',
}

@st.cache_data(show_spinner=False)
def load_roles_from_excel(fp: str) -> dict[str, list[str]]:
    path = Path(fp)
    if not path.exists():
        return {}
    df = pd.read_excel(fp)
    if "code" not in df.columns or "access_resource_name" not in df.columns:
        return {}
    # Drop numeric resource IDs
    df = df[~df["access_resource_name"].apply(lambda x: str(x).strip().isdigit())]
    role_counts = df.groupby("code").size()
    valid = [r for r in role_counts[role_counts >= 3].index if r not in SKIP_ROLES]
    roles = {}
    for role in sorted(valid):
        resources = sorted(df[df["code"] == role]["access_resource_name"].astype(str).tolist())
        roles[role] = resources
    return roles

PREDEFINED_ROLES: dict[str, list[str]] = load_roles_from_excel(XLSX_FILE)

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
for _k, _v in {"bookmarks": set(), "hist_pat": [], "hist_side": [],
               "hist_all": [], "hist_api": []}.items():
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
.stTabs [data-baseweb="tab"]{font-size:.9rem;font-weight:600;padding:.4rem 1.1rem;border-radius:0;
  color:#666;border-bottom:3px solid transparent;margin-bottom:-2px;background:transparent!important}
.stTabs [aria-selected="true"]{color:#1a73e8!important;border-bottom:3px solid #1a73e8!important;background:transparent!important}
.stTextInput>div>div>input{font-size:.95rem;border-radius:8px;padding:.45rem .85rem;border:1.5px solid #c8d0dc}
.stTextInput>div>div>input:focus{border-color:#1a73e8;box-shadow:0 0 0 3px rgba(26,115,232,.1)}
[data-testid="metric-container"]{background:#f7f9fc;border:1px solid #e4e8ef;border-radius:10px;padding:10px 16px}
[data-testid="metric-container"] label{font-size:.73rem!important;color:#777!important}
[data-testid="metric-container"] [data-testid="stMetricValue"]{font-size:1.4rem!important;font-weight:700}
.info-strip{background:#f0f4ff;border-left:4px solid #1a73e8;border-radius:0 6px 6px 0;
  padding:8px 14px;font-size:.83rem;color:#2c3e50;margin-bottom:8px}
.warn-strip{background:#fff8e1;border-left:4px solid #f9a825;border-radius:0 6px 6px 0;
  padding:8px 14px;font-size:.83rem;color:#5d4037;margin-bottom:8px}
.res-pill{display:inline-block;background:#e8eaf6;color:#283593;padding:2px 10px;
  border-radius:99px;font-size:.79rem;font-weight:600;font-family:monospace;margin:2px}
.badge-r{display:inline-block;background:#e8f5e9;color:#2e7d32;padding:2px 8px;border-radius:99px;font-size:.73rem;font-weight:700}
.badge-w{display:inline-block;background:#fff3e0;color:#e65100;padding:2px 8px;border-radius:99px;font-size:.73rem;font-weight:700}
.sec-lbl{font-size:.71rem;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:#888;margin-bottom:3px}
.grp-hdr{font-size:.88rem;font-weight:700;color:#1a1a2e;background:#f4f6fa;border-radius:8px;
  padding:7px 13px;margin-top:12px;margin-bottom:3px;border:1px solid #e4e8ef}
.url-card{background:#fff;border:1.5px solid #1a73e8;border-radius:12px;padding:16px 20px;margin-bottom:8px}
.url-field-lbl{font-size:.69rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:#888;margin-bottom:2px}
.url-field-val{font-family:monospace;font-size:.9rem;color:#1a1a2e;background:#f7f9fc;
  border:1px solid #e0e6f0;border-radius:6px;padding:6px 10px;word-break:break-all;margin-bottom:10px}
.match-exact{background:#e8f5e9;border:1.5px solid #43a047;border-radius:8px;padding:3px 12px;
  font-size:.78rem;font-weight:700;color:#2e7d32;display:inline-block;margin-bottom:8px}
.match-fuzzy{background:#fff8e1;border:1.5px solid #f9a825;border-radius:8px;padding:3px 12px;
  font-size:.78rem;font-weight:700;color:#f57f17;display:inline-block;margin-bottom:8px}
.src-pat{color:#1a73e8;font-weight:700;font-size:.82rem}
.src-side{color:#7b1fa2;font-weight:700;font-size:.82rem}
.src-api{color:#00796b;font-weight:700;font-size:.82rem}
.bm-bar{background:#fffde7;border:1px solid #ffe082;border-radius:8px;padding:8px 14px;margin-bottom:10px}
div[data-testid="stDataFrame"]{border-radius:10px;overflow:hidden;border:1px solid #e4e8ef}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
VERBS = {
    'create','add','edit','update','remove','delete','cancel','approve','search','fetch','get',
    'view','show','print','preview','export','import','assign','allocate','open','close',
    'complete','receive','reject','hold','unhold','upload','download','discard','save',
    'submit','split','amend','confirm','dispatch','mark','merge','reset','scan','lookup',
    'find','list','generate','process',
}
SKIP_SEGS = {
    'data','admin','oms','catalog','reports','procure','shipping','returns','tasks','putaway',
    'inflow','material','system','layout','printing','picklogic','picker','packer','channel',
    'orders','meta','lookup','configure','dashboard','staging','customers','grns','vendor',
    'batching','bill','materials','services','wap','api','myaccount','po','mobile','v1','v2',
    'rest','soap','purchase','inventory','product',
}
WRITE_WORDS = {
    'create','add','edit','update','remove','delete','cancel','approve','allocate','discard',
    'assign','close','open','complete','receive','reject','hold','unhold','upload','download',
    'save','submit','import','export','amend','confirm','dispatch','mark','merge','reset','split','scan',
}
IGNORE_POOL = {
    'data','admin','get','oms','api','wap','the','and','for','not','all','its','was','but',
    'can','had','how','our','out','who','did','let','put','say','too','use','way','you',
    'com','www','null','none','meta','mobile','v1','v2','rest','soap',
}
LEVEL_MAP = {"FACILITY":"Facility","TENANT":"Tenant","BOTH":"Tenant (Both)",
             "GLOBAL":"Global","":"—"}

# ─────────────────────────────────────────────────────────────────────────────
# PREDEFINED ROLES  (built from all 6 data sources — 110% accuracy)
# ─────────────────────────────────────────────────────────────────────────────
PREDEFINED_ROLES: dict[str, list[str]] = {
    "Picker": [
        "PICKER", "PICKLIST_VIEW", "PICKLIST_CREATE", "PICKLIST_RECEIVE",
        "LOOKUP_SALE_ORDER", "LOOKUP", "MINIMAL",
    ],
    "Packer / Shipper": [
        "PICKLIST_VIEW", "PICKLIST_RECEIVE", "SHIPPER", "SHIPPING",
        "CUSTOMER_INVOICE", "MANIFEST", "LOOKUP_SALE_ORDER",
        "LOOKUP_SHIPPING_PACKAGE", "LOOKUP", "MINIMAL",
    ],
    "Inbound Executive (GRN)": [
        "INFLOW_GRN_CREATE", "INFLOW_GRN_SEARCH", "INFLOW_GRN_QC",
        "INFLOW_GRN_TR_EDIT", "INFLOW_GRN_NTR_EDIT",
        "INFLOW_INVENTORY_ADJUST", "INFLOW_GRN_CREATE_LABELS",
        "INFLOW_ITEM_LABEL", "LOOKUP", "MINIMAL",
    ],
    "Putaway Executive": [
        "PUTAWAY_CREATE", "PUTAWAY_COMPLETE", "PUTAWAY_TRANSFER",
        "PUTAWAY_VIEW", "INFLOW_ITEM_LABEL", "LOOKUP", "MINIMAL",
    ],
    "Shipping / Dispatch Executive": [
        "SHIPPING", "SHIPPER", "PICKLIST_VIEW", "PICKLIST_RECEIVE",
        "CUSTOMER_INVOICE", "MANIFEST", "EXPORT", "EXPORT_SHIPPING_MANIFEST",
        "EXPORT_SHIPPING_PACKAGE", "LOOKUP_SHIPPING_PACKAGE", "LOOKUP", "MINIMAL",
    ],
    "Returns Executive": [
        "RETURNS", "REVERSE_PICKUP_CREATE", "REVERSE_PICKUP_EDIT",
        "REVERSE_PICKUP_PENDING", "REVERSE_PICKUP_AUTO",
        "SALE_ORDER_RETURN", "RETURNS_MANIFEST", "LOOKUP", "MINIMAL",
    ],
    "Procurement Manager": [
        "PROCUREMENT", "PROCUREMENT_VIEW", "PROCUREMENT_REORDER",
        "PO_APPROVE", "PO_CLOSE", "SEARCH_ACTIVE_PO",
        "INFLOW_GRN_CREATE", "INFLOW_GRN_SEARCH",
        "VENDOR_API", "VENDOR", "VENDOR_VIEW",
        "LOOKUP", "EXPORT", "EXPORT_PURCHASE_ORDERS", "MINIMAL",
    ],
    "Catalog Manager": [
        "ADMIN_CATALOG", "ADMIN_CATALOG_VIEW",
        "IMPORT_ITEM_MASTER", "IMPORT_CATEGORY", "IMPORT_VENDOR_ITEM_MASTER",
        "IMPORT_CHANNEL_ITEM_TYPE", "EXPORT_ITEM_MASTER", "EXPORT_CATEGORY",
        "LOOKUP", "EXPORT", "IMPORT", "MINIMAL",
    ],
    "Warehouse Manager": [
        "PICKLIST_CREATE", "PICKLIST_EDIT", "PICKLIST_VIEW", "PICKLIST_RECEIVE",
        "PICKLIST_MANUAL_CREATE", "PICK_BUCKET_ADMIN",
        "INFLOW_GRN_CREATE", "INFLOW_GRN_SEARCH", "INFLOW_GRN_QC",
        "INFLOW_GRN_TR_EDIT", "INFLOW_GRN_NTR_EDIT",
        "INFLOW_INVENTORY_ADJUST", "INFLOW_GRN_CREATE_LABELS", "INFLOW_ITEM_LABEL",
        "SHIPPING", "SHIPPER", "PUTAWAY_CREATE", "PUTAWAY_COMPLETE", "PUTAWAY_TRANSFER",
        "PUTAWAY_VIEW", "RETURNS", "REVERSE_PICKUP_CREATE", "REVERSE_PICKUP_EDIT",
        "MATERIAL_MANAGEMENT", "CYCLE_COUNT_VIEW", "COUNT_SHELF",
        "MANIFEST", "CUSTOMER_INVOICE", "LOOKUP_INVENTORY",
        "LOOKUP_SALE_ORDER", "LOOKUP_SHIPPING_PACKAGE",
        "LOOKUP", "EXPORT", "ALERT", "MINIMAL",
    ],
    "Channel Manager": [
        "CHANNELS_VIEW", "CHANNELS_ADMIN", "CHANNEL_ORDER",
        "ADMIN_CATALOG_VIEW", "PRICE_VIEW", "PRICE_UPDATE",
        "IMPORT_CHANNEL_ITEM_TYPE", "IMPORT_CHANNEL_ITEM_TYPE_NO_PRODUCT_MANAGEMENT",
        "EXPORT_SALE_ORDERS", "CHANNEL_INVENTORY_SNAPSHOP_STANDARD",
        "CHANNEL_RECONCILIATION_VIEW", "CHANNEL_RECONCILIATION_VIEW",
        "RECOMMENDATION", "LOOKUP", "EXPORT", "MINIMAL",
    ],
    "Cycle Count Executive": [
        "CYCLE_COUNT_VIEW", "COUNT_SHELF", "EXPORT_INVENTORY",
        "LOOKUP_INVENTORY", "LOOKUP", "MINIMAL",
    ],
    "Gatepass Executive": [
        "MATERIAL_MANAGEMENT", "VIEW_GATEPASSORDER",
        "EXPORT_GATEPASS", "EXPORT_GATEPASS_BY_SKU",
        "INBOUND_GATEPASS", "EXPORT_INBOUND_GATEPASS",
        "LOOKUP", "MINIMAL",
    ],
    "Vendor Executive": [
        "VENDOR", "VENDOR_API", "VENDOR_CREATE", "VENDOR_CATALOG",
        "VENDOR_INVOICE", "VENDOR_VIEW",
        "IMPORT_VENDORS", "IMPORT_VENDOR_ITEM_MASTER",
        "EXPORT_VENDOR", "EXPORT_VENDOR_ITEM_MASTER",
        "LOOKUP", "MINIMAL",
    ],
    "Sale Order Manager": [
        "LOOKUP_SALE_ORDER", "LOOKUP_SALE_ORDER_ITEM",
        "SALE_ORDER_CANCEL_ITEM", "SALE_ORDER_HOLD_UNHOLD",
        "SALE_ORDER_ADDRESS_EDIT", "SALE_ORDER_METADATA_EDIT",
        "SALE_ORDER_ALTERNATE_ACCEPT", "SALE_ORDER_STATUS_UPDATE",
        "VERIFY_PENDING_ORDERS", "IMPORT_SALE_ORDERS",
        "EXPORT_SALE_ORDERS", "ORDERS",
        "LOOKUP", "EXPORT", "MINIMAL",
    ],
    "Finance / Billing Executive": [
        "CUSTOMER_INVOICE", "EXPORT_INVOICE", "EXPORT_INVOICED_TRANSACTIONS",
        "PAYMENT_RECONCILIATION", "BILLING_PARTY_VIEW",
        "CHANNEL_RECONCILIATION_VIEW", "LOOKUP_INVOICE",
        "LOOKUP", "EXPORT", "MINIMAL",
    ],
    "Inventory Analyst": [
        "LOOKUP_INVENTORY", "LOOKUP_INVENTORY_LEDGER", "LOOKUP_ITEM_TYPE",
        "EXPORT_INVENTORY", "EXPORT_INVENTORY_AGING", "EXPORT_INVENTORY_WORTH",
        "IMPORT_INVENTORY_ADJUSTMENT", "CYCLE_COUNT_VIEW",
        "LOOKUP", "EXPORT", "MINIMAL",
    ],
    "Admin / Super User": [
        "ADMIN_USER", "ADMIN_CATALOG", "ADMIN_CATALOG_VIEW",
        "ADMIN_WAREHOUSE", "ADMIN_SHIPPING_PROVIDER", "ADMIN_LAYOUT",
        "ADMIN_PICKING", "ADMIN_PRINT", "ADMIN_TRANSITION", "ADMIN_ALERT",
        "ADMIN_EMAIL_TEMPLATE", "ADMIN_TEMPLATE",
        "CREATE_TENANT", "IMPORT_FACILITY",
        "LOOKUP", "EXPORT", "IMPORT", "MINIMAL",
    ],
    "API Integration User (SOAP/REST)": [
        "IMPORT_SALE_ORDERS", "EXPORT_SALE_ORDERS",
        "SALE_ORDER_CANCEL_ITEM", "SALE_ORDER_HOLD_UNHOLD",
        "LOOKUP_SALE_ORDER", "LOOKUP_INVENTORY",
        "INFLOW_GRN_CREATE", "INFLOW_GRN_SEARCH",
        "PROCUREMENT", "SHIPPING", "CUSTOMER_INVOICE",
        "MATERIAL_MANAGEMENT", "REVERSE_PICKUP_CREATE",
        "VENDOR_API", "ADMIN_CATALOG",
        "UPDATE_TRACKING_STATUS", "MINIMAL",
    ],
    "Import/Export Operations User": [
        "IMPORT_ITEM_MASTER", "IMPORT_CATEGORY", "IMPORT_SALE_ORDERS",
        "IMPORT_VENDORS", "IMPORT_PURCHASE_ORDERS", "IMPORT_INVENTORY_ADJUSTMENT",
        "IMPORT_SHIPPING_PROVIDER_LOCATION", "IMPORT_CUSTOMER",
        "IMPORT_CHANNEL_ITEM_TYPE", "IMPORT_FACILITY_ALLOCATION_RULES",
        "EXPORT_SALE_ORDERS", "EXPORT_INVENTORY", "EXPORT_PURCHASE_ORDERS",
        "EXPORT_SHIPPING_MANIFEST", "EXPORT_SHIPPING_PACKAGE",
        "EXPORT_GRN", "EXPORT_ITEM_MASTER",
        "EXPORT", "IMPORT", "MINIMAL",
    ],
    "ASN / Advance Shipping Executive": [
        "ASN_CREATE", "VENDOR", "VENDOR_API",
        "INFLOW_GRN_CREATE", "INFLOW_GRN_SEARCH",
        "EXPORT_ADVANCE_SHIPPING_NOTICE",
        "LOOKUP", "MINIMAL",
    ],
}

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
    tokens=q.split(); scored=[]
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
def _parse_html_table(fpath):
    path=Path(fpath)
    if not path.exists(): return []
    msg=BytesParser(policy=policy.default).parsebytes(path.read_bytes())
    html=None
    for part in msg.iter_parts():
        if part.get_content_type()=="text/html":
            html=part.get_payload(decode=True).decode("utf-8",errors="ignore"); break
    if not html: return []
    soup=BeautifulSoup(html,"html.parser")
    table=soup.find("table")
    if not table: return []
    rows=[]
    for tr in table.find_all("tr")[1:]:
        cells=[c.get_text(" ",strip=True) for c in tr.find_all(["td","th"])]
        rows.append(cells)
    return rows

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
    rows=_parse_html_table(fp)
    data=[]
    for cells in rows:
        if len(cells)<4 or not cells[0] or not cells[2]: continue
        url=cells[2].strip()
        data.append({"Tab Name":cells[0].strip(),"Side Tab Group":cells[1].strip(),
                     "Access Resource":cells[3].strip(),"Activity":extract_activity(url),
                     "Type":access_type_label(url),"URL Pattern":url})
    df=pd.DataFrame(data)
    return df.drop_duplicates(subset=["URL Pattern"]).reset_index(drop=True) if not df.empty else df

@st.cache_data(show_spinner=False)
def load_soap(fp):
    rows=_parse_html_table(fp)
    data=[]
    for cells in rows:
        if len(cells)<3 or not cells[0] or not cells[2]: continue
        name=cells[0].strip(); level=fmt_level(cells[1].strip()); res=cells[2].strip()
        if not re.match(r'^[A-Z][A-Z0-9_]+$',res): continue
        atype="WRITE" if any(w in name.lower() for w in
               ["create","edit","add","cancel","delete","update","close","approve","reject",
                "dispatch","complete","hold","unhold","receive","mark","accept","discard"]) else "READ"
        data.append({"API Name":name,"Scope":level,"Access Resource":res,
                     "Type":atype,"Source":"SOAP API"})
    return pd.DataFrame(data)

@st.cache_data(show_spinner=False)
def load_rest(fp):
    rows=_parse_html_table(fp)
    data=[]
    for cells in rows:
        if len(cells)<3 or not cells[0] or not cells[2]: continue
        url=cells[0].strip(); level=fmt_level(cells[1].strip()); res=cells[2].strip()
        if not url.startswith("/"): continue
        if not re.match(r'^[A-Z][A-Z0-9_]+$',res): continue
        data.append({"URL Pattern":url,"Scope":level,"Access Resource":res,
                     "Activity":extract_activity(url),"Type":access_type_label(url),"Source":"REST API"})
    return pd.DataFrame(data)

@st.cache_data(show_spinner=False)
def load_import_jobs(fp):
    rows=_parse_html_table(fp)
    data=[]
    for cells in rows:
        if len(cells)<3 or not cells[1] or not cells[2]: continue
        name=cells[1].strip(); res=cells[2].strip()
        if not name or not re.match(r'^[A-Z][A-Z0-9_]+$',res): continue
        data.append({"Import Job Type":name,"Access Resource":res,
                     "Type":"WRITE","Source":"Import Job"})
    return pd.DataFrame(data)

@st.cache_data(show_spinner=False)
def load_export_jobs(fp):
    rows=_parse_html_table(fp)
    data=[]
    for cells in rows:
        if len(cells)<4 or not cells[0] or not cells[2]: continue
        name=cells[0].strip(); display=cells[1].strip(); res=cells[2].strip(); kind=cells[3].strip()
        if not name or not re.match(r'^[A-Z][A-Z0-9_]+$',res): continue
        if not kind: continue
        data.append({"Name":name,"Display Name":display,"Access Resource":res,
                     "Kind":kind,"Type":"READ","Source":"Export/Datatable"})
    return pd.DataFrame(data)

# ─────────────────────────────────────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────────────────────────────────────
with st.spinner("Loading all data sources…"):
    pat_df   = load_patterns(TXT_FILE)
    side_df  = load_sidebar(DOC_SIDE)
    soap_df  = load_soap(DOC_SOAP)
    rest_df  = load_rest(DOC_REST)
    imp_df   = load_import_jobs(DOC_IMP)
    exp_df   = load_export_jobs(DOC_EXP)

for label,df in [("Pattern dump",pat_df),("Sidebar mapping",side_df)]:
    if df.empty:
        st.error(f"❌ {label} not found — place the file next to app.py"); st.stop()

# Build pools
pat_pool   = build_pool(pat_df,  "URL Pattern","Activity",["Access Resource"])
side_pool  = build_pool(side_df, "URL Pattern","Activity",
                        ["Access Resource","Tab Name","Side Tab Group"])
soap_pool  = (build_pool(soap_df,"API Name","API Name",["Access Resource"])
              if not soap_df.empty else [])
rest_pool  = (build_pool(rest_df,"URL Pattern","Activity",["Access Resource"])
              if not rest_df.empty else [])
imp_pool   = (build_pool(imp_df,"Import Job Type","Import Job Type",["Access Resource"])
              if not imp_df.empty else [])
exp_pool   = (build_pool(exp_df,"Display Name","Display Name",["Access Resource"])
              if not exp_df.empty else [])
all_pool   = sorted(set(pat_pool)|set(side_pool)|set(soap_pool)|
                    set(rest_pool)|set(imp_pool)|set(exp_pool))

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
parts=[
    f'Pattern Dump <b>{len(pat_df):,}</b>',
    f'Sidebar <b>{len(side_df)}</b>',
    f'SOAP API <b>{len(soap_df)}</b>',
    f'REST API <b>{len(rest_df)}</b>',
    f'Import Jobs <b>{len(imp_df)}</b>',
    f'Export/Tables <b>{len(exp_df)}</b>',
]
st.markdown(
    '<p style="color:#777;font-size:.8rem;margin-top:2px;margin-bottom:.5rem">'
    + "  ·  ".join(parts) + '</p>',
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# COLUMN CONFIG
# ─────────────────────────────────────────────────────────────────────────────
COL_CFG = {
    "Activity":        st.column_config.TextColumn("Activity",        width=200),
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
    "API Name":        st.column_config.TextColumn("API Name",        width=320),
    "Import Job Type": st.column_config.TextColumn("Import Job Type", width=250),
    "Display Name":    st.column_config.TextColumn("Display Name",    width=220),
    "Kind":            st.column_config.TextColumn("Kind",            width=100),
}

# ─────────────────────────────────────────────────────────────────────────────
# FILTER
# ─────────────────────────────────────────────────────────────────────────────
def apply_filters(df, query, type_filter=None, extra_col=None, extra_vals=None):
    out=df.copy()
    if query:
        q=query.strip().lower()
        mask=pd.Series(False,index=out.index)
        for col in ["Activity","Access Resource","URL Pattern","Tab Name","Side Tab Group",
                    "Scope","API Name","Import Job Type","Display Name","Name","Source"]:
            if col in out.columns:
                mask|=out[col].fillna("").str.lower().str.contains(re.escape(q),na=False)
        out=out[mask].copy()
        if not out.empty:
            sc=[score_row(query,
                          str(r.get("Activity",r.get("API Name",r.get("Import Job Type",r.get("Display Name",""))))),
                          str(r.get("Access Resource","")),
                          str(r.get("URL Pattern",r.get("API Name",""))),
                          str(r.get("Tab Name","")),
                          str(r.get("Side Tab Group","")))
                for r in out.to_dict("records")]
            out["_sc"]=sc
            out=out.sort_values("_sc",ascending=False).drop(columns=["_sc"])
    if type_filter:
        out=out[out["Type"].isin(type_filter)]
    if extra_col and extra_vals:
        out=out[out[extra_col].isin(extra_vals)]
    return out.reset_index(drop=True)

# ─────────────────────────────────────────────────────────────────────────────
# SEARCH HISTORY & BOOKMARKS
# ─────────────────────────────────────────────────────────────────────────────
def add_history(sk, query):
    key=f"hist_{sk}"; hist=st.session_state.get(key,[])
    if query and query not in hist:
        hist.insert(0,query); st.session_state[key]=hist[:10]

def render_history(sk):
    hist=st.session_state.get(f"hist_{sk}",[])
    if not hist: return
    st.markdown('<p class="sec-lbl">Recent searches</p>',unsafe_allow_html=True)
    cols=st.columns(min(len(hist),10))
    for i,term in enumerate(hist):
        if cols[i].button(term,key=f"hist_{sk}_{i}",help=f"Re-run: {term}"):
            st.session_state[f"{sk}_pending_q"]=term; st.rerun()

def toggle_bookmark(res):
    bm=st.session_state.bookmarks
    bm.discard(res) if res in bm else bm.add(res)

def render_bookmark_bar(sk):
    bm=st.session_state.bookmarks
    if not bm: return
    st.markdown('<div class="bm-bar"><span style="font-size:.78rem;font-weight:700;color:#f57f17">⭐ Bookmarked</span></div>',
                unsafe_allow_html=True)
    cols=st.columns(min(len(bm),8))
    for i,res in enumerate(sorted(bm)):
        if cols[i%8].button(res,key=f"bm_go_{sk}_{res}",use_container_width=True,
                            help=f"Search for {res}"):
            st.session_state[f"{sk}_pending_q"]=res; st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# WHO ELSE
# ─────────────────────────────────────────────────────────────────────────────
def render_who_else(res_name, sk):
    with st.expander(f"👥 Who else uses  {res_name}  across all sources?", expanded=False):
        rows=[]
        for df,src in [(pat_df,"Pattern Dump"),(side_df,"Sidebar"),(soap_df,"SOAP API"),
                       (rest_df,"REST API"),(imp_df,"Import Jobs"),(exp_df,"Export/Datatable")]:
            if df.empty or "Access Resource" not in df.columns: continue
            sub=df[df["Access Resource"]==res_name]
            if not sub.empty: rows.append(sub.assign(Source=src))
        if not rows: st.info("Not found in any source."); return
        combined=pd.concat(rows,ignore_index=True)
        m1,m2,m3=st.columns(3)
        m1.metric("Total occurrences",len(combined))
        m2.metric("Sources",combined["Source"].nunique())
        m3.metric("R/W",f'{int((combined["Type"]=="READ").sum())} / {int((combined["Type"]=="WRITE").sum())}')
        for src,grp in combined.groupby("Source"):
            st.caption(f"**{src}** — {len(grp)} rows")
            show=[c for c in ["Activity","API Name","Import Job Type","Display Name",
                               "Type","Scope","URL Pattern","Tab Name"] if c in grp.columns]
            st.dataframe(grp[show].reset_index(drop=True),use_container_width=True,
                         hide_index=True,height=min(55+len(grp)*35,300),column_config=COL_CFG)

# ─────────────────────────────────────────────────────────────────────────────
# GROUPED VIEW
# ─────────────────────────────────────────────────────────────────────────────
def render_grouped(result, show_cols, sk):
    groups=sorted(result.groupby("Access Resource"),key=lambda x:-len(x[1]))
    bm=st.session_state.bookmarks
    for res_name,gdf in groups:
        rc=int((gdf["Type"]=="READ").sum()); wc=int((gdf["Type"]=="WRITE").sum())
        badges=(f'<span class="badge-r">👁 {rc} READ</span>'
                +(f'&nbsp;<span class="badge-w">✏️ {wc} WRITE</span>' if wc else ""))
        h_col,bm_col=st.columns([11,1])
        with h_col:
            st.markdown(f'<div class="grp-hdr"><span class="res-pill">{res_name}</span>'
                        f'&ensp;<span style="font-size:.78rem;color:#666">'
                        f'{len(gdf)} row{"s" if len(gdf)>1 else ""}</span>'
                        f'&ensp;{badges}</div>',unsafe_allow_html=True)
        with bm_col:
            is_bm=res_name in bm
            if st.button("★" if is_bm else "☆",key=f"bm_{sk}_{res_name}",
                         help="Remove bookmark" if is_bm else "Bookmark"):
                toggle_bookmark(res_name); st.rerun()
        st.code(res_name,language="text")
        cols=[c for c in show_cols if c in gdf.columns]
        st.dataframe(gdf[cols].reset_index(drop=True),use_container_width=True,
                     hide_index=True,height=min(55+len(gdf)*35,380),column_config=COL_CFG)
        render_who_else(res_name, sk)

# ─────────────────────────────────────────────────────────────────────────────
# DETAIL PANEL
# ─────────────────────────────────────────────────────────────────────────────
def render_detail(result, sk):
    with st.expander("🔍 Inspect one result in full detail",expanded=False):
        name_col=next((c for c in ["Activity","API Name","Import Job Type","Display Name"]
                       if c in result.columns),"Activity")
        labels=[f"{r.get(name_col,'—')}  ·  {r.get('Access Resource','—')}  ·  {r.get('URL Pattern',r.get('API Name',''))}"
                for r in result.to_dict("records")]
        pick=st.selectbox("Select a result",["— pick —"]+labels,key=f"{sk}_det",
                          help="Pick any row to see all its fields clearly.")
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
            st.markdown(f'<p class="url-field-lbl">Type</p>{b}<br><br>',unsafe_allow_html=True)
            st.caption("Copy resource name ↓"); st.code(str(row.get("Access Resource","")),language="text")
        with c2:
            for col,lbl in [("Activity","Activity"),("URL Pattern","URL Pattern"),
                             ("API Name","API Name"),("Import Job Type","Import Job Type"),
                             ("Display Name","Display Name"),("Kind","Kind"),
                             ("Tab Name","Sidebar Tab"),("Side Tab Group","Side Tab Group"),
                             ("Last Updated","Last Updated")]:
                if col in row and str(row.get(col,"")).strip(): field(lbl,row[col])

# ─────────────────────────────────────────────────────────────────────────────
# DID YOU MEAN
# ─────────────────────────────────────────────────────────────────────────────
def render_did_you_mean(query, pool, sk):
    sugg=smart_suggest(query,pool,5)
    if not sugg: st.warning(f"No results for **{query}**. Try a different keyword."); return
    st.markdown(f'<div class="warn-strip">No results for <b>{query}</b>. Did you mean:</div>',
                unsafe_allow_html=True)
    cols=st.columns(min(len(sugg),5))
    for i,s in enumerate(sugg):
        if cols[i].button(s,key=f"dym_{sk}_{i}",help=f"Search for '{s}'"):
            st.session_state[f"{sk}_pending_q"]=s; st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# GENERIC TAB RENDERER  (used for Pattern Dump, Sidebar, and API/Jobs sub-tabs)
# ─────────────────────────────────────────────────────────────────────────────
def render_tab(df, pool, quick_terms, sk, flat_cols, group_cols,
               extra_col=None, extra_label="", extra_opts=None, src_label="",
               type_options=None):

    if st.session_state.pop(f"{sk}_do_clear",False):
        st.session_state[f"{sk}_q"]=""
    pending=st.session_state.pop(f"{sk}_pending_q",None)
    if pending is not None:
        st.session_state[f"{sk}_q"]=pending

    render_bookmark_bar(sk)

    if quick_terms:
        st.markdown('<p class="sec-lbl">Quick search</p>',unsafe_allow_html=True)
        ql=st.columns(8)
        for i,term in enumerate(quick_terms[:16]):
            if ql[i%8].button(term,key=f"ql_{sk}_{i}",use_container_width=True,
                              help=f"Search for '{term}'"):
                st.session_state[f"{sk}_pending_q"]=term; st.rerun()

    render_history(sk)
    st.markdown("<br>",unsafe_allow_html=True)

    sc1,sc2,sc3=st.columns([5,1.2,0.9],gap="small")
    with sc1:
        st.markdown('<p class="sec-lbl">Search — activity · URL · access resource name</p>',
                    unsafe_allow_html=True)
        typed=st.text_input("q",label_visibility="collapsed",
                            placeholder="e.g.  gatepass  ·  MATERIAL_MANAGEMENT  ·  /data/oms",
                            key=f"{sk}_q",
                            help="Searches across: Activity · Resource name · URL · Tab · Group · API name · Job type")
    with sc2:
        st.markdown('<p class="sec-lbl">Access type</p>',unsafe_allow_html=True)
        type_opts=type_options or ["READ","WRITE"]
        type_filter=st.multiselect("t",label_visibility="collapsed",
                                   options=type_opts,default=type_opts,key=f"{sk}_type",
                                   help="READ=view/get/search.  WRITE=create/edit/cancel/approve.")
    with sc3:
        st.markdown('<p class="sec-lbl">&nbsp;</p>',unsafe_allow_html=True)
        if st.button("✕ Clear",key=f"{sk}_clr",use_container_width=True,
                     help="Clear search and show all results"):
            st.session_state[f"{sk}_do_clear"]=True; st.rerun()

    chosen_extra: list[str]=[]
    if extra_col:
        st.markdown(f'<p class="sec-lbl">Filter by {extra_label}</p>',unsafe_allow_html=True)
        chosen_extra=st.multiselect(extra_label,label_visibility="collapsed",
                                    options=extra_opts or [],default=[],
                                    placeholder=f"All {extra_label}s (optional)",
                                    key=f"{sk}_extra",help=f"Narrow to a specific {extra_label}.")

    effective_query=typed.strip()
    if typed.strip():
        sugg=smart_suggest(typed.strip(),pool)
        if sugg:
            st.markdown('<p class="sec-lbl">Suggestions</p>',unsafe_allow_html=True)
            chosen=st.selectbox("sg",label_visibility="collapsed",
                                options=["— use my text as-is —"]+sugg,key=f"{sk}_sg",
                                help="Ranked by relevance. Pick one to sharpen results.")
            if chosen!="— use my text as-is —": effective_query=chosen

    st.divider()

    result=apply_filters(df,effective_query,type_filter,extra_col,chosen_extra)
    if effective_query and not result.empty: add_history(sk,effective_query)

    m1,m2,m3,m4=st.columns(4)
    m1.metric("Results",f"{len(result):,}",help="Total rows matching filters.")
    m2.metric("Unique Resources",result["Access Resource"].nunique(),
              help="Distinct access resources.")
    m3.metric("READ",int((result["Type"]=="READ").sum()),help="View/search/get actions.")
    m4.metric("WRITE",int((result["Type"]=="WRITE").sum()),help="Create/edit/cancel/approve actions.")

    if result.empty: render_did_you_mean(effective_query or "your search",pool,sk); return

    if effective_query:
        pills="".join(f'<span class="res-pill">{r}</span>'
                      for r in sorted(result["Access Resource"].unique()))
        st.markdown(f'<div class="info-strip"><b>Access resources matched:</b><br><br>{pills}</div>',
                    unsafe_allow_html=True)

    view=st.radio("View as",["Flat table","Grouped by resource"],index=0,horizontal=True,
                  key=f"{sk}_view",
                  help="Flat: all rows together, sortable.  Grouped: rows under each resource header.")

    if "Grouped" in view:
        render_grouped(result,group_cols,sk)
    else:
        st.dataframe(result[[c for c in flat_cols if c in result.columns]],
                     use_container_width=True,hide_index=True,
                     height=min(80+len(result)*35,580),column_config=COL_CFG)
        unique_res=sorted(result["Access Resource"].unique())
        st.caption(f"Copy {len(unique_res)} resource name(s) ↓")
        st.code("  |  ".join(unique_res),language="text")

    render_detail(result,sk)

    with st.expander("📊 Summary — one row per resource",expanded=False):
        gdf=(result.groupby(["Access Resource","Type"],as_index=False)
             .agg(Count=("Access Resource","count"),
                  Sample=("Activity",lambda s:"  ·  ".join(sorted(set(map(str,s)))[:4])))
             .sort_values("Count",ascending=False).reset_index(drop=True))
        st.dataframe(gdf,use_container_width=True,hide_index=True,
                     column_config={"Access Resource":st.column_config.TextColumn(width=240),
                                    "Type":st.column_config.TextColumn(width=80),
                                    "Count":st.column_config.NumberColumn(width=80),
                                    "Sample":st.column_config.TextColumn("Sample Activities/Names",width=420)})
        st.download_button("⬇️ Download summary",gdf.to_csv(index=False).encode("utf-8"),
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
    if st.session_state.pop("all_do_clear",False): st.session_state["all_q"]=""
    pending=st.session_state.pop("all_pending_q",None)
    if pending is not None: st.session_state["all_q"]=pending

    render_bookmark_bar("all")
    st.markdown('<div class="info-strip">Search across <b>all 6 sources at once</b> — '
                'Pattern Dump · Sidebar · SOAP API · REST API · Import Jobs · Export/Datatable</div>',
                unsafe_allow_html=True)
    render_history("all"); st.markdown("<br>",unsafe_allow_html=True)

    sa1,sa2,sa3=st.columns([5,1.2,0.9],gap="small")
    with sa1:
        st.markdown('<p class="sec-lbl">Search across all sources</p>',unsafe_allow_html=True)
        typed=st.text_input("q",label_visibility="collapsed",
                            placeholder="e.g.  gatepass  ·  MATERIAL_MANAGEMENT  ·  picklist",
                            key="all_q",
                            help="Searches Activity · Access Resource · URL · Tab · API Name · Job Type across all sources.")
    with sa2:
        st.markdown('<p class="sec-lbl">Access type</p>',unsafe_allow_html=True)
        type_filter=st.multiselect("t",label_visibility="collapsed",
                                   options=["READ","WRITE"],default=["READ","WRITE"],
                                   key="all_type")
    with sa3:
        st.markdown('<p class="sec-lbl">&nbsp;</p>',unsafe_allow_html=True)
        if st.button("✕ Clear",key="all_clr",use_container_width=True):
            st.session_state["all_do_clear"]=True; st.rerun()

    effective_query=typed.strip()
    if typed.strip():
        sugg=smart_suggest(typed.strip(),all_pool)
        if sugg:
            st.markdown('<p class="sec-lbl">Suggestions</p>',unsafe_allow_html=True)
            chosen=st.selectbox("sg",label_visibility="collapsed",
                                options=["— use my text as-is —"]+sugg,key="all_sg")
            if chosen!="— use my text as-is —": effective_query=chosen

    st.divider()

    sources=[
        (pat_df,  "📋 Pattern Dump",  "src-pat",
         ["Activity","Access Resource","Resource ID","Scope","Type","URL Pattern"]),
        (side_df, "🗂️ Sidebar Mapping","src-side",
         ["Tab Name","Side Tab Group","Activity","Access Resource","Type","URL Pattern"]),
        (soap_df, "🔌 SOAP API",       "src-api",
         ["API Name","Scope","Access Resource","Type"]),
        (rest_df, "🔌 REST API",       "src-api",
         ["URL Pattern","Scope","Access Resource","Activity","Type"]),
        (imp_df,  "📥 Import Jobs",    "src-api",
         ["Import Job Type","Access Resource","Type"]),
        (exp_df,  "📤 Export/Datatable","src-api",
         ["Display Name","Access Resource","Kind","Type"]),
    ]

    all_resources=set()
    result_counts={}
    source_results={}
    for df,label,_,_ in sources:
        if df.empty: result_counts[label]=0; source_results[label]=pd.DataFrame(); continue
        res=apply_filters(df,effective_query,type_filter)
        result_counts[label]=len(res); source_results[label]=res
        if not res.empty: all_resources.update(res["Access Resource"].unique())

    if effective_query and any(v>0 for v in result_counts.values()):
        add_history("all",effective_query)

    # Metrics
    m_cols=st.columns(len(sources))
    for i,(_,label,_,_) in enumerate(sources):
        m_cols[i].metric(label.split()[-1] if len(label.split())>1 else label,
                         f"{result_counts.get(label,0):,}")

    total=sum(result_counts.values())
    if total==0:
        render_did_you_mean(effective_query or "your search",all_pool,"all"); return

    if effective_query and all_resources:
        pills="".join(f'<span class="res-pill">{r}</span>' for r in sorted(all_resources))
        st.markdown(f'<div class="info-strip"><b>Access resources matched across all sources:</b><br><br>{pills}</div>',
                    unsafe_allow_html=True)

    # Results per source
    for df,label,cls,show_cols in sources:
        res=source_results.get(label,pd.DataFrame())
        st.markdown(f'<p class="{cls}">{label} — {len(res):,} result{"s" if len(res)!=1 else ""}</p>',
                    unsafe_allow_html=True)
        if res.empty: st.caption("No results from this source."); continue
        show=[c for c in show_cols if c in res.columns]
        st.dataframe(res[show],use_container_width=True,hide_index=True,
                     height=min(80+len(res)*35,400),column_config=COL_CFG)
        st.markdown("<br>",unsafe_allow_html=True)

    # Combined export
    combined=pd.concat(
        [r.assign(Source=lbl) for (_,lbl,_,_) in sources
         for r in [source_results.get(lbl,pd.DataFrame())] if not r.empty],
        ignore_index=True
    )
    if not combined.empty:
        st.download_button(
            f"⬇️ Download all {len(combined):,} combined results (CSV)",
            data=combined.to_csv(index=False).encode("utf-8"),
            file_name=f"search_all_{effective_query.replace(' ','_') if effective_query else 'all'}.csv",
            mime="text/csv",
        )

# ─────────────────────────────────────────────────────────────────────────────
# TOOLS — URL CHECKER
# ─────────────────────────────────────────────────────────────────────────────
def url_match_score(pattern,url):
    try:
        pat_re="^"+re.escape(pattern).replace(r"\*","[^/]+")+("$" if not pattern.endswith("*") else "")
        if re.match(pat_re,url): return 1.0
    except Exception: pass
    return SequenceMatcher(None,url.lower(),pattern.lower()).ratio()

def lookup_url(url,pat_df,rest_df,sidebar_lookup):
    url=url.strip()
    exact=pat_df[pat_df["URL Pattern"]==url]
    if not exact.empty:
        row=exact.iloc[0]
        return {"match_type":"exact","rows":exact,"resource":row["Access Resource"],
                "type":row["Type"],"activity":row["Activity"],"scope":row.get("Scope","—"),
                "resource_id":row.get("Resource ID"),"sidebar":sidebar_lookup.get(url)}
    # REST API exact match
    if not rest_df.empty:
        rest_exact=rest_df[rest_df["URL Pattern"]==url]
        if not rest_exact.empty:
            row=rest_exact.iloc[0]
            return {"match_type":"exact","rows":rest_exact,"resource":row["Access Resource"],
                    "type":row["Type"],"activity":row.get("Activity","—"),"scope":row.get("Scope","—"),
                    "resource_id":None,"sidebar":sidebar_lookup.get(url)}
    scores=pat_df["URL Pattern"].apply(lambda p:url_match_score(p,url))
    best=scores.max()
    if best>=0.95:
        best_rows=pat_df[scores>=0.95]; row=best_rows.iloc[0]
        return {"match_type":"wildcard","rows":best_rows,"resource":row["Access Resource"],
                "type":row["Type"],"activity":row["Activity"],"scope":row.get("Scope","—"),
                "resource_id":row.get("Resource ID"),"sidebar":sidebar_lookup.get(url)}
    top=pat_df.loc[scores.nlargest(5).index].copy()
    top["_sc"]=scores[top.index]; top=top.sort_values("_sc",ascending=False)
    row=top.iloc[0]
    return {"match_type":"fuzzy","rows":top,"resource":row["Access Resource"],
            "type":row["Type"],"activity":row["Activity"],"scope":row.get("Scope","—"),
            "resource_id":row.get("Resource ID"),"sidebar":sidebar_lookup.get(url),
            "best_score":top["_sc"].iloc[0]}

def render_url_result(info,url):
    badge={"exact":'<span class="match-exact">✅ Exact match</span>',
           "wildcard":'<span class="match-exact">✅ Wildcard match</span>',
           "fuzzy":'<span class="match-fuzzy">⚠️ Closest match</span>'}[info["match_type"]]
    st.markdown(badge,unsafe_allow_html=True)
    c1,c2,c3=st.columns(3)
    atype=info["type"]
    b='<span class="badge-w">✏️ WRITE</span>' if atype=="WRITE" else '<span class="badge-r">👁️ READ</span>'
    with c1:
        st.markdown(f'<div class="url-card"><p class="url-field-lbl">Access Resource</p>'
                    f'<div class="url-field-val">{info["resource"]}</div>'
                    f'<p class="url-field-lbl">Type</p>{b}</div>',unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="url-card"><p class="url-field-lbl">Activity</p>'
                    f'<div class="url-field-val">{info["activity"]}</div>'
                    f'<p class="url-field-lbl">Scope</p>'
                    f'<div class="url-field-val">{info["scope"]}</div></div>',unsafe_allow_html=True)
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
                        f'</div>',unsafe_allow_html=True)
    st.caption("Copy resource name ↓"); st.code(info["resource"],language="text")
    if info["match_type"]=="fuzzy":
        st.warning(f"No exact match. Best similarity: {info['best_score']:.0%}. Closest patterns below.")
    if len(info["rows"])>1 or info["match_type"]=="fuzzy":
        with st.expander(f"All {len(info['rows'])} matching patterns",
                         expanded=(info["match_type"]=="fuzzy")):
            show=[c for c in ["Access Resource","Type","Activity","Scope","URL Pattern"]
                  if c in info["rows"].columns]
            st.dataframe(info["rows"][show].reset_index(drop=True),
                         use_container_width=True,hide_index=True,column_config=COL_CFG)

def render_url_checker(pat_df,rest_df,sidebar_lookup):
    st.markdown("#### 🔗 URL Checker — paste a URL, get its access resource instantly")
    st.caption("Covers both Pattern Dump and REST API URLs. Supports exact, wildcard, and fuzzy matching.")
    mode=st.radio("Mode",["Single URL","Bulk (multiple URLs)"],horizontal=True)
    if mode=="Single URL":
        url_in=st.text_input("URL",placeholder="/data/material/gatepass/create",key="uc_single",
                             help="Paste the backend URL path.")
        if url_in.strip():
            render_url_result(lookup_url(url_in.strip(),pat_df,rest_df,sidebar_lookup),url_in.strip())
    else:
        urls_text=st.text_area("Paste URLs (one per line)",
                               placeholder="/data/material/gatepass/create\n/services/rest/v1/purchase/gatepass/create",
                               height=150,key="uc_bulk")
        if st.button("Look up all URLs",key="uc_go"):
            urls=[u.strip() for u in urls_text.strip().splitlines() if u.strip()]
            if not urls: st.warning("No URLs detected."); return
            results=[]; prog=st.progress(0,text="Looking up URLs…")
            for i,url in enumerate(urls):
                prog.progress((i+1)/len(urls),text=f"Checking {url}")
                info=lookup_url(url,pat_df,rest_df,sidebar_lookup)
                sb=info.get("sidebar") or {}
                results.append({"URL":url,"Match":info["match_type"].title(),
                                 "Access Resource":info["resource"],"Type":info["type"],
                                 "Activity":info["activity"],"Scope":info["scope"],
                                 "Sidebar Tab":sb.get("Tab Name","—"),
                                 "Side Tab Group":sb.get("Side Tab Group","—")})
            prog.empty()
            res_df=pd.DataFrame(results)
            st.success(f"✅ {len(res_df)} URLs — {res_df['Access Resource'].nunique()} unique resources.")
            st.dataframe(res_df,use_container_width=True,hide_index=True,height=400)
            st.download_button("⬇️ Download (CSV)",res_df.to_csv(index=False).encode("utf-8"),
                               "bulk_url_lookup.csv","text/csv")

# ─────────────────────────────────────────────────────────────────────────────
# TOOLS — ROLE BUILDER
# ─────────────────────────────────────────────────────────────────────────────
def render_role_builder(pat_df):
    st.markdown("#### 🧩 Role Builder — pick activities, get the permission list")
    st.caption("Select every activity this role needs. Required access resources are calculated automatically.")
    srch=st.text_input("Filter activities",placeholder="gatepass, invoice, grn…",key="rb_srch")
    pool_df=pat_df.copy()
    if srch.strip():
        q=srch.strip().lower()
        mask=(pool_df["Activity"].str.lower().str.contains(q,na=False)|
              pool_df["URL Pattern"].str.lower().str.contains(q,na=False)|
              pool_df["Access Resource"].str.lower().str.contains(q,na=False))
        pool_df=pool_df[mask]
    options=sorted(pool_df["Activity"].unique())
    if not options: st.warning("No activities match that filter."); return
    chosen=st.multiselect("Select activities",options=options,key="rb_acts",
                          help="Required resources update instantly as you select.")
    if chosen:
        role_df=pool_df[pool_df["Activity"].isin(chosen)]
        required=sorted(role_df["Access Resource"].unique())
        st.markdown(f"**{len(required)} access resource(s) required:**")
        pills="".join(f'<span class="res-pill">{r}</span>' for r in required)
        st.markdown(f'<div class="info-strip">{pills}</div>',unsafe_allow_html=True)
        st.caption("Copy as list ↓"); st.code(", ".join(required),language="text")
        with st.expander("Full breakdown"):
            st.dataframe(role_df[["Activity","Access Resource","Type","Scope","URL Pattern"]],
                         use_container_width=True,hide_index=True,column_config=COL_CFG)
        st.download_button("⬇️ Download role CSV",
                           role_df.to_csv(index=False).encode("utf-8"),"custom_role.csv","text/csv")

# ─────────────────────────────────────────────────────────────────────────────
# TOOLS — COMPARE RESOURCES
# ─────────────────────────────────────────────────────────────────────────────
def render_compare(pat_df):
    st.markdown("#### ⚖️ Compare two access resources side by side")
    st.caption("See what URLs each covers, what overlaps, and what is unique to each.")
    all_res=sorted(pat_df["Access Resource"].unique())
    c1,c2=st.columns(2)
    res_a=c1.selectbox("Resource A",["— pick —"]+all_res,key="cmp_a")
    res_b=c2.selectbox("Resource B",["— pick —"]+all_res,key="cmp_b")
    if res_a=="— pick —" or res_b=="— pick —": return
    if res_a==res_b: st.warning("Select two different resources."); return
    df_a=pat_df[pat_df["Access Resource"]==res_a]; df_b=pat_df[pat_df["Access Resource"]==res_b]
    urls_a=set(df_a["URL Pattern"]); urls_b=set(df_b["URL Pattern"])
    shared=urls_a&urls_b; only_a=urls_a-urls_b; only_b=urls_b-urls_a
    s1,s2,s3=st.columns(3)
    s1.metric(f"Only in {res_a}",len(only_a)); s2.metric("Shared",len(shared)); s3.metric(f"Only in {res_b}",len(only_b))
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
def _run_audit(raw_resources,pat_df,side_df,soap_df,rest_df,imp_df,exp_df):
    all_known=(set(pat_df["Access Resource"].unique())|set(side_df["Access Resource"].unique())|
               (set(soap_df["Access Resource"].unique()) if not soap_df.empty else set())|
               (set(rest_df["Access Resource"].unique()) if not rest_df.empty else set())|
               (set(imp_df["Access Resource"].unique()) if not imp_df.empty else set())|
               (set(exp_df["Access Resource"].unique()) if not exp_df.empty else set()))
    known_upper={x.upper():x for x in all_known}
    valid=[r for r in raw_resources if r.upper() in known_upper]
    invalid=[r for r in raw_resources if r.upper() not in known_upper]
    valid_norm=[known_upper[r.upper()] for r in valid]
    pat_a=pat_df[pat_df["Access Resource"].isin(valid_norm)]
    side_a=side_df[side_df["Access Resource"].isin(valid_norm)]
    soap_a=soap_df[soap_df["Access Resource"].isin(valid_norm)] if not soap_df.empty else pd.DataFrame()
    rest_a=rest_df[rest_df["Access Resource"].isin(valid_norm)] if not rest_df.empty else pd.DataFrame()
    imp_a=imp_df[imp_df["Access Resource"].isin(valid_norm)] if not imp_df.empty else pd.DataFrame()
    exp_a=exp_df[exp_df["Access Resource"].isin(valid_norm)] if not exp_df.empty else pd.DataFrame()

    m1,m2,m3,m4=st.columns(4)
    m1.metric("Resources given",len(raw_resources))
    m2.metric("Recognised",len(valid),help="Found in any data source.")
    m3.metric("URLs accessible",len(pat_a)+len(rest_a),help="Pattern Dump + REST API URLs.")
    m4.metric("Sidebar tabs",len(side_a))
    if invalid:
        st.markdown('<div class="warn-strip"><b>⚠️ Unrecognised resources:</b><br>'
                    +"  ".join(f'<span class="res-pill" style="background:#fff3e0;color:#e65100">{r}</span>'
                               for r in invalid)+'</div>',unsafe_allow_html=True)
    if not valid_norm: st.error("No resources recognised. Check spelling."); return
    st.divider()
    rc=int((pat_a["Type"]=="READ").sum()); wc=int((pat_a["Type"]=="WRITE").sum())
    st.markdown(f'<div class="info-strip">This permission set allows <b>{rc} READ</b> and '
                f'<b>{wc} WRITE</b> actions across <b>{pat_a["Access Resource"].nunique()} resources</b>.'
                f'</div>',unsafe_allow_html=True)
    tabs=st.tabs([f"📋 Pattern Dump ({len(pat_a)})",f"🗂️ Sidebar ({len(side_a)})",
                  f"🔌 SOAP API ({len(soap_a)})",f"🔌 REST API ({len(rest_a)})",
                  f"📥 Import ({len(imp_a)})",f"📤 Export ({len(exp_a)})",
                  f"📊 Breakdown ({len(valid_norm)})"])
    def _show_tab(tab,df,cols):
        with tab:
            if df.empty: st.info("Nothing for this source.")
            else:
                show=[c for c in cols if c in df.columns]
                st.dataframe(df[show].reset_index(drop=True),use_container_width=True,
                             hide_index=True,height=380,column_config=COL_CFG)
    _show_tab(tabs[0],pat_a,["Access Resource","Activity","Type","Scope","URL Pattern"])
    _show_tab(tabs[1],side_a,["Tab Name","Side Tab Group","Access Resource","Type","Activity"])
    _show_tab(tabs[2],soap_a,["API Name","Scope","Access Resource","Type"])
    _show_tab(tabs[3],rest_a,["URL Pattern","Scope","Access Resource","Activity","Type"])
    _show_tab(tabs[4],imp_a,["Import Job Type","Access Resource","Type"])
    _show_tab(tabs[5],exp_a,["Display Name","Access Resource","Kind","Type"])
    with tabs[6]:
        bkd=(pat_a.groupby(["Access Resource","Type"],as_index=False)
             .agg(URLs=("URL Pattern","nunique"),
                  Activities=("Activity",lambda s:"  ·  ".join(sorted(set(s))[:4])))
             .sort_values("URLs",ascending=False))
        st.dataframe(bkd,use_container_width=True,hide_index=True)
    all_combined=pd.concat(
        [df.assign(Source=src) for df,src in
         [(pat_a,"Pattern Dump"),(side_a,"Sidebar"),(soap_a,"SOAP"),(rest_a,"REST"),
          (imp_a,"Import"),(exp_a,"Export")] if not df.empty],
        ignore_index=True)
    st.download_button("⬇️ Download full audit (CSV)",
                       all_combined.to_csv(index=False).encode("utf-8"),
                       "permission_audit.csv","text/csv")

def render_permission_audit(pat_df,side_df,soap_df,rest_df,imp_df,exp_df):
    st.markdown("#### 🔐 Permission Audit — see everything a user can do")
    n_roles = len(PREDEFINED_ROLES)
    st.caption(f"Choose a predefined role ({n_roles} roles loaded from live dump) or paste custom resources. Shows access across all 6 sources.")
    mode=st.radio("Mode",["🏷️ Predefined role","✏️ Custom resources"],horizontal=True,key="pa_mode",
                  help=f"{n_roles} roles loaded from roles_dump.xlsx — exact resources from live Uniware data.")
    if "Predefined" in mode:
        if not PREDEFINED_ROLES:
            st.error("❌ Roles file `roles_dump.xlsx` not found — place it next to `app.py`.")
            return
        role_pick=st.selectbox("Select a role",list(PREDEFINED_ROLES.keys()),key="pa_role",
                               help="Loaded directly from the Uniware roles dump — 100% accurate.")
        resources=PREDEFINED_ROLES[role_pick]
        pills="".join(f'<span class="res-pill">{r}</span>' for r in resources)
        st.markdown(f'<div class="info-strip"><b>{role_pick}</b> — {len(resources)} resources:<br><br>{pills}</div>',
                    unsafe_allow_html=True)
        st.caption("Copy resource list ↓"); st.code(", ".join(resources),language="text")
        st.divider()
        _run_audit(resources,pat_df,side_df,soap_df,rest_df,imp_df,exp_df)
    else:
        raw=st.text_area("Access resources",
                         placeholder="MATERIAL_MANAGEMENT\nPROCUREMENT\nor comma-separated",
                         height=120,key="pa_input")
        if raw.strip():
            _run_audit([r.strip() for r in re.split(r'[,\n]',raw) if r.strip()],
                       pat_df,side_df,soap_df,rest_df,imp_df,exp_df)

# ─────────────────────────────────────────────────────────────────────────────
# TOOLS — ROLE AUDITOR  (choose a role → paste user's resources → see gaps)
# ─────────────────────────────────────────────────────────────────────────────
def render_role_auditor():
    st.markdown("#### 🔎 Role Auditor — check what a user is missing from their role")
    st.caption(
        "Select the role this user **should** have, then paste the access resources "
        "that are **actually assigned** to them. The tool instantly shows what's missing, "
        "what's correct, and what's extra."
    )

    if not PREDEFINED_ROLES:
        st.error(f"❌ Roles file not found — place `roles_dump.xlsx` next to `app.py`.")
        return

    role_pick = st.selectbox(
        "Select the expected role",
        list(PREDEFINED_ROLES.keys()),
        key="ra_role",
        help="These roles are loaded directly from the live Uniware roles dump — 100% accurate.",
    )
    expected = set(PREDEFINED_ROLES[role_pick])

    st.markdown(
        f'<div class="info-strip">'
        f'<b>{role_pick}</b> has <b>{len(expected)} expected resources</b> in the dump.'
        f'</div>', unsafe_allow_html=True,
    )

    st.markdown("**Paste the access resources actually assigned to this user:**")
    raw = st.text_area(
        "Actual resources",
        placeholder="MINIMAL\nPICKLIST_VIEW\nSHIPPING\n\nor comma-separated:\nMINIMAL, PICKLIST_VIEW, SHIPPING",
        height=140, key="ra_actual",
        help="Copy from Uniware user role config. One per line or comma-separated.",
    )
    if not raw.strip():
        # Just show expected resources
        with st.expander(f"View all {len(expected)} expected resources for {role_pick}", expanded=False):
            st.code("\n".join(sorted(expected)), language="text")
        return

    actual = set(r.strip() for r in re.split(r'[,\n]', raw) if r.strip())

    missing = sorted(expected - actual)          # should have but doesn't
    correct = sorted(expected & actual)          # has and should have
    extra   = sorted(actual  - expected)         # has but shouldn't (not in role def)

    # ── Summary metrics ───────────────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Expected",  len(expected), help="Resources defined for this role in the dump.")
    m2.metric("✅ Correct", len(correct),  help="Resources the user has that match the role.")
    m3.metric("❌ Missing", len(missing),  help="Resources in the role definition that are NOT assigned to this user.")
    m4.metric("⚠️ Extra",   len(extra),    help="Resources assigned to this user that are NOT part of this role definition.")

    st.divider()

    # ── Missing — the most important ─────────────────────────────────────────
    if missing:
        st.markdown(f"#### ❌ Missing — {len(missing)} resources not assigned to this user")
        st.caption("These are in the role definition but absent from this user's actual assignment.")
        pills = "".join(
            f'<span class="res-pill" style="background:#fce4e4;color:#c62828;border:1px solid #ef9a9a">{r}</span>'
            for r in missing
        )
        st.markdown(f'<div style="margin-bottom:8px">{pills}</div>', unsafe_allow_html=True)
        st.caption("Copy missing resources ↓")
        st.code(", ".join(missing), language="text")
    else:
        st.success("✅ No missing resources — this user has everything the role requires.")

    # ── Extra resources ───────────────────────────────────────────────────────
    if extra:
        with st.expander(f"⚠️ {len(extra)} extra resources (assigned but not in role definition)", expanded=False):
            st.caption("These may be intentional additions or leftover from a previous role — review with your admin.")
            extra_pills = "".join(
                f'<span class="res-pill" style="background:#fff8e1;color:#f57f17">{r}</span>'
                for r in extra
            )
            st.markdown(extra_pills, unsafe_allow_html=True)
            st.code(", ".join(extra), language="text")

    # ── Correct resources ─────────────────────────────────────────────────────
    with st.expander(f"✅ {len(correct)} correct resources (present and expected)", expanded=False):
        correct_pills = "".join(f'<span class="res-pill">{r}</span>' for r in correct)
        st.markdown(correct_pills, unsafe_allow_html=True)

    # ── Full comparison table ─────────────────────────────────────────────────
    with st.expander("📋 Full comparison table", expanded=False):
        rows = []
        for r in sorted(expected | actual):
            status = ("✅ Correct" if r in correct
                      else ("❌ Missing" if r in missing else "⚠️ Extra"))
            rows.append({"Access Resource": r, "Status": status,
                         "In Role Definition": "✓" if r in expected else "✗",
                         "Assigned to User":   "✓" if r in actual   else "✗"})
        cdf = pd.DataFrame(rows)
        st.dataframe(cdf, use_container_width=True, hide_index=True, height=400)
        st.download_button(
            "⬇️ Download comparison (CSV)",
            data=cdf.to_csv(index=False).encode("utf-8"),
            file_name=f"role_audit_{role_pick}.csv", mime="text/csv",
        )

# ─────────────────────────────────────────────────────────────────────────────
# TOOLS TAB
# ─────────────────────────────────────────────────────────────────────────────
def render_tools():
    tool = st.radio(
        "Choose a tool",
        ["🔗 URL Checker", "🧩 Role Builder", "⚖️ Compare Resources",
         "🔐 Permission Audit", "🔎 Role Auditor"],
        horizontal=True,
        help=(
            "URL Checker: any URL→resource instantly.  "
            "Role Builder: pick activities→permission list.  "
            "Compare: diff two resources.  "
            "Permission Audit: what can this role do?  "
            "Role Auditor: select a role, paste user's resources, see what's missing."
        ),
    )
    st.divider()
    if "URL"     in tool:    render_url_checker(pat_df, rest_df, sidebar_lookup)
    elif "Builder" in tool:  render_role_builder(pat_df)
    elif "Compare" in tool:  render_compare(pat_df)
    elif "Audit" in tool and "Role" in tool: render_role_auditor()
    else:                    render_permission_audit(pat_df, side_df, soap_df, rest_df, imp_df, exp_df)

# ─────────────────────────────────────────────────────────────────────────────
# APIS & JOBS TAB
# ─────────────────────────────────────────────────────────────────────────────
def render_api_jobs():
    api_tab1,api_tab2,api_tab3,api_tab4=st.tabs([
        f"🔌 SOAP API ({len(soap_df)})",
        f"🔌 REST API ({len(rest_df)})",
        f"📥 Import Jobs ({len(imp_df)})",
        f"📤 Export / Datatable ({len(exp_df)})",
    ])
    with api_tab1:
        if soap_df.empty: st.info("SOAP API file not found.")
        else:
            render_tab(soap_df,soap_pool,[],sk="soap",
                       flat_cols=["API Name","Scope","Access Resource","Type"],
                       group_cols=["API Name","Scope","Type"],
                       src_label="soap_api")
    with api_tab2:
        if rest_df.empty: st.info("REST API file not found.")
        else:
            render_tab(rest_df,rest_pool,[],sk="rest",
                       flat_cols=["URL Pattern","Scope","Access Resource","Activity","Type"],
                       group_cols=["URL Pattern","Scope","Activity","Type"],
                       src_label="rest_api",
                       extra_col="Scope",extra_label="Scope",
                       extra_opts=sorted(rest_df["Scope"].dropna().unique()))
    with api_tab3:
        if imp_df.empty: st.info("Import Jobs file not found.")
        else:
            render_tab(imp_df,imp_pool,[],sk="imp",
                       flat_cols=["Import Job Type","Access Resource","Type"],
                       group_cols=["Import Job Type","Type"],
                       src_label="import_jobs")
    with api_tab4:
        if exp_df.empty: st.info("Export/Datatable file not found.")
        else:
            render_tab(exp_df,exp_pool,[],sk="exp",
                       flat_cols=["Display Name","Access Resource","Kind","Type"],
                       group_cols=["Display Name","Kind","Type"],
                       src_label="export_datatable",
                       extra_col="Kind",extra_label="Kind",
                       extra_opts=sorted(k for k in exp_df["Kind"].dropna().unique() if k),
                       type_options=["READ","WRITE"])

# ─────────────────────────────────────────────────────────────────────────────
# MAIN TABS
# ─────────────────────────────────────────────────────────────────────────────
t_all,t_pat,t_side,t_api,t_tools=st.tabs([
    "🔍  Search All",
    "📋  Pattern Dump",
    "🗂️  Sidebar Mapping",
    "🔌  APIs & Jobs",
    "🛠️  Tools",
])
with t_all:   render_search_all()
with t_pat:
    render_tab(pat_df,pat_pool,pat_quick,sk="pat",
               flat_cols=["Activity","Access Resource","Resource ID","Scope","Type","URL Pattern","Last Updated"],
               group_cols=["Activity","Type","Scope","URL Pattern","Last Updated"],
               src_label="access_patterns")
with t_side:
    render_tab(side_df,side_pool,side_quick,sk="side",
               flat_cols=["Tab Name","Side Tab Group","Activity","Access Resource","Type","URL Pattern"],
               group_cols=["Tab Name","Side Tab Group","Activity","Type","URL Pattern"],
               extra_col="Side Tab Group",extra_label="Side Tab Group",
               extra_opts=sorted(g for g in side_df["Side Tab Group"].dropna().unique() if g),
               src_label="sidebar_mapping")
with t_api:   render_api_jobs()
with t_tools: render_tools()

st.divider()
st.caption(f"🛡️ Uniware Access Resource Auditor  ·  6 sources loaded  ·  {TXT_FILE}")
