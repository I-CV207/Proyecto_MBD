import streamlit as st
import pandas as pd
import joblib
import os
import requests
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage
from sqlalchemy import create_engine, text
from auth import load_authenticator
import uuid
from agente import crear_agente

# ─── Estilos visuales ─────────────────────────────────────────────────────
st.markdown("""
    <style>
        .stExpander {
            background-color: #f4f9f4;
            border: 2px solid #56A163;
            border-radius: 10px;
            padding: 10px;
        }
        .stSlider > div, .stSelectbox, .stRadio, .stButton button {
            color: #333333;
            font-weight: 500;
        }
        .stButton > button {
            background-color: #56A163;
            color: white;
            font-weight: bold;
            border-radius: 10px;
            padding: 0.5em 1em;
        }
        .stButton > button:hover {
            background-color: #3c774d;
            color: #ffffff;
        }
    </style>
""", unsafe_allow_html=True)

# ─── Autenticación ────────────────────────────────────────────────────────
unique_suffix = uuid.uuid4().hex[:6]
authenticator = load_authenticator()
login_result = authenticator.login('Login', 'main')
name = login_result[0]
authentication_status = login_result[1]
username = login_result[2]

if authentication_status is False:
    st.error("❌ Usuario o contraseña incorrectos.")
    st.stop()
elif authentication_status is None:
    st.warning("🔐 Por favor inicia sesión.")
    st.stop()

st.sidebar.success(f"Bienvenido, {name}")
authenticator.logout("Cerrar sesión", "sidebar")

# ─── Conexión a la base de datos ──────────────────────────────────────────
engine = create_engine("sqlite:///transacciones.db")

# ─── Carga del modelo y columnas desde Dropbox ────────────────────────────
modelo_url = "https://dl.dropboxusercontent.com/scl/fi/m0nhltpnmduk7q5b0ccpl/modelo_perfil_ahorro.pkl?rlkey=zs1wp7h6iacqwrfdy7ku21zr2&dl=1"
columnas_url = "https://dl.dropboxusercontent.com/scl/fi/mzrf1nz8nrf4kgrrip382/columnas_modelo.pkl?rlkey=8gcyqgabsoaumad1m0r16mqv2&dl=1"
modelo_path = os.path.join("modelos", "modelo_perfil_ahorro.pkl")
columnas_path = os.path.join("modelos", "columnas_modelo.pkl")
os.makedirs("modelos", exist_ok=True)

def descargar_desde_dropbox(url, path):
    response = requests.get(url)
    if response.status_code == 200:
        with open(path, "wb") as f:
            f.write(response.content)
    else:
        st.error(f"❌ Error al descargar {os.path.basename(path)}: {response.status_code}")
        st.stop()

def es_pickle_valido(path):
    if not os.path.exists(path):
        return False
    try:
        with open(path, "rb") as f:
            cabecera = f.read(100)
        if b'<!DOCTYPE html' in cabecera or b'<html' in cabecera:
            return False
        return True
    except Exception:
        return False

def validar_y_cargar_modelo(path):
    if not es_pickle_valido(path):
        st.error("❌ El archivo del modelo no es válido (posiblemente HTML).")
        st.stop()
    try:
        model = joblib.load(path)
        if not hasattr(model, "predict"):
            st.error("❌ El modelo cargado no tiene el método 'predict'")
            st.stop()
        return model
    except Exception as e:
        st.error(f"❌ Error al cargar el modelo: {e}")
        st.stop()

def validar_y_cargar_columnas(path):
    if not es_pickle_valido(path):
        st.error("❌ El archivo de columnas no es válido (posiblemente HTML).")
        st.stop()
    try:
        columnas = joblib.load(path)
        if not isinstance(columnas, list):
            st.error("❌ Las columnas cargadas no son una lista válida")
            st.stop()
        return columnas
    except Exception as e:
        st.error(f"❌ Error al cargar las columnas: {e}")
        st.stop()

if "modelo_descargado" not in st.session_state:
    if not os.path.exists(modelo_path):
        st.info("⬇️ Descargando modelo desde Dropbox...")
        descargar_desde_dropbox(modelo_url, modelo_path)

    if not os.path.exists(columnas_path):
        st.info("⬇️ Descargando columnas desde Dropbox...")
        descargar_desde_dropbox(columnas_url, columnas_path)

    st.session_state.modelo_descargado = True

