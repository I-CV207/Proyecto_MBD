import streamlit as st
import pandas as pd
import numpy as np
import streamlit.components.v1 as components



st.title("Fintruth - Recursos")

st.title("🎯 Reels Financieros por Temática")
st.markdown("Selecciona una temática para ver Reels educativos relacionados:")

# Diccionario de temas y sus respectivos enlaces a YouTube Shorts
temas_videos = {
    "Ahorro personal": [
        "https://www.youtube.com/shorts/nT10LW9y83w",
        "https://www.youtube.com/shorts/KrUIyZ4fkjU",
        "https://www.youtube.com/shorts/mgZGW5BcFtw"
    ],
    "Inversión para principiantes": [
        "https://www.youtube.com/shorts/q5jPRIWQNZU",
        "https://www.youtube.com/shorts/Wl1N2Ax5ntA",
    ],
    "Criptomonedas": [
        "https://www.youtube.com/shorts/EvdU3S0eTYw",
        "https://www.youtube.com/shorts/VQF0e6cgYcA",
    ],
    "Educación financiera": [
        "https://www.youtube.com/shorts/gF5Nx4t2uPk",
        "https://www.youtube.com/shorts/pqrnA6KDmKM",
    ],
}

# Selector de temática
tema_elegido = st.selectbox("🧠 Temática", list(temas_videos.keys()))

# Convertir enlaces de Shorts a formato embed compatible
def shorts_to_embed(url):
    video_id = url.split("/")[-1]
    return f"https://www.youtube.com/embed/{video_id}"

# Crear contenedor horizontal con scroll
st.markdown(f"### Resultados para: **{tema_elegido}**")

video_html = '<div style="display:flex; overflow-x:auto; gap:20px;">'
for url in temas_videos[tema_elegido]:
    embed_url = shorts_to_embed(url)
    video_html += f'''
        <iframe width="300" height="530"
        src="{embed_url}"
        frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
        allowfullscreen></iframe>
    '''
video_html += '</div>'

# Renderizar HTML
components.html(video_html, height=550, scrolling=True)
