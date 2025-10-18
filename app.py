import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ======================
# LOGIN COM DOIS NÍVEIS
# ======================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.nivel = None

if not st.session_state.autenticado:
    usuario = st.text_input("👤 Usuário")
    senha = st.text_input("🔐 Senha", type="password")

    if st.button("Entrar"):
        if usuario == st.secrets["auth"]["gestor_user"] and senha == st.secrets["auth"]["gestor_pass"]:
            st.session_state.autenticado = True
            st.session_state.nivel = "gestor"
            st.success("✅ Acesso liberado: Gestor")
        elif usuario == st.secrets["auth"]["operador_user"] and senha == st.secrets["auth"]["operador_pass"]:
            st.session_state.autenticado = True
            st.session_state.nivel = "operador"
            st.success("✅ Acesso liberado: Operador")
        else:
            st.error("❌ Usuário ou senha inválidos")
    st.stop()

# BLOQUEIA OPERADORES
if st.session_state.nivel != "gestor":
    st.error("⛔ Você não tem permissão para acessar esta página.")
    st.stop()

# ======================
# CONFIGURAÇÕES
# ======================
st.set_page_config(page_title="Dashboard - AmorSaúde", page_icon="❤️", layout="wide")
st.title("🏠 Painel de Atendimento - AmorSaúde Indaiatuba")

# ======================
# CONEXÃO GOOGLE SHEETS
# ======================
SHEET_ID = "19V9iX_wKsRulGeDZYgbzqEhK3bpOEgS5-t_fk2kRjdA"
SHEET_NAME = "Planilha1"  # altere conforme o nome real da aba

scope = ["https://