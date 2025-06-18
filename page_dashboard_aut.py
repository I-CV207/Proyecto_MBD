# app.py
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from auth import load_authenticator
from utils import (
    guardar_transaccion_usuario,cargar_transacciones_usuario,
    get_total_spent, get_total_earned, registrar_transaccion_desde_texto, get_ultimas_transacciones,
    resumen_mensual, get_balance_actual, get_gastos_por_categoria,
    get_promedio_gastos, proyeccion_saldo_fin_mes, ranking_gastos_categorias, ranking_ingresos_categorias,
    porcentaje_gastos_por_categoria, alerta_gasto_excesivo, sugerencia_ahorro, buscar_transacciones,
    evolucion_balance, comparativa_gastos_mensual, gastos_recurrentes, sugerencia_presupuesto, simulador_sin_gasto_en,
    get_total_ahorrado, get_total_asignado_metas, get_ahorro_disponible,get_resumen_metas, get_recomendacion_asignacion,construir_presupuesto_asistido
)
from agente import crear_agente
from datetime import datetime
import re
import locale
from sqlalchemy import text
import matplotlib.pyplot as plt
import math
import uuid

unique_suffix = uuid.uuid4().hex[:6] 
# Autenticación
authenticator = load_authenticator()
#name, authentication_status, username = authenticator.login('Login','main') --Tuple de vriables, a veces no funciona, no es opcion viable
# Mostrar pantalla de login
login_result=authenticator.login('Login','main')
#Guardar name
name=login_result[0]
#Estatus de login
authentication_status=login_result[1]
#Guardar nombre de usuario
username=login_result[2]


if authentication_status is False:
    st.error("❌ Usuario o contraseña incorrectos.")
    st.stop()
elif authentication_status is None:
    st.warning("🔐 Por favor inicia sesión.")
    st.stop()

st.sidebar.success(f"Bienvenido, {name}")
authenticator.logout("Cerrar sesión", "sidebar")

# Conexión a la base SQLite
engine = create_engine("sqlite:///transacciones.db")

# Cargar datos del usuario
if "transacciones" not in st.session_state:
    st.session_state.transacciones = cargar_transacciones_usuario(engine, username)

