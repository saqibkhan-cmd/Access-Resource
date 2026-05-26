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
    "upload", "download", "discard", "save", "submit"
]

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

def extract_activity(url: str) -> str:
    url = str(url).strip()
    parts = [p for p in url.strip("/").split("/") if p]
    if not parts:
        return "Root"

    system_words = {
        "data", "admin", "oms", "catalog", "reports", "procure",
        "shipping", "returns", "tasks", "putaway", "inflow", "material"
    }

    for idx in range(len(parts) - 1, -1, -1):
        seg = split_camel(parts[idx])
        low = seg.lower()

        for verb in VERBS:
            if low == verb:
                if idx + 1 < len(parts):
                    tail = split_camel(parts[idx + 1])
                    if tail and tail.lower() not in system_words:
                        return f"{verb.title()} {tail.title()}"
                return verb.title()

            if low.startswith(verb):
                tail = seg[len(verb):].strip()
                tail = re.sub(r"^[-_/ ]+", "", tail)
                tail = split_camel(tail)
                if tail:
                    return f"{verb.title()} {tail.title()}"
                if idx + 1 < len(parts):
                    tail2 = split_camel(parts[idx + 1])
                    if tail2 and tail2.lower() not in system_words:
                        return f"{verb.title()} {tail2.title()}"
                return verb.title()

    return split_camel(parts[-1]).title()

def access_type(url: str) -> str:
    u = normalize_text(url)
    write_words = [
        "create", "add", "edit", "update", "remove", "delete", "cancel",
        "approve", "allocate", "discard", "assign", "close", "open",
        "complete", "receive", "reject", "hold", "unhold", "upload",
        "download", "save", "submit", "import", "export"
    ]
    return "WRITE" if any(w in u for w in write_words) else "READ"

def derive_module(url: str) -> str:
    u = normalize_text(url)
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
    if "/admin" in u:
        return "Admin"
    if "/catalog" in u or "/products" in u:
        return "Catalog"
    if "/tasks" in u:
        return "Tasks"
    if "/material" in u:
        return "Material"
    return "Other"

def resource_label(resource_id) -> str:
    return f"Access Resource {resource_id}"

def score_match(query: str, activity: str, url: str, resource_id: int) -> float:
    q = normalize_text(query)
    a = normalize_text(activity)
    u = normalize_text(url)
    rid = str(resource_id)

    if not q:
        return 0.0

    score = 0.0
    if q == rid:
        score += 100
    if q in u:
        score += 90
    if q in a:
        score += 70
    if a in q:
        score += 35

    score += SequenceMatcher(None, q, u).ratio() * 30
    score += SequenceMatcher(None, q, a).ratio() * 25

    for token in q.split():
        if token in u or token in a:
            score += 6

    return score

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

    df["activity"] = df["url_pattern"].apply(extract_activity)
    df["access_type"] = df["url_pattern"].apply(access_type)
    df["module"] = df["url_pattern"].apply(derive_module)
    df["resource_label"] = df["access_resource_id"].apply(resource_label)
    df["search_blob"] = (
        df["access_resource_id"].astype(str) + " " +
        df["url_pattern"].astype(str) + " " +
        df["activity"].astype(str) + " " +
        df["access_type"].astype(str)
    ).str.lower()

    return df.drop_duplicates(subset=["access_resource_id", "url_pattern"]).reset_index(drop=True)

def filter_df(df: pd.DataFrame, query: str, access_types, modules) -> pd.DataFrame:
    out = df.copy()

    if query.strip():
        q = normalize_text(query)
        mask = out["search_blob"].apply(
            lambda x: q in x or score_match(q, x, x, 0) > 0
        )
        out = out[mask]

    if access_types:
        out = out[out["access_type"].isin(access_types)]

    if modules:
        out = out[out["module"].isin(modules)]

    return out

def grouped_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    return (
        df.groupby(["access_resource_id", "resource_label", "access_type"], as_index=False)
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
    placeholder="Type activity, URL, or resource id",
    help="Search by a word like 'create', 'add tag', '/data/catalog/addTag', or '459'."
)

access_types_all = sorted(df["access_type"].dropna().unique().tolist())
selected_access_types = st.sidebar.multiselect(
    "Access type",
    access_types_all,
    default=access_types_all,
    help="Choose whether you want READ, WRITE, or both."
)

