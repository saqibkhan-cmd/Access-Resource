from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from core import (
    build_index,
    export_resource_csv,
    load_master_file,
    module_options,
    related_resources,
    resource_details,
    resource_options,
    search_resources,
    urls_for_resource,
    preview_tables,
)

APP_DIR = Path(__file__).resolve().parent
DEFAULT_MASTER = APP_DIR / "data" / "master_access_file.txt"

st.set_page_config(page_title="Access Intelligence", layout="wide")
st.title("Access Intelligence")
st.caption("Pick a module or access resource and see what it controls.")

with st.sidebar:
    st.header("Master file")
    uploaded = st.file_uploader(
        "Upload the master pipe file",
        type=["txt", "csv", "tsv", "psv"],
        help="Use the same file format as the one in the repo.",
    )
    st.markdown("Using the bundled master file if nothing is uploaded.")
    st.markdown("---")
    st.write("This app reads the master file directly and keeps the UI simple.")

patterns, resources = load_master_file(uploaded, DEFAULT_MASTER)
resources_index = build_index(patterns, resources)

if patterns.empty or resources.empty:
    st.error("No data found. Please upload the master file.")
    st.stop()

modules = module_options(resources)
module_choice = st.selectbox("Module", modules if modules else ["All"])

filtered_resources = resource_options(resources, module_choice)
if filtered_resources.empty:
    st.warning("No resources found for the selected module.")
    st.stop()

resource_labels = {
    int(row["id"]): f"{int(row['id'])} — {row.get('friendly_label', row.get('name', 'Access'))}"
    for _, row in filtered_resources.iterrows()
}

chosen_id = st.selectbox(
    "Access resource",
    options=list(resource_labels.keys()),
    format_func=lambda rid: resource_labels.get(rid, str(rid)),
)

details = resource_details(chosen_id, patterns, resources)
urls = details["urls"]
related = related_resources(chosen_id, patterns, resources, limit=12)

tab1, tab2, tab3, tab4 = st.tabs(["Access view", "Search", "Master preview", "Export"])

with tab1:
    left, right = st.columns([1.2, 1])
    with left:
        st.subheader(details["friendly_label"])
        st.write(details["description"])
        c1, c2, c3 = st.columns(3)
        c1.metric("Access ID", details["id"])
        c2.metric("Routes", details["url_count"])
        c3.metric("Module", details.get("level") or "-")
        st.write(f"**Raw name:** {details.get('name') or '-'}")
        st.write(f"**Group ID:** {details.get('group_id') or '-'}")
        if details.get("keywords"):
            st.write("**Keywords:** " + ", ".join(details["keywords"]))
    with right:
        st.subheader("What it helps in")
        if urls.empty:
            st.info("No URLs found for this access resource.")
        else:
            for u in urls["url_pattern"].tolist():
                st.code(u, language="text")

    st.subheader("Related access resources")
    if related.empty:
        st.info("No close related resources found.")
    else:
        st.dataframe(
            related[["id", "friendly_label", "name", "level", "group_id", "score"]],
            use_container_width=True,
            hide_index=True,
        )

with tab2:
    st.subheader("Search by activity, URL, or access ID")
    query = st.text_input("Search", placeholder="create gatepass / /material / 85")
    limit = st.slider("Results", 5, 25, 10)
    if query.strip():
        results = search_resources(query, patterns, resources, limit=limit)
        if results.empty:
            st.info("No match found.")
        else:
            for _, row in results.iterrows():
                with st.expander(f"{row['id']} — {row.get('friendly_label', row.get('name', 'Access'))} | {row.get('level', '-')}", expanded=(row["score"] >= 20)):
                    st.write(f"Raw name: {row.get('name', '-')}")
                    st.write(f"Routes: {row.get('url_count', 0)}")
                    if row.get("sample_urls"):
                        st.write("Sample URLs")
                        for u in row["sample_urls"]:
                            st.code(u, language="text")

with tab3:
    st.subheader("How the master file is being used")
    p, r = preview_tables(patterns, resources, n=25)
    c1, c2 = st.columns(2)
    with c1:
        st.write("Access patterns")
        st.dataframe(p, use_container_width=True, hide_index=True)
    with c2:
        st.write("Access resources")
        st.dataframe(r, use_container_width=True, hide_index=True)

    st.markdown("### Simple rule")
    st.write("One access resource ID can control many URL routes. This app shows all of them together.")

with tab4:
    st.subheader("Download one access as CSV")
    export_df = export_resource_csv(chosen_id, patterns, resources)
    st.dataframe(export_df, use_container_width=True, hide_index=True)

    csv = export_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download CSV",
        csv,
        file_name=f"access_{chosen_id}.csv",
        mime="text/csv",
    )

st.markdown("---")
st.caption("Built for a single master file with both the URL mappings and the access-resource master table.")
