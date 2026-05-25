# app.py
# READY TO RUN VERSION
# NO rapidfuzz dependency
# Works directly with your uploaded file

# RUN COMMAND:
# pip install streamlit pandas
# streamlit run app.py

import re
import pandas as pd
import streamlit as st
from difflib import SequenceMatcher

# =====================================================
# CONFIG
# =====================================================

FILE_PATH = "access_patterns (2).txt"

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="Access Resource Intelligence Engine",
    layout="wide"
)

st.title("Access Resource Intelligence Engine")
st.caption("Activity → Required Access Resource Automation")

# =====================================================
# LOAD FILE
# =====================================================

@st.cache_data
def load_access_patterns(file_path):

    rows = []

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    for line in lines:

        if "|" not in line:
            continue

        try:

            parts = [x.strip() for x in line.split("|")]

            if len(parts) < 3:
                continue

            id_val = parts[0]
            access_resource_id = parts[1]
            url_pattern = parts[2]

            if not id_val.isdigit():
                continue

            rows.append({
                "id": int(id_val),
                "access_resource_id": int(access_resource_id),
                "url_pattern": url_pattern
            })

        except:
            continue

    return pd.DataFrame(rows)

# =====================================================
# LOAD DATA
# =====================================================

try:
    df = load_access_patterns(FILE_PATH)

except Exception as e:

    st.error(f"Error loading file: {e}")
    st.stop()

# =====================================================
# IDENTIFY MODULE
# =====================================================

def identify_module(url):

    url = url.lower()

    if "/oms/" in url:
        return "OMS"

    elif "/shipping" in url:
        return "Shipping"

    elif "/returns" in url:
        return "Returns"

    elif "/reports" in url:
        return "Reports"

    elif "/procure" in url or "/po/" in url:
        return "Procurement"

    elif "/inflow" in url:
        return "Inflow"

    elif "/putaway" in url:
        return "Putaway"

    elif "/admin" in url:
        return "Admin"

    elif "/catalog" in url or "/products" in url:
        return "Catalog"

    elif "/tasks" in url:
        return "Tasks"

    return "Others"

df["module"] = df["url_pattern"].apply(identify_module)

# =====================================================
# CLEAN ACCESS NAME
# =====================================================

def clean_access_name(url):

    text = url

    text = text.replace("/", " ")
    text = text.replace("_", " ")
    text = text.replace("-", " ")

    text = text.replace("*", "")

    text = re.sub(r"\s+", " ", text)

    return text.strip().title()

df["access_name"] = df["url_pattern"].apply(clean_access_name)

# =====================================================
# PURPOSE GENERATOR
# =====================================================

def generate_purpose(url):

    url = url.lower()

    if "create" in url:
        return "Allows creation operations"

    elif "edit" in url:
        return "Allows edit operations"

    elif "update" in url:
        return "Allows update operations"

    elif "search" in url:
        return "Allows searching records"

    elif "fetch" in url:
        return "Allows fetching/viewing records"

    elif "get" in url:
        return "Allows getting data"

    elif "cancel" in url:
        return "Allows cancellation operation"

    elif "approve" in url:
        return "Allows approval operation"

    elif "manifest" in url:
        return "Allows shipment manifest operations"

    elif "picklist" in url:
        return "Allows picklist operations"

    elif "invoice" in url:
        return "Allows invoice operations"

    return "General access operation"

df["purpose"] = df["url_pattern"].apply(generate_purpose)

# =====================================================
# ACCESS TYPE
# =====================================================

def access_type(url):

    url = url.lower()

    if any(x in url for x in [
        "create",
        "edit",
        "update",
        "cancel",
        "approve",
        "discard",
        "allocate"
    ]):
        return "WRITE"

    return "READ"

df["access_type"] = df["url_pattern"].apply(access_type)

# =====================================================
# STRING MATCH
# =====================================================

def similarity(a, b):

    return SequenceMatcher(None, a, b).ratio()

# =====================================================
# ACTIVITY MAPPING KEYWORDS
# =====================================================

