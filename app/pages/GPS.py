import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import gspread
import os
import subprocess
from oauth2client.service_account import ServiceAccountCredentials

# CONFIGURACIÓN

SHEET_URL = "https://docs.google.com/spreadsheets/d/11ntkguPaXrRHnZX9kNguLODWBjpupPz4s8gdbZ75_Ck/edit"
SHEET_NAME = "Hoja 1"
SERVICE_ACCOUNT_FILE = "credentials/credentials.json"  # o simplemente "credentials.json" si va en raíz
RSCRIPT_PATH = "C:/Program Files/R/R-4.5.1/bin/Rscript.exe"  # Verifica que sea correcta
SCRIPT_R = "r_scripts/actualizar_catapult.R"  # Esta sí está mal, cámbiala


# FUNCIONES
def safe_float(x):
    try:
        x = str(x).strip()
        if "," in x:
            x = x.replace(".", "").replace(",", ".")
        return float(x)
    except:
        return 0.0

@st.cache_data(ttl=600)
def load_data():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(SHEET_URL)
    ws = sheet.worksheet(SHEET_NAME)

    data = ws.get_all_values()
    headers, rows = data[0], data[1:]
    df = pd.DataFrame(rows, columns=headers)

    text_cols = ['date', 'day_type', 'session', 'athlete_name']
    numeric_cols = [col for col in df.columns if col not in text_cols]

    for col in numeric_cols:
        df[col] = df[col].apply(safe_float)
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    return df

# INTERFAZ
st.set_page_config(layout="wide", page_title="GPS Dashboard", page_icon="📈")

st.markdown("""
    <div style="display: flex; align-items: center; margin-bottom: 10px;">
        <img src="https://tmssl.akamaized.net//images/wappen/head/45457.png?lm=1534711579"
             width="80"
             style="margin-right: 15px; opacity: 0.6;">
        <h1 style="margin: 0;">📊 GPS Dashboard</h1>
    </div>
    """, unsafe_allow_html=True)
# BOTONES
with st.expander("🔄 Update Options"):
    col1, col2 = st.columns(2)

    with col1:
        day_type = st.selectbox("📅 What is the day type?", ["MD", "MD-1", "MD-2", "MD-3", "MD-4", "MD-5", "MD+1", "MD+2", "PRE"])
        day_tipe = st.text_input("🆚 Opponent") if day_type == "MD" else "TRAINING"

        if st.button("🚀 Run R script (Catapult sync)"):

            try:
                with open("log_r_output.txt", "w", encoding="utf-8") as f_out, \
                    open("log_r_error.txt", "w", encoding="utf-8") as f_err:

                    env = {"DAY_TYPE": day_type, "DAY_TIPE": day_tipe, **os.environ}
                    result = subprocess.run(
                        [RSCRIPT_PATH, "--vanilla", SCRIPT_R],
                        stdout=f_out, stderr=f_err, text=True, env=env
                    )

                if result.returncode == 0:
                    st.success("✅ R script executed successfully.")
                    with open("log_r_output.txt", "r", encoding="utf-8", errors="replace") as f:
                        st.code(f.read())
                else:
                    st.error("❌ Error in R script.")
                    with open("log_r_error.txt", "r", encoding="utf-8", errors="replace") as f:
                        st.code(f.read())

            except Exception as e:
                st.error(f"Exception occurred: {str(e)}")

    with col2:
        if st.button("🔁 Refresh data from Google Sheets"):
            st.cache_data.clear()
            st.success("Data cache cleared. Reloading...")

# CARGA DE DATOS
df = load_data()

# TABS
tab1, tab2, tab3 = st.tabs(["📌 Session Report", "👤 Player Report", "📈 ACWR Summary"])

