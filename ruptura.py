import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import timedelta
import streamlit as st

DATA_ATUAL_SIMULADA_ESTOQUE = pd.to_datetime("2025-06-16").date()  # Data simulada para o estoque

df = pd.read_csv('base/vendas.csv')
mov = pd.read_csv('base/movestoque.csv')
embalagem = pd.read_csv('base/embalagem.csv')
formapgto = pd.read_csv('base/formapgto.csv')
produto = pd.read_csv('base/produto.csv')
classificacao = pd.read_csv('base/classificacao2.csv')

estoque = mov[['descricao_movimentacao', 'embalagemid',
       'unidadenegocioid', 'datahora','quantidade',
       'estoqueanterior', 'estoque', 'precoreferencial', 'precovenda',
       'customedio']].copy()
estoque = estoque.merge(embalagem[['id', 'produtoid', 'apresentacao', 'codigobarras', 
                         'markup', 'descricao']],
                         left_on='embalagemid', right_on='id', how='left')
estoque = estoque.merge(classificacao,
                        on='produtoid',
                        how='left'
                        )
estoque.rename(columns={'nome': 'classificacao_nome'}, inplace=True)

mapping = {
    93733: "DROGARIA JB - F01 - MATRIZ",
    93729: "DROGARIA JB - F02 - CAMERINO",
    93730: "DROGARIA JB - F03 - AILKA"
}

estoque["filial_nome"] = estoque["unidadenegocioid"].map(mapping)

mapping2 = {
    93733: 1,
    93729: 2,
    93730: 3
} 
estoque["filial_codigo"] = estoque["unidadenegocioid"].map(mapping2)
estoque = estoque[estoque['unidadenegocioid'].isin(mapping.keys())]

def extrair_class_painome(caminho):
    if caminho is None or pd.isna(caminho):
        return "Sem classificação"
    if 'QUERODELIVERY' in caminho:
        return 'QUERODELIVERY'
    partes = caminho.split(' > ')
    return partes[1] if len(partes) > 1 else None

estoque['class_painome'] = estoque['caminho'].apply(extrair_class_painome)

class_estoque = ['VAREJO', 'PRESCRIÇÃO', 'INDICAÇÃO', 'SBB']
estoque = estoque[estoque['class_painome'].isin(class_estoque)]

def calcular_curva_abc(estoque, data_atual):
    """
    Calcula a curva ABC baseada nas vendas dos últimos 90 dias
    
    Parâmetros:
    - estoque: DataFrame com movimentações de estoque
    - data_atual: data de referência
    
    Retorna:
    - DataFrame com embalagemid e curvaABC
    """
    
    # Converter datahora para datetime se necessário
    estoque['datahora'] = pd.to_datetime(estoque['datahora'])
    
    # Filtrar vendas dos últimos 90 dias
    data_limite_90 = pd.Timestamp(data_atual) - pd.Timedelta(days=90)
    vendas_90d = estoque[
        (estoque['descricao_movimentacao'] == 'Venda') &
        (estoque['datahora'] >= data_limite_90)
    ].copy()
    
    # Converter quantidade para positiva (vendas são negativas)
    vendas_90d['quantidade'] = vendas_90d['quantidade'].abs()
    
    # Agrupar por embalagemid e somar quantidades
    vendas_produto = (vendas_90d.groupby('embalagemid')['quantidade']
                      .sum()
                      .reset_index()
                      .sort_values('quantidade', ascending=False))
    
    # Calcular percentual acumulado
    vendas_produto['quantidade_acum'] = vendas_produto['quantidade'].cumsum()
    total_vendas = vendas_produto['quantidade'].sum()
    vendas_produto['perc_acum'] = (vendas_produto['quantidade_acum'] / total_vendas) * 100
    
    # Classificar em curvas ABC
    def classificar_curva(perc):
        if perc <= 50:
            return 'A'
        elif perc <= 80:
            return 'B'
        else:
            return 'C'
    
    vendas_produto['curvaABC'] = vendas_produto['perc_acum'].apply(classificar_curva)
    
    # Produtos que tiveram vendas nos últimos 90 dias
    produtos_com_vendas = vendas_produto[['embalagemid', 'curvaABC']]
    
    # Todos os produtos únicos no estoque
    todos_produtos = estoque['embalagemid'].unique()
    
    # Produtos sem vendas nos últimos 90 dias = Curva D
    produtos_sem_vendas = set(todos_produtos) - set(produtos_com_vendas['embalagemid'])
    
    # DataFrame com produtos curva D
    curva_d = pd.DataFrame({
        'embalagemid': list(produtos_sem_vendas),
        'curvaABC': 'D'
    })
    
    # Combinar todos os produtos
    curva_abc_final = pd.concat([produtos_com_vendas, curva_d], ignore_index=True)
    
    return curva_abc_final

def aplicar_curva_abc_ao_estoque(estoque, data_atual):
    """
    Aplica a curva ABC ao DataFrame de estoque
    """
    # Calcular curva ABC
    curva_abc = calcular_curva_abc(estoque, data_atual)
    
    # Fazer merge com o estoque
    estoque_com_curva = estoque.merge(curva_abc, on='embalagemid', how='left')
    
    # Produtos não encontrados ficam como 'D'
    estoque_com_curva['curvaABC'] = estoque_com_curva['curvaABC'].fillna('D')
    
    return estoque_com_curva

