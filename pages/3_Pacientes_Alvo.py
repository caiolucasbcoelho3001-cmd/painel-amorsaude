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
# AGRUPAR POR CPF + ESPECIALIDADE (ÚLTIMA CONSULTA)
# =========================
historico = df.groupby(['CPF', 'Especialidade'])['Data'].max().reset_index()
historico.rename(columns={'Data': 'Ultima_Consulta'}, inplace=True)

# Se a coluna de status não existir ainda, cria uma vazia
if 'Status' not in historico.columns:
    historico['Status'] = ""

# =========================
# FILTROS
# =========================
col1, col2 = st.columns(2)
with col1:
    especialidades = sorted(historico['Especialidade'].dropna().unique())
    especialidade_sel = st.selectbox("🩺 Escolha a especialidade", especialidades)

with col2:
    meses = st.slider("⏳ Pacientes sem retorno há (meses):", 1, 36, 12)

limite_data = datetime.today() - timedelta(days=meses * 30)
filtro = (historico['Especialidade'] == especialidade_sel) & (historico['Ultima_Consulta'] < limite_data)
pacientes_alvo = historico[filtro].sort_values(by='Ultima_Consulta', ascending=True)

st.subheader(f"📋 Pacientes que não voltam à especialidade '{especialidade_sel}' há mais de {meses} meses")
st.write(f"Total de pacientes: {len(pacientes_alvo)}")

# =========================
# STATUS INTERATIVO
# =========================
st.subheader("📌 Status de contato")

status_opcoes = [
    "",
    "🔴 Não quer reagendar",
    "🟢 Reagendou",
    "🟡 Não atendeu (retornar contato)",
    "🔵 Mudou de médico"
]

# Criar um dicionário local para armazenar alterações
status_alterados = {}

for i in range(len(pacientes_alvo)):
    cpf = pacientes_alvo.iloc[i]['CPF']
    especialidade = pacientes_alvo.iloc[i]['Especialidade']
    ultima_data = pacientes_alvo.iloc[i]['Ultima_Consulta'].date()

    col1, col2 = st.columns([4, 3])
    with col1:
        st.write(f"👤 CPF: {cpf} | 🩺 {especialidade} | 📅 Última consulta: {ultima_data}")
    with col2:
        status_atual = pacientes_alvo.iloc[i]['Status']
        novo_status = st.radio(
            "Status:",
            options=status_opcoes,
            index=status_opcoes.index(status_atual) if status_atual in status_opcoes else 0,
            key=f"status_{i}",
            horizontal=True
        )
        if novo_status != status_atual:
            status_alterados[cpf] = novo_status

# =========================
# SALVAR ALTERAÇÕES NO GOOGLE SHEETS
# =========================
if st.button("💾 Salvar alterações"):
    if status_alterados:
        all_data = sheet.get_all_records()
        df_all = pd.DataFrame(all_data)

        for cpf, novo_status in status_alterados.items():
            mask = (df_all['CPF'] == cpf) & (df_all['Especialidade'] == especialidade_sel)
            idx = df_all.index[mask]
            if len(idx) > 0:
                df_all.loc[idx[-1], 'Status'] = novo_status  # atualiza a última ocorrência

        # sobrescreve toda a planilha (pode otimizar depois com update parcial)
        sheet.clear()
        sheet.update([df_all.columns.values.tolist()] + df_all.values.tolist())
        st.success("✅ Status atualizados com sucesso!")
    else:
        st.info("⚠️ Nenhum status foi alterado.")

# =========================
# DOWNLOAD
# =========================
st.download_button(
    label="📥 Baixar lista em CSV",
    data=pacientes_alvo.to_csv(index=False).encode('utf-8'),
    file_name=f"pacientes_{especialidade_sel}_{meses}meses.csv",
    mime="text/csv"
)