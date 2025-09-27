"""
Componentes CSS para estilização da interface
"""
import streamlit as st

def apply_cards_css_duck():
    st.markdown("""
    <style>
      /* Card padrão (cinza claro) */
      .kpi-card-duck {
        width: 100%;
        height: 108px;
        background: #f5f7fa;
        border: 1px solid #e6e9ef;
        border-radius: 10px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        color: #0f2d5c;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        gap: 6px;
        text-align: center;
        padding: 14px 10px;
        position: relative;
        overflow: hidden;
        margin-bottom: 12px;
      }
      .kpi-card-duck::before {
        content: '';
        position: absolute;
        top: 0; left: 10px; right: 10px;
        height: 3px;
        background: linear-gradient(90deg, #cfd6dd, #e1e6eb);
        border-radius: 10px 10px 0 0;
      }
      .kpi-card-duck:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 18px rgba(0,0,0,0.12);
        border-color: #d8dde5;
      }
      .kpi-card-title {
        font-size: 12px;
        font-weight: 700;
        color: #5c6b7a;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin: 0;
      }
      .kpi-card-value {
        font-size: 22px;
        font-weight: 800;
        color: #1d2b3a;
        margin: 0;
        line-height: 1.1;
        text-shadow: 0 1px 2px rgba(0,0,0,0.06);
      }
      .kpi-card-duck.is-alt {
        background: #eef7f2;
        border: 1px solid #d7eadf;
      }
      .kpi-card-duck.is-alt::before {
        background: linear-gradient(90deg, #bfe7cf, #d9f0e4);
      }
    </style>
    """, unsafe_allow_html=True)

def apply_light_card_css():
    # Cinza clarinho nos cards (st.metric e wrappers) — escopado para não afetar os de classificação
    import streamlit as st
    st.markdown(
        """
        <style>
        div[data-testid="stMetric"] {
            background: #f6f6f6 !important;
            padding: 12px 16px !important;
            border-radius: 10px !important;
            border: 1px solid #eee !important;
        }
        div[data-testid="stMetric"] > div { justify-content: center !important; }
        .kpi-card {
            background: #f6f6f6 !important;
            border: 1px solid #eee !important;
            border-radius: 10px !important;
            padding: 12px 16px !important;
        }
        /* Escopar para .kpi-card apenas, evitando colidir com .kpi-card-classificacao-verde */
        .kpi-card .kpi-label { font-size:11px; font-weight:600; letter-spacing:0.5px; text-transform:uppercase; color:#6c7a89; line-height:1.0; }
        .kpi-card .kpi-value { font-size:18px; font-weight:700; color:#1f2d3d; text-shadow:none; line-height:1.05; }
        .kpi-card .kpi-perc  { font-size:10px; font-weight:500; color:#8a99a8; line-height:1.0; }
        </style>
        """,
        unsafe_allow_html=True
    )

def apply_classificacao_cards_css():
    # CSS original dos cards de classificação (lojas.py)
    st.markdown("""
    <style>
    .kpi-card-classificacao-verde {
        background: linear-gradient(145deg, darkslategrey 0%, cadetblue 100%);
        border: 1px solid firebrick;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        color: #ecf0f1;
        box-shadow: 0 6px 20px rgba(0,0,0,0.3);
        margin-bottom: 0px;
        transition: all 0.3s ease;
        position: relative;
        display: flex;
        flex-direction: column;
        justify-content: center;
        height: 130px;
        min-height: 130px;
    }
    .kpi-card-classificacao-verde::after {
        content: '';
        position: absolute;
        top: 0;
        left: 10px;
        right: 10px;
        height: 2px;
        background: linear-gradient(90deg, #90EE90, #32CD32, #228B22, #006400);
        border-radius: 10px 10px 0 0;
    }
    .kpi-card-classificacao-verde:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(85, 107, 47, 0.4);
        border-color: #90EE90;
    }
    .kpi-title {
        font-size: 12px;
        margin-bottom: 5px;
        font-weight: 600;
        color: #bdc3c7;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .kpi-value {
        font-size: 20px;
        font-weight: 700;
        margin-bottom: 2px;
        color: #ecf0f1;
        text-shadow: 0 1px 2px rgba(0,0,0,0.4);
    }
    .progress-container-scaled { margin-top: 10px; }
    .progress-bar-bg-scaled {
        background-color: #2c3e50;
        border-radius: 5px;
        height: 16px;
        width: 100%;
        position: relative;
        overflow: hidden;
    }
    .progress-bar-scaled {
        height: 100%;
        border-radius: 5px;
        transition: width 0.5s ease-in-out;
        display: flex;
        align-items: center;
        justify-content: flex-start;
        padding-left: 8px;
        font-size: 10px;
        font-weight: bold;
        color: white;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.6);
    }
    .meta-marker {
        position: absolute;
        top: -3px;
        bottom: -3px;
        width: 3px;
        background-color: yellow;
        border-radius: 2px;
        transition: left 0.5s ease-in-out;
        z-index: 2;
    }
    .axis-labels {
        display: flex;
        justify-content: space-between;
        font-size: 10px;
        color: #95a5a6;
        padding: 2px 0;
    }
    </style>
    """, unsafe_allow_html=True)

