# =========================
# FILTROS
# =========================
st.title("🧑‍💻 Painel de Operadores - AmorSaúde")

# 📅 Filtro de datas
if not df.empty and 'Data' in df.columns:
    col1, col2 = st.columns(2)
    with col1:
        data_inicial = st.date_input("📅 Data inicial", value=df['Data'].min().date())
    with col2:
        data_final = st.date_input("📅 Data final", value=df['Data'].max().date())
    df = df[(df['Data'] >= pd.to_datetime(data_inicial)) & (df['Data'] <= pd.to_datetime(data_final))]

# 🩺 Filtro de especialidade
if "Especialidade" in df.columns:
    especialidades_disponiveis = sorted(df["Especialidade"].dropna().unique())
    especialidade_selecionada = st.multiselect("🩺 Filtrar por especialidade", especialidades_disponiveis)
    if especialidade_selecionada:
        df = df[df["Especialidade"].isin(especialidade_selecionada)]

# 📌 Filtro de status
status_opcoes = [
    "Todos",
    "🔴 Não quer reagendar",
    "🟢 Reagendou",
    "🟡 Não atendeu (retornar contato)",
    "🔵 Mudou de médico"
]
status_selecionado = st.selectbox("📌 Filtrar por status", status_opcoes)
if status_selecionado != "Todos":
    df = df[df["Status"] == status_selecionado]

# 📊 Contador por status
st.subheader("📊 Status geral")
contagem = df["Status"].value_counts()
for s in status_opcoes[1:]:
    st.write(f"{s}: {contagem.get(s, 0)}")