import streamlit as st
import os
import pandas as pd
import utils
import auth
from collections import defaultdict
import views
import datetime
import time

# --- AUXILIARES VISUAIS & UI ---
def section_title(icon, text):
    """Renderiza um título de seção com espaçamento e estilo corporativo."""
    st.markdown(f"""
    <div style="margin-top: 20px; margin-bottom: 10px; display: flex; align-items: center; gap: 8px;">
        <span class='material-symbols-outlined' style='font-size: 24px; color: #fafafa;'>{icon}</span>
        <span style='font-size: 18px; font-weight: 600; color: #fafafa;'>{text}</span>
    </div>
    """, unsafe_allow_html=True)

# --- NOVA FUNÇÃO: UI DO CLIENTE ---
def view_configuracao_backup_cliente(usuario_ativo):
    """
    Renderiza o formulário de configuração de backup para o cliente logado.
    """
    st.markdown("### Configuração de Backup Automático")
    st.info("Receba diariamente (às 20:00) um arquivo .zip contendo seus dados e fotos.")
    
    # Carrega preferências
    todas_prefs = utils.carregar_prefs_todos_clientes()
    user_prefs = todas_prefs.get(usuario_ativo, {})
    
    email_atual = user_prefs.get("email", "")
    ativo_atual = user_prefs.get("ativo", False)
    
    with st.form("form_backup_cliente"):
        col1, col2 = st.columns([3, 1])
        with col1:
            novo_email = st.text_input("E-mail para recebimento", value=email_atual, placeholder="seu.email@exemplo.com")
        with col2:
            st.write("") # Espaçamento
            st.write("") 
            novo_ativo = st.checkbox("Ativar envio diário", value=ativo_atual)
        
        submit = st.form_submit_button("Salvar Preferências")
        
        if submit:
            if novo_ativo and not novo_email:
                st.error("Para ativar o backup, é necessário informar um e-mail.")
            else:
                utils.salvar_prefs_cliente(usuario_ativo, novo_email, novo_ativo)
                st.success("Configurações salvas com sucesso!")
                time.sleep(1)
                st.rerun()

# --- ATUALIZAÇÃO: UI DO ADMIN (Opcional, mas recomendado) ---
def view_configuracao_backup_admin():
    # ... código existente ...
    # Apenas altere os textos para indicar "Auditoria" ou "Backup Global"
    st.markdown("### 🔒 Auditoria de Dados (Admin)")
    st.write("E-mail para recebimento consolidado de TODOS os clientes.")
    # ... resto da lógica existente ...

def main_header(icon, text):
    """Cabeçalho principal da página."""
    st.markdown(f"""
    <div style="border-bottom: 1px solid #ddd; padding-bottom: 10px; margin-bottom: 20px;">
        <h2 style='display: flex; align-items: center; gap: 10px; margin: 0; font-size: 26px;'>
            <span class='material-symbols-outlined' style='font-size: 32px;'>{icon}</span> {text}
        </h2>
    </div>
    """, unsafe_allow_html=True)

def alterar_senha_dialog():
    """Modal para alteração de senha."""
    @st.experimental_dialog("Alterar Senha")
    def dialog():
        with st.form("new_pass"):
            nova = st.text_input("Nova Senha", type="password")
            if st.form_submit_button("Salvar"):
                users = auth.carregar_usuarios()
                users[st.session_state['usuario_ativo']] = auth.hash_senha(nova)
                auth.salvar_usuarios(users)
                st.success("Senha alterada!")
                st.rerun()
    dialog()





# --- AUXILIARES VISUAIS & UI ---
def section_title(icon, text):
    """Renderiza um título de seção com espaçamento e estilo corporativo."""
    st.markdown(f"""
    <div style="margin-top: 20px; margin-bottom: 10px; display: flex; align-items: center; gap: 8px;">
        <span class='material-symbols-outlined' style='font-size: 24px; color: #fafafa;'>{icon}</span>
        <span style='font-size: 18px; font-weight: 600; color: #fafafa;'>{text}</span>
    </div>
    """, unsafe_allow_html=True)

def main_header(icon, text):
    """Cabeçalho principal da página."""
    st.markdown(f"""
    <div style="border-bottom: 1px solid #ddd; padding-bottom: 10px; margin-bottom: 20px;">
        <h2 style='display: flex; align-items: center; gap: 10px; margin: 0; font-size: 26px;'>
            <span class='material-symbols-outlined' style='font-size: 32px;'>{icon}</span> {text}
        </h2>
    </div>
    """, unsafe_allow_html=True)

# --- MODAIS E DIALOGS (Lógica preservada, ajuste visual de textos) ---
@st.dialog("Campos em Branco")
def confirmar_salvamento_incompleto(novo_registro):
    st.warning("Alguns campos do formulário não foram preenchidos.")
    st.write("Deseja salvar o registro assim mesmo?")
    
    col_sim, col_nao = st.columns(2)
    
    if col_sim.button("Sim, Salvar", use_container_width=True, type="primary"):
        st.session_state['db_formularios'].append(novo_registro)
        utils.salvar_dados_locais(st.session_state['db_formularios'])
        st.session_state['form_id'] += 1
        st.session_state['sucesso_salvamento'] = True 
        
        keys_to_clear = [k for k in st.session_state.keys() if k.startswith("resp_") or k.startswith("nome_foto_")]
        for k in keys_to_clear: del st.session_state[k]
        st.rerun()
    
    if col_nao.button("Não, Cancelar", use_container_width=True):
        st.rerun()

