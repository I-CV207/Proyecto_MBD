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
from utils import (
    cargar_fondos_desde_db, construir_prompt_recomendaciones_fondos, simular_inversion,
    calcular_evolucion_anual, obtener_perfil_ahorro,forecast_yf_ticker
)
from agente_inversion import crear_agente_inversion
import matplotlib.pyplot as plt


# ─── Estilos visuales ─────────────────────────────────────────────────────
st.markdown("""
    <style>
        .stExpander {
            background-color: #ffffff;
            border: 2px solid #56A163;
            border-radius: 10px;
            padding: 10px;
        }
        .stSlider > div, .stSelectbox, .stRadio, .stButton button {
            color: #333333;
            font-weight: 500;
        }
        .stButton > button {
            background-color: #white;
            color: black;
            font-weight: bold;
            border-radius: 10px;
            padding: 0.5em 1em;
        }
        .stButton > button:hover {
            background-color: #ffffff;
            color: black;
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

st.sidebar.success(f"Hola, {name}")
authenticator.logout("Cerrar sesión", "sidebar")

# ─── Conexión a la base de datos ──────────────────────────────────────────
engine = create_engine("sqlite:///transacciones.db")

# ─── URLs desde GitHub ────────────────────────────────────────────────────
modelo_url = "https://raw.githubusercontent.com/I-CV207/modelos_billia/main/modelo_perfil_ahorro.pkl"
columnas_url = "https://raw.githubusercontent.com/I-CV207/modelos_billia/main/columnas_modelo.pkl"
modelo_path = os.path.join("modelos", "modelo_perfil_ahorro.pkl")
columnas_path = os.path.join("modelos", "columnas_modelo.pkl")
os.makedirs("modelos", exist_ok=True)

def descargar_desde_github(url, path):
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
        return not (b'<!DOCTYPE html' in cabecera or b'<html' in cabecera)
    except:
        return False

def validar_y_cargar_modelo(path):
    if not es_pickle_valido(path):
        st.error("❌ El archivo del modelo no es válido (posiblemente HTML).")
        st.stop()
    try:
        modelo = joblib.load(path)
        if not hasattr(modelo, "predict"):
            st.error("❌ El modelo cargado no tiene método predict.")
            st.stop()
        return modelo
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
            st.error("❌ Las columnas no son una lista válida.")
            st.stop()
        return columnas
    except Exception as e:
        st.error(f"❌ Error al cargar las columnas: {e}")
        st.stop()

# ─── Descargar si no existen ────────────────────────────
if "modelo_descargado" not in st.session_state:
    if os.path.exists(modelo_path):
        os.remove(modelo_path)
    if os.path.exists(columnas_path):
        os.remove(columnas_path)

    st.info("Generando modelo de perfilamiento...")
    descargar_desde_github(modelo_url, modelo_path)

    st.info("Espera un poco mas...")
    descargar_desde_github(columnas_url, columnas_path)

    st.session_state.modelo_descargado = True

# ─── Cargar ─────────────────────────────────────────────
model = validar_y_cargar_modelo(modelo_path)
columnas_modelo = validar_y_cargar_columnas(columnas_path)
# ───────────────────────────────────────
# Mensaje de bienvenida si usuario tiene o no perfil
# ───────────────────────────────────────

with engine.connect() as conn:
    perfil = conn.execute(
        text("SELECT * FROM perfiles_ahorro WHERE usuario = :u"),
        {"u": username}
    ).fetchone()

st.markdown(f"<h3 style='text-align: center;'>Hola, {name}</h3>", unsafe_allow_html=True)

if perfil:
    st.markdown("""
        <div style='display: flex; justify-content: center; margin-top: 30px;'>
            <div style='background-color: #009473; color: #ffffff ; border: 1px solid #c3e6cb;
                        padding: 20px 40px; border-radius: 10px; text-align: center; max-width: 500px;'>
                <h4>Actualmente tu perfil es:</h4>
                <p style='font-size: 22px; font-weight: bold;'>{} {}</p>
            </div>
        </div>
    """.format(perfil[1], perfil[2]), unsafe_allow_html=True)
else:
    st.warning("⚠️ Aún no has definido tu perfil de ahorro. Por favor responde el cuestionario para obtener recomendaciones personalizadas.")

st.markdown("")

# ─── Revisar perfil previo ────────────────────────────────────────────────
if "modificar_perfil" not in st.session_state:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM perfiles_ahorro WHERE usuario = :u"), {"u": username}).fetchone()
        if result:
            st.session_state.perfil = result[1]
            st.session_state.perfil_riesgo = result[2]
            st.info(f"Actualemente tu perfil es: **{result[1]} {result[2]}**.")
        st.session_state.modificar_perfil = False

# ─── Formulario expandible ────────────────────────────────────────────────
with engine.connect() as conn:
            result = conn.execute(
                text("""SELECT ABS(SUM(Monto)) FROM transacciones 
                        WHERE Usuario = :u AND Categoria = 'Metas financieras 💰'"""),
                {"u": username}
            )
            ahorro_actual = result.scalar() or 10000

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
    inversion = st.selectbox(f"Si inviertes {int(ahorro_actual)} y al siguiente mes disminuye a {int(ahorro_actual*.85)} ¿Qué harías?", [
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
            return "Arriesgado" if comodidad in ["Relajado/a, sé que es normal en inversiones", "Me gusta la emoción, ¡es parte del juego!"] else "Moderado"
        if inversion == "Compro más acciones, es una buena oportunidad de compra":
            return "Arriesgado" if comodidad in ["Relajado/a, sé que es normal en inversiones", "Me gusta la emoción, ¡es parte del juego!"] else "Arriesgado"
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

        st.success(f"¡Gracias {name}! He analizado tus respuestas, y,dentro del ecosistema de Bill.iA actualmente tu perfil es: **{perfil} {perfil_riesgo}**")
        st.session_state.modificar_perfil = False
#_____________________________________
#Seccion de recomendacion de agente
#____________________________________
# ─── Sección: Recomendaciones y simulación ───────────────────────────────
st.subheader("Descubre cómo tu ahorro podría evolucionar...")

# Obtener perfil del usuario
perfil_ahorro, perfil_riesgo = obtener_perfil_ahorro(engine, username)

if not perfil_riesgo:
    st.warning("⚠️ Aún no tienes un perfil registrado. Completa el formulario primero.")
else:
    # Estilo personalizado del slider
    st.markdown("""
    <style>
    /* Fuerza un filtro de color para modificar el aspecto general */
    div[data-baseweb="slider"] {
        filter: hue-rotate(90deg);  /* Ajusta el matiz: 90 = verde, 270 = azul */
    }

    /* Opcional: mejorar el contraste del thumb */
    div[data-baseweb="slider"] [role="slider"] {
        box-shadow: 0 0 0 3px #56A16350;
    }
    </style>
    """, unsafe_allow_html=True)

    # Cargar fondos y construir prompt
    df_fondos = cargar_fondos_desde_db(engine)
    prompt = construir_prompt_recomendaciones_fondos(df_fondos, perfil_riesgo)
    agente = crear_agente_inversion(username, engine)

    # Estado de simulación
    if "mostrar_recomendaciones" not in st.session_state:
        st.session_state.mostrar_recomendaciones = False

    if st.button("Recomiendame donde invertir"):
        st.session_state.mostrar_recomendaciones = True
        st.session_state.respuesta_agente = agente.run(prompt)

    if st.session_state.mostrar_recomendaciones:
        
        if "respuesta_agente" in st.session_state:
            st.info(st.session_state.respuesta_agente)
        else:
            st.warning("⚠️ No se encontró la respuesta del agente. Haz clic nuevamente en el botón.")

       

        # Recuperar ahorro actual
        with engine.connect() as conn:
            result = conn.execute(
                text("""SELECT ABS(SUM(Monto)) FROM transacciones 
                        WHERE Usuario = :u AND Categoria = 'Metas financieras 💰'"""),
                {"u": username}
            )
            ahorro_actual = result.scalar() or 10000

        # Entradas personalizadas
        monto_inicial = st.number_input("Monto a invertir (puedes ajustarlo)", value=ahorro_actual, step=500.0)
        años = st.slider("Años a simular", 1, 20, 10)

        # Simulación
        st.subheader(f"Si hoy invirtieras ${abs(int(monto_inicial))} en {años} años ganarías aproximadamente:")
        df_fondos_riesgo = df_fondos[df_fondos["riesgo"].str.lower() == perfil_riesgo.lower()]

        # Simulación basada en tickers y yfinance
        # Extraer nombres de fondos mencionados
        texto = st.session_state.respuesta_agente.lower()
        fondos_posibles = df_fondos["fondo"].unique()
        fondos_detectados = [f for f in fondos_posibles if f.lower() in texto]

        # Filtrar DataFrame con los fondos detectados
        fondos_simulables = df_fondos[df_fondos["fondo"].isin(fondos_detectados)].dropna(subset=["ticker"])

        if fondos_simulables.empty:
            st.warning("⚠️ No se pudieron identificar los fondos recomendados. Mostrando los primeros del perfil.")
            fondos_simulables = df_fondos[df_fondos["riesgo"].str.lower() == perfil_riesgo.lower()].dropna(subset=["ticker"]).head(3)
        
        # Ejecutar simulaciones y guardar resultados
        resultados_simulacion = []
        for _, row in fondos_simulables.iterrows():
            with st.spinner(f"Simulando {row['fondo']} con datos reales..."):
                resultado, cagr, model, df_hist, forecast = forecast_yf_ticker(row["ticker"], monto_inicial, años)
                if resultado and model:
                    fecha_corte = model.history['ds'].max()
                else:
                    fecha_corte = None
                resultados_simulacion.append((row, resultado, cagr, forecast, fecha_corte))

        # Mostrar resumen estilo tarjetas con resultados
        cols = st.columns(len(resultados_simulacion))
        for i, (row, resultado, cagr, _,_) in enumerate(resultados_simulacion):
            with cols[i]:
                st.markdown(f"""
                <div style='background-color: #515052; padding: 15px; border-radius: 10px; color: white; text-align: center; min-height: 200px;'>
                    <div style='font-size: 20px; font-weight: bold;'> ${resultado:,.2f}</div>
                    <div style='font-size: 18px; margin-top: 5px;'> CAGR: {cagr * 100:.2f}%</div>
                    <div style='font-size: 16px; font-weight: bold;'>{row['administradora_del_fondo']}</div>
                    <div style='font-size: 14px;'>{row['fondo']}</div>
                    <div style='font-size: 14px;'>{row['ticker']}</div>
                    <div style='font-size: 13px; margin-top: 5px;'>Liquidez-{row['liquidez']} | ⏳ {row['horizonte']}</div>
                    <div style='margin-top: 10px; font-size: 12px;'>Accede aquí ⏩</div>
                </div>
                """, unsafe_allow_html=True)

        # Mostrar gráfica individual al seleccionar un fondo recomendado
        st.markdown("## Explora la proyección de cada fondo")
        opciones = [f"{row['fondo']} ({row['ticker']}) - CAGR: {cagr * 100:.2f}%" for row, resultado, cagr, _, _ in resultados_simulacion]
        fondo_seleccionado = st.selectbox("Selecciona un fondo para ver su gráfica de proyección:", opciones)

        for row, resultado, cagr, forecast, fecha_corte in resultados_simulacion:
            etiqueta = f"{row['fondo']} ({row['ticker']}) - CAGR: {cagr * 100:.2f}%"
            if fondo_seleccionado == etiqueta and resultado and forecast is not None and fecha_corte is not None:
                df_plot = forecast[["ds", "yhat"]].copy()
                df_plot["Histórico"] = df_plot["yhat"].where(df_plot["ds"] <= fecha_corte)
                df_plot["Proyección"] = df_plot["yhat"].where(df_plot["ds"] > fecha_corte)
                df_chart = df_plot.set_index("ds")[["Histórico", "Proyección"]]
                st.line_chart(df_chart, use_container_width=True)

       

        # Botón para ocultar resultados
        if st.button("Ocultar simulación"):
            st.session_state.mostrar_recomendaciones = False
            st.rerun()

