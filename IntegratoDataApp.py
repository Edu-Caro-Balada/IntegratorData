import streamlit as st

st.set_page_config(page_title="Performance & Wellness Hub", page_icon="💡", layout="wide")

# Encabezado con logo
st.markdown(
    """
    <div style="display: flex; align-items: center; margin-bottom: 25px;">
        <img src="https://tmssl.akamaized.net//images/wappen/head/45457.png?lm=1534711579"
             width="70" style="margin-right: 15px; opacity: 0.6;">
        <h1 style="margin: 0;">Performance & Wellness Hub</h1>
    </div>
    """,
    unsafe_allow_html=True
)

st.write("Welcome to the **central dashboard** for player monitoring, wellness, and recovery tracking. Choose one of the following sections:")

# Estilo botones en cuadrícula
st.markdown("""
<style>
.grid-container {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 1.5rem;
    margin-top: 30px;
    max-width: 1000px;
}
.grid-button {
    display: flex;
    align-items: center;
    justify-content: center;
    background-color: #f0f2f6;
    border-radius: 10px;
    padding: 2rem 1.5rem;
    text-decoration: none;
    color: black;
    font-size: 1.2rem;
    font-weight: bold;
    border: 1px solid #d0d0d0;
    height: 120px;
    transition: all 0.2s ease;
    text-align: center;
}
.grid-button:hover {
    background-color: #e0e0e0;
    box-shadow: 0 0 8px rgba(0,0,0,0.12);
    cursor: pointer;
}
</style>

<div class="grid-container">
    <a class="grid-button" href="./Wellness">📊 Wellness Dashboard</a>
    <a class="grid-button" href="./Procedures">💆‍♂️ Physiotherapy Procedures</a>
    <a class="grid-button" href="./Calendar">📅 Individual Activity Calendar</a>
    <a class="grid-button" href="./Weight_and_Fat">⚖️ Weight & Fat Tracking</a>
    <a class="grid-button" href="./GPS">📡 GPS Dashboard</a>
</div>
""", unsafe_allow_html=True)

# Footer
st.markdown("---")
st.caption("Developed by Edu Caro • Performance Science Department")
