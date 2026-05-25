import streamlit as st
import pandas as pd
import os
import glob

# Set Page Config
st.set_page_config(page_title="Access Resource Automation", layout="wide", page_icon="🔐")

@st.cache_data
def get_processed_df():
    # 1. SMART FILE FINDER
    # This looks for any .txt file in your repo that contains "access" or "pattern"
    possible_files = glob.glob("*.txt")
    target_file = None
    
    # Priority 1: Exact match you mentioned
    if os.path.exists("access_patterns (2).txt"):
        target_file = "access_patterns (2).txt"
    # Priority 2: Any file containing the keywords
    else:
        for f in possible_files:
            if "access" in f.lower() or "pattern" in f.lower():
                target_file = f
                break

    if not target_file:
        return pd.DataFrame(), None

    try:
        with open(target_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        return pd.DataFrame(), f"Error reading file: {e}"
    
    patterns = []
    resources = {}
    
    # 2. PARSE THE TEXT FILE
    for line in lines:
        parts = [p.strip() for p in line.split('|') if p.strip() != '']
        if len(parts) >= 3 and parts[0].isdigit():
            # Match URLs
            if parts[2].startswith('/'): 
                patterns.append({"res_id": parts[1], "url": parts[2]})
            # Match Resource Definitions
            elif parts[1].isupper() or "_" in parts[1]: 
                resources[parts[0]] = parts[1]
                
    # 3. BUILD HIERARCHY
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
        
    return pd.DataFrame(data), target_file

# --- UI LOGIC ---
st.title("🔐 Access Resource Automation Tool")

# Load data
df, found_filename = get_processed_df()

if df.empty:
    st.error("❌ No access pattern file found in the repository.")
    st.write("### Debugging Steps:")
    st.write(f"1. Ensure your file is in the **root** folder of your GitHub repository (not in a subfolder).")
    st.write(f"2. Check the filename. Currently, I see these files in your repo: `{os.listdir('.')}`")
else:
    st.success(f"✅ Loaded data from: **{found_filename}**")
    st.markdown("---")

    # --- FILTERS ---
    st.sidebar.header("Filter Activities")
    major_list = sorted(df['Major'].unique())
    sel_major = st.sidebar.selectbox("1. Major Activity", ["All"] + major_list)

    filtered_df = df.copy()
    if sel_major != "All":
        filtered_df = filtered_df[filtered_df['Major'] == sel_major]
        sub_major_list = sorted(filtered_df['SubMajor'].unique())
        sel_sub = st.sidebar.selectbox("2. Sub-Major", ["All"] + sub_major_list)
        
        if sel_sub != "All":
            filtered_df = filtered_df[filtered_df['SubMajor'] == sel_sub]
            sub_sub_list = sorted(filtered_df['SubSub'].unique())
            sel_sub_sub = st.sidebar.selectbox("3. Sub-Sub Activity", ["All"] + sub_sub_list)
            
            if sel_sub_sub != "All":
                filtered_df = filtered_df[filtered_df['SubSub'] == sel_sub_sub]

    # --- DISPLAY ---
    st.subheader(f"Results ({len(filtered_df)} Activities)")
    
    display_df = filtered_df[['Major', 'SubMajor', 'SubSub', 'Action', 'res_name', 'res_id']]
    display_df.columns = ['Major', 'Sub-Major', 'Sub-Sub Major', 'Action/Detail', 'Access Resource Name', 'Resource ID']
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # Summary
    if not filtered_df.empty:
        unique_resources = filtered_df['Access Resource Name'].unique()
        st.info("💡 **Summary:** Permissions required for selection:")
        st.write(", ".join([f"`{r}`" for r in unique_resources]))
