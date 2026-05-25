import streamlit as st
import pandas as pd
import os
import glob

# Set Page Config
st.set_page_config(page_title="Master Access Control Auditor", layout="wide", page_icon="🛡️")

@st.cache_data
def get_master_database():
    # Find the file
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
    
    # 1. PARSE EVERY ROW (Audit Mode)
    for line in lines:
        if '|' not in line: continue
        parts = [p.strip() for p in line.split('|') if p.strip() != '']
        
        if len(parts) >= 3 and parts[0].isdigit():
            # URL Table
            if parts[2].startswith('/'): 
                patterns.append({"res_id": parts[1], "url": parts[2]})
            # Resource Name Table
            elif any(c.isupper() for c in parts[1]) or "_" in parts[1]:
                resources[parts[0]] = parts[1]
                
    # 2. BUILD COMPREHENSIVE HIERARCHY
    data = []
    for p in patterns:
        res_name = resources.get(p['res_id'], f"UNDEFINED_RESOURCE_ID_{p['res_id']}")
        url_raw = p['url'].strip()
        segments = [s.upper() for s in url_raw.split('/') if s]
        
        # LOGIC: Identify the core "Activity Name" from the path
        # We prioritize the 3rd segment (module), then 2nd (sub-system), then 1st
        if len(segments) >= 3:
            major = segments[2] # Example: GATEPASS
            sub = segments[1]   # Example: MATERIAL
        elif len(segments) == 2:
            major = segments[1] # Example: TAGS
            sub = segments[0]   # Example: CATALOG
        else:
            major = segments[0] if segments else "ROOT"
            sub = "SYSTEM"
            
        data.append({
            "ACTIVITY": major,
            "MODULE": sub,
            "RESOURCE_REQUIRED": res_name,
            "FULL_SYSTEM_PATH": url_raw,
            "RESOURCE_ID": p['res_id']
        })
        
    return pd.DataFrame(data), target_file

# --- APP UI ---
st.title("🛡️ Master Access Control Auditor")
st.markdown("### complete list of all system activities and required access resources")

df, filename = get_master_database()

if df is None or df.empty:
    st.error("Critical Error: Master file 'access_patterns (2).txt' not found in repository.")
else:
    # --- SEARCHABLE SIDEBAR ---
    st.sidebar.header("Audit Controls")
    
    # SEARCHABLE SELECT BOX (Typing 'GATE' now finds all Gatepass activities)
    all_activities = sorted(df['ACTIVITY'].unique())
    selected_act = st.sidebar.selectbox(
        "🔍 Search Activity (Type here)",
        options=["[ SHOW ALL ACTIVITIES ]"] + all_activities
    )

    # Filter Logic
    if selected_act != "[ SHOW ALL ACTIVITIES ]":
        display_df = df[df['ACTIVITY'] == selected_act]
    else:
        display_df = df

    # --- MAIN VIEW ---
    st.write(f"📊 **Audit Record Count:** {len(display_df)} entries")

    # The Core Table - Showing everything
    st.dataframe(
        display_df[['ACTIVITY', 'MODULE', 'RESOURCE_REQUIRED', 'FULL_SYSTEM_PATH', 'RESOURCE_ID']], 
        use_container_width=True, 
        hide_index=True
    )

    # Summary Panel for Specific Selections
    if selected_act != "[ SHOW ALL ACTIVITIES ]":
        st.success(f"### Access Requirements for: {selected_act}")
        unique_resources = display_df['RESOURCE_REQUIRED'].unique()
        
        c1, c2 = st.columns(2)
        with c1:
            st.write("**Mandatory Access Resources:**")
            for r in unique_resources:
                st.code(r)
        with c2:
            st.write("**Involved System Modules:**")
            for m in display_df['MODULE'].unique():
                st.info(m)

    # Export for Audit documentation
    csv = display_df.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button(
        label="📥 Download Audit Report (CSV)",
        data=csv,
        file_name=f"access_audit_{selected_act}.csv",
        mime="text/csv"
    )

st.sidebar.markdown("---")
st.sidebar.caption(f"Source File: {filename}")
