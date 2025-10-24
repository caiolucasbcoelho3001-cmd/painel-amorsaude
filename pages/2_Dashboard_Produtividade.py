import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# =========================
# RESTRIÇÃO DE LOGIN
# =========================
if "usuario" not in st.session_state:
    st.warning("⚠️ Você precisa fazer login primeiro.")
    st.stop()

if st.session_state["perfil"] != "gestor":
    st.error("🚫 Acesso negado. Esta página é exclusiva para gestores.")
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
# FILTROS
# =========================
st.title("📊 Dashboard de Produtividade - AmorSaúde")

col1, col2 = st.columns(2)
with col1:
    data_inicial = st.date_input("📅 Data inicial", value=df['Data'].min().date() if not df.empty else None)
with col2:
    data_final = st.date_input("📅 Data final", value=df['Data'].max().date() if not df.empty else None)

df_filtrado = df[(df['Data'] >= pd.to_datetime(data_inicial)) & (df['Data'] <= pd.to_datetime(data_final))]

if 'Especialidade' in df.columns:
    especialidades = sorted(df['Especialidade'].dropna().unique())
    filtro_especialidade = st.multiselect("🩺 Filtrar por Especialidade", options=especialidades, default=[])
    if filtro_especialidade:
        df_filtrado = df_filtrado[df_filtrado['Especialidade'].isin(filtro_especialidade)]

# =========================
# KPIs
# =========================
total_atendimentos = len(df_filtrado)
total_pacientes = df_filtrado['CPF'].nunique()
total_medicos = df_filtrado['Médico'].nunique()
retornos = df_filtrado[df_filtrado.duplicated(subset='CPF', keep=False)]['CPF'].nunique()

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("👤 Pacientes únicos", total_pacientes)
kpi2.metric("🩺 Total de atendimentos", total_atendimentos)
kpi3.metric("👨‍⚕️ Médicos ativos", total_medicos)
kpi4.metric("🔁 Pacientes com retorno", retornos)

# =========================
# GRÁFICOS
# =========================
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

# =========================
# TABELA DETALHADA
# =========================
st.subheader("📋 Tabela de atendimentos filtrados")
st.dataframe(df_filtrado)

# =========================
# DOWNLOAD DOS DADOS
# =========================
st.download_button(
    label="📥 Baixar dados filtrados",
    data=df_filtrado.to_csv(index=False).encode('utf-8'),
    file_name='relatorio_produtividade.csv',
    mime='text/csv'
)