import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta

# =========================
# CONFIGURAÇÃO DO GOOGLE SHEETS
# =========================
SHEET_ID = "19V9iX_wKsRulGeDZYgbzqEhK3bpOEgS5-t_fk2kRjdA"
SHEET_NAME = "Sheet1"

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["google_service_account"], scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
dados = sheet.get_all_records()
df = pd.DataFrame(dados)

# =========================
# LAYOUT
# =========================
st.title("🩺 Pacientes Alvo - AmorSaúde")

# Filtro de especialidade
especialidades = sorted(df['Especialidade'].dropna().unique())
especialidade = st.selectbox("🩺 Selecione a especialidade", especialidades)

# Filtro de tempo sem retorno
meses = st.slider("⏳ Pacientes sem retorno há (meses)", 1, 24, 12)
limite = datetime.today() - timedelta(days=meses * 30)

# Converter Data para datetime
df['Data'] = pd.to_datetime(df['Data'], errors='coerce')

# Selecionar pacientes dessa especialidade com última consulta antiga
filtro = (df['Especialidade'] == especialidade) & (df['Data'] < limite)
pacientes_alvo = df[filtro].drop_duplicates(subset=['CPF'], keep='last')

# =========================
# EXIBIR RESULTADOS
# =========================
st.subheader(f"📋 Pacientes que não retornam há mais de {meses} meses em {especialidade}")

for i in range(len(pacientes_alvo)):
    nome = pacientes_alvo.iloc[i]['Nome']
    telefone = pacientes_alvo.iloc[i]['Telefone']
    cpf = pacientes_alvo.iloc[i]['CPF']
    data = pacientes_alvo.iloc[i]['Data'].strftime("%d/%m/%Y")
    especialidade = pacientes_alvo.iloc[i]['Especialidade']

    telefone_limpo = str(telefone).replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if telefone_limpo.startswith("55"):
        telefone_limpo = telefone_limpo[2:]

    msg = f"Olá, {nome}. Vimos que sua última consulta com o {especialidade} foi no dia {data}. É muito importante que você faça um check-up anual para garantir qualidade na sua saúde. Posso agendar uma consulta pra você nessa semana?"
    link_whatsapp = f"https://wa.me/55{telefone_limpo}?text={msg}"

    col1, col2 = st.columns([3, 1])
    with col1:
        st.write(f"👤 {nome} | 📞 {telefone} | 🩺 {especialidade} | 🪪 {cpf} | 📅 Última: {data}")

    with col2:
        if st.button("💬 Enviar mensagem", key=f"alvo_{i}"):
            sheet.update_cell(i + 2, df.columns.get_loc("Status") + 1, "🟦 Mensagem enviada")
            st.markdown(f"[Abrir WhatsApp]({link_whatsapp})", unsafe_allow_html=True)

st.success("✅ Clique em 'Enviar mensagem' para abrir o WhatsApp e marcar como 'Mensagem enviada'.")
