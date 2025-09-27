import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, timedelta
from streamlit_extras.stylable_container import stylable_container
from calendar import monthrange

# Imports da nova estrutura
from core.database import duck_query
from visualizations.styling.css_components import (
    apply_cards_css_duck,
    apply_light_card_css,
    apply_classificacao_cards_css,
    aplicar_css_header
)
from visualizations.components.cards import (
    render_kpi_card_duck,
    render_kpi_card
)
from utils.formatters import (
    formatar_moeda,
    formatar_numero,
    formatar_numero_uma_casa,
    formatar_percentual
)
from data_processing.previsoes.previsoes import (
    calcular_previsao_mes_hibrido_sql
)
from data_processing.legacy.vendas_legacy import (
    carregar_metas
)
from visualizations.charts.gauges import (
    criar_gauge_plot,
    criar_gauge_invertido_plot
)
from data_processing.vendas.calculations import (
    venda_acumulada_mes_atual,
    venda_dezena1_mes_atual,
    venda_dezena2_mes_atual,
    venda_dezena3_mes_atual,
    cmv_percent_mes_atual,
    desconto_percent_mes_atual,
    conversao_vitaminas_percent_mes_atual,
    vendas_identificadas_percent_mes_atual,
    num_vendas_mes_atual,
    itens_por_nota_mes_atual,
    vitaminas_vendidas_mes_atual,
    vendas_por_classificacao_n1_mes_atual
)
from visualizations.components.lojas_popovers import (
    render_popover_vendas_acumuladas,
    render_popover_num_vendas,
    render_popover_ticket_medio,
    render_popover_itens_por_nota,
    render_popover_vitaminas_vendidas,
    render_popover_conversao_vitaminas,
    render_popover_cmv,
    render_popover_descontos,
    render_popover_vendas_identificadas,
    render_popover_top_produtos,
    render_popover_analise_dia_hora
)


# Funções de navegação para alertas
def ir_para_alertas_duck(filial_sel: str):
    """Navega para a página de alertas"""
    st.session_state['view'] = 'alertas_duck'
    st.session_state['filial_sel'] = filial_sel
    st.query_params.update({"view": "alertas_duck", "filial": str(filial_sel)})


def voltar_para_lojas_duck():
    """Volta da página de alertas para lojas"""
    st.session_state['view'] = 'lojas_duck'
    if 'filial_sel' in st.session_state:
        del st.session_state['filial_sel']
    st.query_params.clear()
    st.rerun()


