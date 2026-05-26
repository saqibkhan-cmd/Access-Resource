import re
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup
from email import policy
from email.parser import BytesParser

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="Uniware Access Resource Auditor",
    layout="wide",
    page_icon="🛡️"
)

st.title("🛡️ Uniware Access Resource Auditor")
st.caption("Search access resources by activity, URL, access resource name, or resource id")

TXT_FILE = "access_patterns (2)(2).txt"
DOC_FILE = "Access+resource+associated+with+uniware+layout+left+side+bar.doc"

# =====================================================
# HELPERS
# =====================================================

VERBS = [
    "create", "add", "edit", "update", "remove", "delete", "cancel",
    "approve", "search", "fetch", "get", "view", "show", "print",
    "preview", "export", "import", "assign", "allocate", "open",
    "close", "complete", "receive", "reject", "hold", "unhold",
    "upload", "download", "discard", "save", "submit", "split"
]

SYSTEM_WORDS = {
    "data", "admin", "oms", "catalog", "reports", "procure",
    "shipping", "returns", "tasks", "putaway", "inflow", "material",
    "system", "layout", "printing", "picklogic", "picker", "packer",
    "channel", "products", "product", "orders", "order", "meta", "lookup",
    "configure", "dashboard", "staging", "customers", "customer", "grns",
    "vendor", "batching", "bill", "materials", "search", "view", "show"
}

def normalize_text(text: str) -> str:
    text = str(text).lower().strip()
    text = text.replace("-", " ").replace("_", " ")
    text = re.sub(r"\s+", " ", text)
    return text

def split_camel(text: str) -> str:
    text = str(text).replace("-", " ").replace("_", " ")
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def titleize_segment(seg: str) -> str:
    return split_camel(seg).title().strip()

def is_intish(value) -> bool:
    try:
        return str(value).strip().isdigit()
    except Exception:
        return False

def access_type(url: str) -> str:
    u = normalize_text(url)
    write_words = [
        "create", "add", "edit", "update", "remove", "delete", "cancel",
        "approve", "allocate", "discard", "assign", "close", "open",
        "complete", "receive", "reject", "hold", "unhold", "upload",
        "download", "save", "submit", "import", "export"
    ]
    return "WRITE" if any(w in u for w in write_words) else "READ"

def extract_activity(url: str) -> str:
    """
    The last meaningful action being performed.
    Examples:
      /data/catalog/addTag -> Add Tag
      /data/shipping/splitPackage -> Split Package
      /channel/returnFacilityMapping -> Return Facility Mapping
    """
    url = str(url).strip()
    parts = [p for p in url.strip("/").split("/") if p]
    if not parts:
        return "Root"

    for idx in range(len(parts) - 1, -1, -1):
        seg = split_camel(parts[idx])
        low = seg.lower()

        for verb in VERBS:
            if low == verb:
                if idx + 1 < len(parts):
                    tail = titleize_segment(parts[idx + 1])
                    if tail and tail.lower() not in SYSTEM_WORDS:
                        return f"{verb.title()} {tail}"
                return verb.title()

            if low.startswith(verb):
                tail = seg[len(verb):].strip()
                tail = re.sub(r"^[-_/ ]+", "", tail)
                tail = titleize_segment(tail)
                if tail:
                    return f"{verb.title()} {tail}"
                if idx + 1 < len(parts):
                    tail2 = titleize_segment(parts[idx + 1])
                    if tail2 and tail2.lower() not in SYSTEM_WORDS:
                        return f"{verb.title()} {tail2}"
                return verb.title()

    return titleize_segment(parts[-1])

