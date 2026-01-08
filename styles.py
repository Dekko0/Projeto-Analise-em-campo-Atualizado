import streamlit as st

def apply_custom_style():
    st.markdown("""
        <style>
            /* Remove o padding excessivo do topo */
            .block-container {
                padding-top: 2rem;
                padding-bottom: 2rem;
            }
            
            /* Ajusta a cor do botão primário para o Verde PoupEnergia */
            .stButton > button[kind="primary"] {
                background-color: #2E7D32;
                border-color: #2E7D32;
            }
            .stButton > button[kind="primary"]:hover {
                background-color: #1B5E20;
                border-color: #1B5E20;
            }

            /* Esconde o menu 'hamburger' do topo direito para visual mais limpo (opcional) */
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)
