import streamlit as st
import pandas as pd
from core import (
    load_master_file,
    get_modules,
    get_access_by_module,
    get_urls_for_access,
    search_access
)

st.set_page_config(
    page_title="Access Intelligence",
    layout="wide"
)

st.title("🔐 Access Intelligence Portal")

MASTER_FILE = "data/master_access_file.txt"

# Load data
access_df, pattern_df = load_master_file(MASTER_FILE)

# Sidebar
st.sidebar.header("Filters")

modules = get_modules(access_df)

selected_module = st.sidebar.selectbox(
    "Select Module",
    ["ALL"] + modules
)

if selected_module == "ALL":
    filtered_access = access_df
else:
    filtered_access = get_access_by_module(access_df, selected_module)

access_options = filtered_access.apply(
    lambda x: f"{x['access_resource_id']} - {x['access_name']}",
    axis=1
).tolist()

selected_access = st.sidebar.selectbox(
    "Select Access Resource",
    access_options
)

search_query = st.sidebar.text_input(
    "Search Activity / URL / Access"
)

# Search section
if search_query:
    st.subheader("🔎 Search Results")

    results = search_access(
        access_df,
        pattern_df,
        search_query
    )

    if results.empty:
        st.warning("No results found.")
    else:
        st.dataframe(results, use_container_width=True)

# Access Details
if selected_access:
    access_id = int(selected_access.split(" - ")[0])

    access_row = access_df[
        access_df["access_resource_id"] == access_id
    ].iloc[0]

    st.subheader("📌 Access Details")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Access Resource ID",
            access_row["access_resource_id"]
        )

    with col2:
        st.metric(
            "Access Name",
            access_row["access_name"]
        )

    with col3:
        st.metric(
            "Module",
            access_row["module"]
        )

    urls_df = get_urls_for_access(
        pattern_df,
        access_id
    )

    st.subheader("🌐 Related URLs / APIs")

    st.dataframe(
        urls_df,
        use_container_width=True
    )

    # Export
    csv = urls_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="⬇ Export URLs CSV",
        data=csv,
        file_name=f"access_{access_id}.csv",
        mime="text/csv"
    )
