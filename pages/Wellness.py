import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import datetime

st.set_page_config(layout="wide", page_icon="🍃")

@st.cache_data(ttl=300)
def load_data():
    sheet_id = "10z9TpU3nwytVqDh3LlNxMloCIC1St4FH7kbZ6Z2CmQg"
    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    df = pd.read_csv(sheet_url)

    df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
    df = df.dropna(subset=['Timestamp'])
    df['Date'] = df['Timestamp'].dt.date

    variables = ["FATIGUE", "SLEEP QUALITY", "MUSCLE DISCOMFORT", "MOOD"]
    for var in variables:
        df[var] = df[var].astype(str).str.extract(r'(\d)').astype(float)
    df["HOW HAVE YOU RECOVERED?"] = pd.to_numeric(df["HOW HAVE YOU RECOVERED?"], errors='coerce')
    return df

# 🏥 Header
st.markdown("""
<div style="display: flex; align-items: center; margin-bottom: 10px;">
    <img src="https://tmssl.akamaized.net//images/wappen/head/45457.png?lm=1534711579"
         width="80" style="margin-right: 15px; opacity: 0.6;">
    <h1 style="margin: 0;">🏥 Wellness Dashboard</h1>
</div>
""", unsafe_allow_html=True)

# 🔄 Botón de refresco
if st.button("🔄 Refresh Data"):
    st.cache_data.clear()

df = load_data()
variables = ["FATIGUE", "SLEEP QUALITY", "MUSCLE DISCOMFORT", "MOOD"]
var_recovery = "HOW HAVE YOU RECOVERED?"

tab1, tab2 = st.tabs(["📊 Daily Overview", "📈 Individual Trend"])

# ===================== TAB 1 =====================
with tab1:
    st.sidebar.title("Filters")
    selected_date = st.sidebar.date_input("Select Date", value=df["Date"].max())
    filtered = df[df["Date"] == selected_date]

    if filtered.empty:
        st.warning("No data available for the selected date.")
    else:
        st.write(f"**Date: {selected_date}**")

        for var in variables + [var_recovery]:
            st.subheader(var)

            def get_color(val):
                if pd.isna(val): return "lightgray"
                if var == var_recovery:
                    return "rgba(255, 0, 0, 0.5)" if val < 5 else "rgba(255,165,0,0.5)" if val <= 7 else "rgba(0,128,0,0.5)"
                return "rgba(255,0,0,0.5)" if val < 3 else "rgba(255,165,0,0.5)" if val == 3 else "rgba(0,128,0,0.5)"

            filtered["bar_color"] = filtered[var].apply(get_color)

            fig = px.bar(
                filtered,
                x="Name",
                y=var,
                color="bar_color",
                color_discrete_map="identity",
                labels={"Name": "", var: var},
                height=300,
            )
            fig.update_traces(
                marker_line_width=0,
                hovertemplate=f"<b>%{{x}}</b><br>{var}: <b>%{{y}}</b>",
                marker=dict(line=dict(width=0), opacity=0.6)
            )
            fig.update_layout(
                xaxis_tickangle=-45,
                xaxis_tickfont=dict(size=16),
                yaxis_range=[0, 10 if var == var_recovery else 5],
                showlegend=False,
                margin=dict(t=30, b=30)
            )
            st.plotly_chart(fig, use_container_width=True, key=f"{var}_bar_daily")

        st.subheader("💧 Urine Color Alert (> 4)")
        alert_urine = filtered[pd.to_numeric(filtered["URINE COLOR"], errors="coerce") > 4]
        if not alert_urine.empty:
            st.dataframe(alert_urine[["Name", "URINE COLOR"]])
        else:
            st.info("No urine color alerts.")

        st.subheader("🦵 Muscle Discomfort")
        alert_muscle = filtered[filtered["IF THE PREVIOUS ANSWER IS 1 OR 2. WHERE (LOW = L / MEDIUM = M /HIGH = H)"].notna()]
        if not alert_muscle.empty:
            st.dataframe(alert_muscle[["Name", "IF THE PREVIOUS ANSWER IS 1 OR 2. WHERE (LOW = L / MEDIUM = M /HIGH = H)"]])
        else:
            st.info("No muscle discomfort.")

        st.subheader("😴 Short Sleep Duration")
        short_sleep = filtered[filtered["HOW MANY HOURS YOU SLEEP?"].isin(["1-5", "5-7"])]
        if not short_sleep.empty:
            st.dataframe(short_sleep[["Name", "HOW MANY HOURS YOU SLEEP?"]])
        else:
            st.info("No short sleep reported.")

# ===================== TAB 2 =====================
with tab2:
    st.sidebar.title("Player Trend Filter")
    players = ["All"] + sorted(df["Name"].dropna().unique())
    selected_player = st.sidebar.selectbox("Select Player", players)

    last_day = df["Date"].max()
    first_day = last_day - datetime.timedelta(days=30)
    date_range = st.sidebar.date_input("Select Date Range", [first_day, last_day])

    if len(date_range) != 2:
        st.warning("⚠️ Please select a valid date range.")
    else:
        df_range = df[(df["Date"] >= date_range[0]) & (df["Date"] <= date_range[1])]
        if selected_player != "All":
            df_range = df_range[df_range["Name"] == selected_player]

        if df_range.empty:
            st.warning("No data available for this filter.")
        else:
            st.write(f"**Player:** {selected_player}")
            st.write(f"**Date Range:** {date_range[0]} → {date_range[1]}")

            for var in variables + [var_recovery]:
                st.subheader(f"📈 {var}")
                fig = go.Figure()

                if selected_player == "All":
                    df_plot = df_range.groupby("Date")[var].mean().reset_index()
                    fig.add_trace(go.Scatter(x=df_plot["Date"], y=df_plot[var], mode="lines+markers", name="Average"))
                else:
                    fig.add_trace(go.Scatter(x=df_range["Date"], y=df_range[var], mode="lines+markers", name=selected_player))

                fig.update_layout(
                    height=350,
                    yaxis=dict(range=[0, 10 if var == var_recovery else 5]),
                    xaxis=dict(tickangle=-45, tickfont=dict(size=13)),
                    margin=dict(t=30, b=30)
                )
                st.plotly_chart(fig, use_container_width=True, key=f"{var}_trend")

            st.subheader("🦵 Muscle Pain Reports")
            mp = df_range[df_range["IF THE PREVIOUS ANSWER IS 1 OR 2. WHERE (LOW = L / MEDIUM = M /HIGH = H)"].notna()]
            if not mp.empty:
                st.dataframe(mp[["Date", "Name", "IF THE PREVIOUS ANSWER IS 1 OR 2. WHERE (LOW = L / MEDIUM = M /HIGH = H)"]])
            else:
                st.info("No discomforts.")

            st.subheader("💧 Urine Color > 4")
            uc = df_range[pd.to_numeric(df_range["URINE COLOR"], errors='coerce') > 4]
            if not uc.empty:
                st.dataframe(uc[["Date", "Name", "URINE COLOR"]])
            else:
                st.info("No alerts.")

            st.subheader("😴 Short Sleep Entries")
            ss = df_range[df_range["HOW MANY HOURS YOU SLEEP?"].isin(["1-5", "5-7"])]
            if not ss.empty:
                st.dataframe(ss[["Date", "Name", "HOW MANY HOURS YOU SLEEP?"]])
            else:
                st.info("No sleep issues.")
