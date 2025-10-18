import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Painel AmorSaúde", page_icon="❤️", layout="wide")

menu = st.navigation([
    st.Page("🏠 Dashboard", "app.py"),
    st.Page("👩‍💻 Painel de Operadores", "pages/1_Painel_Operadores.py"),
    st.Page("📈 Produtividade", "pages/2_Dashboard_Produtividade.py")
])

col_menu1, col_menu2 = st.columns([6, 1])
with col_menu2:
    if st.button("🚪 Sair"):
        st.session_state.clear()
        st.rerun()

def login():
    st.sidebar.header("🔐 Área restrita")
    usuario = st.sidebar.text_input("Usuário")
    senha = st.sidebar.text_input("Senha", type="password")

    gestor_user = st.secrets["auth"]["gestor_user"]
    gestor_pass = st.secrets["auth"]["gestor_pass"]
    operador_user = st.secrets["auth"]["operador_user"]
    operador_pass = st.secrets["auth"]["operador_pass"]

    if usuario == gestor_user and senha == gestor_pass:
        st.session_state["autenticado"] = True
        st.session_state["perfil"] = "gestor"
        st.session_state["usuario"] = usuario
        st.rerun()
    elif usuario == operador_user and senha == operador_pass:
        st.session_state["autenticado"] = True
        st.session_state["perfil"] = "operador"
        st.session_state["usuario"] = usuario
        st.rerun()
    else:
        if usuario or senha:
            st.sidebar.error("❌ Usuário ou senha inválidos")

if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
    st.session_state["perfil"] = None

if not st.session_state["autenticado"]:
    login()
    st.stop()

if st.session_state["perfil"] == "operador":
    st.warning("⚠️ Você está logado como OPERADOR e não tem acesso ao Dashboard.")
    st.info("➡️ Acesse o Painel de Operadores ou Produtividade pelo menu acima.")
    st.stop()

refresh_interval = st.sidebar.slider("⏳ Atualizar automaticamente (segundos)", 10, 120, 30)
st_autorefresh(interval=refresh_interval * 1000, key="auto-refresh")

SHEET_ID = "19V9iX_wKsRulGeDZYgbzqEhK3bpOEgS5-t_fk2kRjdA"
SHEET_NAME = "Página1"

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
service_account_info = st.secrets["google_service_account"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

dados = sheet.get_all_records()
df = pd.DataFrame(dados)

if 'Data' in df.columns:
    df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
df = df.dropna(subset=['Data'])
df = df[df['CPF'].notna() & (df['CPF'] != '')]

st.title("🏠 Dashboard AmorSaúde")
col1, col2 = st.columns(2)
with col1:
    data_inicial = st.date_input("📅 Data inicial", value=df['Data'].min().date())
with col2:
    data_final = st.date_input("📅 Data final", value=df['Data'].max().date())

df_filtrado = df[(df['Data'] >= pd.to_datetime(data_inicial)) & (df['Data'] <= pd.to_datetime(data_final))]

if 'Especialidade' in df.columns:
    especialidades_disponiveis = sorted(df['Especialidade'].dropna().unique())
    especialidade_sel = st.multiselect("🩺 Filtrar por Especialidade", options=especialidades_disponiveis)
    if especialidade_sel:
        df_filtrado = df_filtrado[df_filtrado['Especialidade'].isin(especialidade_sel)]

total_atendimentos = len(df_filtrado)
total_pacientes = df_filtrado['CPF'].nunique()
total_medicos = df_filtrado['Médico'].nunique()
retornos = df_filtrado[df_filtrado.duplicated(subset='CPF', keep=False)]['CPF'].nunique()

k1, k2, k3, k4 = st.columns(4)
k1.metric("👤 Pacientes únicos", total_pacientes)
k2.metric("🩺 Total de atendimentos", total_atendimentos)
k3.metric("👨‍⚕️ Médicos ativos", total_medicos)
k4.metric("🔁 Pacientes com retorno", retornos)

st.subheader("📈 Médicos com mais atendimentos")
medicos_mais = df_filtrado['Médico'].value_counts().reset_index()
medicos_mais.columns = ['Médico', 'Atendimentos']
grafico1 = px.bar(medicos_mais.head(10), x='Médico', y='Atendimentos', text='Atendimentos', color='Médico')
grafico1.update_layout(xaxis_title="", yaxis_title="Atendimentos")
st.plotly_chart(grafico1, use_container_width=True)

st.subheader("📊 Médicos com mais retornos")
pacientes_retorno = df_filtrado[df_filtrado.duplicated(subset='CPF', keep=False)]
medicos_retorno = pacientes_retorno['Médico'].value_counts().reset_index()
medicos_retorno.columns = ['Médico', 'Retornos']
grafico2 = px.bar(medicos_retorno.head(10), x='Médico', y='Retornos', text='Retornos', color='Médico')
grafico2.update_layout(xaxis_title="", yaxis_title="Retornos")
st.plotly_chart(grafico2, use_container_width=True)

st.subheader("📋 Tabela de atendimentos filtrados")
st.dataframe(df_filtrado)

st.download_button(
    label="📥 Baixar dados filtrados",
    data=df_filtrado.to_csv(index=False).encode('utf-8'),
    file_name='relatorio_filtrado.csv',
    mime='text/csv'
)
