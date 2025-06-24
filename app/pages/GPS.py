import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# CONFIGURACIÓN
SHEET_URL = "https://docs.google.com/spreadsheets/d/11ntkguPaXrRHnZX9kNguLODWBjpupPz4s8gdbZ75_Ck/"

@st.cache_data(ttl=600)
@st.cache_data(ttl=600)
def load_data():
    df = pd.read_csv(SHEET_URL, dtype=str)
    df['date'] = pd.to_datetime(df['date'], errors='coerce')

    # Convertir texto a float manejando comas como decimales
    def safe_float(x):
        try:
            x = str(x).replace(".", "").replace(",", ".")
            return float(x)
        except:
            return 0.0

    text_cols = ['date', 'day_type', 'session', 'athlete_name']
    numeric_cols = [col for col in df.columns if col not in text_cols]

    for col in numeric_cols:
        df[col] = df[col].apply(safe_float)
    
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

if st.button("🔁 Refresh data from Google Sheets"):
    st.cache_data.clear()
    st.experimental_rerun()

df = load_data()

tab1, tab2, tab3 = st.tabs(["📌 Session Report", "👤 Player Report", "📈 ACWR Summary"])

# TAB 1
with tab1:
    st.subheader("📅 Session Overview")
    dates = pd.to_datetime(df['date']).dt.date.unique()
    selected_date = st.selectbox("Select a session date", sorted(dates, reverse=True))
    sessions = df[pd.to_datetime(df['date']).dt.date == selected_date]['session'].dropna().unique()
    selected_session = st.selectbox("Select session", sessions)

    df_filtered = df[(pd.to_datetime(df['date']).dt.date == selected_date) & (df['session'] == selected_session)]

    # Sumatorios
    st.subheader("📌 Session Totals")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Distance", f"{int(df_filtered.get('total_distance', 0).sum())} m")
        st.metric("MSR Distance", f"{int(df_filtered.get('MSR_dist', 0).sum())} m")
        st.metric("HIR Distance", f"{int(df_filtered.get('hir_dist', 0).sum())} m")
    with col2:
        st.metric("Sprint Distance", f"{int(df_filtered.get('Sprint_dist', 0).sum())} m")
        st.metric("Acc >3", f"{int(df_filtered.get('acc_eff_3', 0).sum())}")
        st.metric("Dcc >3", f"{int(df_filtered.get('dcc_eff_3', 0).sum())}")
    with col3:
        st.metric("Total Duration", f"{int(df_filtered.get('total_duration', pd.Series([0])).mean())} min")
        st.metric("Avg m/min", f"{df_filtered.get('m_min', pd.Series([0])).mean():.0f}")

    # Alerta pisada
    if 'por_desequilibrio_pisada' in df_filtered.columns:
        alerta = df_filtered[(df_filtered['por_desequilibrio_pisada'] < -10) | (df_filtered['por_desequilibrio_pisada'] > 10)]
        if not alerta.empty:
            alerta_texto = ", ".join(
                f"{row['athlete_name']} ({row['por_desequilibrio_pisada']:.1f})"
                for _, row in alerta.iterrows()
            )
            st.warning(f"⚠️ Players with abnormal footstrike imbalance: {alerta_texto}")

    # 📊 Gráficos
    def bar_scatter(y1, y2, name1, name2, ytitle1, ytitle2):
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df_filtered['athlete_name'], y=df_filtered[y1],
                             name=name1, text=df_filtered[y1].astype(int), textposition='outside'))
        fig.add_trace(go.Scatter(x=df_filtered['athlete_name'], y=df_filtered[y2],
                                 name=name2, yaxis='y2', mode='lines+markers+text',
                                 text=df_filtered[y2].round(0).astype(int), textposition='top center'))
        fig.update_layout(yaxis=dict(title=ytitle1),
                          yaxis2=dict(title=ytitle2, overlaying='y', side='right'),
                          height=400)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Total Distance and m/min")
    if 'total_distance' in df_filtered and 'm_min' in df_filtered:
        bar_scatter('total_distance', 'm_min', 'Distance (m)', 'm/min', 'Distance (m)', 'm/min')

    st.subheader("Top Speed and % Max Speed")
    if 'max_speed' in df_filtered and 'por_vel' in df_filtered:
        bar_scatter('max_speed', 'por_vel', 'Max Speed (km/h)', '% Max Speed', 'Speed', '%')

    # Tabla final
    st.subheader("📋 Table")
    st.dataframe(df_filtered, use_container_width=True)

# TAB 2 y 3 los puedes copiar igual si no hay cambios en estructura


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
