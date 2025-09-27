"""
Estilos CSS específicos para a aplicação principal
"""
import streamlit as st

def apply_sidebar_styles():
    """Aplica estilos CSS para a sidebar"""
    st.markdown("""
    <style>
        /* Estilo da sidebar */
        .css-1d391kg {
            background-color: #f8f9fa;
        }
        
        /* Estilo dos botões da sidebar */
        .stSelectbox > div > div {
            background-color: white;
            border-radius: 8px;
        }
        
        /* Título da sidebar */
        .sidebar-title {
            color: #1f2937;
            font-size: 24px;
            font-weight: 700;
            margin-bottom: 20px;
            text-align: center;
        }
        
        /* Descrição da seção */
        .section-description {
            color: #6b7280;
            font-size: 14px;
            margin-bottom: 15px;
            padding: 10px;
            background-color: #f3f4f6;
            border-radius: 6px;
            border-left: 4px solid #3b82f6;
        }
    </style>
    """, unsafe_allow_html=True)

def apply_main_styles():
    """Aplica estilos CSS para o conteúdo principal"""
    st.markdown("""
    <style>
        /* Estilos gerais da aplicação */
        .main-content {
            padding: 1rem;
        }
        
        /* Títulos dos módulos */
        .module-title {
            font-size: 24px;
            font-weight: 800;
            margin: 0 0 20px 0;
            padding: 0;
            border-bottom: 2px solid #e5e7eb;
            padding-bottom: 10px;
        }
        
        /* Cards de erro */
        .error-card {
            padding: 1rem;
            border-radius: 8px;
            background-color: #fee2e2;
            border: 1px solid #fca5a5;
            margin: 1rem 0;
        }
        
        /* Cards de desenvolvimento */
        .dev-card {
            padding: 1rem;
            border-radius: 8px;
            background-color: #dbeafe;
            border: 1px solid #93c5fd;
            margin: 1rem 0;
        }
    </style>
    """, unsafe_allow_html=True)