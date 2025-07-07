import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from components.db_estoque import estoque
from components.db_df import df

def main():

    st.title("Análise de Impacto de Promoção")

    # Upload do DataFrame de produtos em promoção
    col1, col2, col3 = st.columns(3)

    with col1: 
        st.markdown("##### 1. Carregue a lista de produtos em promoção")
        st.write('(CSV com colunas: produtoid ou codigobarras, filial_codigo)')

        uploaded_file = st.file_uploader("Escolha o arquivo CSV", type="csv")
        if uploaded_file is not None:
            promo_df = pd.read_csv(uploaded_file)
            # Verificar se as colunas existem
            if not {'filial_codigo', 'produtoid'}.issubset(promo_df.columns):
                st.error("O arquivo deve conter as colunas 'filial_codigo' e 'produtoid'.")
                st.stop()
            # Verificar se são inteiras
            if not (pd.api.types.is_integer_dtype(promo_df['filial_codigo']) and pd.api.types.is_integer_dtype(promo_df['produtoid'])):
                st.error("As colunas 'filial_codigo' e 'produtoid' devem ser do tipo inteiro.")
                st.stop()
            # Criar coluna 'chave'
            promo_df['chave'] = promo_df['filial_codigo'].astype(str) + '_' + promo_df['produtoid'].astype(str)
            st.session_state['promo_df'] = promo_df
            st.session_state['uploaded_file_name'] = uploaded_file.name
        else:
            if 'promo_df' in st.session_state:
                promo_df = st.session_state['promo_df']
            else:
                st.warning("Faça upload de um arquivo CSV para continuar.")
                st.stop()

    estoque['chave'] = estoque['filial_codigo'].astype(str) + '_' + estoque['produtoid'].astype(str)

    # Filtrar estoque
    estoque_filtrado = estoque[estoque['chave'].isin(promo_df['chave'].tolist())]
    filtro_estoque = estoque.merge(
        promo_df,
        left_on=["filial_codigo", "produtoid"],
        right_on=["filial_codigo", "produtoid"],
        how="inner"
    )
    filtro_estoque['data'] = pd.to_datetime(filtro_estoque['datahora']).dt.date

    with col2: 
        st.markdown("#### 2. Selecione o período da promoção")
        col21, col22 = st.columns(2)
        with col21:
            data_inicio_promo = st.date_input("Data inicial da promoção", value=datetime.today() - timedelta(days=10))
        with col22:
            data_fim_promo = st.date_input("Data final da promoção", value=datetime.today() - timedelta(days=5))

        # Filtro por loja
        lojas = sorted(promo_df['filial_codigo'].unique())
        selected_loja = st.selectbox("Filial", ["Todas"] + [str(l) for l in lojas], key="loja_select_promo")
    st.markdown("---")

    graficos, tabela = st.tabs(["Resultado Geral", "Detalhamento"])

    with graficos:

        # Converter datas
        filtro_estoque['data'] = pd.to_datetime(filtro_estoque['data'])
        promo_df['filial_codigo'] = promo_df['filial_codigo'].astype(filtro_estoque['filial_codigo'].dtype)

        # Filtrar estoque para produtos em promoção e loja selecionada
        if 'produtoid' in promo_df.columns:
            produtos_promo = promo_df['produtoid'].unique()
            filtro = filtro_estoque[filtro_estoque['produtoid'].isin(produtos_promo)]
        else:
            produtos_promo = promo_df['codigobarras'].unique()
            filtro = filtro_estoque[filtro_estoque['codigobarras'].isin(produtos_promo)]

        if selected_loja != "Todas":
            filtro = filtro[filtro['filial_codigo'] == int(selected_loja)]

        # Converter quantidade para positiva e filtrar apenas vendas
        filtro['quantidade'] = filtro['quantidade'].abs()
        filtro = filtro[filtro['descricao_movimentacao'] == 'Venda']


        # Definir períodos de 6 dias
        data_inicio_promo = pd.to_datetime(data_inicio_promo)
        data_fim_promo = pd.to_datetime(data_fim_promo)
        periodos = {}

        # Período da promoção
        periodos['Promoção'] = {'inicio': data_inicio_promo, 'fim': data_fim_promo}

        # Período após promoção (6 dias após o fim)
        periodos['Após'] = {'inicio': data_fim_promo + timedelta(days=1), 'fim': data_fim_promo + timedelta(days=6)}

        # Período antes da promoção (6 dias antes do início)
        periodos['Antes'] = {'inicio': data_inicio_promo - timedelta(days=6), 'fim': data_inicio_promo - timedelta(days=1)}

        def classificar_periodo(data):
            for nome, periodo in periodos.items():
                if periodo['inicio'] <= data <= periodo['fim']:
                    return nome
            return 'Fora dos períodos'

        filtro['periodo'] = filtro['data'].apply(classificar_periodo)

        # Agrupar por data
        vendas_diarias = filtro.groupby(['data']).agg({'quantidade':'sum'}).reset_index()
        vendas_diarias['periodo'] = vendas_diarias['data'].apply(classificar_periodo)

        # Agrupar por período
        vendas_por_periodo = vendas_diarias.groupby('periodo')['quantidade'].sum().reindex(['Antes', 'Promoção', 'Após']).fillna(0)
        # Calcule a média dos períodos "Antes" e "Após"
        media_sem_promocao_qtd = (vendas_por_periodo['Antes'] + vendas_por_periodo['Após']) / 2

        # Plotar gráfico único
        fig_quantidade, ax = plt.subplots(figsize=(5, 3))  # Menor

        labels = []
        valores = []
        cores = []
        for nome in ['Antes', 'Promoção', 'Após']:
            inicio = periodos[nome]['inicio'].strftime('%d/%m')
            fim = periodos[nome]['fim'].strftime('%d/%m')
            labels.append(f"{inicio} a {fim}")  # <-- só as datas
            valores.append(vendas_por_periodo[nome])
            if nome == 'Promoção':
                cores.append('#ff7f0e')  # alaranjado
            else:
                cores.append('steelblue')

        bars = ax.bar(labels, valores, color=cores)

        # Linha de referência na barra da promoção (posição 1)
        ax.hlines(media_sem_promocao_qtd, xmin=0.5, xmax=1.5, colors='red', linestyles='dashed', label='Média sem promoção')
        ax.text(1, media_sem_promocao_qtd, f'{int(media_sem_promocao_qtd)}', color='red', ha='center', va='bottom', fontsize=10)

        # Remover todas as bordas, exceto a inferior
        for spine in ['top', 'right', 'left']:
            ax.spines[spine].set_visible(False)

        # Esconder y-axis (ticks, label, title)
        ax.yaxis.set_visible(False)
        ax.set_ylabel('')
        ax.set_yticks([])
        ax.set_title('')

        # Adicionar valores nas barras
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                    f'{int(height)}', ha='center', va='bottom', fontsize=11)
        plt.tight_layout()

        # Crie o filtro de combinações válidas
        filtro_embalagem = filtro_estoque[['filial_codigo', 'embalagemid']].drop_duplicates()

        # Faça o merge para filtrar df apenas para essas combinações
        filtro_valor = df.merge(
            filtro_embalagem,
            left_on=['filial_codigo', 'embalagemid'],
            right_on=['filial_codigo', 'embalagemid'],
            how='inner'
        )

        # Converter data para datetime se necessário
        filtro_valor['data_venda_apenas'] = pd.to_datetime(filtro_valor['data_venda_apenas'])

        # Supondo que selected_loja é o filtro de filial (string ou int)
        if selected_loja != "Todas":
            filtro_valor = filtro_valor[filtro_valor['filial_codigo'] == int(selected_loja)]

        # Classificar período
        def classificar_periodo_valor(data):
            for nome, periodo in periodos.items():
                if periodo['inicio'] <= data <= periodo['fim']:
                    return nome
            return 'Fora dos períodos'

        filtro_valor['periodo'] = filtro_valor['data_venda_apenas'].apply(classificar_periodo_valor)

        # Agrupar por período e somar item_valortotal
        valor_por_periodo = filtro_valor.groupby('periodo')['item_valortotal'].sum().reindex(['Antes', 'Promoção', 'Após']).fillna(0)
        media_sem_promocao_valor = (valor_por_periodo['Antes'] + valor_por_periodo['Após']) / 2

        # Plotar gráfico de barras para valor total
        fig_valor, ax2 = plt.subplots(figsize=(5, 3))
        labels_valor = []
        valores_valor = []
        cores_valor = []
        for nome in ['Antes', 'Promoção', 'Após']:
            inicio = periodos[nome]['inicio'].strftime('%d/%m')
            fim = periodos[nome]['fim'].strftime('%d/%m')
            labels_valor.append(f"{inicio} a {fim}")
            valores_valor.append(valor_por_periodo[nome])
            if nome == 'Promoção':
                cores_valor.append('#FFD700')
            else:
                cores_valor.append('steelblue')

        bars2 = ax2.bar(labels_valor, valores_valor, color=cores_valor)

        ax2.hlines(media_sem_promocao_valor, xmin=0.5, xmax=1.5, colors='red', linestyles='dashed', label='Média sem promoção')
        ax2.text(1, media_sem_promocao_valor, f'R$ {media_sem_promocao_valor:,.2f}', color='red', ha='center', va='bottom', fontsize=10)

        # Remover todas as bordas, exceto a inferior
        for spine in ['top', 'right', 'left']:
            ax2.spines[spine].set_visible(False)

        # Esconder y-axis (ticks, label, title)
        ax2.yaxis.set_visible(False)
        ax2.set_ylabel('')
        ax2.set_yticks([])
        ax2.set_title('')

        # Adicionar valores nas barras
        for bar in bars2:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                    f'R$ {height:,.2f}', ha='center', va='bottom', fontsize=11)

        plt.tight_layout()

        # Crie o filtro de combinações válidas
        filtro_embalagem = filtro_estoque[['filial_codigo', 'embalagemid']].drop_duplicates()

        # Faça o merge para filtrar df apenas para essas combinações
        df_merged = df.merge(
            filtro_embalagem,
            left_on=['filial_codigo', 'embalagemid'],
            right_on=['filial_codigo', 'embalagemid'],
            how='inner'
        )

        # Converter data para datetime se necessário
        df_merged['data_venda_apenas'] = pd.to_datetime(df_merged['data_venda_apenas'])

        # 4. Calcule o resultado bruto (item_valortotal - customedio)
        df_merged['resultado'] = df_merged['item_valortotal'] - df_merged['customedio']

        # 5. Classifique o período (antes, durante, depois) usando a mesma lógica dos outros gráficos
        def classificar_periodo_resultado(data):
            for nome, periodo in periodos.items():
                if periodo['inicio'] <= data <= periodo['fim']:
                    return nome
            return 'Fora dos períodos'

        df_merged['data_venda_apenas'] = pd.to_datetime(df_merged['data_venda_apenas'])
        df_merged['periodo'] = df_merged['data_venda_apenas'].apply(classificar_periodo_resultado)

        # 6. Agrupe por período e some o resultado
        resultado_por_periodo = df_merged.groupby('periodo')['resultado'].sum().reindex(['Antes', 'Promoção', 'Após']).fillna(0)

        # 7. Plotar o gráfico

        labels = []
        valores = []
        cores = []
        for nome in ['Antes', 'Promoção', 'Após']:
            inicio = periodos[nome]['inicio'].strftime('%d/%m')
            fim = periodos[nome]['fim'].strftime('%d/%m')
            labels.append(f"{inicio} a {fim}")
            valores.append(resultado_por_periodo[nome])
            if nome == 'Promoção':
                cores.append('#ff7f0e')
            else:
                cores.append('steelblue')

        fig_resultado, ax = plt.subplots(figsize=(5, 3))
        bars = ax.bar(labels, valores, color=cores)

        # Remover todas as bordas, exceto a inferior
        for spine in ['top', 'right', 'left']:
            ax.spines[spine].set_visible(False)
        ax.yaxis.set_visible(False)
        ax.set_ylabel('')
        ax.set_yticks([])
        ax.set_title('')

        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                    f'R$ {height:,.2f}', ha='center', va='bottom', fontsize=11)

        plt.tight_layout()

        # Calcular datas dos 30 dias antes da promoção
        data_inicio_antes = data_inicio_promo - pd.Timedelta(days=30)
        data_fim_antes = data_inicio_promo - pd.Timedelta(days=1)


        col10, col20 = st.columns(2)

        with col10:

            opcao_grafico = st.radio(
                "Escolha o gráfico:",
                ["Quantidade vendida", "Valor total vendido", "Resultado"],
                horizontal=True
            )

            if opcao_grafico == "Quantidade vendida":
                st.markdown("#### Quantidade total vendida dos produtos em promoção")
                st.pyplot(fig_quantidade)
            elif opcao_grafico == "Valor total vendido":
                st.markdown("#### Valor total vendido dos produtos em promoção")
                st.pyplot(fig_valor)
            elif opcao_grafico == "Resultado":
                st.markdown("#### Resultado dos produtos em promoção")
                st.pyplot(fig_resultado)

        with col20:

            # Calcule as médias diárias
            dias_antes = (periodos['Antes']['fim'] - periodos['Antes']['inicio']).days + 1
            dias_apos = (periodos['Após']['fim'] - periodos['Após']['inicio']).days + 1
            dias_promo = (periodos['Promoção']['fim'] - periodos['Promoção']['inicio']).days + 1

            media_antes = vendas_por_periodo['Antes'] / dias_antes if dias_antes > 0 else 0
            media_apos = vendas_por_periodo['Após'] / dias_apos if dias_apos > 0 else 0
            media_promo = vendas_por_periodo['Promoção'] / dias_promo if dias_promo > 0 else 0

            media_fora = (media_antes + media_apos) / 2

            # Para valor
            media_antes_valor = valor_por_periodo['Antes'] / dias_antes if dias_antes > 0 else 0
            media_apos_valor = valor_por_periodo['Após'] / dias_apos if dias_apos > 0 else 0
            media_promo_valor = valor_por_periodo['Promoção'] / dias_promo if dias_promo > 0 else 0
            media_fora_valor = (media_antes_valor + media_apos_valor) / 2

            # Resultado total dos 30 dias antes da promoção
            resultado_antes = df_merged[
                (df_merged['data_venda_apenas'] >= data_inicio_antes) &
                (df_merged['data_venda_apenas'] <= data_fim_antes)
            ]['resultado'].sum()

            # Resultado total durante a promoção
            resultado_promo = df_merged[
                (df_merged['data_venda_apenas'] >= data_inicio_promo) &
                (df_merged['data_venda_apenas'] <= data_fim_promo)
            ]['resultado'].sum()

            st.markdown(
                """
                <style>
                .kpi-label {font-size:20px; color:gray; margin-bottom:8px;}
                .kpi-value {font-size:32px; font-weight:bold; margin-bottom:12px;}
                </style>
                """,
                unsafe_allow_html=True
            )

            # Quantidade média diária
            cor_fora = "red" if media_fora < 0 else "steelblue"
            cor_promo = "red" if media_promo < 0 else "#ff7f0e"

            st.markdown("**Quantidade média diária**")
            st.markdown("<br>", unsafe_allow_html=True)

            kpi_col1, kpi_col2 = st.columns(2)
            with kpi_col1:
                st.markdown('<div class="kpi-label">Fora da Promoção</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="kpi-value" style="color:{cor_fora};">{media_fora:.1f}</div>', unsafe_allow_html=True)
            with kpi_col2:
                st.markdown('<div class="kpi-label">Durante a Promoção</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="kpi-value" style="color:{cor_promo};">{media_promo:.1f}</div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            # Valor médio diário
            cor_fora_valor = "red" if media_fora_valor < 0 else "steelblue"
            cor_promo_valor = "red" if media_promo_valor < 0 else "#ff7f0e"

            st.markdown("**Valor médio diário (R$)**")
            kpi_col3, kpi_col4 = st.columns(2)
            with kpi_col3:
                st.markdown('<div class="kpi-label">Fora da Promoção</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="kpi-value" style="color:{cor_fora_valor};">R$ {media_fora_valor:,.2f}</div>', unsafe_allow_html=True)
            with kpi_col4:
                st.markdown('<div class="kpi-label">Durante a Promoção</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="kpi-value" style="color:{cor_promo_valor};">R$ {media_promo_valor:,.2f}</div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            
            # Resultado Bruto Total
            cor_antes = "red" if resultado_antes < 0 else "steelblue"
            cor_promo_res = "red" if resultado_promo < 0 else "#ff7f0e"

            st.markdown("**Resultado Bruto Total (R$)**")
            kpi_col5, kpi_col6 = st.columns(2)
            with kpi_col5:
                st.markdown('<div class="kpi-label">30 dias antes</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="kpi-value" style="color:{cor_antes};">R$ {resultado_antes:,.2f}</div>', unsafe_allow_html=True)
            with kpi_col6:
                st.markdown('<div class="kpi-label">Durante a Promoção</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="kpi-value" style="color:{cor_promo_res};">R$ {resultado_promo:,.2f}</div>', unsafe_allow_html=True)

    with tabela:
        # Filtros de filial e class_painome
        filiais = sorted(df['filial_codigo'].dropna().unique())
        classes = sorted(df['class_painome'].dropna().unique())
        selected_filial = st.selectbox("Filial", ["Todas"] + [str(f) for f in filiais], key="filial_select_tabela")
        selected_class = st.selectbox("Classificação", ["Todas"] + classes, key="class_select_tabela")

        # Filtrar df conforme seleção
        df_filtro = filtro_estoque.copy()
        if selected_filial != "Todas":
            df_filtro = df_filtro[df_filtro['filial_codigo'] == int(selected_filial)]
        if selected_class != "Todas":
            df_filtro = df_filtro[df_filtro['class_painome'] == selected_class]

        # Garantir que datas estejam em datetime
        df_filtro['data'] = pd.to_datetime(df_filtro['data'])

        # Produtos em promoção
        if 'produtoid' in promo_df.columns:
            produtos_promo = promo_df['produtoid'].unique()
            df_filtro = df_filtro[df_filtro['produtoid'].isin(produtos_promo)]
        elif 'codigobarras' in promo_df.columns:
            produtos_promo = promo_df['codigobarras'].unique()
            df_filtro = df_filtro[df_filtro['codigobarras'].isin(produtos_promo)]

        df_filtro['quantidade'] = df_filtro['quantidade'].abs()
        df_filtro = df_filtro[df_filtro['descricao_movimentacao'] == 'Venda']

        # Quantidade vendida nos 30 dias antes
        df_antes = df_filtro[(df_filtro['data'] >= data_inicio_antes) & (df_filtro['data'] <= data_fim_antes)]
        qtd_antes = df_antes.groupby(['codigobarras', 'descricao'])['quantidade'].sum().reset_index()
        qtd_antes.rename(columns={'quantidade': 'Qtd 30 dias antes'}, inplace=True)

        # Quantidade vendida durante a promoção
        df_durante = df_filtro[(df_filtro['data'] >= data_inicio_promo) & (df_filtro['data'] <= data_fim_promo)]
        qtd_durante = df_durante.groupby(['codigobarras', 'descricao'])['quantidade'].sum().reset_index()
        qtd_durante.rename(columns={'quantidade': 'Qtd Promoção'}, inplace=True)

        # Unir as duas tabelas
        tabela = pd.merge(qtd_antes, qtd_durante, on=['codigobarras', 'descricao'], how='outer').fillna(0)
        tabela = tabela.sort_values(by='Qtd Promoção', ascending=False)
        tabela_sem_venda = tabela[tabela['Qtd Promoção'] == 0]

        st.markdown("#### Vendas dos produtos em promoção (30 dias antes x durante a promoção)")
        mostrar_somente_sem_venda = st.checkbox("Mostrar apenas produtos sem venda durante a promoção")
        if mostrar_somente_sem_venda:
            st.dataframe(tabela_sem_venda, hide_index=True, use_container_width=False)
        else:
            st.dataframe(tabela, hide_index=True, use_container_width=False)


