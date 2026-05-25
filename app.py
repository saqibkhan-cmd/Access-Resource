# app.py
# FINAL PRODUCTION READY VERSION

# RUN:
# pip install streamlit pandas
# streamlit run app.py

import re
import pandas as pd
import streamlit as st
from difflib import SequenceMatcher

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
# FILE UPLOAD
# =====================================================

uploaded_file = st.file_uploader(
    "Upload Access Pattern File",
    type=["txt", "csv"]
)

if uploaded_file is None:
    st.info("Please upload the access pattern file")
    st.stop()

# =====================================================
# LOAD FILE
# =====================================================

@st.cache_data
def load_access_patterns(file):

    rows = []

    try:

        content = file.read().decode(
            "utf-8",
            errors="ignore"
        )

        lines = content.splitlines()

        for line in lines:

            line = line.strip()

            if not line:
                continue

            # auto detect separator
            separator = None

            if "|" in line:
                separator = "|"

            elif "," in line:
                separator = ","

            elif "\t" in line:
                separator = "\t"

            if separator is None:
                continue

            try:

                parts = [
                    x.strip()
                    for x in line.split(separator)
                ]

                # skip malformed rows
                if len(parts) < 3:
                    continue

                url_pattern = parts[-1]

                # find numeric values safely
                numeric_parts = [
                    p for p in parts
                    if p.isdigit()
                ]

                if len(numeric_parts) < 2:
                    continue

                rows.append({
                    "id": numeric_parts[0],
                    "access_resource_id": numeric_parts[1],
                    "url_pattern": url_pattern
                })

            except:
                continue

    except Exception as e:

        st.error(f"File parsing failed: {e}")
        return pd.DataFrame()

    return pd.DataFrame(rows)

# =====================================================
# LOAD DATA
# =====================================================

df = load_access_patterns(uploaded_file)

# =====================================================
# VALIDATION
# =====================================================

if df.empty:

    st.error(
        "No valid access patterns found in file."
    )

    st.write("Preview of uploaded file:")

    uploaded_file.seek(0)

    preview = uploaded_file.read().decode(
        "utf-8",
        errors="ignore"
    )[:3000]

    st.code(preview)

    st.stop()

required_columns = [
    "id",
    "access_resource_id",
    "url_pattern"
]

missing_columns = [
    col for col in required_columns
    if col not in df.columns
]

if missing_columns:

    st.error(
        f"Missing required columns: {missing_columns}"
    )

    st.dataframe(df.head())

    st.stop()

# =====================================================
# IDENTIFY MODULE
# =====================================================

def identify_module(url):

    url = str(url).lower()

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

df["module"] = df["url_pattern"].apply(
    identify_module
)

# =====================================================
# ACCESS NAME
# =====================================================

def clean_access_name(url):

    text = str(url)

    text = text.replace("/", " ")
    text = text.replace("_", " ")
    text = text.replace("-", " ")
    text = text.replace("*", "")

    text = re.sub(r"\s+", " ", text)

    return text.strip().title()

df["access_name"] = df["url_pattern"].apply(
    clean_access_name
)

# =====================================================
# PURPOSE
# =====================================================

def generate_purpose(url):

    url = str(url).lower()

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
        return "Allows cancellation operations"

    elif "approve" in url:
        return "Allows approval operations"

    elif "manifest" in url:
        return "Allows manifest operations"

    elif "picklist" in url:
        return "Allows picklist operations"

    elif "invoice" in url:
        return "Allows invoice operations"

    return "General access operation"

df["purpose"] = df["url_pattern"].apply(
    generate_purpose
)

# =====================================================
# ACCESS TYPE
# =====================================================

def access_type(url):

    url = str(url).lower()

    write_keywords = [
        "create",
        "edit",
        "update",
        "cancel",
        "approve",
        "discard",
        "allocate",
        "delete"
    ]

    for keyword in write_keywords:

        if keyword in url:
            return "WRITE"

    return "READ"

df["access_type"] = df["url_pattern"].apply(
    access_type
)

# =====================================================
# SIMILARITY
# =====================================================

def similarity(a, b):

    return SequenceMatcher(
        None,
        str(a),
        str(b)
    ).ratio()

# =====================================================
# ACTIVITY MAP
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
# MATCH ENGINE
# =====================================================

def get_matching_access(activity):

    activity = str(activity).lower()

    matched_keywords = []

    for activity_name, keywords in activity_map.items():

        if similarity(
            activity,
            activity_name
        ) > 0.45:

            matched_keywords.extend(keywords)

    matched_keywords.extend(
        activity.split()
    )

    matched_keywords = list(
        set(matched_keywords)
    )

    results = []

    for _, row in df.iterrows():

        url = str(
            row["url_pattern"]
        ).lower()

        keyword_score = 0

        for keyword in matched_keywords:

            if keyword in url:
                keyword_score += 20

        fuzzy_score = similarity(
            activity,
            url
        ) * 100

        total_score = (
            keyword_score +
            fuzzy_score
        )

        if total_score > 20:

            results.append({

                "score": round(
                    total_score,
                    2
                ),

                "module": row["module"],

                "access_resource_id":
                row["access_resource_id"],

                "url_pattern":
                row["url_pattern"],

                "access_name":
                row["access_name"],

                "purpose":
                row["purpose"],

                "access_type":
                row["access_type"]
            })

    if not results:
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
# USER INPUT
# =====================================================

activity_input = st.text_input(
    "Enter Activity",
    placeholder="Example: cancel order"
)

# =====================================================
# SEARCH
# =====================================================

if st.button("Find Required Access"):

    if not activity_input.strip():

        st.warning(
            "Please enter an activity"
        )

    else:

        results = get_matching_access(
            activity_input
        )

        if results.empty():

            st.error(
                "No matching access found"
            )

        else:

            st.success(
                f"{len(results)} matching accesses identified"
            )

            for module in results[
                "module"
            ].unique():

                st.markdown(
                    f"## {module}"
                )

                module_df = results[
                    results["module"] == module
                ]

                for _, row in module_df.iterrows():

                    with st.expander(
                        row["access_name"]
                    ):

                        col1, col2 = st.columns(2)

                        with col1:

                            st.markdown(
                                "### URL Pattern"
                            )

                            st.code(
                                row["url_pattern"]
                            )

                            st.markdown(
                                "### Access Resource ID"
                            )

                            st.code(
                                row["access_resource_id"]
                            )

                        with col2:

                            st.markdown(
                                "### Purpose"
                            )

                            st.info(
                                row["purpose"]
                            )

                            st.markdown(
                                "### Access Type"
                            )

                            st.success(
                                row["access_type"]
                            )

# =====================================================
# RAW DATA
# =====================================================

with st.expander(
    "View Parsed Data"
):

    st.dataframe(df.head(100))

# =====================================================
# FOOTER
# =====================================================

st.markdown("---")
st.caption(
    "Activity → Access Resource Intelligence Engine"
)
