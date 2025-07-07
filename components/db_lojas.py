import pandas as pd
from datetime import datetime, timedelta
from components.db_df import df, DATA_ATUAL_SIMULADA  # Importa o DataFrame df do módulo db_df
import plotly.express as px
import calendar

# Simulação da data atual para o dashboard
# Certifique-se de que o ANO aqui corresponde ao ano dos seus dados de abril/maio

def calcular_kpi_vendas_loja(df_vendas):
    """Calcula o KPI de venda acumulada no mês e venda do dia anterior."""
    if df_vendas.empty or 'data_venda_apenas' not in df_vendas.columns or 'valor_total' not in df_vendas.columns:
        print("DataFrame de vendas está vazio ou colunas necessárias ('data_venda_apenas', 'valor_total') ausentes.")
        return 0, 0

    # A coluna 'data_venda_apenas' já foi convertida para objetos datetime.date
    # em carregar_dados_vendas. Não é necessário reconverter aqui.

    df_vendas['data_venda_apenas'] = pd.to_datetime(df_vendas['data_venda_apenas']).dt.date
    data_dia_anterior = DATA_ATUAL_SIMULADA - timedelta(days=1)

    mes_atual = DATA_ATUAL_SIMULADA.month
    ano_atual = DATA_ATUAL_SIMULADA.year
    dia_atual_simulado = DATA_ATUAL_SIMULADA.day

    # Filtrar para o mês atual até o dia simulado
    # Assegura que estamos comparando objetos datetime.date
    # e que os elementos da série são objetos date válidos antes de acessar .month, .year, .day
    vendas_mes_atual_acumulada = df_vendas[
        (df_vendas['data_venda_apenas'].apply(lambda x: x.month if pd.notnull(x) and hasattr(x, 'month') else -1) == mes_atual) &
        (df_vendas['data_venda_apenas'].apply(lambda x: x.year if pd.notnull(x) and hasattr(x, 'year') else -1) == ano_atual) &
        (df_vendas['data_venda_apenas'].apply(lambda x: x.day if pd.notnull(x) and hasattr(x, 'day') else -1) <= dia_atual_simulado)
    ]
    venda_total_mes_acumulada = vendas_mes_atual_acumulada['item_valortotal'].sum()
    
    # Compara diretamente com o objeto datetime.date
    vendas_dia_anterior = df_vendas[df_vendas['data_venda_apenas'] == data_dia_anterior]
    # Usando 'valor_total' para consistência com o KPI de "Venda".
    # Se 'item_valortotal' for o correto para esta parte, ajuste abaixo.
    venda_total_dia_anterior = vendas_dia_anterior['item_valortotal'].sum()

    return venda_total_mes_acumulada, venda_total_dia_anterior

def carregar_dados_metas(caminho_arquivo_metas="base/metas.csv"):
    """Carrega os dados de metas."""
    try:
        # Você mencionou que o separador é ';'
        df_metas = pd.read_csv(caminho_arquivo_metas, sep=';')
        return df_metas
    except FileNotFoundError:
        print(f"Erro: Arquivo de metas não encontrado em {caminho_arquivo_metas}")
        return pd.DataFrame()
    except Exception as e:
        print(f"Erro ao carregar dados de metas: {e}")
        return pd.DataFrame()

