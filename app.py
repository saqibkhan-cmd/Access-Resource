# app.py
# Activity -> Access Resource Intelligence Engine
# Run:
# pip install streamlit pandas rapidfuzz openai
# streamlit run app.py

import re
import pandas as pd
import streamlit as st
from rapidfuzz import fuzz
from collections import defaultdict

# =========================
# CONFIG
# =========================

FILE_PATH = "access_patterns (2).txt"

# =========================
# PAGE CONFIG
# =========================

st.set_page_config(
    page_title="Access Resource Intelligence Engine",
    layout="wide"
)

st.title("Access Resource Intelligence Engine")
st.caption("Activity → Required Access Mapping Automation")

# =========================
# LOAD FILE
# =========================

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

    df = pd.DataFrame(rows)

    return df


df = load_access_patterns(FILE_PATH)

# =========================
# MODULE IDENTIFICATION
# =========================

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

# =========================
# URL TO HUMAN READABLE
# =========================

def clean_url_to_text(url):

    text = url

    text = text.replace("/", " ")
    text = text.replace("_", " ")
    text = text.replace("-", " ")

    text = re.sub(r"\*", "", text)

    text = re.sub(r"\s+", " ", text)

    return text.strip().title()


df["access_name"] = df["url_pattern"].apply(clean_url_to_text)

# =========================
# PURPOSE GENERATOR
# =========================

def generate_purpose(url):

    url = url.lower()

    if "create" in url:
        return "Allows creation operation"

    elif "edit" in url or "update" in url:
        return "Allows modification operation"

    elif "search" in url:
        return "Allows searching records"

    elif "fetch" in url or "get" in url:
        return "Allows fetching/viewing data"

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

# =========================
# ACTIVITY KEYWORDS
# =========================

activity_keywords = {
    "cancel order": [
        "cancel",
        "saleorder",
        "order"
    ],

    "shipment manifest": [
        "manifest",
        "shipping",
        "shipment"
    ],

    "picklist creation": [
        "picklist",
        "picker",
        "picking"
    ],

    "inventory management": [
        "inventory",
        "item",
        "catalog"
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

    "reports": [
        "reports",
        "search"
    ],

    "user management": [
        "user",
        "users",
        "admin/system/user"
    ],

    "shipping allocation": [
        "shipping",
        "allocate",
        "awb"
    ]
}

# =========================
# ACTIVITY MATCHER
# =========================

def get_matching_access(activity):

    activity = activity.lower()

    matched_rows = []

    matched_keywords = []

    # direct activity keyword mapping
    for activity_name, keywords in activity_keywords.items():

        score = fuzz.partial_ratio(activity, activity_name)

        if score > 70:
            matched_keywords.extend(keywords)

    # add words from user query
    matched_keywords.extend(activity.split())

    matched_keywords = list(set(matched_keywords))

    for _, row in df.iterrows():

        url = row["url_pattern"].lower()

        score = 0

        for keyword in matched_keywords:

            if keyword in url:
                score += 10

        fuzzy_score = fuzz.partial_ratio(activity, url)

        final_score = score + fuzzy_score

        if final_score > 40:

            matched_rows.append({
                "score": final_score,
                "module": row["module"],
                "access_resource_id": row["access_resource_id"],
                "url_pattern": row["url_pattern"],
                "access_name": row["access_name"],
                "purpose": row["purpose"]
            })

    result_df = pd.DataFrame(matched_rows)

    if len(result_df) == 0:
        return pd.DataFrame()

    result_df = result_df.sort_values(
        by="score",
        ascending=False
    )

    result_df = result_df.drop_duplicates(
        subset=["url_pattern"]
    )

    return result_df.head(25)

# =========================
# UI
# =========================

activity_input = st.text_input(
    "Enter Activity",
    placeholder="Example: cancel order, create manifest, inventory allocation"
)

if activity_input:

    result = get_matching_access(activity_input)

    st.subheader("Recommended Access Resources")

    if result.empty:

        st.warning("No matching access resources found")

    else:

        st.success(f"{len(result)} matching access resources identified")

        for module in result["module"].unique():

            module_df = result[result["module"] == module]

            st.markdown(f"## {module}")

            for _, row in module_df.iterrows():

                with st.expander(row["access_name"]):

                    st.write(f"### URL Pattern")
                    st.code(row["url_pattern"])

                    st.write(f"### Access Resource ID")
                    st.code(row["access_resource_id"])

                    st.write(f"### Purpose")
                    st.info(row["purpose"])

# =========================
# SIDEBAR
# =========================

st.sidebar.header("Quick Activities")

quick_activities = [
    "cancel order",
    "shipment manifest",
    "picklist creation",
    "inventory management",
    "returns processing",
    "purchase order",
    "shipping allocation"
]

for qa in quick_activities:

    if st.sidebar.button(qa):

        result = get_matching_access(qa)

        st.subheader(f"Results for: {qa}")

        st.dataframe(result)

# =========================
# RAW DATA VIEW
# =========================

with st.expander("View Raw Access Data"):

    st.dataframe(df)

# =========================
# FOOTER
# =========================

st.markdown("---")
st.caption("Built for Activity → Access Resource Intelligence Automation")