def css_popovers_ruptura(pop_width: int = 900):
    st.markdown(f"""
    <style>
    div[data-testid="column"] > div:has(> button[data-testid="stPopoverButton"]) {{
        margin:0 !important;
        padding:0 !important;
    }}
    .kpi-card {{
        width:90% !important;
        height:120px !important;  /* Ajustado para 120px, igual aos gauges */
        background:#ffffff;
        border:1px solid #e2e6ea;
        border-radius:10px;
        box-shadow:0 2px 6px rgba(0,0,0,0.08);
        color:#1f2d3d;
        display:flex;
        flex-direction:column;
        justify-content:center;
        align-items:center;
        gap:6px;  /* Aumentado ligeiramente para melhor espaçamento no novo tamanho */
        text-align:center;
        padding:12px 14px;  /* Padding aumentado para usar o espaço extra */
        position:relative;
        overflow:hidden;
        margin-bottom:12px;
    }}
    .kpi-card::before {{ display:none; }}
    .kpi-label {{
        font-size:11px;  /* Aumentado ligeiramente para melhor legibilidade */
        font-weight:600;
        letter-spacing:0.5px;
        text-transform:uppercase;
        color:#6c7a89;
        line-height:1.0;
    }}
    .kpi-value {{
        font-size:18px;  /* Aumentado para destacar mais no espaço maior */
        font-weight:700;
        color:#1f2d3d;
        text-shadow:none;
        line-height:1.05;
    }}
    .kpi-perc {{
        font-size:10px;  /* Aumentado ligeiramente */
        font-weight:500;
        color:#8a99a8;
        line-height:1.0;
    }}
    .kpi-card:hover {{
        transform:translateY(-2px);
        box-shadow:0 4px 14px rgba(0,0,0,0.16);
        border-color:#c8d0d6;
    }}
    button[kind="secondary"][data-testid="stPopoverButton"] {{
      width:90% !important;
      max-width:90% !important;
      min-width:0 !important;
      box-sizing:border-box !important;
      margin:0 0 12px 0 !important;
      height:78px !important;
      padding:10px 12px !important;
      background:linear-gradient(145deg,#2c3e50 0%,#34495e 100%) !important;
      border:1px solid #34495e !important;
      border-radius:6px !important;
      box-shadow:0 4px 8px rgba(0,0,0,0.25) !important;
      color:#ecf0f1 !important;
      display:flex !important;
      flex-direction:column !important;
      justify-content:center !important;
      align-items:center !important;
      gap:6px !important;
      text-align:center !important;
      font-size:10px !important;
      line-height:1.0 !important;
      font-weight:500 !important;
      white-space:pre-line !important;
      position:relative !important;
      overflow:hidden !important;
      cursor:pointer !important;
    }}
    button[kind="secondary"][data-testid="stPopoverButton"]::before {{
      content:''; position:absolute; top:0; left:10px; right:10px; height:3px;
      background:linear-gradient(90deg,#3498db,#9b59b6,#e74c3c,#f39c12); border-radius:10px 10px 0 0;
    }}
    button[kind="secondary"][data-testid="stPopoverButton"]:hover {{
      transform:translateY(-2px) !important;
      box-shadow:0 6px 20px rgba(0,0,0,0.35) !important;
      border-color:#3498db !important;
      background:linear-gradient(145deg,#34495e 0%,#2c3e50 100%) !important;
    }}
    button[kind="secondary"][data-testid="stPopoverButton"] p {{
      margin:1px 0 !important;
      padding:0 !important;
      line-height:1.1 !important;
      width:100% !important;
      text-align:center !important;
    }}
    button[kind="secondary"][data-testid="stPopoverButton"] p:nth-of-type(1) {{
      font-size:14px !important;
      margin-bottom:2px !important;
      font-weight:600 !important;
      color:#bdc3c7 !important;
      text-transform:uppercase !important;
      letter-spacing:1px !important;
    }}
    button[kind="secondary"][data-testid="stPopoverButton"] p:nth-of-type(2) {{
      font-size:10px !important;
      font-weight:500 !important;
      color:#ecf0f1 !important;
    }}
    button[kind="secondary"][data-testid="stPopoverButton"] svg {{ display:none !important; }}
    div[role="dialog"][data-testid="stPopover"] {{
      width:{pop_width}px !important;
      min-width:{pop_width}px !important;
      max-width:{pop_width}px !important;
      height:640px !important;
      min-height:640px !important;
      max-height:85vh !important;
      margin:0 auto !important;
      padding:0 !important;
    }}
    div[role="dialog"][data-testid="stPopover"] > div {{
      width:{pop_width}px !important;
      max-width:{pop_width}px !important;
      height:100% !important;
      box-sizing:border-box !important;
      padding:18px 24px 26px 24px !important;
    }}
    div[role="dialog"][data-testid="stPopover"] .element-container {{
      width:100% !important; 
      max-width:100% !important;
    }}
    
    /* NOVAS REGRAS PARA GARANTIR LARGURA CONSISTENTE DOS GRÁFICOS */
    
    /* Força tabs dentro de popovers a usar largura total */
    div[role="dialog"][data-testid="stPopover"] div[data-testid="stTabs"] {{
        width: 100% !important;
        max-width: 100% !important;
    }}
    
    /* Força conteúdo das tabs (tabpanels) a usar largura total */
    div[role="dialog"][data-testid="stPopover"] div[role="tabpanel"] {{
        width: 100% !important;
        max-width: 100% !important;
        padding: 0 !important;
        margin: 0 !important;
    }}
    
    /* Força gráficos Plotly dentro de popovers a usar largura total */
    div[role="dialog"][data-testid="stPopover"] .js-plotly-plot,
    div[role="dialog"][data-testid="stPopover"] .plotly,
    div[role="dialog"][data-testid="stPopover"] .plot-container {{
        width: 100% !important;
        max-width: 100% !important;
    }}
    
    /* Força containers de gráficos dentro de tabs a usar largura total */
    div[role="dialog"][data-testid="stPopover"] div[role="tabpanel"] > div {{
        width: 100% !important;
        max-width: 100% !important;
    }}
    
    /* Força elemento iframe do Plotly a usar largura total */
    div[role="dialog"][data-testid="stPopover"] iframe[title*="plot"] {{
        width: 100% !important;
        max-width: 100% !important;
    }}
    
    /* Remove margens e paddings desnecessários dentro das tabs */
    div[role="dialog"][data-testid="stPopover"] div[data-testid="stVerticalBlock"] {{
        gap: 0 !important;
    }}
    
    @media (max-width:850px){{
      div[role="dialog"][data-testid="stPopover"],
      div[role="dialog"][data-testid="stPopover"] > div {{
        width:95vw !important; min-width:95vw !important; max-width:95vw !important;
        height:90vh !important; min-height:90vh !important; max-height:90vh !important;
        padding:14px 16px 22px 16px !important;
      }}
    }}
    </style>
    """, unsafe_allow_html=True)