@st.dialog("Confirmar Exclusão")
def confirmar_exclusao_dialog(indices_alvo=None, tipo="item"):
    """
    indices_alvo: Lista de índices (inteiros) para remover do db_formularios.
    tipo: 'item' (remove indices especificos) ou 'tudo' (limpa o banco).
    """
    st.markdown("### Ação Irreversível")
    st.warning("Você está prestes a remover registros permanentemente.")
    
    if indices_alvo and len(indices_alvo) > 1:
        st.info(f"Quantidade de itens selecionados para exclusão: {len(indices_alvo)}")
    
    senha = st.text_input("Digite sua senha para confirmar", type="password")
    
    col_confirm, col_cancel = st.columns(2)
    if col_confirm.button("Confirmar Exclusão", type="primary", use_container_width=True):
        u_db = auth.carregar_usuarios()
        hash_armazenado = u_db.get(st.session_state['usuario_ativo'])
        
        valido, _ = auth.verificar_senha(senha, hash_armazenado)
        
        if valido:
            if tipo == "tudo":
                st.session_state['db_formularios'] = []
            elif indices_alvo:
                # Remove itens de trás para frente
                for i in sorted(indices_alvo, reverse=True):
                    if 0 <= i < len(st.session_state['db_formularios']):
                        st.session_state['db_formularios'].pop(i)
            
            utils.salvar_dados_locais(st.session_state['db_formularios'])
            st.rerun()
        else: st.error("Senha incorreta.")
    
    if col_cancel.button("Cancelar", use_container_width=True):
        st.rerun()

@st.dialog("Excluir Usuário")
def excluir_usuario_dialog(nome_usuario):
    st.error(f"Remover acesso do técnico: {nome_usuario}?")
    senha_admin = st.text_input("Senha de Administrador", type="password")
    if st.button("Confirmar Exclusão", type="primary", use_container_width=True):
        admin_hash = auth.carregar_usuarios().get("Admin")
        valido, _ = auth.verificar_senha(senha_admin, admin_hash)
        if valido:
            if auth.excluir_usuario(nome_usuario):
                st.success("Usuário removido.")
                st.rerun()
            else: st.error("Erro ao remover usuário.")
        else: st.error("Senha incorreta.")

@st.dialog("Exclusão Permanente de Arquivo")
def excluir_arquivo_permanente_dialog(caminho_arquivo):
    st.warning(f"Excluir arquivo físico: {caminho_arquivo}")
    st.caption("Esta ação não pode ser desfeita.")
    senha = st.text_input("Senha de Administrador", type="password")
    if st.button("Confirmar Exclusão", type="primary", use_container_width=True):
        admin_db = auth.carregar_usuarios()
        admin_hash = admin_db.get("Admin")
        valido, _ = auth.verificar_senha(senha, admin_hash)
        if valido:
            try:
                if os.path.exists(caminho_arquivo):
                    os.remove(caminho_arquivo)
                    st.success("Arquivo excluído.")
                    import time; time.sleep(1)
                    st.rerun()
                else: st.error("Arquivo não encontrado.")
            except Exception as e: st.error(f"Erro: {e}")
        else: st.error("Senha incorreta.")

@st.dialog("Alterar Senha")
def alterar_senha_dialog():
    usuario = st.session_state['usuario_ativo']
    st.markdown(f"Alterar credenciais para: **{usuario}**")
    senha_atual = st.text_input("Senha Atual", type="password")
    nova_senha = st.text_input("Nova Senha", type="password")
    confirmar_senha = st.text_input("Confirmar Nova Senha", type="password")
    if st.button("Atualizar", type="primary", use_container_width=True):
        if not senha_atual or not nova_senha: st.error("Preencha todos os campos.")
        elif nova_senha != confirmar_senha: st.error("Senhas não coincidem.")
        else:
            sucesso = auth.alterar_senha(usuario, senha_atual, nova_senha)
            if sucesso: st.success("Senha atualizada!")
            else: st.error("Senha atual incorreta.")

# --- PÁGINAS DO SISTEMA ---

def render_configurar_modelo():
    main_header("tune", "Gerenciamento de Modelo")
    
    # Seção: Status Atual
    with st.container(border=True):
        section_title("info", "Status da Configuração")
        col_stat1, col_stat2 = st.columns([3, 1])
        with col_stat1:
            st.markdown(f"Origem do Modelo: **{st.session_state.get('origem_modelo', 'Padrão')}**")
            st.caption("Define a estrutura de campos e abas do formulário.")
        
        with col_stat2:
            if st.session_state.get('origem_modelo') == "Pessoal":
                if st.button("Restaurar Padrão", use_container_width=True):
                    path = utils.get_user_template_path()
                    if os.path.exists(path): os.remove(path)
                    utils.carregar_modelo_atual()
                    st.rerun()

    # Seção: Upload
    with st.container(border=True):
        section_title("upload_file", "Carregar Novo Modelo")
        st.markdown("Suba um arquivo Excel (.xlsx) para personalizar os campos de coleta.")
        
        arq = st.file_uploader("Selecionar arquivo", type=["xlsx"], label_visibility="collapsed")
        
        if arq:
            path = utils.get_user_template_path()
            with open(path, "wb") as f: f.write(arq.getbuffer())
            st.success("Modelo personalizado aplicado com sucesso!")
            utils.carregar_modelo_atual()
            st.rerun()

