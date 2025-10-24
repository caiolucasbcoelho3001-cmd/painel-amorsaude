import streamlit as st

# =========================
# CONFIGURAÇÕES INICIAIS
# =========================
st.set_page_config(page_title="Painel AmorSaúde", page_icon="❤️", layout="wide")

def logout():
    """Remove informações de sessão e atualiza a página."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.success("✅ Logout realizado com sucesso.")
    st.experimental_rerun()

# =========================
# TELA DE LOGIN
# =========================
if "usuario" not in st.session_state:
    st.title("🔐 Login - AmorSaúde")

    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if usuario == st.secrets["auth"]["gestor_user"] and senha == st.secrets["auth"]["gestor_pass"]:
            st.session_state["usuario"] = usuario
            st.session_state["perfil"] = "gestor"
            st.success("✅ Login como Gestor realizado!")
            st.experimental_rerun()

        elif usuario == st.secrets["auth"]["operador_user"] and senha == st.secrets["auth"]["operador_pass"]:
            st.session_state["usuario"] = usuario
            st.session_state["perfil"] = "operador"
            st.success("✅ Login como Operador realizado!")
            st.experimental_rerun()

        else:
            st.error("❌ Usuário ou senha incorretos")

# =========================
# ÁREA LOGADA
# =========================
else:
    st.sidebar.success(f"👋 Olá, {st.session_state['usuario']}!")
    if st.sidebar.button("🚪 Logout"):
        logout()

    st.title("📊 Bem-vindo ao Painel AmorSaúde")
    if st.session_state["perfil"] == "gestor":
        st.info("📈 Você está logado como **Gestor** e tem acesso a todos os painéis.")
    elif st.session_state["perfil"] == "operador":
        st.info("🧑‍💻 Você está logado como **Operador** e tem acesso ao painel de operações.")