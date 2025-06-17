import os
import joblib
import pickle
import gdown
import streamlit as st

# ─── IDs de Google Drive ───────────────────────────────
modelo_id = "1vc7JsZuf74vgeJYY2fTglFhqS0BheHBa"
columnas_id = "1AwKtDlQNGssylCZ3zFR-14hfTVLnjtDs"

# ─── Rutas locales ─────────────────────────────────────
modelo_path = "modelos/modelo_perfil_ahorro.pkl"
columnas_path = "modelos/columnas_modelo.pkl"

# ─── Crear carpeta local ───────────────────────────────
os.makedirs("modelos", exist_ok=True)

# ─── Descargar desde Google Drive ──────────────────────
def descargar_archivo_gdrive(file_id, output_path):
    url = f"https://drive.google.com/uc?id={file_id}"
    gdown.download(url, output_path, quiet=False)

# ─── Validar archivo pickle ────────────────────────────
def validar_pickle(path, descripcion, espera_tipo):
    if not os.path.exists(path):
        return f"❌ {descripcion}: el archivo no existe."

    size = os.path.getsize(path)
    st.write(f"📦 {descripcion} - Tamaño: {size} bytes")
    if size < 1000:
        return f"❌ {descripcion}: el archivo es muy pequeño para ser válido."

    with open(path, "rb") as f:
        cabecera = f.read(100)
    st.code(cabecera, language="python")

    if b'<!DOCTYPE html' in cabecera or b'<html' in cabecera:
        return f"❌ {descripcion}: el archivo descargado es HTML, no un pickle válido."

    try:
        obj = joblib.load(path)
    except Exception as e1:
        st.warning(f"⚠️ {descripcion}: joblib falló: {e1}")
        try:
            with open(path, "rb") as f:
                obj = pickle.load(f)
        except Exception as e2:
            return f"❌ {descripcion}: no se pudo cargar ni con joblib ni pickle.\n{e2}"

    # Validaciones específicas por tipo esperado
    if espera_tipo == "modelo":
        if not hasattr(obj, "predict"):
            return f"❌ {descripcion}: el archivo se cargó pero no tiene método `predict`."
    elif espera_tipo == "columnas":
        if not isinstance(obj, list):
            return f"❌ {descripcion}: se esperaba una lista, se recibió: {type(obj)}"
        st.write(f"📋 Columnas cargadas: {obj[:5]}... (+{len(obj)} columnas totales)")

    st.success(f"✅ {descripcion} cargado correctamente.")
    return obj

# ─── Ejecución ─────────────────────────────────────────
if st.button("🔍 Verificar modelo y columnas descargadas"):
    # Modelo
    if not os.path.exists(modelo_path):
        st.info("⬇️ Descargando modelo desde Google Drive...")
        descargar_archivo_gdrive(modelo_id, modelo_path)
    resultado_modelo = validar_pickle(modelo_path, "Modelo", espera_tipo="modelo")

    # Columnas
    if not os.path.exists(columnas_path):
        st.info("⬇️ Descargando columnas desde Google Drive...")
        descargar_archivo_gdrive(columnas_id, columnas_path)
    resultado_columnas = validar_pickle(columnas_path, "Columnas", espera_tipo="columnas")

    if isinstance(resultado_modelo, str) and resultado_modelo.startswith("❌"):
        st.error(resultado_modelo)
    if isinstance(resultado_columnas, str) and resultado_columnas.startswith("❌"):
        st.error(resultado_columnas)
    if not isinstance(resultado_modelo, str) and not isinstance(resultado_columnas, str):
        st.success("🎯 Validación final exitosa: modelo y columnas listas para usarse.")