def infer_resource_name(url: str, resource_id=None) -> str:
    """
    Best-effort fallback when the sidebar doc doesn't give an exact resource name.
    """
    u = normalize_text(url)

    if "/channel/returnfacilitymapping" in u:
        return "CHANNELS_ADMIN"
    if "channelpaymentreconciliation" in u or "/admin/system/paymentreconciliation" in u:
        return "PAYMENT_RECONCILIATION"
    if "/channel/productmapping" in u or "/channel/unmappedsku" in u or "/channel/pendency" in u:
        return "CHANNEL_PRODUCTS"
    if (
        "/channel/addchannel" in u
        or "/channel/sources" in u
        or "/channel/view" in u
        or "/data/meta/sources" in u
        or "/data/channel/getchannels" in u
        or "/data/channel/getchanneldetails" in u
        or "/data/channel/getchannelordersummary" in u
        or "/data/channel/getchannelproductsummary" in u
        or "/channel/preconfigurechannel" in u
        or "/channel/postconfigurechannel" in u
        or "/channel/gotochannellandingpage" in u
        or "/channel/redirect" in u
        or "/data/channel/addchannelconnector" in u
    ):
        return "SOURCES_VIEW"

    if "pricemaster" in u:
        return "PRICE_MASTER"

    if "/catalog" in u or "/products" in u:
        if any(x in u for x in ["/products/inventory", "inventory/adjustmenthistory"]):
            return "LOOKUP_INVENTORY"
        if any(v in u for v in ["create", "add", "edit", "update", "remove", "delete", "category", "tag", "itemtype"]):
            return "ADMIN_CATALOG"
        if any(v in u for v in ["search", "get", "view", "show"]):
            return "ADMIN_CATALOG_VIEW"
        return "ADMIN_CATALOG"

    if "/shipping" in u or "/shipment" in u or "/manifests" in u:
        return "SHIPPING"

    if "/returns" in u:
        return "RETURNS"

    if "/procure" in u or "/po/" in u:
        return "PROCUREMENT"

    if "/inflow" in u:
        return "INFLOW"

    if "/putaway" in u:
        return "PUTAWAY"

    if "/admin/" in u:
        parts = [p for p in u.strip("/").split("/") if p]
        if len(parts) >= 2:
            return "ADMIN_" + parts[1].upper()
        return "ADMIN"

    if resource_id is not None:
        return f"RESOURCE_{resource_id}"

    return "UNMAPPED"

def make_search_blob(df: pd.DataFrame) -> pd.Series:
    cols = [
        df["source"].fillna("").astype(str),
        df["access_resource_name"].fillna("").astype(str),
        df["access_resource_id"].fillna("").astype(str),
        df["tab_name"].fillna("").astype(str),
        df["side_tab_group"].fillna("").astype(str),
        df["url_pattern"].fillna("").astype(str),
        df["activity"].fillna("").astype(str),
        df["access_type"].fillna("").astype(str),
    ]
    return (cols[0] + " " + cols[1] + " " + cols[2] + " " + cols[3] + " " + cols[4] + " " + cols[5] + " " + cols[6] + " " + cols[7]).str.lower()

def score_query(query: str, row) -> float:
    q = normalize_text(query)
    if not q:
        return 0.0

    values = {
        "resource_name": normalize_text(row.access_resource_name),
        "url": normalize_text(row.url_pattern),
        "activity": normalize_text(row.activity),
        "tab": normalize_text(row.tab_name or ""),
        "group": normalize_text(row.side_tab_group or ""),
        "rid": str("" if pd.isna(row.access_resource_id) else row.access_resource_id),
    }

    score = 0.0
    if q == values["rid"]:
        score += 100
    if q in values["resource_name"]:
        score += 50
    if q in values["url"]:
        score += 55
    if q in values["activity"]:
        score += 45
    if q in values["tab"]:
        score += 35
    if q in values["group"]:
        score += 30

    for token in q.split():
        if token in values["resource_name"]:
            score += 8
        if token in values["url"]:
            score += 8
        if token in values["activity"]:
            score += 8
        if token in values["tab"]:
            score += 5
        if token in values["group"]:
            score += 5

    score += SequenceMatcher(None, q, values["resource_name"]).ratio() * 10
    score += SequenceMatcher(None, q, values["url"]).ratio() * 10
    score += SequenceMatcher(None, q, values["activity"]).ratio() * 8
    return score

