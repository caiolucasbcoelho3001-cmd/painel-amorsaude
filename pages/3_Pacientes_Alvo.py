import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from urllib.parse import quote
from datetime import datetime, timedelta
import math
import string
import io

st.set_page_config(page_title="Pacientes Alvo", page_icon="🎯", layout="wide")
st.title("🎯 Pacientes Alvo - Retorno por Especialidade")

# Usuário logado (definido no login)
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
# Linha real no Sheets (cabeçalho é linha 1)
base["Row"] = range(2, 2 + len(base))

# Tipagem e limpeza
if "Data" in base.columns:
    base["Data"] = pd.to_datetime(base["Data"], errors="coerce")
base = base.dropna(subset=["CPF", "Data"])

# Garante coluna Status na base (evita erro se faltar)
if "Status" not in base.columns:
    base["Status"] = ""

# =========================
# Funções auxiliares
# =========================
def ensure_log_sheet():
    """Garante a existência da aba LOG com cabeçalho padrão."""
    try:
        return client.open_by_key(SHEET_ID).worksheet(LOG_SHEET)
    except gspread.exceptions.WorksheetNotFound:
        ws = client.open_by_key(SHEET_ID).add_worksheet(title=LOG_SHEET, rows=1000, cols=10)
        ws.update("A1:F1", [["CPF", "Nome", "Especialidade", "Status", "Operador", "Data_Hora"]])
        return ws

def append_log(cpf, nome, espec, status, operador):
    """Registra linha no LOG."""
    ws_log = ensure_log_sheet()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ws_log.append_row([cpf, nome, espec, status, operador, ts], value_input_option="USER_ENTERED")

def normaliza_telefone(tel: str) -> str:
    """Remove caracteres e prefixo 55 se houver; retorna apenas DDD+numero."""
    if tel is None:
        return ""
    digits = "".join(ch for ch in str(tel) if ch.isdigit())
    if digits.startswith("55"):
        digits = digits[2:]
    return digits

# =========================
# AGRUPAR ÚLTIMA CONSULTA POR (CPF, Especialidade)
# =========================
base_sorted = base.sort_values("Data")
idx_last = base_sorted.groupby(["CPF", "Especialidade"])["Data"].idxmax()
ultimos = base_sorted.loc[idx_last].copy()

# =========================
# FILTROS PRINCIPAIS
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
st.caption(f"Total (antes de letra/ordenação): {len(alvo)}")

if alvo.empty:
    st.info("Nenhum paciente encontrado nesse filtro.")
    st.stop()

# =========================
# FILTRO POR LETRA + ORDENAÇÃO
# =========================
colL, colO = st.columns([2, 2])

letras_disponiveis = sorted(set([str(n)[0].upper() for n in alvo["Nome"].dropna().astype(str) if str(n)]))
op_letras = ["Todas"] + [l for l in string.ascii_uppercase if l in letras_disponiveis]
with colL:
    letra_sel = st.selectbox("🔤 Filtrar por letra inicial do Nome", op_letras, index=0)

with colO:
    ordem = st.radio("🔡 Ordenação por Nome", ["A→Z", "Z→A"], horizontal=True, index=0)

if letra_sel != "Todas":
    alvo = alvo[alvo["Nome"].astype(str).str.upper().str.startswith(letra_sel)]

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
# INTERAÇÃO (WhatsApp + Status)
# =========================
for i in range(len(page_df)):
    row = int(page_df.iloc[i]["Row"])  # linha exata no Sheets
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
                # Atualiza status para 'Mensagem enviada'
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
    for _, r in page_df.iterrows():
        if "Status" in r and pd.notnull(r["Status"]):
            row = int(r["Row"])
            status_col_idx = list(base.columns).index("Status") + 1
            sheet.update_cell(row, status_col_idx, r["Status"])
    st.success("✅ Status atualizados com sucesso!")

st.divider()

# =========================
# EXPORTAR (CSV)
# =========================
st.subheader("📤 Exportar planilha filtrada")
csv_export = alvo.to_csv(index=False, encoding='utf-8-sig')
st.download_button(
    label="📥 Baixar lista filtrada (CSV)",
    data=csv_export,
    file_name=f"Pacientes_Alvo_{especialidade_sel}_{meses}meses.csv",
    mime="text/csv",
    help="Baixa um arquivo CSV com os pacientes filtrados (todas as páginas)."
)
st.caption("💡 O arquivo inclui Nome, CPF, Telefone, Especialidade, Data e Status.")

# =========================
# EXPORTAR (Excel .xlsx) com fallback xlsxwriter -> openpyxl
# =========================
st.subheader("📤 Exportar planilha filtrada (Excel)")
alvo_xlsx = alvo.copy()
if "Data" in alvo_xlsx.columns:
    alvo_xlsx["Data"] = pd.to_datetime(alvo_xlsx["Data"], errors="coerce").dt.strftime("%d/%m/%Y")

xlsx_buffer = io.BytesIO()

# tenta xlsxwriter; se não houver, usa openpyxl (sem ajuste de largura)
try:
    import xlsxwriter  # noqa: F401
    excel_engine = "xlsxwriter"
except Exception:
    excel_engine = "openpyxl"

with pd.ExcelWriter(xlsx_buffer, engine=excel_engine) as writer:
    alvo_xlsx.to_excel(writer, sheet_name="Pacientes", index=False)

    if excel_engine == "xlsxwriter":
        workbook = writer.book
        worksheet = writer.sheets["Pacientes"]
        for i, col in enumerate(alvo_xlsx.columns):
            try:
                max_len = max(alvo_xlsx[col].astype(str).map(len).max(), len(str(col)))
            except Exception:
                max_len = len(str(col))
            width = max(12, min(40, max_len + 2))
            worksheet.set_column(i, i, width)

xlsx_buffer.seek(0)
st.download_button(
    label="📥 Baixar lista filtrada (Excel .xlsx)",
    data=xlsx_buffer.getvalue(),
    file_name=f"Pacientes_Alvo_{especialidade_sel}_{meses}meses.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    help="Baixa um Excel com os pacientes filtrados (todas as páginas)."
)