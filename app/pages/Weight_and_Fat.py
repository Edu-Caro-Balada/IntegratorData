import streamlit as st
import pandas as pd
import datetime
import plotly.graph_objects as go

st.set_page_config(layout="wide",page_icon="⚖️")

# Encabezado
st.markdown("""
    <div style="display: flex; align-items: center; margin-bottom: 10px;">
        <img src="https://tmssl.akamaized.net//images/wappen/head/45457.png?lm=1534711579"
             width="80"
             style="margin-right: 15px; opacity: 0.6;">
        <h1 style="margin: 0;">⚖️ Weight & Body Fat Tracking</h1>
    </div>
    """, unsafe_allow_html=True)

# Botón para refrescar
if st.button("🔄 Refresh Data"):
    st.cache_data.clear()

# ===============================
# Cargar y preparar datos
# ===============================
@st.cache_data(ttl=600)
def load_data():
    # Peso
    url_weight = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTJAPNxMxap3A9olCNHFJnTTLrXGVXVk5VA8_mAKQEf8edOwGH8-BSIKPysPrlqtA/pub?gid=1228753850&single=true&output=csv"
    weight_df = pd.read_csv(url_weight)
    weight_df.columns = [col.strip() for col in weight_df.columns]
    weight_df = weight_df.rename(columns={"Player_name": "Player", "Date": "Date", "Weight": "Weight"})
    weight_df["Date"] = pd.to_datetime(weight_df["Date"], dayfirst=True, errors="coerce").dt.date
    weight_df["Weight"] = (
        weight_df["Weight"]
        .astype(str)
        .str.replace(",", ".", regex=False)
        .str.extract(r'(\d+\.?\d*)')[0]
        .astype(float)
    )

    # Grasa
    url_fat = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQLnDatT5HZr31oJe_dppWxN1VJsyUSBL-lwvyFqsmf0ERKwCzXvUH4OLYtVbLfLw/pub?gid=806789282&single=true&output=csv"
    fat_df = pd.read_csv(url_fat)
    fat_df.columns = [col.strip() for col in fat_df.columns]
    fat_df = fat_df.rename(columns={"Full_Name": "Player", "Date": "Date", "Faulker": "%Fat"})
    fat_df["Date"] = pd.to_datetime(fat_df["Date"], dayfirst=True, errors="coerce").dt.date
    fat_df["%Fat"] = (
        fat_df["%Fat"]
        .astype(str)
        .str.replace(",", ".", regex=False)
        .str.extract(r'(\d+\.?\d*)')[0]
        .astype(float)
    )

    # Fusionar
    merged = pd.merge(weight_df[["Player", "Date", "Weight"]],
                      fat_df[["Player", "Date", "%Fat"]],
                      on=["Player", "Date"], how="outer")

    merged = merged.dropna(subset=["Player", "Date"])
    merged = merged.sort_values(by=["Player", "Date"]).reset_index(drop=True)
    return merged

df = load_data()

# ===============================
# Filtros
# ===============================
st.sidebar.title("Filters")
players = sorted(df["Player"].dropna().unique().tolist())
selected_players = st.sidebar.multiselect("Select Player(s)", players, default=players[:1])

min_date = df["Date"].min()
max_date = df["Date"].max()
date_range = st.sidebar.date_input("Select Date Range", [max_date - datetime.timedelta(days=30), max_date])

if len(date_range) != 2:
    st.warning("⚠️ Please select a valid start and end date.")