activity_map = {
    "cancel order": [
        "cancel",
        "saleorder",
        "order"
    ],

    "shipment manifest": [
        "manifest",
        "shipping"
    ],

    "picklist creation": [
        "picklist",
        "picker",
        "picking"
    ],

    "inventory allocation": [
        "inventory",
        "allocate",
        "allocation"
    ],

    "returns processing": [
        "returns",
        "reversepickup",
        "reshipment"
    ],

    "purchase order": [
        "po",
        "procure",
        "purchase"
    ],

    "invoice": [
        "invoice"
    ],

    "shipping": [
        "shipping",
        "awb"
    ],

    "user management": [
        "user",
        "users"
    ]
}

# =====================================================
# SEARCH ENGINE
# =====================================================

def get_matching_access(activity):

    activity = activity.lower()

    matched_keywords = []

    # mapped keywords
    for activity_name, keywords in activity_map.items():

        if similarity(activity, activity_name) > 0.45:
            matched_keywords.extend(keywords)

    # direct query words
    matched_keywords.extend(activity.split())

    matched_keywords = list(set(matched_keywords))

    results = []

    for _, row in df.iterrows():

        url = row["url_pattern"].lower()

        keyword_score = 0

        for keyword in matched_keywords:

            if keyword in url:
                keyword_score += 20

        fuzzy_score = similarity(activity, url) * 100

        total_score = keyword_score + fuzzy_score

        if total_score > 20:

            results.append({
                "score": round(total_score, 2),
                "module": row["module"],
                "access_resource_id": row["access_resource_id"],
                "url_pattern": row["url_pattern"],
                "access_name": row["access_name"],
                "purpose": row["purpose"],
                "access_type": row["access_type"]
            })

    if len(results) == 0:
        return pd.DataFrame()

    result_df = pd.DataFrame(results)

    result_df = result_df.sort_values(
        by="score",
        ascending=False
    )

    result_df = result_df.drop_duplicates(
        subset=["url_pattern"]
    )

    return result_df.head(30)

# =====================================================
# UI
# =====================================================

activity_input = st.text_input(
    "Enter Activity",
    placeholder="Example: cancel order, shipment manifest, inventory allocation"
)

# =====================================================
# SEARCH BUTTON
# =====================================================

if st.button("Find Required Access"):

    if not activity_input.strip():

        st.warning("Please enter an activity")

    else:

        results = get_matching_access(activity_input)

        if results.empty():

            st.error("No matching access resources found")

        else:

            st.success(
                f"{len(results)} matching access resources identified"
            )

            grouped_modules = results["module"].unique()

            for module in grouped_modules:

                st.markdown(f"## {module}")

                module_df = results[
                    results["module"] == module
                ]

                for _, row in module_df.iterrows():

                    with st.expander(row["access_name"]):

                        col1, col2 = st.columns(2)

                        with col1:

                            st.markdown("### URL Pattern")
                            st.code(row["url_pattern"])

                            st.markdown("### Access Resource ID")
                            st.code(row["access_resource_id"])

                        with col2:

                            st.markdown("### Purpose")
                            st.info(row["purpose"])

                            st.markdown("### Access Type")
                            st.success(row["access_type"])

# =====================================================
# QUICK SEARCHES
# =====================================================

st.sidebar.header("Quick Activities")

quick_activities = [
    "cancel order",
    "shipment manifest",
    "picklist creation",
    "inventory allocation",
    "returns processing",
    "purchase order",
    "shipping allocation",
    "invoice"
]

for item in quick_activities:

    if st.sidebar.button(item):

        results = get_matching_access(item)

        st.subheader(f"Results for: {item}")

        st.dataframe(results)

# =====================================================
# RAW DATA
# =====================================================

with st.expander("View Raw Access Data"):

    st.dataframe(df)

# =====================================================
# FOOTER
# =====================================================

st.markdown("---")
st.caption(
    "Built for Activity → Access Resource Intelligence Automation"
)
