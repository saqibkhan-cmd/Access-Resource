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
    
    # 2. PARSE THE TEXT FILE
    for line in lines:
        if '|' not in line: continue
        parts = [p.strip() for p in line.split('|') if p.strip() != '']
        
        if len(parts) >= 3 and parts[0].isdigit():
            # Match URL Patterns
            if parts[2].startswith('/'): 
                patterns.append({"res_id": parts[1], "url": parts[2]})
            # Match Resource Definitions (IDs to Names)
            elif any(c.isupper() for c in parts[1]) or "_" in parts[1]:
                resources[parts[0]] = parts[1]
                
    # 3. BUILD HIERARCHY (Ensuring all Major categories are captured)
    data = []
    for p in patterns:
        res_name = resources.get(p['res_id'], f"Unassigned (ID: {p['res_id']})")
        raw_url = p['url'].strip()
        url_parts = [u for u in raw_url.split('/') if u]
        
        # We categorize by the URL segments
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
    st.error("❌ No data file found. Please ensure your .txt file is in the root GitHub folder.")
else:
    st.success(f"✅ Active File: {found_filename}")
    st.markdown("---")

    # --- SEARCHABLE DROPDOWN FILTERS ---
    st.sidebar.header("🔍 Search Activity")
    st.sidebar.info("Tip: Click a dropdown and type to search (e.g., type 'G' for Gatepass)")

    # 1. Searchable Major Activity
    major_list = sorted(df['Major'].unique())
    selected_major = st.sidebar.selectbox(
        "1. Search & Select Major Category", 
        options=["Select Category"] + major_list,
        index=0
    )

    filtered_df = df.copy()

    if selected_major != "Select Category":
        filtered_df = filtered_df[filtered_df['Major'] == selected_major]
        
        # 2. Searchable Sub-Major Activity
        sub_list = sorted(filtered_df['SubMajor'].unique())
        selected_sub = st.sidebar.selectbox(
            f"2. Search Sub-Major in {selected_major}", 
            options=["All Sub-Majors"] + sub_list,
            index=0
        )
        
        if selected_sub != "All Sub-Majors":
            filtered_df = filtered_df[filtered_df['SubMajor'] == selected_sub]
            
            # 3. Searchable Sub-Sub Activity
            sub_sub_list = sorted(filtered_df['SubSub'].unique())