def calcular_kpis(df_vendas, data_atual):
    # Acumulado mês
    vendas_mes = df_vendas[
        (df_vendas['data_venda_apenas'].apply(lambda x: x.month) == data_atual.month) &
        (df_vendas['data_venda_apenas'].apply(lambda x: x.year) == data_atual.year) &
        (df_vendas['data_venda_apenas'].apply(lambda x: x.day) <= data_atual.day)
    ]
    venda_total_mes = vendas_mes['item_valortotal'].sum()
    ticket_medio_mes = vendas_mes['item_valortotal'].sum() / vendas_mes['venda_coo'].nunique() if vendas_mes['venda_coo'].nunique() > 0 else 0
    itens_por_nota_mes = vendas_mes['item_quantidade'].sum() / vendas_mes['venda_coo'].nunique() if vendas_mes['venda_coo'].nunique() > 0 else 0

    # Dia anterior
    data_dia_anterior = data_atual - timedelta(days=1)
    vendas_dia_ant = df_vendas[df_vendas['data_venda_apenas'] == data_dia_anterior]
    venda_total_dia_ant = vendas_dia_ant['item_valortotal'].sum()
    ticket_medio_dia_ant = vendas_dia_ant['item_valortotal'].sum() / vendas_dia_ant['venda_coo'].nunique() if vendas_dia_ant['venda_coo'].nunique() > 0 else 0
    itens_por_nota_dia_ant = vendas_dia_ant['item_quantidade'].sum() / vendas_dia_ant['venda_coo'].nunique() if vendas_dia_ant['venda_coo'].nunique() > 0 else 0

    return {
        "venda_total_mes": venda_total_mes,
        "venda_total_dia_ant": venda_total_dia_ant,
        "ticket_medio_mes": ticket_medio_mes,
        "ticket_medio_dia_ant": ticket_medio_dia_ant,
        "itens_por_nota_mes": itens_por_nota_mes,
        "itens_por_nota_dia_ant": itens_por_nota_dia_ant
    }

def format_brl(number):
    # Formata com 2 casas decimais usando o padrão en_US e depois substitui
    formatted = "{:,.3f}".format(number)
    # Troca vírgulas por ponto e vice-versa:
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return formatted

def abbreviate_brl(value):
    if value >= 1_000_000:
        # Formata em milhões com 3 casas decimais
        return format_brl(value/1_000_000) + " M"
    elif value >= 10_000:
        # Formata em milhares com 1 casa decimal
        return format_brl(round(value/1000, 1)) + " mil"
    else:
        return format_brl(value)

# Filtro para o mês corrente até DATA_ATUAL_SIMULADA
def filtro_mes_corrente(df, data_col, data_atual):
    return df[
        (df[data_col].apply(lambda x: x.month) == data_atual.month) &
        (df[data_col].apply(lambda x: x.year) == data_atual.year) &
        (df[data_col].apply(lambda x: x.day) <= data_atual.day)
    ]

def calcular_projecoes(df_vendas, data_atual):
    """
    Retorna (venda_projetada, resultado_projetado) para o mês corrente,
    projetando vendas e resultado bruto com base no ritmo até ontem.
    """
    # dias decorrido no mês (até dia anterior)
    dias_decorridos = data_atual.day - 1
    total_dias = calendar.monthrange(data_atual.year, data_atual.month)[1]

    # filtra vendas do mês até o dia anterior
    df_mes = filtro_mes_corrente(df_vendas, 'data_venda_apenas', data_atual)
    # soma vendas e calcula resultado bruto até agora
    venda_ate_hoje = df_mes['item_valortotal'].sum()
    custo_ate_hoje = (df_mes['customedio'] * df_mes['item_quantidade']).sum()
    resultado_ate_hoje = venda_ate_hoje - custo_ate_hoje

    if dias_decorridos > 0:
        venda_projetada   = venda_ate_hoje   / dias_decorridos * total_dias
        resultado_projetado = resultado_ate_hoje / dias_decorridos * total_dias
    else:
        venda_projetada = resultado_projetado = 0

    return venda_projetada, resultado_projetado

def grafico_ticket_medio(df):
    df = df.copy()
    df['mes_ano'] = df['data_venda_apenas'].apply(lambda x: f"{x.month:02d}-{x.year}")
    df_agg = (
        df.groupby('mes_ano').agg(
            valor_total=('item_valortotal', 'sum'),
            num_vendas=('venda_coo', 'nunique')
        ).reset_index()
    )
    df_agg['ticket_medio'] = df_agg['valor_total'] / df_agg['num_vendas']
    fig = px.bar(
        df_agg,
        x='mes_ano',
        y='ticket_medio',
        text=df_agg['ticket_medio'].apply(lambda x: f"R$ {x:,.2f}"),
        color_discrete_sequence=["limegreen"]
    )
    fig.update_traces(textposition='outside')
    fig.update_layout(
        yaxis=dict(showticklabels=False),
        yaxis_title=None,
        xaxis_title=None,
        margin=dict(t=100, b=20, l=20, r=20)
    )
    return fig

