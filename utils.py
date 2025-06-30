import pandas as pd
import streamlit as st
import re
from datetime import datetime
import unicodedata
from sqlalchemy import text
from calendar import monthrange
import yfinance as yf
from prophet import Prophet
import numpy as np
import os
from PIL import Image
import base64
from io import BytesIO


def cargar_transacciones_usuario(engine, username):
    try:
        with engine.connect() as conn:
            df = pd.read_sql_query(
                text("SELECT * FROM transacciones WHERE Usuario = :username"),
                conn,
                params={"username": username}
            )
    except Exception as e:
        print(f"Error al cargar transacciones: {e}")
        df = pd.DataFrame(columns=["ID", "Fecha","Descripcion", "Categoria", "Cuenta", "Monto", "Usuario"])
    return df

def guardar_transaccion_usuario(engine, fecha, categoria, cuenta, monto, username, descripcion):
    with engine.begin() as conn:
        next_id = int(st.session_state.transacciones["ID"].max() + 1) if not st.session_state.transacciones.empty else 1
        conn.execute(
            text("""
                INSERT INTO transacciones (ID,Usuario, Fecha, Categoria, Cuenta, Monto,Descripcion)
                VALUES (:ID,:Usuario, :Fecha, :Categoria, :Cuenta, :Monto,:Descripcion)
            """),
            {
                "ID": next_id,
                "Usuario": username,
                "Fecha": fecha.strftime("%Y-%m-%d"),
                "Categoria": categoria,
                "Cuenta": cuenta,
                "Monto": monto,
                "Descripcion": descripcion
            }
        )

def get_total_spent(username: str):
    df = st.session_state.get("transacciones", pd.DataFrame())
    if df.empty:
        return "No hay transacciones registradas."
    df = df[df["Usuario"] == username]
    total = df[df["Monto"] < 0]["Monto"].sum()
    return f"Has gastado ${abs(total):,.2f}"

def get_total_earned(username: str):
    df = st.session_state.get("transacciones", pd.DataFrame())
    if df.empty:
        return "No hay transacciones registradas."
    df = df[df["Usuario"] == username]
    total = df[df["Monto"] > 0]["Monto"].sum()
    return f"Has ingresado ${total:,.2f}"

