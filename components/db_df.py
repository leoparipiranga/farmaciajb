import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta

# DATA_ATUAL_SIMULADA = date.today() # Ex: Se seus dados são de 2023, use datetime(2023, 5, 12)
DATA_ATUAL_SIMULADA = datetime(2025, 6, 4).date()

metas = pd.read_csv('base/metas.csv', sep=';')
df = pd.read_csv('base/vendas.csv')
df['orcamento_datahora'] = pd.to_datetime(df['orcamento_datahora'], format='%Y-%m-%d %H:%M:%S')
df['orcamento_data'] = pd.to_datetime(df['orcamento_datahora']).dt.date
df['mês/ano'] = df['orcamento_datahora'].dt.to_period('M')
df['hora'] = df['orcamento_datahora'].dt.hour
df['venda_datahoraabertura'] = pd.to_datetime(df['venda_datahoraabertura'], format='%Y-%m-%d %H:%M:%S')
df['venda_datahorafechamento'] = pd.to_datetime(df['venda_datahorafechamento'], format='%Y-%m-%d %H:%M:%S')
df['mes'] = df['venda_datahorafechamento'].dt.strftime("%m-%Y")

classifica = pd.read_csv('base/classificacao.csv')
def extrair_class_painome(caminho):
    if 'QUERODELIVERY' in caminho:
        return 'QUERODELIVERY'
    partes = caminho.split(' > ')
    return partes[1] if len(partes) > 1 else None

df['class_painome'] = df['classificacao_caminho'].apply(extrair_class_painome)
df['data_venda_apenas'] = df['venda_datahorafechamento'].dt.date

embalagem = pd.read_csv('base/embalagem.csv')
mov = pd.read_csv('base/movestoque.csv')

mov_filtrado = mov.loc[mov.groupby(['embalagemid', 'unidadenegocioid'])['datahora'].idxmax()]
mov_filtrado.reset_index(drop=True, inplace=True)
mov_filtrado = mov_filtrado[['embalagemid', 'unidadenegocioid','customedio']]

df = df.merge(mov_filtrado, 
              how='left', 
              left_on=['embalagem_id', 'caixa_unidnegocioid'], 
              right_on=['embalagemid', 'unidadenegocioid'])

formapgto = pd.read_csv('base/formapgto.csv')
df = df.merge(formapgto[['id','nome']], left_on='orcamento_formapagamentoid', right_on='id', how='left')