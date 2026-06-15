import streamlit as st
from langchain_groq import ChatGroq

def get_llm(temperature=0.2, streaming=True):
    return ChatGroq(model="llama-3.3-70b-versatile", temperature=temperature, groq_api_key=st.secrets["GROQ_API_KEY"], streaming=streaming, max_retries=3)
