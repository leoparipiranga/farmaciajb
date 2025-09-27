import streamlit as st
from business_logic.estoque.disponibilidade import (
    render_content_filial,
    render_content_curva_abc,
    render_content_grupo,
    render_content_historico,
    render_content_nivel2

) 

def css_popovers_ruptura_duck(pop_width=850):
    """
    Injeta CSS para popovers de ruptura.
    """
    import streamlit as st
    st.markdown(f"""
    <style>
    .metric-card {{
        background: white;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #e1e5e9;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }}
    
    .metric-title {{
        font-size: 0.875rem;
        color: #6b7280;
        margin-bottom: 0.25rem;
    }}
    
    .metric-value {{
        font-size: 1.5rem;
        font-weight: 700;
        color: #111827;
    }}
    </style>
    """, unsafe_allow_html=True)

def render_interface_indicadores_estoque(data_atual):
    """Interface com menu de navegação e área principal dos indicadores de estoque."""
    import streamlit as st

    st.markdown("""
        <style>
        .main .block-container {
            padding-top: 0.5rem !important;
            padding-bottom: 0.5rem !important;
            max-width: 100% !important;
        }
        .element-container { margin-bottom: 0 !important; }
        div[data-testid="column"] { gap: 0.25rem !important; }
        .main-content-area {
            padding-top: 0 !important;
            margin-top: 0 !important;
        }
        </style>
    """, unsafe_allow_html=True)

    if 'selected_indicator' not in st.session_state:
        st.session_state.selected_indicator = 'filial'

    indicadores = [
        ("Filial", "filial", render_content_filial),
        ("Curva ABC", "curva_abc", render_content_curva_abc),
        ("Grupo Principal", "grupo", render_content_grupo),
        ("Subgrupo", "nivel2", render_content_nivel2),
        ("Histórico", "historico", render_content_historico),
    ]

    key_to_label = {key: label for label, key, _ in indicadores}
    label_to_key = {label: key for key, label in key_to_label.items()}

    escolha_label = st.segmented_control(
        "📊 Navegação de Indicadores",
        options=[label for label, _, _ in indicadores],
        key="estoque_menu",
        default=key_to_label.get(st.session_state.selected_indicator, "Filial")
    )

    st.session_state.selected_indicator = label_to_key[escolha_label]

    st.markdown('<div class="main-content-area">', unsafe_allow_html=True)
    _, _, func_render = next(item for item in indicadores if item[1] == st.session_state.selected_indicator)
    func_render(data_atual)
    st.markdown('</div>', unsafe_allow_html=True)