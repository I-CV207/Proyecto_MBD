from langchain.agents import Tool, initialize_agent, AgentType
from langchain.chat_models import ChatOpenAI
from sqlalchemy import text
from utils import construir_prompt_recomendaciones_fondos, cargar_fondos_desde_db
import streamlit as st


def crear_agente_inversion(username, engine):
    llm = ChatOpenAI(
        #openai_api_key=st.secrets["openrouter"]["api_key"],
        #base_url="https://openrouter.ai/api/v1",
        #model="mistralai/mixtral-8x7b-instruct",
        openai_api_key=st.secrets["openai"]["api_key"],
        model="gpt-4",
    )

    # ────────────────────────────────────────────────────────
    # Función interna para generar el prompt con perfil y fondos
    # ────────────────────────────────────────────────────────
    def generar_prompt(username):
        with engine.connect() as conn:
            perfil_result = conn.execute(
                text("SELECT * FROM perfiles_ahorro WHERE usuario = :u"),
                {"u": username}
            ).fetchone()

        if perfil_result is None:
            return "⚠️ El usuario aún no ha definido su perfil de ahorro."

        perfil_usuario = perfil_result[2]  # Ajusta si es otro índice
        df_fondos = cargar_fondos_desde_db(engine)
        return construir_prompt_recomendaciones_fondos(df_fondos, perfil_usuario)

    # ────────────────────────────────────────────────────────
    # Definir Tool con acceso sólo a la función de inversión
    # ────────────────────────────────────────────────────────
    tools = [
        Tool(
            name="recomendaciones_fondos",
            func=generar_prompt,
            description="Genera recomendaciones de inversión basadas en el perfil del usuario."
        )
    ]

    # ────────────────────────────────────────────────────────
    # Inicializar agente con solo este conjunto de herramientas
    # ────────────────────────────────────────────────────────
    return initialize_agent(
        tools,
        llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True
    )
