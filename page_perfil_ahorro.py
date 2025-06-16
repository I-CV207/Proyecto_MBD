import streamlit as st
import pandas as pd
import joblib
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage

# Cargar modelo y columnas
model = joblib.load("modelos/modelo_perfil_ahorro.pkl")
columnas_modelo = joblib.load("modelos/columnas_modelo.pkl")

st.title("🧠 Clasificador de Perfil de Ahorro")

st.markdown("Completa el siguiente formulario para conocer tu perfil financiero:")

# Entradas del usuario
edad = st.slider("Edad", 18, 99, 30)
sexo = st.selectbox("Sexo", ["Hombre", "Mujer"])
escolaridad = st.selectbox("Grado de estudios", [
    "Primaria", "Secundaria", "Preparatoria o bachillerato",
    "Licenciatura o ingenieria (profesional)", "Posgrado"
])
estado_civil = st.selectbox("Estado civil", [
    "Es soltera(o)", "Esta casada(o)", "Esta separada(o)", "Es viuda(o)"
])
actividad = st.selectbox("Actividad económica", [
    "Trabajo por lo menos una hora", 
    "Es persona jubilada o pensionada", 
    "Se dedica a los quehaceres del hogar o al cuidado de algún familiar", 
    "Estudia", 
    "No realiza ninguna actividad"
])
salario = st.selectbox("Rango de salario mensual", ["0-10K", "10K-19K", "20K-40K", "40K+"])
presupuesto = st.radio("¿Llevas presupuesto?", ["Si", "No"])
anota_gastos = st.radio("¿Anotas tus gastos?", ["Si", "No"])
separa_deudas = st.radio("¿Separas dinero para pagar deudas?", ["Si", "No"])
suficiencia = st.radio("¿Tienes dinero suficiente para cubrir gastos básicos?", ["Si", "No"])
curso_finanzas = st.radio("¿Has tomado algún curso de finanzas personales?", ["Si", "No"])
cuanto_resiste = st.selectbox("¿Cuánto tiempo podrías cubrir tus gastos sin ingresos?", [
    "Menos de una semana/ no tiene ahorros",
    "Al menos una semana, pero menos de un mes",
    "Al menos un mes, pero menos de tres meses",
    "Al menos tres meses, pero menos de seis meses",
    "Seis meses o más",
    "No sabe"
])
cuenta = st.radio("¿Tienes cuenta bancaria?", ["Si", "No"])
acciones = st.radio("¿Tienes fondo de inversión o acciones?", ["Si", "No"])
cripto = st.radio("¿Has invertido en criptomonedas?", ["Si", "No"])
seguro = st.radio("¿Tienes algún seguro?", ["Si", "No"])
afore = st.radio("¿Tienes AFORE?", ["Si", "No"])
tarjeta = st.radio("¿Tienes tarjeta de crédito bancaria o departamental?", ["Si", "No"])

# Crear DataFrame
input_dict = {
    "EDAD": edad,
    "SEXO": sexo,
    "GRADO_ESTUDIOS": escolaridad,
    "ESTADO_CIVIL": estado_civil,
    "ACTIVIDAD_ECONOMICA": actividad,
    "CLASIFICACION_SALARIO_MENSUAL": salario,
    "LLEVA_PRESUPUESTO": presupuesto,
    "ANOTA_GASTOS": anota_gastos,
    "SEPARA_DINERO_DEUDAS": separa_deudas,
    "DINERO_SUFICIENTE_CUBRIR_GASTOS_BASICOS": suficiencia,
    "TOMADO_CURSO_FINANZAS_PERSONALES": curso_finanzas,
    "CUANTO_TIEMPO_PODRIA_CUBRIR_GASTOS_SIN_INGRESOS": cuanto_resiste,
    "CUENTA_BANCARIA": cuenta,
    "FONDO_INVERSION_ACCIONES": acciones,
    "INVERTIDO_EN_CRIPTO": cripto,
    "TIENE_ALGUN_SEGURO": seguro,
    "TIENE_AFORE": afore,
    "TARJETA_DE_CREDITO_BANCARIA_O_DEPARTAMENTAL": tarjeta
}
df_input = pd.DataFrame([input_dict])

# Preprocesar
df_input_encoded = pd.get_dummies(df_input)
for col in columnas_modelo:
    if col not in df_input_encoded:
        df_input_encoded[col] = 0
df_input_encoded = df_input_encoded[columnas_modelo]

# Clasificación
if st.button("🔍 Clasificar perfil"):
    perfil = model.predict(df_input_encoded)[0]
    st.session_state.perfil = perfil  # Guardar en la sesión
    st.success(f"🎯 Tu perfil de ahorro es: **{perfil}**")

#------------AGENTE
# API key para OpenRouter
api_key = st.secrets["openrouter"]["api_key"]

llm = ChatOpenAI(
    openai_api_key=api_key,
    base_url="https://openrouter.ai/api/v1",
    model="mistralai/mixtral-8x7b-instruct",
)

# Ver sugerencias solo si se clasificó el perfil
if st.button("💡 Ver sugerencias de inversión"):
    if "perfil" in st.session_state:
        perfil = st.session_state.perfil
        prompt = f"""
        Eres un asesor financiero. La persona fue clasificada como perfil de ahorro **{perfil}**.
        Sugiere 3 acciones concretas de ahorro o inversión apropiadas para su nivel, considerando que vive en México,
        probablemente tiene ingresos variables y poco conocimiento técnico si es principiante.

        Sé claro, práctico y no incluyas términos técnicos innecesarios.
        """

        respuesta = llm([HumanMessage(content=prompt)])
        st.info(f"🤖 Recomendaciones personalizadas:\n\n{respuesta.content}")
    else:
        st.warning("⚠️ Primero debes clasificar tu perfil antes de ver las sugerencias.")