else:
    start_date, end_date = date_range
    df_filtered = df[
        (df["Date"] >= start_date) & (df["Date"] <= end_date) &
        (df["Player"].isin(selected_players))
    ]

    if df_filtered.empty:
        st.warning("No data for selected filters.")
    else:
        st.markdown(f"**Date Range:** {start_date} to {end_date}")
        st.markdown(f"**Players:** {', '.join(selected_players)}")

        # ===============================
        # 📊 Gráfico combinado por jugador
        # ===============================
        st.subheader("📈 Weight and Body Fat Trend")

        fig = go.Figure()

        for player in selected_players:
            player_df = df_filtered[df_filtered["Player"] == player].sort_values("Date")

            # Línea de peso
            fig.add_trace(go.Scatter(
                x=player_df["Date"], y=player_df["Weight"],
                mode='lines+markers',
                name=f"{player} – Weight (kg)",
                yaxis="y1"
            ))

            # Línea de grasa
            fig.add_trace(go.Scatter(
            x=player_df["Date"],
            y=player_df["%Fat"],
            mode='lines+markers+text',
            name=f"{player} – % Fat",
            yaxis="y2",
            text=[f"{val:.1f}%" if not pd.isna(val) else "" for val in player_df["%Fat"]],
            textposition="top center",
            textfont=dict(size=9),
            line=dict(dash="dot"),
            connectgaps=True  # 🔧 Fuerza la conexión entre puntos
        ))


        fig.update_layout(
            xaxis=dict(title="Date"),
            yaxis=dict(title="Weight (kg)", side="left"),
            yaxis2=dict(title="% Fat", overlaying="y", side="right"),
            height=400,
            margin=dict(t=30, b=30),
            legend=dict(orientation="h", yanchor="top", y=1.15, xanchor="left", x=0),
            plot_bgcolor="white"
        )

        st.plotly_chart(fig, use_container_width=True, config={
    "displayModeBar": True,
    "displaylogo": False,
    "modeBarButtonsToRemove": [
        "zoom", "pan", "select", "lasso2d", "zoomIn", "zoomOut",
        "autoScale", "resetScale2d", "hoverClosestCartesian",
        "hoverCompareCartesian", "toggleSpikelines", "toImage"
    ],
    "modeBarButtonsToAdd": ["toImage"]
})

        # ================================
        # 🏷️ Últimos valores por jugador
        # ================================
        st.subheader("🏷️ Latest Fat & Weight Record")

        latest_records = df_filtered.sort_values("Date").groupby("Player", as_index=False).last()

        cols = st.columns(len(selected_players))
        for i, player in enumerate(selected_players):
            with cols[i]:
                record = latest_records[latest_records["Player"] == player]
                if not record.empty:
                    fat = record["%Fat"].values[0]
                    weight = record["Weight"].values[0]
                    fat_status = "✅" if fat <= 11.5 else "🚨"
                    st.metric(label=f"{player}", value=f"{weight:.1f} kg / {fat:.1f}% {fat_status}")
                else:
                    st.metric(label=f"{player}", value="No data")

        # ================================
        # 🔖 Best % Fat per Selected Player
        # ================================
        st.subheader("🔖 Best % Fat per Player")
        fat_data = df[df["%Fat"].notna()]
        selected_data = fat_data[fat_data["Player"].isin(selected_players)]
        best_fat = selected_data.groupby("Player")["%Fat"].min().reset_index()

        cols = st.columns(len(best_fat))
        for i, row in best_fat.iterrows():
            with cols[i]:
                st.metric(label=f"Best % Fat – {row['Player']}", value=f"{row['%Fat']:.2f}%")

        # ===============================
        # 📋 Data Table
        # ===============================
        st.subheader("📋 Data Table")
        st.dataframe(df_filtered.sort_values(["Player", "Date"]), use_container_width=True)

# ================================
# 🚨 Players Over 11.5% Body Fat
# ================================
st.subheader("🚨 Players with Body Fat > 11.5% (Latest Record)")
latest_fat = df.dropna(subset=["%Fat"]).sort_values("Date").groupby("Player", as_index=False).last()
over_fat = latest_fat[latest_fat["%Fat"] > 11.5]

if not over_fat.empty:
    st.dataframe(over_fat[["Player", "Date", "%Fat"]].sort_values("%Fat", ascending=False), use_container_width=True)
else:
    st.success("✅ All players are below 11.5% body fat.")
