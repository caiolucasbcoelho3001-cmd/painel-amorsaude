import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from urllib.parse import quote
from datetime import datetime

# =========================
# CONFIG GERAL
# =========================
st.set_page_config(page_title="Painel de Operadores", page_icon="🧑‍💻", layout="wide")
st.title("🧑‍💻 Painel de Operadores - AmorSaúde")

# Controle de sessão (nome do usuário logado)
usuario_logado = st.session_state.get("usuario", "operador")

# =========================
# GOOGLE SHEETS
# =========================
SHEET_ID = "19V9iX_wKsRulGeDZYgbzqEhK3bpOEgS5-t_fk2kRjdA"
DATA_SHEET = "Sheet1"
LOG_SHEET = "LOG"

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["google_service_account"], scope)
client = gspread.authorize(creds)

sheet = client.open_by_key(SHEET_ID).worksheet(DATA_SHEET)
# get_all_records preserva a ordem das linhas de dados; índice 0 corresponde à linha 2 na planilha
records = sheet.get_all_records()
df_all = pd.DataFrame(records)

# Adiciona coluna "Row" com o número real da linha no Sheets (cabeçalho é linha 1)
df_all["Row"] = range(2, 2 + len(df_all))

# Tipagem e limpeza
if "Data" in df_all.columns:
    df_all["Data"] = pd.to_datetime(df_all["Data"], errors="coerce")
df_all = df_all.dropna(subset=["CPF", "Data"])

# =========================
# FILTROS
# =========================
col1, col2, col3 = st.columns(3)
with col1:
    data_min = df_all["Data"].min().date() if not df_all.empty else datetime.today().date()
    data_max = df_all["Data"].max().date() if not df_all.empty else datetime.today().date()
    data_inicial = st.date_input("📅 Data inicial", value=data_min)
with col2:
    data_final = st.date_input("📅 Data final", value=data_max)
with col3:
    especialidades = sorted(df_all["Especialidade"].dropna().unique()) if "Especialidade" in df_all.columns else []
    especialidade = st.multiselect("🩺 Especialidade(s)", especialidades, default=[])

# Aplica filtros
df = df_all[(df_all["Data"] >= pd.to_datetime(data_inicial)) & (df_all["Data"] <= pd.to_datetime(data_final))].copy()
if especialidade:
    df = df[df["Especialidade"].isin(especialidade)]

# Filtro de status
status_opcoes = ["Todos", "🟢 Reagendou", "🔴 Não quer reagendar", "🟡 Não atendeu (retornar contato)", "🟦 Mensagem enviada"]
status_filtro = st.selectbox("📋 Filtrar por Status", status_opcoes)
if status_filtro != "Todos":
    df = df[df["Status"] == status_filtro]

st.divider()

# =========================
# FUNÇÕES AUXILIARES
# =========================
def normaliza_telefone(tel: str) -> str:
    if tel is None:
        return ""
    digits = "".join(ch for ch in str(tel) if ch.isdigit())
    # remove prefixo 55 se já vier
    if digits.startswith("55"):
        digits = digits[2:]
    return digits

def ensure_log_sheet():
    try:
        return client.open_by_key(SHEET_ID).worksheet(LOG_SHEET)
    except gspread.exceptions.WorksheetNotFound:
        ws = client.open_by_key(SHEET_ID).add_worksheet(title=LOG_SHEET, rows=1000, cols=10)
        ws.update("A1:F1", [["CPF", "Nome", "Especialidade", "Status", "Operador", "Data_Hora"]])
        return ws

def append_log(cpf, nome, espec, status, operador):
    ws_log = ensure_log_sheet()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ws_log.append_row([cpf, nome, espec, status, operador, ts], value_input_option="USER_ENTERED")

# =========================
# LISTA E AÇÕES
# =========================
st.subheader("📞 Contatos")
if df.empty:
    st.info("Nenhum registro encontrado com os filtros selecionados.")
else:
    for i in range(len(df)):
        row_sheets = int(df.iloc[i]["Row"])
        nome = df.iloc[i].get("Nome", "")
        telefone = df.iloc[i].get("Telefone", "")
        cpf = df.iloc[i].get("CPF", "")
        espec = df.iloc[i].get("Especialidade", "")
        data_val = df.iloc[i].get("Data", None)
        data_str = pd.to_datetime(data_val).strftime("%d/%m/%Y") if pd.notnull(data_val) else ""

        # Monta link do WhatsApp com URL-encoding correto
        fone_limpo = normaliza_telefone(telefone)
        msg = f"Olá, {nome}. Vimos que sua última consulta com o {espec} foi no dia {data_str}. É muito importante que você faça um check-up anual para garantir qualidade na sua saúde. Posso agendar uma consulta pra você nessa semana?"
        link_whats = f"https://wa.me/55{fone_limpo}?text={quote(msg)}" if fone_limpo else ""

        colA, colB = st.columns([4, 3])
        with colA:
            st.write(f"👤 {nome} | 📞 {telefone} | 🪪 {cpf}")
            st.write(f"🩺 {espec} | 📅 {data_str}")
            if link_whats:
                if st.button("💬 Enviar mensagem no WhatsApp", key=f"wpp_{row_sheets}"):
                    # Atualiza status imediato na linha exata
                    status_col_idx = list(df_all.columns).index("Status") + 1  # base 1
                    sheet.update_cell(row_sheets, status_col_idx, "🟦 Mensagem enviada")
                    append_log(cpf, nome, espec, "🟦 Mensagem enviada", usuario_logado)
                    st.markdown(f"[Abrir conversa no WhatsApp]({link_whats})", unsafe_allow_html=True)

        with colB:
            # Botões/rádio de status manual
            estados = [
                "",
                "🔴 Não quer reagendar",
                "🟢 Reagendou",
                "🟡 Não atendeu (retornar contato)",
                "🟦 Mensagem enviada",
            ]
            atual = df.iloc[i].get("Status", "")
            novo = st.radio(
                "Atualizar status:",
                estados,
                index=estados.index(atual) if atual in estados else 0,
                key=f"rad_{row_sheets}",
                horizontal=True
            )
            df.at[df.index[i], "Status"] = novo

    st.divider()
    if st.button("💾 Salvar alterações manuais"):
        # Persiste todos os statuses alterados em lote
        for _, r in df.iterrows():
            if "Status" in r and pd.notnull(r["Status"]):
                row_sheets = int(r["Row"])
                status_col_idx = list(df_all.columns).index("Status") + 1
                sheet.update_cell(row_sheets, status_col_idx, r["Status"])
        st.success("✅ Status atualizados com sucesso!")