import streamlit as st
import pandas as pd
import plotly.express as px

# --- Config ---
st.set_page_config(page_title="SUBISU Business Development Dashboard", layout="wide")

# --- Theme ---
st.markdown("""
<style>
body { background-color: #000000; color: white; }
h1, h2, h3, h4, h5, h6 { color: #ED1C24; }
.css-1v3fvcr, .css-18e3th9 { background-color: #000000; }
</style>
""", unsafe_allow_html=True)

# --- Load Data ---
df = pd.read_csv("Dataset.csv")

# --- Cleaning & Feature Engineering ---
df["Bandwidth"] = df["InternetBW"].str.extract(r"(\d+)").astype(float)
df["BookingDate"] = pd.to_datetime(df["BookingDate"], errors="coerce")
df["InstallationDate"] = pd.to_datetime(df["InstallationDate"], errors="coerce")
df["DaysToInstall"] = (df["InstallationDate"] - df["BookingDate"]).dt.days

df["FunnelStage"] = df.apply(
    lambda x: "Installed" if pd.notnull(x["InstallationDate"]) 
    else "Booked" if pd.notnull(x["BookingDate"]) 
    else "Inquiry", axis=1
)

def device_status(row):
    if row["DeviceRequested"] == "-" or row["DeviceRequested"] == "":
        return "Not Requested"
    elif row["DeviceSold"] != "-" and row["DeviceSold"] != "":
        return "Sold"
    else:
        return "Not Sold"
df["DeviceStatus"] = df.apply(device_status, axis=1)

df["PlanMatch"] = df["InquiredPlanOffer"] == df["InstalledPlanOffer"]
df["ChurnRisk"] = df["FunnelStage"].isin(["Booked", "Inquiry"]) & (df["DaysToInstall"].isnull() | (df["DaysToInstall"] > 14))

# --- Sidebar Filters ---
st.sidebar.header("🔍 Filters")
regions = df["Region"].dropna().unique().tolist()
selected_region = st.sidebar.multiselect("Select Region(s):", regions, default=regions)

services = df["ServiceType"].dropna().unique().tolist()
selected_services = st.sidebar.multiselect("Select Service Type(s):", services, default=services)

if "AgentName" in df.columns:
    agents = df["AgentName"].dropna().unique().tolist()
    selected_agents = st.sidebar.multiselect("Select Agent(s):", agents, default=agents)
    df_filtered = df[(df["Region"].isin(selected_region)) & 
                     (df["ServiceType"].isin(selected_services)) & 
                     (df["AgentName"].isin(selected_agents))]
else:
    df_filtered = df[(df["Region"].isin(selected_region)) & 
                     (df["ServiceType"].isin(selected_services))]

# --- Download Button ---
st.sidebar.markdown("### ⬇️ Download Filtered Data")
csv = df_filtered.to_csv(index=False).encode('utf-8')
st.sidebar.download_button(
    label="Download as CSV",
    data=csv,
    file_name='filtered_leads.csv',
    mime='text/csv',
)

# --- Header ---
st.title("📊 SUBISU Business Development Dashboard")

# --- KPIs ---
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Leads", len(df_filtered))
col2.metric("Installed %", f"{(df_filtered['FunnelStage']=='Installed').mean()*100:.1f}%")
col3.metric("Avg Install Delay", f"{df_filtered['DaysToInstall'].mean():.1f} days")
col4.metric("Churn Risk Leads", df_filtered["ChurnRisk"].sum())
conversion_base = (df_filtered['FunnelStage'] != 'Installed').sum()
conversion_pct = (df_filtered['FunnelStage'] == 'Installed').sum() / conversion_base * 100 if conversion_base else 0
col5.metric("Inquiry → Installed Conversion", f"{conversion_pct:.1f}%")

# --- Visualizations ---
st.markdown("---")

with st.spinner("Loading Visual Insights..."):
    st.subheader("🔄 Funnel Conversion Overview")
    st.plotly_chart(px.histogram(df_filtered, x="FunnelStage", color="FunnelStage",
                                  color_discrete_sequence=["#034EA2", "#ED1C24", "white"],
                                  hover_data=["Region", "ServiceType", "BookingDate"]))

    st.subheader("🌍 Leads by Region")
    st.plotly_chart(px.bar(df_filtered["Region"].value_counts(),
                           labels={"value": "Leads", "index": "Region"},
                           color_discrete_sequence=["#ED1C24"]))

    st.subheader("🏆 Agent Leaderboard (Installed Leads)")
    if "AgentName" in df_filtered.columns:
        top_agents = df_filtered[df_filtered['FunnelStage'] == 'Installed'] \
            .groupby('AgentName').size().reset_index(name='InstalledCount')
        st.plotly_chart(px.bar(top_agents.sort_values('InstalledCount', ascending=False),
                               x='AgentName', y='InstalledCount',
                               color='InstalledCount', hover_name='AgentName',
                               color_continuous_scale='greens'))

    st.subheader("📦 Device Sale Status")
    st.plotly_chart(px.pie(df_filtered, names="DeviceStatus",
                           color_discrete_sequence=["#ED1C24", "#034EA2", "white"]))

    st.subheader("🧾 Plan Match Rate")
    match_rate = df_filtered["PlanMatch"].value_counts()
    st.plotly_chart(px.pie(values=match_rate.values,
                           names=match_rate.index.map({True: "Match", False: "Mismatch"}),
                           color_discrete_sequence=["#034EA2", "#ED1C24"]))

    st.subheader("📆 Monthly Booking Trend")
    df_time = df_filtered[df_filtered['BookingDate'].notnull()]
    df_time = df_time.groupby(df_time['BookingDate'].dt.to_period('M')).size().reset_index(name='Leads')
    df_time['BookingDate'] = df_time['BookingDate'].dt.to_timestamp()
    st.plotly_chart(px.line(df_time, x='BookingDate', y='Leads',
                            markers=True, color_discrete_sequence=["#034EA2"]))

    st.subheader("🚩 Churn Risk by Region")
    risk_region = df_filtered[df_filtered['ChurnRisk']].groupby('Region').size().reset_index(name='HighRiskLeads')
    st.plotly_chart(px.bar(risk_region, x='Region', y='HighRiskLeads',
                           color='HighRiskLeads', color_continuous_scale='reds'))
