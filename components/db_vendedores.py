import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from components.db_df import df, DATA_ATUAL_SIMULADA  # Importa o DataFrame df do módulo db_df
import plotly.express as px
import calendar


# Converter DATA_ATUAL_SIMULADA para pd.Timestamp para os cálculos:
data_fim = pd.Timestamp(DATA_ATUAL_SIMULADA) - pd.Timedelta(days=1)
data_inicio = data_fim - pd.Timedelta(days=90)

# Converter a coluna de data/hora, se ainda não estiver em datetime
df['venda_datahorafechamento'] = pd.to_datetime(df['venda_datahorafechamento'], format='%Y-%m-%d %H:%M:%S')

# Filtrar os últimos 90 dias (até hoje - 1)
df_90 = df[(df['venda_datahorafechamento'] >= data_inicio) & (df['venda_datahorafechamento'] <= data_fim)].copy()

# Extrair a hora de venda
df_90['hora'] = df_90['venda_datahorafechamento'].dt.hour

# Agrupar por filial e hora, calculando o ticket médio = total de item_valortotal / número de vendas únicas (venda_coo)
ticket_por_hora = (
    df_90.groupby(['filial_nome', 'hora'])
         .agg(
             total_valor=('item_valortotal', 'sum'),
             n_vendas=('venda_coo', 'nunique')
         )
         .reset_index()
)

ticket_por_hora['ticket_medio'] = ticket_por_hora['total_valor'] / ticket_por_hora['n_vendas']

vendas_vendedores_por_hora = (
    df_90.groupby(['nome_vendedor', 'hora'])
         .agg(n_vendas=('venda_coo', 'nunique'))
         .reset_index()
)

def calcular_metas_vendedores(df, df_ticket_por_hora):
    """
    Calcula para cada vendedor:
      - filial_nome
      - nome_vendedor
      - Número total de vendas únicas da loja (venda_coo) 
      - Número de vendas únicas do vendedor
      - Ticket médio geral da loja  
      - Ticket médio das horas em que o vendedor tem vendas  
      - Meta do vendedor = (vendas_vendedor / vendas_loja) * (ticket_medio_vendedor / ticket_medio_loja)
    Retorna um DataFrame com esses dados.
    """
    import numpy as np

    resultados = []
    
    # Itera sobre cada vendedor único no DataFrame
    for vendedor in df['nome_vendedor'].unique():
        df_vend = df[df['nome_vendedor'] == vendedor]
        if df_vend.empty:
            continue
        # Supõe que o vendedor atua em uma única loja
        loja = df_vend['filial_nome'].iloc[0]
        
        # Total de vendas da loja (venda_coo únicos)
        vendas_loja = df[df['filial_nome'] == loja]['venda_coo'].nunique()
        # Vendas do vendedor (venda_coo únicos)
        vendas_vend = df_vend['venda_coo'].nunique()
        proporcao_vendas = vendas_vend / vendas_loja if vendas_loja > 0 else np.nan
        
        # Horas em que o vendedor tem vendas
        horas_vendedor = df_vend['hora'].unique()
        
        # Ticket médio da loja apenas nas horas de atuação do vendedor
        df_ticket_vend = df_ticket_por_hora[
            (df_ticket_por_hora['filial_nome'] == loja) & 
            (df_ticket_por_hora['hora'].isin(horas_vendedor))
        ]
        ticket_medio_vend = df_ticket_vend['ticket_medio'].mean() if not df_ticket_vend.empty else np.nan
        
        # Ticket médio geral da loja (todas as horas)
        df_ticket_loja = df_ticket_por_hora[df_ticket_por_hora['filial_nome'] == loja]
        ticket_medio_loja = df_ticket_loja['ticket_medio'].mean() if not df_ticket_loja.empty else np.nan
        
        # Ponderação: razão entre o ticket médio nas horas do vendedor e o geral da loja
        ponderacao = ticket_medio_vend / ticket_medio_loja if (ticket_medio_loja and ticket_medio_loja > 0) else np.nan
        
        # Meta do vendedor: produto da proporção de vendas pela ponderação
        meta = proporcao_vendas * ponderacao if (not np.isnan(proporcao_vendas) and not np.isnan(ponderacao)) else np.nan
        
        resultados.append({
            "filial_nome": loja,
            "nome_vendedor": vendedor,
            "vendas_loja": vendas_loja,
            "vendas_vendedor": vendas_vend,
            "ticket_medio_loja": ticket_medio_loja,
            "ticket_medio_vendedor": ticket_medio_vend,
            "meta_vendedor": meta
        })
        
    return pd.DataFrame(resultados)