def render_preenchimento():
    # CSS para limpar inputs desabilitados e ajustes de UI
    st.markdown("""
        <style>
        div[data-baseweb="select"] input { readonly: readonly; pointer-events: none; }
        .stSlider { padding-bottom: 20px; }
        </style>
        """, unsafe_allow_html=True)
    
    main_header("edit_document", "Registro de Equipamento")
    
    # Init Session States (Mantém valores ao trocar de aba se não salvou)
    if 'loc_uc' not in st.session_state: st.session_state['loc_uc'] = ""
    if 'loc_pav' not in st.session_state: st.session_state['loc_pav'] = ""
    if 'loc_amb' not in st.session_state: st.session_state['loc_amb'] = ""
    if 'loc_pred' not in st.session_state: st.session_state['loc_pred'] = ""
    if 'fotos_temp' not in st.session_state: st.session_state['fotos_temp'] = []
    
    # Feedback de sucesso
    if 'sucesso_salvamento' in st.session_state and st.session_state['sucesso_salvamento']:
        st.success("Registro salvo com sucesso.")
        st.session_state['sucesso_salvamento'] = False 

    if 'step_atual' not in st.session_state: st.session_state['step_atual'] = 0
    
    if 'estrutura_modelo' in st.session_state and st.session_state['estrutura_modelo']:
        
        # --- BLOC 1: LOCALIZAÇÃO (PERSISTENTE) ---
        with st.container(border=True):
            section_title("location_on", "Dados de Localização")
            col_l1, col_l2 = st.columns(2)
            st.session_state['loc_uc'] = col_l1.text_input("Unidade Consumidora *", value=st.session_state['loc_uc'])
            st.session_state['loc_pav'] = col_l2.text_input("Pavimento *", value=st.session_state['loc_pav'])
            col_l3, col_l4 = st.columns(2)
            st.session_state['loc_amb'] = col_l3.text_input("Ambiente *", value=st.session_state['loc_amb'])
            st.session_state['loc_pred'] = col_l4.text_input("Prédio/Bloco (Opcional)", value=st.session_state['loc_pred'])

        # --- BLOC 2: SELEÇÃO DO TIPO ---
        st.markdown("<br>", unsafe_allow_html=True)
        tipo_opcoes = list(st.session_state['estrutura_modelo'].keys())
        
        default_tipo = tipo_opcoes[0] if tipo_opcoes else None
        tipo = st.pills("Selecione o Tipo de Equipamento", options=tipo_opcoes, default=default_tipo, selection_mode="single")

        if not tipo and tipo_opcoes: tipo = tipo_opcoes[0]

        if tipo:
            todos_campos = st.session_state['estrutura_modelo'][tipo]
            campos_reservados = [
                "Nome da Unidade Consumidora", "Pavimento", "Ambiente", 
                "Código do Prédio/Bloco", "Código de Instalação", "Local de instalação"
            ]
            campos_tecnicos = [c for c in todos_campos if c['nome'] not in campos_reservados]
            respostas = {}

            # --- BLOC 3: FORMULÁRIO TÉCNICO DINÂMICO ---
            with st.form(key=f"form_{st.session_state['form_id']}", border=True):
                section_title("description", "Especificações Técnicas")
                
                cols = st.columns(2)
                for i, c in enumerate(campos_tecnicos):
                    target = cols[i % 2]
                    key_name = f"resp_{c['nome']}"
                    default_val = st.session_state.get(key_name, "")
                    
                    # --- LÓGICA DE RENDERIZAÇÃO DOS TIPOS ---
                    
                    # TIPO 1: SLIDER (Lista de Números + Formato Numérico)
                    if c['tipo'] == 'slider':
                        try:
                            opcoes_nums = sorted([float(x) for x in c['opcoes'] if x and str(x).strip() != ''])
                            if opcoes_nums:
                                min_v = opcoes_nums[0]
                                max_v = opcoes_nums[-1]
                                # Define valor padrão seguro dentro do range
                                val_safe = float(default_val) if default_val and min_v <= float(default_val) <= max_v else min_v
                                respostas[c['nome']] = target.slider(c['nome'], min_value=min_v, max_value=max_v, value=val_safe)
                            else:
                                respostas[c['nome']] = target.text_input(c['nome'], value=str(default_val))
                        except:
                            respostas[c['nome']] = target.text_input(c['nome'], value=str(default_val))

                    # TIPO 2: NUMBER INPUT (Formato numérico sem lista)
                    elif c['tipo'] == 'numero':
                        try:
                            val_float = float(default_val) if default_val else 0.0
                            respostas[c['nome']] = target.number_input(c['nome'], value=val_float, step=1.0)
                        except:
                             respostas[c['nome']] = target.number_input(c['nome'], value=0.0)

                    # TIPO 3: SELEÇÃO ABERTA (Lista + Campo de Digitação)
                    # Exibe Pills e um Text Input. A lógica prioriza o texto se preenchido.
                    elif c['tipo'] == 'selecao_aberta':
                        target.markdown(f"**{c['nome']}**")
                        cont = target.container(border=True)
                        # Pills
                        sel_pill = cont.pills("Opções", options=c['opcoes'], selection_mode="single", key=f"pill_{c['nome']}_{st.session_state['form_id']}", label_visibility="collapsed")
                        # Texto
                        sel_text = cont.text_input("Ou digite outro valor:", key=f"txt_{c['nome']}_{st.session_state['form_id']}")
                        
                        # Decisão final: Texto ganha se existir, senão Pill
                        respostas[c['nome']] = sel_text if sel_text else (sel_pill if sel_pill else "")

                    # TIPO 4: SELEÇÃO PADRÃO (Pills)
                    elif c['tipo'] == 'selecao':
                        val_sel = default_val if default_val in c['opcoes'] else None
                        respostas[c['nome']] = target.pills(c['nome'], options=c['opcoes'], default=val_sel, selection_mode="single")

                    # TIPO 5: TEXTO (Geral)
                    else:
                        respostas[c['nome']] = target.text_input(c['nome'], value=str(default_val))
                
                st.markdown("---")
                
                # AÇÕES
                c_act_1, c_act_2, c_act_3 = st.columns(3)
                btn_novo_equip = c_act_1.form_submit_button("Salvar e Adicionar Item")
                btn_novo_amb = c_act_2.form_submit_button("Salvar e Mudar Ambiente")
                btn_salvar_full = c_act_3.form_submit_button("Salvar e Finalizar", type="primary")

            # --- BLOC 4: FOTOS ---
            with st.container(border=True):
                section_title("cloud_upload", "Registro Fotográfico")
                col_u1, col_u2 = st.columns([3, 1])
                foto_upl = col_u1.file_uploader("Selecionar imagem", type=['png', 'jpg', 'jpeg'], key="uploader_galeria", label_visibility="collapsed")
                
                col_nome, col_add = st.columns([3, 1])
                nome_foto_atual = col_nome.text_input("Descrição da Imagem", key="input_nome_foto")
                col_add.markdown("<div style='height: 28px'></div>", unsafe_allow_html=True)
                
                if col_add.button("Anexar Imagem", use_container_width=True):
                    if foto_upl:
                        st.session_state['fotos_temp'].append({
                            "arquivo": foto_upl,
                            "nome": nome_foto_atual if nome_foto_atual else f"Foto {len(st.session_state['fotos_temp'])+1}",
                            "origem": "upload"
                        })
                        st.success("Imagem anexada.")
                        st.rerun()

                if st.session_state['fotos_temp']:
                    st.markdown("---")
                    for idx, item in enumerate(st.session_state['fotos_temp']):
                        c1, c2, c3 = st.columns([0.1, 0.7, 0.2])
                        c1.image(item['arquivo'], width=60)
                        c2.markdown(f"**{item['nome']}**")
                        if c3.button("Remover", key=f"rm_foto_{idx}"):
                            st.session_state['fotos_temp'].pop(idx)
                            st.rerun()

            # --- PROCESSAMENTO DOS BOTÕES ---
            action_type = None
            if btn_novo_equip: action_type = "novo_equip"
            elif btn_novo_amb: action_type = "novo_amb"
            elif btn_salvar_full: action_type = "full"

            if action_type:
                loc_data = {
                    "Nome da Unidade Consumidora": st.session_state['loc_uc'],
                    "Pavimento": st.session_state['loc_pav'],
                    "Ambiente": st.session_state['loc_amb'],
                    "Código do Prédio/Bloco": st.session_state['loc_pred']
                }
                if not loc_data["Nome da Unidade Consumidora"] or not loc_data["Pavimento"] or not loc_data["Ambiente"]:
                    st.error("Campos obrigatórios de localização não preenchidos.")
                else:
                    views.processar_salvamento(loc_data, tipo, respostas, st.session_state['fotos_temp'], action_type)
        else:
            st.info("Selecione um tipo de equipamento.")
    else:
        st.warning("Modelo de dados não carregado.")

