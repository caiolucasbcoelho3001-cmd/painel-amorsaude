import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from urllib.parse import quote
from datetime import datetime, timedelta
import math
import string

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
base_sorted = base.sort_values("Data")
idx_last = base_sorted.groupby(["CPF", "Especialidade"])["Data"].idxmax()
ultimos = base_sorted.loc[idx_last].copy()

# =========================
# FILTROS (especialidade + tempo)
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
st.caption(f"Total (antes dos filtros de letra/ordenação): {len(alvo)}")

if alvo.empty:
    st.info("Nenhum paciente encontrado nesse filtro.")
    st.stop()

# =========================
# FILTRO POR LETRA + ORDENAÇÃO
# =========================
colL, colO = st.columns([2, 2])

# Letra inicial: 'Todas' + A..Z, mas só exibe letras que existem na base
letras_disponiveis = sorted(set([str(n)[0].upper() for n in alvo["Nome"].dropna().astype(str) if str(n)]))
op_letras = ["Todas"] + [l for l in string.ascii_uppercase if l in letras_disponiveis]
with colL:
    letra_sel = st.selectbox("🔤 Filtrar por letra inicial do Nome", op_letras, index=0)

with colO:
    ordem = st.radio("🔡 Ordenação por Nome", ["A→Z", "Z→A"], horizontal=True, index=0)

# Aplica filtro de letra
if letra_sel != "Todas":
    alvo = alvo[alvo["Nome"].astype(str).str.upper().str.startswith(letra_sel)]

# Ordena
alvo = alvo.sort_values("Nome", ascending=(ordem == "A→Z"))

st.caption(f"Total após filtros: {len(alvo)}")

# =========================
# PAGINAÇÃO (50 por página)
# =========================
PAGE_SIZE = 50
total_reg = len(alvo)
total_pages = max(1, math.ceil(total_reg / PAGE_SIZE))

if "alvo_page" not in st.session_state:
    st.session_state.alvo_page = 1

colP1, colP2, colP3 = st.columns([1, 2, 1])
with colP1:
    prev_disabled = st.session_state.alvo_page <= 1
    if st.button("⬅️ Anterior", disabled=prev_disabled):
        st.session_state.alvo_page = max(1, st.session_state.alvo_page - 1)
with colP2:
    page_choice = st.number_input("Página", min_value=1, max_value=total_pages, value=st.session_state.alvo_page, step=1)
    if page_choice != st.session_state.alvo_page:
        st.session_state.alvo_page = page_choice
with colP3:
    next_disabled = st.session_state.alvo_page >= total_pages
    if st.button("Próxima ➡️", disabled=next_disabled):
        st.session_state.alvo_page = min(total_pages, st.session_state.alvo_page + 1)

start = (st.session_state.alvo_page - 1) * PAGE_SIZE
end = start + PAGE_SIZE
page_df = alvo.iloc[start:end].copy()

st.caption(f"Mostrando {start+1}–{min(end, total_reg)} de {total_reg} | Página {st.session_state.alvo_page}/{total_pages}")
st.divider()

# =========================
# INTERAÇÃO (WHATSAPP + STATUS)
# =========================
for i in range(len(page_df)):
    row = int(page_df.iloc[i]["Row"])  # linha da ocorrência mais recente nessa especialidade
    nome = page_df.iloc[i].get("Nome", "")
    telefone = page_df.iloc[i].get("Telefone", "")
    cpf = page_df.iloc[i].get("CPF", "")
    espec = page_df.iloc[i].get("Especialidade", "")
    data_val = page_df.iloc[i].get("Data", None)
    data_str = pd.to_datetime(data_val).strftime("%d/%m/%Y") if pd.notnull(data_val) else ""
    status_atual = page_df.iloc[i].get("Status", "")

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
        novo = st.radio(
            "Atualizar status:",
            estados,
            index=estados.index(status_atual) if status_atual in estados else 0,
            key=f"rad_alvo_{row}",
            horizontal=True
        )
        page_df.at[page_df.index[i], "Status"] = novo

st.divider()
if st.button("💾 Salvar alterações manuais desta página"):
    # Atualiza apenas os registros da página visível
    for _, r in page_df.iterrows():
        if "Status" in r and pd.notnull(r["Status"]):
            row = int(r["Row"])
            status_col_idx = list(base.columns).index("Status") + 1
            sheet.update_cell(row, status_col_idx, r["Status"])
    st.success("✅ Status atualizados com sucesso!")