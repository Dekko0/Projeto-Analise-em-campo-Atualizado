import threading
import time
import datetime
import utils
import os
import streamlit as st

# --- CONSTANTES DE AGENDAMENTO ---
HORA_ENVIO = 16    # Hora definida para 19h
MINUTO_ENVIO = 10   # Minutos definidos para 00min -> Total 19:00

def _rotina_agendamento():
    """
    Rotina em background que verifica se deve enviar os backups.
    Verifica a cada minuto se o horário atual é >= ao horário configurado.
    """
    while True:
        try:
            agora = datetime.datetime.now()
            hoje_str = agora.strftime("%Y-%m-%d")
            
            # Verifica se já passamos das 19:00 hoje
            horario_atingido = (agora.hour > HORA_ENVIO) or (agora.hour == HORA_ENVIO and agora.minute >= MINUTO_ENVIO)
            
            if horario_atingido:
                
                # --- PROCESSAMENTO POR USUÁRIO ---
                prefs_clientes = utils.carregar_prefs_todos_clientes()
                
                for usuario, config in prefs_clientes.items():
                    email_destino = config.get("email")
                    ultimo_envio = config.get("ultimo_envio")
                    ativo = config.get("ativo", True)
                    
                    # Só envia se: 1. Ativo, 2. Tem Email cadastrado, 3. Não foi enviado hoje
                    if ativo and email_destino and ultimo_envio != hoje_str:
                        try:
                            # Padrão de nome do ZIP gerado no utils.py (ex: backup_usuario_20231025.zip)
                            nome_zip_esperado = f"backup_{usuario}_{agora.strftime('%Y%m%d')}.zip"
                            
                            # Verifica se o arquivo de backup já existe no diretório padrão
                            if os.path.exists(nome_zip_esperado):
                                
                                # Confirmação extra: verifica se a data de modificação física é de hoje
                                mtime = os.path.getmtime(nome_zip_esperado)
                                data_modificacao = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
                                
                                if data_modificacao == hoje_str:
                                    print(f"[Scheduler] Backup de hoje encontrado para {usuario}. Enviando...")
                                    
                                    # Dispara o e-mail via SMTP aproveitando a função já existente
                                    sucesso = utils.enviar_email_backup_servico(email_destino, nome_zip_esperado)
                                    
                                    if sucesso:
                                        # Atualiza a flag de envio usando a assinatura correta do utils.py
                                        utils.atualizar_status_envio_cliente(usuario, hoje_str)
                                        print(f"[Scheduler] Backup diário enviado com sucesso para {usuario}")
                                    else:
                                        print(f"[Scheduler] Falha ao tentar enviar e-mail para {usuario}")
                                else:
                                    # Arquivo existe, mas é de dias anteriores. Ignora.
                                    pass
                            else:
                                # Não há backup gerado hoje. Ignora sem disparar erros.
                                pass
                                
                        except Exception as e_user:
                            print(f"[Scheduler] Erro isolado ao processar usuário {usuario}: {e_user}")

            # Dorme 60 segundos para evitar processamento excessivo de CPU
            time.sleep(60)
            
        except Exception as e:
            print(f"[Scheduler] Erro crítico no loop principal: {e}")
            time.sleep(60)

def iniciar_agendador():
    """
    Garante que a thread do agendador só é iniciada uma vez no ciclo de vida do Streamlit.
    """
    if 'agendador_iniciado' not in st.session_state:
        thread = threading.Thread(target=_rotina_agendamento, daemon=True)
        thread.start()
        st.session_state['agendador_iniciado'] = True
        print(f"[System] Agendador configurado para as {HORA_ENVIO}:{MINUTO_ENVIO:02d}.")
    return True