import streamlit as st
import pandas as pd
import numpy as np
import os
from PIL import Image
import base64
from io import BytesIO


st.set_page_config(page_title="Billie App", layout="wide")

# Inject custom CSS
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Poppins', sans-serif !important;
        background-color: white;
    }}

    /* Sidebar */
    section[data-testid="stSidebar"] {{
        background-color: #E4E2E2;
    }}
    section[data-testid="stSidebar"] * {{
        color: #000000 !important;
        font-size: 20px !important;
    }}
    section[data-testid="stSidebar"] div[aria-current="page"],
    section[data-testid="stSidebar"] a[aria-current="page"] {{
        background-color: #009473 !important;
        color: white !important;
        border-radius: 10px;
        font-weight: bold;
        padding: 8px 16px;
        margin-bottom: 4px;
    }}
    section[data-testid="stSidebar"] a:hover {{
        background-color: #009473 !important;
        color: white !important;
    }}

    </style>
""", unsafe_allow_html=True)

# -------------------- SIDEBAR Y NAVEGACIÓN --------------------
pages = {
    "Bill.IA": [
        st.Page("page_dashboard_aut.py", title="Tu dinero"),
        st.Page("page_perfil_ahorro_V2.py", title="Evoluciona"),
        st.Page("page_aprende.py", title="Aprende"),

    ],
}

# Activar navegación
pg = st.navigation(pages)
pg.run()
