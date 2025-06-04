import streamlit as st
import pandas as pd

# ---- Page Configuration ----
st.set_page_config(page_title="Fintruth - Simulador de Ahorro", layout="centered")

# ---- Header ----
st.title("💰 Fintruth - Simulador de Ahorro")
st.subheader("Proyecta tu ahorro con interés compuesto")
st.markdown("Ajusta los parámetros y observa cómo crece tu inversión con el tiempo.")
st.divider()

# ---- Input Section ----
st.markdown("### 📊 Parámetros de Simulación")
col1, col2, col3 = st.columns(3)

with col1:
    initial_capital = st.number_input("Capital inicial ($)", min_value=1, value=10000, step=100)

with col2:
    interest_rate_percent = st.selectbox("Tasa de interés anual (%)", list(range(1, 101)), index=4)
with col3:
    years = st.number_input("Años", min_value=1, value=20, step=1)

# Convert interest rate to decimal
interest_rate = interest_rate_percent / 100

# ---- Simulation ----
#years = 20
capital_over_time = [round(initial_capital * (1 + interest_rate) ** year,2) for year in range(years + 1)]

df = pd.DataFrame({
    "Año": list(range(years + 1)),
    "Valor acumulado ($)": capital_over_time
})

# ---- Results ----
st.markdown("### 📈 Crecimiento proyectado del ahorro")
st.line_chart(df.set_index("Año"))

# ---- Summary ----
final_amount = capital_over_time[-1]

st.markdown(f"**📌 Resultado:** Después de **{years} años**, tu capital crecería a **${final_amount:,.2f}** con una tasa de interés del **{interest_rate_percent}% anual**.")

