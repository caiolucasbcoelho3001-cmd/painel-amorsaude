import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# =========================
# CONFIGURAÇÕES INICIAIS
# =========================
st.set_page_config(page_title="Painel AmorSaúde", page_icon="❤️", layout="wide")
st.title("📊 Painel de Atendimento - AmorSaúde Indaiatuba")

# =========================
# AUTO REFRESH
# =========================
refresh_interval = st.sidebar.slider("⏳ Atualizar automaticamente (segundos)", 10, 120, 30)
st.sidebar.write(f"🔄 Atualização a cada {refresh_interval} segundos")
st_autorefresh = st.experimental_rerun
st_autorefresh = st.autorefresh(interval=refresh_interval * 1000, key="auto-refresh")

# =========================
# CONEXÃO GOOGLE SHEETS
# =========================
SHEET_ID = "19V9iX_wKsRulGeDZYgbzqEhK3bpOEgS5-t_fk2kRjdA"
SHEET_NAME = "Página1"

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
service_account_info = st.secrets["google_service_account"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

# =========================
# CARREGAR DADOS
# =========================
dados = sheet.get_all_records()
df = pd.DataFrame(dados)

# Garante que a coluna 'Status' exista
if 'Status' not in df.columns:
    df['Status'] = ""

df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
df = df.dropna(subset=['Data'])

# =========================
# FILTRO DE PERÍODO
# =========================
col1, col2 = st.columns(2)
with col1:
    data_inicial = st.date_input("📅 Data inicial", value=df['Data'].min().date())
with col2:
    data_final = st.date_input("📅 Data final", value=df['Data'].max().date())

df_filtrado = df[(df['Data'] >= pd.to_datetime(data_inicial)) & (df['Data'] <= pd.to_datetime(data_final))]

# =========================
# FILTRO POR ESPECIALIDADE
# =========================
if 'Especialidade' in df.columns:
    especialidades_disponiveis = sorted(df['Especialidade']_