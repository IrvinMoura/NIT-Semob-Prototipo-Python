# app.py
import streamlit as st
import km
import mco
import soltura
import ipk
import viabilidade

# Configuração da página
st.set_page_config(layout="wide")

# Estado para navegação
if "pagina" not in st.session_state:
    st.session_state.pagina = "home"

def voltar_home():
    st.session_state.pagina = "home"

# =========================
# Tela inicial (HUB)
# =========================
if st.session_state.pagina == "home":
    st.title("HUB - SEMOB")
    st.markdown("### Escolha o relatório desejado:")

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        if st.button("📊 Quilometragem", use_container_width=True):
            st.session_state.pagina = "km"
    with col2:
        if st.button("🚌 Passagens de Ônibus", use_container_width=True):
            st.session_state.pagina = "mco"
    with col3:
        if st.button("🚍 Soltura", use_container_width=True):
            st.session_state.pagina = "soltura"
    with col4:
        if st.button("📊 IPK", use_container_width=True):
            st.session_state.pagina = "ipk"
    with col5:
        if st.button("📊 Viabilidade", use_container_width=True):
            st.session_state.pagina = "viabilidade"

# =========================
# Relatórios
# =========================
elif st.session_state.pagina == "km":
    st.button("⬅️ Voltar", on_click=voltar_home)
    km.main()

elif st.session_state.pagina == "mco":
    st.button("⬅️ Voltar", on_click=voltar_home)
    mco.main()

elif st.session_state.pagina == "soltura":
    st.button("⬅️ Voltar", on_click=voltar_home)
    soltura.main()

elif st.session_state.pagina == "ipk":
    st.button("⬅️ Voltar", on_click=voltar_home)
    ipk.main()

elif st.session_state.pagina == "viabilidade":
    st.button("⬅️ Voltar", on_click=voltar_home)
    viabilidade.main()
