import streamlit as st
import pandas as pd
import os

# Set Page Config
st.set_page_config(page_title="Access Resource Automation", layout="wide", page_icon="🔐")

@st.cache_data
def get_processed_df():
    """
    Reads the file locally from the GitHub folder and processes 
    it into the Major/Sub-Major hierarchy.
    """
    file_path = "access_patterns (2).txt"
    
    if not os.path.exists(file_path):
        return pd.DataFrame() # Return empty if file is missing

    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    patterns = []
    resources = {}
    
    # 1. Parse the text file (URLs and Resource Names)
    for line in lines:
        parts = [p.strip() for p in line.split('|') if p.strip() != '']
        if len(parts) >= 3 and parts[0].isdigit():
            # Check if it's a URL path or a Resource Definition
            if parts[2].startswith('/'): 
                patterns.append({"res_id": parts[1], "url": parts[2]})
            elif parts[1].isupper() or "_" in parts[1]: 
                resources[parts[0]] = parts[1]
                
    # 2. Match URLs to Names and Build Hierarchy
    data = []
    for p in patterns:
        res_name = resources.get(p['res_id'], f"ID_{p['res_id']}")
        url_parts = [u for u in p['url'].split('/') if u]
        
        data.append({
            "Major": url_parts[0].replace("_", " ").title() if len(url_parts) > 0 else "Root",
            "SubMajor": url_parts[1].replace("_", " ").title() if len(url_parts) > 1 else "General",
            "SubSub": url_parts[2].replace("_", " ").title() if len(url_parts) > 2 else "General",
            "Action": "/".join(url_parts[3:]) if len(url_parts) > 3 else "View",
            "url": p['url'],
            "res_name": res_name,
            "res_id": p['res_id']
        })
        
    return pd.DataFrame(data)

# --- UI LOGIC ---
st.title("🔐 Access Resource Automation Tool")
st.markdown("### Activity-to-Resource Mapping")

# Load the data automatically from the file in the repo
df = get_processed_df()

if df.empty:
    st.error(f"Error: 'access_patterns (2).txt' not found in the repository. Please upload it to GitHub.")
else:
    # --- SIDEBAR FILTERS ---
    st.sidebar.header("Filter Activities")

    # 1. Major Activity Filter
    major_list = sorted(df['Major'].unique())
    sel_major = st.sidebar.selectbox("1. Select Major Activity", ["All"] + major_list)

    filtered_df = df.copy()
    
    if sel_major != "All":
        filtered_df = filtered_df[filtered_df['Major'] == sel_major]
        
        # 2. Sub-Major Activity Filter
        sub_major_list = sorted(filtered_df['SubMajor'].unique())
        sel_sub = st.sidebar.selectbox(f"2. Select Sub-Major", ["All"] + sub_major_list)
        
        if sel_sub != "All":
            filtered_df = filtered_df[filtered_df['SubMajor'] == sel_sub]
            
            # 3. Sub-Sub Activity Filter
            sub_sub_list = sorted(filtered_df['SubSub'].unique())
            sel_sub_sub = st.sidebar.selectbox("3. Select Sub-Sub Activity", ["All"] + sub_sub_list)
            
            if sel_sub_sub != "All":
                filtered_df = filtered_df[filtered_df['SubSub'] == sel_sub_sub]

    # --- MAIN DISPLAY ---
    st.subheader(f"Results ({len(filtered_df)} Activities Found)")
    
    # Cleaning table for display
    display_df = filtered_df[['Major', 'SubMajor', 'SubSub', 'Action', 'res_name', 'res_id']]
    display_df.columns = ['Major', 'Sub-Major', 'Sub-Sub Major', 'Action/Detail', 'Access Resource Name', 'Resource ID']
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # Summary Box
    if not filtered_df.empty:
        unique_resources = filtered_df['Access Resource Name'].unique()
        st.info("💡 **Summary:** To perform the selected activities, the following resources are required:")
        for res in unique_resources:
            st.code(res)

    # Search Feature
    st.divider()
    search = st.text_input("🔍 Search by keyword (e.g. 'gatepass', 'invoice', 'create')")
    if search:
        search_results = df[df.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)]
        st.write(f"Search Results for '{search}':")
        st.dataframe(search_results[['url', 'res_name']], use_container_width=True, hide_index=True)
