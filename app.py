import streamlit as st
import pandas as pd
import re

st.set_page_config(
    page_title="Access Resource Helper",
    layout="wide"
)

st.title("🔐 Access Resource Helper")

st.markdown("Upload master access file")

uploaded_file = st.file_uploader(
    "Upload Master File",
    type=["txt", "csv"]
)

if uploaded_file:

    content = uploaded_file.read().decode("utf-8")

    lines = content.splitlines()

    access_resources = []
    url_mappings = []

    # -------------------------
    # PARSE MASTER FILE
    # -------------------------

    for line in lines:

        parts = [p.strip() for p in line.split("|")]

        if len(parts) < 2:
            continue

        # URL Mapping
        if "/" in line:

            try:
                access_id = int(parts[0])
                url = parts[1]

                url_mappings.append({
                    "access_id": access_id,
                    "url": url
                })

            except:
                pass

        # Access Resource Master
        else:

            try:
                access_id = int(parts[0])

                access_name = parts[1]

                module = ""

                if len(parts) >= 4:
                    module = parts[3]

                access_resources.append({
                    "access_id": access_id,
                    "access_name": access_name,
                    "module": module
                })

            except:
                pass

    access_df = pd.DataFrame(access_resources)
    url_df = pd.DataFrame(url_mappings)

    # -------------------------
    # MERGE
    # -------------------------

    merged_df = pd.merge(
        url_df,
        access_df,
        on="access_id",
        how="left"
    )

    # -------------------------
    # CREATE MAJOR ACTIVITY
    # -------------------------

    def extract_major(url):

        parts = url.strip("/").split("/")

        for p in parts:

            if p in [
                "data",
                "oms",
                "v2",
                "api",
                "internal"
            ]:
                continue

            if len(p) > 2:
                return p.replace("-", " ").title()

        return "Other"

    merged_df["major_activity"] = merged_df["url"].apply(
        extract_major
    )

    # -------------------------
    # CREATE SUB ACTIVITY
    # -------------------------

    def extract_sub(url):

        url = url.lower()

        if "create" in url:
            action = "Create"
        elif "search" in url:
            action = "Search"
        elif "open" in url:
            action = "Open"
        elif "edit" in url:
            action = "Edit"
        elif "cancel" in url:
            action = "Cancel"
        elif "close" in url:
            action = "Close"
        elif "approve" in url:
            action = "Approve"
        elif "manifest" in url:
            action = "Manifest"
        else:
            action = "Manage"

        parts = url.strip("/").split("/")

        subject = ""

        for p in parts[::-1]:

            if p not in [
                "create",
                "search",
                "open",
                "edit",
                "cancel",
                "close",
                "approve",
                "data",
                "oms",
                "api",
                "v2"
            ]:
                subject = p.replace("-", " ").title()
                break

        return f"{action} {subject}"

    merged_df["sub_activity"] = merged_df["url"].apply(
        extract_sub
    )

    # -------------------------
    # DROPDOWN 1
    # -------------------------

    major_options = sorted(
        merged_df["major_activity"].dropna().unique()
    )

    selected_major = st.selectbox(
        "Select Major Activity",
        major_options
    )

    # -------------------------
    # FILTER
    # -------------------------

    filtered_major = merged_df[
        merged_df["major_activity"] == selected_major
    ]

    # -------------------------
    # DROPDOWN 2
    # -------------------------

    sub_options = sorted(
        filtered_major["sub_activity"].dropna().unique()
    )

    selected_sub = st.selectbox(
        "Select Sub Activity",
        sub_options
    )

    # -------------------------
    # FINAL DATA
    # -------------------------

    final_df = filtered_major[
        filtered_major["sub_activity"] == selected_sub
    ]

    if not final_df.empty:

        first_row = final_df.iloc[0]

        st.divider()

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Access Resource ID",
                first_row["access_id"]
            )

        with col2:
            st.metric(
                "Access Name",
                first_row["access_name"]
            )

        with col3:
            st.metric(
                "Module",
                first_row["module"]
            )

        # -------------------------
        # HELPS IN
        # -------------------------

        st.subheader("✅ What This Access Helps In")

        helps = final_df["sub_activity"].unique()

        for h in helps:
            st.write(f"- {h}")

        # -------------------------
        # URLS
        # -------------------------

        st.subheader("🌐 Related URLs / APIs")

        urls = final_df["url"].unique()

        for u in urls:
            st.code(u)

        # -------------------------
        # SUMMARY
        # -------------------------

        st.subheader("🧠 Summary")

        summary = f"""
        Access `{first_row['access_id']} - {first_row['access_name']}`
        belongs to module `{first_row['module']}`.

        This access helps in:
        {", ".join(helps)}.
        """

        st.info(summary)

        # -------------------------
        # DOWNLOAD CSV
        # -------------------------

        csv = final_df.to_csv(index=False).encode("utf-8")

        st.download_button(
            "⬇ Download CSV",
            csv,
            file_name="access_resource.csv",
            mime="text/csv"
        )

else:

    st.warning("Please upload master access file.")