# TAB 1 - Session Report
with tab1:
    st.subheader("📅 Session Overview")

    dates = pd.to_datetime(df['date']).dt.date.unique()
    selected_date = st.selectbox("Select a session date", sorted(dates, reverse=True))
    sessions = df[pd.to_datetime(df['date']).dt.date == selected_date]['session'].dropna().unique()
    selected_session = st.selectbox("Select session", sessions)

    df_filtered = df[(pd.to_datetime(df['date']).dt.date == selected_date) & (df['session'] == selected_session)]

    # 🔢 Sumatorios
    st.subheader("📌 Session Totals")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Distance", f"{int(df_filtered['total_distance'].sum())} m")
        st.metric("MSR Distance", f"{int(df_filtered['MSR_dist'].sum())} m")
        st.metric("HIR Distance", f"{int(df_filtered['hir_dist'].sum())} m")
    with col2:
        st.metric("Sprint Distance", f"{int(df_filtered['Sprint_dist'].sum())} m")
        st.metric("Acc >3", f"{int(df_filtered['acc_eff_3'].sum())}")
        st.metric("Dcc >3", f"{int(df_filtered['dcc_eff_3'].sum())}")
    with col3:
        st.metric("Total Duration", f"{int(df_filtered['total_duration'].mean())} min")
        st.metric("Avg m/min", f"{df_filtered['m_min'].mean():.0f}")

    #Alerta desequilibrio pisada
    alerta = df_filtered[(df_filtered['por_desequilibrio_pisada'] < -10) | (df_filtered['por_desequilibrio_pisada'] > 10)]
    if not alerta.empty:
        alerta_texto = ", ".join(
            f"{row['athlete_name']} ({row['por_desequilibrio_pisada']:.1f})"
            for _, row in alerta.iterrows()
        )
        st.warning(f"⚠️ Players with abnormal footstrike imbalance (< -10 or > 10): {alerta_texto}")


    # 📊 Distancia y m/min
    st.subheader("Total Distance and m/min")
    fig1 = go.Figure()
    fig1.add_trace(go.Bar(x=df_filtered['athlete_name'], y=df_filtered['total_distance'],
                          name='Distance (m)', text=df_filtered['total_distance'].astype(int),
                          textposition='outside'))
    fig1.add_trace(go.Scatter(x=df_filtered['athlete_name'], y=df_filtered['m_min'],
                              name='m/min', yaxis='y2', mode='lines+markers+text',
                              text=df_filtered['m_min'].round(0).astype(int), textposition='top center'))
    fig1.update_layout(yaxis=dict(title="Distance (m)"),
                       yaxis2=dict(title="m/min", overlaying="y", side="right"),
                       height=400)
    st.plotly_chart(fig1, use_container_width=True)

    # ⚡ Velocidad máxima y % max
    st.subheader("Top Speed and % Max Speed")
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=df_filtered['athlete_name'], y=df_filtered['max_speed'],
                          name='Max Speed (km/h)', text=df_filtered['max_speed'].round(0).astype(int),
                          textposition='outside'))
    fig2.add_trace(go.Scatter(x=df_filtered['athlete_name'], y=(df_filtered['por_vel'] * 100),
                              name='% Max Speed', yaxis='y2', mode='lines+markers+text',
                              text=(df_filtered['por_vel'] * 100).round(0).astype(int),
                              textposition='top center'))
    fig2.update_layout(yaxis=dict(title="Speed (km/h)"),
                       yaxis2=dict(title="% Max", overlaying="y", side="right"),
                       height=400)
    st.plotly_chart(fig2, use_container_width=True)

    # 📈 MSR, HIR y Sprint
    st.subheader("MSR, HIR and Sprint Distance")
    fig3 = go.Figure(data=[
        go.Bar(name='MSR', x=df_filtered['athlete_name'], y=df_filtered['MSR_dist'],
               text=df_filtered['MSR_dist'].astype(int), textposition='outside'),
        go.Bar(name='HIR', x=df_filtered['athlete_name'], y=df_filtered['hir_dist'],
               text=df_filtered['hir_dist'].astype(int), textposition='outside'),
        go.Bar(name='Sprint', x=df_filtered['athlete_name'], y=df_filtered['Sprint_dist'],
               text=df_filtered['Sprint_dist'].astype(int), textposition='outside')
    ])
    fig3.update_layout(barmode='group', height=400)
    st.plotly_chart(fig3, use_container_width=True)

    # 🦵 Aceleraciones y frenadas
    st.subheader("Accelerations and Decelerations >3")
    fig4 = go.Figure(data=[
        go.Bar(name='Acc >3', x=df_filtered['athlete_name'], y=df_filtered['acc_eff_3'],
               text=df_filtered['acc_eff_3'].astype(int), textposition='outside'),
        go.Bar(name='Dcc >3', x=df_filtered['athlete_name'], y=df_filtered['dcc_eff_3'],
               text=df_filtered['dcc_eff_3'].astype(int), textposition='outside'),
    ])
    fig4.update_layout(barmode='group', height=400)
    st.plotly_chart(fig4, use_container_width=True)

    # 📋 Tabla
    st.subheader("📋 Table")
    st.dataframe(df_filtered[['athlete_name', 'total_distance', 'm_min', 'Sprint_dist', 'acc_eff_3', 'dcc_eff_3', 'por_vel']].sort_values(by='m_min', ascending=False), use_container_width=True)


