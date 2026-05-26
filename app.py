import re
from difflib import SequenceMatcher

import pandas as pd
import streamlit as st

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="Uniware Access Resource Auditor",
    layout="wide",
    page_icon="🛡️"
)

st.title("🛡️ Uniware Access Resource Auditor")
st.caption("Search access resources by activity, URL, or resource id")

FILE_PATH = "access_patterns (2).txt"

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
    "system", "layout", "printing", "picklogic", "picker", "packer"
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
    seg = split_camel(seg)
    return seg.title().strip()

def extract_activity(url: str) -> str:
    """
    Last action being performed.
    Example:
      /data/catalog/addTag -> Add Tag
      /data/catalog/get/categories -> Get Categories
      /data/shipping/splitPackage -> Split Package
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

def derive_resource_name(url: str) -> str:
    """
    Human-friendly access resource name.
    This is the system area/resource family, not the last action.
    Example:
      /data/shipping/splitPackage -> Shipping
      /data/oms/returns/reversePickup/create -> OMS Returns
      /admin/system/users -> Admin System
      /admin/layout/shelfTypes -> Admin Layout
    """
    u = normalize_text(url)

    if u.startswith("/admin/"):
        parts = [p for p in u.strip("/").split("/") if p]
        if len(parts) >= 2:
            return f"Admin {titleize_segment(parts[1])}"
        return "Admin"

    if "/oms/returns/" in u:
        return "OMS Returns"
    if "/oms/shipment/" in u:
        return "OMS Shipping"
    if "/oms/picker/" in u:
        return "OMS Picking"
    if "/oms/packer/" in u:
        return "OMS Packing"
    if "/oms/" in u:
        return "OMS"

    if "/shipping" in u:
        return "Shipping"
    if "/returns" in u:
        return "Returns"
    if "/reports" in u:
        return "Reports"
    if "/procure" in u or "/po/" in u:
        return "Procurement"
    if "/inflow" in u:
        return "Inflow"
    if "/putaway" in u:
        return "Putaway"
    if "/catalog" in u or "/products" in u:
        return "Catalog"
    if "/tasks" in u:
        return "Tasks"
    if "/material" in u:
        return "Material"

    parts = [p for p in u.strip("/").split("/") if p]
    return titleize_segment(parts[0]) if parts else "Other"

def access_type(url: str) -> str:
    u = normalize_text(url)
    write_words = [
        "create", "add", "edit", "update", "remove", "delete", "cancel",
        "approve", "allocate", "discard", "assign", "close", "open",
        "complete", "receive", "reject", "hold", "unhold", "upload",
        "download", "save", "submit", "import", "export"
    ]
    return "WRITE" if any(w in u for w in write_words) else "READ"

def resource_label(resource_name: str, resource_id: int) -> str:
    return f"{resource_name} ({resource_id})"

def build_search_blob(df: pd.DataFrame) -> pd.Series:
    return (
        df["access_resource_id"].astype(str) + " " +
        df["resource_name"].astype(str) + " " +
        df["url_pattern"].astype(str) + " " +
        df["activity"].astype(str) + " " +
        df["access_type"].astype(str) + " " +
        df["combined_label"].astype(str)
    ).str.lower()

@st.cache_data
def load_data(file_path: str) -> pd.DataFrame:
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            raw = f.read()
    except FileNotFoundError:
        st.error(f"File not found: {file_path}")
        st.stop()
    except Exception as e:
        st.error(f"Could not read file: {e}")
        st.stop()

    rows = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or "|" not in line or line.startswith("+---"):
            continue

        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) < 3:
            continue

        if parts[0].lower() == "id":
            continue

        if not parts[0].isdigit() or not parts[1].isdigit():
            continue

        url = parts[2].strip()
        if not url.startswith("/"):
            continue

        rid = int(parts[1])
        rows.append(
            {
                "id": int(parts[0]),
                "access_resource_id": rid,
                "url_pattern": url,
                "created": parts[3].strip() if len(parts) > 3 else "",
                "updated": parts[4].strip() if len(parts) > 4 else "",
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df["activity"] = df["url_pattern"].apply(extract_activity)
    df["resource_name"] = df["url_pattern"].apply(derive_resource_name)
    df["access_type"] = df["url_pattern"].apply(access_type)
    df["combined_label"] = df.apply(
        lambda r: f"{r['activity']} | {r['resource_name']} | ID {r['access_resource_id']}",
        axis=1
    )
    df["search_blob"] = build_search_blob(df)

    return df.drop_duplicates(subset=["access_resource_id", "url_pattern"]).reset_index(drop=True)

def score_match(query: str, row: pd.Series) -> float:
    q = normalize_text(query)
    if not q:
        return 0.0

    score = 0.0
    rid = str(row["access_resource_id"])
    url = normalize_text(row["url_pattern"])
    activity = normalize_text(row["activity"])
    resource_name = normalize_text(row["resource_name"])
    combined = normalize_text(row["combined_label"])

    if q == rid:
        score += 100
    if q in url:
        score += 95
    if q in activity:
        score += 85
    if q in resource_name:
        score += 80
    if q in combined:
        score += 70

    score += SequenceMatcher(None, q, combined).ratio() * 25
    score += SequenceMatcher(None, q, url).ratio() * 20
    score += SequenceMatcher(None, q, activity).ratio() * 20

    for token in q.split():
        if token in combined:
            score += 6

    return score

def search_access(query: str, df: pd.DataFrame) -> pd.DataFrame:
    q = normalize_text(query)
    if not q:
        return pd.DataFrame()

    out = []
    for _, row in df.iterrows():
        score = score_match(q, row)
        if score >= 20:
            out.append(
                {
                    "confidence": round(min(score, 100.0), 1),
                    "access_resource_id": row["access_resource_id"],
                    "resource_name": row["resource_name"],
                    "activity": row["activity"],
                    "access_type": row["access_type"],
                    "url_pattern": row["url_pattern"],
                    "combined_label": row["combined_label"],
                    "created": row["created"],
                    "updated": row["updated"],
                }
            )

    if not out:
        return pd.DataFrame()

    result = pd.DataFrame(out)
    result = result.sort_values(["confidence", "access_resource_id"], ascending=[False, True])

    # keep related URL patterns together, but still readable
    grouped = (
        result.groupby(["access_resource_id", "resource_name"], as_index=False)
        .agg(
            confidence=("confidence", "max"),
            activity=("activity", lambda s: " • ".join(sorted(set(map(str, s))))),
            access_type=("access_type", lambda s: " / ".join(sorted(set(map(str, s))))),
            pattern_count=("url_pattern", "nunique"),
            url_patterns=("url_pattern", lambda s: list(sorted(set(map(str, s))))),
            combined_label=("combined_label", lambda s: " • ".join(sorted(set(map(str, s))))),
            created=("created", lambda s: " / ".join(sorted(set(map(str, s))))),
            updated=("updated", lambda s: " / ".join(sorted(set(map(str, s))))),
        )
        .sort_values(["confidence", "pattern_count"], ascending=[False, False])
        .reset_index(drop=True)
    )

    return grouped

def grouped_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    return (
        df.groupby(["access_resource_id", "resource_name", "access_type"], as_index=False)
        .agg(
            activities=("activity", lambda s: " • ".join(sorted(set(map(str, s))))),
            url_patterns=("url_pattern", lambda s: " • ".join(sorted(set(map(str, s))))),
            pattern_count=("url_pattern", "nunique"),
        )
        .sort_values(["access_resource_id"])
        .reset_index(drop=True)
    )

# =====================================================
# LOAD DATA
# =====================================================

df = load_data(FILE_PATH)

if df.empty:
    st.error("No valid rows were found in the access pattern file.")
    st.stop()

# =====================================================
# SIDEBAR
# =====================================================

st.sidebar.header("Search")

search_query = st.sidebar.text_input(
    "Search",
    placeholder="Try: create tag, split package, shipping, 36",
    help="Search by activity, access resource name, URL, or resource id."
)

access_types_all = sorted(df["access_type"].dropna().unique().tolist())
selected_access_types = st.sidebar.multiselect(
    "Access type",
    access_types_all,
    default=access_types_all,
    help="READ means view/search/get. WRITE means create/update/cancel/allocate and other change actions."
)

show_resource_filter = st.sidebar.checkbox(
    "Show access resource filter",
    value=False,
    help="Turn this on only if you want to filter directly by access resource name."
)

resource_names_all = sorted(df["resource_name"].dropna().unique().tolist())
selected_resources = resource_names_all
if show_resource_filter:
    selected_resources = st.sidebar.multiselect(
        "Access resource name",
        resource_names_all,
        default=resource_names_all,
        help="Filter by the access resource family, such as Shipping, Returns, Admin System, or OMS Returns."
    )

show_grouped = st.sidebar.checkbox(
    "Show grouped resource view",
    value=True,
    help="Shows one line per access resource with all related URL patterns grouped together."
)

show_raw = st.sidebar.checkbox(
    "Show raw rows",
    value=False,
    help="Shows the underlying rows from the source file."
)

only_unique_resources = st.sidebar.checkbox(
    "Show unique resources only",
    value=False,
    help="Keeps one row per access resource in the main result table."
)

# =====================================================
# FILTER DATA
# =====================================================

filtered_df = df.copy()

if selected_access_types:
    filtered_df = filtered_df[filtered_df["access_type"].isin(selected_access_types)]

if selected_resources:
    filtered_df = filtered_df[filtered_df["resource_name"].isin(selected_resources)]

if search_query.strip():
    q = normalize_text(search_query)
    filtered_df = filtered_df[
        filtered_df["search_blob"].str.contains(re.escape(q), na=False) |
        filtered_df["access_resource_id"].astype(str).eq(q)
    ]

# =====================================================
# MAIN AREA
# =====================================================

st.subheader("Choose one result")

activity_options = ["All results"] + sorted(filtered_df["combined_label"].dropna().unique().tolist())
selected_item = st.selectbox(
    "Result dropdown",
    activity_options,
    help="This dropdown keeps activity and access resource together but still distinct, for example: Split Package | Shipping | ID 36."
)

display_df = filtered_df.copy()
if selected_item != "All results":
    display_df = display_df[display_df["combined_label"] == selected_item]

if only_unique_resources:
    display_df = display_df.drop_duplicates(subset=["access_resource_id"]).reset_index(drop=True)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Rows", len(display_df))
c2.metric("Unique resources", display_df["access_resource_id"].nunique() if not display_df.empty else 0)
c3.metric("Unique activities", display_df["activity"].nunique() if not display_df.empty else 0)
c4.metric("URL patterns", display_df["url_pattern"].nunique() if not display_df.empty else 0)

st.divider()

# =====================================================
# RESULTS
# =====================================================

st.subheader("Results")

if display_df.empty:
    st.warning("No matching access resources found. Try another search term or clear some filters.")
else:
    st.dataframe(
        display_df[[
            "access_resource_id",
            "resource_name",
            "access_type",
            "activity",
            "url_pattern"
        ]],
        use_container_width=True,
        hide_index=True
    )

    st.markdown("### Focus on one access resource")

    focus_options = sorted(display_df["access_resource_id"].unique().tolist())
    selected_resource = st.selectbox(
        "Access resource id",
        focus_options,
        help="Select one resource id to see the access resource name, its activity, and its URL mappings."
    )

    resource_df = display_df[display_df["access_resource_id"] == selected_resource]

    if not resource_df.empty:
        row = resource_df.iloc[0]

        col1, col2 = st.columns(2)

        with col1:
            st.write("Access resource")
            st.code(f"{row['resource_name']} ({row['access_resource_id']})", language="text")

            st.write("Access type")
            st.code(row["access_type"], language="text")
            st.caption("READ = mostly viewing/searching/getting data. WRITE = creates or changes data.")

            st.write("Activity")
            st.code(row["activity"], language="text")

        with col2:
            st.write("URL mappings")
            for u in resource_df["url_pattern"].drop_duplicates().tolist():
                st.code(u, language="text")

        st.info(
            "The access resource name is the system area or permission family, while the activity is the actual action being performed."
        )

# =====================================================
# GROUPED VIEW
# =====================================================

if show_grouped and not display_df.empty:
    st.subheader("Grouped resource summary")

    grouped_df = grouped_summary(display_df)

    st.dataframe(
        grouped_df[[
            "access_resource_id",
            "resource_name",
            "access_type",
            "pattern_count"
        ]],
        use_container_width=True,
        hide_index=True
    )

# =====================================================
# RAW DATA
# =====================================================

if show_raw:
    with st.expander("Raw rows"):
        st.dataframe(display_df, use_container_width=True, hide_index=True)

# =====================================================
# DOWNLOADS
# =====================================================

st.subheader("Downloads")

export_col1, export_col2 = st.columns(2)

with export_col1:
    csv_main = display_df.drop(columns=["search_blob"], errors="ignore").to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download filtered access map",
        data=csv_main,
        file_name="filtered_access_map.csv",
        mime="text/csv",
        help="Downloads the rows currently visible in the main result table."
    )

with export_col2:
    grouped_csv = grouped_summary(display_df).to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download grouped resource summary",
        data=grouped_csv,
        file_name="grouped_resource_summary.csv",
        mime="text/csv",
        help="Downloads one row per access resource with all related URL patterns grouped together."
    )

st.caption("Built for fast access lookup, debugging, mapping, and request support.")