# =====================================================
# PARSERS
# =====================================================

@st.cache_data
def parse_txt_dump(file_path: str) -> pd.DataFrame:
    path = Path(file_path)
    if not path.exists():
        return pd.DataFrame()

    raw = path.read_text(encoding="utf-8", errors="ignore")
    rows = []

    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("+---") or "|" not in line:
            continue

        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) < 5:
            continue
        if parts[0].lower() == "id":
            continue
        if not parts[0].isdigit() or not parts[1].isdigit():
            continue

        url = parts[2].strip()
        if not url.startswith("/"):
            continue

        rows.append(
            {
                "id": int(parts[0]),
                "access_resource_id": int(parts[1]),
                "url_pattern": url,
                "created": parts[3].strip() if len(parts) > 3 else "",
                "updated": parts[4].strip() if len(parts) > 4 else "",
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df["source"] = "access pattern dump"
    return df.drop_duplicates(subset=["access_resource_id", "url_pattern"]).reset_index(drop=True)

@st.cache_data
def parse_sidebar_doc(file_path: str) -> pd.DataFrame:
    path = Path(file_path)
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

    soup = BeautifulSoup(html_payload, "html.parser")
    table = soup.find("table")
    if table is None:
        return pd.DataFrame()

    rows = []
    for tr in table.find_all("tr")[1:]:
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        if len(cells) < 4:
            continue
        rows.append(
            {
                "tab_name": cells[0],
                "side_tab_group": cells[1],
                "url_pattern": cells[2],
                "access_resource_name": cells[3],
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df["source"] = "sidebar mapping"
    return df.drop_duplicates(subset=["url_pattern"]).reset_index(drop=True)

def build_master_dataframe(txt_df: pd.DataFrame, doc_df: pd.DataFrame) -> pd.DataFrame:
    if txt_df.empty and doc_df.empty:
        return pd.DataFrame()

    exact_doc = doc_df.copy() if not doc_df.empty else pd.DataFrame(columns=["url_pattern", "tab_name", "side_tab_group", "access_resource_name", "source"])
    exact_doc_map = exact_doc.set_index("url_pattern").to_dict("index") if not exact_doc.empty else {}

    merged_txt = txt_df.copy()
    if not merged_txt.empty:
        merged_txt["tab_name"] = merged_txt["url_pattern"].map(lambda u: exact_doc_map.get(u, {}).get("tab_name"))
        merged_txt["side_tab_group"] = merged_txt["url_pattern"].map(lambda u: exact_doc_map.get(u, {}).get("side_tab_group"))
        merged_txt["exact_access_resource_name"] = merged_txt["url_pattern"].map(lambda u: exact_doc_map.get(u, {}).get("access_resource_name"))

        dominant_by_id = {}
        exact_subset = merged_txt.dropna(subset=["exact_access_resource_name"])
        for rid, g in exact_subset.groupby("access_resource_id"):
            counts = g["exact_access_resource_name"].value_counts()
            if len(counts) == 1 or counts.iloc[0] > counts.iloc[1]:
                dominant_by_id[rid] = counts.index[0]

        def finalize_name(row):
            exact_name = row["exact_access_resource_name"]
            if pd.notna(exact_name) and str(exact_name).strip():
                return str(exact_name).strip(), "exact"
            if row["access_resource_id"] in dominant_by_id:
                return dominant_by_id[row["access_resource_id"]], "dominant-id"
            return infer_resource_name(row["url_pattern"], row["access_resource_id"]), "inferred"

        values = merged_txt.apply(finalize_name, axis=1, result_type="expand")
        merged_txt["access_resource_name"] = values[0]
        merged_txt["resource_name_source"] = values[1]

        merged_txt["tab_name"] = merged_txt["tab_name"].fillna("")
        merged_txt["side_tab_group"] = merged_txt["side_tab_group"].fillna("")
        merged_txt["access_type"] = merged_txt["url_pattern"].apply(access_type)
        merged_txt["activity"] = merged_txt["url_pattern"].apply(extract_activity)
        merged_txt["row_label"] = merged_txt.apply(
            lambda r: f"{r['activity']} | {r['access_resource_name']} | {r['access_resource_id']} | {r['url_pattern']}",
            axis=1,
        )
    else:
        merged_txt = pd.DataFrame(columns=[
            "id", "access_resource_id", "url_pattern", "created", "updated",
            "tab_name", "side_tab_group", "exact_access_resource_name",
            "access_resource_name", "resource_name_source", "access_type", "activity", "row_label", "source"
        ])

    txt_urls = set(txt_df["url_pattern"].tolist()) if not txt_df.empty else set()
    doc_only_rows = []
    for r in doc_df.itertuples(index=False):
        if r.url_pattern in txt_urls:
            continue
        doc_only_rows.append(
            {
                "id": None,
                "access_resource_id": None,
                "url_pattern": r.url_pattern,
                "created": "",
                "updated": "",
                "tab_name": r.tab_name,
                "side_tab_group": r.side_tab_group,
                "exact_access_resource_name": r.access_resource_name,
                "access_resource_name": r.access_resource_name,
                "resource_name_source": "exact-doc",
                "access_type": access_type(r.url_pattern),
                "activity": extract_activity(r.url_pattern),
                "row_label": f"{extract_activity(r.url_pattern)} | {r.access_resource_name} | {r.url_pattern}",
                "source": "sidebar mapping",
            }
        )

    doc_only_df = pd.DataFrame(doc_only_rows)
    master = pd.concat([merged_txt, doc_only_df], ignore_index=True, sort=False)
    master["search_blob"] = make_search_blob(master)
    master = master.drop_duplicates(subset=["source", "access_resource_name", "access_resource_id", "url_pattern"]).reset_index(drop=True)
    return master

def search_master(df: pd.DataFrame, query: str, source_filter: str | None = None, access_type_filter: list[str] | None = None) -> pd.DataFrame:
    q = normalize_text(query)
    out = df.copy()

    if source_filter and source_filter != "all":
        out = out[out["source"] == source_filter]

    if access_type_filter:
        out = out[out["access_type"].isin(access_type_filter)]

    if q:
        mask = (
            out["search_blob"].str.contains(re.escape(q), na=False)
            | out["row_label"].str.lower().str.contains(re.escape(q), na=False)
            | out["url_pattern"].str.lower().str.contains(re.escape(q), na=False)
            | out["access_resource_name"].str.lower().str.contains(re.escape(q), na=False)
            | out["tab_name"].fillna("").str.lower().str.contains(re.escape(q), na=False)
            | out["side_tab_group"].fillna("").str.lower().str.contains(re.escape(q), na=False)
            | out["access_resource_id"].astype(str).eq(q)
        )
        out = out[mask].copy()

        if out.empty:
            return out

        scores = []
        for r in out.itertuples(index=False):
            scores.append(score_query(q, r))
        out["score"] = scores
        out = out.sort_values(["score", "source", "access_resource_name", "url_pattern"], ascending=[False, True, True, True])

    return out.reset_index(drop=True)

def grouped_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    return (
        df.groupby(["access_resource_name", "access_type", "source"], as_index=False)
        .agg(
            urls=("url_pattern", lambda s: " • ".join(sorted(set(map(str, s))))),
            tab_names=("tab_name", lambda s: " • ".join(sorted(set([x for x in map(str, s) if x and x != 'nan'])))),
            count=("url_pattern", "nunique"),
        )
        .sort_values(["count", "access_resource_name"], ascending=[False, True])
        .reset_index(drop=True)
    )

# =====================================================
# LOAD DATA
# =====================================================

txt_df = parse_txt_dump(TXT_FILE)
doc_df = parse_sidebar_doc(DOC_FILE)
master_df = build_master_dataframe(txt_df, doc_df)

if master_df.empty:
    st.error("No data could be loaded from the files.")
    st.stop()

# =====================================================
# SIDEBAR
# =====================================================

st.sidebar.header("Search")

query = st.sidebar.text_input(
    "Search",
    placeholder="Try: create catalog, split package, /channel/returnFacilityMapping, ADMIN_CATALOG",
    help="Search works across activity, access resource name, URL pattern, tab name, side tab group, and resource id."
)

access_type_choices = sorted(master_df["access_type"].dropna().unique().tolist())
selected_access_types = st.sidebar.multiselect(
    "Access type",
    access_type_choices,
    default=access_type_choices,
    help="READ = mostly view/search/get. WRITE = create/update/cancel/approve/allocate and other change actions."
)

source_choice = st.sidebar.selectbox(
    "Source",
    options=["all", "access pattern dump", "sidebar mapping"],
    index=0,
    help="Choose the raw pattern dump, the sidebar mapping doc, or both."
)

show_resource_filter = st.sidebar.checkbox(
    "Show access resource filter",
    value=False,
    help="Use this only when you want to narrow the result set by a specific access resource name."
)

selected_resource_names = None
if show_resource_filter:
    resource_search = st.sidebar.text_input(
        "Filter resource names",
        placeholder="Type part of a resource name, e.g. catalog, shipping, channels",
        help="This narrows the dropdown to matching resource names."
    )
    resource_options = sorted(master_df["access_resource_name"].dropna().unique().tolist())
    if resource_search.strip():
        rs = normalize_text(resource_search)
        resource_options = [r for r in resource_options if rs in normalize_text(r)]
    resource_options = ["All access resources"] + resource_options
    chosen_resource = st.sidebar.selectbox(
        "Access resource name",
        resource_options,
        help="Exact resource name from the file or a best-fit inferred resource name."
    )
    if chosen_resource != "All access resources":
        selected_resource_names = [chosen_resource]

show_grouped = st.sidebar.checkbox(
    "Show grouped summary",
    value=True,
    help="Shows a compact one-row-per-resource summary."
)

show_raw = st.sidebar.checkbox(
    "Show raw rows",
    value=False,
    help="Shows the underlying merged rows from both files."
)

only_unique_resources = st.sidebar.checkbox(
    "Show unique resources only",
    value=False,
    help="Keeps one row per resource in the main results table."
)

quick_terms = [
    "create", "add", "edit", "update", "search", "get",
    "view", "cancel", "approve", "allocate", "print",
    "export", "import", "manifest", "picklist", "channel",
    "catalog", "shipping", "returns"
]

st.sidebar.markdown("Quick search")
qcols = st.sidebar.columns(2)
for i, term in enumerate(quick_terms):
    if qcols[i % 2].button(term.title(), key=f"quick_{term}"):
        st.session_state["q"] = term
        st.rerun()

query = st.session_state.get("q", query)

# =====================================================
# SEARCH + FILTER
# =====================================================

filtered = search_master(
    master_df,
    query=query,
    source_filter=source_choice,
    access_type_filter=selected_access_types,
)

if selected_resource_names:
    filtered = filtered[filtered["access_resource_name"].isin(selected_resource_names)].reset_index(drop=True)

if only_unique_resources and not filtered.empty:
    filtered = filtered.sort_values(["score", "access_resource_name"], ascending=[False, True]) if "score" in filtered.columns else filtered
    filtered = filtered.drop_duplicates(subset=["access_resource_name", "access_resource_id"], keep="first").reset_index(drop=True)

# =====================================================
# SUMMARY
# =====================================================

c1, c2, c3, c4 = st.columns(4)
c1.metric("Rows", len(filtered))
c2.metric("Unique resources", filtered["access_resource_name"].nunique() if not filtered.empty else 0)
c3.metric("Unique activities", filtered["activity"].nunique() if not filtered.empty else 0)
c4.metric("Unique URLs", filtered["url_pattern"].nunique() if not filtered.empty else 0)

st.divider()

# =====================================================
# RESULTS
# =====================================================

st.subheader("Results")

if filtered.empty:
    st.warning("No matching access resources found. Try another search term or clear some filters.")
else:
    display_cols = [
        "source",
        "access_resource_name",
        "access_resource_id",
        "access_type",
        "activity",
        "url_pattern",
        "tab_name",
        "side_tab_group",
        "resource_name_source",
    ]
    if "score" in filtered.columns:
        display_cols = ["score"] + display_cols

    st.dataframe(
        filtered[display_cols],
        use_container_width=True,
        hide_index=True
    )

    st.markdown("### Focus on one result")

    dropdown_df = filtered.copy()
    dropdown_df["dropdown_label"] = dropdown_df.apply(
        lambda r: f"{r['activity']}  |  {r['access_resource_name']}  |  {r['access_resource_id'] if pd.notna(r['access_resource_id']) else '—'}  |  {r['url_pattern']}",
        axis=1
    )
    dropdown_options = ["All results"] + dropdown_df["dropdown_label"].dropna().tolist()
    chosen = st.selectbox(
        "Choose a result",
        dropdown_options,
        help="Use this to focus on one activity/resource combination without losing the distinction between them."
    )

    focus_df = filtered.copy()
    if chosen != "All results":
        focus_df = focus_df[dropdown_df["dropdown_label"] == chosen].copy()

    if not focus_df.empty:
        row = focus_df.iloc[0]
        col1, col2 = st.columns(2)

        with col1:
            st.write("Access resource name")
            st.code(str(row["access_resource_name"]), language="text")

            st.write("Access resource id")
            st.code("" if pd.isna(row["access_resource_id"]) else str(int(row["access_resource_id"])), language="text")

            st.write("Access type")
            st.code(str(row["access_type"]), language="text")
            st.caption("READ = view/search/get. WRITE = create/update/cancel/approve/allocate and similar actions.")

        with col2:
            st.write("Activity")
            st.code(str(row["activity"]), language="text")

            st.write("URL pattern")
            st.code(str(row["url_pattern"]), language="text")

            if str(row.get("tab_name", "")).strip():
                st.write("Tab name")
                st.code(str(row["tab_name"]), language="text")

            if str(row.get("side_tab_group", "")).strip():
                st.write("Side tab group")
                st.code(str(row["side_tab_group"]), language="text")

        st.info(
            f"Mapping source: {row['resource_name_source']} • "
            f"Source file: {row['source']}"
        )

        if row["source"] == "sidebar mapping":
            st.success("This row comes from the sidebar mapping document and is an exact UI mapping.")
        elif row["resource_name_source"] == "exact":
            st.success("This row has an exact access resource name from the sidebar mapping document.")
        else:
            st.warning("This row uses a best-fit resource name because the sidebar doc did not contain an exact URL match.")

# =====================================================
# GROUPED VIEW
# =====================================================

if show_grouped and not filtered.empty:
    st.subheader("Grouped summary")
    gdf = grouped_summary(filtered)
    st.dataframe(
        gdf,
        use_container_width=True,
        hide_index=True
    )

# =====================================================
# RAW VIEW
# =====================================================

if show_raw:
    with st.expander("Raw merged rows"):
        st.dataframe(master_df, use_container_width=True, hide_index=True)

# =====================================================
# DOWNLOADS
# =====================================================

st.subheader("Downloads")
d1, d2 = st.columns(2)

with d1:
    export_main = filtered.drop(columns=["search_blob"], errors="ignore").to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download filtered results",
        data=export_main,
        file_name="filtered_access_resources.csv",
        mime="text/csv",
        help="Downloads the rows you are currently seeing in the results table."
    )

with d2:
    export_grouped = grouped_summary(filtered).to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download grouped summary",
        data=export_grouped,
        file_name="grouped_access_summary.csv",
        mime="text/csv",
        help="Downloads one line per access resource with URLs grouped together."
    )

st.caption("Built from both the pattern dump and the sidebar mapping document.")