def registrar_transaccion_desde_texto(texto, usuario, engine):
    def normalizar(text):
        return unicodedata.normalize("NFKD", text).encode("ASCII", "ignore").decode("utf-8").lower()

    MESES_ESPANOL = {
        "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
        "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
        "septiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12"
    }

    try:
        texto_norm = normalizar(texto)
        palabras_texto = set(texto_norm.split())
        categorias = {
            "necesidades": "Necesidades 🍎", "super": "Necesidades 🍎", "comida": "Necesidades 🍎", 
            "renta": "Necesidades 🍎", "medico": "Necesidades 🍎", "transporte": "Necesidades 🍎", "escuela": "Necesidades 🍎",
            "gustos": "Gustos 🎁", "cine": "Gustos 🎁", "restaurante": "Gustos 🎁", "ropa": "Gustos 🎁", "viaje": "Gustos 🎁",
            "metas financieras": "Metas financieras 💰", "ahorro": "Metas financieras 💰",
            "nomina": "Ingresos 💵", "ingreso": "Ingresos 💵", "quincena": "Ingresos 💵", "salario": "Ingresos 💵"
        }
        categoria = None
        for k, v in categorias.items():
            if k in palabras_texto:
                categoria = v
                break
        if not categoria:
            categoria = "Gustos 🎁"

        # Buscar descripción usando "en <palabra>"
        descripcion = categoria
        match_desc = re.search(r"en ([a-zA-Záéíóúñ]+)", texto_norm)
        if match_desc:
            descripcion = match_desc.group(1).capitalize()

        monto_match = re.search(r"(-?\$?\d+(?:[\.,]\d{1,2})?)", texto_norm)
        monto = float(monto_match.group().replace("$", "").replace(",", "")) if monto_match else 0.0

        palabras_egreso = ["gasto", "egreso", "pague", "pago", "compra", "retiro", "salida"]
        palabras_ingreso = ["ingreso", "abono", "deposito", "bonificacion", "reembolso", "reintegro"]
        if any(p in texto_norm for p in palabras_egreso):
            monto = -abs(monto)
        elif any(p in texto_norm for p in palabras_ingreso):
            monto = abs(monto)
        categorias_negativas = ["Necesidades 🍎", "Gustos 🎁", "Metas financieras 💰"]
        if categoria in categorias_negativas and monto > 0:
            monto = -abs(monto)

        cuenta_match = re.search(r"(tarjeta|banorte|bbva|hsbc|efectivo|cash|card)", texto_norm)
        cuenta = cuenta_match.group().capitalize() if cuenta_match else "General"

        fecha = datetime.now().date()
        fecha_match = re.search(r"(\d{1,2}) de ([a-zA-Z]+)", texto_norm)
        if fecha_match:
            dia = int(fecha_match.group(1))
            mes_str = fecha_match.group(2)
            mes_num = MESES_ESPANOL.get(mes_str)
            if mes_num:
                anio = datetime.today().year
                fecha_str = f"{anio}-{mes_num}-{dia:02d}"
                fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()

        with engine.connect() as conn:
            result = conn.execute(
                text("""
                SELECT COUNT(*) FROM transacciones
                WHERE Usuario = :Usuario AND Fecha = :Fecha AND Categoria = :Categoria AND Monto = :Monto AND Cuenta = :Cuenta
                """),
                {
                    "Usuario": usuario,
                    "Fecha": fecha.strftime("%Y-%m-%d"),
                    "Categoria": categoria,
                    "Monto": monto,
                    "Cuenta": cuenta
                }
            )
            ya_existe = result.scalar() > 0

        if ya_existe:
            return "⚠️ Esta transacción ya existe y no fue registrada de nuevo."

        with engine.begin() as conn:
            result = conn.execute(text("SELECT MAX(ID) FROM transacciones"))
            next_id = (result.scalar() or 0) + 1
            conn.execute(
                text("""
                    INSERT INTO transacciones (ID, Usuario, Fecha, Descripcion, Categoria, Cuenta, Monto)
                    VALUES (:ID, :Usuario, :Fecha, :Descripcion, :Categoria, :Cuenta, :Monto)
                """),
                {
                    "ID": next_id,
                    "Usuario": usuario,
                    "Fecha": fecha.strftime("%Y-%m-%d"),
                    "Descripcion": descripcion,
                    "Categoria": categoria,
                    "Cuenta": cuenta,
                    "Monto": monto
                }
            )

        tipo = "ingreso" if monto >= 0 else "gasto"
        return f"✅ Se registró un {tipo}: {descripcion} ({categoria}), {cuenta}, ${abs(monto):,.2f} el {fecha.isoformat()}"

    except Exception as e:
        return f"❌ Error al procesar el texto: {e}"



def get_gastos_por_categoria(categoria_input: str, username: str):
    df = st.session_state.get("transacciones", pd.DataFrame())
    if df.empty or "Categoria" not in df or "Monto" not in df or "Usuario" not in df:
        return "No hay datos de transacciones disponibles."
    categoria_input = categoria_input.strip().lower()
    CATEGORIA_ALIAS = {
        "necesidades": "Necesidades 🍎",
        "gustos": "Gustos 🎁",
        "metas financieras": "Metas financieras 💰"
    }
    categoria_real = CATEGORIA_ALIAS.get(categoria_input)
    if not categoria_real:
        return f"La categoría '{categoria_input}' no es válida. Usa: {', '.join(CATEGORIA_ALIAS.keys())}."
    df = df[df["Usuario"] == username]
    mask = (df["Categoria"] == categoria_real) & (df["Monto"] < 0)
    total = df[mask]["Monto"].sum()
    if total == 0:
        return f"No hay gastos registrados en la categoría '{categoria_real}'."
    return f"Gasto en {categoria_real}: ${abs(total):,.2f}"