# TAB 2 - Player Report
# TAB 2 - Player Report
with tab2:
    st.subheader("👤 Individual Report")

    player = st.selectbox("Select player", sorted(df['athlete_name'].dropna().unique()))
    date_range = st.date_input("Select date range", [])

    if len(date_range) != 2:
        st.warning("Please select a start and end date.")
    else:
        start_date, end_date = date_range
        dff = df[(df['athlete_name'] == player) &
                 (df['date'] >= pd.to_datetime(start_date)) &
                 (df['date'] <= pd.to_datetime(end_date))]

        st.header(player)

        # Top metrics in horizontal layout
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Max Speed", f"{dff['max_speed'].max():.2f} km/h")
        with col2:
            st.metric("Max Acceleration", f"{dff['max_accel'].max():.2f} m/s²")
        with col3:
            st.metric("Max Deceleration", f"{dff['max_decc'].min():.2f} m/s²")

        # Total distance
        st.subheader("📏 Total Distance Over Time")
        fig_dist = go.Figure()
        fig_dist.add_trace(go.Bar(x=dff['date'], y=dff['total_distance'].astype(int),
                                  name='Total Distance', text=dff['total_distance'].astype(int),
                                  textposition='outside'))
        fig_dist.update_layout(yaxis_title="Distance (m)", height=400)
        st.plotly_chart(fig_dist, use_container_width=True)

        # MSR, HIR, Sprint
        st.subheader("🏃 MSR, HIR and Sprint Distance")
        fig_msr = go.Figure(data=[
            go.Bar(name='MSR', x=dff['date'], y=dff['MSR_dist'].astype(int),
                   text=dff['MSR_dist'].astype(int), textposition='outside'),
            go.Bar(name='HIR', x=dff['date'], y=dff['hir_dist'].astype(int),
                   text=dff['hir_dist'].astype(int), textposition='outside'),
            go.Bar(name='Sprint', x=dff['date'], y=dff['Sprint_dist'].astype(int),
                   text=dff['Sprint_dist'].astype(int), textposition='outside'),
        ])
        fig_msr.update_layout(barmode='group', height=400)
        st.plotly_chart(fig_msr, use_container_width=True)

        # Accelerations & Decelerations
        st.subheader("⚡ Accelerations and Decelerations")
        fig_acc = go.Figure(data=[
            go.Bar(name='Acc >3', x=dff['date'], y=dff['acc_eff_3'].astype(int),
                   text=dff['acc_eff_3'].astype(int), textposition='outside'),
            go.Bar(name='Dcc >3', x=dff['date'], y=dff['dcc_eff_3'].astype(int),
                   text=dff['dcc_eff_3'].astype(int), textposition='outside'),
        ])
        fig_acc.update_layout(barmode='group', height=400)
        st.plotly_chart(fig_acc, use_container_width=True)

        # ACWR Progression
        st.subheader("📈 ACWR Progression")
        for acwr_var in ['dist', 'hir', 'acc']:
            last_row = dff.dropna(subset=[f'acwr_{acwr_var}']).sort_values(by='date').tail(1)
            if not last_row.empty:
                last_ratio = last_row[f'acwr_{acwr_var}'].values[0]
                st.metric(f"ACWR {acwr_var.upper()} (last session)", f"{last_ratio:.2f}")

            fig = go.Figure()
            fig.add_trace(go.Bar(x=dff['date'], y=dff[f'acute_{acwr_var}'].astype(int),
                                 name='Acute', text=dff[f'acute_{acwr_var}'].astype(int),
                                 textposition='outside'))
            fig.add_trace(go.Bar(x=dff['date'], y=dff[f'chronic_{acwr_var}'].astype(int),
                                 name='Chronic', text=dff[f'chronic_{acwr_var}'].astype(int),
                                 textposition='outside'))
            fig.add_trace(go.Scatter(x=dff['date'], y=dff[f'acwr_{acwr_var}'],
                                     name='Ratio', yaxis='y2',
                                     mode='lines+markers+text',
                                     text=dff[f'acwr_{acwr_var}'].round(2),
                                     textposition='top center'))

            fig.update_layout(
                yaxis=dict(title='Load'),
                yaxis2=dict(title='ACWR', overlaying='y', side='right'),
                title=f"ACWR - {acwr_var.upper()}",
                height=400,
                barmode='group'
            )
            st.plotly_chart(fig, use_container_width=True)


