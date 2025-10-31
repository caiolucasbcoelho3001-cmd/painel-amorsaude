import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from urllib.parse import quote
from datetime import datetime, timedelta

st.set_page_config(page_title="Pacientes Alvo", page_icon="🎯", layout="wide")
st.title("🎯 Pacientes Alvo - Retorno por Especialidade")

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
records = sheet.get_all_records()
base = pd.DataFrame(records)
base["Row"] = range(2, 2 + len(base))

if "Data" in base.columns:
    base["Data"] = pd.to_datetime(base["Data"], errors="coerce")
base = base.dropna(subset=["CPF", "Data"])

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

def normaliza_telefone(tel: str) -> str:
    if tel is None:
        return ""
    digits = "".join(ch for ch in str(tel) if ch.isdigit())
    if digits.startswith("55"):
        digits = digits[2:]
    return digits

# =========================
# AGRUPAR ÚLTIMA CONSULTA POR CPF + ESPECIALIDADE
# =========================
# Ordena por data e pega a linha mais recente por (CPF, Especialidade)
base_sorted = base.sort_values("Data")
idx_last = base_sorted.groupby(["CPF", "Especialidade"])["Data"].idxmax()
ultimos = base_sorted.loc[idx_last].copy()

# =========================
# FILTROS
# =========================
col1, col2 = st.columns(2)
with col1:
    especialidades = sorted(ultimos["Especialidade"].dropna().unique())
    especialidade_sel = st.selectbox("🩺 Especialidade", especialidades)

with col2:
    meses = st.slider("⏳ Sem retorno há (meses)", 1, 36, 12)

limite = datetime.today() - timedelta(days=meses * 30)
alvo = ultimos[(ultimos["Especialidade"] == especialidade_sel) & (ultimos["Data"] < limite)].copy()

st.subheader(f"📋 Pacientes sem retorno em {especialidade_sel} há mais de {meses} meses")
st.write(f"Total: {len(alvo)}")

if alvo.empty:
    st.info("Nenhum paciente encontrado nesse filtro.")
    st.stop()

# =========================
# INTERAÇÃO (WHATSAPP + STATUS)
# =========================
for i in range(len(alvo)):
    row = int(alvo.iloc[i]["Row"])  # linha da ocorrência mais recente nessa especialidade
    nome = alvo.iloc[i].get("Nome", "")
    telefone = alvo.iloc[i].get("Telefone", "")
    cpf = alvo.iloc[i].get("CPF", "")
    espec = alvo.iloc[i].get("Especialidade", "")
    data_val = alvo.iloc[i].get("Data", None)
    data_str = pd.to_datetime(data_val).strftime("%d/%m/%Y") if pd.notnull(data_val) else ""

    fone = normaliza_telefone(telefone)
    msg = f"Olá, {nome}. Vimos que sua última consulta com o {espec} foi no dia {data_str}. É muito importante que você faça um check-up anual para garantir qualidade na sua saúde. Posso agendar uma consulta pra você nessa semana?"
    link_whats = f"https://wa.me/55{fone}?text={quote(msg)}" if fone else ""

    colA, colB = st.columns([4, 3])
    with colA:
        st.write(f"👤 {nome} | 📞 {telefone} | 🪪 {cpf}")
        st.write(f"🩺 {espec} | 📅 Última: {data_str}")
        if link_whats:
            if st.button("💬 Enviar mensagem no WhatsApp", key=f"wpp_alvo_{row}"):
                # Atualiza status na linha mais recente dessa especialidade
                status_col_idx = list(base.columns).index("Status") + 1  # base 1
                sheet.update_cell(row, status_col_idx, "🟦 Mensagem enviada")
                append_log(cpf, nome, espec, "🟦 Mensagem enviada", usuario_logado)
                st.markdown(f"[Abrir conversa no WhatsApp]({link_whats})", unsafe_allow_html=True)

    with colB:
        estados = [
            "",
            "🔴 Não quer reagendar",
            "🟢 Reagendou",
            "🟡 Não atendeu (retornar contato)",
            "🟦 Mensagem enviada",
        ]
        atual = alvo.iloc[i].get("Status", "")
        novo = st.radio(
            "Atualizar status:",
            estados,
            index=estados.index(atual) if atual in estados else 0,
            key=f"rad_alvo_{row}",
            horizontal=True
        )
        alvo.at[alvo.index[i], "Status"] = novo

st.divider()
if st.button("💾 Salvar alterações manuais"):
    for _, r in alvo.iterrows():
        if "Status" in r and pd.notnull(r["Status"]):
            row = int(r["Row"])
            status_col_idx = list(base.columns).index("Status") + 1
            sheet.update_cell(row, status_col_idx, r["Status"])
    st.success("✅ Status atualizados com sucesso!")