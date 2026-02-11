import streamlit as st
import pandas as pd
import io
import json
import os
import smtplib
import zipfile
import shutil
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from openpyxl import load_workbook
from datetime import datetime, timedelta, timezone
from io import BytesIO
from openpyxl import load_workbook
import io


# --- CONSTANTES ---
ARQUIVO_PREFS_CLIENTES = "backup_prefs_clientes.json"

# --- PERSISTÊNCIA PREFERÊNCIAS DO CLIENTE ---

def carregar_prefs_todos_clientes():
    """Carrega as preferências de backup de todos os clientes."""
    if os.path.exists(ARQUIVO_PREFS_CLIENTES):
        try:
            with open(ARQUIVO_PREFS_CLIENTES, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def salvar_prefs_cliente(usuario, email, ativo):
    """Salva a preferência de um cliente específico."""
    prefs = carregar_prefs_todos_clientes()
    
    # Preserva a data do último envio se já existir
    ultimo_envio = None
    if usuario in prefs:
        ultimo_envio = prefs[usuario].get("ultimo_envio")

    prefs[usuario] = {
        "email": email,
        "ativo": ativo,
        "ultimo_envio": ultimo_envio
    }
    
    with open(ARQUIVO_PREFS_CLIENTES, "w") as f:
        json.dump(prefs, f, indent=4)


def _coletar_fotos_de_registros(registros):
    """Retorna caminhos de fotos válidos a partir de uma lista de registros."""
    fotos = set()
    for registro in registros:
        for foto in registro.get("fotos", []):
            caminho_fisico = foto.get("caminho_fisico")
            if caminho_fisico and os.path.exists(caminho_fisico):
                fotos.add(caminho_fisico)
    return fotos

def atualizar_status_envio_cliente(usuario, data_envio):
    """Atualiza a flag de data do último envio para o cliente."""
    prefs = carregar_prefs_todos_clientes()
    if usuario in prefs:
        prefs[usuario]["ultimo_envio"] = data_envio
        with open(ARQUIVO_PREFS_CLIENTES, "w") as f:
            json.dump(prefs, f, indent=4)

# --- GERAÇÃO DE ZIP ---

def gerar_zip_usuario(usuario):
    """
    Gera um ZIP contendo apenas os dados do usuário especificado.
    Assume que os arquivos de dados possuem o nome do usuário ou estrutura identificável.
    """
    try:
        dados_path = get_user_data_path(usuario)
        if not dados_path or not os.path.exists(dados_path):
            return None

        registros = carregar_dados_locais(dados_path)
        if not registros:
            return None

        nome_zip = f"backup_{usuario}_{datetime.now().strftime('%Y%m%d')}.zip"
        template_path = get_user_template_path(usuario)
        fotos_usuario = _coletar_fotos_de_registros(registros)

        with zipfile.ZipFile(nome_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(dados_path)

            if template_path and os.path.exists(template_path):
                zipf.write(template_path)

            for caminho_foto in fotos_usuario:
                nome_foto = os.path.basename(caminho_foto)
                zipf.write(caminho_foto, arcname=os.path.join("fotos", nome_foto))

        return nome_zip
    except Exception as e:
        print(f"[Erro ZIP Usuario] Falha ao gerar ZIP para {usuario}: {e}")
        return None


def analisar_modelo_excel(file_content):
    try:
        buffer = io.BytesIO(file_content) if isinstance(file_content, bytes) else io.BytesIO(file_content.getvalue())
        wb = load_workbook(buffer, data_only=True)
        estrutura = {}
        
        for sheet_name in wb.sheetnames:
            sheet = wb[sheet_name]
            headers = []
            
            # Percorrer colunas pelo índice (1 até max_column) para garantir que lemos tudo
            for col_idx in range(1, sheet.max_column + 1):
                c1 = sheet.cell(row=1, column=col_idx)
                c2 = sheet.cell(row=2, column=col_idx)
                
                # Lógica para definir o Nome do Campo:
                # 1. Se Row 2 tem valor, usa Row 2 (ex: "Dias/Mês").
                # 2. Se Row 2 vazio, usa Row 1 (ex: "Observações").
                # 3. Concatena se necessário (opcional, aqui priorizamos Row 2 para casos de subtítulos)
                nome_campo = None
                if c2.value:
                    nome_campo = str(c2.value)
                elif c1.value:
                    nome_campo = str(c1.value)
                
                # Se encontrou um nome válido, processa o tipo
                if nome_campo:
                    # Definição padrão
                    tipo_detectado = "texto"
                    opcoes = []
                    
                    # Célula de amostra de dados (Linha 3, pois 1 e 2 são cabeçalhos)
                    # Se não houver dados na linha 3, usamos a formatação dela mesmo assim
                    sample_cell = sheet.cell(row=3, column=col_idx)
                    fmt_code = sample_cell.number_format
                    
                    # --- DETECÇÃO VIA VALIDAÇÃO DE DADOS (LISTAS) ---
                    has_validation = False
                    for dv in sheet.data_validations.dataValidation:
                        # Verifica se a validação atinge a coluna atual
                        # Nota: A verificação de range 'sqref' simples pode falhar em ranges complexos,
                        # mas funciona para colunas inteiras ou intervalos comuns.
                        ranges = dv.sqref
                        # Lógica simplificada: Se a coluna (letra) está na validação
                        if c1.column_letter in str(ranges) or c2.column_letter in str(ranges):
                            if dv.type == "list":
                                has_validation = True
                                formula = dv.formula1
                                if formula:
                                    # Limpa a formula para extrair opções (se for lista explícita)
                                    opcoes_limpas = [op.strip() for op in formula.replace('"', '').split(',')]
                                    opcoes = opcoes_limpas
                                    
                                    # Verifica se é numérico
                                    is_numeric_list = all(str(op).replace('.','',1).isdigit() for op in opcoes if op)
                                    is_numeric_fmt = any(c in str(fmt_code) for c in ['0', '#']) and str(fmt_code).lower() != 'general'
                                    
                                    # TIPO: SLIDER (Lista de Números + Formato Numérico)
                                    if is_numeric_list and is_numeric_fmt:
                                        tipo_detectado = "slider"
                                    
                                    # TIPO: SELEÇÃO ABERTA (Lista + Permite Erro/Digitação)
                                    # showErrorMessage é True por padrão. Se False, permite digitar.
                                    elif not dv.showErrorMessage:
                                        tipo_detectado = "selecao_aberta"
                                    
                                    # TIPO: PILLS (Lista Padrão)
                                    else:
                                        tipo_detectado = "selecao"

                    # --- DETECÇÃO SEM VALIDAÇÃO ---
                    if not has_validation:
                        # Se formato for numérico (ex: 0.00, #,##0) -> NUMBER_INPUT
                        if any(c in str(fmt_code) for c in ['0', '#']) and str(fmt_code).lower() != 'general':
                            tipo_detectado = "numero"
                        else:
                            tipo_detectado = "texto"

                    headers.append({
                        "nome": nome_campo, 
                        "col_letter": c1.column_letter, 
                        "tipo": tipo_detectado, 
                        "opcoes": opcoes
                    })
            
            estrutura[sheet_name] = [{"nome": h["nome"], "tipo": h["tipo"], "opcoes": h["opcoes"]} for h in headers]
            
        return estrutura
    except Exception as e:
        st.error(f"Erro ao analisar o Excel: {e}")
        return {}

# Constantes
PLANILHA_PADRAO_ADMIN = "Levantamento_Base.xlsx"
PASTA_FOTOS = "fotos_uploads"

# Garantir que a pasta de fotos existe
if not os.path.exists(PASTA_FOTOS):
    os.makedirs(PASTA_FOTOS)

# DATAS E CAMINHOS
def get_data_hora_br():
    fuso_br = timezone(timedelta(hours=-3))
    return datetime.now(fuso_br)

def get_user_data_path(nome_usuario=None):
    user = nome_usuario if nome_usuario else st.session_state.get('usuario_ativo')
    if user:
        nome_limpo = "".join(filter(str.isalnum, user))
        return f"dados_{nome_limpo}.json"
    return None

def get_user_template_path(nome_usuario=None):
    user = nome_usuario if nome_usuario else st.session_state.get('usuario_ativo')
    if user:
        nome_limpo = "".join(filter(str.isalnum, user))
        return f"template_{nome_limpo}.xlsx"
    return None

# PERSISTÊNCIA JSON
def salvar_dados_locais(dados):
    path = get_user_data_path()
    if path:
        with open(path, "w") as f: json.dump(dados, f)

def carregar_dados_locais(path_especifico=None):
    path = path_especifico if path_especifico else get_user_data_path()
    if path and os.path.exists(path):
        with open(path, "r") as f: return json.load(f)
    return []

# LÓGICA DE FOTOS

def salvar_fotos_local(lista_fotos_obj, cod_instalacao):
    """
    Recebe uma lista de dicionários: [{'arquivo': buffer, 'nome': 'descricao'}]
    Salva no disco e retorna os metadados.
    """
    caminhos_salvos = []
    
    # Garantir pasta
    if not os.path.exists(PASTA_FOTOS):
        os.makedirs(PASTA_FOTOS)
    
    for item in lista_fotos_obj:
        arquivo = item['arquivo']
        nome_personalizado = item['nome']
        
        if arquivo:
            # Tenta pegar extensão do arquivo original, se não tiver (câmera), usa .jpg
            nome_orig = getattr(arquivo, "name", "foto_camera.jpg")
            ext = os.path.splitext(nome_orig)[1]
            if not ext: ext = ".jpg"
            
            # Limpar nome definido pelo usuário para ser seguro no Windows/Linux
            nome_limpo = "".join(x for x in nome_personalizado if x.isalnum() or x in " -_")
            if not nome_limpo: nome_limpo = "imagem_sem_nome"
            
            # Timestamp para evitar sobrescrever
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S_%f")
            
            # Nome final físico: UC_TIMESTAMP_DESCRIÇÃO.ext
            nome_arquivo_final = f"{cod_instalacao}_{timestamp}_{nome_limpo}{ext}"
            caminho_completo = os.path.join(PASTA_FOTOS, nome_arquivo_final)
            
            # Salvar bytes
            with open(caminho_completo, "wb") as f:
                f.write(arquivo.getbuffer())
            
            caminhos_salvos.append({
                "caminho_fisico": caminho_completo,
                "nome_exportacao": f"{nome_limpo}{ext}", # Nome bonito para o ZIP
                "nome_original": nome_orig
            })
            
    return caminhos_salvos

# --- FUNÇÕES AUXILIARES DE FORMATAÇÃO ---

def is_numeric_format(fmt_code):
    """Verifica se o formato da célula é numérico (não Geral ou Texto)."""
    if not fmt_code: return False
    # Formatos comuns de texto no Excel: "General", "@"
    if str(fmt_code).lower() == 'general' or fmt_code == '@':
        return False
    # Verifica se parece formato numérico (0.00, #,##0, etc)
    return any(c in str(fmt_code) for c in ['0', '#', '%', 'E+'])

def is_list_numeric(lista_opcoes):
    """Verifica se todos os itens de uma lista são convertíveis para número."""
    if not lista_opcoes: return False
    try:
        # Tenta converter tudo para float (ignora vazios)
        [float(x) for x in lista_opcoes if x and str(x).strip() != '']
        return True
    except ValueError:
        return False

# --- FUNÇÃO PRINCIPAL DE ANÁLISE ---

def analisar_modelo_excel(file_content):
    try:
        buffer = io.BytesIO(file_content) if isinstance(file_content, bytes) else io.BytesIO(file_content.getvalue())
        wb = load_workbook(buffer, data_only=True)
        estrutura = {}
        
        for sheet_name in wb.sheetnames:
            sheet = wb[sheet_name]
            headers = []
            
            # Percorrer colunas pelo índice (1 até max_column)
            for col_idx in range(1, sheet.max_column + 1):
                c1 = sheet.cell(row=1, column=col_idx)
                c2 = sheet.cell(row=2, column=col_idx)
                
                # 1. Definição do Nome do Campo (Prioriza Linha 2 se houver mesclagem)
                nome_campo = None
                if c2.value:
                    nome_campo = str(c2.value)
                elif c1.value:
                    nome_campo = str(c1.value)
                
                if nome_campo:
                    tipo_detectado = "texto" # Default
                    opcoes = []
                    
                    # 2. Célula de amostra de DADOS (Linha 3)
                    # É aqui que a validação e formatação real costumam estar
                    sample_cell = sheet.cell(row=3, column=col_idx)
                    fmt_code = sample_cell.number_format
                    
                    # --- DETECÇÃO VIA VALIDAÇÃO DE DADOS (LISTAS) ---
                    has_validation = False
                    for dv in sheet.data_validations.dataValidation:
                        # Verifica se a célula de DADOS (ex: C3) está na regra de validação
                        if sample_cell.coordinate in dv.sqref:
                            if dv.type == "list":
                                has_validation = True
                                formula = dv.formula1
                                if formula:
                                    # Limpa a formula para extrair opções (se for lista explícita)
                                    opcoes_limpas = [op.strip() for op in formula.replace('"', '').split(',')]
                                    opcoes = opcoes_limpas
                                    
                                    # Verifica subtipos
                                    numeric_list = is_list_numeric(opcoes_limpas)
                                    numeric_fmt = is_numeric_format(fmt_code)
                                    
                                    # Regra: Lista Números + Formato Numérico = SLIDER
                                    if numeric_list and numeric_fmt:
                                        tipo_detectado = "slider"
                                    
                                    # Regra: Lista + Permite erro (showErrorMessage=False) = SELEÇÃO ABERTA
                                    elif dv.showErrorMessage is False:
                                        tipo_detectado = "selecao_aberta"
                                    
                                    # Regra: Padrão = PILLS
                                    else:
                                        tipo_detectado = "selecao"
                                break # Achou a validação desta coluna, para de buscar

                    # --- DETECÇÃO SEM VALIDAÇÃO ---
                    if not has_validation:
                        # Se formato for numérico -> NUMBER_INPUT
                        if is_numeric_format(fmt_code):
                            tipo_detectado = "numero"
                        else:
                            tipo_detectado = "texto"

                    headers.append({
                        "nome": nome_campo, 
                        "col_letter": c1.column_letter, 
                        "tipo": tipo_detectado, 
                        "opcoes": opcoes
                    })
            
            estrutura[sheet_name] = [{"nome": h["nome"], "tipo": h["tipo"], "opcoes": h["opcoes"]} for h in headers]
            
        return estrutura
    except Exception as e:
        st.error(f"Erro ao analisar o Excel: {e}")
        return {}

# utils.py

# ... (imports e funções auxiliares is_numeric_format / is_list_numeric mantidas) ...

def analisar_modelo_excel(file_content):
    try:
        buffer = io.BytesIO(file_content) if isinstance(file_content, bytes) else io.BytesIO(file_content.getvalue())
        wb = load_workbook(buffer, data_only=True)
        estrutura = {}
        
        for sheet_name in wb.sheetnames:
            sheet = wb[sheet_name]
            headers = []
            
            # Percorrer colunas pelo índice
            for col_idx in range(1, sheet.max_column + 1):
                c1 = sheet.cell(row=1, column=col_idx)
                c2 = sheet.cell(row=2, column=col_idx)
                
                # Definição do Nome (Lógica de Mesclagem mantida)
                nome_campo = None
                if c2.value:
                    nome_campo = str(c2.value)
                elif c1.value:
                    nome_campo = str(c1.value)
                
                if nome_campo:
                    tipo_detectado = "texto" # Default
                    opcoes = []
                    
                    # Célula de amostra de DADOS (Linha 3)
                    # É aqui que a validação geralmente começa
                    sample_cell = sheet.cell(row=3, column=col_idx)
                    fmt_code = sample_cell.number_format
                    
                    # --- DETECÇÃO VIA VALIDAÇÃO DE DADOS (LISTAS) ---
                    has_validation = False
                    for dv in sheet.data_validations.dataValidation:
                        # CORREÇÃO PRINCIPAL:
                        # Verifica se a coordenada da célula de dados (ex: 'B3') está dentro
                        # do range de validação definido no Excel.
                        # O 'dv.sqref' gerencia automaticamente intervalos complexos.
                        if sample_cell.coordinate in dv.sqref:
                            if dv.type == "list":
                                has_validation = True
                                formula = dv.formula1
                                if formula:
                                    # Limpa a formula para extrair opções (se for lista explícita "A,B,C")
                                    # Se for referência (=Plan2!A1:A5), isso retornaria vazio ou string crua,
                                    # mas para listas simples funciona bem.
                                    opcoes_limpas = [op.strip() for op in formula.replace('"', '').split(',')]
                                    opcoes = opcoes_limpas
                                    
                                    # Análise de subtipos de lista
                                    is_numeric_list = is_list_numeric(opcoes_limpas)
                                    is_numeric_fmt = is_numeric_format(fmt_code)
                                    
                                    # Regra 1: Lista Números + Formato Numérico = SLIDER
                                    if is_numeric_list and is_numeric_fmt:
                                        tipo_detectado = "slider"
                                    
                                    # Regra 2: Lista + Permite erro (showErrorMessage=False) = PILLS + DIGITAÇÃO
                                    elif dv.showErrorMessage is False: # Verifica explicitamente False
                                        tipo_detectado = "selecao_aberta"
                                    
                                    # Regra 3: Caso contrário (Lista Texto ou Núm s/ formato) = PILLS
                                    else:
                                        tipo_detectado = "selecao"
                                
                            # Se encontrou a validação para esta coluna, para de procurar outras regras
                            break 

                    # --- DETECÇÃO SEM VALIDAÇÃO ---
                    if not has_validation:
                        # Se formato for numérico -> NUMBER_INPUT
                        if is_numeric_format(fmt_code):
                            tipo_detectado = "numero"
                        else:
                            tipo_detectado = "texto"

                    headers.append({
                        "nome": nome_campo, 
                        "col_letter": c1.column_letter, 
                        "tipo": tipo_detectado, 
                        "opcoes": opcoes
                    })
            
            estrutura[sheet_name] = [{"nome": h["nome"], "tipo": h["tipo"], "opcoes": h["opcoes"]} for h in headers]
            
        return estrutura
    except Exception as e:
        st.error(f"Erro ao analisar o Excel: {e}")
        return {}
    
def carregar_modelo_atual():
    path_pessoal = get_user_template_path()
    if path_pessoal and os.path.exists(path_pessoal):
        with open(path_pessoal, "rb") as f:
            content = f.read()
            st.session_state['planilha_modelo'] = io.BytesIO(content)
            st.session_state['estrutura_modelo'] = analisar_modelo_excel(content)
            st.session_state['origem_modelo'] = "Pessoal"
    elif os.path.exists(PLANILHA_PADRAO_ADMIN):
        with open(PLANILHA_PADRAO_ADMIN, "rb") as f:
            content = f.read()
            st.session_state['planilha_modelo'] = io.BytesIO(content)
            st.session_state['estrutura_modelo'] = analisar_modelo_excel(content)
            st.session_state['origem_modelo'] = "Padrão do Sistema"

def gerar_zip_exportacao(dados_lista):
    """
    Gera um arquivo ZIP contendo o Excel de levantamento e uma pasta com as fotos.
    """
    if 'planilha_modelo' not in st.session_state: return None
    
    # 1. Gerar o Excel em memória
    st.session_state['planilha_modelo'].seek(0)
    book = load_workbook(st.session_state['planilha_modelo'])
    
    for registro in dados_lista:
        if registro['tipo_equipamento'] in book.sheetnames:
            sheet = book[registro['tipo_equipamento']]
            
            # Mapeamento dinâmico baseado no cabeçalho
            headers = {sheet.cell(row=1, column=i).value: i for i in range(1, sheet.max_column + 1)}
            
            nova_linha_dados = registro['dados']
            
            # Preparar array para append (garantindo ordem)
            # Como append adiciona no fim, precisamos garantir que as colunas batem com os valores
            # Melhor abordagem com openpyxl para dados esparsos: escrever celula a celula na nova linha
            next_row = sheet.max_row + 1
            
            for k, v in nova_linha_dados.items():
                if k in headers:
                    sheet.cell(row=next_row, column=headers[k], value=v)
            
            # Tratamento de Fotos no Excel (se houver coluna)
            if "Fotos" in headers and "fotos" in registro:
                 nomes_fotos = ", ".join([f['nome_exportacao'] for f in registro["fotos"]])
                 sheet.cell(row=next_row, column=headers["Fotos"], value=nomes_fotos)
    
    excel_buffer = io.BytesIO()
    book.save(excel_buffer)
    excel_buffer.seek(0)
    
    # 2. Criar o ZIP
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # Adicionar Excel
        zf.writestr("Levantamento_Cargas.xlsx", excel_buffer.getvalue())
        
        # Adicionar Fotos
        for registro in dados_lista:
            if "fotos" in registro and registro["fotos"]:
                uc = registro.get("cod_instalacao", "SemUC")
                tipo = registro.get("tipo_equipamento", "Geral")
                
                # Pasta dentro do ZIP para organizar
                folder_path = f"Fotos/{uc} - {tipo}/"
                
                for foto in registro["fotos"]:
                    caminho_origem = foto["caminho_fisico"]
                    if os.path.exists(caminho_origem):
                        # Nome dentro do ZIP
                        zf.write(caminho_origem, arcname=f"{folder_path}{foto['nome_exportacao']}")
    
    zip_buffer.seek(0)
    return zip_buffer

# EMAIL (Atualizado para enviar ZIP se tiver fotos ou apenas Excel)
def enviar_email(arquivo_buffer, destinatario, is_zip=False):
    try:
        msg = MIMEMultipart()
        msg['From'] = "levantamento.poupenergia@gmail.com"
        msg['To'] = destinatario
        msg['Subject'] = f"Levantamento {st.session_state['usuario_ativo']} - {get_data_hora_br().strftime('%d/%m/%Y')}"
        msg.attach(MIMEText("Segue em anexo o levantamento realizado.", 'plain'))
        
        part = MIMEBase('application', 'zip' if is_zip else 'octet-stream')
        part.set_payload(arquivo_buffer.getvalue())
        encoders.encode_base64(part)
        
        filename = "levantamento_completo.zip" if is_zip else "levantamento.xlsx"
        part.add_header('Content-Disposition', f'attachment; filename={filename}')
        
        msg.attach(part)
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        # Nota: Idealmente usar variáveis de ambiente para senhas
        server.login("levantamento.poupenergia@gmail.com", "kiqplowxqprcugjc")
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(e)
        return False
    
def exportar_para_excel(dados):
    """
    Gera um arquivo Excel simples (BytesIO) a partir de uma lista de dicionários.
    Achata a estrutura (tira os campos de dentro de 'dados') para criar uma tabela única.
    """
    if not dados:
        return None
    
    try:
        # Lista para armazenar os dados "achatados" (flat)
        lista_plana = []
        
        for item in dados:
            # 1. Pegar dados principais (cabeçalho)
            row = {
                "UC": item.get("cod_instalacao"),
                "Tipo": item.get("tipo_equipamento"),
                "Data": item.get("data_hora"),
            }
            
            # 2. Pegar os dados técnicos dinâmicos (que estão dentro da chave 'dados')
            # Isso faz com que 'Potência', 'Marca', etc, virem colunas do Excel
            dados_tecnicos = item.get("dados", {})
            if isinstance(dados_tecnicos, dict):
                row.update(dados_tecnicos)
            
            # 3. Formatar lista de fotos para uma string simples
            fotos = item.get("fotos", [])
            if fotos and isinstance(fotos, list):
                nomes_fotos = [f.get("nome_exportacao", "foto") for f in fotos]
                row["Fotos Anexadas"] = ", ".join(nomes_fotos)
            
            lista_plana.append(row)
            
        # Criar DataFrame
        df = pd.DataFrame(lista_plana)
        
        # Salvar em memória (BytesIO)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name="Exportacao")
            
        output.seek(0)
        return output

    except Exception as e:
        print(f"Erro ao exportar excel: {e}")
        return None


# --- ADICIONAR AO FINAL DO UTILS.PY ---

def carregar_config_backup():
    if os.path.exists("config_backup.json"):
        with open("config_backup.json", "r") as f:
            config = json.load(f)
            if "ativo" not in config:
                config["ativo"] = bool(config.get("email"))
            return config
    return {}

def salvar_config_backup(email, ativo):
    with open("config_backup.json", "w") as f:
        json.dump({"email": email, "ativo": ativo}, f)

def carregar_estado_backup():
    if os.path.exists("estado_backup.json"):
        with open("estado_backup.json", "r") as f: return json.load(f)
    return {}

def salvar_estado_backup(data_envio, status):
    # Se data_envio for None, mantém a última data de sucesso para não repetir falhas
    estado_atual = carregar_estado_backup()
    dados = {
        "data_ultimo_envio": data_envio if data_envio else estado_atual.get("data_ultimo_envio"),
        "status": status,
        "ultimo_check": datetime.now().isoformat()
    }
    with open("estado_backup.json", "w") as f: json.dump(dados, f)

def gerar_zip_sistema_completo():
    """Gera um ZIP de auditoria com dados de todos os clientes e anexos."""
    try:
        arquivos_dados = sorted([f for f in os.listdir(".") if f.startswith("dados_") and f.endswith(".json")])
        dados_com_conteudo = []
        fotos = set()

        for arquivo_dados in arquivos_dados:
            registros = carregar_dados_locais(path_especifico=arquivo_dados)
            if registros:
                dados_com_conteudo.append(arquivo_dados)
                fotos.update(_coletar_fotos_de_registros(registros))

        if not dados_com_conteudo:
            return None

        nome_arquivo = f"auditoria_poupenergia_{datetime.now().strftime('%Y%m%d')}.zip"

        with zipfile.ZipFile(nome_arquivo, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for arquivo_dados in dados_com_conteudo:
                zipf.write(arquivo_dados)

            if os.path.exists(PLANILHA_PADRAO_ADMIN):
                zipf.write(PLANILHA_PADRAO_ADMIN)

            for caminho_foto in fotos:
                zipf.write(caminho_foto, arcname=os.path.join("fotos", os.path.basename(caminho_foto)))

        return nome_arquivo
    except Exception as e:
        print(f"[Erro ZIP Sistema] {e}")
        return None


def gerar_zip_sistema():
    """Compatibilidade com chamadas legadas."""
    return gerar_zip_sistema_completo()

def enviar_email_backup_servico(destinatario, zip_path):
    """Envia o ZIP via SMTP usando credenciais existentes."""
    try:
        msg = MIMEMultipart()
        msg['Subject'] = f"Backup Automático Diário - PoupEnergia - {datetime.now().strftime('%d/%m/%Y')}"
        msg['From'] = "levantamento.poupenergia@gmail.com"
        msg['To'] = destinatario
        msg.attach(MIMEText("Segue em anexo o backup completo do sistema.", 'plain'))
        
        with open(zip_path, "rb") as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(zip_path)}')
            msg.attach(part)
            
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login("levantamento.poupenergia@gmail.com", "kiqplowxqprcugjc")
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Erro SMTP Backup: {e}")
        return False


# --- CONTROLE DE SESSÃO PERSISTENTE (LEMBRAR DE MIM) ---
ARQUIVO_REMEMBER_ME = "session_token.json"
DIAS_EXPIRACAO = 7

def salvar_sessao_persistente(usuario):
    """
    Salva um token de sessão local para 'Lembrar de mim'.
    Não armazena senhas, apenas o usuário e a data de validade.
    """
    try:
        expiracao = datetime.now() + timedelta(days=DIAS_EXPIRACAO)
        dados = {
            "usuario": usuario,
            "expira_em": expiracao.strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(ARQUIVO_REMEMBER_ME, "w") as f:
            json.dump(dados, f)
    except Exception as e:
        print(f"[Auth] Erro ao salvar sessão persistente: {e}")

def verificar_sessao_persistente():
    """
    Verifica se existe uma sessão salva e válida.
    Retorna o nome do usuário se válido, ou None se inválido/expirado.
    """
    if not os.path.exists(ARQUIVO_REMEMBER_ME):
        return None
        
    try:
        with open(ARQUIVO_REMEMBER_ME, "r") as f:
            dados = json.load(f)
            
        expira_em = datetime.strptime(dados["expira_em"], "%Y-%m-%d %H:%M:%S")
        
        if datetime.now() < expira_em:
            return dados["usuario"]
        else:
            # Token expirado, limpa o arquivo
            limpar_sessao_persistente()
            return None
    except:
        return None

def limpar_sessao_persistente():
    """Remove o arquivo de sessão persistente (Logout manual)."""
    if os.path.exists(ARQUIVO_REMEMBER_ME):
        try:
            os.remove(ARQUIVO_REMEMBER_ME)
        except:
            pass





