import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import streamlit.components.v1 as components
import uuid
from auth import load_authenticator
import re

#─── Autenticacion ─────────────────────────────
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

# ─── Conexión a la base y carga de perfil ─────────────────────────────
engine = create_engine("sqlite:///transacciones.db")

def obtener_perfil_ahorro(engine, username):
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT perfil_ahorro, perfil_riesgo FROM perfiles_ahorro WHERE usuario = :u"),
            {"u": username}
        ).mappings().first()
    return result["perfil_ahorro"] if result else None

perfil_usuario = obtener_perfil_ahorro(engine, username)

# ─── Cargar contenido desde Excel y limpiar ──────────────────────────
df = pd.read_excel("BD CONTENIDO.xlsx")
df["PERFIL"] = df["PERFIL"].fillna("").str.strip().str.lower()
df["TIPO"] = df["TIPO"].str.strip().str.upper()
df["TAG"] = df["TAG"].str.strip().str.title()
df.drop_duplicates(subset="LINK", inplace=True)

perfil_usuario = perfil_usuario.lower().strip() if perfil_usuario else ""

# ─── Separar contenido relevante y adicional sin intersección ───────
df_relevante = df[df["PERFIL"] == perfil_usuario].copy()
df_otros = df[~df.index.isin(df_relevante.index)].copy()
# ─── Barra de búsqueda ─────────────────────────────────────
query = st.text_input("🔎Buscar: ahorro, podcast, inversión", "").strip().lower()

# Combinar todos los campos relevantes como texto
def coincide_busqueda(row, texto):
    texto_total = f"{row.get('TITULO','')} {row.get('TIPO','')} {row.get('TAG','')} {row.get('PERFIL','')} {row.get('LINK','')}"
    return texto.lower() in texto_total.lower()

# Filtrar DataFrame si hay búsqueda activa
if query:
    df_relevante = df_relevante[df_relevante.apply(lambda row: coincide_busqueda(row, query), axis=1)]
    df_otros = df_otros[df_otros.apply(lambda row: coincide_busqueda(row, query), axis=1)]

st.markdown(f"### {name}, aprende sobre tu dinero")
st.markdown(f"Todo lo que necesitas saber sobre el manejo de tu dinero en un solo lugar")

# ─── Filtros por temática (TAG) ──────────────────────────────────────
# ─── Inicializar selección múltiple ─────────────────────────
if "tags_seleccionados" not in st.session_state:
    st.session_state.tags_seleccionados = set()

# ─── Mostrar chips horizontalmente con estilo ──────────────
st.markdown("### Temáticas disponibles:")

# Estilo visual
st.markdown("""
<style>
.scroll-container {
    display: flex;
    flex-wrap: nowrap;
    overflow-x: auto;
    padding: 10px;
    gap: 10px;
}
.scroll-container::-webkit-scrollbar {
    height: 6px;
}
.scroll-container::-webkit-scrollbar-thumb {
    background-color: #ccc;
    border-radius: 3px;
}
.tag-chip {
    display: inline-block;
    width: 140px; 
    text-align: center;
    padding: 10px;
    border: 2px solid #009473;
    border-radius: 20px;
    background-color: white;
    color: #009473;
    font-weight: 500;
    font-size: 14px;
    white-space: nowrap;
    cursor: pointer;
    flex-shrink: 0;
    transition: all 0.2s ease-in-out;
}
.tag-chip.active {
    background-color: #009473;
    color: white;
}
</style>
""", unsafe_allow_html=True)




# Botón para limpiar filtros
cols_reset = st.columns(1)
if cols_reset[0].button("Todo"):
    st.session_state.tags_seleccionados.clear()

# Mostrar botones por TAG en columnas múltiples
tags_unicos = sorted(df["TAG"].dropna().unique())
cols = st.columns(min(len(tags_unicos), 6))  # 6 por fila

for i, tag in enumerate(tags_unicos):
    col = cols[i % 6]
    with col:
        estado = tag in st.session_state.tags_seleccionados
        texto_boton = f"✅ {tag}" if estado else tag
        if st.button(texto_boton, key=f"tag_{tag}"):
            if estado:
                st.session_state.tags_seleccionados.remove(tag)
            else:
                st.session_state.tags_seleccionados.add(tag)
