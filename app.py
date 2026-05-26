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

# =====================================================
# FILE PATH
# =====================================================

FILE_PATH = "access_patterns (2).txt"

# =====================================================
# CONSTANTS
# =====================================================

VERBS = [
    "create", "add", "edit", "update", "remove", "delete", "cancel",
    "approve", "search", "fetch", "get", "view", "show", "print",
    "preview", "export", "import", "assign", "allocate", "open",
    "close", "complete", "receive", "reject", "hold", "unhold",
    "upload", "download", "discard", "save", "submit"
]

SYNONYMS = {
    "create": ["create", "add", "new", "make"],
    "add": ["add", "create", "new"],
    "remove": ["remove", "delete", "discard"],
    "delete": ["delete", "remove", "discard"],
    "view": ["view", "get", "fetch", "show", "search", "list"],
    "search": ["search", "find", "lookup", "fetch"],
    "update": ["update", "edit", "modify"],
    "edit": ["edit", "update", "modify"],
    "print": ["print", "preview", "pdf"],
    "export": ["export", "download"],
    "import": ["import", "upload"],
    "cancel": ["cancel", "void"],
    "approve": ["approve", "authorize", "confirm"],
    "allocate": ["allocate", "assign"],
}

DEFAULT_RULES = pd.DataFrame(
    [
        {"keyword": "add", "friendly_activity": "Add", "access_type_hint": "WRITE", "enabled": True, "priority": 3},
        {"keyword": "create", "friendly_activity": "Create", "access_type_hint": "WRITE", "enabled": True, "priority": 3},
        {"keyword": "update", "friendly_activity": "Update", "access_type_hint": "WRITE", "enabled": True, "priority": 3},
        {"keyword": "edit", "friendly_activity": "Edit", "access_type_hint": "WRITE", "enabled": True, "priority": 3},
        {"keyword": "remove", "friendly_activity": "Remove", "access_type_hint": "WRITE", "enabled": True, "priority": 3},
        {"keyword": "delete", "friendly_activity": "Delete", "access_type_hint": "WRITE", "enabled": True, "priority": 3},
        {"keyword": "search", "friendly_activity": "Search", "access_type_hint": "READ", "enabled": True, "priority": 2},
        {"keyword": "fetch", "friendly_activity": "Fetch", "access_type_hint": "READ", "enabled": True, "priority": 2},
        {"keyword": "get", "friendly_activity": "Get", "access_type_hint": "READ", "enabled": True, "priority": 2},
        {"keyword": "print", "friendly_activity": "Print", "access_type_hint": "READ", "enabled": True, "priority": 2},
        {"keyword": "manifest", "friendly_activity": "Manifest", "access_type_hint": "WRITE", "enabled": True, "priority": 2},
        {"keyword": "picklist", "friendly_activity": "Picklist", "access_type_hint": "WRITE", "enabled": True, "priority": 2},
    ]
)

# =====================================================
# SESSION STATE
# =====================================================

if "rules_df" not in st.session_state:
    st.session_state.rules_df = DEFAULT_RULES.copy()

if "favorites" not in st.session_state:
    st.session_state.favorites = []

# =====================================================
# HELPERS
# =====================================================

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

def humanize_url(url: str) -> str:
    url = str(url).strip().strip("/")
    if not url:
        return "Root"
    return " / ".join(split_camel(part).title() for part in url.split("/") if part)

def extract_activity(url: str) -> str:
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
                    tail = split_camel(parts[idx + 1])
                    if tail and tail.lower() not in {"data", "admin", "oms", "catalog", "reports", "procure", "shipping", "returns", "tasks", "putaway", "inflow", "material"}:
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
                    if tail2 and tail2.lower() not in {"data", "admin", "oms", "catalog", "reports", "procure", "shipping", "returns", "tasks", "putaway", "inflow", "material"}:
                        return f"{verb.title()} {tail2.title()}"
                return verb.title()

    return split_camel(parts[-1]).title()

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