def grafico_desc_medio(df_filtrado):
    df_filtrado['mes_ano'] = df_filtrado['data_venda_apenas'].apply(lambda x: f"{x.month:02d}-{x.year}")

    # Calcular desconto médio por mês
    df_desc_agg = (
        df_filtrado.groupby('mes_ano').agg(
            desconto_total=('item_desconto', 'sum'),
            valor_total=('item_valortotal', 'sum')
        )
        .reset_index()
    )
    df_desc_agg['desconto_medio'] = (df_desc_agg['desconto_total'] / df_desc_agg['valor_total'] * 100).fillna(0)
    # Gráfico
    fig_desc = px.bar(
        df_desc_agg,
        x='mes_ano',
        y='desconto_medio',
        text=df_desc_agg['desconto_medio'].apply(lambda x: f"{x:.1f}%"),
        color_discrete_sequence=["indianred"]
    )

    fig_desc.update_traces(
        textposition='outside'
    )
    fig_desc.update_layout(
        yaxis=dict(showticklabels=False),
        yaxis_title=None,
        xaxis_title=None,
        margin=dict(t=100, b=20, l=20, r=20)
    )
    return fig_desc


def grafico_cmv(df_filtrado):
    df_filtrado['mes_ano'] = df_filtrado['data_venda_apenas'].apply(lambda x: f"{x.month:02d}-{x.year}")
    # Calcular valores auxiliares
    df_filtrado['custo_total'] = df_filtrado['customedio'] * df_filtrado['item_quantidade']
    df_filtrado['resultado_bruto'] = df_filtrado['item_valortotal'] - df_filtrado['custo_total']
    # Agrupar por mês
    df_cmv_agg = (
        df_filtrado.groupby('mes_ano').agg(
            custo_total=('custo_total', 'sum'),
            valor_total=('item_valortotal', 'sum'),
            resultado_bruto=('resultado_bruto', 'sum')
        )
        .reset_index()
    )
    df_cmv_agg['cmv_percent'] = (df_cmv_agg['custo_total'] / df_cmv_agg['valor_total'] * 100).fillna(0)
    # 1) Gráfico de evolução do CMV (%)
    fig_cmv = px.bar(
        df_cmv_agg,
        x='mes_ano',
        y='cmv_percent',
        text=df_cmv_agg['cmv_percent'].apply(lambda x: f"{x:.1f}%"),
        color_discrete_sequence=["Tan"]
    )
    fig_cmv.update_traces(textposition='outside')
    fig_cmv.update_layout(
        yaxis=dict(showticklabels=False),
        yaxis_title=None,
        xaxis_title=None,
        margin=dict(t=100, b=20, l=20, r=20)
    )
    return fig_cmv

def grafico_resultado_bruto(df_filtrado):
    df_filtrado['mes_ano'] = df_filtrado['data_venda_apenas'].apply(lambda x: f"{x.month:02d}-{x.year}")
    # Calcular valores auxiliares
    df_filtrado['custo_total'] = df_filtrado['customedio'] * df_filtrado['item_quantidade']
    df_filtrado['resultado_bruto'] = df_filtrado['item_valortotal'] - df_filtrado['custo_total']
    # Agrupar por mês
    df_cmv_agg = (
        df_filtrado.groupby('mes_ano').agg(
            custo_total=('custo_total', 'sum'),
            valor_total=('item_valortotal', 'sum'),
            resultado_bruto=('resultado_bruto', 'sum')
        )
        .reset_index()
    )
    df_cmv_agg['cmv_percent'] = (df_cmv_agg['custo_total'] / df_cmv_agg['valor_total'] * 100).fillna(0)
    fig_rb = px.bar(
            df_cmv_agg,
            x='mes_ano',
            y='resultado_bruto',
            text=df_cmv_agg['resultado_bruto'].apply(lambda x: f"R$ {x:,.2f}"),
            color_discrete_sequence=["coral"]
        )
    fig_rb.update_traces(textposition='outside')
    fig_rb.update_layout(
        yaxis=dict(showticklabels=False),
        yaxis_title=None,
        xaxis_title=None,
        margin=dict(t=100, b=20, l=20, r=20)
    )
    return fig_rb