def get_gastos_por_mes(mes: int, anio: int):
    df = st.session_state.get("transacciones", pd.DataFrame())
    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    mask = (df["Fecha"].dt.month == mes) & (df["Fecha"].dt.year == anio) & (df["Monto"] < 0)
    total = df[mask]["Monto"].sum()
    return f"Gasto en {anio}-{mes:02d}: ${abs(total):,.2f}"

def resumen_mensual():
    df = st.session_state.get("transacciones", pd.DataFrame())
    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    df["Mes"] = df["Fecha"].dt.to_period("M")
    resumen = df.groupby("Mes")["Monto"].sum().reset_index()
    resumen["Monto"] = resumen["Monto"].map(lambda x: f"${x:,.2f}")
    return resumen.to_string(index=False)

def get_balance_actual():
    df = st.session_state.get("transacciones", pd.DataFrame())
    total = df["Monto"].sum()
    return f"Tu balance actual es de ${total:,.2f}"

def get_ultimas_transacciones(n=5):
    df = st.session_state.get("transacciones", pd.DataFrame())
    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    ultimas = df.sort_values("Fecha", ascending=False).head(n)
    return ultimas[["Fecha","Descripcion","Categoria", "Cuenta", "Monto"]].to_string(index=False)

def get_promedio_gastos(periodo="mensual", username=None):
    df = st.session_state.get("transacciones", pd.DataFrame())
    if username:
        df = df[df["Usuario"] == username]
    df = df[df["Monto"] < 0]
    if df.empty:
        return "No hay gastos registrados."
    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    if periodo == "mensual":
        res = df.groupby([df["Fecha"].dt.year, df["Fecha"].dt.month])["Monto"].sum()
    elif periodo == "semanal":
        res = df.groupby(df["Fecha"].dt.isocalendar().week)["Monto"].sum()
    else:  # diario
        res = df.groupby(df["Fecha"].dt.date)["Monto"].sum()
    promedio = res.mean()
    return f"El gasto promedio {periodo} es de ${abs(promedio):,.2f}"

def proyeccion_saldo_fin_mes(username=None):
    df = st.session_state.get("transacciones", pd.DataFrame())
    if username:
        df = df[df["Usuario"] == username]
    if df.empty:
        return "No hay datos suficientes."
    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    hoy = datetime.today()
    saldo_actual = df["Monto"].sum()
    gastos_mes = df[(df["Fecha"].dt.month == hoy.month) & (df["Monto"] < 0)]["Monto"].sum()
    ingresos_mes = df[(df["Fecha"].dt.month == hoy.month) & (df["Monto"] > 0)]["Monto"].sum()
    dias_mes = monthrange(hoy.year, hoy.month)[1]
    dias_faltantes = dias_mes - hoy.day
    gasto_diario = gastos_mes / hoy.day if hoy.day > 0 else 0
    ingreso_diario = ingresos_mes / hoy.day if hoy.day > 0 else 0
    saldo_proyectado = saldo_actual + (dias_faltantes * (ingreso_diario + gasto_diario))
    return f"Tu saldo proyectado a fin de mes es de ${saldo_proyectado:,.2f}"

def ranking_gastos_categorias(username=None, top=3):
    df = st.session_state.get("transacciones", pd.DataFrame())
    if username:
        df = df[df["Usuario"] == username]
    gastos = df[df["Monto"] < 0].groupby("Categoria")["Monto"].sum().abs().sort_values(ascending=False)
    if gastos.empty:
        return "No hay gastos registrados."
    return gastos.head(top).to_string()

def ranking_ingresos_categorias(username=None, top=3):
    df = st.session_state.get("transacciones", pd.DataFrame())
    if username:
        df = df[df["Usuario"] == username]
    ingresos = df[df["Monto"] > 0].groupby("Categoria")["Monto"].sum().sort_values(ascending=False)
    if ingresos.empty:
        return "No hay ingresos registrados."
    return ingresos.head(top).to_string()