# TAB 3 - ACWR Summary
with tab3:
    st.subheader("📈 ACWR Summary")

    # Fecha sin hora
    available_dates = sorted(pd.to_datetime(df['date']).dt.date.unique(), reverse=True)
    selected_date2 = st.selectbox("Select a date for ACWR summary", available_dates)
    df_filtered2 = df[pd.to_datetime(df['date']).dt.date == selected_date2]

    for var in ['dist', 'hir', 'acc']:
        st.subheader(f"ACWR - {var.upper()}")

        # Alertas solo para amarillos y rojos
        alerta_rows = []
        for _, row in df_filtered2.iterrows():
            ratio = row.get(f'acwr_{var}', None)
            if pd.notna(ratio):
                if 0.7 <= ratio < 0.8 or 1.2 < ratio <= 1.4:
                    color = "🟡"
                    alerta_rows.append(f"{row['athlete_name']}: {ratio:.2f} {color}")
                elif ratio < 0.7 or ratio > 1.4:
                    color = "🔴"
                    alerta_rows.append(f"{row['athlete_name']}: {ratio:.2f} {color}")
        if alerta_rows:
            st.warning("⚠️ Players with concerning ACWR values:\n\n• " + "\n• ".join(alerta_rows))

        # Gráfico
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_filtered2['athlete_name'],
            y=df_filtered2[f'acute_{var}'],
            name='Acute',
            text=df_filtered2[f'acute_{var}'].astype(int),
            textposition='outside'
        ))
        fig.add_trace(go.Bar(
            x=df_filtered2['athlete_name'],
            y=df_filtered2[f'chronic_{var}'],
            name='Chronic',
            text=df_filtered2[f'chronic_{var}'].astype(int),
            textposition='outside'
        ))
        fig.add_trace(go.Scatter(
            x=df_filtered2['athlete_name'],
            y=df_filtered2[f'acwr_{var}'],
            mode='lines+markers+text',
            name='ACWR Ratio',
            yaxis='y2',
            text=df_filtered2[f'acwr_{var}'].round(2),
            textposition='top center'
        ))

        fig.update_layout(
            barmode='group',
            height=400,
            yaxis=dict(title='Load'),
            yaxis2=dict(title='ACWR', overlaying='y', side='right')
        )
        st.plotly_chart(fig, use_container_width=True)