def access_type(url: str) -> str:
    u = normalize_text(url)
    write_words = [
        "create", "add", "edit", "update", "remove", "delete", "cancel",
        "approve", "allocate", "discard", "assign", "close", "open",
        "complete", "receive", "reject", "hold", "unhold", "upload",
        "download", "save", "submit", "import", "export"
    ]
    return "WRITE" if any(w in u for w in write_words) else "READ"

def resource_label(resource_id) -> str:
    return f"Access Resource {resource_id}"

def make_search_blob(df: pd.DataFrame) -> pd.Series:
    return (
        df["access_resource_id"].astype(str) + " " +
        df["url_pattern"].astype(str) + " " +
        df["activity"].astype(str) + " " +
        df["module"].astype(str) + " " +
        df["access_type"].astype(str)
    ).str.lower()

@st.cache_data
def parse_access_file(file_path: str) -> pd.DataFrame:
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
        if not line or line.startswith("+---") or "|" not in line:
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

    df["module"] = df["url_pattern"].apply(derive_module)
    df["activity"] = df["url_pattern"].apply(extract_activity)
    df["activity_type"] = df["activity"].apply(lambda x: str(x).split()[0].title() if str(x).split() else "Other")
    df["access_type"] = df["url_pattern"].apply(access_type)
    df["resource_label"] = df["access_resource_id"].apply(resource_label)
    df["search_blob"] = make_search_blob(df)
    df = df.drop_duplicates(subset=["access_resource_id", "url_pattern"]).reset_index(drop=True)
    return df

def expand_query_tokens(query: str) -> list[str]:
    tokens = re.findall(r"[a-zA-Z0-9]+", normalize_text(query))
    expanded = []
    for token in tokens:
        expanded.extend(SYNONYMS.get(token, [token]))
    seen = set()
    out = []
    for t in expanded:
        if t not in seen:
            out.append(t)
            seen.add(t)
    return out

def safe_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, str(a), str(b)).ratio()

def rule_boost(row: pd.Series, rules_df: pd.DataFrame) -> tuple[int, str | None]:
    blob = normalize_text(f"{row['url_pattern']} {row['activity']} {row['module']} {row['access_resource_id']}")
    best_label = None
    best_priority = -1
    boost = 0

    for _, rule in rules_df.iterrows():
        if not bool(rule.get("enabled", True)):
            continue
        keyword = normalize_text(rule.get("keyword", ""))
        if not keyword:
            continue

        if keyword in blob:
            priority = int(rule.get("priority", 1) or 1)
            boost += priority * 4
            if priority > best_priority and str(rule.get("friendly_activity", "")).strip():
                best_priority = priority
                best_label = str(rule.get("friendly_activity")).strip()

    return boost, best_label

def score_row(query: str, row: pd.Series, rules_df: pd.DataFrame) -> tuple[float, str]:
    q = normalize_text(query)
    blob = row["search_blob"]

    score = 0.0
    if not q:
        return 0.0, row["activity"]

    if q == str(row["access_resource_id"]):
        score += 90

    if q in row["url_pattern"].lower():
        score += 85

    if q in blob:
        score += 30

    score += safe_ratio(q, blob) * 45

    q_tokens = expand_query_tokens(q)
    for token in q_tokens:
        if token in blob:
            score += 7

    if q in row["activity"].lower() or row["activity"].lower() in q:
        score += 20

    if q in row["module"].lower():
        score += 10

    rb, label_override = rule_boost(row, rules_df)
    score += rb

    if row["access_type"] == "WRITE":
        score += 2

    label = label_override or row["activity"]
    return min(score, 100.0), label

