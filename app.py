# ==============================================================
# app.py — Mechatronics Power BI Edition (System v5.5 - Stylish Header)
# ==============================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import re
import datetime

# 1. PAGE CONFIGURATION
st.set_page_config(
    page_title="Mechatronics BI", 
    page_icon="📊", 
    layout="wide",
    initial_sidebar_state="collapsed" # Force collapse since we hide it
)

# 2. LOAD CSS
def load_css():
    css_path = Path(__file__).parent / "style.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)
    else:
        st.warning("⚠️ Style file not found. Ensure 'assets/style.css' exists.")

load_css()

# --- THEME ENGINE ---
def theme_plotly(fig, height=300):
    fig.update_layout(
        font_family="Inter, Segoe UI, sans-serif",
        font_color="#64748b",
        title=None, # Explicitly remove title to prevent "undefined" artifacts
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=0, b=10, l=0, r=0), # Remove top margin since we use HTML headers
        height=height,
        hoverlabel=dict(bgcolor="white", font_size=12, font_family="Inter, sans-serif")
    )
    fig.update_xaxes(showgrid=False, linecolor="#cbd5e1", automargin=True)
    fig.update_yaxes(showgrid=True, gridcolor="#f1f5f9", automargin=True)
    return fig

# ------------------------------------------------------------
# 3. NAVIGATION (TOP APP BAR ONLY)
# ------------------------------------------------------------