def porcentaje_gastos_por_categoria(username=None):
    df = st.session_state.get("transacciones", pd.DataFrame())
    if username:
        df = df[df["Usuario"] == username]
    total_gastos = abs(df[df["Monto"] < 0]["Monto"].sum())
    if total_gastos == 0:
        return "No hay gastos registrados."
    resumen = df[df["Monto"] < 0].groupby("Categoria")["Monto"].sum().abs() / total_gastos * 100
    return resumen.round(2).to_string()

def alerta_gasto_excesivo(username=None):
    df = st.session_state.get("transacciones", pd.DataFrame())
    if username:
        df = df[df["Usuario"] == username]
    if df.empty:
        return "No hay datos suficientes."
    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    mes_actual = datetime.now().month
    gastos_mes = abs(df[(df["Fecha"].dt.month == mes_actual) & (df["Monto"] < 0)]["Monto"].sum())
    promedio_6m = abs(df[df["Monto"] < 0].groupby(df["Fecha"].dt.to_period("M"))["Monto"].sum()).mean()
    if gastos_mes > promedio_6m * 1.2:
        return "🚨 ¡Alerta! Este mes has gastado más de lo habitual. Revisa tus gastos."
    return "Tus gastos van dentro de lo normal."

def sugerencia_ahorro(username=None):
    df = st.session_state.get("transacciones", pd.DataFrame())
    if username:
        df = df[df["Usuario"] == username]
    top_gusto = df[df["Categoria"] == "Gustos 🎁"]["Monto"].sum()
    if top_gusto < 0:
        return f"Si reduces tus gastos en 'Gustos 🎁' un 20%, podrías ahorrar ${abs(top_gusto)*0.2:,.2f} este mes."
    return "No hay gastos suficientes para sugerencias."

def buscar_transacciones(keyword, username=None):
    df = st.session_state.get("transacciones", pd.DataFrame())
    if username:
        df = df[df["Usuario"] == username]
    matches = df[df["Descripcion"].str.contains(keyword, case=False, na=False)]
    if matches.empty:
        return "No se encontraron transacciones."
    return matches[["Fecha","Descripcion","Categoria","Cuenta","Monto"]].to_string(index=False)

def evolucion_balance(username=None):
    df = st.session_state.get("transacciones", pd.DataFrame())
    if username:
        df = df[df["Usuario"] == username]
    if df.empty:
        return pd.DataFrame(columns=["Fecha", "Balance"])
    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    df = df.sort_values("Fecha")
    df["Balance"] = df["Monto"].cumsum()
    return df[["Fecha", "Balance"]]

def comparativa_gastos_mensual(username=None):
    df = st.session_state.get("transacciones", pd.DataFrame())
    if username:
        df = df[df["Usuario"] == username]
    if df.empty:
        return "No hay transacciones."
    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    resumen = df[df["Monto"] < 0].groupby(df["Fecha"].dt.to_period("M"))["Monto"].sum().abs()
    return resumen.round(2).to_string()

def gastos_recurrentes(username=None):
    df = st.session_state.get("transacciones", pd.DataFrame())
    if username:
        df = df[df["Usuario"] == username]
    if df.empty:
        return "No hay transacciones."
    recurrentes = df[df["Monto"] < 0]["Descripcion"].value_counts()
    recurrentes = recurrentes[recurrentes > 2]
    if recurrentes.empty:
        return "No se detectaron gastos recurrentes."
    return recurrentes.to_string()

def sugerencia_presupuesto(username=None):
    df = st.session_state.get("transacciones", pd.DataFrame())
    if username:
        df = df[df["Usuario"] == username]
    if df.empty:
        return "No hay transacciones."
    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    promedio_gasto = abs(df[df["Monto"] < 0].groupby(df["Fecha"].dt.to_period("M"))["Monto"].sum()).mean()
    sugerido = promedio_gasto * 0.9  # Sugerir gastar un 10% menos
    return f"Te sugerimos establecer un presupuesto mensual máximo de ${sugerido:,.2f}."

