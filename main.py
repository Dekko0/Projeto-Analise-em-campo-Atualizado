import streamlit as st
import styles
import auth
import views
from utils import carregar_dados_locais, carregar_modelo_atual

# 1. Configuração da Página (LAYOUT WIDE para dar respiro)
st.set_page_config(
    page_title="PoupEnergia", 
    layout="wide", 
    page_icon="⚡",
    initial_sidebar_state="expanded"
)

# 2. Styles
styles.apply_custom_style()

# 3. Session State
if 'usuario_ativo' not in st.session_state: st.session_state['usuario_ativo'] = None
if 'form_id' not in st.session_state: st.session_state['form_id'] = 0

# 4. Login Check
if not st.session_state['usuario_ativo']:
    auth.tela_login()
else:
    if 'db_formularios' not in st.session_state:
        st.session_state['db_formularios'] = carregar_dados_locais()
        carregar_modelo_atual()

# --- SIDEBAR MINIMALISTA ---
with st.sidebar:
    # Logo / Título
    st.markdown("<h2 style='color: #9acc1f; text-align: center;'>⚡ PoupEnergia</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    # Menu de Navegação Limpo
    st.markdown("### Navegação")
    opts = {
        "📋 Modelo de Dados": "Configurar Modelo",
        "📝 Preenchimento": "Preenchimento",
        "📤 Meus Levantamentos": "Exportar & Listar"
    }
    
    # Adiciona Admin se necessário
    if st.session_state.get('usuario_funcao') == "Admin": 
        opts["⚙️ Administração"] = "Painel Admin"
    
    # O Radio Button padrão do Streamlit já é limpo, mas vamos renomear as chaves para ficar mais amigável
    selection = st.radio("Ir para:", list(opts.keys()), label_visibility="collapsed")
    menu = opts[selection]

    # Espaçador para empurrar o perfil para baixo
    st.markdown("<br>" * 5, unsafe_allow_html=True)
    
    # Card de Perfil no final da sidebar
    with st.container(border=True):
        col_avatar, col_info = st.columns([1, 3])
        with col_avatar:
            st.markdown("👤") # Pode substituir por st.image se tiver foto
        with col_info:
            st.write(f"**{st.session_state['usuario_ativo']}**")
            st.caption(st.session_state.get('usuario_funcao', 'Técnico'))
        
        if st.button("Sair da Conta", use_container_width=True):
            auth.logout()

# --- ROTEAMENTO ---
# Adicionei um container principal para centralizar e dar margem
with st.container():
    if menu == "Configurar Modelo":
        views.render_configurar_modelo()
    elif menu == "Preenchimento":
        views.render_preenchimento()
    elif menu == "Exportar & Listar":
        views.render_exportar_listar()
    elif menu == "Painel Admin":
        views.render_admin_panel()
