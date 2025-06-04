import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Custom Styled App", layout="wide")

# Inject custom CSS
st.markdown("""
    <style>
    /* Main app background */
    .stApp {
        background-color: #fafafa;
    }

    /* Sidebar background */
    section[data-testid="stSidebar"] {
        background-color: #0065a2;
    }
            
    /* Sidebar text styles */
    section[data-testid="stSidebar"] * {
        color: #fadfed !important;        /* white */
        font-size: 20px !important;       /* Font size */
        font-family: 'Arial', sans-serif !important;  /* Font family */
    }

    /* Optional: sidebar text */
    section[data-testid="stSidebar"] .css-1v0mbdj {
        color: black;
    }
    </style>
""", unsafe_allow_html=True)


pages = {
    "Dashboard": [
        st.Page("page_dashboard.py", title="📊 Dashboard"),
    ],
    "Recursos": [
        st.Page("page_aprende.py", title="📚 Aprende"),
        st.Page("page_simulador.py", title="Simula tu ahorro"),
        st.Page("page_yahoo_finance.py", title="Consulta de Acciones"),
    ],
     "BILLI": [
        st.Page("page_billi.py", title="Preguntale a BILLI"),
     ], 
     "About": [
        st.Page("page_about.py", title="Conoce el proyecto"),
    ],
}

pg = st.navigation(pages)
pg.run()





