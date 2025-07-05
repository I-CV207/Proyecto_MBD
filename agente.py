from langchain.chat_models import ChatOpenAI
from langchain.agents import initialize_agent, Tool, AgentType
from utils import (
    get_total_spent, get_total_earned, registrar_transaccion_desde_texto, get_ultimas_transacciones,
    resumen_mensual, get_balance_actual, get_gastos_por_categoria,
    get_promedio_gastos, proyeccion_saldo_fin_mes, ranking_gastos_categorias, ranking_ingresos_categorias,
    porcentaje_gastos_por_categoria, alerta_gasto_excesivo, sugerencia_ahorro, buscar_transacciones,
    evolucion_balance, comparativa_gastos_mensual, gastos_recurrentes, sugerencia_presupuesto, simulador_sin_gasto_en,get_total_ahorrado, get_total_asignado_metas, get_ahorro_disponible,
    get_resumen_metas, get_recomendacion_asignacion,construir_presupuesto_asistido
)
import streamlit as st

def crear_agente(username,engine):
    llm = ChatOpenAI(
        #openai_api_key=st.secrets["openrouter"]["api_key"],
        #base_url="https://openrouter.ai/api/v1",
        #model="mistralai/mixtral-8x7b-instruct",
        openai_api_key=st.secrets["openai"]["api_key"],
        model="gpt-4",
        #openai_api_key=st.secrets["openrouter2"]["api_key"],
        #base_url="https://openrouter.ai/api/v1",
        #model="deepseek/deepseek-chat-v3-0324:free",

    )

    tools = [
        Tool(
            name="Gasto total",
            func=lambda _: get_total_spent(username),
            description="Devuelve el total de dinero gastado por el usuario."
        ),
        Tool(
            name="Ingreso total",
            func=lambda _: get_total_earned(username),
            description="Devuelve el total de dinero generado por el usuario."
        ),
        Tool(
            name="Gastos por categoria",
            func=lambda t: get_gastos_por_categoria(t, username),
            description="Obtiene los gastos por categoría especificada."
        ),
        Tool(
            name="Registrar transacción",
            func=lambda t: registrar_transaccion_desde_texto(t, username,engine),
            description="Registra una transacción a partir de un texto como 'gasté 200 en comida con tarjeta'."
        ),
        Tool(
            name="Ver últimas transacciones", 
            func=lambda _: get_ultimas_transacciones(), 
            description="Muestra los últimos movimientos."
        ),
        Tool(
            name="Resumen mensual", 
            func=lambda _: resumen_mensual(), 
            description="Muestra resumen mensual de ingresos y egresos."
        ),
        Tool(
            name="Balance actual", 
            func=lambda _: get_balance_actual(), 
            description="Muestra el balance acumulado."
        ),
        # FUNCIONES AVANZADAS:
        Tool(
            name="Promedio de gastos",
            func=lambda p: get_promedio_gastos(periodo=p if p else "mensual", username=username),
            description="Devuelve el promedio de gastos diario, semanal o mensual. Usa como input 'diario', 'semanal' o 'mensual'."
        ),
        Tool(
            name="Proyección de saldo fin de mes",
            func=lambda _: proyeccion_saldo_fin_mes(username),
            description="Estima el saldo que tendrá el usuario al final del mes si mantiene su ritmo de gasto/ingreso."
        ),
        Tool(
            name="Ranking gastos por categoría",
            func=lambda _: ranking_gastos_categorias(username),
            description="Muestra las categorías donde el usuario ha gastado más."
        ),
        Tool(
            name="Ranking ingresos por categoría",
            func=lambda _: ranking_ingresos_categorias(username),
            description="Muestra las categorías de ingresos más importantes."
        ),
        Tool(
            name="Porcentaje gastos por categoría",
            func=lambda _: porcentaje_gastos_por_categoria(username),
            description="Devuelve el porcentaje del gasto que representa cada categoría."
        ),
        Tool(
            name="Alerta gasto excesivo",
            func=lambda _: alerta_gasto_excesivo(username),
            description="Alerta si el usuario gasta mucho más que su promedio habitual."
        ),
        Tool(
            name="Sugerencia de ahorro",
            func=lambda _: sugerencia_ahorro(username),
            description="Sugiere una meta de ahorro reduciendo un poco los gustos."
        ),
        Tool(
            name="Buscar transacciones",
            func=lambda palabra: buscar_transacciones(palabra, username),
            description="Busca transacciones por palabra clave o descripción."
        ),
        Tool(
            name="Evolución de balance",
            func=lambda _: evolucion_balance(username).to_string(index=False),
            description="Muestra la evolución del balance a lo largo del tiempo."
        ),
        Tool(
            name="Comparativa de gastos mensual",
            func=lambda _: comparativa_gastos_mensual(username),
            description="Compara los gastos mes a mes."
        ),
        Tool(
            name="Gastos recurrentes",
            func=lambda _: gastos_recurrentes(username),
            description="Detecta gastos recurrentes como suscripciones."
        ),
        Tool(
            name="Sugerencia presupuesto mensual",
            func=lambda _: sugerencia_presupuesto(username),
            description="Sugiere un presupuesto mensual personalizado."
        ),
        Tool(
            name="Simulador: sin gasto en categoría",
            func=lambda c: simulador_sin_gasto_en(c, username),
            description="Simula el balance si dejas de gastar en cierta categoría. Especifica la categoría como input."
        ),
        Tool(name="Ver total ahorrado", 
             func=lambda x: get_total_ahorrado(engine, username), 
             description="Muestra el total ahorrado en Metas financieras 💰"
        ),
        Tool(name="Ver total asignado", 
             func=lambda x: get_total_asignado_metas(engine, username), 
             description="Muestra cuánto del ahorro está asignado a metas."
        ),
        Tool(name="Ver ahorro disponible", 
            func=lambda x: get_ahorro_disponible(engine, username), 
            description="Muestra el ahorro no asignado."
        ),
        Tool(name="Ver resumen de metas", 
            func=lambda x: get_resumen_metas(engine, username), 
            description="Muestra el resumen y progreso de todas las metas."
        ),
        Tool(name="Recomendación de asignación", 
            func=lambda x: get_recomendacion_asignacion(engine, username), 
            description="Sugiere cómo distribuir el ahorro disponible entre las metas."
        ),
        Tool(name="Asistente de presupuesto",
        func=construir_presupuesto_asistido,
        description="Guía al usuario para construir su presupuesto mensual basado en su ingreso y estilo de vida."
        ),
    ]

    agent = initialize_agent(
        tools,
        llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        handle_parsing_errors=True,
        verbose=True
    )

    return agent
