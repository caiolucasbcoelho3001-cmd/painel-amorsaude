import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# =========================
# RESTRIÇÃO DE LOGIN
# =========================
if "usuario" not in st.session_state:
    st.warning("⚠️ Você precisa fazer login primeiro.")
    st.stop()

# 👉 Gestores e operadores têm acesso
if st.session_state["perfil"] not in ["operador", "gestor"]:
    st.error("🚫 Acesso negado. Esta página é exclusiva para operadores e gestores.")
    st.stop()

# =========================
# CONFIGURAÇÃO GOOGLE SHEETS
# =========================
SHEET_ID = "19V9iX_wKsRulGeDZYgbzqEhK3bpOEgS5-t_fk2kRjdA"  # Seu ID da planilha
SHEET_NAME = "Sheet1"  # Nome da aba da planilha

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["google_service_account"], scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

# =========================
# CARREGAR DADOS
# =========================
@st.cache_data(ttl=60)
def carregar_dados():
    dados = pd.DataFrame(sheet.get_all_records())
    if 'Data' in dados.columns:
        dados['Data'] = pd.to_datetime(dados['Data'], errors='coerce')
    dados = dados[dados['CPF'].notna() & (dados['CPF'] != "")]
    if "Status" not in dados.columns:
        dados["Status"] = ""
    return dados

df = carregar_dados()

# =========================
# FILTROS
# =========================
st.title("🧑‍💻 Painel de Operadores - AmorSaúde")

# 📅 Filtro de datas
if not df.empty and 'Data' in df.columns:
    col1, col2 = st.columns(2)
    with col1:
        data_inicial = st.date_input("📅 Data inicial", value=df['Data'].min().date())
    with col2:
        data_final = st.date_input("📅 Data final", value=df['Data'].max().date())
    df = df[(df['Data'] >= pd.to_datetime(data_inicial)) & (df['Data'] <= pd.to_datetime(data_final))]

# 🩺 Filtro de especialidade
if "Especialidade" in df.columns:
    especialidades_disponiveis = sorted(df["Especialidade"].dropna().unique())
    especialidade_selecionada = st.multiselect("🩺 Filtrar por especialidade", especialidades_disponiveis)
    if especialidade_selecionada:
        df = df[df["Especialidade"].isin(especialidade_selecionada)]

# 📌 Filtro de status
status_opcoes = [
    "Todos",
    "🔴 Não quer reagendar",
    "🟢 Reagendou",
    "🟡 Não atendeu (retornar contato)",
    "🔵 Mudou de médico"
]
status_selecionado = st.selectbox("📌 Filtrar por status", status_opcoes)
if status_selecionado != "Todos":
    df = df[df["Status"] == status_selecionado]

# 📊 Contador por status
st.subheader("📊 Status geral")
contagem = df["Status"].value_counts()
for s in status_opcoes[1:]:
    st.write(f"{s}: {contagem.get(s, 0)}")

# =========================
# PAGINAÇÃO
# =========================
itens_por_pagina = 50
total_paginas = max((len(df) // itens_por_pagina) + (1 if len(df) % itens_por_pagina > 0 else 0), 1)
pagina = st.number_input("📄 Página", min_value=1, max_value=total_paginas, step=1)
inicio = (pagina - 1) * itens_por_pagina
fim = inicio + itens_por_pagina
df_pagina = df.iloc[inicio:fim]

# =========================
# INTERAÇÃO DE STATUS
# =========================
for i in range(len(df_pagina)):
    col1, col2 = st.columns([3, 2])
    with col1:
        st.write(
            f"👤 CPF: {df_pagina.iloc[i]['CPF']} | 🩺 Médico: {df_pagina.iloc[i]['Médico']} | 📅 {df_pagina.iloc[i]['Data'].date()} | 💉 {df_pagina.iloc[i].get('Especialidade','')}"
        )
    with col2:
        status = st.radio(
            "Status:",
            options=[
                "",
                "🔴 Não quer reagendar",
                "🟢 Reagendou",
                "🟡 Não atendeu (retornar contato)",
                "🔵 Mudou de médico"
            ],
            key=f"status_{i + inicio}",
            horizontal=True
        )
        df.at[df_pagina.index[i], 'Status'] = status

# =========================
# SALVAR STATUS NA PLANILHA
# =========================
if st.button("💾 Salvar alterações"):
    valores = df.values.tolist()
    sheet.update([df.columns.values.tolist()] + valores)
    st.success("✅ Status atualizado com sucesso!")