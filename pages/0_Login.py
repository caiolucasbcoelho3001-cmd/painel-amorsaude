import streamlit as st

# =========================
# PÁGINA DE LOGIN
# =========================
st.set_page_config(page_title="Login", page_icon="🔐", layout="centered")

st.title("🔐 Login - Painel AmorSaúde")

# Se já estiver logado, redireciona
if "usuario" in st.session_state:
    st.success(f"✅ Você já está logado como: {st.session_state['usuario']}")
    st.stop()

# Formulário de login
with st.form("login_form"):
    usuario = st.text_input("👤 Usuário")
    senha = st.text_input("🔑 Senha", type="password")
    submit = st.form_submit_button("Entrar")

# =========================
# VERIFICAÇÃO DE CREDENCIAIS
# =========================
if submit:
    gestor_user = st.secrets["auth"]["gestor_user"]
    gestor_pass = st.secrets["auth"]["gestor_pass"]
    operador_user = st.secrets["auth"]["operador_user"]
    operador_pass = st.secrets["auth"]["operador_pass"]

    if usuario == gestor_user and senha == gestor_pass:
        st.session_state["usuario"] = usuario
        st.session_state["perfil"] = "gestor"
        st.success("✅ Login gestor realizado com sucesso!")
        st.rerun()

    elif usuario == operador_user and senha == operador_pass:
        st.session_state["usuario"] = usuario
        st.session_state["perfil"] = "operador"
        st.success("✅ Login operador realizado com sucesso!")
        st.rerun()

    else:
        st.error("❌ Usuário ou senha inválidos.")
