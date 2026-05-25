import streamlit as st
import pandas as pd
import re
import io

# 1. Page Configuration & Styling
st.set_page_config(page_title="Access Matrix Automation", layout="wide", page_icon="🔐")

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e1e4e8; }
    </style>
    """, unsafe_allow_html=True)

# 2. Optimized Parser with Caching
@st.cache_data
def parse_access_file(file_content):
    """
    Parses the ASCII tables from the master file. 
    It identifies the 'Patterns' table and the 'Resource Names' table automatically.
    """
    lines = file_content.splitlines()
    patterns = []
    resources = []
    
    for line in lines:
        # Clean the line and split by pipe
        parts = [p.strip() for p in line.split('|') if p.strip() != '']
        if not parts or len(parts) < 2:
            continue
            
        # Identify rows starting with a digit ID
        if parts[0].isdigit():
            # TABLE A: URL Patterns (contains a path starting with /)
            if any(p.startswith('/') for p in parts):
                patterns.append({
                    "access_resource_id": parts[1],
                    "url_pattern": parts[2]
                })
            # TABLE B: Resource Definitions (contains UPPER_CASE names)
            elif parts[1].isupper() or "_" in parts[1]:
                resources.append({
                    "resource_id": parts[0],
                    "resource_name": parts[1]
                })

    df_p = pd.DataFrame(patterns)
    df_r = pd.DataFrame(resources)

    if df_p.empty:
        return pd.DataFrame()

    # Merge Patterns with their Resource Names
    final_df = pd.merge(df_p, df_r, left_on="access_resource_id", right_on="resource_id", how="left")
    
    # Fill missing resource names if mapping is incomplete
    final_df['resource_name'] = final_df['resource_name'].fillna("UNKNOWN_RESOURCE_" + final_df['access_resource_id'])
    
    return final_df

def process_hierarchy(path):
    """Splits URL /data/material/gatepass/create into 4 levels."""
    parts = [p for p in path.split('/') if p]
    major = parts[0] if len(parts) > 0 else "Root"
    sub_major = parts[1] if len(parts) > 1 else "General"
    sub_sub = parts[2] if len(parts) > 2 else "General"
    action = "/".join(parts[3:]) if len(parts) > 3 else "View"
    return pd.Series([major, sub_major, sub_sub, action])

# 3. UI Header
st.title("🛡️ Access Resource Automation")
st.info("Upload your master activity file to map activities to system permissions instantly.")

# 4. Sidebar - File Upload and Global Search
with st.sidebar:
    st.header("1. Data Source")
    uploaded_file = st.file_uploader("Upload access_patterns.txt", type=['txt'])
    
    st.divider()
    st.header("2. Global Search")
    search_query = st.text_input("Search any activity or URL...", placeholder="e.g. gatepass")

# 5. Main Logic
if uploaded_file:
    # Read file
    content = uploaded_file.getvalue().decode("utf-8")
    data = parse_access_file(content)

    if not data.empty:
        # Create Hierarchy Columns
        data[['Major', 'Sub-Major', 'Sub-Sub-Major', 'Specific Action']] = data['url_pattern'].apply(process_hierarchy)
        
        # Apply Global Search Filter
        if search_query:
            data = data[data.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)]

        # --- Hierarchy Filter UI ---
        st.subheader("Filter by Activity Hierarchy")
        c1, c2, c3 = st.columns(3)
        
        with c1:
            major_opt = sorted(data['Major'].unique())
            sel_major = st.selectbox("Major Activity", ["All"] + major_opt)
        
        filtered_df = data.copy()
        if sel_major != "All":
            filtered_df = filtered_df[filtered_df['Major'] == sel_major]
            
            with c2:
                sub_major_opt = sorted(filtered_df['Sub-Major'].unique())
                sel_sub_m = st.selectbox("Sub-Major", ["All"] + sub_major_opt)
            
            if sel_sub_m != "All":
                filtered_df = filtered_df[filtered_df['Sub-Major'] == sel_sub_m]
                
                with c3:
                    sub_sub_opt = sorted(filtered_df['Sub-Sub-Major'].unique())
                    sel_sub_sub = st.selectbox("Sub-Sub-Major", ["All"] + sub_sub_opt)
                    if sel_sub_sub != "All":
                        filtered_df = filtered_df
