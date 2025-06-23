import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.lines import Line2D
import datetime

st.set_page_config(layout="wide",page_icon="📅")

@st.cache_data(ttl=600)
def load_calendar_data():
    url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSMsjTKKdu36YrJAL2IVFuXVhBBHSMx99DJPUp1CGq7RufXf2dNRlATMqa8gLWb1VZJ2kWZgO82TNVa/pub?gid=1443408897&single=true&output=csv"
    df = pd.read_csv(url)
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce").dt.date
    df.dropna(subset=["Date"], inplace=True)
    df["Player"] = df["Player"].astype(str).str.split(", ")
    df = df.explode("Player")
    df["Workout"] = df["Workout"].str.strip()
    return df

df = load_calendar_data()

# Filtros
# Filtros previos necesarios
min_date = df["Date"].min()
max_date = df["Date"].max()
date_range = st.sidebar.date_input("Select Date Range", [max_date - datetime.timedelta(days=30), max_date])
available_players = sorted(df["Player"].unique())  # 🔁 Definido antes de usar
selected_player = st.sidebar.selectbox("Select Player", ["All"] + available_players)

# Mostrar título con nombre si se selecciona solo un jugador
player_title = f" – {selected_player}" if selected_player != "All" else ""
st.markdown(
    f"""
    <div style="display: flex; align-items: center; margin-bottom: 10px;">
        <img src="https://tmssl.akamaized.net//images/wappen/head/45457.png?lm=1534711579"
             width="80"
             style="margin-right: 15px; opacity: 0.6;">
        <h1 style="margin: 0;">📅 Activity Calendar{player_title}</h1>
    </div>
    """,
    unsafe_allow_html=True
)

# Botón para refrescar datos
if st.button("🔄 Refresh Data"):
    st.cache_data.clear()

if len(date_range) != 2:
    st.warning("⚠️ Please select a valid start and end date.")
else:
    start_date, end_date = date_range
    df_filtered = df[(df["Date"] >= start_date) & (df["Date"] <= end_date)]
    if selected_player != "All":
        df_filtered = df_filtered[df_filtered["Player"] == selected_player]

    if df_filtered.empty:
        st.warning("No activity data available for the selected filters.")
    else:
        # Preparar calendario
        calendar = df_filtered.groupby(["Player", "Date"])["Workout"].apply(lambda x: list(set(x))).unstack(fill_value=[])
        all_dates = pd.date_range(start=start_date, end=end_date).date
        calendar = calendar.reindex(columns=all_dates, fill_value=[])

        unique_workouts = sorted({w for sublist in df_filtered["Workout"].dropna().apply(lambda x: x.split(", ")) for w in sublist})
        colors = plt.cm.tab20.colors[:len(unique_workouts)]
        color_map = dict(zip(unique_workouts, colors))

        fig, ax = plt.subplots(figsize=(len(calendar.columns) * 0.28, len(calendar.index) * 0.20))
        row_height = 0.7 # Más compacto

        # Fondo general con bordes redondeados
        background = FancyBboxPatch((0, 0), len(calendar.columns), len(calendar.index),
                                    boxstyle="round,pad=0.02", linewidth=0,
                                    facecolor="#f0f0f0", edgecolor="#f0f0f0", zorder=0)
        ax.add_patch(background)

        for i, player in enumerate(calendar.index):
            for j, date in enumerate(calendar.columns):
                workouts = calendar.loc[player, date]
                if not workouts:
                    rect = FancyBboxPatch((j, i + (1 - row_height) / 2), 1, row_height,
                                          boxstyle="round,pad=0.02", linewidth=0.4,
                                          edgecolor="lightgray", facecolor='white')
                    ax.add_patch(rect)
                else:
                    height = row_height / len(workouts)
                    for k, workout in enumerate(workouts):
                        rect = FancyBboxPatch((j, i + (1 - row_height) / 2 + k * height), 1, height,
                                              boxstyle="round,pad=0.02", linewidth=0.4,
                                              edgecolor="lightgray", facecolor=color_map.get(workout, "gray"))
                        ax.add_patch(rect)

        ax.set_xticks(range(len(calendar.columns)))
        ax.set_xticklabels([d.strftime("%d-%b") for d in calendar.columns], rotation=45, ha="right", fontsize=7)
        ax.set_yticks([i + 0.5 - (1 - row_height) / 2 for i in range(len(calendar.index))])
        ax.set_yticklabels(calendar.index, fontsize=8, va='center')
        ax.set_xlim(0, len(calendar.columns))
        ax.set_ylim(0, len(calendar.index))
        ax.invert_yaxis()

        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.set_title("")

        # Leyenda
        legend_elements = [Line2D([0], [0], marker='s', color='w', label=w,
                                  markersize=8, markerfacecolor=color_map[w]) for w in unique_workouts]
        ax.legend(handles=legend_elements, bbox_to_anchor=(1.01, 1), loc='upper left', borderaxespad=0., fontsize=8)

        ax.tick_params(axis='both', which='both', length=0)
        plt.tight_layout()
        st.pyplot(fig)


        # ================================
        # 📊 Bar Chart by Player & Workout
        # ================================

        st.subheader("📊 Activity Count per Player and Workout")

        # Expand multientries
        df_expanded = df_filtered.copy()
        df_expanded["Workout"] = df_expanded["Workout"].str.split(", ")
        df_expanded = df_expanded.explode("Workout")

        # Agrupar y contar
        summary = df_expanded.groupby(["Player", "Workout"]).size().unstack(fill_value=0)

        # Crear gráfico de barras apiladas
        fig_bar, ax_bar = plt.subplots(figsize=(10, 5))
        summary.plot(kind="bar", stacked=True, ax=ax_bar, colormap="tab20")

        # Añadir etiquetas a cada segmento de barra
        for i, player in enumerate(summary.index):
            bottom = 0
            for workout in summary.columns:
                value = summary.loc[player, workout]
                if value > 0:
                    ax_bar.text(i, bottom + value / 2, str(int(value)),
                                ha='center', va='center', fontsize=8, color='white')
                    bottom += value

        ax_bar.set_ylabel("Number of Activities")
        ax_bar.set_xlabel("")
        ax_bar.legend(title="Workout", bbox_to_anchor=(1.05, 1), loc="upper left")
        plt.tight_layout()
        st.pyplot(fig_bar)


        # ================================
        # 🏷️ Etiquetas de conteo por actividad
        # ================================
        st.subheader("🏷️ Total Activities by Type")

        activity_totals = df_expanded["Workout"].value_counts()

        cols = st.columns(len(activity_totals))
        for i, (activity, count) in enumerate(activity_totals.items()):
            with cols[i]:
                st.metric(label=activity, value=int(count))

        # Tabla de detalles
        st.subheader("📋 Activity Details")
        df_details = df_filtered[["Date", "Player", "Details"]].dropna().sort_values(by="Date")
        st.dataframe(df_details.reset_index(drop=True), use_container_width=True)