def simulador_sin_gasto_en(categoria, username=None):
    df = st.session_state.get("transacciones", pd.DataFrame())
    if username:
        df = df[df["Usuario"] == username]
    if df.empty:
        return "No hay transacciones."
    total_categoria = df[(df["Categoria"] == categoria) & (df["Monto"] < 0)]["Monto"].sum()
    saldo_actual = df["Monto"].sum()
    saldo_proyectado = saldo_actual - total_categoria
    return f"Si dejas de gastar en {categoria}, tu balance aumentaría a ${saldo_proyectado:,.2f}."

def get_total_ahorrado(engine, username):
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT ABS(SUM(Monto)) FROM transacciones WHERE Usuario = :u AND Categoria = 'Metas financieras 💰'"),
            {"u": username}
        )
        total = result.scalar() or 0
    return f"Tu ahorro total en 'Metas financieras 💰' es de ${total:,.2f}"

def get_total_asignado_metas(engine, username):
    with engine.connect() as conn:
        df_metas = pd.read_sql("SELECT * FROM metas_financieras WHERE usuario = :u", conn, params={"u": username})
    asignado = df_metas["monto_actual"].sum()
    return f"Tienes ${asignado:,.2f} asignados actualmente a tus metas."

def get_ahorro_disponible(engine, username):
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT ABS(SUM(Monto)) FROM transacciones WHERE Usuario = :u AND Categoria = 'Metas financieras 💰'"),
            {"u": username}
        )
        total = result.scalar() or 0
        df_metas = pd.read_sql("SELECT * FROM metas_financieras WHERE usuario = :u", conn, params={"u": username})
    asignado = df_metas["monto_actual"].sum()
    disponible = total - asignado
    return f"Tu ahorro disponible (no asignado a ninguna meta) es de ${disponible:,.2f}"

def get_resumen_metas(engine, username):
    with engine.connect() as conn:
        df = pd.read_sql("SELECT * FROM metas_financieras WHERE usuario = :u", conn, params={"u": username})
    if df.empty:
        return "Aún no tienes metas financieras registradas."

    resumen = "Aquí tienes un resumen de tus metas:\n\n"
    for _, row in df.iterrows():
        progreso = (row["monto_actual"] / row["monto_objetivo"]) * 100
        restante = row["monto_objetivo"] - row["monto_actual"]
        resumen += (
            f"- {row['nombre_meta']}: ${row['monto_actual']:,.0f} de ${row['monto_objetivo']:,.0f} ahorrados "
            f"({progreso:.1f}% completado, faltan ${restante:,.0f})\n"
        )
    return resumen

def get_recomendacion_asignacion(engine, username):
    with engine.connect() as conn:
        df = pd.read_sql("SELECT * FROM metas_financieras WHERE usuario = :u ORDER BY plazo_meses ASC", conn, params={"u": username})
        result = conn.execute(
            text("SELECT ABS(SUM(Monto)) FROM transacciones WHERE Usuario = :u AND Categoria = 'Metas financieras 💰'"),
            {"u": username}
        )
        total_ahorrado = result.scalar() or 0
        asignado = df["monto_actual"].sum()
        disponible = total_ahorrado - asignado

    if disponible <= 0:
        return "No tienes ahorro disponible para asignar a tus metas por ahora."

    mensaje = f"Tienes ${disponible:,.0f} disponibles. Puedes asignarlos así:\n\n"
    for _, row in df.iterrows():
        restante = row["monto_objetivo"] - row["monto_actual"]
        sugerido = min(disponible, restante)
        if sugerido > 0:
            mensaje += f"- Asignar ${sugerido:,.0f} a '{row['nombre_meta']}'\n"
            disponible -= sugerido
        if disponible <= 0:
            break

    return mensaje