def processar_salvamento(loc_data, tipo, respostas, lista_fotos_temp, action_type):
    uc = loc_data["Nome da Unidade Consumidora"]
    dados_completos = loc_data.copy()
    dados_completos.update(respostas)

    meta_fotos = utils.salvar_fotos_local(lista_fotos_temp, uc)
    
    novo_registro = {
        "cod_instalacao": uc, 
        "tipo_equipamento": tipo, 
        "data_hora": utils.get_data_hora_br().strftime("%d/%m/%Y %H:%M:%S"), 
        "dados": dados_completos,
        "fotos": meta_fotos
    }
    
    st.session_state['db_formularios'].append(novo_registro)
    utils.salvar_dados_locais(st.session_state['db_formularios'])
    st.session_state['form_id'] += 1
    st.session_state['sucesso_salvamento'] = True 
    
    # Limpeza Técnica
    keys_tecnicas = [k for k in st.session_state.keys() if k.startswith("resp_")]
    for k in keys_tecnicas: del st.session_state[k]
    st.session_state['fotos_temp'] = [] 

    # Limpeza Contextual
    if action_type == "novo_amb":
        st.session_state['loc_pav'] = ""
        st.session_state['loc_amb'] = ""
        st.session_state['loc_pred'] = ""
    elif action_type == "full":
        st.session_state['loc_uc'] = ""
        st.session_state['loc_pav'] = ""
        st.session_state['loc_amb'] = ""
        st.session_state['loc_pred'] = ""

    st.rerun()

