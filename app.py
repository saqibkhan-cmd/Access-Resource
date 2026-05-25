import streamlit as st
import pandas as pd
import os
import glob

# Set Page Config
st.set_page_config(page_title="Uniware Access Resource Auditor", layout="wide", page_icon="🛡️")

@st.cache_data
def get_consolidated_database():
    # 1. LOAD MASTER URL PATTERNS
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
    
    for line in lines:
        if '|' not in line: continue
        parts = [p.strip() for p in line.split('|') if p.strip() != '']
        if len(parts) >= 3 and parts[0].isdigit():
            if parts[2].startswith('/'): 
                patterns.append({"res_id": parts[1], "url": parts[2]})
            elif any(c.isupper() for c in parts[1]) or "_" in parts[1]:
                resources[parts[0]] = parts[1]

    # 2. INTEGRATE FULL SIDEBAR DOC DATA (Extracted exactly from the provided .doc file)
    sidebar_mapping = {
        "COD Reconciliation": "COD_RECONCILIATION",
        "Allocation Rules": "CONFIGURE_FACILITY_ALLOCATION_RULES",
        "Create Shelf": "CONFIGURE_SHELVES",
        "Search Shelf": "CONFIGURE_SHELVES",
        "Shelf Types": "ADMIN_LAYOUT",
        "Edit Zones": "ADMIN_PICKING",
        "Zone > Sections": "ADMIN_PICKING",
        "Edit Sections": "ADMIN_PICKING",
        "Edit Templates": "GLOBAL_EDIT_TEMPLATE",
        "Shipping Rules": "ADMIN_SHIPPING_ALLOCATION_RULE",
        "Package Types": "ADMIN_SHIPPING_PACKAGE_TYPE",
        "Shipping Providers": "ADMIN_SHIPPING_PROVIDER",
        "Clear Data": "TENANT_GO_LIVE",
        "Roles": "CREATE_ROLES",
        "Scripts": "ADMIN_SCRIPTS",
        "General Settings": "EDIT_SYSTEM_CONFIGURATION",
        "Custom Fields": "CONFIGURE_CUSTOM_FIELDS",
        "API": "CREATE_API_USER",
        "Edit Facility": "ADMIN_WAREHOUSE",
        "Email Templates": "ADMIN_EMAIL_TEMPLATE",
        "Export Job Type": "ADMIN_EXPORT_CONFIG",
        "Facilities": "ADMIN_WAREHOUSE",
        "Import job Type": "ADMIN_IMPORT_JOB_TYPE",
        "Reconciliations": "ADMIN_PAYMENT_RECONCILIATION",
        "Users": "ADMIN_USER",
        "Batch Group": "VIEW_BATCH",
        "Bill of Materials": "BOM_VIEW",
        "Bulk Returns": "LOOKUP_BULK_RETURNS",
        "Categories": "ADMIN_CATALOG",
        "Discount Group Items": "CUSTOMER",
        "Facility ItemTypes": "VIEW_FACILITY_ITEM_MASTER",
        "Tax Classes": "ADMIN_TAX_TYPE",
        "Tax Types": "ADMIN_TAX_TYPE",
        "Add Channel": "SOURCES_VIEW",
        "Reconciliation": "PAYMENT_RECONCILIATION",
        "Channel Pendency": "CHANNEL_PRODUCTS",
        "Price Master": "PRICE_MASTER",
        "Listings": "CHANNEL_PRODUCTS",
        "Channel Return Facility Mapping": "CHANNELS_ADMIN",
        "Channels": "SOURCES_VIEW",
        "View Channel": "SOURCES_VIEW",
        "Billing Parties": "BILLING_PARTY_VIEW",
        "Add Billing Party": "BILLING_PARTY_EDIT",
        "Edit Billing Party": "BILLING_PARTY_EDIT",
        "Templates": "MINIMAL",
        "Customer Discount Groups": "CUSTOMER",
        "Customers": "CUSTOMER",
        "Add Customer": "CUSTOMER",
        "Edit Customer": "CUSTOMER",
        "Cycle Counts": "CYCLE_COUNT_VIEW",
        "Fulfillment": "ADMIN_FULFILLMENT_DASHBOARD",
        "Inventory": "ADMIN_INVENTORY_DASHBOARD",
        "Overview": "MINIMAL",
        "Payments": "ADMIN_PAYMENTS_DASHBOARD",
        "Purchases": "ADMIN_PROCURE_DASHBOARD",
        "Returns": "ADMIN_SHIPPING_DASHBOARD",
        "Sales": "ADMIN_SALES_DASHBOARD",
        "Datatable Views": "DATATABLE_CUSTOMIZATION",
        "GRNs": "PROCUREMENT_VIEW",
        "Gate Entry": "INBOUND_GATEPASS",
        "Create Label": "INFLOW_GRN_CREATE_LABELS",
        "Quality Check": "JABONG_QC",
        "Create PO Labels": "MINIMAL",
        "Item Details": "ITEM_DETAIL",
        "Search PO": "SEARCH_ACTIVE_PO",
        "Vendor Invoices": "VENDOR_INVOICE",
        "Manifests": "MANIFEST",
        "Edit Manifest": "MANIFEST",
        "Gatepass": "MATERIAL_MANAGEMENT",
        "Gatepass Order": "VIEW_GATEPASSORDER",
        "View/Edit Order": "LOOKUP_SALE_ORDER",
        "Create Order": "CREATE_ORDER",
        "Orders": "ORDERS",
        "Failed Orders": "CHANNEL_ORDER",
        "Picklists": "PICKLIST_VIEW",
        "Manual Picklist": "PICKLIST_MANUAL_CREATE",
        "View/Edit Picklist": "PICKLIST_VIEW"
    }

    # 3. BUILD THE FINAL DATABASE
    master_data = []
    for p in patterns:
        res_name = resources.get(p['res_id'], f"ID_{p['res_id']}")
        url_raw = p['url'].strip()
        segments = [s.upper() for s in url_raw.split('/') if s]
        
        # Match UI Tab Name if it exists in the extracted document mapping
        ui_tab = next((tab for tab, res in sidebar_mapping.items() if res == res_name), "System Background Process")
        
        # Extract meaningful Activity Name
        if len(segments) >= 3:
            major = segments[2]
            sub = segments[1]
        elif len(segments) == 2:
            major = segments[1]
            sub = segments[0]
        else:
            major = segments[0] if segments else "ROOT"
            sub = "CORE"
            
        master_data.append({
            "UI_TAB_NAME": ui_tab,
            "MAJOR_ACTIVITY": major,
            "SUB_MODULE": sub,
            "ACCESS_RESOURCE": res_name,
            "URL_PATTERN": url_raw
        })
        
    return pd.DataFrame(master_data), target_file