df_metas_vendedores = calcular_metas_vendedores(df, ticket_por_hora)

def calcular_escada_100(df, df_metas_vendedores, df_metas):
    """
    Calcula a comissão dos vendedores segundo a metodologia "Escada 100".

    Parâmetros:
      df: DataFrame de vendas com colunas como 'filial_nome', 'nome_vendedor', 
          'venda_coo', 'item_valortotal', 'customedio', 'item_quantidade',
          'class_painome' e 'classificacao_nome'
      df_metas_vendedores: DataFrame com 'filial_nome', 'nome_vendedor', 'meta_vendedor'
                           (valor entre 0 e 1, que representa a proporção da meta do vendedor)
      df_metas: DataFrame com as metas da loja contendo as colunas
                'filial_nome', 'meta', 'meta_indicacao', 'meta_sbb', 'meta_vitamina'
                (obs.: para teleentrega, usei meta_sbb como proxy; ajuste se necessário)
    
    Procedimento:
      (a) Determina a filial de cada vendedor a partir de df, considerando a loja onde
          ele realizou o maior número de vendas.
      (b) Faz merge desse resultado com df_metas para trazer as metas da loja.
      (c) Faz merge com df_metas_vendedores para trazer o valor de meta_vendedor do vendedor.
      (d) Calcula, para cada vendedor, as vendas acumuladas em cada categoria:
             - Vendas geral – soma de item_valortotal para o vendedor.
             - Vendas INDICAÇÃO: soma onde class_painome contém "INDICAÇÃO".
             - Vendas SBB: soma onde class_painome contém "SBB".
             - Vendas VITAMINA: soma onde classificacao_nome contém "VITAMINA".
      (e) O degrau da categoria é calculado como:
             degrau_categoria = floor( (vendas_categoria / meta_categoria) * 25 )
          de forma que, se o vendedor atingir sua meta na categoria, degrau = 25.
      (f) O degrau total é a soma dos degraus de todas as categorias (geral, indicação, SBB e vitamina).
      (g) Em seguida, é atribuída a performance e a comissão para cada categoria conforme faixas:
             Genéricos (meta geral): base = 3%
                  <15: "Insatisfatório" → 3% - 1%
                  15-20: "Abaixo da Média" → 3%
                  21-24: "Satisfatório" → 3% + 1%
                  25-28: "Acima da Média" → 3% + 2%
                  ≥29: "Excepcional" → 3% + 3%
             Vitaminas: base = 5%
                  <15: "Insatisfatório" → 5% - 5%
                  15-20: "Abaixo da Média" → 5%
                  21-24: "Satisfatório" → 5% + 3%
                  25-28: "Acima da Média" → 5% + 7%
                  ≥29: "Excepcional" → 5% + 10%
             SBB (usando meta_indicacao): base = 1%
                  <15: "Insatisfatório" → 1% - 1%
                  15-20: "Abaixo da Média" → 1%
                  21-24: "Satisfatório" → 1% + 0.5%
                  25-28: "Acima da Média" → 1% + 1%
                  ≥29: "Excepcional" → 1% + 2%
      (h) Se o degrau_total ultrapassar 100, adiciona-se bonus de 1 ponto percentual em cada
          categoria (genéricos, vitaminas e SBB).
    
    Retorna um DataFrame com as seguintes colunas:
       'filial_nome', 'nome_vendedor', 'meta_vendedor', 
       'meta', 'meta_indicacao', 'meta_sbb', 'meta_vitamina',
       'total_geral', 'total_indicacao', 'total_sbb', 'total_vitamina',
       'degrau_geral', 'degrau_indicacao', 'degrau_sbb', 'degrau_vitamina',
       'degrau_total',
       'perf_geral', 'comm_geral', 'perf_vitamina', 'comm_vitamina', 'perf_sbb', 'comm_sbb'
    """
    # (a) Determinar a filial de cada vendedor (loja com mais vendas)
    df_vend_store = (df.groupby(['nome_vendedor', 'filial_nome'])
                        .agg(vendas=('venda_coo', 'nunique'))
                        .reset_index())
    df_vend_store = df_vend_store.sort_values(['nome_vendedor', 'vendas'], ascending=[True, False])
    df_vend_store = df_vend_store.drop_duplicates(subset=['nome_vendedor'], keep='first')
    df_vend_store = df_vend_store[['nome_vendedor', 'filial_nome']]
    
    # (b) Merge com df_metas (loja)
    df_meta = pd.merge(df_vend_store, df_metas, on='filial_nome', how='left')
    
    # (c) Merge com df_metas_vendedores para trazer 'meta_vendedor'
    df_meta = pd.merge(df_meta, df_metas_vendedores[['nome_vendedor', 'meta_vendedor']], on='nome_vendedor', how='left')

    # Calcular as metas específicas para cada categoria:
    df_meta['meta_vend_geral'] = df_meta['meta_vendedor'] * df_meta['meta']
    df_meta['meta_vend_indicacao'] = df_meta['meta_vendedor'] * df_meta['meta_indicacao']
    df_meta['meta_vend_sbb'] = df_meta['meta_vendedor'] * df_meta['meta_sbb']
    df_meta['meta_vend_vitamina'] = df_meta['meta_vendedor'] * df_meta['meta_vitamina']
    
    # (d) Calcular vendas acumuladas por vendedor (para o período analisado)
    # Total geral
    df_total = df.groupby('nome_vendedor').agg(total_geral=('item_valortotal','sum')).reset_index()
    
    # Vendas em INDICAÇÃO – usando class_painome
    mask_indicacao = df['class_painome'].str.upper().str.contains("INDICAÇÃO", na=False)
    df_indicacao = (df[mask_indicacao]
                    .groupby('nome_vendedor')
                    .agg(total_indicacao=('item_valortotal', 'sum'))
                    .reset_index())
                    
    # Vendas em SBB – usando class_painome
    mask_sbb = df['class_painome'].str.upper().str.contains("SBB", na=False)
    df_sbb = (df[mask_sbb]
              .groupby('nome_vendedor')
              .agg(total_sbb=('item_valortotal', 'sum'))
              .reset_index())
    
    # Vendas em VITAMINA – usando classificacao_nome
    mask_vitamina = df['classificacao_nome'].str.upper().str.contains("VITAMINA", na=False)
    df_vitamina = (df[mask_vitamina]
                   .groupby('nome_vendedor')
                   .agg(total_vitamina=('item_valortotal', 'sum'))
                   .reset_index())
    
    # Merge as vendas com o df_meta
    df_meta = pd.merge(df_meta, df_total, on='nome_vendedor', how='left')
    df_meta = pd.merge(df_meta, df_indicacao, on='nome_vendedor', how='left')
    df_meta = pd.merge(df_meta, df_sbb, on='nome_vendedor', how='left')
    df_meta = pd.merge(df_meta, df_vitamina, on='nome_vendedor', how='left')
    
    # Preencha NaN com 0
    for col in ['total_geral', 'total_indicacao', 'total_sbb', 'total_vitamina']:
        df_meta[col] = df_meta[col].fillna(0)
    
    # (e) Calcular degraus para cada categoria: 
    # A fórmula: degrau = floor( (vendas_acumuladas / meta_categoria) * 25 )
    df_meta['degrau_geral'] = np.floor((df_meta['total_geral'] / df_meta['meta_vend_geral']) * 25)
    df_meta['degrau_indicacao'] = np.floor((df_meta['total_indicacao'] / df_meta['meta_vend_indicacao']) * 25)
    df_meta['degrau_sbb'] = np.floor((df_meta['total_sbb'] / df_meta['meta_vend_sbb']) * 25)
    df_meta['degrau_vitamina'] = np.floor((df_meta['total_vitamina'] / df_meta['meta_vend_vitamina']) * 25)
    
    # (f) Degrau total como soma dos degraus individuais:
    df_meta['degrau_total'] = (df_meta['degrau_geral'] + df_meta['degrau_indicacao'] +
                               df_meta['degrau_sbb'] + df_meta['degrau_vitamina'])
    
    # (g) Definir função para determinar performance e comissão de cada categoria
    def classificacao_e_comm(degrau, base, ajuste_insat, ajuste_satisf, ajuste_acima, ajuste_excep):
        if degrau < 15:
            return "Insatisfatório", base - ajuste_insat
        elif degrau < 21:
            return "Abaixo da Média", base
        elif degrau < 25:
            return "Satisfatório", base + ajuste_satisf
        elif degrau < 29:
            return "Acima da Média", base + ajuste_acima
        else:
            return "Excepcional", base + ajuste_excep

    # (h) Calcular performance e comissão para cada categoria:
    # Para genéricos (meta geral): base = 3%
    perf_comm_indicacao = df_meta['degrau_indicacao'].apply(lambda d: classificacao_e_comm(d, 3, 1, 1, 2, 3))
    df_meta['perf_indicacao'] = perf_comm_indicacao.apply(lambda x: x[0])
    df_meta['comm_indicacao'] = perf_comm_indicacao.apply(lambda x: x[1] / 100)
    
    # Para vitaminas: base = 5%
    perf_comm_vitamina = df_meta['degrau_vitamina'].apply(lambda d: classificacao_e_comm(d, 5, 5, 0, 3, 10))
    df_meta['perf_vitamina'] = perf_comm_vitamina.apply(lambda x: x[0])
    df_meta['comm_vitamina'] = perf_comm_vitamina.apply(lambda x: x[1] / 100)
    
    # Para SBB: usando o degrau de INDICAÇÃO (meta_indicacao) com base = 1%
    perf_comm_sbb = df_meta['degrau_indicacao'].apply(lambda d: classificacao_e_comm(d, 1, 1, 0.5, 1, 2))
    df_meta['perf_sbb'] = perf_comm_sbb.apply(lambda x: x[0])
    df_meta['comm_sbb'] = perf_comm_sbb.apply(lambda x: x[1] / 100)
    
    # (i) Regra adicional: se o degrau_total exceder 100, adicionar 1% extra em cada categoria (geral, vitaminas e SBB)
    bonus_mask = df_meta['degrau_total'] > 100
    df_meta.loc[bonus_mask, 'comm_indicacao'] += .01
    df_meta.loc[bonus_mask, 'comm_vitamina'] += .01
    df_meta.loc[bonus_mask, 'comm_sbb'] += .01

    # Calcular valores de comissão por categoria
    df_meta['comissao_indicacao'] = df_meta['comm_indicacao'] * df_meta['total_indicacao']
    df_meta['comissao_vitamina'] = df_meta['comm_vitamina'] * df_meta['total_vitamina']
    df_meta['comissao_sbb'] = df_meta['comm_sbb'] * df_meta['total_sbb']
    df_meta['comissao_total'] = (df_meta['comissao_indicacao'] +
                                    df_meta['comissao_vitamina'] + 
                                    df_meta['comissao_sbb'])

    # (j) Retornar as colunas desejadas:
    df_meta = df_meta[['filial_nome', 'nome_vendedor', 'meta_vendedor', 
                       'meta_vend_geral', 'meta_vend_indicacao', 'meta_vend_sbb', 'meta_vend_vitamina',
                       'total_geral', 'total_indicacao', 'total_sbb', 'total_vitamina',
                       'degrau_geral', 'degrau_indicacao', 'degrau_sbb', 'degrau_vitamina',
                       'degrau_total',
                       'perf_indicacao', 'comm_indicacao', 
                       'perf_vitamina', 'comm_vitamina', 
                       'perf_sbb', 'comm_sbb', 'comissao_indicacao',
                          'comissao_vitamina', 'comissao_sbb', 'comissao_total'
                       ]]
    return df_meta