def render_exportar_listar():
    main_header("table_view", "Gerenciamento de Levantamentos")
    
    registros = st.session_state['db_formularios']
    
    if not registros:
        st.info("Nenhum registro encontrado no banco de dados local.")
        return

    # Painel de Controle Geral
    with st.container(border=True):
        c_tot, c_act = st.columns([0.7, 0.3])
        c_tot.metric("Total de Equipamentos Coletados", len(registros))
        if c_act.button("Excluir Tudo", type="primary", use_container_width=True, icon=":material/delete_forever:"):
            confirmar_exclusao_dialog(indices_alvo=None, tipo="tudo")

    st.markdown("### Levantamentos por Unidade")

    # Agrupamento
    grupos_uc = defaultdict(list)
    for idx, item in enumerate(registros):
        uc_nome = item.get('cod_instalacao') or item.get('dados', {}).get('Nome da Unidade Consumidora', 'UC Indefinida')
        grupos_uc[uc_nome].append((idx, item))

    # Listagem Hierárquica
    for uc, lista_itens in grupos_uc.items():
        qtd_equipamentos = len(lista_itens)
        qtd_fotos_total = sum(len(i[1].get('fotos', [])) for i in lista_itens)
        
        datas = [i[1].get('data_hora', '-') for i in lista_itens]
        data_resumo = datas[0].split()[0] if datas else "-"

        # Cabeçalho do Expander (Texto Limpo)
        expander_label = f"{uc}  |  {data_resumo}  |  {qtd_equipamentos} iten(s)"

        with st.expander(expander_label, expanded=False):
            # Header Interno
            c_h1, c_h2, c_h3, c_h4 = st.columns([3, 2, 2, 3])
            c_h1.caption("Unidade Consumidora")
            c_h1.markdown(f"**{uc}**")
            
            c_h2.caption("Data Base")
            c_h2.markdown(f"**{data_resumo}**")
            
            c_h3.caption("Fotos Totais")
            c_h3.markdown(f"**{qtd_fotos_total}**")
            
            c_h4.caption("Ações do Grupo")
            indices_grupo = [i[0] for i in lista_itens]
            if c_h4.button("Excluir Levantamento Completo", key=f"del_grp_{uc}", use_container_width=True, icon=":material/folder_delete:"):
                confirmar_exclusao_dialog(indices_alvo=indices_grupo, tipo="item")

            st.divider()
            
            # Tabela de Itens
            for real_idx, item in lista_itens:
                dados = item.get('dados', {})
                tipo = item.get('tipo_equipamento', 'Equipamento')
                data_hora = item.get('data_hora', '-')
                fotos = item.get('fotos', [])
                pav = dados.get('Pavimento', '-')
                amb = dados.get('Ambiente', '-')

                with st.container(border=True):
                    row1, row2, row3 = st.columns([0.4, 0.4, 0.2])
                    
                    with row1:
                        st.markdown(f"**{tipo}**")
                        st.caption(f"Local: {pav} > {amb}")
                    
                    with row2:
                        st.caption(f"Registro: {data_hora}")
                        if fotos:
                            st.markdown(f"📎 {len(fotos)} anexo(s)")
                    
                    with row3:
                        # Alinhamento vertical para botão
                        st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                        if st.button("Excluir", key=f"del_item_{real_idx}", icon=":material/delete:", use_container_width=True):
                            confirmar_exclusao_dialog(indices_alvo=[real_idx], tipo="item")
                    
                    # Expander de fotos discreto
                    if fotos:
                        with st.popover("Visualizar Anexos"):
                            cols_foto = st.columns(3)
                            for idx_f, f in enumerate(fotos):
                                with cols_foto[idx_f % 3]:
                                    st.image(f['caminho_fisico'], caption=f['nome_exportacao'], use_container_width=True)

    st.markdown("---")
    
    # Rodapé: Exportação
    main_header("download", "Exportação de Dados")
    
    zip_data = utils.gerar_zip_exportacao(st.session_state['db_formularios'])
    
    col_dl, col_email = st.columns(2)
    with col_dl:
        if zip_data:
            st.download_button(
                "Baixar Pacote Completo (.zip)", 
                data=zip_data, 
                file_name="levantamento_poup.zip", 
                mime="application/zip",
                use_container_width=True, 
                type="primary",
                icon=":material/archive:"
            )
        else:
            st.button("Baixar Pacote Completo", disabled=True, use_container_width=True)
            
    with col_email:
        with st.form("form_email_envio"):
            c_e1, c_e2 = st.columns([0.7, 0.3])
            email_dest = c_e1.text_input("Email", placeholder="usuario@empresa.com", label_visibility="collapsed")
            btn_env = c_e2.form_submit_button("Enviar", icon=":material/send:", use_container_width=True)
            
            if btn_env:
                if email_dest and zip_data and utils.enviar_email(zip_data, email_dest, is_zip=True):
                    st.success("Relatório enviado!")
                else:
                    st.error("Erro ao enviar ou email inválido.")

