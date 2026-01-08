import streamlit as st
import os
import pandas as pd
import utils
import auth

# --- MODAIS E DIALOGS ---

# 1. Dialog para salvar com campos vazios (MANTIDO)
@st.dialog("Campos em Branco")
def confirmar_salvamento_incompleto(novo_registro):
    st.warning("Alguns campos do formulário não foram preenchidos.")
    st.write("Deseja salvar o levantamento mesmo assim?")
    col_sim, col_nao = st.columns(2)
    if col_sim.button("Sim, Salvar", use_container_width=True, type="primary"):
        st.session_state['db_formularios'].append(novo_registro)
        utils.salvar_dados_locais(st.session_state['db_formularios'])
        st.session_state['form_id'] += 1
        st.session_state['sucesso_salvamento'] = True 
        st.rerun()
    if col_nao.button("Não, Cancelar", use_container_width=True):
        st.rerun()

# 2. Dialog para excluir registro de levantamento (SEM SENHA, POIS JÁ ESTÁ LOGADO)
@st.dialog("Confirmar Exclusão")
def confirmar_exclusao_dialog(index=None, tipo="individual"):
    st.warning("⚠️ Esta ação não pode ser desfeita.")
    if st.button("Confirmar Exclusão", type="primary", use_container_width=True):
        if tipo == "individual": st.session_state['db_formularios'].pop(index)
        else: st.session_state['db_formularios'] = []
        utils.salvar_dados_locais(st.session_state['db_formularios'])
        st.rerun()

# 3. Dialog para excluir USUÁRIO DA LISTA DE ACESSO (Admin)
@st.dialog("Revogar Acesso")
def excluir_usuario_dialog(email_usuario):
    st.error(f"⚠️ Remover acesso de: **{email_usuario}**?")
    st.warning("Este usuário não conseguirá mais logar com o Google.")
    
    if st.button("Confirmar Revogação", type="primary", use_container_width=True):
        if auth.remover_usuario_autorizado(email_usuario):
            st.success(f"Acesso de {email_usuario} revogado!")
            st.rerun()
        else:
            st.error("Erro: Não é possível remover o Admin principal.")

@st.dialog("Exclusão Permanente de Arquivo")
def excluir_arquivo_permanente_dialog(caminho_arquivo):
    st.warning(f"🔥 ATENÇÃO: Apagar arquivo: **{caminho_arquivo}**")
    if st.button("CONFIRMAR EXCLUSÃO", type="primary", use_container_width=True):
        # Verifica se é admin pela função na sessão
        if st.session_state.get('usuario_funcao') == "Admin":
            if os.path.exists(caminho_arquivo):
                os.remove(caminho_arquivo)
                st.rerun()
        else:
            st.error("Apenas administradores podem excluir arquivos.")

# (Removido Dialog Alterar Senha - Não se aplica ao OAuth)

# --- FUNÇÕES DE PÁGINA ---
# (render_configurar_modelo, render_preenchimento, render_exportar_listar MANTIDOS IGUAIS)

def render_configurar_modelo():
    st.header("📋 Gerenciamento de Modelo")
    with st.container(border=True):
        st.markdown("### 🔍 Configuração Atual")
        st.write(f"Origem do Modelo: **{st.session_state.get('origem_modelo', 'Padrão')}**")
        if st.session_state.get('origem_modelo') == "Pessoal":
            if st.button("Restaurar para Modelo Padrão"):
                os.remove(utils.get_user_template_path())
                utils.carregar_modelo_atual()
                st.rerun()

    with st.container(border=True):
        st.markdown("### ⏫ Personalizar Meu Modelo")
        arq = st.file_uploader("Escolher arquivo (XLSX)", type=["xlsx"])
        if arq:
            path = utils.get_user_template_path()
            with open(path, "wb") as f: f.write(arq.getbuffer())
            st.success("Modelo personalizado carregado!")
            utils.carregar_modelo_atual()
            st.rerun()

