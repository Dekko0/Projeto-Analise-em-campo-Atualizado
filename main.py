# ---main.py---

import streamlit as st
import styles
import auth
import views
import scheduler 
import time          # Import necessário para o controle de tempo
import utils         # Import necessário para checar persistência

# configuração da pagina
st.set_page_config(page_title="Levantamento de Cargas", layout="wide", page_icon="⚡")

# --- CONSTANTES DE CONFIGURAÇÃO ---
SESSION_TIMEOUT_MINUTES = 30  # Tempo limite em minutos

# --- INICIALIZAÇÃO DO AGENDADOR ---
scheduler.iniciar_agendador()

# aplicar estilos
styles.apply_custom_style()

# inicializar session state
if 'usuario_ativo' not in st.session_state: st.session_state['usuario_ativo'] = None
if 'form_id' not in st.session_state: st.session_state['form_id'] = 0

# --- FUNCIONALIDADE 2: VERIFICAÇÃO "LEMBRAR DE MIM" (AUTO-LOGIN) ---
# Executa apenas se não houver usuário logado
if st.session_state['usuario_ativo'] is None:
    usuario_persistido = utils.verificar_sessao_persistente()
    if usuario_persistido:
        st.session_state['usuario_ativo'] = usuario_persistido
        st.session_state['db_formularios'] = utils.carregar_dados_locais()
        utils.carregar_modelo_atual()
        st.toast(f"Bem-vindo de volta, {usuario_persistido}!", icon="👋")

# --- FUNCIONALIDADE 1: CONTROLE DE INATIVIDADE ---
if st.session_state['usuario_ativo']:
    # Inicializa o timestamp se não existir
    if 'last_activity' not in st.session_state:
        st.session_state['last_activity'] = time.time()
    
    # Verifica o tempo decorrido
    tempo_inativo = time.time() - st.session_state['last_activity']
    limite_segundos = SESSION_TIMEOUT_MINUTES * 60
    
    if tempo_inativo > limite_segundos:
        # Timeout atingido: Logout suave (mantém "lembrar de mim" se existir, mas pede re-autenticação por segurança imediata ou apenas limpa a sessão RAM)
        # Nota: A regra diz "Logout por inatividade NÃO deve apagar o lembrar de mim".
        # Porém, para forçar o login, precisamos limpar a variavel de sessão. 
        # Na proxima recarga, se o "lembrar de mim" existir, ele logaria de novo.
        # Para evitar loop, o timeout idealmente invalida a sessão atual RAM.
        
        st.session_state['usuario_ativo'] = None
        st.error(f"Sessão expirada por inatividade ({SESSION_TIMEOUT_MINUTES} min). Por favor, faça login novamente.")
        st.session_state.pop('last_activity', None) # Limpa o timer
        time.sleep(2) # Pequeno delay para ler a mensagem
        st.rerun()
    else:
        # Usuário ativo: Atualiza o timestamp
        st.session_state['last_activity'] = time.time()

# 4. verificar login
if not st.session_state['usuario_ativo']:
    auth.tela_login()
    st.stop() # Interrompe execução se não logado para evitar renderizar sidebar vazia

# 5. sidebar e navegação
with st.sidebar:
    # icone google energy_savings_leaf
    st.markdown("## <span class='material-symbols-outlined'>energy_savings_leaf</span> PoupEnergia", unsafe_allow_html=True)
    # icone google person
    st.markdown(f"<span class='material-symbols-outlined'>person</span> **{st.session_state['usuario_ativo']}**", unsafe_allow_html=True)
    
    if st.button("Alterar Senha", use_container_width=True):
        views.alterar_senha_dialog()
    
    st.divider()
    
    # opções limpas
    opts = ["Configurar Modelo", "Preenchimento", "Exportar & Listar"]
    if st.session_state['usuario_ativo'] == "Admin": opts.append("Painel Admin")
    
    menu = st.radio("Navegação", opts)
    st.divider()
    
    # --- LOGOUT MANUAL ---
    if st.button("Sair / Logout", use_container_width=True):
        st.session_state['usuario_ativo'] = None
        # Logout manual DEVE apagar o "lembrar de mim"
        utils.limpar_sessao_persistente() 
        st.rerun()
    # ---------------------
   
    st.divider()
    # Adicione um expander ou botão para configurações
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
