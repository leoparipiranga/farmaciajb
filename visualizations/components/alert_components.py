import streamlit as st
from typing import Optional


def render_alert_card(categoria: str, nivel: str, janela: int, 
                     obtido: float, esperado: float, variacao_pct: float, 
                     status: str, label: Optional[str] = None):
    """Renderiza um card de alerta"""
    
    CARD_COLORS = {"normal": "#FFFFFF", "acima": "#5DD8A9", "abaixo": "#F1857D"}
    BORDER_COLORS = {"normal": "#DDDDDD", "acima": "#2ECC71", "abaixo": "#E74C3C"}
    
    bg = CARD_COLORS.get(status, "#FFFFFF")
    border = BORDER_COLORS.get(status, "#DDDDDD")
    
    # AJUSTE: Usar label se fornecido, senão usar categoria
    # Para produto_id, omitir o prefixo "produto_id:" 
    if nivel == "produto_id":
        titulo = f"{label or categoria} — {janela} dia(s)"
    else:
        titulo = f"{nivel}: {label or categoria} — {janela} dia(s)"
    
    var_txt = ("+" if variacao_pct >= 0 else "") + f"{variacao_pct*100:.1f}%"
    
    html = f"""
    <div style="background:{bg}; border:1px solid {border}; border-radius:10px; padding:10px; margin-bottom:10px;">
      <div style="font-weight:600; font-size:14px; margin-bottom:6px;">{titulo}</div>
      <div style="font-size:13px;">Obtido: <b>{int(round(obtido)):,}</b></div>
      <div style="font-size:13px;">Esperado: <b>{int(round(esperado)):,}</b></div>
      <div style="font-size:13px;">Variação: <b>{var_txt}</b></div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_cmv_card(filial: str, cmv_pct: float, custo: float, venda: float):
    """Renderiza card específico de CMV"""
    # Determinar label da filial
    if filial == "TODAS":
        titulo = "🏢 Todas as Filiais"
        bg_color = "#FFF5F5"
        border_color = "#DC143C"
    else:
        titulo = f"📍 Filial {filial}"
        bg_color = "#FDEDEC"
        border_color = "#E74C3C"
    
    html = f"""
    <div style="
        background:{bg_color}; 
        border:2px solid {border_color}; 
        border-radius:12px;
        padding:14px 16px; 
        margin-bottom:12px;
    ">
      <div style="font-weight:700; font-size:15px; color:#B03A2E; margin-bottom:8px;">
        {titulo}
      </div>
      <div style="font-size:24px; font-weight:800; color:#C0392B; margin:4px 0 6px;">
        CMV: {cmv_pct:.1f}%
      </div>
      <div style="font-size:12px; color:#7B7D7D;">
        Custo: R$ {custo:,.2f}
      </div>
      <div style="font-size:12px; color:#7B7D7D;">
        Vendas: R$ {venda:,.2f}
      </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def render_alert_page_css(n_anoms_qtd: int, n_anoms_cli: int, n_anoms_cmv: int):
    """Renderiza CSS específico da página de alertas"""
    css = f"""
    <style>
      [data-testid="stPopover"] {{
        position: relative !important;
      }}
      button[data-testid="stPopoverButton"] {{
        width: 100% !important;
        height: 140px !important;
        min-height: 140px !important;
        padding: 16px 20px !important;
        border-radius: 16px !important;
        border: 0 !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 22px !important;
        letter-spacing: 0.5px !important;
        box-shadow: 0 10px 24px rgba(0,0,0,0.25) !important;
        position: relative !important;
        transition: all 0.3s ease !important;
        overflow: hidden !important;
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
      }}
      /* Card 1 - Volume de Vendas (Azul escuro) */
      div[data-testid="stColumn"]:nth-of-type(1) button[data-testid="stPopoverButton"] {{
        background: linear-gradient(135deg, #191970 0%, #22308f 100%) !important;
      }}
      div[data-testid="stColumn"]:nth-of-type(1) button[data-testid="stPopoverButton"]:hover {{
        background: linear-gradient(135deg, #22308f 0%, #2a3fa5 100%) !important;
        transform: translateY(-2px) !important;
      }}
      /* Card 2 - Vendas Identificadas (Marrom) */
      div[data-testid="stColumn"]:nth-of-type(2) button[data-testid="stPopoverButton"] {{
        background: linear-gradient(135deg, #8B4513 0%, #9C4F1B 100%) !important;
      }}
      div[data-testid="stColumn"]:nth-of-type(2) button[data-testid="stPopoverButton"]:hover {{
        background: linear-gradient(135deg, #9C4F1B 0%, #A65A2A 100%) !important;
        transform: translateY(-2px) !important;
      }}
      /* Card 3 - CMV (Verde escuro) */
      div[data-testid="stColumn"]:nth-of-type(3) button[data-testid="stPopoverButton"] {{
        background: linear-gradient(135deg, #0B3D2E 0%, #145A32 100%) !important;
      }}
      div[data-testid="stColumn"]:nth-of-type(3) button[data-testid="stPopoverButton"]:hover {{
        background: linear-gradient(135deg, #145A32 0%, #1D7A46 100%) !important;
        transform: translateY(-2px) !important;
      }}
      /* Texto branco dentro dos botões */
      button[data-testid="stPopoverButton"] [data-testid="stMarkdownContainer"],
      button[data-testid="stPopoverButton"] [data-testid="stMarkdownContainer"] * {{
        color: #ffffff !important;
        opacity: 1 !important;
        visibility: visible !important;
        display: block !important;
        font-size: 26px !important;
        font-weight: 800 !important;
        line-height: 1.2 !important;
      }}
      /* Badge com números de anomalias */
      {"div[data-testid='stColumn']:nth-of-type(1) [data-testid='stPopover']::after { content: '" + str(n_anoms_qtd) + "'; }" if n_anoms_qtd > 0 else ""}
      {"div[data-testid='stColumn']:nth-of-type(2) [data-testid='stPopover']::after { content: '" + str(n_anoms_cli) + "'; }" if n_anoms_cli > 0 else ""}
      {"div[data-testid='stColumn']:nth-of-type(3) [data-testid='stPopover']::after { content: '" + str(n_anoms_cmv) + "'; }" if n_anoms_cmv > 0 else ""}
      [data-testid="stPopover"]::after {{
        position: absolute;
        top: 10px;
        right: 12px;
        width: 24px;
        height: 24px;
        border-radius: 50%;
        background: #E74C3C;
        color: #fff;
        font-size: 14px;
        font-weight: 700;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        animation: pulseBadge 1.2s infinite ease-in-out;
        z-index: 2;
        pointer-events: none;
      }}
      @keyframes pulseBadge {{
        0%   {{ transform: scale(1);   background: #E74C3C; }}
        50%  {{ transform: scale(1.1); background: #ffffff; color: #E74C3C; }}
        100% {{ transform: scale(1);   background: #E74C3C; }}
      }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