# CSS para botões pills (movido de dentro da função main)
def css_pills_vendedores():
    st.markdown("""
    <style>
    .pill-btn button {
        border-radius: 999px !important;
        padding: 4px 10px !important;
        font-size: 16px !important;
        line-height: 1 !important;
        border: 1px solid #2563eb !important;
        background: #ffffff !important;
        color: #2563eb !important;
        box-shadow: none !important;
    }
    .pill-btn button:hover {
        background: #2563eb10 !important;
    }
    .pill-btn button:active {
        background: #2563eb25 !important;
        color:#0f172a !important;
    }
    .pill-btn.active button {
        background: linear-gradient(90deg,#2563eb,#1d4ed8) !important;
        color: #fff !important;
        border-color:#1d4ed8 !important;
    }
    .pill-btn button:focus {
        outline: none !important;
        box-shadow: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

def aplicar_css_header():
    # CSS para remover o espaço no topo e padding extra
    st.markdown("""
        <style>
        /* Oculta header/toolbar do Streamlit e decorações */
        header[data-testid="stHeader"] { display: none !important; }
        div[data-testid="stToolbar"] { display: none !important; }
        div[data-testid="stDecoration"] { display: none !important; }

        /* Zera o padding-top do container principal (sobrescreve o .block-container do app.py) */
        .main .block-container, .block-container {
            padding-top: 0.05rem !important;
            padding-bottom: 0.25rem !important;
        }

        /* Remove espaçamento extra das colunas no topo */
        div[data-testid="column"] { padding-top: 0 !important; }
        div[data-testid="column"] > div {
            margin-top: 0 !important;
            padding-top: 0 !important;
        }
        </style>
        """, unsafe_allow_html=True)

def aplicar_css_html():
    """Aplica CSS de forma mais robusta"""
    st.markdown("""
        <style>
        /* Popovers dos KPIs */
        button[data-testid="stPopoverButton"],
        .stApp button[data-testid="stPopoverButton"] {
            width: 100% !important;
            max-width: 100% !important;
            height: 108px !important;
            min-height: 108px !important;
            padding: 14px 10px !important;
            background: linear-gradient(145deg,#2c3e50 0%,#34495e 100%) !important;
            border: 1px solid #e6e9ef !important;
            border-radius: 10px !important;
            box-shadow: 0 4px 15px rgba(0,0,0,0.25) !important;
            color: #ecf0f1 !important;
            display: flex !important;
            flex-direction: column !important;
            justify-content: center !important;
            align-items: center !important;
            gap: 6px !important;
            text-align: center !important;
            position: relative !important;
            overflow: hidden !important;
            font-size: 13px !important;
            font-weight: 500 !important;
            line-height: 1.32 !important;
            white-space: pre-line !important;
            transition: all 0.3s ease !important;
            cursor: pointer !important;
        }

        /* Barra superior colorida */
        button[data-testid="stPopoverButton"]::before,
        .stApp button[data-testid="stPopoverButton"]::before {
            content: '';
            position: absolute;
            top: 0;
            left: 10px;
            right: 10px;
            height: 3px;
            background: linear-gradient(90deg,#3498db,#9b59b6,#e74c3c,#f39c12);
            border-radius: 10px 10px 0 0;
        }

        /* Título (primeiro parágrafo) */
        button[data-testid="stPopoverButton"] [data-testid="stMarkdownContainer"] p:nth-of-type(1),
        .stApp button[data-testid="stPopoverButton"] [data-testid="stMarkdownContainer"] p:nth-of-type(1) {
            font-size: 12px !important;
            margin-bottom: 2px !important;
            font-weight: 600 !important;
            color: #bdc3c7 !important;
            text-transform: uppercase !important;
            letter-spacing: 1px !important;
        }

        /* Valor (segundo parágrafo) */
        button[data-testid="stPopoverButton"] [data-testid="stMarkdownContainer"] p:nth-of-type(2),
        .stApp button[data-testid="stPopoverButton"] [data-testid="stMarkdownContainer"] p:nth-of-type(2) {
            font-size: 22px !important;
            font-weight: 700 !important;
            margin-bottom: 2px !important;
            color: #ecf0f1 !important;
            text-shadow: 0 1px 2px rgba(0,0,0,0.4) !important;
        }

        /* Centralizar conteúdo */
        button[data-testid="stPopoverButton"] [data-testid="stMarkdownContainer"],
        .stApp button[data-testid="stPopoverButton"] [data-testid="stMarkdownContainer"] {
            width: 100% !important;
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            justify-content: center !important;
            text-align: center !important;
        }

        /* Remover seta (chevron) */
        button[data-testid="stPopoverButton"] > div:last-of-type,
        .stApp button[data-testid="stPopoverButton"] > div:last-of-type {
            display: none !important;
        }

        /* Hover effect */
        button[data-testid="stPopoverButton"]:hover,
        .stApp button[data-testid="stPopoverButton"]:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(0,0,0,0.35) !important;
            border-color: #3498db !important;
            background: linear-gradient(145deg,#34495e 0%,#2c3e50 100%) !important;
        }

        /* Remover outline */
        button[data-testid="stPopoverButton"]:hover,
        button[data-testid="stPopoverButton"]:focus,
        .stApp button[data-testid="stPopoverButton"]:hover,
        .stApp button[data-testid="stPopoverButton"]:focus {
            outline: none !important;
        }

        /* Consistência de cores */
        button[data-testid="stPopoverButton"] *,
        .stApp button[data-testid="stPopoverButton"] * {
            color: inherit !important;
        }
                
        /* Largura mínima dos popovers */
        div[role="dialog"][data-testid="stPopover"] [data-baseweb="tab-panel"] {
            min-width: 650px !important;
            width: 100% !important;
            min-height: 600px !important;
        }
        
        div[role="dialog"][data-testid="stPopover"] [data-testid="element-container"] {
            min-width: 650px !important;
            width: 100% !important;
            min-height: 600px !important;
        }
        
        div[role="dialog"][data-testid="stPopover"] .js-plotly-plot,
        div[role="dialog"][data-testid="stPopover"] .stDataFrame {
            min-width: 650px !important;
            width: 100% !important;
            min-height: 600px !important;
        }
        </style>
    """, unsafe_allow_html=True)