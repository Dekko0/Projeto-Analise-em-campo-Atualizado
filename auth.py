import streamlit as st
import json
import os
import google_auth_oauthlib.flow
from googleapiclient.discovery import build

# Arquivo que agora guarda apenas EMAILS e FUNÇÕES (não mais senhas)
PERMISSOES_FILE = "permissoes.json"

# Configuração do Google carregada do secrets.toml
CLIENT_CONFIG = {
    "web": {
        "client_id": st.secrets["google"]["client_id"],
        "client_secret": st.secrets["google"]["client_secret"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}

# --- GERENCIAMENTO DE PERMISSÕES ---
def carregar_permissoes():
    # Carrega do secrets em vez de arquivo json local
    lista_fixa = st.secrets["acesso"]["permitidos"]
    # Transforma em dicionário para compatibilidade
    return {email: "Técnico" for email in lista_fixa}
    
    with open(PERMISSOES_FILE, "r") as f:
        return json.load(f)

def salvar_permissoes(dados):
    with open(PERMISSOES_FILE, "w") as f:
        json.dump(dados, f)

def adicionar_usuario_autorizado(email, funcao="Técnico"):
    users = carregar_permissoes()
    users[email] = funcao
    salvar_permissoes(users)

def remover_usuario_autorizado(email):
    users = carregar_permissoes()
    # Proteção para não remover o Admin principal dos secrets
    if email == st.secrets["admin"]["email"]:
        return False
        
    if email in users:
        del users[email]
        salvar_permissoes(users)
        return True
    return False

# --- LÓGICA DE OAUTH ---
def login_google():
    """Gera a URL de login do Google"""
    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        CLIENT_CONFIG,
        scopes=['openid', 'https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile'],
        redirect_uri=st.secrets["google"]["redirect_uri"]
    )
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    return authorization_url

def processar_callback():
    """Troca o código recebido na URL por um Token e pega o email"""
    try:
        # Pega o código da URL
        query_params = st.query_params
        code = query_params.get("code")

        if code:
            flow = google_auth_oauthlib.flow.Flow.from_client_config(
                CLIENT_CONFIG,
                scopes=['openid', 'https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile'],
                redirect_uri=st.secrets["google"]["redirect_uri"]
            )
            flow.fetch_token(code=code)
            credentials = flow.credentials
            
            # Pega info do usuário
            service = build('oauth2', 'v2', credentials=credentials)
            user_info = service.userinfo().get().execute()
            email = user_info['email']
            nome = user_info.get('name', email.split('@')[0]) # Usa o nome do Google ou parte do email

            # Verifica se o email está na lista de permitidos
            permissoes = carregar_permissoes()
            
            if email in permissoes:
                st.session_state['usuario_ativo'] = nome
                st.session_state['usuario_email'] = email
                st.session_state['usuario_funcao'] = permissoes[email]
                
                # Limpa a URL para remover o código
                st.query_params.clear()
                return True
            else:
                st.error(f"O e-mail {email} não tem permissão de acesso. Contate o Administrador.")
                return False
    except Exception as e:
        st.error(f"Erro na autenticação: {e}")
        return False

def logout():
    for key in ['usuario_ativo', 'usuario_email', 'usuario_funcao', 'db_formularios']:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

def tela_login():
    # Espaçamento superior para não colar no topo da página
    st.write("")
    st.write("")
    st.write("")

    # Centralização Horizontal: [Espaço, Conteúdo, Espaço]
    # A coluna do meio (1.5) define a largura do cartão de login
    col_esq, col_centro, col_dir = st.columns([1, 1.5, 1])

    with col_centro:
        # Container com borda suave
        with st.container(border=True):
            
            # --- TÍTULO E LOGO ---
            # Ícone grande centralizado, Título verde e Subtítulo cinza
            st.markdown("""
                <div style='text-align: center; padding: 20px 0;'>
                    <div style='font-size: 50px; margin-bottom: 10px;'>⚡</div>
                    <h1 style='
                        font-family: sans-serif; 
                        font-weight: 700; 
                        color: #9acc1f; 
                        margin: 0; 
                        padding: 0;
                        font-size: 32px;
                    '>
                        PoupEnergia
                    </h1>
                    <p style='
                        color: #666; 
                        font-size: 14px; 
                        margin-top: 5px; 
                        font-family: sans-serif;
                    '>
                        Acesso Seguro ao Sistema de Cargas
                    </p>
                </div>
            """, unsafe_allow_html=True)
            
            st.write("") # Pequeno respiro antes do botão
            
            # --- LÓGICA DO BOTÃO ---
            url_login = login_google()
            
            # Botão CSS Minimalista e Interativo
            # Inclui hover (mudança de cor) e sombra suave
            btn_html = f"""
            <div style="display: flex; justify-content: center; margin-bottom: 30px;">
                <a href="{url_login}" target="_self" style="text-decoration: none; width: 80%;">
                    <button style="
                        width: 100%; 
                        padding: 12px 20px; 
                        background-color: #2E7D32; 
                        color: white; 
                        border: none; 
                        border-radius: 8px; 
                        font-size: 16px; 
                        font-weight: 600; 
                        cursor: pointer; 
                        box-shadow: 0 2px 5px rgba(0,0,0,0.1); 
                        transition: background-color 0.3s ease;
                    "
                    onmouseover="this.style.backgroundColor='#1B5E20'" 
                    onmouseout="this.style.backgroundColor='#2E7D32'">
                        Entrar com Google
                    </button>
                </a>
            </div>
            """
            st.markdown(btn_html, unsafe_allow_html=True)

            # --- PROCESSAMENTO DO CALLBACK ---
            if "code" in st.query_params:
                with st.spinner("Autenticando..."):
                    if processar_callback():
                        st.rerun()

    st.stop()


    

