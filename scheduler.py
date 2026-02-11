import threading
import time
import datetime
import utils
import os
import streamlit as st

# --- CONSTANTES ---
HORA_ENVIO = 16

def _rotina_agendamento():
    """
    Rotina principal que verifica backups globais (Admin) e individuais (Clientes).
    """
    while True:
        try:
            agora = datetime.datetime.now()
            hoje_str = agora.strftime("%Y-%m-%d")
            
            # Executa apenas se for >= 20:00
            if agora.hour >= HORA_ENVIO:
                
                # --- 1. ROTINA DE CLIENTES (Individual) ---
                prefs_clientes = utils.carregar_prefs_todos_clientes()
                
                for usuario, config in prefs_clientes.items():
                    # Verifica se está ativo, tem email e ainda não foi enviado hoje
                    if config.get("ativo") and config.get("email") and config.get("ultimo_envio") != hoje_str:
                        try:
                            print(f"[Scheduler] Iniciando backup cliente: {usuario}")
                            arquivo_zip = utils.gerar_zip_usuario(usuario)
                            
                            if arquivo_zip and os.path.exists(arquivo_zip):
                                sucesso = utils.enviar_email_backup_servico(config["email"], arquivo_zip)
                                if sucesso:
                                    utils.atualizar_status_envio_cliente(usuario, hoje_str)
                                    print(f"[Scheduler] Sucesso envio cliente: {usuario}")
                                    # Limpeza
                                    os.remove(arquivo_zip)
                            else:
                                print(f"[Scheduler] Arquivo ZIP vazio ou inexistente para {usuario}")
                                
                        except Exception as e_cli:
                            print(f"[Scheduler] Erro ao processar cliente {usuario}: {e_cli}")
                            # Continua para o próximo cliente, não para o loop

                # --- 2. ROTINA DE ADMIN (Global/Auditoria) ---
                config_admin = utils.carregar_config_backup() # Configuração global existente
                estado_admin = utils.carregar_estado_backup() # Estado global existente
                
                email_admin = config_admin.get("email")
                ultimo_envio_admin = estado_admin.get("data_ultimo_envio")
                
                admin_ativo = config_admin.get("ativo", bool(email_admin))

                if admin_ativo and email_admin and ultimo_envio_admin != hoje_str:
                    try:
                        print(f"[Scheduler] Iniciando Auditoria Global para: {email_admin}")
                        zip_global = utils.gerar_zip_sistema() # Usa função existente que zipa tudo
                        
                        if zip_global and os.path.exists(zip_global):
                            sucesso = utils.enviar_email_backup_servico(email_admin, zip_global)
                            if sucesso:
                                utils.salvar_estado_backup(hoje_str, "sucesso")
                                print("[Scheduler] Backup Auditoria enviado.")
                                os.remove(zip_global)
                        else:
                            utils.salvar_estado_backup(None, "sem_dados")
                            print("[Scheduler] Auditoria sem dados para envio.")
                    except Exception as e_adm:
                        print(f"[Scheduler] Erro crítico no backup Admin: {e_adm}")

            # Aguarda 60 segundos antes da próxima verificação
            time.sleep(60)
            
        except Exception as e:
            print(f"[Scheduler] Erro crítico na thread: {e}")
            time.sleep(60)

# Mantenha a função iniciar_agendador() inalterada
def iniciar_agendador():
    if 'agendador_iniciado' not in st.session_state:
        thread = threading.Thread(target=_rotina_agendamento, daemon=True)
        thread.start()
        st.session_state['agendador_iniciado'] = True

        print("[System] Agendador atualizado iniciado.")

