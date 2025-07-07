import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
from datetime import timedelta
from components.db_estoque import estoque, DATA_ATUAL_SIMULADA_ESTOQUE

def main():

    # Definir o dia anterior
    # data_ontem = DATA_ATUAL_SIMULADA_ESTOQUE  # se necessário, mantenha DATA_ATUAL_SIMULADA_ESTOQUE
    data_ontem = DATA_ATUAL_SIMULADA_ESTOQUE - timedelta(days=1)



    # Criar os filtros
    filial_options = sorted(estoque["filial_nome"].dropna().unique().tolist())
    selected_filial = st.selectbox("Filial", ["Todas"] + filial_options)

    curva_options = sorted(estoque["curvaabc"].dropna().unique().tolist())
    selected_curva = st.selectbox("Curva ABC", ["Todas"] + curva_options)

    class_options = sorted(estoque["class_painome"].dropna().unique().tolist())
    selected_class = st.selectbox("Classificação", ["Todas"] + class_options)

    mov_options = sorted(estoque["descricao_movimentacao"].dropna().unique().tolist())
    selected_mov = st.selectbox("Tipo de Movimentação", ["Todas"] + mov_options)

    # Crie um sub menu para alternar entre tabelas
    selected_table = option_menu(
        menu_title="",
        options=["Produtos Zerados", "Produtos com 1 Unidade"],
        icons=["x-circle", "1-circle"],
        menu_icon="",
        default_index=0,
        orientation="horizontal",
        styles={
            "container": {
                "display": "flex",
                "justify-content": "flex-start",
                "padding": "0!important",
                "background-color": "transparent",
                "width": "fit-content"
            },
            "icon": {
                "font-size": "14px",
                "margin-bottom": "0",
            },
            "nav-link": {
                "font-size": "14px",
                "color": "white",
                "padding": "4px",
                "margin": "2px 6px 2px 0",
                "width": "180px",
                "height": "80px",
                "text-align": "center",
                "display": "flex",
                "flex-direction": "column",
                "align-items": "center",
                "justify-content": "center",
                "border": "2px solid #7FDBFF",
                "border-radius": "5px",
                "background-color": "lightgray"
            },
            "nav-link:hover": {
                "background-color": "gray",
                "border-color": "#7FDBFF"
            },
            "nav-link-selected": {
                "background-color": "gray",
            },
        }
    )

    # Filtrar a base de estoque conforme a condição selecionada:
    if selected_table == "Produtos Zerados":
        df_temp = estoque[(estoque['estoque'] == 0) &
                        (estoque['datahora'].dt.date == data_ontem)
                        ].copy()
    else:  # Produtos com 1 unidade
        df_temp = estoque[(estoque['estoque'] == 1) &
                        (estoque['datahora'].dt.date == data_ontem)
                        ].copy()

    # Mantenha os filtros já aplicados anteriormente (ex: filial, curva, classificação, movimentação)
    if selected_filial != "Todas":
        df_temp = df_temp[df_temp["filial_nome"] == selected_filial]
    if selected_curva != "Todas":
        df_temp = df_temp[df_temp["curvaabc"] == selected_curva]
    if selected_class != "Todas":
        df_temp = df_temp[df_temp["class_painome"] == selected_class]
    if selected_mov != "Todas":
        df_temp = df_temp[df_temp["descricao_movimentacao"] == selected_mov]

    # Adicione 'produtoid' às colunas de visualização
    colunas_viz = ["produtoid", "quantidade", "codigobarras", "descricao", "curvaabc", "classificacao_nome"]
    df_estoque_viz = df_temp.loc[:, colunas_viz]

    # Cria um pivot para obter o estoque atual por produto e filial
    pivo_estoque = estoque.groupby(['produtoid', 'filial_codigo'])['estoque'] \
                        .last().unstack(fill_value=0)
    pivo_estoque.rename(columns={
        1: "Filial 1",
        2: "Filial 2",
        3: "Filial 3"
    }, inplace=True)

    # Merge do DataFrame visual com o pivot (com base em produtoid)
    df_final = pd.merge(df_estoque_viz, pivo_estoque, on="produtoid", how="left")
    df_final.drop(columns="produtoid", inplace=True)
    df_final = df_final[['codigobarras', 'descricao', 'curvaabc', 'classificacao_nome',
                        'quantidade', 'Filial 1', 'Filial 2', 'Filial 3']]
    df_final.rename(columns={
        'codigobarras': 'Código de Barras',
        'descricao': 'Descrição',
        'curvaabc': 'Curva ABC',
        'classificacao_nome': 'Classificação',
        'quantidade': 'Quantidade',
        
    }, inplace=True)

    # Exibe uma mensagem com o número de produtos encontrados

    st.write(f"{df_final.shape[0]} produtos encontrados para {selected_table.lower()} em {data_ontem}.")
    st.dataframe(df_final, hide_index=True, use_container_width=True)