import streamlit as st
import pandas as pd
import joblib
import os
import gdown
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

# ─── Descarga y carga del modelo y columnas con gdown ─────────────────────
modelo_path = os.path.join("modelos", "modelo_perfil_ahorro.pkl")
columnas_path = os.path.join("modelos", "columnas_modelo.pkl")
modelo_id = "1vc7JsZuf74vgeJYY2fTglFhqS0BheHBa"
columnas_id = "1AwKtDlQNGssylCZ3zFR-14hfTVLnjtDs"

os.makedirs("modelos", exist_ok=True)

def descargar_archivo_gdrive(file_id, output_path):
    url = f"https://drive.google.com/uc?id={file_id}"
    gdown.download(url, output_path, quiet=False)

def es_pickle_valido(path):
    with open(path, "rb") as f:
        firma = f.read(4)
        return firma != b'<!DO'

if "modelo_descargado" not in st.session_state:
    if not os.path.exists(modelo_path):
        st.info("⬇️ Descargando modelo desde Google Drive...")
        descargar_archivo_gdrive(modelo_id, modelo_path)

    if not os.path.exists(columnas_path):
        st.info("⬇️ Descargando columnas desde Google Drive...")
        descargar_archivo_gdrive(columnas_id, columnas_path)

    if not es_pickle_valido(modelo_path):
        st.error("❌ El archivo del modelo no es válido.")
        st.stop()
    if not es_pickle_valido(columnas_path):
        st.error("❌ El archivo de columnas no es válido.")
        st.stop()

    st.session_state.modelo_descargado = True

try:
    model = joblib.load(modelo_path)
    if not hasattr(model, "predict"):
        st.error("❌ El modelo cargado no tiene el método 'predict'.")
        st.stop()
except Exception as e:
    st.error(f"❌ Error al cargar el modelo: {e}")
    st.stop()

try:
    columnas_modelo = joblib.load(columnas_path)
    if not isinstance(columnas_modelo, list):
        st.error("❌ Las columnas cargadas no son una lista válida.")
        st.stop()
except Exception as e:
    st.error(f"❌ Error al cargar las columnas: {e}")
    st.stop()

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
