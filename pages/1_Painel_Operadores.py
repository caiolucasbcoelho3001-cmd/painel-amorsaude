import streamlit as st
import pandas as pd
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

# BLOQUEIA ACESSO DE QUEM NÃO FOR OPERADOR OU GESTOR
if st.session_state.nivel not in ["gestor", "operador"]:
    st.error("⛔ Você não tem permissão para acessar esta página.")
    st.stop()

# ======================
# CONFIGURAÇÕES
# ======================
st.set_page_config(page_title="Painel Operadores", page_icon="🧑‍💻", layout="wide")
st.title("🧑‍💻 Painel de Interação com Pacientes")

# ======================
# CONEXÃO GOOGLE SHEETS
# ======================
SHEET_ID = "19V9iX_wKsRulGeDZYgbzqEhK3bpOEgS5-t_fk2kRjdA"
SHEET_NAME = "Planilha1"  # altere conforme o nome real da aba

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["google_service_account"], scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

# ======================
# CARREGAR DADOS
# ======================
@st.cache_data(ttl=60)
def carregar_dados():
    dados = pd.DataFrame(sheet.get_all_records())
    if 'Data' in dados.columns:
        dados['Data'] = pd.to_datetime(dados['Data'], errors='coerce')
    if 'CPF' in dados.columns:
        dados = dados[dados['CPF'].notna() & (dados['CPF'] != "")]
    return dados

df = carregar_dados()

# ======================
# FILTROS
# ======================
col1, col2 = st.columns(2)
with col1:
    especialidades = sorted(df['Especialidade'].dropna().unique()) if 'Especialidade' in df.columns else []
    filtro_especialidade = st.selectbox("🩺 Especialidade", ["Todas"] + especialidades)

with col2:
    status_opcoes = ["Todos", "🔴 Não quer reagendar", "🟢 Reagendou", "🟡 Não atendeu", "🔵 Mudou de médico"]
    filtro_status = st.selectbox("📊 Status atual", status_opcoes)

# Aplica filtros
if filtro_especialidade != "Todas":
    df = df[df['Especialidade'] == filtro_especialidade]
if filtro_status != "Todos" and 'Status' in df.columns:
    df = df[df['Status'] == filtro_status]

# Adiciona coluna de status se não existir
if 'Status' not in df.columns:
    df['Status'] = ""

# ======================
# INTERAÇÃO LINHA A LINHA
# ======================
st.write("### 📞 Lista de pacientes:")

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
            # Atualiza no Google Sheets
            col_status = df.columns.get_loc('Status') + 1
            sheet.update_cell(i + 2, col_status, novo_status)

st.success("✅ Alterações de status salvas automaticamente no Google Sheets!")
