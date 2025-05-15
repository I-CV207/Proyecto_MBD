import streamlit as st
import pandas as pd
import numpy as np

pages = {
    "About": [
        st.Page("page_about.py", title="Conoce el proyecto"),
    ],
    "Recursos": [
        st.Page("page_articulos.py", title="Articulos"),
        st.Page("page_simulador.py", title="Simula tu ahorro"),
    ],
}

pg = st.navigation(pages)
pg.run()


