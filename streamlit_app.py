import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Custom Styled App", layout="wide")

# Inject custom CSS
st.markdown("""
    <style>
    /* Fondo general de la app */
    .stApp {
        background-color: #ffffff;
    }

    /* Sidebar general */
    section[data-testid="stSidebar"] {
        background-color: #E4E2E2;
    }

    /* Texto general del sidebar */
    section[data-testid="stSidebar"] * {
        color: #000000 !important;
        font-size: 20px !important;
        font-family: 'Montserrat', sans-serif !important;
    }

    /* Selector de página activo */
    section[data-testid="stSidebar"] div[aria-current="page"],
    section[data-testid="stSidebar"] a[aria-current="page"] {
        background-color: #009473 !important;  /* Verde activo */
        color: white !important;
        border-radius: 10px;
        font-weight: bold;
        padding: 8px 16px;
        margin-bottom: 4px;
        transition: background-color 0.3s ease;
    }

    /* Efecto hover en todos los enlaces */
    section[data-testid="stSidebar"] a:hover {
        background-color: #009473 !important;  /* Verde oscuro */
        color: white !important;
    }

    </style>
""", unsafe_allow_html=True)

# Definición de páginas
pages = {
    "Bill.ai": [
        st.Page("page_dashboard_aut.py", title="Tu dinero"),
        st.Page("page_perfil_ahorro_v2.py", title="Evoluciona"),
        st.Page("page_aprende.py", title="Aprende"),
        #st.Page("page_simulador.py", title="Simula tu ahorro"),
        #st.Page("page_yahoo_finance.py", title="Consulta de Acciones"),
        #st.Page("page_billi.py", title="Pregúntale a BILLI"),
        #st.Page("page_about.py", title="Conoce el proyecto"),
        #st.Page("test.py", title="Test"),
    ],
}

# Activar navegación
pg = st.navigation(pages)
pg.run()