def render():
    """Função principal de renderização"""
    # Verificar se deve renderizar alertas
    if st.session_state.get('view') == 'alertas_duck':
        from interfaces.alertas_interface import render_alertas_duck
        render_alertas_duck(
            filial_sel=st.session_state.get('filial_sel', 'Todas as Filiais'),
            on_voltar=voltar_para_lojas_duck,
            conn=None
        )
        return

    # Aplicar CSS
    aplicar_css_header()
    apply_light_card_css()
    apply_cards_css_duck()
    apply_classificacao_cards_css()

    # CSS customizado para popovers
    st.markdown("""
        <style>
        /* Popovers dos KPIs: fundo escuro, barra superior e altura igual ao ALERTAS (108px) */
        button[data-testid="stPopoverButton"] {
        width: 100% !important;
        max-width: 100% !important;
        height: 108px !important;
        min-height: 108px !important;
        padding: 14px 10px !important;
        background:linear-gradient(145deg,#2c3e50 0%,#34495e 100%) !important;
        border: 1px solid #e6e9ef !important;
        border-radius: 10px !important;
        box-shadow:0 4px 15px rgba(0,0,0,0.25) !important;
        color:#ecf0f1 !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
        align-items: center !important;
        gap: 6px !important;
        text-align: center !important;
        position: relative !important;
        overflow: hidden !important;
        font-size:13px !important;
        font-weight:500 !important;
        line-height:1.32 !important;
        white-space: pre-line !important;
        transition: all 0.3s ease !important;
        cursor: pointer !important;
        }

        /* Barra superior colorida */
        button[data-testid="stPopoverButton"]::before {
        content:'';
        position:absolute;
        top:0; left:10px; right:10px;
        height:3px;
        background:linear-gradient(90deg,#3498db,#9b59b6,#e74c3c,#f39c12);
        border-radius:10px 10px 0 0;
        }

        /* Título menor */
        button[data-testid="stPopoverButton"] [data-testid="stMarkdownContainer"] p:nth-of-type(1) {
        font-size:12px !important;
        margin-bottom:2px !important;
        font-weight:600 !important;
        color:#bdc3c7 !important;
        text-transform:uppercase !important;
        letter-spacing:1px !important;
        }

        /* Valor maior */
        button[data-testid="stPopoverButton"] [data-testid="stMarkdownContainer"] p:nth-of-type(2) {
        font-size:22px !important;
        font-weight:700 !important;
        margin-bottom:2px !important;
        color:#ecf0f1 !important;
        text-shadow:0 1px 2px rgba(0,0,0,0.4) !important;
        }

        /* Centraliza o conteúdo */
        button[data-testid="stPopoverButton"] [data-testid="stMarkdownContainer"] {
        width: 100% !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
        }

        /* Chevron no canto superior direito */
        button[data-testid="stPopoverButton"] > div:last-of-type {
        position: absolute !important;
        right: 10px !important;
        top: 10px !important;
        opacity: 0.75 !important;
        color: #c2c7cf !important;
        }

        /* Hover effect */
        button[data-testid="stPopoverButton"]:hover {
        transform:translateY(-2px) !important;
        box-shadow:0 6px 20px rgba(0,0,0,0.35) !important;
        border-color:#3498db !important;
        background:linear-gradient(145deg,#34495e 0%,#2c3e50 100%) !important;
        }

        /* Força largura mínima dos popovers */
        div[role="dialog"][data-testid="stPopover"] [data-baseweb="tab-panel"] {
            min-width: 650px !important;
            width: 100% !important;
        }
        
        div[role="dialog"][data-testid="stPopover"] [data-testid="element-container"] {
            min-width: 650px !important;
            width: 100% !important;
        }
        
        div[role="dialog"][data-testid="stPopover"] .js-plotly-plot,
        div[role="dialog"][data-testid="stPopover"] .stDataFrame {
            min-width: 650px !important;
            width: 100% !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # Buscar bounds de data
    bounds = duck_query("SELECT MIN(data_date) AS min_d, MAX(data_date) AS max_d FROM fact_vendas_final")
    min_d = pd.to_datetime(bounds.loc[0, "min_d"]).date()
    max_d = pd.to_datetime(bounds.loc[0, "max_d"]).date()

    # Filtro de Filial
    df_lojas = duck_query("""
        SELECT DISTINCT 
            CAST(filial_codigo AS VARCHAR) AS filial_codigo,
            COALESCE(filial_nome, CAST(filial_codigo AS VARCHAR)) AS filial_nome
        FROM fact_vendas_final
        WHERE filial_codigo IS NOT NULL
        ORDER BY filial_codigo
    """)
    
    col_filtro, col_spacer, col_data_info, col_prev = st.columns([3, 4.8, 2.2, 2.2], gap="small")
    
    with col_filtro:
        opcoes = ["Todas as Filiais"] + [f"{r.filial_codigo} - {r.filial_nome}" for _, r in df_lojas.iterrows()]
        sel = st.selectbox("Filial", options=opcoes, index=0)
        if sel == "Todas as Filiais":
            codigo_selecionado = "Todas as Filiais"
        else:
            codigo_selecionado = sel.split(" - ")[0]
           
    with col_data_info:
        _ontem = (date.today() - timedelta(days=1)).strftime("%d/%m/%Y")
        st.markdown(f"""
        <div style="color:#6b7280; font-size:12px; text-align:right; padding-top:8px;">
            Dados atualizados até {_ontem}
        </div>
        """, unsafe_allow_html=True)

    with col_prev:
        # Previsão
        prev = calcular_previsao_mes_hibrido_sql(
            None if codigo_selecionado == "Todas as Filiais" else str(codigo_selecionado),
            None  # usa D-1 por padrão
        )
        hi = prev.get('high'); mid = prev.get('previsto'); lo = prev.get('low')

        def fmt_safe(v):
            return formatar_moeda(v) if isinstance(v, (int, float)) and np.isfinite(v) else "—"

        _meses_pt = {
            1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
            5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
            9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
        }
        _hoje = date.today()
        _titulo_prev = f"Previsão ({_meses_pt.get(_hoje.month, str(_hoje.month))}/{_hoje.year})"

        st.markdown(f"""
        <div style="max-width: 190px; margin-left: auto;">
          <div style="
            background:#fff; border:1px solid #eee; border-radius:10px; padding:10px 12px;
            box-shadow:0 1px 3px rgba(0,0,0,0.08); text-align:right;">
            <div style="font-size:14px; color:#0f2d5c; font-weight:700; margin-bottom:8px;">{_titulo_prev}</div>
            <div style="font-size:12px; color:#0b7a36; line-height:1; white-space:nowrap;">
              <span style="color:#16a34a; font-weight:700; margin-right:6px;">▲</span>{fmt_safe(hi)}
            </div>
            <div style="font-size:22px; color:#0f2d5c; font-weight:800; line-height:1.2;">{fmt_safe(mid)}</div>
            <div style="font-size:12px; color:#991b1b; line-height:1; white-space:nowrap;">
              <span style="color:#dc2626; font-weight:700; margin-right:6px;">▼</span>{fmt_safe(lo)}
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # Carregar metas
    df_metas = carregar_metas()
    meta_vendas = 0.0
    if df_metas is not None:
        try:
            meta_vendas = float(df_metas.loc[codigo_selecionado, 'meta'])
        except Exception:
            try:
                meta_vendas = float(df_metas.loc['Todas as Filiais', 'meta'])
            except Exception:
                meta_vendas = 0.0

    # Buscar dados principais
    filial_param = None if codigo_selecionado == "Todas as Filiais" else str(codigo_selecionado)
    
    venda_acumulada = venda_acumulada_mes_atual(filial_param)
    d1_val = venda_dezena1_mes_atual(filial_param)
    d2_val = venda_dezena2_mes_atual(filial_param)
    d3_val = venda_dezena3_mes_atual(filial_param)
    cmv_atual = cmv_percent_mes_atual(filial_param)
    conversao_atual = conversao_vitaminas_percent_mes_atual(filial_param)
    desconto_atual = desconto_percent_mes_atual(filial_param)
    vendas_identificadas_atual = vendas_identificadas_percent_mes_atual(filial_param)

    # Calcular metas das dezenas
    dias_no_mes = monthrange(pd.Timestamp.today().year, pd.Timestamp.today().month)[1]
    meta_dia = (meta_vendas / dias_no_mes) if dias_no_mes else 0.0
    meta_d1, meta_d2 = meta_dia * 10, meta_dia * 10
    meta_d3 = meta_dia * max(0, dias_no_mes - 20)

    # Metas dos percentuais (placeholder)
    meta_cmv = 72.33
    meta_conversao = 20.0
    meta_desconto = 34.0
    meta_identificadas = 70.0

    # LINHA 1: 8 Gauges
    col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(8, gap='small')
    cfg = {'displayModeBar': False}
    
    with col1:
        st.plotly_chart(
            criar_gauge_plot(venda_acumulada, meta_vendas, "Meta Mensal Total"),
            use_container_width=True, config=cfg
        )
    with col2:
        st.plotly_chart(
            criar_gauge_plot(d1_val, meta_d1, "1ª Dezena (1-10)"), 
            use_container_width=True, config=cfg
        )
    with col3:
        st.plotly_chart(
            criar_gauge_plot(d2_val, meta_d2, "2ª Dezena (11-20)"), 
            use_container_width=True, config=cfg
        )
    with col4:
        st.plotly_chart(
            criar_gauge_plot(d3_val, meta_d3, "3ª Dezena (21-Fim)"), 
            use_container_width=True, config=cfg
        )
    with col5:
        st.plotly_chart(
            criar_gauge_invertido_plot(cmv_atual, meta_cmv, "CMV (%)"), 
            use_container_width=True, config=cfg
        )
    with col6:
        st.plotly_chart(
            criar_gauge_plot(conversao_atual, meta_conversao, "Conversão Vitaminas (%)"), 
            use_container_width=True, config=cfg
        )
    with col7:
        st.plotly_chart(
            criar_gauge_invertido_plot(desconto_atual, meta_desconto, "Desconto (%)"), 
            use_container_width=True, config=cfg
        )
    with col8:
        st.plotly_chart(
            criar_gauge_plot(vendas_identificadas_atual, meta_identificadas, "Vendas Identif. (%)"), 
            use_container_width=True, config=cfg
        )

    # Buscar dados para cards
    num_vendas = num_vendas_mes_atual(filial_param)
    ticket_medio = (venda_acumulada / num_vendas) if num_vendas > 0 else 0.0
    itens_por_nota = itens_por_nota_mes_atual(filial_param)
    vitaminas_vendidas = vitaminas_vendidas_mes_atual(filial_param)
    taxa_conv = conversao_vitaminas_percent_mes_atual(filial_param)

    # LINHA 2: 4 Cards KPI com popovers
    c1, c2, c3, c4 = st.columns(4, gap='small')
    
    with c1:
        label = f"💰 VENDA ACUMULADA\n\n{formatar_moeda(venda_acumulada)}"
        with st.popover(label=label, use_container_width=True, help="Clique para ver detalhes"):
            render_popover_vendas_acumuladas(filial_param)
    
    with c2:
        label = f"🛒 NÚMERO DE VENDAS\n\n{formatar_numero(num_vendas)}"
        with st.popover(label=label, use_container_width=True, help="Clique para ver detalhes"):
            render_popover_num_vendas(filial_param)
      
    with c3:
        label = f"🧾 TICKET MÉDIO\n\n{formatar_moeda(ticket_medio)}"
        with st.popover(label=label, use_container_width=True, help="Clique para ver detalhes"):
            render_popover_ticket_medio(filial_param)

    with c4:
        label = f"🏆 TOP 10 PRODUTOS"
        with st.popover(label=label, use_container_width=True, help="Clique para ver detalhes"):
            render_popover_top_produtos(filial_param)

    # LINHA 3: 4 Cards KPI com popovers
    c5, c6, c7, c8 = st.columns(4, gap='small')
    
    with c5:
        label = f"📦 ITENS POR NOTA\n\n{formatar_numero_uma_casa(itens_por_nota)}"
        with st.popover(label=label, use_container_width=True, help="Clique para ver detalhes"):
            render_popover_itens_por_nota(filial_param)

    with c6:
        label = f"💊 VITAMINAS VENDIDAS\n\n{formatar_numero(vitaminas_vendidas)}"
        with st.popover(label=label, use_container_width=True, help="Clique para ver detalhes"):
            render_popover_vitaminas_vendidas(filial_param)

    with c7:
        label = f"🔄 TAXA DE CONVERSÃO\n\n{formatar_numero_uma_casa(taxa_conv)}"
        with st.popover(label=label, use_container_width=True, help="Clique para ver detalhes"):
            render_popover_conversao_vitaminas(filial_param)
    
    with c8:
        label = f"⏰ ANÁLISE DIA/HORA"
        with st.popover(label=label, use_container_width=True, help="Clique para ver detalhes"):
            render_popover_analise_dia_hora(filial_param)

    # LINHA 4: 4 Cards KPI com popovers
    c9, c10, c11, c12 = st.columns(4, gap='small')
    
    with c9:
        label = f"📉 CMV (%)\n\n{formatar_numero_uma_casa(cmv_atual)}%"
        with st.popover(label=label, use_container_width=True, help="Clique para ver detalhes"):
            render_popover_cmv(filial_param)
    
    with c10:
        label = f"🏷️ DESCONTO (%)\n\n{formatar_percentual(desconto_atual)}"
        with st.popover(label=label, use_container_width=True, help="Clique para ver detalhes"):
            render_popover_descontos(filial_param)
    
    with c11:
        label = f"🆔 VENDAS IDENTIFICADAS (%)\n\n{formatar_percentual(vendas_identificadas_atual)}"
        with st.popover(label=label, use_container_width=True, help="Clique para ver detalhes"):
            render_popover_vendas_identificadas(filial_param)
    
    with c12:
        # Card ALERTAS - botão vermelho especial
        with stylable_container(
            key="alertas_kpi_card_duck",
            css_styles="""
            .stButton > button {
                width: 100% !important;
                max-width: 100% !important;
                margin: 13px 0 0 0 !important;
                height: 108px !important;
                padding: 14px 10px !important;
                background: linear-gradient(145deg,#7f1d1d 0%, #b91c1c 100%) !important;
                border: 1px solid #b91c1c !important;
                border-radius: 10px !important;
                box-shadow: 0 4px 15px rgba(0,0,0,0.25) !important;
                color: #ecf0f1 !important;
                font-size: 13px !important;
                font-weight: 700 !important;
                white-space: pre-line !important;
                transition: all 0.3s ease !important;
                cursor: pointer !important;
            }
            
            .stButton > button:hover {
                transform: translateY(-2px) !important;
                box-shadow: 0 6px 20px rgba(0,0,0,0.35) !important;
                border-color: #dc2626 !important;
                background: linear-gradient(145deg, #b91c1c 0%, #7f1d1d 100%) !important;
            }
            """
        ):
            st.button(
                "🚨 ALERTAS",
                key="alertas_kpi_card_duck",
                use_container_width=True,
                on_click=ir_para_alertas_duck,
                args=(str(codigo_selecionado),)
            )
    
    # LINHA 5: Classificação N1 (barra de progresso)
    df_cls = vendas_por_classificacao_n1_mes_atual(filial_param)

    # Configurações das classificações
    metas_classificacao = {"INDICAÇÃO": 0.30, "PRESCRIÇÃO": 0.33, "SBB": 0.04, "VAREJO": 0.12}
    limites_eixo = {"INDICAÇÃO": (0.15, 0.45), "PRESCRIÇÃO": (0.18, 0.48), "SBB": (0.00, 0.15), "VAREJO": (0.07, 0.17)}
    cores_classificacao = {"INDICAÇÃO": "forestgreen", "PRESCRIÇÃO": "lightcoral", "SBB": "cornflowerblue", "VAREJO": "darkkhaki"}
    ordem_classificacao = ["INDICAÇÃO", "PRESCRIÇÃO", "SBB", "VAREJO"]

    # Mapear dados do SQL
    map_venda = {str(r.classificacao_n1): float(r.venda_total) for _, r in df_cls.iterrows()}
    map_perc = {str(r.classificacao_n1): float(r.perc_total) for _, r in df_cls.iterrows()}
    venda_total_acumulada = float(venda_acumulada)

    cols = st.columns(4)
    for i, classificacao in enumerate(ordem_classificacao):
        with cols[i]:
            venda = map_venda.get(classificacao, 0.0)
            meta_perc = metas_classificacao[classificacao]
            realizado_perc = map_perc.get(classificacao, (venda / venda_total_acumulada if venda_total_acumulada > 0 else 0.0))

            # Lógica da barra de progresso
            min_eixo, max_eixo = limites_eixo[classificacao]
            range_eixo = max_eixo - min_eixo
            realizado_clamped = max(min_eixo, min(realizado_perc, max_eixo))
            meta_clamped = max(min_eixo, min(meta_perc, max_eixo))
            realizado_width_perc = ((realizado_clamped - min_eixo) / range_eixo) * 100 if range_eixo > 0 else 0
            meta_pos_perc = ((meta_clamped - min_eixo) / range_eixo) * 100 if range_eixo > 0 else 0

            st.markdown(f"""
            <div class="kpi-card-classificacao-verde">
                <div>
                    <div class="kpi-title">{classificacao}</div>
                    <div class="kpi-value">{formatar_moeda(venda)}</div>
                </div>
                <div class="progress-container-scaled">
                    <div class="axis-labels">
                        <span>{min_eixo:.0%}</span>
                        <span>Meta: {meta_perc:.1%}</span>
                        <span>{max_eixo:.0%}</span>
                    </div>
                    <div class="progress-bar-bg-scaled">
                        <div class="meta-marker" style="left: {meta_pos_perc}%;"></div>
                        <div class="progress-bar-scaled" style="width: {realizado_width_perc}%; background-color: {cores_classificacao[classificacao]};">
                            {realizado_perc:.1%}
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)


if __name__ == "__main__":
    render()