model = validar_y_cargar_modelo(modelo_path)
columnas_modelo = validar_y_cargar_columnas(columnas_path)


# ─── Revisar perfil previo ────────────────────────────────────────────────
if "modificar_perfil" not in st.session_state:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM perfiles_ahorro WHERE usuario = :u"), {"u": username}).fetchone()
        if result:
            st.session_state.perfil = result[1]
            st.session_state.perfil_riesgo = result[2]
            st.info(f"📝 Ya tienes un perfil guardado como **{result[1]} {result[2]}**.")
        st.session_state.modificar_perfil = False

# ─── Formulario expandible ────────────────────────────────────────────────
with st.expander("Descrubre o modifica tu perfil financiero", expanded=st.session_state.get("modificar_perfil", False)):
    edad = st.slider("Edad", 18, 99, 30)
    sexo = st.selectbox("Sexo", ["Hombre", "Mujer"])
    escolaridad = st.selectbox("Grado de estudios", [
        "Primaria", "Secundaria", "Preparatoria o bachillerato",
        "Licenciatura o ingenieria (profesional)", "Posgrado"])
    estado_civil = st.selectbox("Estado civil", [
        "Es soltera(o)", "Esta casada(o)", "Esta separada(o)", "Es viuda(o)"])
    actividad = st.selectbox("Actividad económica", [
        "Trabajo por lo menos una hora",
        "Es persona jubilada o pensionada",
        "Se dedica a los quehaceres del hogar o al cuidado de algún familiar",
        "Estudia", "No realiza ninguna actividad"])
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
        "Seis meses o más", "No sabe"])
    cuenta = st.radio("¿Tienes cuenta bancaria?", ["Si", "No"])
    acciones = st.radio("¿Tienes fondo de inversión o acciones?", ["Si", "No"])
    cripto = st.radio("¿Has invertido en criptomonedas?", ["Si", "No"])
    seguro = st.radio("¿Tienes algún seguro?", ["Si", "No"])
    afore = st.radio("¿Tienes AFORE?", ["Si", "No"])
    tarjeta = st.radio("¿Tienes tarjeta de crédito bancaria o departamental?", ["Si", "No"])
    inversion = st.selectbox("Si inviertes 10,000 y al siguiente mes disminuye a 8,500, ¿Qué harías?", [
        "Lo retiro de inmediato", "Espero un par de meses y si no mejora, lo retiro",
        "Me tranquilizo, lo dejo minimo un año", "Compro más acciones, es una buena oportunidad de compra"])
    comodidad = st.selectbox("¿Qué tan cómodo/cómoda te sientes con que tu inversión suba y baje día con día si a largo plazo podrías ganar más?", [
        "Nada cómodo/a, prefiero algo seguro", "Un poco nervioso/a, pero confío en el largo plazo",
        "Relajado/a, sé que es normal en inversiones", "Me gusta la emoción, ¡es parte del juego!"])

    input_dict = {
        "EDAD": edad, "SEXO": sexo, "GRADO_ESTUDIOS": escolaridad,
        "ESTADO_CIVIL": estado_civil, "ACTIVIDAD_ECONOMICA": actividad,
        "CLASIFICACION_SALARIO_MENSUAL": salario, "LLEVA_PRESUPUESTO": presupuesto,
        "ANOTA_GASTOS": anota_gastos, "SEPARA_DINERO_DEUDAS": separa_deudas,
        "DINERO_SUFICIENTE_CUBRIR_GASTOS_BASICOS": suficiencia,
        "TOMADO_CURSO_FINANZAS_PERSONALES": curso_finanzas,
        "CUANTO_TIEMPO_PODRIA_CUBRIR_GASTOS_SIN_INGRESOS": cuanto_resiste,
        "CUENTA_BANCARIA": cuenta, "FONDO_INVERSION_ACCIONES": acciones,
        "INVERTIDO_EN_CRIPTO": cripto, "TIENE_ALGUN_SEGURO": seguro,
        "TIENE_AFORE": afore, "TARJETA_DE_CREDITO_BANCARIA_O_DEPARTAMENTAL": tarjeta
    }

    df_input = pd.DataFrame([input_dict])
    df_input_encoded = pd.get_dummies(df_input)
    for col in columnas_modelo:
        if col not in df_input_encoded:
            df_input_encoded[col] = 0
    df_input_encoded = df_input_encoded[columnas_modelo]

    def clasificar_perfil_riesgo(inversion, comodidad):
        if inversion == "Lo retiro de inmediato":
            return "Conservador"
        if inversion == "Espero un par de meses y si no mejora, lo retiro":
            return "Moderado" if comodidad != "Nada cómodo/a, prefiero algo seguro" else "Conservador"
        if inversion == "Me tranquilizo, lo dejo minimo un año":
            return "Audaz" if comodidad in ["Relajado/a, sé que es normal en inversiones", "Me gusta la emoción, ¡es parte del juego!"] else "Moderado"
        if inversion == "Compro más acciones, es una buena oportunidad de compra":
            return "Agresivo" if comodidad in ["Relajado/a, sé que es normal en inversiones", "Me gusta la emoción, ¡es parte del juego!"] else "Audaz"
        return "Sin clasificar"

    if st.button("✅ Guardar y clasificar perfil"):
        perfil = model.predict(df_input_encoded)[0]
        perfil_riesgo = clasificar_perfil_riesgo(inversion, comodidad)
        st.session_state.perfil = perfil
        st.session_state.perfil_riesgo = perfil_riesgo

        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO perfiles_ahorro (
                    usuario, perfil_ahorro, perfil_riesgo, edad, sexo, escolaridad, estado_civil, actividad,
                    salario, presupuesto, anota_gastos, separa_deudas, suficiencia, curso_finanzas,
                    cuanto_resiste, cuenta, acciones, cripto, seguro, afore, tarjeta, inversion, comodidad
                ) VALUES (
                    :usuario, :perfil_ahorro, :perfil_riesgo, :edad, :sexo, :escolaridad, :estado_civil, :actividad,
                    :salario, :presupuesto, :anota_gastos, :separa_deudas, :suficiencia, :curso_finanzas,
                    :cuanto_resiste, :cuenta, :acciones, :cripto, :seguro, :afore, :tarjeta, :inversion, :comodidad
                )
                ON CONFLICT(usuario) DO UPDATE SET
                    perfil_ahorro = excluded.perfil_ahorro,
                    perfil_riesgo = excluded.perfil_riesgo,
                    edad = excluded.edad,
                    sexo = excluded.sexo,
                    escolaridad = excluded.escolaridad,
                    estado_civil = excluded.estado_civil,
                    actividad = excluded.actividad,
                    salario = excluded.salario,
                    presupuesto = excluded.presupuesto,
                    anota_gastos = excluded.anota_gastos,
                    separa_deudas = excluded.separa_deudas,
                    suficiencia = excluded.suficiencia,
                    curso_finanzas = excluded.curso_finanzas,
                    cuanto_resiste = excluded.cuanto_resiste,
                    cuenta = excluded.cuenta,
                    acciones = excluded.acciones,
                    cripto = excluded.cripto,
                    seguro = excluded.seguro,
                    afore = excluded.afore,
                    tarjeta = excluded.tarjeta,
                    inversion = excluded.inversion,
                    comodidad = excluded.comodidad
            """), {
                "usuario": username, "perfil_ahorro": perfil, "perfil_riesgo": perfil_riesgo,
                "edad": edad, "sexo": sexo, "escolaridad": escolaridad, "estado_civil": estado_civil, "actividad": actividad,
                "salario": salario, "presupuesto": presupuesto, "anota_gastos": anota_gastos,
                "separa_deudas": separa_deudas, "suficiencia": suficiencia, "curso_finanzas": curso_finanzas,
                "cuanto_resiste": cuanto_resiste, "cuenta": cuenta, "acciones": acciones,
                "cripto": cripto, "seguro": seguro, "afore": afore, "tarjeta": tarjeta,
                "inversion": inversion, "comodidad": comodidad
            })

        st.success(f"🎯 Tu perfil fue clasificado como: **{perfil} {perfil_riesgo}** y guardado exitosamente.")
        st.session_state.modificar_perfil = False
