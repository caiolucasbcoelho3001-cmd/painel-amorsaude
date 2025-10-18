import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="Painel dos Operadores", page_icon="🧑‍💻", layout="wide")
st.title("🧑‍💻 Painel de Interação com Pacientes")

# Conexão com Google Sheets
SHEET_ID = "19V9iX_wKsRulGeDZYgbzqEhK3bpOEgS5-t_fk2kRjdA"
SHEET_NAME = "Sheet1"

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["google_service_account"], scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

# Carrega dados
@st.cache_data(ttl=60)
def carregar_dados():
    dados = pd.DataFrame(sheet.get_all_records())
    if 'Data' in dados.columns:
        dados['Data'] = pd.to_datetime(dados['Data'], errors='coerce')
    return dados

df = carregar_dados()

# Filtra pacientes sem CPF
if 'CPF' in df.columns:
    df = df[df['CPF'].notna() & (df['CPF'] != "")]

# Filtros
col1, col2 = st.columns(2)
with col1:
    especialidades = sorted(df['Especialidade'].dropna().unique()) if 'Especialidade' in df.columns else []
    filtro_especialidade = st.selectbox("🩺 Especialidade", ["Todas"] + especialidades)
with col2:
    status_filtros = ["Todos", "🔴 Não quer reagendar", "🟢 Reagendou", "🟡 Não atendeu", "🔵 Mudou de médico"]
    filtro_status = st.selectbox("📊 Status atual", status_filtros)

# Aplica filtros
if filtro_especialidade != "Todas":
    df = df[df['Especialidade'] == filtro_especialidade]
if filtro_status != "Todos" and 'Status' in df.columns:
    df = df[df['Status'] == filtro_status]

# Adiciona coluna de Status se não existir
if 'Status' not in df.columns:
    df['Status'] = ""

st.write("### Pacientes para contato:")
for i in range(len(df)):
    col1, col2 = st.columns([3, 2])
    with col1:
        st.write(f"👤 CPF: {df.iloc[i]['CPF']} | 🩺 {df.iloc[i]['Médico']} | 💉 {df.iloc[i]['Especialidade']} | 📅 {df.iloc[i]['Data'].date()}")
    with col2:
        novo_status = st.radio(
            "Status:",
            options=["", "🔴 Não quer reagendar", "🟢 Reagendou", "🟡 Não atendeu", "🔵 Mudou de médico"],
            key=f"status_{i}",
            horizontal=True
        )
        if novo_status:
            df.at[df.index[i], 'Status'] = novo_status
            sheet.update_cell(i + 2, df.columns.get_loc('Status') + 1, novo_status)  # atualiza célula diretamente no Sheets

st.success("✅ Atualizações salvas automaticamente no Google Sheets!")