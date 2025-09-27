"""
Cálculos legacy para compatibilidade com pandas (será migrado para SQL)
"""
import streamlit as st
import pandas as pd
from datetime import date

@st.cache_data
def carregar_metas(caminho_arquivo="metas_julho.csv"):
    """Carrega o arquivo de metas e calcula o total para 'Todas as Filiais'."""
    try:
        df_metas = pd.read_csv(caminho_arquivo)
        # Garantir que o código da filial seja string para consistência
        df_metas['codigo'] = df_metas['codigo'].astype(str).str.zfill(2)
        
        # Calcular a meta total da rede
        meta_total_rede = df_metas['meta'].sum()
        
        # Criar uma nova linha para 'Todas as Filiais'
        todas_filiais_row = pd.DataFrame([{'codigo': 'Todas as Filiais', 'meta': meta_total_rede}])
        
        # Combinar com o DataFrame original
        df_metas_final = pd.concat([df_metas, todas_filiais_row], ignore_index=True)
        
        return df_metas_final.set_index('codigo')
    except FileNotFoundError:
        st.error(f"Arquivo de metas não encontrado em '{caminho_arquivo}'.")
        return None

@st.cache_data
def calcular_vendas_por_dezenas(df_vendas_completo, codigo_filial):
    """Calcula as vendas acumuladas para as três dezenas do mês atual."""
    if codigo_filial != 'Todas as Filiais':
        df_filtrado = df_vendas_completo[df_vendas_completo['codigo'] == codigo_filial].copy()
    else:
        df_filtrado = df_vendas_completo.copy()

    hoje = date.today()
    
    # Garante que a coluna de data é do tipo datetime
    df_filtrado['data_date'] = pd.to_datetime(df_filtrado['data_date'])
    
    # ✅ CORREÇÃO: Filtrar pelo ANO e MÊS atuais
    df_mes_atual = df_filtrado[
        (df_filtrado['data_date'].dt.month == hoje.month) &
        (df_filtrado['data_date'].dt.year == hoje.year)
    ].copy()

    # Adicionar a coluna 'dia' apenas no dataframe já filtrado pelo mês/ano
    df_mes_atual['dia'] = df_mes_atual['data_date'].dt.day

    vendas_d1 = df_mes_atual[df_mes_atual['dia'] <= 10]['item_valortotal'].sum()
    vendas_d2 = df_mes_atual[(df_mes_atual['dia'] > 10) & (df_mes_atual['dia'] <= 20)]['item_valortotal'].sum()
    vendas_d3 = df_mes_atual[df_mes_atual['dia'] > 20]['item_valortotal'].sum()

    return {
        "dezena1": vendas_d1,
        "dezena2": vendas_d2,
        "dezena3": vendas_d3
    }

def obter_top_vendedores_por_filial(df, filial_selecionada, ONTEM, top_n=10):
    """
    Retorna os top N vendedores de uma filial baseado nas vendas do mês atual
    """
    # Filtrar por filial se especificada
    if filial_selecionada != "Todas as Filiais":
        df_filtrado = df[df['nome_filial'] == filial_selecionada].copy()
    else:
        df_filtrado = df.copy()
    
    # Filtrar até ontem
    df_filtrado = df_filtrado[df_filtrado['data_venda_apenas'] <= ONTEM]
    
    # Dados do mês atual
    mes_atual = ONTEM.month
    ano_atual = ONTEM.year
    df_mes_atual = df_filtrado[
        (df_filtrado['data_venda_apenas'].dt.year == ano_atual) &
        (df_filtrado['data_venda_apenas'].dt.month == mes_atual)
    ]
    
    # Agrupar por vendedor e calcular vendas totais
    vendas_por_vendedor = df_mes_atual.groupby('vendedor_nome').agg({
        'item_valortotal': 'sum'
    }).reset_index()
    
    # Ordenar do maior para o menor e pegar top N
    top_vendedores = vendas_por_vendedor.sort_values('item_valortotal', ascending=False).head(top_n)
    
    return top_vendedores['vendedor_nome'].tolist()

