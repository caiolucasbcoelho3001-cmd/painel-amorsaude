import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# =========================
# CONFIGURAÇÕES INICIAIS
# =========================
st.set_page_config(page_title="Painel AmorSaúde", page_icon="❤️", layout="wide")
st.title("📊 Painel de Atendimento - AmorSaúde Indaiatuba")

# =========================
# AUTO REFRESH
# =========================
refresh_interval = st.sidebar.slider("⏳ Atualizar automaticamente (segundos)", 10, 120, 30)
st.sidebar.write(f"🔄 Atualização a cada {refresh_interval} segundos")
st_autorefresh = st.autorefresh(interval=refresh_interval * 1000, key="auto-refresh")

# =========================
# CONEXÃO GOOGLE SHEETS
# =========================
SHEET_ID = "19V9iX_wKsRulGeDZYgbzqEhK3bpOEgS5-t_fk2kRjdA"  # ✅ Seu ID
SHEET_NAME = "Página1"  # Ajuste se o nome da aba for diferente

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
service_account_info = st.secrets["google_service_account"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

# =========================
# CARREGAR DADOS
# =========================
dados = sheet.get_all_records()
df = pd.DataFrame(dados)

# Garante que a coluna 'Status' exista
if 'Status' not in df.columns:
    df['Status'] = ""

df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
df = df.dropna(subset=['Data'])

# =========================
# FILTRO DE PERÍODO
# =========================
col1, col2 = st.columns(2)
with col1:
    data_inicial = st.date_input("📅 Data inicial", value=df['Data'].min().date())
with col2:
    data_final = st.date_input("📅 Data final", value=df['Data'].max().date())

df_filtrado = df[(df['Data'] >= pd.to_datetime(data_inicial)) & (df['Data'] <= pd.to_datetime(data_final))]

# =========================
# FILTRO POR ESPECIALIDADE
# =========================
if 'Especialidade' in df.columns:
    especialidades_disponiveis = sorted(df['Especialidade'].dropna().unique())
    especialidade_selecionada = st.multiselect("🩺 Filtrar por Especialidade", options=especialidades_disponiveis)
    if especialidade_selecionada:
        df_filtrado = df_filtrado[df_filtrado['Especialidade'].isin(especialidade_selecionada)]

# =========================
# INDICADORES GERAIS
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
# PAINEL DE OPERADORES - FILTRO DE STATUS
# =========================
st.header("🧑‍💻 Painel de Operadores")

status_opcoes = [
    "",
    "🔴 Não quer reagendar",
    "🟢 Reagendou",
    "🟡 Não atendeu (retornar contato)",
    "🔵 Mudou de médico"
]

status_filtro = st.selectbox("📌 Filtrar pacientes por status", options=["Todos"] + status_opcoes, index=0)
if status_filtro != "Todos":
    df_filtrado = df_filtrado[df_filtrado['Status'] == status_filtro]

# =========================
# PAGINAÇÃO
# =========================
linhas_por_pagina = 50
total_linhas = len(df_filtrado)
total_paginas = (total_linhas // linhas_por_pagina) + (1 if total_linhas % linhas_por_pagina != 0 else 0)

pagina_atual = st.number_input(
    "Página:",
    min_value=1,
    max_value=max(total_paginas, 1),
    step=1,
    value=1
)

inicio = (pagina_atual - 1) * linhas_por_pagina
fim = inicio + linhas_por_pagina
df_paginado = df_filtrado.iloc[inicio:fim]

# =========================
# EXIBIR E ATUALIZAR STATUS
# =========================
for i in range(len(df_paginado)):
    col1, col2 = st.columns([3, 2])
    with col1:
        st.write(
            f"👤 CPF: {df_paginado.iloc[i]['CPF']} | 🩺 Médico: {df_paginado.iloc[i]['Médico']} "
            f"| 📆 {df_paginado.iloc[i]['Data'].date()} | 💉 {df_paginado.iloc[i]['Especialidade']}"
        )
    with col2:
        status = st.radio(
            "Status:",
            options=status_opcoes,
            key=f"status_{inicio+i}",
            horizontal=True,
            index=status_opcoes.index(df_paginado.iloc[i]['Status']) if df_paginado.iloc[i]['Status'] in status_opcoes else 0
        )
        df_paginado.at[df_paginado.index[i], 'Status'] = status

# =========================
# SALVAR NO GOOGLE SHEETS
# =========================
if st.button("💾 Salvar alterações na planilha"):
    sheet.clear()
    sheet.update([df.columns.values.tolist()] + df.values.tolist())
    st.success("✅ Alterações salvas com sucesso no Google Sheets!")

# =========================
# DOWNLOAD
# =========================
st.download_button(
    label="📥 Baixar relatório filtrado",
    data=df_filtrado.to_csv(index=False).encode('utf-8'),
    file_name='relatorio_com_status.csv',
    mime='text/csv'
)