import streamlit as st
import sys
import os
from datetime import datetime

# Imports da nova estrutura
from core.database import duck_query
from visualizations.styling.app_styling import apply_main_styles
from utils.session_state import initialize_session_state

# Configuração da página
st.set_page_config(
    page_title="Farmácia JB - SprintD Farma",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

def _inject_sidebar_button_css():
    st.markdown("""
    <style>
    div[data-testid="stSidebar"] {
        --btn-primary-bg: CadetBlue;
        --btn-primary-color: #ffffff;
        --btn-primary-border: #2F4F4F;
        --btn-secondary-bg: #E6F2F6;
        --btn-secondary-color: #17495E;
        --btn-secondary-border: #9BBCC6;
    }
    div[data-testid="stSidebar"] .sidebar-menu {
        display: flex !important;
        flex-direction: column !important;
        gap: 0.6rem !important;
        width: 100% !important;
    }
    div[data-testid="stSidebar"] .sidebar-menu .stButton > button {
        width: 100% !important;
        min-height: 54px !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        box-shadow: none !important;
    }
    div[data-testid="stSidebar"] .sidebar-menu .stButton > button[kind="primary"] {
        background-color: var(--btn-primary-bg) !important;
        color: var(--btn-primary-color) !important;
        border: 1px solid var(--btn-primary-border) !important;
    }
    div[data-testid="stSidebar"] .sidebar-menu .stButton > button[kind="secondary"] {
        background-color: var(--btn-secondary-bg) !important;
        color: var(--btn-secondary-color) !important;
        border: 1px solid var(--btn-secondary-border) !important;
    }
    div[data-testid="stSidebar"] .sidebar-menu .stButton > button[kind="secondary"]:hover {
        background-color: #D2E8EE !important;
        color: #103B52 !important;
        border-color: #5F9EA0 !important;
    }
    div[data-testid="stSidebar"] .sidebar-menu .stButton > button[kind="primary"]:hover {
        background-color: #5F9EA0 !important;
        border-color: #2F4F4F !important;
    }
    </style>
    """, unsafe_allow_html=True)

def verificar_credenciais(usuario: str, senha: str) -> tuple[bool, str | None]:
    try:
        usuarios = st.secrets.get("usuarios", {})
        if usuario in usuarios and usuarios[usuario].get("senha") == senha:
            return True, usuarios[usuario].get("nome_completo", usuario)

        credenciais_padrao = {
            "admin": {"senha": "123456", "nome_completo": "Administrador"},
            "farmacia": {"senha": "farmacia123", "nome_completo": "Farmácia JB"},
        }
        if usuario in credenciais_padrao and credenciais_padrao[usuario]["senha"] == senha:
            return True, credenciais_padrao[usuario]["nome_completo"]

        return False, None
    except Exception as exc:
        st.error(f"Erro ao verificar credenciais: {exc}")
        return False, None

def tela_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div class="login-container">
            <div class="login-header">
                <h1>💊 SprintD Farma</h1>
                <p>Dashboards Inteligentes</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            st.markdown("### 🔐 Acesso ao Sistema")
            usuario = st.text_input("👤 Usuário:", placeholder="Digite seu usuário")
            senha = st.text_input("🔑 Senha:", type="password", placeholder="Digite sua senha")

            submit = st.form_submit_button("🚀 Entrar no Sistema", type="primary", use_container_width=True)

            if submit:
                if usuario and senha:
                    ok, nome_completo = verificar_credenciais(usuario, senha)
                    if ok:
                        st.session_state.autenticado = True
                        st.session_state.usuario = usuario
                        st.session_state.nome_completo = nome_completo
                        st.session_state.pagina_atual = "Lojas"
                        st.success(f"✅ Bem-vindo, {nome_completo}!")
                        st.rerun()
                    else:
                        st.error("❌ Usuário ou senha incorretos!")
                        st.warning("💡 Verifique suas credenciais e tente novamente")
                else:
                    st.warning("⚠️ Por favor, preencha usuário e senha")

        st.markdown("---")
        with st.expander("ℹ️ Informações do Sistema"):
            st.info("""
            **📊 Funcionalidades:**
            - 🏪 Lojas
            - 👥 Vendedores
            - 📦 Estoque
            - 🎯 Promoções

            **👤 Login teste:** admin / 123456
            """)

def main():
    _inject_sidebar_button_css()
    apply_main_styles()
    initialize_session_state()

    if not st.session_state.get("autenticado"):
        tela_login()
        return

    modulo_selecionado = render_sidebar()
    render_main_content(modulo_selecionado)

    _inject_sidebar_button_css()
    update_last_update_timestamp()

def render_sidebar():
    with st.sidebar:
        st.markdown("### 🏥 Farmácia JB")

        if "pagina_atual" not in st.session_state:
            st.session_state.pagina_atual = "Lojas"

        st.markdown('<div class="sidebar-menu">', unsafe_allow_html=True)

        opcoes = ["Lojas", "Vendedores", "Estoque", "Promoções"]
        for opcao in opcoes:
            ativo = (st.session_state.pagina_atual == opcao)
            if st.button(opcao,
                         key=f"menu_{opcao}",
                         type="primary" if ativo else "secondary",
                         use_container_width=True):
                st.session_state.pagina_atual = opcao
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

        st.divider()
        st.caption(f"📅 Última atualização: {st.session_state.get('ultima_atualizacao', 'Carregando...')}")
        st.caption("🔄 Dados atualizados automaticamente")
        
        st.divider()
        st.caption("Versão Beta • SprintD Farma")
        return st.session_state.pagina_atual
    
def render_module_info(modulo_selecionado):
    """Renderiza informações específicas de cada módulo"""
    module_configs = {
        "Lojas": {
            "title": "📈 Análise por Lojas",
            "description": "Visualize KPIs, vendas, metas e performance de cada filial. Analise alertas e tendências por loja.",
            "options": [
                ("Mostrar alertas automáticos", "mostrar_alertas", True),
                ("Mostrar previsões", "mostrar_previsoes", True)
            ]
        },
        "Estoque": {
            "title": "📦 Análise de Estoque",
            "description": "Monitore níveis de estoque, produtos em falta, e otimize a reposição para evitar rupturas.",
            "options": [
                ("Mostrar produtos em falta", "mostrar_produtos_falta", True),
                ("Mostrar níveis de estoque", "mostrar_niveis_estoque", True)
            ]
        },
        "Promoções": {
            "title": "🏷️ Análise das Promoções",
            "description": "Avalie a eficácia das promoções, impacto nas vendas, e comportamento do cliente durante campanhas promocionais.",
            "options": [
                ("Mostrar impacto nas vendas", "mostrar_impacto", True),
                ("Mostrar comportamento do cliente", "mostrar_comportamento", True)
            ]
        },
        "Vendedores": {
            "title": "👥 Análise por Vendedores",
            "description": "Performance individual dos vendedores, comissões, rankings e metas por colaborador.",
            "options": [
                ("Mostrar ranking", "mostrar_ranking", True),
                ("Mostrar comissões", "mostrar_comissoes", True)
            ]
        }
    }
    
    config = module_configs.get(modulo_selecionado, {})
    
    if config:
        st.markdown(
            f'<div class="section-description">'
            f'<strong>{config["title"]}</strong><br>'
            f'{config["description"]}'
            f'</div>', 
            unsafe_allow_html=True
        )
        
        # Opções específicas do módulo
        st.markdown("**🔧 Opções Avançadas:**")
        for label, key, default in config["options"]:
            st.checkbox(label, value=default, key=key)


def render_system_info():
    """Renderiza informações do sistema"""
    st.markdown("**ℹ️ Informações do Sistema**")
    st.caption(f"📅 Última atualização: {st.session_state.get('ultima_atualizacao', 'Carregando...')}")
    st.caption("🔄 Dados atualizados automaticamente")
    
    # Botão de refresh
    if st.button("🔄 Atualizar Dados", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


def render_main_content(modulo_selecionado):
    """Renderiza o conteúdo principal baseado no módulo selecionado"""
    try:
        if modulo_selecionado == "Lojas":
            render_lojas_module()
        elif modulo_selecionado == "Estoque":
            render_estoque_module()
        elif modulo_selecionado == "Promoções":
            render_promocoes_module()
        else:  # Vendedores
            render_vendedores_module()
            
    except Exception as e:
        render_error_page(e)

def render_lojas_module():
    """Renderiza o módulo de lojas"""
    
    from modules_duck.lojas_duck import render as render_lojas
    
    st.markdown(
        '<div id="titulo_lojas" style="font-size:24px; font-weight:800; margin:0 0 0 0; padding:0;">'
        '🏪 <strong>Análise por Lojas</strong></div>', 
        unsafe_allow_html=True
    )
    
    render_lojas()

def render_estoque_module():
    """Renderiza o módulo de estoque"""
    
    from modules_duck.estoque_duck import main as main_estoque
    
    st.markdown(
        '<div id="titulo_estoque" style="font-size:24px; font-weight:800; margin:0 0 0 0; padding:0;">'
        '📦 <strong>Análise de Estoque</strong></div>', 
        unsafe_allow_html=True
    )
    
    main_estoque()
        
    

def render_promocoes_module():
    """Renderiza o módulo de promoções"""
    
    from modules_duck.promocoes_duck import main as main_promocoes
        
    st.markdown(
        '<div id="titulo_promocoes" style="font-size:24px; font-weight:800; margin:0 0 0 0; padding:0;">'
        '🏷️ <strong>Análise das Promoções</strong></div>', 
        unsafe_allow_html=True
    )
    
    main_promocoes()

def render_vendedores_module():
    """Renderiza o módulo de vendedores"""
    
    from modules_duck.vendedores_duck import main as main_vendedores
    
    st.markdown(
        '<div id="titulo_vendedores" style="font-size:24px; font-weight:800; margin:0 0 0 0; padding:0;">'
        '👥 <strong>Análise por Vendedores</strong></div>', 
        unsafe_allow_html=True
    )
    
    main_vendedores()
        
def render_error_page(error):
    """Renderiza página de erro"""
    st.error(f"❌ **Erro ao carregar página:** {error}")
    
    with st.expander("🔍 **Detalhes do Erro**", expanded=False):
        st.exception(error)
        
    st.info("""
    **💡 Sugestões para resolver:**
    1. Verifique se todos os módulos estão na pasta correta
    2. Confirme se as importações estão funcionando
    3. Teste a conexão com o banco de dados
    """)


def update_last_update_timestamp():
    """Atualiza o timestamp da última atualização"""
    if 'ultima_atualizacao' not in st.session_state:
        st.session_state['ultima_atualizacao'] = datetime.now().strftime("%d/%m/%Y %H:%M")


if __name__ == "__main__":
    main()