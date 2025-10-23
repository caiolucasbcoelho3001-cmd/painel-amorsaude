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

if st.session_state["perfil"] != "operador":
    st.error("🚫 Acesso negado. Esta página é exclusiva para operadores.")
    st.stop()

# =========================
# CONFIGURAÇÃO GOOGLE SHEETS
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
@st.cache_data(ttl=60)
def carregar_dados():
    dados = pd.DataFrame(sheet.get_all_records())
    if 'Data' in dados.columns:
        dados['Data'] = pd.to_datetime(dados['Data'], errors='coerce')
    dados = dados[dados['CPF'].notna() & (dados['CPF'] != "")]
    return dados

df = carregar_dados()

# =========================
# INTERFACE DO OPERADOR
# =========================
st.title("🧑‍💻 Painel de Operadores - AmorSaúde")

st.info("Use os botões abaixo para registrar o status de contato de cada paciente.")

if "Status" not in df.columns:
    df["Status"] = ""

# Exibição paginada — mostra 50 por página
itens_por_pagina = 50
total_paginas = (len(df) // itens_por_pagina) + 1
pagina = st.number_input("Página", min_value=1, max_value=total_paginas, step=1)

inicio = (pagina - 1) * itens_por_pagina
fim = inicio + itens_por_pagina
df_pagina = df.iloc[inicio:fim]

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
