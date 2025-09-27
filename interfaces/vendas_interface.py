# Importações dos módulos reorganizados
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
    vendas_por_classificacao_n1_mes_atual,
)

from visualizations.components.lojas_popovers import (
    render_popover_vendas_acumuladas,
    render_popover_num_vendas,
    render_popover_ticket_medio,
    render_popover_itens_por_nota,
    render_popover_vitaminas_vendidas,
    render_popover_conversao_vitaminas,
    render_popover_vendas_identificadas,
    render_popover_cmv,
    render_popover_descontos,
    render_popover_top_produtos,
    render_popover_analise_dia_hora,
    
    )

def render_vendas_interface():
    # Lógica principal da interface
    pass