def calcular_indice_ruptura_por_curva(estoque, data_atual):
    """
    Calcula índice de ruptura por filial e curva ABC
    """
    # Aplicar curva ABC ao estoque
    estoque_com_curva = aplicar_curva_abc_ao_estoque(estoque, data_atual)
    
    # Filtrar movimentações dos últimos 90 dias
    data_limite_90 = pd.Timestamp(data_atual) - pd.Timedelta(days=90)
    estoque_90d = estoque_com_curva[estoque_com_curva['datahora'] >= data_limite_90].copy()
    
    # Obter estoque atual
    estoque_atual = (estoque_90d.sort_values('datahora')
                     .groupby(['filial_nome', 'embalagemid'])
                     .tail(1)[['filial_nome', 'embalagemid', 'curvaABC', 'estoque']])
    
    # Calcular índice de ruptura por filial e curva
    resultado = []
    
    for filial in estoque_atual['filial_nome'].unique():
        for curva in ['A', 'B', 'C', 'D']:
            
            produtos_curva = estoque_atual[
                (estoque_atual['filial_nome'] == filial) & 
                (estoque_atual['curvaABC'] == curva)
            ]
            
            if len(produtos_curva) > 0:
                total_produtos = len(produtos_curva)
                produtos_zerados = len(produtos_curva[produtos_curva['estoque'] == 0])
                indice_ruptura = (produtos_zerados / total_produtos) * 100
                
                resultado.append({
                    'filial_nome': filial,
                    'curvaABC': curva,
                    'total_produtos': total_produtos,
                    'produtos_zerados': produtos_zerados,
                    'indice_ruptura': indice_ruptura
                })
    
    return pd.DataFrame(resultado)

def criar_grafico_ruptura_curva_abc(df_ruptura_curva, filial):
    """
    Cria gráfico de gauge para ruptura por curva ABC de uma filial
    """
    dados_filial = df_ruptura_curva[df_ruptura_curva['filial_nome'] == filial]
    
    if dados_filial.empty:
        return None
    
    from plotly.subplots import make_subplots
    
    # Garantir que todas as curvas A, B, C, D estejam presentes
    curvas_completas = []
    for curva in ['A', 'B', 'C', 'D']:
        linha_curva = dados_filial[dados_filial['curvaABC'] == curva]
        if not linha_curva.empty:
            curvas_completas.append({
                'curva': curva,
                'valor': linha_curva['indice_ruptura'].iloc[0]
            })
        else:
            curvas_completas.append({
                'curva': curva,
                'valor': 0
            })
    
    fig = make_subplots(
        rows=1, 
        cols=4,
        specs=[[{"type": "indicator"}] * 4],
        subplot_titles=[f"Curva {item['curva']}" for item in curvas_completas]
    )
    
    cores = {'A': 'green', 'B': 'blue', 'C': 'orange', 'D': 'red'}
    
    for i, item in enumerate(curvas_completas):
        curva = item['curva']
        valor = item['valor']
        
        fig.add_trace(
            go.Indicator(
                mode="gauge+number",
                value=valor,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': f"Curva {curva}<br>Ruptura (%)"},
                gauge={
                    'axis': {'range': [None, 100]},
                    'bar': {'color': cores[curva]},
                    'steps': [
                        {'range': [0, 10], 'color': "lightgreen"},
                        {'range': [10, 25], 'color': "yellow"},
                        {'range': [25, 50], 'color': "orange"},
                        {'range': [50, 100], 'color': "lightcoral"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 30
                    }
                }
            ),
            row=1, col=i+1
        )
    
    fig.update_layout(
        title=f"Índice de Ruptura por Curva ABC - {filial}",
        height=400,
        showlegend=False
    )
    
    return fig

def main_ruptura_curva_abc():
    """Função principal para análise de ruptura por curva ABC"""
    
    # Calcular índices de ruptura por curva ABC
    df_ruptura_curva = calcular_indice_ruptura_por_curva(estoque, DATA_ATUAL_SIMULADA_ESTOQUE)
    
    # Mostrar tabela
    st.subheader("Índice de Ruptura por Curva ABC")
    
    df_display = df_ruptura_curva.copy()
    df_display['indice_ruptura'] = df_display['indice_ruptura'].round(1)
    df_display = df_display.rename(columns={
        'filial_nome': 'Filial',
        'curvaABC': 'Curva ABC',
        'total_produtos': 'Total Produtos',
        'produtos_zerados': 'Produtos Zerados',
        'indice_ruptura': 'Índice Ruptura (%)'
    })
    
    st.dataframe(df_display, use_container_width=True)
    
    # Gráficos por filial
    st.subheader("Gráficos de Ruptura por Curva ABC - Por Filial")
    
    filiais = df_ruptura_curva['filial_nome'].unique()
    
    for filial in filiais:
        fig = criar_grafico_ruptura_curva_abc(df_ruptura_curva, filial)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
    
    # Resumo por curva
    st.subheader("Resumo Geral por Curva ABC")
    
    resumo_curva = df_ruptura_curva.groupby('curvaABC')['indice_ruptura'].mean().reset_index()
    resumo_curva['indice_ruptura'] = resumo_curva['indice_ruptura'].round(1)
    
    col1, col2, col3, col4 = st.columns(4)
    
    for i, (col, curva) in enumerate(zip([col1, col2, col3, col4], ['A', 'B', 'C', 'D'])):
        with col:
            valor_curva = resumo_curva[resumo_curva['curvaABC'] == curva]['indice_ruptura']
            if not valor_curva.empty:
                st.metric(f"Curva {curva}", f"{valor_curva.iloc[0]:.1f}%")
            else:
                st.metric(f"Curva {curva}", "0.0%")

# Para usar:
if __name__ == "__main__":
    main_ruptura_curva_abc()