def render_admin_panel():
    main_header("admin_panel_settings", "Painel Administrativo")
    
    tab_users, tab_audit, tab_master = st.tabs(["Equipe Técnica", "Auditoria de Dados", "Modelo de Dados"])
    
    with tab_users:
        with st.container(border=True):
            section_title("person_add", "Cadastrar Novo Técnico")
            with st.form("novo_user_form", clear_on_submit=True):
                c1, c2, c3 = st.columns([0.4, 0.4, 0.2])
                new_u = c1.text_input("Usuário")
                new_p = c2.text_input("Senha", type="password")
                c3.markdown("<div style='height: 28px'></div>", unsafe_allow_html=True)
                if c3.form_submit_button("Adicionar", use_container_width=True, type="primary"):
                    if new_u and new_p:
                        d = auth.carregar_usuarios()
                        d[new_u] = auth.hash_senha(new_p) 
                        auth.salvar_usuarios(d)
                        st.success("Cadastrado com sucesso!")
                    else:
                        st.error("Dados incompletos.")

        st.markdown("<br>", unsafe_allow_html=True)
        section_title("group", "Técnicos Ativos")
        
        users = auth.carregar_usuarios()
        if users:
            for nome, senha in users.items():
                with st.container(border=True):
                    c_n, c_a = st.columns([0.8, 0.2])
                    c_n.markdown(f"**{nome}**")
                    if nome != "Admin": 
                        if c_a.button("Remover", key=f"del_user_{nome}", use_container_width=True):
                            excluir_usuario_dialog(nome)
                    else:
                        c_a.markdown("*Sistema*")

    with tab_audit:
        section_title("history", "Histórico de Arquivos Locais")
        arquivos = sorted([f for f in os.listdir(".") if f.startswith("dados_") and f.endswith(".json")])
        
        if arquivos:
            sel = st.selectbox("Selecione o arquivo de backup:", arquivos)
            dados_rec = utils.carregar_dados_locais(path_especifico=sel)
            
            # Métricas
            cm1, cm2 = st.columns(2)
            cm1.metric("Registros", len(dados_rec))
            cm2.metric("Tamanho", f"{(os.path.getsize(sel)/1024):.2f} KB")
            
            # Preview
            st.caption("Visualização Rápida dos Dados")
            df = pd.DataFrame([{"UC": d.get('cod_instalacao'), "Tipo": d.get('tipo_equipamento'), "Data": d.get('data_hora')} for d in dados_rec])
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Ações
            c_act1, c_act2 = st.columns(2)
            rec_excel = utils.exportar_para_excel(dados_rec)
            if rec_excel:
                 c_act1.download_button("Baixar Planilha (Excel)", data=rec_excel, file_name=f"backup_{sel}.xlsx", use_container_width=True, icon=":material/download:")

            if c_act2.button("Apagar Arquivo do Servidor", use_container_width=True, icon=":material/delete_forever:"):
                excluir_arquivo_permanente_dialog(sel)
        else:
            st.info("Nenhum arquivo de backup encontrado.")
    
    with tab_master:
        with st.container(border=True):
            section_title("settings_system_daydream", "Modelo Padrão do Sistema")
            st.warning("A substituição deste arquivo afeta todos os novos levantamentos iniciados sem modelo pessoal.")
            
            mestre = st.file_uploader("Substituir 'Levantamento_Base.xlsx'", type=["xlsx"])
            if mestre:
                with open(utils.PLANILHA_PADRAO_ADMIN, "wb") as f: f.write(mestre.getbuffer())
                st.success("Modelo Padrão atualizado com sucesso!")


# --- AUXILIARES VISUAIS & UI ---
def section_title(icon, text):
    """Renderiza um título de seção com espaçamento e estilo corporativo."""
    st.markdown(f"""
    <div style="margin-top: 20px; margin-bottom: 10px; display: flex; align-items: center; gap: 8px;">
        <span class='material-symbols-outlined' style='font-size: 24px; color: #fafafa;'>{icon}</span>
        <span style='font-size: 18px; font-weight: 600; color: #fafafa;'>{text}</span>
    </div>
    """, unsafe_allow_html=True)

def main_header(icon, text):
    """Cabeçalho principal da página."""
    st.markdown(f"""
    <div style="border-bottom: 1px solid #ddd; padding-bottom: 10px; margin-bottom: 20px;">
        <h2 style='display: flex; align-items: center; gap: 10px; margin: 0; font-size: 26px;'>
            <span class='material-symbols-outlined' style='font-size: 32px;'>{icon}</span> {text}
        </h2>
    </div>
    """, unsafe_allow_html=True)

# --- CALLBACKS PARA CAMPOS MÚTUOS ---
def clear_text_input(key_text, key_pills):
    """Callback: Se selecionou Pills, limpa o Texto."""
    if st.session_state.get(key_pills):
        st.session_state[key_text] = ""

def clear_pills_input(key_text, key_pills):
    """Callback: Se digitou Texto, limpa Pills."""
    if st.session_state.get(key_text):
        st.session_state[key_pills] = None

