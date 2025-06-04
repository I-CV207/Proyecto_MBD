import streamlit as st
from langchain.chat_models import ChatOpenAI
from langchain.agents import initialize_agent, Tool, AgentType
from langchain.tools import tool
from langchain.schema import HumanMessage


# Load API key
api_key = st.secrets["openrouter"]["api_key"]

# Use OpenAI-compatible LangChain wrapper for OpenRouter
llm = ChatOpenAI(
    openai_api_key=api_key,
    base_url="https://openrouter.ai/api/v1",
    model="mistralai/mistral-7b-instruct",  # or mistralai/mixtral-8x7b-instruct
)

st.title("🤖 BILLIE AI, tu amigo financiero")

user_prompt = st.text_input("Preguntale a BILLIE:")

if user_prompt:
    response = llm([HumanMessage(content=user_prompt)])
    st.write("### Respuesta")
    st.markdown(response.content)