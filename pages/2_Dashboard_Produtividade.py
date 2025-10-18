import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px

st.set_page_config(page_title="Produtividade dos Operadores", page_icon="📈", layout="wide")
st.title("📊 Relatório de Produtividade")

# Conexão com Google Sheets
SHEET_ID = "19V9iX_wKsRulGeDZYgbzqEhK3bpOEgS5-t_fk2kRjdA"
SHEET_NAME = "Sheet1"

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["google_service_account"], scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

# Carregar dados
@st.cache_data(ttl=60)
def carregar_dados():
    dados = pd.DataFrame(sheet.get_all_records())
    if 'Data' in dados.columns:
        dados['Data'] = pd.to_datetime(dados['Data'], errors='coerce')
    return dados

df = carregar_dados()

# KPIs
st.metric("🧾 Total de Pacientes", len(df))
st.metric("🔁 Reagendamentos", (df['Status'] == "🟢 Reagendou").sum())
st.metric("🔴 Não quiseram", (df['Status'] == "🔴 Não quer reagendar").sum())

# Gráfico de distribuição por status
if 'Status' in df.columns:
    contagem_status = df['Status'].value_counts().reset_index()
    contagem_status.columns = ['Status', 'Quantidade']
    fig = px.bar(contagem_status, x='Status', y='Quantidade', color='Status', text='Quantidade')
    st.plotly_chart(fig, use_container_width=True)