def render_preenchimento():
    st.header("📝 Registro de Equipamento")
    if 'sucesso_salvamento' in st.session_state and st.session_state['sucesso_salvamento']:
        st.success("Levantamento Salvo com Sucesso!")
        st.session_state['sucesso_salvamento'] = False 

    if 'estrutura_modelo' in st.session_state and st.session_state['estrutura_modelo']:
        with st.container(border=True):
            col1, col2 = st.columns(2)
            tipo = col1.selectbox("Selecione o Equipamento", options=list(st.session_state['estrutura_modelo'].keys()))
            uc = col2.text_input("Código da Instalação / UC", placeholder="Ex: 312312", key=f"uc_{st.session_state['form_id']}")
        
        campos = st.session_state['estrutura_modelo'][tipo]
        respostas = {}
        with st.form(key=f"form_{st.session_state['form_id']}", border=True):
            st.markdown("#### Detalhamento Técnico")
            cols = st.columns(2)
            for i, c in enumerate(campos):
                target = cols[i % 2]
                if c['tipo'] == 'selecao':
                    respostas[c['nome']] = target.selectbox(c['nome'], options=c['opcoes'])
                else:
                    respostas[c['nome']] = target.text_input(c['nome'])
            
            submit_btn = st.form_submit_button("✅ SALVAR NO LEVANTAMENTO", use_container_width=True, type="primary")

            if submit_btn:
                if uc:
                    novo_registro = {
                        "cod_instalacao": uc, "tipo_equipamento": tipo, 
                        "data_hora": utils.get_data_hora_br().strftime("%d/%m/%Y %H:%M:%S"), "dados": respostas
                    }
                    campos_vazios = [k for k, v in respostas.items() if str(v).strip() == ""]
                    if campos_vazios: confirmar_salvamento_incompleto(novo_registro)
                    else:
                        st.session_state['db_formularios'].append(novo_registro)
                        utils.salvar_dados_locais(st.session_state['db_formularios'])
                        st.session_state['form_id'] += 1
                        st.session_state['sucesso_salvamento'] = True 
                        st.rerun()
                else: st.error("A UC é obrigatória.")
    else: st.warning("Carregue um modelo antes.")

# Em views.py