# --- RENDERIZAÇÃO DINÂMICA ---
def renderizar_formulario_dinamico(sheet_name):
    """Renderiza campos baseado puramente no JSON de estrutura do Excel."""
    estrutura = st.session_state.get("modelo_excel_structure", {})
    if sheet_name not in estrutura:
        st.error(f"Modelo não encontrado para a aba: {sheet_name}")
        return {}

    dados_capturados = {}
    campos = estrutura[sheet_name]
    
    # Cria colunas para organizar o layout (Grid)
    # Agrupa campos em linhas de 3 ou 4 para não ficar uma lista vertical infinita
    cols_layout = st.columns(3)
    col_counter = 0

    for campo in campos:
        # Pula campos informativos gerais que geralmente ficam no final ou são obs
        if campo['header'].lower() in ['informações gerais', 'obs', 'observações']:
            continue

        with cols_layout[col_counter % 3]:
            key_base = f"{sheet_name}_{campo['header']}"
            val = None
            
            label = campo['header']
            options = campo.get('options', [])
            allow_custom = campo.get('allow_custom', False)
            tipo_st = campo.get('tipo_streamlit', 'text_input')
            
            # --- CASO 1: LISTA (PILLS) ---
            if tipo_st == "pills" and options:
                key_pills = f"{key_base}_pills"
                key_text = f"{key_base}_text"
                
                # Se permite customização (Erro no Excel = False)
                if allow_custom:
                    # Exibe Pills
                    sel_pill = st.pills(
                        label, 
                        options=options, 
                        key=key_pills, 
                        selection_mode="single",
                        on_change=clear_text_input,
                        args=(key_text, key_pills)
                    )
                    # Exibe Input de Texto logo abaixo (Outro)
                    sel_text = st.text_input(
                        "Ou digite outro:", 
                        key=key_text,
                        on_change=clear_pills_input,
                        args=(key_text, key_pills)
                    )
                    
                    # Lógica de decisão final
                    val = sel_text if sel_text else sel_pill

                else:
                    # Lista Estrita (apenas Pills)
                    val = st.pills(label, options=options, key=key_base, selection_mode="single")

            # --- CASO 2: SLIDER (Numérico com Range) ---
            elif tipo_st == "slider":
                min_v = campo.get('min_val', 0.0)
                max_v = campo.get('max_val', 100.0)
                val = st.slider(label, min_value=min_v, max_value=max_v, key=key_base)

            # --- CASO 3: NUMBER INPUT ---
            elif tipo_st == "number_input":
                val = st.number_input(label, step=1.0, key=key_base)

            # --- CASO 4: TEXTO GERAL ---
            else:
                val = st.text_input(label, key=key_base)
            
            # Armazena dado
            dados_capturados[campo['header']] = val
            
        col_counter += 1

    # Campo de Observações Gerais (sempre útil no final)
    st.divider()
    obs = st.text_area("Informações Gerais / Observações", key=f"{sheet_name}_obs_final")
    dados_capturados["Informações Gerais"] = obs
    
    return dados_capturados

# --- TELAS PRINCIPAIS ---

