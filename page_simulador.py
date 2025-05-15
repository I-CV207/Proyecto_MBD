import streamlit as st
import pandas as pd
import numpy as np

st.title("Fintruth - Simulador")
st.header("Empieza a simular tu ahorro con nuestra herramienta gratuita")
st.divider()
st.markdown("")
st.markdown("Selecciona los parametros para simular tu ahorro")
st.divider()
st.markdown("")
st.markdown("")


col1, col2=st.columns(2)
with col1:
    x=st.slider("Escoge un valor con el que piensas empezar tu ahorro",1,1000000)
with col2:
    st.write("El capital con el que empezaras es: $",x)

chart_data=pd.DataFrame(np.random.rand(20,3),columns=["a","b","c"])
st.area_chart(chart_data)