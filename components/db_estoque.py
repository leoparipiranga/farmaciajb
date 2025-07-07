import pandas as pd
import numpy as np
from datetime import timedelta

mov = pd.read_csv('base/movestoque.csv')
curvaabc = pd.read_csv('base/curvaabc.csv')
produto = pd.read_csv('base/produto.csv')
embalagem = pd.read_csv('base/embalagem.csv')
classificacao = pd.read_csv('base/classificacao2.csv')

estoque = mov[['descricao_movimentacao', 'embalagemid',
       'unidadenegocioid', 'datahora','quantidade',
       'estoqueanterior', 'estoque', 'precoreferencial', 'precovenda',
       'customedio']].copy()
estoque = estoque.merge(embalagem[['id', 'produtoid', 'apresentacao', 'codigobarras', 
                         'markup', 'descricao']],
                         left_on='embalagemid', right_on='id', how='left')
estoque = estoque.merge(curvaabc[['produtoid', 'unidadenegocioid','nome']],
                            left_on=['produtoid', 'unidadenegocioid'], 
                            right_on=['produtoid', 'unidadenegocioid'], 
                            how='left')
estoque.rename(columns={'nome': 'curvaabc',
                        }, inplace=True)
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

DATA_ATUAL_SIMULADA_ESTOQUE = pd.to_datetime(estoque['datahora']).max().date() - timedelta(days=1)  # Data máxima 'datahora' do estoque

# Converter a coluna datahora para datetime, se necessário
estoque['datahora'] = pd.to_datetime(estoque['datahora'], format='%Y-%m-%d %H:%M:%S')

# Se não existir a coluna class_painome e você tiver uma coluna 'classificacao_caminho',
# crie-a assim:
def extrair_class_painome(caminho):
    if not isinstance(caminho, str):
        return None
    if 'QUERODELIVERY' in caminho:
        return 'QUERODELIVERY'
    partes = caminho.split(' > ')
    return partes[1] if len(partes) > 1 else None

estoque['class_painome'] = estoque['caminho'].apply(extrair_class_painome)