import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from langchain.chat_models import ChatOpenAI
from langchain.agents import initialize_agent, Tool, AgentType
from langchain.schema import HumanMessage
import re
from datetime import datetime

# Conexión a la base de datos SQLite
engine = create_engine("sqlite:///transacciones.db")

# Cargar datos desde la base de datos al iniciar
if "transacciones" not in st.session_state:
    try:
        df_db = pd.read_sql("SELECT * FROM transacciones", engine)
    except Exception:
        df_db = pd.DataFrame(columns=["ID", "Fecha", "Categoría", "Cuenta", "Monto"])
    st.session_state.transacciones = df_db

# Título principal
st.title("💼 Mi dashboard financiero")

# ─────────────────────────────
# Registrar nueva transacción
# ─────────────────────────────
with st.expander("➕ Registrar nueva transacción"):
    with st.form("nueva_transaccion"):
        fecha = st.date_input("Fecha")
        categoria = st.selectbox("Categoría", [
            "💵Nomina", "🏠 Vivienda", "💡 Servicios", "🛒 Supermercado", "🚗 Transporte", "🩺 Salud",
            "🍔 Comidas fuera", "🎉 Entretenimiento", "👗 Ropa", "🛍️ Compras", "💄 Belleza", "👶 Hijos"
        ])
        cuenta = st.text_input("Cuenta")
        monto = st.number_input("Monto", min_value=-100000.0, max_value=100000.0, step=10.0)
        submitted = st.form_submit_button("Agregar")

        if submitted:
            next_id = int(st.session_state.transacciones["ID"].max() + 1) if not st.session_state.transacciones.empty else 1
            nueva = pd.DataFrame([{
                "ID": next_id,
                "Fecha": fecha,
                "Categoría": categoria,
                "Cuenta": cuenta,
                "Monto": monto
            }])
            st.session_state.transacciones = pd.concat(
                [st.session_state.transacciones, nueva], ignore_index=True)
            st.session_state.transacciones.to_sql("transacciones", engine, if_exists="replace", index=False)
            st.success("✅ Transacción agregada")
            st.rerun()

    # Mostrar tabla con botón de eliminar por fila
    st.markdown("### 📋 Transacciones registradas")

    df = st.session_state.transacciones
    if not df.empty:
        cols_header = st.columns([1, 2, 2, 2, 2, 1])
        cols_header[0].markdown("**ID**")
        cols_header[1].markdown("**Fecha**")
        cols_header[2].markdown("**Categoría**")
        cols_header[3].markdown("**Cuenta**")
        cols_header[4].markdown("**Monto**")
        cols_header[5].markdown("**Eliminar**")

        for idx, row in df.iterrows():
            cols = st.columns([1, 2, 2, 2, 2, 1])
            cols[0].write(row["ID"])
            cols[1].write(row["Fecha"])
            cols[2].write(row["Categoría"])
            cols[3].write(row["Cuenta"])
            cols[4].write(f"${row['Monto']:,.2f}")
            if cols[5].button("🗑️", key=f"delete_{row['ID']}"):
                st.session_state.transacciones = st.session_state.transacciones[st.session_state.transacciones["ID"] != row["ID"]]
                st.session_state.transacciones.reset_index(drop=True, inplace=True)
                st.session_state.transacciones.to_sql("transacciones", engine, if_exists="replace", index=False)
                st.rerun()
    else:
        st.info("No hay transacciones registradas.")

# ─────────────────────────────
# Cálculos de métricas
# ─────────────────────────────
df = st.session_state.transacciones
ingresos = df[df["Monto"] > 0]["Monto"].sum()
gastos = df[df["Monto"] < 0]["Monto"].sum()
balance = ingresos + gastos
ahorro_pct = (balance / ingresos * 100) if ingresos > 0 else 0

# ─────────────────────────────
# Métricas visuales
# ─────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 Balance", f"${balance:,.2f}")
col2.metric("🟢 Ingresos", f"${ingresos:,.2f}")
col3.metric("🔴 Gastos", f"${gastos:,.2f}")
col4.metric("📈 % de ahorro", f"{ahorro_pct:.1f}%")

# ─────────────────────────────
# Tabla de transacciones
# ─────────────────────────────
st.subheader("📄 Historial de Transacciones")
st.dataframe(df, use_container_width=True)