def search_access(query: str, df: pd.DataFrame, rules_df: pd.DataFrame) -> pd.DataFrame:
    q = normalize_text(query)
    if not q:
        return pd.DataFrame()

    matched = []
    for _, row in df.iterrows():
        score, label = score_row(q, row, rules_df)
        if score >= 20:
            matched.append(
                {
                    "confidence": round(score, 1),
                    "access_resource_id": row["access_resource_id"],
                    "resource_label": row["resource_label"],
                    "activity": label,
                    "access_type": row["access_type"],
                    "module": row["module"],
                    "url_pattern": row["url_pattern"],
                    "created": row["created"],
                    "updated": row["updated"],
                }
            )

    if not matched:
        return pd.DataFrame()

    raw = pd.DataFrame(matched)

    grouped = (
        raw.groupby(["access_resource_id", "resource_label"], as_index=False)
        .agg(
            confidence=("confidence", "max"),
            activity=("activity", lambda s: " • ".join(sorted(set(map(str, s))))),
            access_type=("access_type", lambda s: " / ".join(sorted(set(map(str, s))))),
            module=("module", lambda s: " / ".join(sorted(set(map(str, s))))),
            pattern_count=("url_pattern", "nunique"),
            url_patterns=("url_pattern", lambda s: list(sorted(set(map(str, s))))),
            created=("created", lambda s: " / ".join(sorted(set(map(str, s))))),
            updated=("updated", lambda s: " / ".join(sorted(set(map(str, s))))),
        )
        .sort_values(["confidence", "pattern_count"], ascending=[False, False])
        .reset_index(drop=True)
    )

    return grouped

def overlap_map(filtered_df: pd.DataFrame) -> pd.DataFrame:
    if filtered_df.empty:
        return pd.DataFrame()

    return (
        filtered_df.groupby(["activity", "access_resource_id"], as_index=False)
        .agg(url_count=("url_pattern", "nunique"))
    )

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

def build_request_text(activity: str, missing_resources: list[int], missing_df: pd.DataFrame) -> str:
    if not missing_resources:
        return f"No additional access is required for: {activity}"

    lines = [f"Please provide the following access for activity: {activity}", ""]
    for rid in missing_resources:
        row = missing_df[missing_df["access_resource_id"] == rid].head(1)
        if row.empty:
            lines.append(f"- Access Resource {rid}")
        else:
            r = row.iloc[0]
            lines.append(f"- {r['resource_label']} ({rid})")
            lines.append(f"  Helps with: {r['activity']}")
            lines.append(f"  URL: {r['url_pattern']}")
    return "\n".join(lines)

# =====================================================
# LOAD DATA
# =====================================================

df = parse_access_file(FILE_PATH)

if df.empty:
    st.error("No valid rows were found in the access pattern file.")
    st.stop()

# =====================================================
# SIDEBAR
# =====================================================

st.sidebar.header("Search")

search_query = st.sidebar.text_input(
    "Search by activity, URL, or resource id",
    placeholder="Try: create tag, add customer, /data/catalog/addTag, 459"
)

quick_terms = [
    "create", "add", "edit", "update", "search", "get",
    "view", "cancel", "approve", "allocate", "print",
    "export", "import", "manifest", "picklist"
]

st.sidebar.markdown("Quick search")
qcols = st.sidebar.columns(2)
for i, term in enumerate(quick_terms):
    if qcols[i % 2].button(term.title(), key=f"quick_{term}"):
        st.session_state["search_query"] = term
        st.rerun()

search_query = st.session_state.get("search_query", search_query)

st.sidebar.header("Filters")
access_type_options = sorted(df["access_type"].dropna().unique().tolist())
selected_access_types = st.sidebar.multiselect(
    "Access type",
    access_type_options,
    default=access_type_options
)

module_options = sorted(df["module"].dropna().unique().tolist())
show_module_filter = st.sidebar.checkbox("Show module filter", value=False)
selected_modules = module_options
if show_module_filter:
    selected_modules = st.sidebar.multiselect(
        "Module",
        module_options,
        default=module_options
    )

activity_type_options = sorted(df["activity_type"].dropna().unique().tolist())
show_activity_type_filter = st.sidebar.checkbox("Show activity-type filter", value=False)
selected_activity_types = activity_type_options
if show_activity_type_filter:
    selected_activity_types = st.sidebar.multiselect(
        "Activity type",
        activity_type_options,
        default=activity_type_options
    )

show_grouped = st.sidebar.checkbox("Grouped resource view", value=True)
show_raw = st.sidebar.checkbox("Show raw rows", value=False)
only_unique_resources = st.sidebar.checkbox("Show unique resources only", value=False)