# --- APP UI ---
st.title("🛡️ Uniware Access & Sidebar Consolidated Auditor")
st.markdown("### Integrated view of Sidebar Menu items, URL Patterns, and Required Resources")

df, filename = get_consolidated_database()

if df is None or df.empty:
    st.error("Critical Error: Master text file not found.")
else:
    # --- SEARCH & NAVIGATION ---
    st.sidebar.header("🔍 Global Search")
    st.sidebar.info("Search by Sidebar Tab Name or Activity")
    
    # UI Tab Filter (from the Word Doc)
    all_tabs = sorted([t for t in df['UI_TAB_NAME'].unique() if t != "System Background Process"])
    selected_tab = st.sidebar.selectbox("Filter by Sidebar Menu Tab", ["ALL TABS"] + all_tabs + ["System Background Process"])

    # System Activity Filter (from the URL Path)
    all_activities = sorted(df['MAJOR_ACTIVITY'].unique())
    selected_act = st.sidebar.selectbox("Filter by System Activity", ["ALL ACTIVITIES"] + all_activities)

    # Multi-level filtering
    filtered_df = df.copy()
    if selected_tab != "ALL TABS":
        filtered_df = filtered_df[filtered_df['UI_TAB_NAME'] == selected_tab]
    if selected_act != "ALL ACTIVITIES":
        filtered_df = filtered_df[filtered_df['MAJOR_ACTIVITY'] == selected_act]

    # --- RESULTS DISPLAY ---
    st.write(f"📊 Displaying **{len(filtered_df)}** associated system patterns.")

    # Main Data Table
    st.dataframe(
        filtered_df[['UI_TAB_NAME', 'MAJOR_ACTIVITY', 'SUB_MODULE', 'ACCESS_RESOURCE', 'URL_PATTERN']], 
        use_container_width=True, 
        hide_index=True
    )

    # Permission Summary (Audit Details)
    if not filtered_df.empty and (selected_tab != "ALL TABS" or selected_act != "ALL ACTIVITIES"):
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🔑 Security Requirements")
            for res in filtered_df['ACCESS_RESOURCE'].unique():
                st.code(res)
        with col2:
            st.subheader("🌐 Involved System Paths")
            for url in filtered_df['URL_PATTERN'].unique()[:10]: # Limit preview
                st.text(url)

    # Download
    csv = filtered_df.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button("📥 Export Audit View", csv, "consolidated_access.csv", "text/csv")
