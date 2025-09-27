"""
Utilitários para gerenciar session state
"""
import streamlit as st
from datetime import datetime

def initialize_session_state():
    """Inicializa variáveis do session state"""
    defaults = {
        'ultima_atualizacao': datetime.now().strftime("%d/%m/%Y %H:%M"),
        'modulo_ativo': 'Lojas',
        'cache_timestamp': datetime.now().timestamp()
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def update_module_state(module_name: str):
    """Atualiza o estado do módulo ativo"""
    st.session_state['modulo_ativo'] = module_name
    st.session_state['ultima_atualizacao'] = datetime.now().strftime("%d/%m/%Y %H:%M")

def clear_module_cache():
    """Limpa cache específico do módulo"""
    # Implementar lógica para limpar cache específico se necessário
    st.cache_data.clear()
    st.session_state['cache_timestamp'] = datetime.now().timestamp()