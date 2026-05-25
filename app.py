import streamlit as st
import pandas as pd
import os
import glob

# Set Page Config
st.set_page_config(page_title="Access Resource Automation", layout="wide", page_icon="🔐")

@st.cache_data
def get_processed_df():
    # 1. SMART FILE FINDER
    possible_files = glob.glob("*.txt")
    target_file = next((f for f in possible_files if "access" in f.lower() or "pattern" in f.lower()), None)
    
    if not target_file:
        return pd.DataFrame(), None

    try:
        with open(target_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception as e:
        return pd.DataFrame(), str(e)
    
    patterns = []
    resources = {}
    
    # 2. PARSE THE TEXT FILE (Capturing all rows)
    for line in lines:
        if '|' not in line: continue
        parts = [p.strip() for p in line.split('|') if p.strip() != '']
        
        if len(parts) >= 3 and parts[0].isdigit():
            # It's a Pattern row
            if parts[2].startswith('/'): 
                patterns.append({"res_id": parts[1], "url": parts[2]})
            # It's a Resource Name row
            elif any(c.isupper() for c in parts[1]) or "_" in parts[1]:
                resources[parts[0]] = parts[1]
                
    # 3. BUILD ROBUST HIERARCHY
    data = []
    for p in patterns:
        res_name = resources.get(p['res_id'], f"Unassigned (ID: {p['res_id']})")
        # Clean URL and split
        raw_url = p['url'].strip()
        url_parts = [u for u in raw_url.split('/') if u]
        
        # Determine Major/Minor based on URL depth
        major = url_parts[0].upper() if len(url_parts) > 0 else "SYSTEM"
        sub_major = url_parts[1].upper() if len(url_parts) > 1 else "GENERAL"
        sub_sub = url_parts[2].upper() if len(url_parts) > 2 else "ALL"
        action = "/".join(url_parts[3:]) if len(url_parts) > 3 else "VIEW"
        
        data.append({
            "Major": major,
            "SubMajor": sub_major,
            "SubSub": sub_sub,
            "Action": action,
            "url": raw_url,
            "res_name": res_name,
            "res_id": p['res_id']
        })
        
    return pd.DataFrame(data), target_file

# --- UI LOGIC ---
st.title("🔐 Access Resource Automation Tool")

df, found_filename = get_processed_df()

if df is None or df.empty:
    st.error("❌ No data file found. Please ensure 'access_patterns (2).txt' is in the root GitHub folder.")
    st.info(f"Files currently detected: {os.listdir('.')}")
else:
    # --- SEARCH & FILTER SECTION ---
    st.sidebar.header("🔍 Search & Filter")
    
    # Text Search for Categories
    cat_search = st.sidebar.text_input("Search Major/Minor Activity", "").upper()
    
    # Dropdown Filters
    major_list = sorted(df['Major'].unique())
    sel_major = st.sidebar.selectbox("1. Select Major Category", ["All"] + major_list)

    filtered_df = df.copy()

    # Apply Text Search Filter
    if cat_search:
        filtered_df = filtered_df[
            filtered_df['Major'].str.contains(cat_search) | 
            filtered_df['SubMajor'].str.contains(cat_search)
        ]

    # Apply Dropdown Filter
    if sel_major != "All":
        filtered_df = filtered_df[filtered_df['Major'] == sel_major]
        sub_list = sorted(filtered_df['SubMajor'].unique())
        sel_sub = st.sidebar.selectbox("2. Select Sub-Major", ["All"] + sub_list)
        if sel_sub != "All":
            filtered_df = filtered_df[filtered_df['SubMajor'] == sel_sub]

    # --- MAIN DISPLAY ---
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader(f"Activity Patterns ({len(filtered_df)})")
        # Final clean display table
        final_table = filtered_df[['Major', 'SubMajor', 'SubSub', 'Action', 'res_name']]
        final_table.columns = ['MAJOR', 'SUB-MAJOR', 'SUB-SUB', 'ACTION', 'ACCESS RESOURCE NAME']
        st.dataframe(final_table, use_container_width=True, hide_index=True)

    with col2:
        st.subheader("🛠️ Technical Details")
        if not filtered_df.empty:
            # Show the actual Resource ID and URL for the first selected item or summary
            st.metric("Unique Resources", len(filtered_df['res_name'].unique()))
            st.write("**Required Permissions:**")
            for res in filtered_df['res_name'].unique():
                st.code(res)
            
            # Export Option
            csv = filtered_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download This View", csv, "access_export.csv", "text/csv")
        else:
            st.warning("No activities match your search.")

    # Global Keyword Search at the bottom
    st.divider()
    st.write("### 🔎 Deep URL Search")
    deep_search = st.text_input("Type any part of a URL (e.g. 'gatepass', 'price', 'vendor')...")
    if deep_search:
        results = df[df['url'].str.contains(deep_search, case=False)]
        st.table(results[['url', 'res_name']].head(20))
