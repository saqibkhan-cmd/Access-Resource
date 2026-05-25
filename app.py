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
        "Quality Check": "J
