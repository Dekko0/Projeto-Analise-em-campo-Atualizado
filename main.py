import streamlit as st
from streamlit_cookies_controller import CookieController # <-- Adicionado
import styles
import auth
import views
import scheduler 
import time          
import utils        

# configuração da pagina
st.set_page_config(page_title="Levantamento de Cargas", layout="wide", page_icon="⚡")

# Inicializa o controlador de cookies
controller = CookieController()

# --- CONSTANTES DE CONFIGURAÇÃO ---
SESSION_TIMEOUT_MINUTES = 30  

# --- INICIALIZAÇÃO DO AGENDADOR ---
scheduler.iniciar_agendador()

# aplicar estilos
styles.apply_custom_style()

# inicializar session state
if 'usuario_ativo' not in st.session_state: st.session_state['usuario_ativo'] = None
if 'form_id' not in st.session_state: st.session_state['form_id'] = 0

# --- NOVO: VERIFICAÇÃO DO COOKIE NA MÁQUINA DO USUÁRIO ---
if st.session_state['usuario_ativo'] is None:
    token_salvo = controller.get("poupenergia_session")
    if token_salvo:
        usuario_persistido = utils.validar_token_sessao(token_salvo)
        if usuario_persistido:
            st.session_state['usuario_ativo'] = usuario_persistido
            st.session_state['db_formularios'] = utils.carregar_dados_locais()
            utils.carregar_modelo_atual()
            st.toast(f"Bem-vindo de volta, {usuario_persistido}!", icon="👋")
        else:
            # Token inválido ou expirado, limpa do navegador
            controller.remove("poupenergia_session")


# --- FUNCIONALIDADE 1: CONTROLE DE INATIVIDADE ---
if st.session_state['usuario_ativo']:
    if 'last_activity' not in st.session_state:
        st.session_state['last_activity'] = time.time()
    
    tempo_inativo = time.time() - st.session_state['last_activity']
    limite_segundos = SESSION_TIMEOUT_MINUTES * 60
    
    if tempo_inativo > limite_segundos:
        st.session_state['usuario_ativo'] = None
        st.error(f"Sessão expirada por inatividade ({SESSION_TIMEOUT_MINUTES} min). Por favor, faça login novamente.")
        st.session_state.pop('last_activity', None) 
        time.sleep(2) 
        st.rerun()
    else:
        st.session_state['last_activity'] = time.time()


# 4. verificar login
if not st.session_state['usuario_ativo']:
    auth.tela_login()
    st.stop() 


# 5. sidebar e navegação
with st.sidebar:
    st.markdown("## <span class='material-symbols-outlined'>energy_savings_leaf</span> PoupEnergia", unsafe_allow_html=True)
    st.markdown(f"<span class='material-symbols-outlined'>person</span> **{st.session_state['usuario_ativo']}**", unsafe_allow_html=True)
    
    if st.button("Alterar Senha", use_container_width=True):
        views.alterar_senha_dialog()
    
    st.divider()
    
    opts = ["Configurar Modelo", "Preenchimento", "Exportar & Listar"]
    if st.session_state['usuario_ativo'] == "Admin": opts.append("Painel Admin")
    
    menu = st.radio("Navegação", opts)
    st.divider()
    
    # --- NOVO: LOGOUT MANUAL REMOVE O COOKIE ---
    if st.button("Sair / Logout", use_container_width=True):
        # Limpa o token do servidor e do navegador
        token_atual = controller.get("poupenergia_session")
        if token_atual:
            utils.remover_sessao(token_atual)
            controller.remove("poupenergia_session")
            
        st.session_state['usuario_ativo'] = None
        st.rerun()
   
    st.divider()
    with st.expander("⚙️ Configurações"):
        views.view_configuracao_backup_cliente(st.session_state['usuario_ativo'])


# roteamento de paginas
if menu == "Configurar Modelo":
    views.render_configurar_modelo()
elif menu == "Preenchimento":
    views.render_preenchimento()
elif menu == "Exportar & Listar":
    views.render_exportar_listar()
elif menu == "Painel Admin":
    views.render_admin_panel()
