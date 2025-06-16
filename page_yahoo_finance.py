import streamlit as st
import yfinance as yf
import matplotlib.pyplot as plt
import plotly.graph_objects as go

# Configuración de la página
#st.set_page_config(page_title="📈 Stock Info", layout="centered")

st.title("📊 Consulta de acciones - Yahoo Finance")

# Input del usuario
ticker_symbol = st.text_input("Escribe el símbolo del ticker (Ej: AAPL, MSFT, TSLA):", "VOO")

# Obtener datos de Yahoo Finance
try:
    stock = yf.Ticker(ticker_symbol)

    # Información general
    st.subheader("📌 Información general")
    info = stock.info
    st.markdown(f"**Nombre:** {info.get('longName', 'N/A')}")
    st.markdown(f"**Sector:** {info.get('sector', 'N/A')}")
    st.markdown(f"**Precio actual:** ${info.get('currentPrice', 'N/A')}")
    st.markdown(f"**Moneda:** {info.get('currency', 'N/A')}")
    st.markdown(f"**Sitio web:** [{info.get('website', 'N/A')}]({info.get('website', '#')})")

    # Gráfico de precios históricos
    
    ##############-*******************************************************
    st.subheader("📈 Precio histórico (últimos 6 meses)")

    hist = stock.history(period="6mo")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hist.index,
        y=hist["Close"],
        mode="lines",
        name="Precio de cierre",
        line=dict(width=2)
    ))

    fig.update_layout(
        title=f"Precio histórico de {ticker_symbol.upper()}",
        xaxis_title="Fecha",
        yaxis_title="Precio de cierre",
        xaxis=dict(rangeselector=dict(
            buttons=list([
                dict(count=1, label="1M", step="month", stepmode="backward"),
                dict(count=3, label="3M", step="month", stepmode="backward"),
                dict(count=6, label="6M", step="month", stepmode="backward"),
                dict(step="all")
            ])
        ),
            rangeslider=dict(visible=True),
            type="date"
        ),
        hovermode="x unified",
        template="plotly_white"
    )

    st.plotly_chart(fig, use_container_width=True)

    # Indicadores clave
    st.subheader("📊 Indicadores clave")
    st.write({
        "Market Cap": info.get("marketCap", "N/A"),
        "Forward PE": info.get("forwardPE", "N/A"),
        "Beta": info.get("beta", "N/A"),
        "Dividend Yield": info.get("dividendYield", "N/A"),
        "52 Week High": info.get("fiftyTwoWeekHigh", "N/A"),
        "52 Week Low": info.get("fiftyTwoWeekLow", "N/A"),
    })

except Exception as e:
    st.error(f"No se pudo obtener información para el ticker '{ticker_symbol}'. Verifica que sea correcto.")
    st.exception(e)