# ───────────────────────────────────────
# Navegación visual personalizada
# ───────────────────────────────────────
st.markdown("""
    <style>
    /* Quitar márgenes visuales y modificar estilo de los botones */
    .stButton > button {
        margin: 0.0px !important;
        padding: .5rem 0.2rem;
        font-size: 28px;
        color: #C5C4C4 !important;
        background-color: #ffffff;  /* Fondo oscuro personalizado */
        border: none;
        border-radius: 10px;
        transition: background-color 0.3s ease;
    }
    .stButton > button:hover {
        background-color: #ffffff;
        color: #6495ED !important;
    }
                
    /* Estilo para botón activo */
    .active-button > button {
        color: #6495ED !important;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

if "seccion" not in st.session_state:
    st.session_state.seccion = "dashboard"

col1, col2, col3 = st.columns(3)
with col1:
    if st.button("Resumen", use_container_width=True):
        st.session_state.seccion = "dashboard"

with col2:
    if st.button("Lo que Gastaste", use_container_width=True):
        st.session_state.seccion = "registro"

with col3:
    if st.button("Lo que ahorras", use_container_width=True):
        st.session_state.seccion = "ahorro"

seccion = st.session_state.seccion
df = st.session_state.transacciones

# ────────────────────────────────
# Sección: Registrar transacción
# ────────────────────────────────
if seccion == "registro":
    # Verificar si el usuario ya tiene un presupuesto
    with engine.connect() as conn:
        stmt = text("SELECT * FROM presupuestos WHERE Usuario = :username")
        result = conn.execute(stmt, {"username": username})
        presupuesto_existente = result.fetchone()
    # ────────────────────────────────
    # Sección: Aistente presupuesto
    # ────────────────────────────────    
    
    agent = crear_agente(username, engine)

    # Botón para activar asistente de presupuesto
    if "mostrar_asistente_presupuesto" not in st.session_state:
        st.session_state.mostrar_asistente_presupuesto = False

    if not st.session_state.mostrar_asistente_presupuesto:
        if st.button(f"Billie: Hola, {name}, armemos o modifiquemos tu presupuesto ¿Quieres que te ayude?"):
            st.session_state.mostrar_asistente_presupuesto = True
            st.rerun()

    if st.session_state.mostrar_asistente_presupuesto:
        with st.expander(f"Billie: {name} deja que te ayude a construir tu presupuesto, empecemos......", expanded=True):
            construir_presupuesto_asistido(username, engine)

    # Verificar si el usuario ya tiene un presupuesto
    with engine.connect() as conn:
        stmt = text("SELECT * FROM presupuestos WHERE Usuario = :username")
        result = conn.execute(stmt, {"username": username})
        presupuesto_existente = result.fetchone()

 
        
        # ───────────────────────────────────────
        # SECCIÓN: Añadir o editar presupuesto
        # ───────────────────────────────────────
        with st.expander("Ver o modificar presupuesto manualmente"):
            with st.form("form_presupuesto"):
                # Leer presupuesto actual del usuario
                with engine.connect() as conn:
                    result = conn.execute(
                        text("SELECT * FROM presupuestos WHERE Usuario = :username"),
                        {"username": username}
                    ).mappings()
                    presupuesto_existente = result.fetchone()

                # Valores actuales o por defecto
                valores_actuales = {
                    "Necesidades": presupuesto_existente["Necesidades"] if presupuesto_existente else 0.0,
                    "Gustos": presupuesto_existente["Gustos"] if presupuesto_existente else 0.0,
                    "MetasFinancieras": presupuesto_existente["MetasFinancieras"] if presupuesto_existente else 0.0
                }

                necesidades = st.number_input("Presupuesto para Necesidades 🍎", min_value=0.0, step=10.0, value=valores_actuales["Necesidades"])
                gustos = st.number_input("Presupuesto para Gustos 🎁", min_value=0.0, step=10.0, value=valores_actuales["Gustos"])
                metas = st.number_input("Presupuesto para Metas financieras 💰", min_value=0.0, step=10.0, value=valores_actuales["MetasFinancieras"])
                submitted = st.form_submit_button("Guardar cambios")

                if submitted:
                    with engine.begin() as conn:  # begin() asegura commit automático
                        conn.execute(
                            text("""
                                INSERT OR REPLACE INTO presupuestos (Usuario, Necesidades, Gustos, MetasFinancieras)
                                VALUES (:Usuario, :Necesidades, :Gustos, :MetasFinancieras)
                            """),
                            {
                                "Usuario": username,
                                "Necesidades": necesidades,
                                "Gustos": gustos,
                                "MetasFinancieras": metas
                            }
                        )
                    st.success("✅ Presupuesto actualizado.")
                    st.rerun()

        # Volver a cargar presupuesto después del guardado
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM presupuestos WHERE Usuario = :username"),
                {"username": username}
            ).mappings()
            presupuesto_existente = result.fetchone()

        valores_actuales = {
            "Necesidades": presupuesto_existente["Necesidades"] if presupuesto_existente else 0.0,
            "Gustos": presupuesto_existente["Gustos"] if presupuesto_existente else 0.0,
            "MetasFinancieras": presupuesto_existente["MetasFinancieras"] if presupuesto_existente else 0.0
        }
        mes_actual = datetime.now().strftime('%B').capitalize()
        mes_numero = datetime.now().month
        anio_actual = datetime.now().year
        st.markdown(f"""<p style='text-align: center; font-size: 20px;'>
            {name}, echemos un vistazo a cómo has usado tu dinero en {mes_actual}
            </p>""", unsafe_allow_html=True)
 

        # Colores y configuraciones por categoría
        categorias = {
            "Necesidades": {"emoji": "🍎", "color_fondo": "#8ECA62", "color_donut": "#4c8bf5"},
            "Gustos": {"emoji": "🎁", "color_fondo": "#56A163", "color_donut": "#4c8bf5"},
            "MetasFinancieras": {"emoji": "💰", "color_fondo": "#61ACAB", "color_donut": "#4c8bf5"},
        }

        # Obtener mes y año actual
        hoy = datetime.today()
        mes = f"{hoy.month:02d}"
        anio = str(hoy.year)

        # Consultar gastos del mes actual por categoría
        with engine.connect() as conn:
            df_gastos = pd.read_sql(
                text("""
                    SELECT Categoria, ABS(SUM(Monto)) as Gasto
                    FROM transacciones
                    WHERE Usuario = :usuario
                    AND strftime('%m', Fecha) = :mes
                    AND strftime('%Y', Fecha) = :anio
                    GROUP BY Categoria
                """),
                conn,
                params={"usuario": username, "mes": mes, "anio": anio}
            )

        gastos_dict = df_gastos.set_index("Categoria")["Gasto"].to_dict()

        # Mostrar los gráficos
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])  # Agrega una 4ta columna para Billie

        def donut_chart(presupuesto, gasto, color_fondo, color_donut, categoria, emoji, col):
            # Validar y corregir NaN
            if math.isnan(presupuesto):
                presupuesto = 0
            if math.isnan(gasto):
                gasto = 0

            restante = max(presupuesto - gasto, 0)
            porcentaje = (gasto / presupuesto) if presupuesto else 0

            fig, ax = plt.subplots(figsize=(1.7,1.7))
            fig.patch.set_facecolor(color_fondo)
            ax.pie(
                [gasto, restante],
                startangle=90,
                colors=[color_donut, "#e0e0e0"],
                wedgeprops={"width": 0.25, "edgecolor": "white"}
            )
            ax.set(aspect="equal")
            plt.axis("off")

            # Texto debajo del gráfico
            col.pyplot(fig)
            col.markdown(f"""
                <div style="background-color:{color_fondo};padding:1px;border-radius:20px;text-align:center;color:white">
                    <div style="font-size:18px;font-weight:bold">{categoria} {emoji}</div>
                    <div style="font-size:22px;font-weight:bold">${int(gasto):,} gastados de</div>
                    <div style="font-size:16px;">${int(presupuesto):,} presupuestados</div>
                </div>
            """, unsafe_allow_html=True)

        # ───────────────────────────────────────
        # SECCIÓN: Mostrar Donut charts
        # ───────────────────────────────────────

     
        def valor_valido(v):
            return v is not None and isinstance(v, (int, float)) and not math.isnan(v) and not math.isinf(v)

        def puede_graficar(valor_presupuesto, valor_gasto):
            return valor_valido(valor_presupuesto) and valor_valido(valor_gasto) and (valor_presupuesto + valor_gasto > 0)

        if puede_graficar(valores_actuales.get("Necesidades"), gastos_dict.get("Necesidades 🍎", 0.0)):
            donut_chart(
                valores_actuales["Necesidades"], gastos_dict.get("Necesidades 🍎", 0.0),
                categorias["Necesidades"]["color_fondo"], categorias["Necesidades"]["color_donut"],
                "Necesidades", categorias["Necesidades"]["emoji"], col1
            )
        else:
            col1.warning("🛠️ Arma tu presupuesto para ver tus necesidades.")

        if puede_graficar(valores_actuales.get("Gustos"), gastos_dict.get("Gustos 🎁", 0.0)):
            donut_chart(
                valores_actuales["Gustos"], gastos_dict.get("Gustos 🎁", 0.0),
                categorias["Gustos"]["color_fondo"], categorias["Gustos"]["color_donut"],
                "Gustos", categorias["Gustos"]["emoji"], col2
            )
        else:
            col2.warning("🛠️ Arma tu presupuesto para ver tus gustos.")

        if puede_graficar(valores_actuales.get("MetasFinancieras"), gastos_dict.get("Metas financieras 💰", 0.0)):
            donut_chart(
                valores_actuales["MetasFinancieras"], gastos_dict.get("Metas financieras 💰", 0.0),
                categorias["MetasFinancieras"]["color_fondo"], categorias["MetasFinancieras"]["color_donut"],
                "Metas financieras", categorias["MetasFinancieras"]["emoji"], col3
            )
        else:
            col3.warning("🛠️ Arma tu presupuesto para ver tus metas.")


         # ───────────────────────────────────────
        # Observaciones
        # ───────────────────────────────────────       
        with col4:
            st.markdown("""
            <div style='background-color: #f4f4f4; padding: 20px; border-radius: 10px; color: #333;'>
                <h5> Billie te dice:</h5>
            """, unsafe_allow_html=True)
            st.markdown("")

            prompt_analisis = f"""
            Eres un asesor financiero. Analiza estos datos del mes:
            - Necesidades: gasto ${gastos_dict.get("Necesidades 🍎", 0.0):,.2f} de ${valores_actuales['Necesidades']:,.2f} presupuestados
            - Gustos: gasto ${gastos_dict.get("Gustos 🎁", 0.0):,.2f} de ${valores_actuales['Gustos']:,.2f} presupuestados
            - Metas: gasto ${gastos_dict.get("Metas financieras 💰", 0.0):,.2f} de ${valores_actuales['MetasFinancieras']:,.2f} presupuestados

            Redacta un resumen amable y en lenguaje cotidiano que conteste:
            - ¿Va bien?
            - ¿En qué puede mejorar?
            - ¿Recomendaciones de acción simples?
            - Si no hay registros, invítalo a comenzar.
            """

            try:
                respuesta_billie = agent.run(prompt_analisis)
            except Exception as e:
                respuesta_billie = "Billie no pudo hacer el análisis."

            st.markdown(f"""
                <div style='font-size: 14px; line-height: 1.6;'>
                {respuesta_billie}
                </div>
                </div>
            """, unsafe_allow_html=True)

        # ───────────────────────────────────────
        # Mostrar tabla de transacciones en formato desplazable
        # ───────────────────────────────────────
        st.markdown("### Historico de transacciones del mes")

        if df.empty:
            st.info("No hay transacciones registradas.")
        else:
            # Filtrar las del mes actual
            df_mes = df[
                (pd.to_datetime(df["Fecha"]).dt.month == mes_numero) &
                (pd.to_datetime(df["Fecha"]).dt.year == anio_actual)&
                (df['Usuario']==username)
            ]

            if df_mes.empty:
                st.warning("No hay transacciones para el mes actual.")
            else:
                # Estilo de scroll horizontal
                st.markdown("""
                <style>
                .scrollable-table {
                    overflow-x: auto;
                    border: 1px solid #ccc;
                    padding: 10px;
                    border-radius: 10px;
                }
                </style>
                """, unsafe_allow_html=True)

                st.markdown('<div class="scrollable-table">', unsafe_allow_html=True)
                st.dataframe(df_mes[['ID','Fecha','Descripcion','Categoria','Cuenta','Monto']], use_container_width=True, height=250)
                st.markdown('</div>', unsafe_allow_html=True)
        # Agente
        #agent = crear_agente(username, engine)

        # ────────────────
        # ESTILO PERSONALIZADO
        # ────────────────
        # CSS unificado y correcto
        st.markdown("""
            <style>
            .custom-button button {
                background-color: #1e1e1e !important;
                color: black !important;
                font-size: 16px !important;
                padding: 0.6rem 1.2rem !important;
                border-radius: 8px !important;
                transition: all 0.3s ease;
                border: none !important;
            }
            .custom-button button:hover {
                background-color: #333 !important;
                color: #6495ED !important;
            }

            .enviar-btn button {
                background-color: #1e1e1e !important;
                color: white !important;
                font-size: 32px !important;
                padding: 0.5rem 1.2rem !important;
                border-radius: 10px !important;
                border: none !important;
                transition: background-color 0.3s ease;
                margin-top: 0.6rem;
            }

            .enviar-btn button:hover {
                background-color: #333 !important;
                color: #6495ED !important;
            }
            </style>
        """, unsafe_allow_html=True)

        # ────────────────
        # BLOQUE DE INTERACCIÓN CON BILLIE
        # ────────────────
        respuesta = None
        # Input de texto personalizado
        user_prompt_registro = st.chat_input(placeholder="O pregunta lo que quieras...",key=f"user_input_registro_{username}")
        # Ejecutar si hay algo que responder
        if user_prompt_registro:
            with st.spinner("BILLIE está pensando..."):
                respuesta = agent.run(user_prompt_registro)

        # Mostrar respuesta (solo una sección visible)
        if respuesta:
            st.markdown("### Respuesta")
            st.markdown(respuesta)


    # ───────────────────────────────────────
    # CONTINUACIÓN: Visualización y registro
    # ───────────────────────────────────────
    st.markdown("")
    # Mostrar formulario de registro de transacción SIEMPRE
    with st.expander("Registrar nueva transacción"):
        with st.form("nueva_transaccion"):
            fecha = st.date_input("Fecha", value=datetime.today())
            descripcion = st.text_input("Descripcion")
            categoria = st.selectbox("Categoría", [
                "Ingresos 💵","Necesidades 🍎", "Gustos 🎁", "Metas financieras 💰"])
            cuenta = st.text_input("Cuenta")
            monto = st.number_input("Monto", min_value=-100000.0, max_value=100000.0, step=10.0)
            submitted = st.form_submit_button("Agregar")

            if submitted:
                guardar_transaccion_usuario(engine, fecha, categoria, cuenta, monto, username,descripcion)
                st.success("✅ Transacción registrada.")
                st.session_state.transacciones = cargar_transacciones_usuario(engine, username)
                st.rerun()

    # Mostrar tabla solo si hay transacciones
    if df.empty:
        st.info("No hay transacciones registradas.")
    else:
        try:
            # Intenta con el locale estándar para español en Linux
            locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
        except locale.Error:
            try:
                # Intenta con el locale de Windows (en caso de entorno local)
                locale.setlocale(locale.LC_TIME, 'Spanish_Mexico.1252')
            except locale.Error:
                # Si nada funciona, sigue con el locale por defecto
                pass

        mes_actual = datetime.now().strftime('%B').capitalize()
        mes_numero = datetime.now().month
        anio_actual = datetime.now().year

        df_mes = df[
            (pd.to_datetime(df["Fecha"]).dt.month == mes_numero) &
            (pd.to_datetime(df["Fecha"]).dt.year == anio_actual)
        ]

        with st.expander("Eliminar transacciones registradas"):
            st.markdown("""
            <style>
                .tabla-header div {
                    font-weight: bold;
                    border-bottom: 1px solid #ccc;
                    padding: 6px 0;
                }
            </style>
            """, unsafe_allow_html=True)

            header = st.columns([0.5, 1.2,1.5, 1.5, 1.5, 1, 0.7])
            header[0].markdown("**ID**")
            header[1].markdown("**Fecha**")
            header[2].markdown("**Descripcion**")
            header[3].markdown("**Categoría**")
            header[4].markdown("**Cuenta**")
            header[5].markdown("**Monto**")
            header[6].markdown("**Acción**")

            
            #Edicion de registros
            for idx, row in df.iterrows():
                with st.container():
                    cols = st.columns([0.5, 1.2,1.5, 1.5, 1.5, 1, 0.7])
                    cols[0].write(row["ID"])
                    cols[1].write(row["Fecha"])
                    cols[2].write(row["Descripcion"])
                    cols[3].write(row["Categoria"])
                    cols[4].write(row["Cuenta"])
                    cols[5].write(f"${row['Monto']:,.2f}")

                    if cols[6].button("🗑️", key=f"delete_{row['ID']}_{idx}"):
                        # Confirmación opcional (puedes quitar esto si no lo deseas)
                        # confirm = st.confirm(f"¿Borrar transacción ID {row['ID']}?")
                        # if confirm:
                        with engine.begin() as conn:
                            conn.execute(
                                text("DELETE FROM transacciones WHERE ID = :id AND Usuario = :username"),
                                {"id": row["ID"], "username": username}
                            )
                        st.session_state.transacciones = cargar_transacciones_usuario(engine, username)
                        st.rerun()

# ─────────────────────────────────────────────────────────────
# Sección: Ver métricas y consultar a BILLIE (agente financiero)
# ─────────────────────────────────────────────────────────────
elif seccion == "dashboard":
    if df.empty:
        st.info("No hay transacciones registradas. Empie")
        if st.button("🛠️ Armar presupuesto ahora"):
            st.session_state.seccio = "registro"
            st.rerun()
    else:
        try:
            # Intenta con el locale estándar para español en Linux
            locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
        except locale.Error:
            try:
                # Intenta con el locale de Windows (en caso de entorno local)
                locale.setlocale(locale.LC_TIME, 'Spanish_Mexico.1252')
            except locale.Error:
                # Si nada funciona, sigue con el locale por defecto
                pass

        # Obtener nombre del mes actual
        mes_actual = datetime.now().strftime('%B').capitalize()
        mes_numero = datetime.now().month
        anio_actual = datetime.now().year

        # Filtrar transacciones del mes actual
        df_mes = df[
            (pd.to_datetime(df["Fecha"]).dt.month == mes_numero) &
            (pd.to_datetime(df["Fecha"]).dt.year == anio_actual)
        ]

        # Calcular métricas del mes actual
        ingresos = df_mes[(df_mes["Monto"] > 0)&(df_mes["Usuario"]==username)]["Monto"].sum()
        gastos = df_mes[(df_mes["Monto"] < 0)&(df_mes["Usuario"]==username)]["Monto"].sum()
        balance = ingresos + gastos
        ahorro_pct = (balance / ingresos * 100) if ingresos > 0 else 0

        # Mensaje de bienvenida
        
        st.markdown(f"""<h1 style='text-align: center;'>
            Hola {name}
        </h1>""", unsafe_allow_html=True)

        st.markdown(f"""<p style='text-align: center; font-size: 20px;'>
            Soy Billie, tu asesor financiero personal
        </p>""", unsafe_allow_html=True)

        st.markdown(f"""<p style='text-align: center; font-size: 20px;'>
            Aquí tienes un resumen de tus finanzas de <strong>{mes_actual}</strong>
        </p>""", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        # Mostrar métricas con estilo
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(f"<h2 style='text-align:center; color:#446DF6; font-size:40px'>${balance:,.2f}</h2>", unsafe_allow_html=True)
            st.markdown("<p style='text-align:center;font-size:20px'>Lo que te queda</p>", unsafe_allow_html=True)

        with col2:
            st.markdown(f"<h2 style='text-align:center; color:#27A365;font-size:40px''>${ingresos:,.2f}</h2>", unsafe_allow_html=True)
            st.markdown("<p style='text-align:center;font-size:20px'>Lo que ganaste</p>", unsafe_allow_html=True)

        with col3:
            st.markdown(f"<h2 style='text-align:center; color:#DC143C;font-size:40px'>${gastos:,.2f}</h2>", unsafe_allow_html=True)
            st.markdown("<p style='text-align:center;font-size:20px'>Lo que gastaste </p>", unsafe_allow_html=True)

 

  
        # Agente
        agent = crear_agente(username, engine)

        # ────────────────
        # ESTILO PERSONALIZADO
        # ────────────────
        # CSS unificado y correcto
        st.markdown("""
            <style>
            .custom-button button {
                background-color: #1e1e1e !important;
                color: black !important;
                font-size: 16px !important;
                padding: 0.6rem 1.2rem !important;
                border-radius: 8px !important;
                transition: all 0.3s ease;
                border: none !important;
            }
            .custom-button button:hover {
                background-color: #333 !important;
                color: #6495ED !important;
            }

            .enviar-btn button {
                background-color: #1e1e1e !important;
                color: white !important;
                font-size: 32px !important;
                padding: 0.5rem 1.2rem !important;
                border-radius: 10px !important;
                border: none !important;
                transition: background-color 0.3s ease;
                margin-top: 0.6rem;
            }

            .enviar-btn button:hover {
                background-color: #333 !important;
                color: #6495ED !important;
            }
            </style>
        """, unsafe_allow_html=True)

        # ────────────────
        # BLOQUE DE INTERACCIÓN CON BILLIE
        # ────────────────
        st.markdown("## ¿En que puedo ayudarte hoy?")

        
        # Inicializar variable de respuesta fuera del flujo
        respuesta = None
        pregunta_seleccionada = None

        # Botones fila 1
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        if col1.button("¿Cuánto he gastado?", key="btn1"):
            pregunta_seleccionada = "¿Cuánto he gastado en total?"
        elif col2.button("¿Metas financieras?", key="btn2"):
            pregunta_seleccionada = "¿Cuánto he gastado en Metas financieras?"
        elif col3.button("Ingresos", key="btn3"):
            pregunta_seleccionada = "¿Cuánto dinero he ingresado?"
        elif col4.button("Ultimas transacciones", key="btn4"):
            pregunta_seleccionada = "Muéstrame las últimas transacciones"
        elif col5.button("Balance", key="btn5"):
            pregunta_seleccionada = "¿Cuál es mi balance actual?"
        elif col6.button("Gastos por mes", key="btn6"):
            pregunta_seleccionada = "¿Qué gastos he tenido por mes?"

        # Botones fila 2
        col7, col8, col9, col10, col11, col12 = st.columns(6)
        if col7.button("Mayor gasto", key="btn7"):
            pregunta_seleccionada = "¿Cuál ha sido mi mayor gasto?"
        elif col8.button("Porcentaje de gastos respecto a Metas financieras", key="btn8"):
            pregunta_seleccionada = "¿Cuál es el porcentaje de mis gastos que corresponde a metas financieras?"
        elif col9.button("Promedio mensual", key="btn9"):#Check
            pregunta_seleccionada = "¿Cuál es mi gasto promedio mensual?"
        elif col10.button("Sugerencia de ahorro", key="btn10"):
            pregunta_seleccionada = "¿Me puedes sugerir una meta de ahorro?"
        elif col11.button("Proyectar saldo", key="btn11"):
            pregunta_seleccionada = "¿Cuál será mi saldo al final del mes si sigo con este ritmo?"
        elif col12.button("Presupuesto recomendado", key="btn12"):#Check
            pregunta_seleccionada = "¿Cuál sería un presupuesto mensual recomendado para mí?"

        # Input de texto personalizado
        user_prompt_dashboard = st.chat_input(placeholder="O pregunta lo que quieras...", key=f"user_input_dashoboards_{username}")

        # Prioridad: input > botón
        if user_prompt_dashboard:
            pregunta_seleccionada = user_prompt_dashboard

        # Ejecutar si hay algo que responder
        if pregunta_seleccionada:
            with st.spinner("BILLIE está pensando..."):
                respuesta = agent.run(pregunta_seleccionada)

        # Mostrar respuesta (solo una sección visible)
        if respuesta:
            st.markdown("### Respuesta")
            st.markdown(respuesta)
# ─────────────────────────────────────────────────────────────
# Sección: Ver ahorro y metas financieras (agente financiero)
# ─────────────────────────────────────────────────────────────
elif seccion == "ahorro":
    # Calcular ahorro total en la categoría "Metas Financieras"
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT ABS(SUM(Monto)) FROM transacciones WHERE Usuario = :u AND Categoria = 'Metas financieras 💰'"),
            {"u": username}
        )
        total_ahorrado = result.scalar() or 0

    
    # Calcular total asignado a metas
    with engine.connect() as conn:
        df_metas = pd.read_sql("SELECT * FROM metas_financieras WHERE usuario = :u", conn, params={"u": username})
        total_asignado = df_metas["monto_actual"].sum()
        ahorro_disponible = total_ahorrado - total_asignado

    st.markdown(f"""
    <div style='text-align: center;'>
        <div style='display: inline-block; background-color: #56A163; padding: 15px 40px; border-radius: 10px; margin-top: 10px;'>
            <div style='color: white; font-size: 20px;'>Dale propósito a tus</div>
            <div style='color:#f9e423; font-size: 30px; font-weight: bold; margin-top: 5px;'>${total_ahorrado:,.0f}</div>
            <div style='color: white; font-size: 16px; margin-top: 5px;'>Disponible: ${ahorro_disponible:,.0f}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("")
    st.info(f"Billie:\n\n{name}\n\n¡Vamos a empezar a mover tu dinero con propósito! Crea tu primera meta financiera y descubre lo rápido que una idea se convierte en realidad cuando Billie te acompaña paso a paso.")
    st.markdown("")
    if len(df_metas) < 3:
        with st.expander("¡Quiero crear una nueva meta!"):
            with st.form("form_nueva_meta", clear_on_submit=True):
                nombre = st.text_input("Nombre de la meta")
                monto = st.number_input("Monto objetivo", min_value=100.0, step=100.0)
                plazo = st.number_input("Plazo para lograrlo (meses)", min_value=1, step=1)

                submit = st.form_submit_button("Guardar")
                if submit:
                    with engine.begin() as conn:
                        conn.execute(text("""
                            INSERT INTO metas_financieras (usuario, nombre_meta, monto_objetivo, plazo_meses, fecha_creacion)
                            VALUES (:u, :n, :m, :p, :f)
                        """), {
                            "u": username,
                            "n": nombre,
                            "m": monto,
                            "p": plazo,
                            "f": datetime.today().strftime("%Y-%m-%d")
                        })
                    st.success("🎯 Meta creada exitosamente.")
                    st.info("✔️ Cambios realizados. Por favor recarga la página para ver los resultados.")

    cols = st.columns(3)
    for i, row in df_metas.iterrows():
        progreso = (row["monto_actual"] / row["monto_objetivo"]) * 100
        restante = row["monto_objetivo"] - row["monto_actual"]
        mensual = restante / row["plazo_meses"]

        # Color dinámico basado en el progreso
        if progreso < 30:
            fondo = "#FFE5E5"  # rojo suave
        elif progreso < 70:
            fondo = "#FFF8DC"  # amarillo suave
        else:
            fondo = "#E6FFEA"  # verde suave

        with cols[i % 3]:
            with st.container():
                st.markdown(f"""
                <div style='background-color: {fondo}; padding: 15px; border-radius: 15px; box-shadow: 0px 2px 5px rgba(0,0,0,0.1); margin-bottom: 10px;'>
                """, unsafe_allow_html=True)

                st.markdown(f"#### {row['nombre_meta']}")
                st.metric("Ahorro actual", f"${row['monto_actual']:,.0f}")
                st.markdown(f"de ${row['monto_objetivo']:,.0f} ahorrados")
                st.progress(progreso / 100)
                st.caption(f"Progreso: {progreso:.1f}% | Te faltan ${restante:,.0f} y {row['plazo_meses']} meses para lograrlo")
                st.markdown("</div>", unsafe_allow_html=True)

                with st.expander(f"Asignar ahorro a '{row['nombre_meta']}'"):
                    with st.form(f"form_asignar_{row['id']}"):
                        monto_asignar = st.number_input(
                            "Monto a asignar", min_value=0.0,
                            max_value=ahorro_disponible,
                            key=f"input_{row['id']}"
                        )
                        confirmar_asignacion = st.form_submit_button("Confirmar asignación")
                        if confirmar_asignacion:
                            if monto_asignar > ahorro_disponible:
                                st.error("🚫 No tienes suficiente ahorro para asignar ese monto.")
                            else:
                                with engine.begin() as conn:
                                    conn.execute(text("""
                                        UPDATE metas_financieras
                                        SET monto_actual = monto_actual + :m
                                        WHERE id = :id
                                    """), {"m": monto_asignar, "id": row["id"]})
                                st.success("✅ Monto asignado correctamente.")
                                st.info("✔️ Cambios realizados. Por favor recarga la página para ver los resultados.")

                with st.expander("Editar meta"):
                    with st.form(f"form_editar_{row['id']}"):
                        nuevo_nombre = st.text_input("Nuevo nombre", value=row['nombre_meta'])
                        nuevo_monto = st.number_input("Nuevo monto objetivo", value=row['monto_objetivo'], step=100.0)
                        nuevo_plazo = st.number_input("Nuevo plazo (meses)", value=row['plazo_meses'], min_value=1, step=1)
                        submit_edit = st.form_submit_button("Guardar cambios")

                        if submit_edit:
                            with engine.begin() as conn:
                                conn.execute(text("""
                                    UPDATE metas_financieras
                                    SET nombre_meta = :n, monto_objetivo = :m, plazo_meses = :p
                                    WHERE id = :id
                                """), {
                                    "n": nuevo_nombre,
                                    "m": nuevo_monto,
                                    "p": nuevo_plazo,
                                    "id": row["id"]
                                })
                            st.success("✏️ Meta actualizada.")
                            st.info("✔️ Cambios realizados. Por favor recarga la página para ver los resultados.")

                with st.expander("Eliminar meta"):
                    with st.form(f"form_eliminar_{row['id']}"):
                        confirmar_eliminar = st.checkbox("Confirmo que deseo eliminar esta meta")
                        submit_eliminar = st.form_submit_button("Eliminar meta")

                        if submit_eliminar and confirmar_eliminar:
                            with engine.begin() as conn:
                                conn.execute(text("DELETE FROM metas_financieras WHERE id = :id"), {"id": row["id"]})
                            st.success("Meta eliminada.")
                            st.info("✔️ Cambios realizados. Por favor recarga la página para ver los resultados.")
    
        #Insertar agente
    agent = crear_agente(username, engine)
        #Set respuesta a None
    respuesta = None
    # Input de texto personalizado
    user_prompt_ahorro = st.chat_input(placeholder="Pregunta a BILLIE sobre tus metas...", key=f"user_input_ahorro_{username}")
    # Ejecutar si hay algo que responder
    if user_prompt_ahorro:
        with st.spinner("BILLIE está pensando..."):
            respuesta = agent.run(user_prompt_ahorro)

        # Mostrar respuesta (solo una sección visible)
    if respuesta:
        st.markdown("### Respuesta")
        st.markdown(respuesta)
