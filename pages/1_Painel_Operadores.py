import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# =========================
# CONFIGURAÇÃO DO GOOGLE SHEETS
# =========================
SHEET_ID = "19V9iX_wKsRulGeDZYgbzqEhK3bpOEgS5-t_fk2kRjdA"
SHEET_NAME = "Sheet1"

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["google_service_account"], scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
dados = sheet.get_all_records()
df = pd.DataFrame(dados)

# =========================
# LAYOUT
# =========================
st.title("🧑‍💻 Painel de Operadores - AmorSaúde")

# Filtro de especialidade
especialidades = sorted(df['Especialidade'].dropna().unique())
especialidade = st.selectbox("🩺 Filtrar por Especialidade", ["Todas"] + especialidades)

if especialidade != "Todas":
    df = df[df['Especialidade'] == especialidade]

# Filtro de status
status_opcoes = ["Todos", "🟢 Reagendou", "🔴 Não quer reagendar", "🟡 Não atendeu (retornar contato)", "🟦 Mensagem enviada"]
status_filtro = st.selectbox("📋 Filtrar por Status", status_opcoes)

if status_filtro != "Todos":
    df = df[df['Status'] == status_filtro]

st.divider()

# =========================
# LISTAGEM DE PACIENTES
# =========================
st.subheader("📞 Lista de Pacientes")

for i in range(len(df)):
    cpf = df.iloc[i]['CPF']
    nome = df.iloc[i]['Nome']
    telefone = df.iloc[i]['Telefone']
    especialidade = df.iloc[i]['Especialidade']
    data = df.iloc[i]['Data']

    telefone_limpo = str(telefone).replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if telefone_limpo.startswith("55"):
        telefone_limpo = telefone_limpo[2:]

    msg = f"Olá, {nome}. Vimos que sua última consulta com o {especialidade} foi no dia {data}. É muito importante que você faça um check-up anual para garantir qualidade na sua saúde. Posso agendar uma consulta pra você nessa semana?"
    link_whatsapp = f"https://wa.me/55{telefone_limpo}?text={msg}"

    col1, col2 = st.columns([3, 1])
    with col1:
        st.write(f"👤 {nome} | 📞 {telefone} | 🩺 {especialidade} | 🪪 {cpf} | 📅 {data}")

    with col2:
        if st.button("💬 Enviar mensagem", key=f"btn_{i}"):
            # Atualiza status automaticamente
            df.at[i, 'Status'] = "🟦 Mensagem enviada"
            sheet.update_cell(i + 2, df.columns.get_loc("Status") + 1, "🟦 Mensagem enviada")
            st.markdown(f"[Abrir WhatsApp]({link_whatsapp})", unsafe_allow_html=True)

st.success("✅ Clique no botão para enviar mensagem e atualizar status automaticamente.")