def construir_presupuesto_asistido(username: str, engine):
    """
    Interacción asistida para sugerir presupuesto basado en ingreso y preferencias.
    Guarda o actualiza el presupuesto en la tabla presupuestos.
    """

    ingreso = st.text_input("¿Cuánto ganas al mes (aproximadamente)? Puedes escribirlo con palabras o números")
    if ingreso:
        try:
            ingreso_valor = float(ingreso.replace(",", "").replace("$", ""))
        except:
            st.error("⛔️ No pude entender el monto que escribiste. Intenta escribirlo en números como 10000 o $10,000.")
            return

        st.markdown("""
        ### ¿Qué parte de tu ingreso quieres destinar a:
        (Puedes ajustar los valores o escribir sugerencias como "quiero ahorrar más", "que sea balanceado", etc.)
        """)
        estilo = st.radio("Estilo de reparto de presupuesto", [
            "Clásico 50/30/20",
            "Quiero ahorrar más",
            "Quiero gastar más en gustos",
            "Personalizado"
        ])

        if estilo == "Clásico 50/30/20":
            porc_nec, porc_gus, porc_met = 50, 30, 20
        elif estilo == "Quiero ahorrar más":
            porc_nec, porc_gus, porc_met = 40, 25, 35
        elif estilo == "Quiero gastar más en gustos":
            porc_nec, porc_gus, porc_met = 40, 45, 15
        else:
            porc_nec = st.slider("Necesidades", 0, 100, 50)
            porc_gus = st.slider("Gustos", 0, 100 - porc_nec, 30)
            porc_met = 100 - (porc_nec + porc_gus)

        st.info(f"Asignación propuesta:")
        st.markdown(f"- 🍎 Necesidades: **{porc_nec}%** → ${ingreso_valor * porc_nec / 100:,.2f}")
        st.markdown(f"- 🎁 Gustos: **{porc_gus}%** → ${ingreso_valor * porc_gus / 100:,.2f}")
        st.markdown(f"- 💰 Metas: **{porc_met}%** → ${ingreso_valor * porc_met / 100:,.2f}")

        if st.button("✅ Confirmar y guardar presupuesto"):
            with engine.begin() as conn:
                conn.execute(
                    text("""
                        INSERT OR REPLACE INTO presupuestos (Usuario, Necesidades, Gustos, MetasFinancieras)
                        VALUES (:Usuario, :Necesidades, :Gustos, :MetasFinancieras)
                    """),
                    {
                        "Usuario": username,
                        "Necesidades": ingreso_valor * porc_nec / 100,
                        "Gustos": ingreso_valor * porc_gus / 100,
                        "MetasFinancieras": ingreso_valor * porc_met / 100
                    }
                )
            st.success("Presupuesto guardado con éxito.")
            st.rerun()
#________________________________
#**Funciones de perfil de ahorro
#________________________________
def obtener_perfil_ahorro(engine, username):
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT perfil_ahorro, perfil_riesgo FROM perfiles_ahorro WHERE usuario = :u"),
            {"u": username}
        ).mappings().first()

    if result:
        return result["perfil_ahorro"], result["perfil_riesgo"]
    else:
        return None, None

def cargar_fondos_desde_db(engine):#Fondos de inversion
    with engine.connect() as conn:
        #df = pd.read_sql("SELECT * FROM fondos_inversion", conn)
        df = pd.read_sql("SELECT * FROM fondos_inversion_v2", conn)
    return df