def render_exportar_listar():
    # Cabeçalho Minimalista
    c_title, c_metric = st.columns([3, 1])
    with c_title:
        st.header("📂 Gerenciamento de Dados")
        st.caption("Visualize, exclua ou exporte seus levantamentos.")
    with c_metric:
        # Mostra o contador num cartão destacado
        st.metric("Itens Registrados", len(st.session_state['db_formularios']), delta_color="normal")

    st.divider()

    # --- LISTA DE ITENS (LAYOUT EM CARTÕES) ---
    if st.session_state['db_formularios']:
        # Cabeçalho da tabela visual (opcional, ajuda na organização)
        c1, c2, c3, c4 = st.columns([2, 3, 2, 1])
        c1.markdown("**Código/UC**")
        c2.markdown("**Equipamento**")
        c3.markdown("**Data**")
        c4.markdown("**Ação**")
        st.markdown("---")

        for idx, item in enumerate(st.session_state['db_formularios']):
            # Container com fundo branco e borda suave
            with st.container():
                c_uc, c_tipo, c_data, c_del = st.columns([2, 3, 2, 1])
                
                # Alinhamento vertical visual usando padding ou markdown
                c_uc.markdown(f"**{item['cod_instalacao']}**")
                c_tipo.write(f"{item['tipo_equipamento']}")
                c_data.caption(f"{item['data_hora']}")
                
                # Botão de deletar menor e vermelho suave
                if c_del.button("✕", key=f"del_{idx}", help="Excluir item", type="secondary"):
                    confirmar_exclusao_dialog(index=idx)
            
            # Linha separadora sutil entre itens
            st.markdown("<hr style='margin: 5px 0; border-top: 1px solid #f0f2f6;'>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # --- BARRA DE EXPORTAÇÃO (CLEAN) ---
        with st.container(border=True):
            st.markdown("#### 📤 Exportar Relatório")
            
            excel_data = utils.exportar_para_excel(st.session_state['db_formularios'])
            
            # Grid para botões ficarem alinhados
            col_download, col_email_input, col_email_btn = st.columns([1.5, 2, 1])
            
            with col_download:
                st.download_button(
                    label="⬇️ Baixar Excel",
                    data=excel_data,
                    file_name="levantamento_poup.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    type="primary"
                )
            
            with col_email_input:
                email_dest = st.text_input("Enviar por e-mail:", placeholder="seu@email.com", label_visibility="collapsed")
            
            with col_email_btn:
                if st.button("Enviar 📧", use_container_width=True):
                    if email_dest:
                        with st.spinner("Enviando..."):
                            if utils.enviar_email(excel_data, email_dest):
                                st.toast("E-mail enviado com sucesso!", icon="✅")
                            else:
                                st.error("Erro ao enviar.")
                    else:
                        st.warning("Digite um e-mail.")

    else:
        # Estado vazio (Empty State) bonito
        st.info("ℹ️ Nenhum levantamento realizado ainda. Vá para a aba 'Preenchimento' para começar.")

def render_admin_panel():
    st.title("⚙️ Administração Geral")
    tab_users, tab_audit, tab_master = st.tabs(["👥 Controle de Acesso", "📂 Auditoria", "📄 Modelo Padrão"])
    
    with tab_users:
        st.subheader("Autorizar Novo E-mail")
        st.info("Adicione e-mails do Gmail ou Google Workspace para permitir o acesso.")
        with st.container(border=True):
            with st.form("novo_user_form", clear_on_submit=True):
                c1, c2 = st.columns([2, 1])
                new_email = c1.text_input("E-mail Google")
                role = c2.selectbox("Função", ["Técnico", "Admin"])
                
                if st.form_submit_button("Autorizar Acesso", use_container_width=True, type="primary"):
                    if new_email and "@" in new_email:
                        auth.adicionar_usuario_autorizado(new_email, role)
                        st.success(f"{new_email} agora tem acesso ao sistema!")
                    else:
                        st.error("Insira um e-mail válido.")

        st.divider()
        st.subheader("Usuários Autorizados")
        users = auth.carregar_permissoes()
        
        if users:
            for email, funcao in users.items():
                with st.container(border=True):
                    col_info, col_btn = st.columns([0.8, 0.2])
                    col_info.markdown(f"👤 **{email}** | 🛡️ {funcao}")
                    
                    if email != st.secrets["admin"]["email"]: 
                        if col_btn.button("Revogar", key=f"del_user_{email}"):
                            excluir_usuario_dialog(email)
                    else:
                        col_btn.markdown("*(Admin Geral)*")
        else:
            st.info("Nenhum usuário encontrado.")

    # (tab_audit e tab_master MANTIDOS IGUAIS ao código original)
    with tab_audit:
        arquivos = sorted([f for f in os.listdir(".") if f.startswith("dados_") and f.endswith(".json")])
        if arquivos:
            sel = st.selectbox("Selecione um arquivo:", arquivos)
            dados_rec = utils.carregar_dados_locais(path_especifico=sel)
            m1, m2 = st.columns(2)
            m1.metric("Registros", len(dados_rec))
            m2.metric("Tamanho", f"{(os.path.getsize(sel)/1024):.2f} KB")
            
            df = pd.DataFrame([{"UC": d.get('cod_instalacao'), "Tipo": d.get('tipo_equipamento'), "Data": d.get('data_hora')} for d in dados_rec])
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            c_act1, c_act2 = st.columns(2)
            rec_excel = utils.exportar_para_excel(dados_rec)
            if rec_excel: c_act1.download_button("⬇️ Baixar Backup", data=rec_excel, file_name=f"backup_{sel}.xlsx", use_container_width=True, type="primary")
            if c_act2.button("🔥 APAGAR DO SERVIDOR", use_container_width=True): excluir_arquivo_permanente_dialog(sel)
    
    with tab_master:
        st.subheader("Configuração Estrutural")
        with st.container(border=True):
            st.warning("⚠️ O arquivo padrão define o formulário inicial.")
            mestre = st.file_uploader("Substituir Modelo Base (xlsx)", type=["xlsx"])
            if mestre:
                with open(utils.PLANILHA_PADRAO_ADMIN, "wb") as f: f.write(mestre.getbuffer())
                st.success("Modelo Padrão atualizado!")
