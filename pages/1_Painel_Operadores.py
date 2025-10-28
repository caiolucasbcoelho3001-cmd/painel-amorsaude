import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# =========================
# CONFIGURAÇÕES INICIAIS
# =========================
st.set_page_config(page_title="Painel de Operadores", page_icon="🧑‍💻", layout="wide")
st.title("🧑‍💻 Painel de Operadores - AmorSaúde")

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
# FILTROS
# =========================
col1, col2, col3 = st.columns(3)
with col1:
    data_inicial = st.date_input("📅 Data inicial", value=df['Data'].min().date())
with col2:
    data_final = st.date_input("📅 Data final", value=df['Data'].max().date())
with col3:
    especialidades_disponiveis = sorted(df['Especialidade'].dropna().unique())
    especialidade_selecionada = st.multiselect("🩺 Filtrar por especialidade", especialidades_disponiveis, default=[])

# Aplicar filtros
df = df[(df['Data'] >= pd.to_datetime(data_inicial)) & (df['Data'] <= pd.to_datetime(data_final))]
if especialidade_selecionada:
    df = df[df['Especialidade'].isin(especialidade_selecionada)]

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

status_alterados = {}

for i in range(len(df)):
    cpf = df.iloc[i]['CPF']
    nome = df.iloc[i].get('Nome', 'Sem nome')
    telefone = df.iloc[i].get('Telefone', '')
    especialidade = df.iloc[i]['Especialidade']
    data_consulta = df.iloc[i]['Data'].date()

    telefone_limpo = str(telefone).replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    link_whatsapp = f"https://wa.me/55{telefone_limpo}" if telefone_limpo else ""

    col1, col2 = st.columns([5, 3])
    with col1:
        st.write(f"👤 {nome} | 📞 {telefone} | 🪪 CPF: {cpf} | 🩺 {especialidade} | 📅 {data_consulta}")
        if telefone_limpo:
            col1.markdown(f"[💬 Abrir no WhatsApp]({link_whatsapp})", unsafe_allow_html=True)
    with col2:
        status_atual = df.iloc[i]['Status']
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
# SALVAR STATUS
# =========================
if st.button("💾 Salvar alterações"):
    if status_alterados:
        all_data = sheet.get_all_records()
        df_all = pd.DataFrame(all_data)

        for cpf, novo_status in status_alterados.items():
            mask = df_all['CPF'] == cpf
            idx = df_all.index[mask]
            if len(idx) > 0:
                df_all.loc[idx[-1], 'Status'] = novo_status

        sheet.clear()
        sheet.update([df_all.columns.values.tolist()] + df_all.values.tolist())
        st.success("✅ Status atualizados com sucesso!")
    else:
        st.info("⚠️ Nenhum status foi alterado.")