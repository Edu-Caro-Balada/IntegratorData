import streamlit as st
import pandas as pd
import datetime as dt
import plotly.express as px

st.set_page_config(layout="wide",page_icon="💆‍♂️")

# Logo y titulo
st.markdown(
    """
    <div style="display: flex; align-items: center; margin-bottom: 10px;">
        <img src="https://tmssl.akamaized.net//images/wappen/head/45457.png?lm=1534711579"
             width="80"
             style="margin-right: 15px; opacity: 0.6;">
        <h1 style="margin: 0;">💆‍♂️ Procedure Overview (Physiotherapy)</h1>
    </div>
    """,
    unsafe_allow_html=True
)


# Botón para refrescar datos
if st.button("🔄 Refresh Data"):
    st.cache_data.clear()

# Cargar datos desde Google Sheets
@st.cache_data(ttl=300)
def load_data():
    url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRwKKzVCkFoANZQkD0r27jCIYG9JHGpgSBwnJ3g_R3Ah7E4EfdJf7qjAHlFT2eySz_TTYQ3bqHD5agQ/pub?gid=928266016&single=true&output=csv"
    df = pd.read_csv(url)
    df.columns = [col.strip() for col in df.columns]
    df["DATE"] = pd.to_datetime(df["DATE"], dayfirst=True, errors="coerce").dt.date  # ✅ Corrección aquí
    df = df.dropna(subset=["DATE"])
    df["PLAYER"] = df["PLAYER"].astype(str)
    return df




df = load_data()

# Filtros
players = ["All"] + sorted(df["PLAYER"].unique().tolist())
selected_player = st.sidebar.selectbox("Select Player", players)

last_day = df["DATE"].max()
first_day = last_day - dt.timedelta(days=14)
date_range = st.sidebar.date_input("Date Range", [first_day, last_day])

# Validar que se seleccionen dos fechas
if len(date_range) != 2:
    st.warning("⚠️ Please select a valid start and end date.")
else:
    df_range = df[(df["DATE"] >= date_range[0]) & (df["DATE"] <= date_range[1])]
    if selected_player != "All":
        df_range = df_range[df_range["PLAYER"] == selected_player]

    if df_range.empty:
        st.warning("No data available for the selected filters.")
    else:
        st.markdown(f"**Date Range:** {date_range[0]} to {date_range[1]}")
        st.markdown(f"**Player:** {selected_player}")

        # 📊 Gráfico de barras por fecha
        st.subheader("📊 Procedures per Day")
        count_by_date = df_range.groupby("DATE").size().reset_index(name="Procedures")
        fig = px.bar(count_by_date, x="DATE", y="Procedures", text="Procedures")
        fig.update_traces(marker_color='lightblue', marker_line_width=1.2)
        st.plotly_chart(
    fig,
    use_container_width=True,
    config={
        "displayModeBar": True,
        "displaylogo": False,
        "modeBarButtonsToRemove": [
            "zoom", "pan", "select", "zoomIn", "zoomOut", "autoScale", "resetScale", "lasso"
        ]
    }
)


        # 📋 Tabla total por jugador
        st.subheader("📋 Total Procedures per Player")
        player_counts = df_range["PLAYER"].value_counts().reset_index()
        player_counts.columns = ["PLAYER", "Count"]
        st.dataframe(player_counts)

        # 📍 Pie chart por PLACE
        st.subheader("📍 Places of Procedure")
        place_counts = df_range["PLACE"].dropna().value_counts().reset_index()
        place_counts.columns = ["PLACE", "Count"]
        fig_pie = px.pie(place_counts, names="PLACE", values="Count", hole=0.3)
        st.plotly_chart(fig_pie, use_container_width=True)

        # 📝 Tabla de razones con responsable
        st.subheader("📝 Reasons for Procedures")
        why_table = df_range[["DATE", "PLAYER", "Why?", "REGISTERED BY:"]].dropna(subset=["Why?"]).reset_index(drop=True)
        st.dataframe(why_table)


# ================================
# 🧍 Treated Body Areas (Dual View)
# ================================
st.subheader("🧍 Treated Body Areas (Beta)")

from PIL import Image
import matplotlib.pyplot as plt

# Diccionario de coordenadas ajustado (2 cm ≈ +25 px de desplazamiento horizontal)
region_coords = {
    # Vista trasera (izquierda)
    "Right Adductor": (115, 270),
    "Left Adductor": (90, 270),
    "Right biceps femoris": (120, 300),
    "Left biceps femoris": (70, 300),
    "Lower back": (95, 215),

    # Vista frontal (derecha)
    "Abdomen": (308, 210),
    "Left Knee": (325, 335),
    "Right anterior rectum": (290, 275),
    "Left anterior rectum": (318, 275),
    "Right ankle": (290, 430),
    "Left ankle": (320, 430),
}


# Contar tratamientos por región en el rango de fechas filtrado
region_counts = df_range["PLACE"].dropna().value_counts()

# Cargar imagen base
body_img = Image.open("assets/body_map.png")

fig, ax = plt.subplots(figsize=(4, 6))
ax.imshow(body_img)
ax.axis("off")

# Normalizar tamaño del círculo
max_count = region_counts.max() if not region_counts.empty else 1

# Pintar solo regiones con conteo > 0
for region, count in region_counts.items():
    if region in region_coords:
        x, y = region_coords[region]
        size = 80 + 200 * (count / max_count)  # Mucho más pequeño
        ax.scatter(x, y, s=size, c="red", alpha=0.5, edgecolors="black", linewidths=0.5)
        ax.text(x, y, str(count), fontsize=6, ha="center", va="center", color="white", weight="bold")
        ax.text(x, y + 12, region, fontsize=5.5, ha="center", va="top", color="black")

st.pyplot(fig)