# ─────────────────────────────
# Herramientas del asistente BILLIE
# ─────────────────────────────
def get_total_spent():
    df = st.session_state.get("transacciones", pd.DataFrame())
    if df.empty:
        return "No hay transacciones registradas."
    total = df[df["Monto"] < 0]["Monto"].sum()
    return f"Has gastado ${abs(total):,.2f}"

def get_food_expenses():
    df = st.session_state.get("transacciones", pd.DataFrame())
    if df.empty:
        return "No hay transacciones registradas."
    filtro = df["Categoría"].str.contains("comida", case=False) | df["Categoría"].str.contains("🍔", na=False)
    total = df[filtro & (df["Monto"] < 0)]["Monto"].sum()
    return f"Has gastado ${abs(total):,.2f} en comida."

def registrar_transaccion_desde_texto(texto):
    try:
        # Buscar monto (positivo o negativo)
        monto = re.search(r"(-?\$?\d+(?:[\.,]\d{1,2})?)", texto)
        monto = float(monto.group().replace("$", "").replace(",", "")) if monto else 0

        # Buscar categoría simple por palabras clave
        categorias = {
            "comida": "🍔 Comidas fuera", "super": "🛒 Supermercado", "salud": "🩺 Salud",
            "transporte": "🚗 Transporte", "ropa": "👗 Ropa", "belleza": "💄 Belleza"
        }
        categoria = next((v for k, v in categorias.items() if k in texto.lower()), "💵Nomina")

        # Buscar cuenta
        cuenta = re.search(r"(tarjeta|banorte|bbva|hsbc|efectivo)", texto.lower())
        cuenta = cuenta.group().capitalize() if cuenta else "General"

        # Buscar fecha
        fecha_match = re.search(r"\d{1,2} de [a-zA-Z]+", texto)
        fecha = datetime.today().date()
        if fecha_match:
            try:
                fecha = datetime.strptime(fecha_match.group() + f" {datetime.today().year}", "%d de %B %Y").date()
            except:
                pass

        # Crear registro
        df = st.session_state.transacciones
        next_id = int(df["ID"].max() + 1) if not df.empty else 1

        nuevo = pd.DataFrame([{
            "ID": next_id,
            "Fecha": fecha,
            "Categoría": categoria,
            "Cuenta": cuenta,
            "Monto": monto
        }])

        st.session_state.transacciones = pd.concat([df, nuevo], ignore_index=True)
        st.session_state.transacciones.to_sql("transacciones", engine, if_exists="replace", index=False)

        return f"✅ Transacción registrada: {categoria}, {cuenta}, ${monto:,.2f} el {fecha}"

    except Exception as e:
        return f"❌ Error al procesar el texto: {e}"

# ─────────────────────────────
# Sección BILLIE en expander
# ─────────────────────────────
with st.expander("🤖 Pregunta a BILLIE (Asistente financiero)", expanded=False):
    try:
        api_key = st.secrets["openrouter"]["api_key"]

        llm = ChatOpenAI(
            openai_api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            model="mistralai/mixtral-8x7b-instruct",
        )

        tools = [
            Tool(
                name="Gasto total",
                func=lambda _: get_total_spent(),
                description="Calcula cuánto he gastado en total"
            ),
            Tool(
                name="Gasto en comida",
                func=lambda _: get_food_expenses(),
                description="Calcula cuánto he gastado en comida"
            ),
            Tool(name="Registrar transacción", 
                 func=lambda text: registrar_transaccion_desde_texto(text),
                 description="Registra transacciones desde descripciones en lenguaje natural")
        ]

        agent = initialize_agent(
            tools=tools,
            llm=llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=False,
        )

        st.markdown("### Preguntas que puedes hacer:")
        col1, col2 = st.columns(2)
        preguntas = {
            "¿Cuánto he gastado en total?": col1.button("💸 ¿Cuánto he gastado?"),
            "¿Cuánto he gastado en comida?": col2.button("🍔 ¿Gasto en comida?")
        }

        for pregunta, presionado in preguntas.items():
            if presionado:
                with st.spinner("BILLIE está pensando..."):
                    respuesta = agent.run(pregunta)
                st.markdown("### Respuesta de BILLIE")
                st.markdown(respuesta)

        st.markdown("### O haz una pregunta personalizada:")
        user_prompt = st.text_input("Escribe tu pregunta:")

        if user_prompt:
            with st.spinner("BILLIE está pensando..."):
                respuesta = agent.run(user_prompt)
            st.markdown("### Respuesta de BILLIE")
            st.markdown(respuesta)

    except Exception as e:
        st.error(f"No se pudo conectar a BILLIE: {e}")