# B. MAIN HEADER NAV (Single Row, Stylish)
with st.container():
    # -----------------------------------------------------------------------------
    # CUSTOM APP BAR
    # -----------------------------------------------------------------------------
    st.markdown("""
    <style>
    /* Fixed App Bar */
    .app-bar {
        background: white;
        padding: 12px 24px;
        border-bottom: 1px solid #e2e8f0;
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin: -2rem -6rem 0rem -6rem !important; /* Zero bottom margin to connect with toolbar */
        position: sticky;
        top: 0;
        z-index: 999;
    }
    
    /* Toolbar Area (Sub-header) */
    .toolbar-container {
        background: white;
        padding: 8px 24px;
        border-bottom: 1px solid #e2e8f0;
        margin: 0rem -6rem 1rem -6rem !important; 
        display: flex;
        align-items: center;
        gap: 16px;
    }
    
    .app-bar-title {
        font-family: 'Outfit', sans-serif;
        font-weight: 600;
        font-size: 18px;
        color: #0f172a;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .app-bar-icon {
        font-size: 20px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: #f0fdf4;
        color: #16a34a;
        width: 32px;
        height: 32px;
        border-radius: 8px;
    }
    .app-bar-badge {
        background: #f1f5f9;
        color: #64748b;
        font-size: 11px;
        padding: 4px 8px;
        border-radius: 99px;
        font-weight: 500;
        text-transform: uppercase;
    }
    </style>
    <!-- 1. The Top Bar -->
    <div class="app-bar">
        <div class="app-bar-title">
            <div class="app-bar-icon">📊</div>
            <span>Mechatronics BI</span>
            <span class="app-bar-badge">v6.0 Pro</span>
        </div>
    </div>
    
    <!-- 2. The Toolbar Background (Visual Only, Streamlit widgets sit on top) -->
    <div class="toolbar-container">
        <!-- We leave this empty or use it for static labels, 
             but we rely on Streamlit vertical stack to place widgets here -->
    </div>
    """, unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # TOOLBAR CONTROLS (Floating in the toolbar area)
    # -------------------------------------------------------------------------
    # We use a container to inject negative margin to pull this UP into the toolbar-container visually
    
    # c_toolbar = st.container()
    # with c_toolbar:
    
    # We use columns but with tighter ratios
    c_nav, c_spacer, c_refresh = st.columns([4, 4, 1], gap="small")
    
    with c_nav:
        # Navigation pills
        page_main = st.radio("Go to:", ["Inventory Overview", "Delivery Tracking", "Project Explorer"], 
                                horizontal=True, label_visibility="collapsed", key="nav_main")
    
    with c_refresh:
        # Aligned right
        if st.button("↻ Update", help="Reload Data", type="secondary"):
            st.cache_data.clear()
            st.rerun()
            
    # Add a little divider between toolbar and content
    st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

# LOGIC: Sync Main Nav
page = page_main 

# ------------------------------------------------------------
# 4. DATA ENGINE (v10 - Deep Cleaning & Normalization)
# ------------------------------------------------------------
@st.cache_data
def load_data_v10():
    file_path = "Mechatronics Project Parts_Data.xlsx"
    if not Path(file_path).exists(): return None, None, None

    try:
        xls = pd.ExcelFile(file_path, engine='openpyxl')
        
        # Load Sheets
        comp_sheet = next((s for s in xls.sheet_names if "Component" in s), xls.sheet_names[0])
        df_comp = pd.read_excel(xls, sheet_name=comp_sheet)
        
        set_sheet = next((s for s in xls.sheet_names if "Set" in s and "Delivery" in s), None)
        if not set_sheet: set_sheet = next((s for s in xls.sheet_names if "Delivery" in s), None)
        df_sets = pd.read_excel(xls, sheet_name=set_sheet) if set_sheet else pd.DataFrame()

        proj_sheet = next((s for s in xls.sheet_names if "Project" in s and "Considered" in s), None)
        df_proj = pd.read_excel(xls, sheet_name=proj_sheet) if proj_sheet else pd.DataFrame()

        # Clean Headers
        for df in [df_comp, df_sets, df_proj]:
            if not df.empty:
                df.columns = [c.strip() for c in df.columns]

        # --- DEEP CLEANER FUNCTION ---
        def clean(df):
            if df.empty: return df
            
            # Helper to normalize ID strings (remove non-alphanumeric for matching)
            def normalize_id(val):
                s = str(val).strip().upper()
                if s.endswith('.0'): s = s[:-2] # Fix floats
                return s

            for col in df.columns:
                # Skip Links
                if "link" in col.lower(): continue
                
                # 1. Base conversion
                df[col] = df[col].astype(str).str.strip()
                
                # 2. Fix Float Strings (Global)
                df[col] = df[col].str.replace(r'\.0$', '', regex=True)
                
                # 3. Replace Junk with clean dash
                df[col] = df[col].replace(
                    r'(?i)^(nan|none|unknown|undefined|null|nat|0)$', 
                    '-', 
                    regex=True
                )
                
                # 4. Standardize Case
                # If column looks like an ID/Code, make it UPPERCASE for matching
                # Otherwise Title Case for readability
                if any(x in col.lower() for x in ['no', 'id', 'code', 'mfg']):
                    df[col] = df[col].str.upper()
                else:
                    df[col] = df[col].str.title()

            # 5. Brand Standardization
            brand_map = {
                "DFROBOT": "DFRobot", "DFR": "DFRobot", "ADAFRUIT": "Adafruit", 
                "POLOLU": "Pololu", "SPARKFUN": "SparkFun", "ARDUINO": "Arduino", 
                "ESPRESSIF": "Espressif", "SEEED": "Seeed Studio"
            }
            for c in df.columns:
                if c.lower() in ["mfg", "manufacturer", "brand"]:
                    df[c] = df[c].replace(brand_map)
                    
            return df

        return clean(df_comp), clean(df_sets), clean(df_proj)

    except Exception as e:
        st.error(f"Data Load Error: {e}")
        return None, None, None

df_components, df_sets, df_projects = load_data_v10()

if df_components is None:
    st.error("❌ File not found. Please upload 'Mechatronics Project Parts_Data.xlsx'")
    st.stop()
else:
    # Diagnostic Timestamp
    st.sidebar.caption(f"System Ready: {datetime.datetime.now().strftime('%H:%M:%S')}")

# --- HELPERS ---
def get_col(df, candidates):
    if df is None or df.empty: return None
    col_map = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in col_map: return col_map[cand.lower()]
    return None

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', str(s))]

def kpi_card(label, value, color="#111827"):
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value" style="color: {color};">{value}</div>
    </div>
    """, unsafe_allow_html=True)

# ------------------------------------------------------------
# DASHBOARD 1: INVENTORY OVERVIEW
# ------------------------------------------------------------
if page == "Inventory Overview":
    
    c_cat = get_col(df_components, ["Category"])
    c_status = get_col(df_components, ["Status"])
    c_brand = get_col(df_components, ["Mfg", "Manufacturer", "Brand"])
    c_sub1 = get_col(df_components, ["SubCategory"])
    c_sub2 = get_col(df_components, ["SubCategory2"])
    
    c_mfg_no = get_col(df_components, ["MfgNo", "Mfg No", "PartNo", "Part Number"])
    c_name = get_col(df_components, ["Name", "Description", "Component Name"])
    c_link = get_col(df_components, ["Link", "Url"])

    st.sidebar.header("🔍 Filters")
    # Duplicate filter in main expander for accessibility
    with st.expander("🔍 Filter Options", expanded=False):
        c_f1, c_f2 = st.columns(2)
        df_filtered = df_components.copy()
        filters_active = False

        sel_stat = []
        sel_cat = []
        
        if c_status:
            opts = sorted(list(df_components[c_status].unique()))
            with c_f1:
                sel_stat = st.multiselect("Status", opts, default=opts, key="main_stat")
            if len(sel_stat) < len(opts): filters_active = True
            if sel_stat: df_filtered = df_filtered[df_filtered[c_status].isin(sel_stat)]
            
        if c_cat:
            opts = sorted(list(df_components[c_cat].unique()))
            with c_f2:
                sel_cat = st.multiselect("Category", opts, default=opts, key="main_cat")
            if len(sel_cat) < len(opts): filters_active = True
            if sel_cat: df_filtered = df_filtered[df_filtered[c_cat].isin(sel_cat)]

    c_title, c_search = st.columns([1, 1])
    with c_title: st.markdown("## 🏭 Inventory Cockpit")
    with c_search:
        search_inv = st.text_input("Search", placeholder="Search Mfg No, Name, or Brand...", label_visibility="collapsed")
        if search_inv:
            search_term = search_inv.strip()
            # Searching against Uppercased columns
            search_targets = [c for c in [c_mfg_no, c_name, c_brand] if c]
            mask = df_filtered[search_targets].astype(str).apply(lambda x: x.str.contains(search_term, case=False)).any(axis=1)
            df_filtered = df_filtered[mask]
            filters_active = True 

    total = len(df_filtered)
    avail = df_filtered[c_status].str.contains("Available", case=False).sum() if c_status else 0
    pct = int((avail/total)*100) if total > 0 else 0
    
    k1, k2, k3, k4 = st.columns(4)
    with k1: kpi_card("Parts Found", total)
    with k2: kpi_card("Availability", f"{pct}%", "#16a34a" if pct > 50 else "#dc2626")
    with k3: kpi_card("Categories", df_filtered[c_cat].nunique() if c_cat else 0)
    with k4: kpi_card("Manufacturers", df_filtered[c_brand].nunique() if c_brand else 0)

    st.markdown("<br>", unsafe_allow_html=True)

    c_left, c_right = st.columns([1, 2])
    with c_left:
        st.markdown('<div class="card-container"><div class="chart-title">Status Overview</div>', unsafe_allow_html=True)
        if c_status and not df_filtered.empty:
            stat_counts = df_filtered[c_status].value_counts().reset_index()
            stat_counts.columns = ["Status", "Count"]
            fig = px.pie(stat_counts, names="Status", values="Count", hole=0.6, color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(theme_plotly(fig), use_container_width=True)
        else: st.info("No data.")
        st.markdown('</div>', unsafe_allow_html=True)

    with c_right:
        st.markdown('<div class="card-container"><div class="chart-title">Category Distribution</div>', unsafe_allow_html=True)
        if c_cat and not df_filtered.empty:
            cat_counts = df_filtered[c_cat].value_counts().reset_index().head(12)
            cat_counts.columns = ["Category", "Count"]
            fig = px.bar(cat_counts, x="Category", y="Count", text="Count", color="Count", color_continuous_scale="Blues")
            st.plotly_chart(theme_plotly(fig), use_container_width=True)
        else: st.info("No data.")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card-container"><div class="chart-title">Top Manufacturers</div>', unsafe_allow_html=True)
    if c_brand and not df_filtered.empty:
        brand_data = df_filtered[c_brand].value_counts().reset_index().head(25)
        brand_data.columns = ["Brand", "Count"]
        fig = px.treemap(brand_data, path=["Brand"], values="Count", color="Count", color_continuous_scale="Mint")
        st.plotly_chart(theme_plotly(fig, height=350), use_container_width=True)
    else: st.info("No data.")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card-container"><div class="chart-title">Data Explorer (Sunburst)</div>', unsafe_allow_html=True)
    if c_cat and c_sub1 and not df_filtered.empty:
        df_sun = df_filtered.copy()
        # Ensure we don't map "undefined" or "-" here, use "General" for better UX
        df_sun[c_cat] = df_sun[c_cat].replace("-", "Unknown") 
        path = [c_cat, c_sub1]
        if c_sub2 and df_sun[c_sub2].notna().any():
            df_sun[c_sub2] = df_sun[c_sub2].fillna("-")
            path.append(c_sub2)
        fig = px.sunburst(df_sun, path=path, color=c_cat, color_discrete_sequence=px.colors.qualitative.Prism, maxdepth=3)
        st.plotly_chart(theme_plotly(fig, height=600), use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if filters_active:
        st.markdown('<div class="card-container"><div class="chart-title">📋 Component Details</div>', unsafe_allow_html=True)
        if not df_filtered.empty:
            cols_to_show = [c for c in [c_mfg_no, c_brand, c_name, c_cat, c_status, c_link] if c]
            st.dataframe(df_filtered[cols_to_show], hide_index=True, use_container_width=True)
        else: st.warning("No components match your filters.")
        st.markdown('</div>', unsafe_allow_html=True)
    else: st.caption("👇 *Use the Search bar or Sidebar Filters to see the detailed component list.*")

# ------------------------------------------------------------
# DASHBOARD 2: DELIVERY TRACKING
# ------------------------------------------------------------
elif page == "Delivery Tracking":
    
    s_set = get_col(df_sets, ["Set No", "Set"])
    s_status = get_col(df_sets, ["Final Status", "Status"])
    s_link = get_col(df_sets, ["Link", "Url"])
    s_name = get_col(df_sets, ["xDesign Name", "Name", "Description", "Component Name"])
    s_mfg = get_col(df_sets, ["Mfg No", "MfgNo", "Part No"])
    
    if df_sets.empty or not s_set or not s_status:
        st.error("❌ Delivery Data Missing.")
        st.stop()
        
    st.markdown("## 🚚 Delivery Tracking")
    f1, f2 = st.columns(2)
    with f1:
        all_sets = sorted(list(df_sets[s_set].unique()), key=natural_sort_key)
        selected_sets = st.multiselect("Select Set(s)", all_sets, placeholder="Choose specific sets (e.g. Set 1)")
    with f2:
        search_del = st.text_input("Text Search", placeholder="Search Mfg No, Name, or Status...", label_visibility="visible")

    df_view = df_sets.copy()
    is_filtered = False

    if selected_sets:
        df_view = df_view[df_view[s_set].isin(selected_sets)]
        is_filtered = True
    
    if search_del:
        target_cols = [c for c in [s_name, s_mfg, s_status] if c] 
        mask = df_view[target_cols].astype(str).apply(lambda x: x.str.contains(search_del, case=False)).any(axis=1)
        df_view = df_view[mask]
        is_filtered = True

    total = len(df_view)
    released = df_view[s_status].str.contains("Released", case=False, na=False).sum()
    pending = total - released
    pct_rel = int((released/total)*100) if total > 0 else 0
    
    k1, k2, k3 = st.columns(3)
    with k1: kpi_card("Items Found", total)
    with k2: kpi_card("Released", released, "#16a34a")
    with k3: kpi_card("Pending", pending, "#dc2626")
    st.markdown("<br>", unsafe_allow_html=True)

    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown('<div class="card-container"><div class="chart-title">Readiness Gauge</div>', unsafe_allow_html=True)
        fig_gauge = go.Figure(go.Indicator(mode = "gauge+number", value = pct_rel, gauge = {'axis': {'range': [None, 100]}, 'bar': {'color': "#3b82f6"}}))
        st.plotly_chart(theme_plotly(fig_gauge, height=250), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="card-container"><div class="chart-title">Set Composition</div>', unsafe_allow_html=True)
        if not df_view.empty:
            df_stack = df_view.groupby([s_set, s_status]).size().reset_index(name="Count")
            df_stack = df_stack.sort_values(by=s_set, key=lambda col: col.map(lambda x: natural_sort_key(x)))
            colors = {"Released": "#22c55e", "Backorder": "#ef4444", "Split": "#eab308", "Out Of Stock": "#dc2626"}
            fig = px.bar(df_stack, x=s_set, y="Count", color=s_status, color_discrete_map=colors)
            st.plotly_chart(theme_plotly(fig, height=280), use_container_width=True)
        else: st.info("No data matches current filter.")
        st.markdown('</div>', unsafe_allow_html=True)

    if is_filtered:
        st.markdown('<div class="card-container"><div class="chart-title">📋 Complete Manifest</div>', unsafe_allow_html=True)
        if not df_view.empty:
            display_cols = [c for c in [s_set, s_mfg, s_name, s_status, s_link] if c is not None]
            st.dataframe(df_view[display_cols], hide_index=True, use_container_width=True, height=600)
        else: st.warning("No items match your search criteria.")
        st.markdown('</div>', unsafe_allow_html=True)
    else: st.caption("👇 *Select a Set or Search to view individual line items.*")

# ------------------------------------------------------------
# DASHBOARD 3: PROJECT EXPLORER
# ------------------------------------------------------------
elif page == "Project Explorer":
    
    st.markdown("## 🚀 Project Explorer")
    if df_projects is None or df_projects.empty:
        st.error("❌ 'Projects Considered' sheet not found.")
        st.stop()

    p_name_col = df_projects.columns[0]
    comp_cols = [c for c in df_projects.columns if "Component" in c]

    all_projects = sorted(df_projects[p_name_col].astype(str).unique())
    selected_proj = st.selectbox("Select a Project to View Bill of Materials (BOM)", all_projects, index=None, placeholder="Choose a Project...")

    if selected_proj:
        proj_row = df_projects[df_projects[p_name_col] == selected_proj]
        bom = proj_row.melt(id_vars=[p_name_col], value_vars=comp_cols, value_name="MfgNo").dropna()
        
        # KEY FIX: Pre-process keys identically to load_data_v10 logic
        bom["MfgNo"] = bom["MfgNo"].astype(str).str.strip().str.upper()
        bom["MfgNo"] = bom["MfgNo"].str.replace(r'\.0$', '', regex=True)
        
        # Filter junk
        bom = bom[bom["MfgNo"].str.len() > 1]
        bom = bom[~bom["MfgNo"].isin(["-", "UNKNOWN", "NAN", "NONE", "NAT", "0"])]
        
        c_mfg_no = get_col(df_components, ["MfgNo", "Mfg No", "PartNo", "Part Number"])
        
        if c_mfg_no:
            # We already cleaned df_components in load_data_v10
            # Perform the merge
            df_bom = pd.merge(bom, df_components, left_on="MfgNo", right_on=c_mfg_no, how="left")
            
            # FINAL SWEEP: Replace any lingering NaNs from the merge with "-"
            df_bom = df_bom.fillna("-")
            
            total_parts = len(df_bom)
            c_status = get_col(df_components, ["Status"])
            
            if c_status in df_bom.columns:
                in_stock = df_bom[c_status].str.contains("Available", case=False, na=False).sum()
                missing = total_parts - in_stock
                readiness = int((in_stock/total_parts)*100) if total_parts > 0 else 0
            else:
                readiness = 0
                missing = total_parts

            k1, k2, k3 = st.columns(3)
            with k1: kpi_card("Total Components", total_parts)
            with k2: kpi_card("Readiness", f"{readiness}%", "#16a34a" if readiness == 100 else "#eab308")
            with k3: kpi_card("Missing / Issues", missing, "#dc2626" if missing > 0 else "#16a34a")
            st.markdown("<br>", unsafe_allow_html=True)

            c_cat = get_col(df_components, ["Category"])
            vc1, vc2 = st.columns([1, 2])
            
            with vc1:
                st.markdown('<div class="card-container"><div class="chart-title">Stock Status</div>', unsafe_allow_html=True)
                if c_status in df_bom.columns:
                    status_data = df_bom[c_status].value_counts().reset_index()
                    status_data.columns = ["Status", "Count"]
                    fig_stat = px.pie(status_data, names="Status", values="Count", hole=0.6, color_discrete_sequence=px.colors.qualitative.Pastel)
                    st.plotly_chart(theme_plotly(fig_stat, height=300), use_container_width=True)
                else: st.info("Status info unavailable")
                st.markdown('</div>', unsafe_allow_html=True)
            
            with vc2:
                st.markdown('<div class="card-container"><div class="chart-title">Component Composition</div>', unsafe_allow_html=True)
                if c_cat and c_cat in df_bom.columns:
                    cat_data = df_bom[c_cat].replace("-", "Uncategorized").value_counts().reset_index().head(10)
                    cat_data.columns = ["Category", "Count"]
                    fig_cat = px.bar(cat_data, x="Count", y="Category", text="Count", orientation='h', color="Count", color_continuous_scale="Blues")
                    fig_cat.update_layout(yaxis=dict(autorange="reversed"), xaxis_title=None, yaxis_title=None)
                    st.plotly_chart(theme_plotly(fig_cat, height=300), use_container_width=True)
                else: st.info("Category info unavailable")
                st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="card-container"><div class="chart-title">📋 Bill of Materials</div>', unsafe_allow_html=True)
            c_name = get_col(df_components, ["Name", "Description", "Component Name"])
            c_link = get_col(df_components, ["Link", "Url"])
            disp_cols = ["MfgNo"]
            if c_name: disp_cols.append(c_name)
            if c_status: disp_cols.append(c_status)
            if c_link: disp_cols.append(c_link)
            
            final_cols = [c for c in disp_cols if c in df_bom.columns]
            st.dataframe(df_bom[final_cols], hide_index=True, use_container_width=True, height=500)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.error("Could not link Project Data to Inventory. 'MfgNo' column missing in Inventory.")
    else: st.info("👆 Please select a project above to see its components.")