st.sidebar.header("Favorites")
favorites = st.session_state.favorites
if favorites:
    favorite_pick = st.sidebar.selectbox("Saved activities", [""] + favorites)
    if favorite_pick and st.sidebar.button("Search favorite"):
        st.session_state["search_query"] = favorite_pick
        st.rerun()
else:
    st.sidebar.caption("No saved favorites yet.")

# =====================================================
# TABS
# =====================================================

tab_search, tab_compare, tab_manage = st.tabs(["Search", "Compare", "Rules & Downloads"])

# =====================================================
# SEARCH TAB
# =====================================================

with tab_search:
    st.subheader("Search results")

    query = search_query.strip()

    filtered_df = df.copy()
    if selected_access_types:
        filtered_df = filtered_df[filtered_df["access_type"].isin(selected_access_types)]
    if selected_modules:
        filtered_df = filtered_df[filtered_df["module"].isin(selected_modules)]
    if selected_activity_types:
        filtered_df = filtered_df[filtered_df["activity_type"].isin(selected_activity_types)]

    results = search_access(query, filtered_df, st.session_state.rules_df) if query else pd.DataFrame()

    if only_unique_resources and not results.empty:
        results = results.drop_duplicates(subset=["access_resource_id"]).reset_index(drop=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rows", len(filtered_df))
    c2.metric("Matches", len(results))
    c3.metric("Unique resources", results["access_resource_id"].nunique() if not results.empty else 0)
    c4.metric("Unique activities", results["activity"].nunique() if not results.empty else 0)

    if query and results.empty:
        st.warning("No matches found. Try a shorter query or a different keyword.")
    elif query:
        st.dataframe(
            results[["confidence", "access_resource_id", "resource_label", "activity", "access_type", "pattern_count"]],
            use_container_width=True,
            hide_index=True
        )

        if not results.empty:
            st.markdown("### Details")

            activity_filter_choice = st.selectbox(
                "Focus on one result",
                results["activity"].tolist()
            )

            focus_row = results[results["activity"] == activity_filter_choice].head(1)
            if not focus_row.empty:
                r = focus_row.iloc[0]
                rid = int(r["access_resource_id"])

                with st.expander(f"{r['resource_label']} · {rid}"):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.write("What this access helps with")
                        st.write(r["activity"])

                        st.write("Access type")
                        st.write(r["access_type"])

                        st.write("Confidence")
                        st.write(f"{r['confidence']} / 100")

                    with col2:
                        st.write("Related URL patterns")
                        for u in r["url_patterns"]:
                            st.code(u)

                    overlaps = overlap_map(filtered_df)
                    same_activity = overlaps[overlaps["activity"] == r["activity"]]
                    other_resources = same_activity[same_activity["access_resource_id"] != rid]["access_resource_id"].tolist()

                    st.write("Overlap check")
                    if other_resources:
                        st.info(
                            "This activity is also seen under other resources: "
                            + ", ".join(map(str, sorted(set(other_resources))))
                        )
                    else:
                        st.success("No overlap detected for this activity in the current filtered set.")

                st.markdown("### Missing access checker")
                granted = st.multiselect(
                    "Resources already available to the user",
                    options=sorted(df["access_resource_id"].unique().tolist()),
                    default=[]
                )

                recommended_ids = results["access_resource_id"].head(5).tolist()
                missing_ids = [x for x in recommended_ids if x not in granted]

                left, right = st.columns(2)
                with left:
                    st.write("Recommended resources")
                    st.write(", ".join(map(str, recommended_ids)) if recommended_ids else "None")

                with right:
                    st.write("Missing resources")
                    st.write(", ".join(map(str, missing_ids)) if missing_ids else "None")

                if st.button("Save this search to favorites"):
                    if query not in st.session_state.favorites:
                        st.session_state.favorites.append(query)
                        st.success("Saved to favorites.")
                    else:
                        st.info("Already saved.")

                request_text = build_request_text(
                    activity=query,
                    missing_resources=missing_ids,
                    missing_df=filtered_df
                )
                st.text_area("Access request helper", value=request_text, height=220)

    if show_grouped and not filtered_df.empty:
        st.markdown("### Resource combinations")
        grouped_df = grouped_summary(filtered_df)
        st.dataframe(
            grouped_df[["access_resource_id", "resource_label", "access_type", "pattern_count"]],
            use_container_width=True,
            hide_index=True
        )

        for _, row in grouped_df.head(20).iterrows():
            with st.expander(f"{row['resource_label']} · {row['access_type']} · {row['pattern_count']} pattern(s)"):
                st.write("Activities")
                st.write(row["activities"])

                st.write("URL patterns")
                st.write(row["url_patterns"])

                st.write("Typical debug helper")
                st.write(f"This resource usually supports: {row['activities']}")

    if show_raw:
        st.markdown("### Raw rows")
        st.dataframe(filtered_df, use_container_width=True, hide_index=True)

# =====================================================
# COMPARE TAB
# =====================================================

with tab_compare:
    st.subheader("Bulk compare")

    bulk_text = st.text_area(
        "Enter one activity per line",
        placeholder="create tag\nadd customer\ncancel order\nshipment manifest",
        height=160
    )

    if st.button("Compare activities"):
        activities = [x.strip() for x in bulk_text.splitlines() if x.strip()]
        if not activities:
            st.warning("Add at least one activity.")
        else:
            rows = []
            matched_sets = []

            for act in activities:
                res = search_access(act, df, st.session_state.rules_df)
                if res.empty:
                    rows.append(
                        {
                            "Activity": act,
                            "Top resources": "",
                            "Top confidence": 0,
                            "Top activity label": "",
                        }
                    )
                    matched_sets.append(set())
                else:
                    top = res.head(5)
                    ids = top["access_resource_id"].tolist()
                    matched_sets.append(set(ids))
                    rows.append(
                        {
                            "Activity": act,
                            "Top resources": ", ".join(map(str, ids)),
                            "Top confidence": float(top["confidence"].max()),
                            "Top activity label": top.iloc[0]["activity"],
                        }
                    )

            compare_df = pd.DataFrame(rows)
            st.dataframe(compare_df, use_container_width=True, hide_index=True)

            if len(matched_sets) > 1:
                common = set.intersection(*matched_sets) if all(matched_sets) else set()
                st.write("Common resources across all activities")
                st.write(", ".join(map(str, sorted(common))) if common else "None")

# =====================================================
# RULES & DOWNLOADS TAB
# =====================================================

with tab_manage:
    st.subheader("Mapping rules")

    st.write("Use these rules to improve friendly activity labels and search matching.")
    edited_rules = st.data_editor(
        st.session_state.rules_df,
        use_container_width=True,
        num_rows="dynamic",
        key="rules_editor"
    )
    st.session_state.rules_df = edited_rules.copy()

    st.divider()

    st.subheader("Saved favorites")
    if st.session_state.favorites:
        st.write(", ".join(st.session_state.favorites))
    else:
        st.info("No favorites saved yet.")

    st.divider()

    st.subheader("Downloads")

    full_map = df.drop(columns=["search_blob"], errors="ignore").copy()
    grouped = grouped_summary(df)

    csv_full = full_map.to_csv(index=False).encode("utf-8")
    csv_grouped = grouped.to_csv(index=False).encode("utf-8")
    csv_favorites = pd.DataFrame({"favorite_activity": st.session_state.favorites}).to_csv(index=False).encode("utf-8")

    d1, d2, d3 = st.columns(3)
    d1.download_button(
        "Download filtered access map",
        data=csv_full,
        file_name="filtered_access_map.csv",
        mime="text/csv"
    )
    d2.download_button(
        "Download grouped resource summary",
        data=csv_grouped,
        file_name="grouped_resource_summary.csv",
        mime="text/csv"
    )
    d3.download_button(
        "Download favorites",
        data=csv_favorites,
        file_name="favorites.csv",
        mime="text/csv"
    )

    st.divider()
    st.subheader("Parsed data preview")
    st.dataframe(df.head(200), use_container_width=True, hide_index=True)

st.caption("Built for fast access lookup, debugging, mapping, and request support.")
