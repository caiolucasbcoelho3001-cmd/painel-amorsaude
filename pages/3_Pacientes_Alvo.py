import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta

# =========================
# CONFIGURAÇÕES
# =========================
st.set_page_config(page_title="Pacientes Alvo", page_icon="🎯", layout="wide")
st.title("🎯 Pacientes Alvo - Filtros por Especialidade e Tempo")

# =========================
# CONEXÃO COM GOOGLE SHEETS
# =========================
SHEET_ID = "19V9iX_wKsRulGeDZYgbzqEhK3bpOEgS5-t_fk2kRjdA"
SHEET_NAME = "Sheet1"

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["google_service_account"], scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

# =========================
# CARREGAR DADOS
# =========================
dados = sheet.get_all_records()
df = pd.DataFrame(dados)

if 'Data' in df.columns:
    df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
df = df.dropna(subset=['CPF', 'Data'])

# =========================
# AGRUPAMENTO POR CPF + ESPECIALIDADE
# =========================
# Pegamos a última data de consulta de cada paciente para cada especialidade
historico = df.groupby(['CPF', 'Especialidade'])['Data'].max().reset_index()
historico.rename(columns={'Data': 'Ultima_Consulta'}, inplace=True)

# =========================
# FILTROS
# =========================
col1, col2 = st.columns(2)
with col1:
    especialidades = sorted(historico['Especialidade'].dropna().unique())
    especialidade_sel = st.selectbox("🩺 Escolha a especialidade", especialidades)

with col2:
    meses = st.slider("⏳ Pacientes sem retorno há (meses):", 1, 36, 12)

# Calcula o limite de data
limite_data = datetime.today() - timedelta(days=meses * 30)

# Aplica filtro
filtro = (historico['Especialidade'] == especialidade_sel) & (historico['Ultima_Consulta'] < limite_data)
pacientes_alvo = historico[filtro].sort_values(by='Ultima_Consulta', ascending=True)

# =========================
# RESULTADOS
# =========================
st.subheader(f"📋 Pacientes que não voltam à especialidade '{especialidade_sel}' há mais de {meses} meses")
st.write(f"Total de pacientes: {len(pacientes_alvo)}")
st.dataframe(pacientes_alvo)

# =========================
# DOWNLOAD
# =========================
st.download_button(
    label="📥 Baixar lista em CSV",
    data=pacientes_alvo.to_csv(index=False).encode('utf-8'),
    file_name=f"pacientes_{especialidade_sel}_{meses}meses.csv",
    mime="text/csv"
)