def preenchimento_formulario():
    main_header("edit_document", "Novo Levantamento")
    
    if not st.session_state.get("modelo_excel_structure"):
        st.warning("Nenhum modelo carregado. Vá em 'Configurar Modelo' ou contate o Admin.")
        return

    # 1. Seleção do Tipo de Carga (Abas do Excel)
    abas_disponiveis = list(st.session_state["modelo_excel_structure"].keys())
    tipo_carga = st.selectbox("Selecione o Tipo de Equipamento/Carga", abas_disponiveis)
    
    st.divider()
    
    # 2. Renderização Dinâmica baseada no Excel
    with st.form(key="form_coleta_dados", clear_on_submit=True):
        section_title("list_alt", f"Dados: {tipo_carga}")
        
        dados = renderizar_formulario_dinamico(tipo_carga)
        
        # Upload de Fotos (Fixo, pois não depende do Excel)
        st.divider()
        section_title("photo_camera", "Registro Fotográfico")
        fotos = st.file_uploader("Anexar fotos do equipamento/ambiente", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'])
        
        c1, c2 = st.columns([1, 4])
        enviou = c1.form_submit_button("Salvar Registro", type="primary", use_container_width=True)
        
        if enviou:
            # Consolida dados
            registro_final = dados.copy()
            registro_final["tipo_equipamento"] = tipo_carga
            registro_final["data_hora"] = utils.get_data_hora_br().strftime("%Y-%m-%d %H:%M:%S")
            registro_final["usuario"] = st.session_state['usuario_ativo']
            
            # Processa fotos
            lista_fotos = []
            if fotos:
                dir_fotos = f"fotos_upload/{st.session_state['usuario_ativo']}"
                os.makedirs(dir_fotos, exist_ok=True)
                for f in fotos:
                    nome_safe = f"{utils.get_data_hora_br().strftime('%Y%m%d%H%M%S')}_{f.name}"
                    caminho = os.path.join(dir_fotos, nome_safe)
                    with open(caminho, "wb") as buffer:
                        buffer.write(f.getbuffer())
                    lista_fotos.append({"caminho_fisico": caminho, "nome_exportacao": f.name})
            
            registro_final["fotos"] = lista_fotos
            
            # Salva
            db = st.session_state['db_formularios']
            id_novo = str(len(db) + 1)
            db[id_novo] = registro_final
            utils.salvar_dados_locais(db)
            st.session_state['db_formularios'] = db
            
            st.success("Dados salvos com sucesso!")
            st.rerun()

def listar_exportar():
    main_header("table_view", "Dados Coletados")
    
    dados = st.session_state.get('db_formularios', {})
    if not dados:
        st.info("Nenhum dado coletado ainda.")
        return

    # Converte Dict para Lista
    lista_dados = list(dados.values())
    df = pd.DataFrame(lista_dados)
    
    # Filtros
    c1, c2 = st.columns(2)
    filtro_tipo = c1.multiselect("Filtrar por Tipo", df["tipo_equipamento"].unique())
    if filtro_tipo:
        df = df[df["tipo_equipamento"].isin(filtro_tipo)]
        
    st.dataframe(df, use_container_width=True)
    
    st.divider()
    section_title("download", "Exportação")
    
    c_btn1, c_btn2 = st.columns(2)
    
    # Botão Excel
    excel_file = utils.exportar_para_excel(df.to_dict('records'))
    if excel_file:
        c_btn1.download_button("Baixar Excel Completo", data=excel_file, file_name="levantamento_geral.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    
    # Botão ZIP (Com fotos)
    zip_file = utils.gerar_zip_fotos(df.to_dict('records'))
    c_btn2.download_button("Baixar Pacote Completo (.ZIP)", data=zip_file, file_name="levantamento_com_fotos.zip", mime="application/zip", use_container_width=True)

def alterar_senha_dialog():
    @st.dialog("Alterar Senha")
    def modal():
        senha_atual = st.text_input("Senha Atual", type="password")
        nova_senha = st.text_input("Nova Senha", type="password")
        confirmar = st.text_input("Confirmar Nova Senha", type="password")
        
        if st.button("Confirmar Alteração"):
            user = st.session_state['usuario_ativo']
            db_users = auth.carregar_usuarios()
            
            valido, _ = auth.verificar_senha(senha_atual, db_users[user])
            if not valido:
                st.error("Senha atual incorreta.")
                return
            
            if nova_senha != confirmar:
                st.error("As novas senhas não coincidem.")
                return
            
            db_users[user] = auth.hash_senha(nova_senha)
            auth.salvar_usuarios(db_users)
            st.success("Senha alterada com sucesso!")
            st.rerun()
    modal()

def excluir_arquivo_permanente_dialog(arquivo):
    # Função placeholder caso lógica de backup de arquivos do servidor seja necessária
    pass

def painel_admin():
    main_header("admin_panel_settings", "Painel Administrativo")
    
    tab_users, tab_master = st.tabs(["Gerenciar Usuários", "Modelo de Dados"])
    
    with tab_users:
        st.write("Usuários cadastrados:")
        users = auth.carregar_usuarios()
        for u in users:
            c1, c2 = st.columns([3, 1])
            c1.markdown(f"**{u}**")
            if u != "Admin":
                if c2.button("Excluir", key=f"del_{u}"):
                    if auth.excluir_usuario(u):
                        st.rerun()
        
        st.divider()
        with st.form("novo_user"):
            st.write("Adicionar Usuário")
            n = st.text_input("Nome")
            s = st.text_input("Senha Inicial", type="password")
            if st.form_submit_button("Criar Usuário"):
                users[n] = auth.hash_senha(s)
                auth.salvar_usuarios(users)
                st.success("Criado!")
                st.rerun()

    with tab_master:
        with st.container(border=True):
            section_title("settings_system_daydream", "Modelo Padrão do Sistema")
            st.warning("O sistema lê o arquivo 'Levantamento_Base.xlsx' para gerar os formulários.")
            st.info("Para atualizar as regras, faça upload de um novo arquivo Excel com as mesmas abas e novas validações de dados.")
            
            novo_modelo = st.file_uploader("Substituir 'Levantamento_Base.xlsx'", type=["xlsx"])
            if novo_modelo:
                with open("Levantamento_Base.xlsx", "wb") as f:
                    f.write(novo_modelo.getbuffer())
                
                # Força recarga da estrutura
                st.session_state.pop("modelo_excel_structure", None)
                utils.carregar_modelo_atual()
                st.success("Modelo atualizado! Os formulários refletirão as mudanças.")


# --- ADICIONAR NO VIEWS.PY ---

def view_configuracao_backup():
    section_title("mail", "Configuração de Backup Automático")
    st.write("Defina o e-mail que receberá o backup completo (.zip) todos os dias às 20:00.")
    
    config = utils.carregar_config_backup()
    estado = utils.carregar_estado_backup()
    
    email_atual = config.get("email", "")
    
    with st.form("backup_form"):
        novo_email = st.text_input("E-mail de Destino", value=email_atual)
        if st.form_submit_button("Salvar Configuração"):
            if "@" in novo_email and "." in novo_email:
                utils.salvar_config_backup(novo_email)
                st.success("Configuração salva!")
                st.rerun()
            else:
                st.error("E-mail inválido.")
    
    st.divider()
    c1, c2 = st.columns(2)
    c1.metric("Último Envio", estado.get("data_ultimo_envio", "Nenhum"))
    c2.metric("Status", estado.get("status", "Inativo"))