'''
def construir_prompt_recomendaciones_fondos(df_resumen_fondos, perfil_usuario):
    filas = []
    for _, row in df_resumen_fondos.iterrows():
        linea = (
            f"- {row['Nombre coloquial']} → {row['perfil_recomendado']} "
            f"(rendimiento promedio: {row['vl_promedio']:.2f}, volatilidad: {row['vl_std']:.2f})"
        )
        filas.append(linea)

    listado_fondos = "\n".join(filas)

    prompt = f"""
Eres un asesor financiero. El usuario tiene un perfil de riesgo **{perfil_usuario}**.

Aquí tienes fondos de inversión disponibles en México, clasificados por perfil, con su rendimiento histórico y volatilidad:

{listado_fondos}

Responde en lenguaje claro y práctico, sin tecnicismos. Tu respuesta debe contener:

1. Una introducción breve.
2. 3 fondos recomendados alineados con el perfil del usuario, explicando por qué.
3. Al menos 1 instrumento adicional de renta fija y 1 de renta variable con base al perfil.
4. En cada recomendación, si conoces un sitio web público o confiable (como el de la operadora, Morningstar, la CNBV o el documento informativo del fondo), agrega un **enlace directo** al final.
5. Si no tienes un enlace exacto, sugiere dónde podría buscar información confiable (ej. "busca en el sitio de GBM" o "consulta Morningstar México").
"""

    return prompt
'''
def construir_prompt_recomendaciones_fondos(df_fondos, perfil_usuario):
    df_fondos.columns = [col.strip().replace(" ", "_").lower() for col in df_fondos.columns]

    fondos_filtrados = df_fondos[df_fondos["riesgo"].str.lower() == perfil_usuario.lower()]

    if fondos_filtrados.empty:
        return f"No se encontraron fondos para el perfil de riesgo '{perfil_usuario}'."

    resumen = "\n".join(
        f"- {row['fondo']} ({row['administradora_del_fondo']}): {row['horizonte']}, "
        f"Liquidez: {row['liquidez']}, Calificación: {row['calificación']}, Ticker: {row['ticker']}"
        for _, row in fondos_filtrados.iterrows()
    )
    prompt = f"""
Eres un asesor financiero y el usuario tiene un perfil de riesgo **{perfil_usuario}**.

Estos son algunos fondos compatibles con su perfil:

{resumen}
Responde en lenguaje claro y práctico en forma de lista, sin tecnicismos. Tu respuesta debe contener:

1. Una introducción breve.
2. Elige 4 fondos para recomendar, y explica por qué, con base en su horizonte, calificación y liquidez.
3. Al menos 1 instrumento adicional de renta fija y 1 de renta variable con base al perfil.
4. En cada recomendación, si conoces un sitio web público o confiable (como el de la operadora, Morningstar, la CNBV o el documento informativo del fondo), agrega un **enlace directo** al final.
5. Si no tienes un enlace exacto, sugiere dónde podría buscar información confiable (ej. "busca en el sitio de GBM" o "consulta Morningstar México").


"""
    return prompt

def simular_inversion(monto_inicial: float, tasa_anual: float, años: int):
    return monto_inicial * (1 + tasa_anual) ** años

def calcular_evolucion_anual(monto_inicial, tasa_anual, años):
    return [round(monto_inicial * (1 + tasa_anual) ** a, 2) for a in range(años + 1)]

def forecast_yf_ticker(ticker: str, monto_inicial: float, años: int):
    try:
        #df = yf.Ticker(ticker, period="max", interval="1d", progress=False)[["Close"]].dropna()
        fondo = yf.Ticker(ticker)
        hist = fondo.history(period="max")
        df = hist[["Close"]].reset_index()
        df = df.reset_index().rename(columns={"Date": "ds", "Close": "y"})
        df["ds"]=df["ds"].dt.tz_localize(None)
        df = df[df["y"] > 0]

        model = Prophet(daily_seasonality=True)
        model.fit(df)

        future = model.make_future_dataframe(periods=años * 365)
        forecast = model.predict(future)

        df_merge = forecast[["ds", "yhat"]].tail(1)
        final_price = df_merge["yhat"].values[0]
        initial_price = df["y"].iloc[-1]

        crecimiento = final_price / initial_price
        monto_final = monto_inicial * crecimiento
        cagr = (crecimiento) ** (1 / años) - 1

        return monto_final, cagr, model, df, forecast
    except Exception as e:
        return None, None, None, None, None

# Función para convertir imagen a base64
def image_to_base64(img_filename):
    base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '.'))
    img_path = os.path.join(base_path, img_filename)
    img = Image.open(img_path)
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