tags_activas = st.session_state.tags_seleccionados
if tags_activas:
    df_relevante = df_relevante[df_relevante["TAG"].isin(tags_activas)]
    df_otros = df_otros[df_otros["TAG"].isin(tags_activas)]

# ─── Renderizador universal de tarjetas con embebido ─────────────────


# Actualizar función para extraer ID y renderizar con fallback si falla
def extraer_id_youtube(url):
    if isinstance(url, str):
        match = re.search(r"(?:v=|be/)([\w\-]{11})", url)
        return match.group(1) if match else None
    return None

def render_tarjetas(df_seccion):
    cols = st.columns(3)
    for idx, row in df_seccion.iterrows():
        with cols[idx % 3]:
            url = row["LINK"]
            titulo = row.get("TITULO", "Contenido educativo")

            # Mostrar video de YouTube
            if "youtube.com" in url or "youtu.be" in url:
                video_id = extraer_id_youtube(url)
                if video_id:
                    embed_url = f"https://www.youtube.com/embed/{video_id}"
                    st.markdown(
                        f'<iframe width="100%" height="230" src="{embed_url}" frameborder="0" '
                        f'allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" '
                        f'allowfullscreen></iframe>', unsafe_allow_html=True
                    )
                else:
                    st.warning("⚠️ No se pudo mostrar el video.")
                    st.markdown(f"[Ver en YouTube 🔗]({url})", unsafe_allow_html=True)

            # Mostrar video de TikTok
            elif "tiktok.com" in url:
                try:
                    video_id = url.split("/")[-1]
                    embed_url = f"https://www.tiktok.com/embed/{video_id}"
                    st.components.v1.html(
                        f'<iframe src="{embed_url}" width="100%" height="500" frameborder="0" '
                        f'allow="autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" '
                        f'allowfullscreen></iframe>', height=550
                    )
                except:
                    st.warning("No se pudo cargar el video de TikTok.")
                    st.markdown(f"[Ver en TikTok 🔗]({url})", unsafe_allow_html=True)

            # Mostrar video MP4 directo
            elif url.endswith((".mp4", ".webm", ".mov")):
                st.video(url)

            # Mostrar recursos tipo guía o podcast
            else:
                st.markdown(
                    f"""
                    <div style="background-color:#f8f9fa; padding:15px; border-radius:10px;
                                border-left: 5px solid #009473; margin-bottom:20px;">
                        <a href="{url}" target="_blank" style="color:#009473;">🔗 Ver recurso</a>
                    </div>
                    """, unsafe_allow_html=True
                )

            # Mostrar título debajo del contenido
            st.markdown(f"<p style='margin-top:10px; font-weight:bold; text-align:center'>{titulo}</p>", unsafe_allow_html=True)



# ─── Mostrar contenido por tipo ──────────────────────────────────────
def mostrar_seccion(df_fuente, titulo_seccion, tipo):
    df_tipo = df_fuente[df_fuente["TIPO"] == tipo]
    if not df_tipo.empty:
        st.markdown(f"### {titulo_seccion}")
        render_tarjetas(df_tipo)

# ─── Sección recomendada para el perfil ──────────────────────────────
st.markdown("## 📌 Recomendado para ti")
for tipo, titulo in {
    "VIDEO": "Videos",
    "GUIA": "Guías",
    "TIKTOK": "TikToks",
    "PODCAST": "Podcasts"
}.items():
    mostrar_seccion(df_relevante, titulo, tipo)

# ─── Contenido adicional si existe ───────────────────────────────────
if not df_otros.empty:
    st.markdown("---")
    st.markdown("## 🎒 También podría interesarte")
    for tipo, titulo in {
        "VIDEO": "Videos adicionales",
        "GUIA": "Otras guías",
        "TIKTOK": "Más TikToks",
        "PODCAST": "Más podcasts"
    }.items():
        mostrar_seccion(df_otros, titulo, tipo)

