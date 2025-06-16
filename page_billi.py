import streamlit as st
import sqlite3
from langchain.agents import initialize_agent, Tool, AgentType
from langchain.chat_models import ChatOpenAI
from langchain.tools import tool
from langchain.schema import HumanMessage
from guardrails import validate_prompt
import os

# Configuración de la página (debe ir primero)

st.title("💬 BILLIE - Agente de Productos Financieros")

# API key para OpenRouter
api_key = st.secrets["openrouter"]["api_key"]

llm = ChatOpenAI(
    openai_api_key=api_key,
    base_url="https://openrouter.ai/api/v1",
    model="mistralai/mixtral-8x7b-instruct",
    temperature=0.2,
    max_tokens=900,
)

# ────────────────────────────────────────────────────────
# Herramienta: búsqueda + resumen en múltiples tablas
# ────────────────────────────────────────────────────────
@tool
def buscar_y_resumir(pregunta: str) -> str:
    """
    Consulta las tres tablas de finai.db y genera un resumen de los datos financieros relacionados.
    """
    conn = sqlite3.connect("finai.db")  # Ruta ajustada al archivo subido
    cursor = conn.cursor()
    query = f"%{pregunta.lower().strip()}%"

    resultados = []

    # 1. Buscar en documents
    cursor.execute("""
        SELECT 'Documento' as tipo, d.local_path, substr(d.text, 1, 500)
        FROM documents d
        WHERE lower(d.text) LIKE ?
        LIMIT 3
    """, (query,))
    resultados += cursor.fetchall()

    # 2. Buscar en products
    cursor.execute("""
        SELECT 'Producto' as tipo, p.url, p.title || ' - ' || p.slug
        FROM products p
        WHERE lower(p.title) LIKE ? OR lower(p.slug) LIKE ? OR lower(p.url) LIKE ?
        LIMIT 3
    """, (query, query, query))
    resultados += cursor.fetchall()

    # 3. Buscar en institutions
    cursor.execute("""
        SELECT 'Institución' as tipo, i.slug, i.slug
        FROM institutions i
        WHERE lower(i.slug) LIKE ?
        LIMIT 3
    """, (query,))
    resultados += cursor.fetchall()

    conn.close()

    if not resultados:
        return "❌ No encontré información relevante en la base de datos."

    resumen_preliminar = ""
    raw_info = ""
    for tipo, campo1, campo2 in resultados:
        if tipo == "Documento":
            resumen_preliminar += f"\n🔹 *{tipo}*\n📄 [Ver documento]({campo1})\n📝 {campo2.strip()}\n"
        else:
            resumen_preliminar += f"\n🔹 *{tipo}*\n🔗 {campo1}\n📝 {campo2.strip()}\n"
        raw_info += f"{tipo}:\nRuta o enlace: {campo1}\nContenido: {campo2.strip()}\n\n"

    prompt_resumen = f"""
Tengo la siguiente información financiera extraída de una base de datos. Resume los hallazgos de forma clara para un usuario sin conocimientos técnicos. Si hay información sobre tasas, beneficios, restricciones o instituciones, inclúyela en el resumen.

{raw_info}

Resumen:
"""
    resumen = llm([HumanMessage(content=prompt_resumen)]).content
    return f"🔎 Resultados encontrados:\n{resumen_preliminar}\n\n🧠 **Resumen automático**:\n{resumen}"

# Agente con herramienta
tools = [buscar_y_resumir]
agente = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=False
)

# Entrada del usuario
if "history" not in st.session_state:
    st.session_state.history = []

for msg in st.session_state.history:
    st.chat_message(msg["role"]).markdown(msg["content"])

if prompt := st.chat_input("Pregunta sobre finanzas personales, banca o inversión…"):
    valid, refusal = validate_prompt(prompt)
    st.session_state.history.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)

    if not valid:
        st.session_state.history.append({"role": "assistant", "content": refusal})
        st.chat_message("assistant").markdown(refusal)
    else:
        response = llm([HumanMessage(content=prompt)])
        st.session_state.history.append({"role": "assistant", "content": response.content})
        st.chat_message("assistant").markdown(response.content)