def calcular_kpis_vendedor(df_vendedores, filial_selecionada, vendedor_selecionado, ontem):
    """Calcula KPIs para o vendedor selecionado"""
    if df_vendedores.empty:
        return {
            'venda_acumulada': 0.0,
            'num_vendas': 0,
            'ticket_medio': 0.0,
            'itens_por_nota': 0.0,
            'num_vitaminas': 0,
            'taxa_conversao_vitaminas': 0.0,
            'cmv': 0.0,
            'desconto_medio': 0.0,
            'vendas_identificadas_perc': 0.0
        }
    
    # Filtrar dados
    df = df_vendedores.copy()
    
    # Filtrar pelo mês atual
    if 'data_venda_apenas' in df.columns:
        inicio_mes = ontem.replace(day=1)
        df = df[(df['data_venda_apenas'] >= inicio_mes) & 
                (df['data_venda_apenas'] <= ontem)]
    
    # Filtrar por filial
    if filial_selecionada != "Todas as Filiais" and 'nome_filial' in df.columns:
        df = df[df['nome_filial'] == filial_selecionada]
    
    # Filtrar por vendedor
    if vendedor_selecionado != "Todos os Vendedores" and 'vendedor_nome' in df.columns:
        df = df[df['vendedor_nome'] == vendedor_selecionado]
    
    # Calcular KPIs
    kpis = {}
    
    # Venda acumulada
    kpis['venda_acumulada'] = df['item_valortotal'].sum() if 'item_valortotal' in df.columns else 0.0
    
    # Número de vendas
    if 'venda_id' in df.columns:
        kpis['num_vendas'] = df['venda_id'].nunique()
    elif 'venda_coo' in df.columns:
        kpis['num_vendas'] = df['venda_coo'].nunique()
    else:
        kpis['num_vendas'] = 0
    
    # Ticket médio
    kpis['ticket_medio'] = (kpis['venda_acumulada'] / kpis['num_vendas']) if kpis['num_vendas'] > 0 else 0.0
    
    # Itens por nota
    if 'item_quantidade' in df.columns and kpis['num_vendas'] > 0:
        kpis['itens_por_nota'] = df['item_quantidade'].sum() / kpis['num_vendas']
    else:
        kpis['itens_por_nota'] = 0.0
    
    # Vitaminas
    if 'classificacao_n1' in df.columns:
        df_vit = df[df['classificacao_n1'].str.upper() == 'VITAMINAS']
        kpis['num_vitaminas'] = df_vit['item_quantidade'].sum() if 'item_quantidade' in df_vit.columns else 0
        kpis['taxa_conversao_vitaminas'] = (df_vit['venda_id'].nunique() / kpis['num_vendas'] * 100) if kpis['num_vendas'] > 0 and 'venda_id' in df_vit.columns else 0.0
    else:
        kpis['num_vitaminas'] = 0
        kpis['taxa_conversao_vitaminas'] = 0.0
    
    # CMV
    if 'item_custototal' in df.columns and 'item_valortotal' in df.columns:
        total_custo = df['item_custototal'].sum()
        total_venda = df['item_valortotal'].sum()
        kpis['cmv'] = (total_custo / total_venda * 100) if total_venda > 0 else 0.0
    else:
        kpis['cmv'] = 0.0
    
    # Desconto médio
    if 'item_descontopercentual' in df.columns:
        kpis['desconto_medio'] = df['item_descontopercentual'].mean()
    else:
        kpis['desconto_medio'] = 0.0
    
    # Vendas identificadas
    if 'vendedor_nome' in df.columns:
        vendas_com_vendedor = df[df['vendedor_nome'].notna() & (df['vendedor_nome'] != '')]
        if 'venda_id' in vendas_com_vendedor.columns:
            num_vendas_ident = vendas_com_vendedor['venda_id'].nunique()
        elif 'venda_coo' in vendas_com_vendedor.columns:
            num_vendas_ident = vendas_com_vendedor['venda_coo'].nunique()
        else:
            num_vendas_ident = 0
        kpis['vendas_identificadas_perc'] = (num_vendas_ident / kpis['num_vendas'] * 100) if kpis['num_vendas'] > 0 else 0.0
    else:
        kpis['vendas_identificadas_perc'] = 0.0
    
    return kpis
