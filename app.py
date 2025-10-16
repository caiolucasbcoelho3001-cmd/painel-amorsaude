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
# CONEXÃO COM GOOGLE SHEETS (USANDO SECRETS)
# =========================
SHEET_ID = "19V9iX_wKsRulGeDZYgbzqEhK3bpOEgS5-t_fk2kRjdA"  # ID da sua planilha
SHEET_NAME = "Página1"  # Nome exato da aba no Google Sheets

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# ✅ Correção: não usar json.loads()
service_account_info = st.secrets["google_service_account"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

# =========================
# CARREGAR STATUS EXISTENTES
# =========================
status_records = sheet.get_all_records()
status_df = pd.DataFrame(status_records)
for col in ["CPF", "Data", "Médico", "Especialidade", "Status"]:
    if col not in status_df.columns:
        status_df[col] = ""

# =========================
# FUNÇÃO PARA SALVAR STATUS NO GOOGLE SHEETS
# =========================
def salvar_status_google(df_atualizado):
    df_atualizado = df_atualizado.fillna("")
    df_atualizado = df_atualizado.astype(str)
    df_atualizado.replace(["nan", "NaT", "None"], "", inplace=True)

    if "Data" in df_atualizado.columns:
        df_atualizado["Data"] = pd.to_datetime(
            df_atualizado["Data"], errors="coerce"
        ).dt.strftime("%Y-%m-%d")
        df_atualizado["Data"] = df_atualizado["Data"].fillna("")

    sheet.clear()
    sheet.append_row(["CPF", "Data", "Médico", "Especialidade", "Status"])
    for _, row in df_atualizado.iterrows():
        sheet.append_row([
            row["CPF"],
            row["Data"],
            row["Médico"],
            row["Especialidade"],
            row["Status"]
        ])

# =========================
# CARREGAR DADOS PRINCIPAIS
# =========================
@st.cache_data
def carregar_dados():
    df = pd.read_excel("Relatorio_Final.xlsx")
    df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
    return df.dropna(subset=['Data'])

df = carregar_dados()
df = df[df['CPF'].notna() & (df['CPF'] != '')]

# =========================
# FILTROS GERAIS
# =========================
col1, col2 = st.columns(2)
with col1:
    data_inicial = st.date_input("📅 Data inicial", value=df['Data'].min().date())
with col2:
    data_final = st.date_input("📅 Data final", value=df['Data'].max().date())

df_filtrado = df[(df['Data'] >= pd.to_datetime(data_inicial)) & (df['Data'] <= pd.to_datetime(data_final))]

especialidades_disponiveis = sorted(df['Especialidade'].dropna().unique())
especialidade_selecionada = st.multiselect(
    "🩺 Filtrar por Especialidade",
    options=especialidades_disponiveis,
    default=[]
)
if especialidade_selecionada:
    df_filtrado = df_filtrado[df_filtrado['Especialidade'].isin(especialidade_selecionada)]

st.caption(f"📊 Total de registros após filtros: {len(df_filtrado)}")

# =========================
# MENU DE PÁGINAS
# =========================
pagina = st.sidebar.radio(
    "📌 Selecione a página:",
    ["📊 Dashboard", "🧑‍💻 Operações"]
)

# =========================
# PÁGINA DASHBOARD
# =========================
if pagina == "📊 Dashboard":
    total_atendimentos = len(df_filtrado)
    total_pacientes = df_filtrado['CPF'].nunique()
    total_medicos = df_filtrado['Médico'].nunique()
    retornos = df_filtrado[df_filtrado.duplicated(subset='CPF', keep=False)]['CPF'].nunique()

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("👤 Pacientes únicos", total_pacientes)
    kpi2.metric("🩺 Total de atendimentos", total_atendimentos)
    kpi3.metric("👨‍⚕️ Médicos ativos", total_medicos)
    kpi4.metric("🔁 Pacientes com retorno", retornos)

    st.subheader("📈 Médicos com mais atendimentos por especialidade")
    if not df_filtrado.empty:
        medicos_mais = df_filtrado.groupby(['Médico', 'Especialidade']).size().reset_index(name='Atendimentos')
        grafico1 = px.bar(
            medicos_mais.sort_values('Atendimentos', ascending=False).head(10),
            x='Médico', y='Atendimentos', color='Especialidade', text='Atendimentos'
        )
        grafico1.update_layout(xaxis_title="Médico", yaxis_title="Atendimentos")
        st.plotly_chart(grafico1, use_container_width=True)

        st.subheader("📊 Médicos com mais retornos")
        pacientes_retorno = df_filtrado[df_filtrado.duplicated(subset='CPF', keep=False)]
        medicos_retorno = pacientes_retorno['Médico'].value_counts().reset_index()
        medicos_retorno.columns = ['Médico', 'Retornos']
        grafico2 = px.bar(
            medicos_retorno.head(10), x='Médico', y='Retornos', text='Retornos', color='Médico'
        )
        grafico2.update_layout(xaxis_title="", yaxis_title="Retornos")
        st.plotly_chart(grafico2, use_container_width=True)
    else:
        st.warning("⚠️ Nenhum registro encontrado com os filtros selecionados.")

    st.subheader("📋 Tabela de atendimentos filtrados")
    st.dataframe(df_filtrado)

    st.download_button(
        label="📥 Baixar dados filtrados",
        data=df_filtrado.to_csv(index=False).encode('utf-8'),
        file_name='relatorio_filtrado.csv',
        mime='text/csv'
    )

# =========================
# PÁGINA OPERAÇÕES
# =========================
elif pagina == "🧑‍💻 Operações":
    st.subheader("🧑‍💻 Painel de Interações com Pacientes")

    if 'Status' not in df_filtrado.columns:
        df_filtrado['Status'] = ""

    # Mesclar status já existentes
    status_df['CPF'] = status_df['CPF'].astype(str)
    df_filtrado['CPF'] = df_filtrado['CPF'].astype(str)
    df_filtrado['Data'] = df_filtrado['Data'].dt.strftime('%Y-%m-%d')
    df_filtrado = df_filtrado.merge(
        status_df[['CPF', 'Data', 'Status']],
        on=['CPF', 'Data'],
        how='left',
        suffixes=('', '_salvo')
    )
    df_filtrado['Status'] = df_filtrado['Status_salvo'].fillna(df_filtrado['Status'])
    df_filtrado.drop(columns=['Status_salvo'], inplace=True)

    status_opcoes = [
        "🚫 Sem status",
        "🔴 Não quer reagendar",
        "🟢 Reagendou",
        "🟡 Não atendeu (retornar contato)",
        "🔵 Mudou de médico"
    ]
    status_filtrado = st.multiselect(
        "📌 Filtrar por Status",
        options=status_opcoes,
        default=["🚫 Sem status"]
    )

    df_operacoes = df_filtrado.copy()
    if "🚫 Sem status" in status_filtrado:
        sem_status = df_operacoes[df_operacoes['Status'].isna() | (df_operacoes['Status'] == "")]
    else:
        sem_status = pd.DataFrame()
    outros_status = df_operacoes[df_operacoes['Status'].isin([s for s in status_filtrado if s != "🚫 Sem status"])]
    df_operacoes = pd.concat([sem_status, outros_status])

    # Paginação
    registros_por_pagina = 50
    total_registros = len(df_operacoes)
    total_paginas = max(1, (total_registros + registros_por_pagina - 1) // registros_por_pagina)

    if "pagina_atual" not in st.session_state:
        st.session_state.pagina_atual = 1

    col_pag1, col_pag2, col_pag3 = st.columns([1, 2, 1])
    with col_pag1:
        if st.button("◀ Anterior", disabled=(st.session_state.pagina_atual == 1)):
            st.session_state.pagina_atual -= 1
    with col_pag2:
        st.markdown(
            f"<div style='text-align:center;'>📄 Página {st.session_state.pagina_atual} de {total_paginas}</div>",
            unsafe_allow_html=True
        )
    with col_pag3:
        if st.button("Próxima ▶", disabled=(st.session_state.pagina_atual == total_paginas)):
            st.session_state.pagina_atual += 1

    pagina_atual = st.session_state.pagina_atual
    inicio = (pagina_atual - 1) * registros_por_pagina
    fim = inicio + registros_por_pagina
    df_pagina = df_operacoes.iloc[inicio:fim]

    st.caption(f"📊 Exibindo registros {inicio + 1} a {min(fim, total_registros)} de {total_registros}")

    for i in range(len(df_pagina)):
        col1, col2 = st.columns([3, 2])
        with col1:
            st.write(
                f"👤 CPF: {df_pagina.iloc[i]['CPF']} | 🩺 Médico: {df_pagina.iloc[i]['Médico']} "
                f"| 📆 {df_pagina.iloc[i]['Data']} | 💉 {df_pagina.iloc[i]['Especialidade']}"
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
                key=f"status_{inicio + i}",
                horizontal=True,
                index=(
                    0 if pd.isna(df_pagina.iloc[i]['Status']) else
                    ["", "🔴 Não quer reagendar", "🟢 Reagendou", "🟡 Não atendeu (retornar contato)", "🔵 Mudou de médico"].index(df_pagina.iloc[i]['Status'])
                    if df_pagina.iloc[i]['Status'] in ["", "🔴 Não quer reagendar", "🟢 Reagendou", "🟡 Não atendeu (retornar contato)", "🔵 Mudou de médico"]
                    else 0
                )
            )
            df_operacoes.at[df_pagina.index[i], 'Status'] = status

    # Salvar no Google Sheets
    status_salvar = df_operacoes[['CPF', 'Data', 'Médico', 'Especialidade', 'Status']].copy()
    salvar_status_google(status_salvar)

    st.download_button(
        label="📥 Baixar relatório com status",
        data=status_salvar.to_csv(index=False).encode('utf-8'),
        file_name='relatorio_com_status.csv',
        mime='text/csv'
    )
