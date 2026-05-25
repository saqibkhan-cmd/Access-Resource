import streamlit as st
import pandas as pd

# -----------------------------------
# PAGE CONFIG
# -----------------------------------

st.set_page_config(
    page_title="Access Resource Helper",
    layout="wide"
)

st.title("🔐 Access Resource Helper")

st.markdown(
    "Upload your master access file to explore all access resources, activities, URLs, and modules."
)

# -----------------------------------
# FILE UPLOAD
# -----------------------------------

uploaded_file = st.file_uploader(
    "Upload Master Access File",
    type=["txt", "csv"]
)

# -----------------------------------
# MAIN LOGIC
# -----------------------------------

if uploaded_file:

    try:

        # -----------------------------------
        # READ FILE
        # -----------------------------------

        content = uploaded_file.read().decode(
            "utf-8",
            errors="ignore"
        )

        lines = content.splitlines()

        access_resources = []
        url_mappings = []

        # -----------------------------------
        # PARSE FILE
        # -----------------------------------

        for line in lines:

            line = line.strip()

            if not line:
                continue

            if "|" not in line:
                continue

            parts = [p.strip() for p in line.split("|")]

            # -----------------------------------
            # URL MAPPING
            # -----------------------------------

            if "/" in line:

                try:

                    access_id = int(parts[0])

                    url = parts[1]

                    if url:

                        url_mappings.append({
                            "access_id": access_id,
                            "url": url
                        })

                except:
                    continue

            # -----------------------------------
            # ACCESS RESOURCE MASTER
            # -----------------------------------

            else:

                try:

                    access_id = int(parts[0])

                    access_name = parts[1]

                    module = ""

                    if len(parts) > 3:
                        module = parts[3]

                    access_resources.append({
                        "access_id": access_id,
                        "access_name": access_name,
                        "module": module
                    })

                except:
                    continue

        # -----------------------------------
        # CREATE DATAFRAMES
        # -----------------------------------

        access_df = pd.DataFrame(access_resources)
        url_df = pd.DataFrame(url_mappings)

        # -----------------------------------
        # VALIDATION
        # -----------------------------------

        if access_df.empty:
            st.error("No access resource data found.")
            st.stop()

        if url_df.empty:
            st.error("No URL mapping data found.")
            st.stop()

        # -----------------------------------
        # MERGE
        # -----------------------------------

        merged_df = pd.merge(
            url_df,
            access_df,
            on="access_id",
            how="left"
        )

        # -----------------------------------
        # CLEAN NULLS
        # -----------------------------------

        merged_df["access_name"] = merged_df["access_name"].fillna("UNKNOWN")
        merged_df["module"] = merged_df["module"].fillna("UNKNOWN")

        # -----------------------------------
        # CREATE MAJOR ACTIVITY
        # -----------------------------------

        def extract_major(url):

            ignore = [
                "data",
                "oms",
                "api",
                "v2",
                "internal"
            ]

            parts = url.strip("/").split("/")

            for p in parts:

                p = p.lower()

                if p not in ignore and len(p) > 2:
                    return p.replace("-", " ").title()

            return "Other"

        merged_df["major_activity"] = merged_df["url"].apply(
            extract_major
        )

        # -----------------------------------
        # CREATE SUB ACTIVITY
        # -----------------------------------

        def extract_sub(url):

            url_lower = url.lower()

            actions = [
                "create",
                "search",
                "open",
                "edit",
                "cancel",
                "close",
                "approve",
                "update",
                "delete",
                "generate",
                "assign",
                "manifest",
                "print"
            ]

            action = "Manage"

            for a in actions:

                if a in url_lower:
                    action = a.title()
                    break

            parts = url.strip("/").split("/")

            ignore = actions + [
                "data",
                "oms",
                "api",
                "v2",
                "internal"
            ]

            subject = "Activity"

            for p in reversed(parts):

                p_lower = p.lower()

                if p_lower not in ignore and len(p_lower) > 2:

                    subject = p.replace("-", " ").title()
                    break

            return f"{action} {subject}"

        merged_df["sub_activity"] = merged_df["url"].apply(
            extract_sub
        )

        # -----------------------------------
        # SIDEBAR
        # -----------------------------------

        st.sidebar.header("Filters")

        # -----------------------------------
        # MAJOR ACTIVITY DROPDOWN
        # -----------------------------------

        major_options = sorted(
            merged_df["major_activity"].dropna().unique()
        )

        selected_major = st.sidebar.selectbox(
            "Select Major Activity",
            major_options
        )

        filtered_major = merged_df[
            merged_df["major_activity"] == selected_major
        ]

        # -----------------------------------
        # SUB ACTIVITY DROPDOWN
        # -----------------------------------

        sub_options = sorted(
            filtered_major["sub_activity"].dropna().unique()
        )

        selected_sub = st.sidebar.selectbox(
            "Select Sub Activity",
            sub_options
        )

        # -----------------------------------
        # ACCESS DROPDOWN
        # -----------------------------------

        access_options = sorted(
            filtered_major["access_name"].dropna().unique()
        )

        selected_access = st.sidebar.selectbox(
            "Select Access Resource",
            access_options
        )

        # -----------------------------------
        # FINAL FILTER
        # -----------------------------------

        final_df = filtered_major[
            (filtered_major["sub_activity"] == selected_sub)
            &
            (filtered_major["access_name"] == selected_access)
        ]

        if final_df.empty:
            st.warning("No matching data found.")
            st.stop()

        # -----------------------------------
        # FIRST ROW
        # -----------------------------------

        row = final_df.iloc[0]

        # -----------------------------------
        # HEADER METRICS
        # -----------------------------------

        st.subheader("📌 Access Details")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Access Resource ID",
                row["access_id"]
            )

        with col2:
            st.metric(
                "Access Name",
                row["access_name"]
            )

        with col3:
            st.metric(
                "Module",
                row["module"]
            )

        # -----------------------------------
        # HELPS IN
        # -----------------------------------

        st.subheader("✅ What This Access Helps In")

        helps = sorted(
            final_df["sub_activity"].unique()
        )

        for h in helps:
            st.write(f"- {h}")

        # -----------------------------------
        # RELATED URLS
        # -----------------------------------

        st.subheader("🌐 Related URLs / APIs")

        urls = sorted(
            final_df["url"].unique()
        )

        for u in urls:
            st.code(u)

        # -----------------------------------
        # SUMMARY
        # -----------------------------------

        st.subheader("🧠 Summary")

        summary = f"""
        Access Resource ID: {row['access_id']}

        Access Name: {row['access_name']}

        Module: {row['module']}

        This access helps in:
        {", ".join(helps)}
        """

        st.info(summary)

        # -----------------------------------
        # DOWNLOAD CSV
        # -----------------------------------

        csv = final_df.to_csv(index=False).encode("utf-8")

        st.download_button(
            "⬇ Download CSV",
            csv,
            file_name="access_resource_data.csv",
            mime="text/csv"
        )

        # -----------------------------------
        # RAW DATA
        # -----------------------------------

        with st.expander("📄 View Raw Data"):

            st.dataframe(
                final_df,
                use_container_width=True
            )

    except Exception as e:

        st.error(f"Error: {str(e)}")

# -----------------------------------
# NO FILE
# -----------------------------------

else:

    st.info("Please upload your master access file.")