modules_all = sorted(df["module"].dropna().unique().tolist())
show_module_filter = st.sidebar.checkbox(
    "Show module filter",
    value=False,
    help="Turn this on only if you want to narrow results by module like OMS, Shipping, or Catalog."
)
selected_modules = modules_all
if show_module_filter:
    selected_modules = st.sidebar.multiselect(
        "Module",
        modules_all,
        default=modules_all,
        help="Optional filter for advanced narrowing."
    )

show_grouped = st.sidebar.checkbox(
    "Show grouped resource view",
    value=True,
    help="Shows one row per access resource so you can quickly understand which URLs belong together."
)

show_raw = st.sidebar.checkbox(
    "Show raw rows",
    value=False,
    help="Shows the underlying rows from the source file."
)

only_unique_resources = st.sidebar.checkbox(
    "Show unique resources only",
    value=False,
    help="Removes duplicate rows and keeps one row per access resource in the main result table."
)

# =====================================================
# FILTER DATA
# =====================================================

filtered_df = filter_df(df, search_query, selected_access_types, selected_modules)

# =====================================================
# MAIN AREA
# =====================================================

st.subheader("Activity dropdown")

activity_options = ["All activities"] + sorted(filtered_df["activity"].dropna().unique().tolist())
selected_activity = st.selectbox(
    "Choose an activity",
    activity_options,
    help="Use this dropdown to focus on one activity like 'Add Tag', 'Create Manifest', or 'Cancel Order'."
)

activity_df = filtered_df.copy()
if selected_activity != "All activities":
    activity_df = activity_df[activity_df["activity"] == selected_activity]

if only_unique_resources:
    activity_df = activity_df.drop_duplicates(subset=["access_resource_id"]).reset_index(drop=True)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Rows", len(activity_df))
c2.metric("Unique resources", activity_df["access_resource_id"].nunique() if not activity_df.empty else 0)
c3.metric("Unique activities", activity_df["activity"].nunique() if not activity_df.empty else 0)
c4.metric("URL patterns", activity_df["url_pattern"].nunique() if not activity_df.empty else 0)

st.divider()

# =====================================================
# RESULTS
# =====================================================

st.subheader("Results")

if activity_df.empty:
    st.warning("No matching access resources found. Try a different search or activity.")
else:
    view_df = activity_df[[
        "access_resource_id",
        "access_type",
        "activity",
        "url_pattern"
    ]].copy()

    st.dataframe(
        view_df,
        use_container_width=True,
        hide_index=True
    )

    st.markdown("### Focus on one resource")

    focus_options = sorted(activity_df["access_resource_id"].unique().tolist())
    selected_resource = st.selectbox(
        "Access resource id",
        focus_options,
        help="Select one resource id to see its related URL patterns and exact mapping."
    )

    resource_df = activity_df[activity_df["access_resource_id"] == selected_resource]

    if not resource_df.empty:
        row = resource_df.iloc[0]

        col1, col2 = st.columns(2)

        with col1:
            st.write("Access resource")
            st.code(f"{row['resource_label']} ({row['access_resource_id']})")

            st.write("Access type")
            st.code(row["access_type"])

            st.write("Activity")
            st.code(row["activity"])

        with col2:
            st.write("URL mappings")
            for u in resource_df["url_pattern"].drop_duplicates().tolist():
                st.code(u)

        st.write("Why this matters")
        st.info(
            "This section keeps the access resource, access type, activity, and URL mapping together so the combination stays easy to read."
        )

# =====================================================
# GROUPED VIEW
# =====================================================

if show_grouped and not activity_df.empty:
    st.subheader("Grouped resource summary")
    grouped_df = grouped_summary(activity_df)

    st.dataframe(
        grouped_df[[
            "access_resource_id",
            "resource_label",
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
        st.dataframe(activity_df, use_container_width=True, hide_index=True)

# =====================================================
# DOWNLOADS
# =====================================================

st.subheader("Downloads")

export_col1, export_col2 = st.columns(2)

with export_col1:
    csv_main = activity_df.drop(columns=["search_blob"], errors="ignore").to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download filtered access map",
        data=csv_main,
        file_name="filtered_access_map.csv",
        mime="text/csv",
        help="Downloads the rows currently visible in the main result table."
    )

with export_col2:
    grouped_csv = grouped_summary(activity_df).to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download grouped resource summary",
        data=grouped_csv,
        file_name="grouped_resource_summary.csv",
        mime="text/csv",
        help="Downloads one row per access resource with all related URL patterns grouped together."
    )

st.caption("Built for fast access lookup, debugging, mapping, and request support.")
