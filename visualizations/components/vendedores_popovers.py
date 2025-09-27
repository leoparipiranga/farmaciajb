"""
Componentes de popover para análise de vendedores
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import date, timedelta
from core.database import duck_query
from data_processing.vendedores.calculations import _escape, _bounds_mes_atual, _cond_filial

# ========================================
# FUNÇÕES PARA POPOVERS DE VENDEDORES (MIGRADAS DE functions_modals.py)
# ========================================

def criar_conteudo_popover_vendas_vendedores_duck(df_vendas, filial_selecionada, top_n=10):
    """
    Migração de criar_conteudo_popover_vendas_vendedores para DuckDB.
    Cria conteúdo do popover de vendas para vendedores - VERSÃO COMPLETA COM ABAS.
    Mantém exatamente a mesma estrutura e parâmetros da função original, mas usa SQL em vez de Pandas.
    """
    
    # Data de referência
    data_ref = date.today() - timedelta(days=1)
    inicio_mes = data_ref.replace(day=1)
    jan_90 = data_ref - timedelta(days=89)
    
    # Âncora de largura
    st.markdown("""
    <div style="width:650px; min-width:650px; height:1px; background:transparent; margin:0; padding:0; overflow:hidden;"></div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"### 💰 Vendas - Filial {filial_selecionada}")
    
    # Filtrar vendedores válidos via SQL
    cond_filial = _cond_filial(filial_selecionada)
    
    # Total da loja MTD
    sql_total_loja = f"""
        SELECT COALESCE(SUM(item_valortotal), 0) AS total_loja_mtd
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{inicio_mes}' AND DATE '{data_ref}'
        {cond_filial}
    """
    df_total = duck_query(sql_total_loja)
    total_loja_mtd = float(df_total.iloc[0]['total_loja_mtd']) if not df_total.empty else 0.0
    
    # Ranking por valor
    sql_rank_valor = f"""
        SELECT 
            TRIM(vendedor_nome) AS vendedor_nome,
            SUM(item_valortotal) AS item_valortotal
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{inicio_mes}' AND DATE '{data_ref}'
        {cond_filial}
          AND vendedor_nome IS NOT NULL 
          AND TRIM(vendedor_nome) != ''
          AND TRIM(vendedor_nome) != 'Sem Vendedor'
        GROUP BY 1
        ORDER BY 2 DESC
        LIMIT {top_n}
    """
    rank_valor = duck_query(sql_rank_valor)
    if rank_valor.empty:
        st.info("Sem vendedores para exibir")
        return
    
    rank_valor['percentual'] = (rank_valor['item_valortotal'] / total_loja_mtd * 100) if total_loja_mtd > 0 else 0
    top_names = rank_valor['vendedor_nome'].tolist()
    
    # Dados 90 dias
    sql_90 = f"""
        SELECT 
            TRIM(vendedor_nome) AS vendedor_nome,
            SUM(item_valortotal) AS item_valortotal
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{jan_90}' AND DATE '{data_ref}'
        {cond_filial}
          AND vendedor_nome IS NOT NULL 
          AND TRIM(vendedor_nome) != ''
          AND TRIM(vendedor_nome) != 'Sem Vendedor'
        GROUP BY 1
    """
    df_90 = duck_query(sql_90)
    
    # Média por dia
    dias_corridos = (data_ref - inicio_mes).days + 1
    media_dia = rank_valor.copy()
    media_dia['media_dia'] = media_dia['item_valortotal'] / dias_corridos
    
    # Média 90 dias
    if not df_90.empty:
        rank90 = df_90.groupby('vendedor_nome')['item_valortotal'].sum().reset_index()
        rank90['media_90d'] = rank90['item_valortotal'] / 90.0
        media_dia = media_dia.merge(rank90[['vendedor_nome','media_90d']], on='vendedor_nome', how='left')
    else:
        media_dia['media_90d'] = 0
    
    media_dia = media_dia[media_dia['vendedor_nome'].isin(top_names)]
    media_dia = media_dia.sort_values('media_dia', ascending=False)
    
    # Preparar heatmaps (adaptado para SQL)
    def preparar_heatmap_horas():
        # Query para dados horários
        sql_horas = f"""
            SELECT 
                TRIM(vendedor_nome) AS vendedor_nome,
                EXTRACT(hour FROM datahora) AS hora,
                SUM(item_valortotal) AS item_valortotal
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{inicio_mes}' AND DATE '{data_ref}'
            {cond_filial}
              AND vendedor_nome IS NOT NULL 
              AND TRIM(vendedor_nome) != ''
              AND TRIM(vendedor_nome) != 'Sem Vendedor'
              AND EXTRACT(hour FROM datahora) BETWEEN 7 AND 22
            GROUP BY 1, 2
        """
        df_h = duck_query(sql_horas)
        if df_h.empty:
            return None, None, False
        
        # Matriz vendedores
        mat = df_h.pivot_table(index='vendedor_nome', columns='hora', values='item_valortotal', fill_value=0)
        for h in range(7, 23):
            if h not in mat.columns:
                mat[h] = 0
        mat = mat[list(range(7, 23))]
        mat = mat.reindex(index=top_names)
        
        # Total Loja
        sql_total_hora = f"""
            SELECT 
                EXTRACT(hour FROM datahora) AS hora,
                SUM(item_valortotal) AS item_valortotal
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{inicio_mes}' AND DATE '{data_ref}'
            {cond_filial}
              AND EXTRACT(hour FROM datahora) BETWEEN 7 AND 22
            GROUP BY 1
        """
        df_mes_h = duck_query(sql_total_hora)
        total_por_hora = df_mes_h.set_index('hora')['item_valortotal'].reindex(range(7,23), fill_value=0)
        row_total = pd.DataFrame([total_por_hora.values], index=['Total Loja'], columns=range(7,23))
        final_mat = pd.concat([row_total, mat], axis=0)
        
        # Normalização
        mat_norm = final_mat.copy()
        row_min = mat_norm.min(axis=1)
        row_max = mat_norm.max(axis=1)
        denom = (row_max - row_min).replace(0, 1)
        mat_norm = mat_norm.sub(row_min, axis=0).div(denom, axis=0)
        
        return final_mat, mat_norm, True
    
    def preparar_heatmap_dias():
        sql_dias = f"""
            SELECT 
                TRIM(vendedor_nome) AS vendedor_nome,
                EXTRACT(dow FROM data_date) AS weekday,
                SUM(item_valortotal) AS item_valortotal
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{inicio_mes}' AND DATE '{data_ref}'
            {cond_filial}
              AND vendedor_nome IS NOT NULL 
              AND TRIM(vendedor_nome) != ''
              AND TRIM(vendedor_nome) != 'Sem Vendedor'
            GROUP BY 1, 2
        """
        df_dias = duck_query(sql_dias)
        if df_dias.empty:
            return None, None, False
        
        mat = df_dias.pivot_table(index='vendedor_nome', columns='weekday', values='item_valortotal', fill_value=0)
        for w in range(7):
            if w not in mat.columns:
                mat[w] = 0
        mat = mat[list(range(7))]
        mat = mat.reindex(index=top_names)
        
        sql_total_dia = f"""
            SELECT 
                EXTRACT(dow FROM data_date) AS weekday,
                SUM(item_valortotal) AS item_valortotal
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{inicio_mes}' AND DATE '{data_ref}'
            {cond_filial}
            GROUP BY 1
        """
        df_mes_d = duck_query(sql_total_dia)
        total_por_dia = df_mes_d.set_index('weekday')['item_valortotal'].reindex(range(7), fill_value=0)
        row_total = pd.DataFrame([total_por_dia.values], index=['Total Loja'], columns=range(7))
        final_mat = pd.concat([row_total, mat], axis=0)
        
        mat_norm = final_mat.copy()
        row_min = mat_norm.min(axis=1)
        row_max = mat_norm.max(axis=1)
        denom = (row_max - row_min).replace(0, 1)
        mat_norm = mat_norm.sub(row_min, axis=0).div(denom, axis=0)
        
        return final_mat, mat_norm, True
    
    horas_raw, horas_norm, tem_horas = preparar_heatmap_horas()
    dias_raw, dias_norm, tem_dias = preparar_heatmap_dias()
    
    opcoes = ["💵 Valor", "📅 Média/dia", "🕒 Horas", "🗓️ Dias"]
    state_key = f"pills_vendas_vendedores_{filial_selecionada}"
    if state_key not in st.session_state:
        st.session_state[state_key] = opcoes[0]
    escolha = st.pills("Escolha a visualização:", opcoes, key=state_key)
    
    if escolha == "💵 Valor":
        df_plot = rank_valor.sort_values('item_valortotal', ascending=False)
        fig = px.bar(df_plot, x='item_valortotal', y='vendedor_nome', orientation='h', text_auto='.2s')
        fig.update_traces(marker_color='darkslateblue', textangle=0, textposition="inside", textfont=dict(color='white', size=10))
        fig.update_layout(
            height=max(300, min(800, 28 * len(df_plot) + 120)),
            showlegend=False, template="plotly_white",
            margin=dict(t=20, b=20, l=30, r=30),
            xaxis=dict(title="Vendas (R$)", tickfont=dict(size=10)),
            yaxis=dict(title="", tickfont=dict(size=10), autorange='reversed'),
            bargap=0.35
        )
        st.plotly_chart(fig, use_container_width=True)
    
    elif escolha == "📅 Média/dia":
        if media_dia.empty:
            st.info("Sem dados para exibir")
        else:
            fig = px.bar(media_dia, x='media_dia', y='vendedor_nome', orientation='h', text_auto='.2s')
            fig.update_traces(marker_color='indianred', textangle=0, textposition="inside", 
                            textfont=dict(color='white', size=10), name="Média/dia (mês)")
            
            fig.add_trace(go.Scatter(
                x=media_dia['media_90d'], y=media_dia['vendedor_nome'], mode='markers',
                marker=dict(symbol='line-ns', size=14, color='black', line=dict(width=2, color='orange')),
                name='Média 90d', showlegend=True,
                hovertemplate="Vendedor: %{y}<br>Média 90d: R$ %{x:.2f}<extra></extra>"
            ))
            
            fig.update_layout(
                height=max(300, min(800, 28 * len(media_dia) + 120)),
                template="plotly_white", margin=dict(t=20, b=20, l=30, r=30),
                showlegend=True, legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
                xaxis=dict(title="Média por dia (R$)", tickfont=dict(size=10)),
                yaxis=dict(title="", tickfont=dict(size=10), autorange='reversed'),
                bargap=0.35
            )
            st.plotly_chart(fig, use_container_width=True)
    
    elif escolha == "🕒 Horas":
        if not tem_horas:
            st.info("Sem dados horários para exibir")
        else:
            altura = max(300, min(750, 22 * len(horas_norm.index) + 140))

            # preparar matrizes
            z_norm = horas_norm.values.astype(float)                # valores normalizados (0..1)
            raw_vals = np.array(horas_raw.values, dtype=float)     # valores brutos (R$)
            # main heatmap: apenas células > 0 (zeros viram NaN para não serem coloridas pelo gradiente)
            z_main = np.where(raw_vals > 0, z_norm, np.nan)
            # máscara para zeros: 1 onde zero, NaN caso contrário (será desenhada em cinza)
            z_zero = np.where(raw_vals == 0, 1.0, np.nan)

            fig = go.Figure()
            # Heatmap principal (gradiente para valores > 0)
            fig.add_trace(go.Heatmap(
                z=z_main,
                x=list(range(7,23)),
                y=list(horas_norm.index),
                colorscale=[(0.0, "rgb(49,130,189)"), (1.0, "rgb(220,20,60)")],
                zmin=0, zmax=1,
                colorbar=dict(title="Baixo ↔ Alto"),
                hoverongaps=False,
                showscale=True
            ))
            # Overlay para zeros (cor cinza)
            fig.add_trace(go.Heatmap(
                z=z_zero,
                x=list(range(7,23)),
                y=list(horas_norm.index),
                colorscale=[[0, "lightgray"], [1, "gray"]],
                zmin=0, zmax=1,
                showscale=False,
                hoverongaps=False
            ))

            # customdata para hover (usar valores brutos)
            fig.data[0].customdata = raw_vals[..., np.newaxis]
            fig.data[0].hovertemplate = "Linha: %{y}<br>Hora: %{x}h<br>Vendas: R$ %{customdata[0]:.2f}<extra></extra>"
            fig.data[1].customdata = raw_vals[..., np.newaxis]
            fig.data[1].hovertemplate = "Linha: %{y}<br>Hora: %{x}h<br>Vendas: R$ %{customdata[0]:.2f}<extra></extra>"

            fig.update_layout(
                height=altura, template="plotly_white", margin=dict(t=20, b=20, l=30, r=30),
                xaxis_title="Hora do dia", yaxis=dict(
                title="",
                tickfont=dict(size=10),
                autorange='reversed',
                categoryorder='array',
                categoryarray=top_names
            ))
            # manter gaps visuais
            fig.update_traces(xgap=1, ygap=2)
            st.plotly_chart(fig, use_container_width=True)

    elif escolha == "🗓️ Dias":
        if not tem_dias:
            st.info("Sem dados por dia da semana")
        else:
            weekday_labels = ["Seg","Ter","Qua","Qui","Sex","Sáb","Dom"]
            altura = max(300, min(750, 22 * len(dias_norm.index) + 140))

            # preparar matrizes
            z_norm = dias_norm.values.astype(float)
            raw_vals = np.array(dias_raw.values, dtype=float)
            z_main = np.where(raw_vals > 0, z_norm, np.nan)
            z_zero = np.where(raw_vals == 0, 1.0, np.nan)

            fig = go.Figure()
            fig.add_trace(go.Heatmap(
                z=z_main,
                x=weekday_labels,
                y=list(dias_norm.index),
                colorscale=[(0.0, "rgb(49,130,189)"), (1.0, "rgb(220,20,60)")],
                zmin=0, zmax=1,
                colorbar=dict(title="Baixo ↔ Alto"),
                hoverongaps=False,
                showscale=True
            ))
            fig.add_trace(go.Heatmap(
                z=z_zero,
                x=weekday_labels,
                y=list(dias_norm.index),
                colorscale=[[0, "lightgray"], [1, "gray"]],
                zmin=0, zmax=1,
                showscale=False,
                hoverongaps=False
            ))

            fig.data[0].customdata = raw_vals[..., np.newaxis]
            fig.data[0].hovertemplate = "Linha: %{y}<br>Dia: %{x}<br>Vendas: R$ %{customdata[0]:.2f}<extra></extra>"
            fig.data[1].customdata = raw_vals[..., np.newaxis]
            fig.data[1].hovertemplate = "Linha: %{y}<br>Dia: %{x}<br>Vendas: R$ %{customdata[0]:.2f}<extra></extra>"

            fig.update_layout(
                height=altura, template="plotly_white", margin=dict(t=20, b=20, l=30, r=30),
                xaxis_title="Dia da semana", yaxis=dict(
                title="",
                tickfont=dict(size=10),
                autorange='reversed',
                categoryorder='array',
                categoryarray=top_names
            ))
            fig.update_xaxes(side="top")
            fig.update_traces(xgap=1, ygap=2)
            st.plotly_chart(fig, use_container_width=True)

def criar_conteudo_popover_num_vendas_vendedores_duck(df_vendas, filial_selecionada, top_n=10):
    """
    Migração de criar_conteudo_popover_num_vendas_vendedores para DuckDB.
    Mantém a assinatura e comportamento da função original, mas utiliza consultas SQL internamente.
    """
    
    # Datas
    data_ref = date.today() - timedelta(days=1)
    inicio_mes = data_ref.replace(day=1)
    jan_90 = data_ref - timedelta(days=89)

    # Âncora largura e título (mesma UI)
    st.markdown("""
    <div style="width:650px; min-width:650px; height:1px; background:transparent; margin:0; padding:0; overflow:hidden;"></div>
    """, unsafe_allow_html=True)

    st.markdown(f"### 🛒 Nº de Vendas (por Itens) - Filial {filial_selecionada}")
    
    # Condição filial
    cond_filial = _cond_filial(filial_selecionada)

    # Total loja (por quantidade) no mês
    sql_total_loja = f"""
        SELECT COALESCE(SUM(item_quantidade),0) AS total_loja_mtd
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{inicio_mes}' AND DATE '{data_ref}'
        {cond_filial}
    """
    df_total = duck_query(sql_total_loja)
    total_loja_mtd = float(df_total.iloc[0]['total_loja_mtd']) if (df_total is not None and not df_total.empty) else 0.0

    # Ranking por quantidade (top N)
    sql_rank_qtd = f"""
        SELECT
            TRIM(vendedor_nome) AS vendedor_nome,
            SUM(item_quantidade) AS quantidade_total
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{inicio_mes}' AND DATE '{data_ref}'
        {cond_filial}
          AND vendedor_nome IS NOT NULL
          AND TRIM(vendedor_nome) != ''
          AND TRIM(vendedor_nome) != 'Sem Vendedor'
        GROUP BY 1
        ORDER BY 2 DESC
        LIMIT {top_n}
    """
    rank_qtd = duck_query(sql_rank_qtd)
    if rank_qtd is None or rank_qtd.empty:
        st.info("Sem vendedores para exibir")
        return

    rank_qtd['percentual'] = (rank_qtd['quantidade_total'] / total_loja_mtd * 100) if total_loja_mtd > 0 else 0.0
    top_names = rank_qtd['vendedor_nome'].tolist()

    # Dados 90 dias (quantidade)
    sql_90 = f"""
        SELECT
            TRIM(vendedor_nome) AS vendedor_nome,
            SUM(item_quantidade) AS quantidade_total
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{jan_90}' AND DATE '{data_ref}'
        {cond_filial}
          AND vendedor_nome IS NOT NULL
          AND TRIM(vendedor_nome) != ''
          AND TRIM(vendedor_nome) != 'Sem Vendedor'
        GROUP BY 1
    """
    df_90 = duck_query(sql_90)

    # Média por dia (mês atual)
    dias_corridos = (data_ref - inicio_mes).days + 1
    media_dia = rank_qtd.copy()
    media_dia['media_dia'] = media_dia['quantidade_total'] / dias_corridos

    # Média 90 dias
    if df_90 is not None and not df_90.empty:
        rank90 = df_90.groupby('vendedor_nome')['quantidade_total'].sum().reset_index()
        rank90['media_90d'] = rank90['quantidade_total'] / 90.0
        media_dia = media_dia.merge(rank90[['vendedor_nome', 'media_90d']], on='vendedor_nome', how='left')
    else:
        media_dia['media_90d'] = 0.0

    media_dia = media_dia[media_dia['vendedor_nome'].isin(top_names)]
    media_dia = media_dia.sort_values('media_dia', ascending=False)

    # Preparar heatmaps (horas) — agregação por quantidade
    def preparar_heatmap_horas():
        sql_horas = f"""
            SELECT
                TRIM(vendedor_nome) AS vendedor_nome,
                EXTRACT(hour FROM datahora) AS hora,
                SUM(item_quantidade) AS quantidade_total
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{inicio_mes}' AND DATE '{data_ref}'
            {cond_filial}
              AND vendedor_nome IS NOT NULL
              AND TRIM(vendedor_nome) != ''
              AND TRIM(vendedor_nome) != 'Sem Vendedor'
              AND EXTRACT(hour FROM datahora) BETWEEN 7 AND 22
            GROUP BY 1,2
        """
        df_h = duck_query(sql_horas)
        if df_h is None or df_h.empty:
            return None, None, False

        mat = df_h.pivot_table(index='vendedor_nome', columns='hora', values='quantidade_total', fill_value=0)
        for h in range(7, 23):
            if h not in mat.columns:
                mat[h] = 0
        mat = mat[list(range(7, 23))]
        mat = mat.reindex(index=top_names)

        # Total loja por hora
        sql_total_hora = f"""
            SELECT EXTRACT(hour FROM datahora) AS hora, SUM(item_quantidade) AS quantidade_total
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{inicio_mes}' AND DATE '{data_ref}'
            {cond_filial}
              AND EXTRACT(hour FROM datahora) BETWEEN 7 AND 22
            GROUP BY 1
        """
        df_mes_h = duck_query(sql_total_hora)
        total_por_hora = df_mes_h.set_index('hora')['quantidade_total'].reindex(range(7,23), fill_value=0)
        row_total = pd.DataFrame([total_por_hora.values], index=['Total Loja'], columns=range(7,23))
        final_mat = pd.concat([row_total, mat], axis=0)

        mat_norm = final_mat.copy()
        row_min = mat_norm.min(axis=1)
        row_max = mat_norm.max(axis=1)
        denom = (row_max - row_min).replace(0, 1)
        mat_norm = mat_norm.sub(row_min, axis=0).div(denom, axis=0)

        return final_mat, mat_norm, True

    # Preparar heatmaps (dias) — agregação por quantidade
    def preparar_heatmap_dias():
        sql_dias = f"""
            SELECT
                TRIM(vendedor_nome) AS vendedor_nome,
                EXTRACT(dow FROM data_date) AS weekday,
                SUM(item_quantidade) AS quantidade_total
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{inicio_mes}' AND DATE '{data_ref}'
            {cond_filial}
              AND vendedor_nome IS NOT NULL
              AND TRIM(vendedor_nome) != ''
              AND TRIM(vendedor_nome) != 'Sem Vendedor'
            GROUP BY 1,2
        """
        df_dias = duck_query(sql_dias)
        if df_dias is None or df_dias.empty:
            return None, None, False

        mat = df_dias.pivot_table(index='vendedor_nome', columns='weekday', values='quantidade_total', fill_value=0)
        for w in range(7):
            if w not in mat.columns:
                mat[w] = 0
        mat = mat[list(range(7))]
        mat = mat.reindex(index=top_names)

        sql_total_dia = f"""
            SELECT EXTRACT(dow FROM data_date) AS weekday, SUM(item_quantidade) AS quantidade_total
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{inicio_mes}' AND DATE '{data_ref}'
            {cond_filial}
            GROUP BY 1
        """
        df_mes_d = duck_query(sql_total_dia)
        total_por_dia = df_mes_d.set_index('weekday')['quantidade_total'].reindex(range(7), fill_value=0)
        row_total = pd.DataFrame([total_por_dia.values], index=['Total Loja'], columns=range(7))
        final_mat = pd.concat([row_total, mat], axis=0)

        mat_norm = final_mat.copy()
        row_min = mat_norm.min(axis=1)
        row_max = mat_norm.max(axis=1)
        denom = (row_max - row_min).replace(0, 1)
        mat_norm = mat_norm.sub(row_min, axis=0).div(denom, axis=0)

        return final_mat, mat_norm, True

    horas_raw, horas_norm, tem_horas = preparar_heatmap_horas()
    dias_raw, dias_norm, tem_dias = preparar_heatmap_dias()

    opcoes = ["🔢 Quantidade", "📅 Média/dia", "🕒 Horas", "🗓️ Dias"]
    state_key = f"pills_num_vendas_vendedores_{filial_selecionada}"
    if state_key not in st.session_state:
        st.session_state[state_key] = opcoes[0]
    escolha = st.pills("Escolha a visualização:", opcoes, key=state_key)

    if escolha == "🔢 Quantidade":
        df_plot = rank_qtd.head(top_n).sort_values('quantidade_total', ascending=False)
        fig = px.bar(df_plot, x='quantidade_total', y='vendedor_nome', orientation='h')
        fig.update_traces(marker_color='darkslateblue', textangle=0, textposition="inside",
                          textfont=dict(color='white', size=10), texttemplate='%{x:,.0f}')
        fig.update_layout(
            height=max(300, min(800, 28 * len(df_plot) + 120)),
            showlegend=False, template="plotly_white",
            margin=dict(t=20, b=20, l=30, r=30),
            xaxis=dict(title="Quantidade Vendida (Itens)", tickfont=dict(size=10)),
            yaxis=dict(title="", tickfont=dict(size=10), autorange='reversed'),
            bargap=0.35
        )
        st.plotly_chart(fig, use_container_width=True)

    elif escolha == "📅 Média/dia":
        if media_dia.empty:
            st.info("Sem dados para exibir")
        else:
            fig = px.bar(media_dia, x='media_dia', y='vendedor_nome', orientation='h')
            fig.update_traces(marker_color='indianred', textangle=0, textposition="inside",
                              textfont=dict(color='white', size=10), name="Média/dia (mês)",
                              texttemplate='%{x:,.1f}')
            fig.add_trace(go.Scatter(
                x=media_dia['media_90d'], y=media_dia['vendedor_nome'], mode='markers',
                marker=dict(symbol='line-ns', size=14, color='black', line=dict(width=2, color='orange')),
                name='Média 90d', showlegend=True,
                hovertemplate="Vendedor: %{y}<br>Média 90d: %{x:.1f} itens<extra></extra>"
            ))
            fig.update_layout(
                height=max(300, min(800, 28 * len(media_dia) + 120)),
                template="plotly_white", margin=dict(t=20, b=20, l=30, r=30),
                showlegend=True, legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
                xaxis=dict(title="Média por dia (Itens)", tickfont=dict(size=10)),
                yaxis=dict(title="", tickfont=dict(size=10), autorange='reversed'),
                bargap=0.35
            )
            st.plotly_chart(fig, use_container_width=True)

    elif escolha == "🕒 Horas":
        if not tem_horas:
            st.info("Sem dados horários para exibir")
        else:
            altura = max(300, min(750, 22 * len(horas_norm.index) + 140))

            # preparar matrizes
            z_norm = horas_norm.values.astype(float)                # valores normalizados (0..1)
            raw_vals = np.array(horas_raw.values, dtype=float)     # valores brutos (itens)
            # main heatmap: apenas células > 0 (zeros viram NaN para não serem coloridas pelo gradiente)
            z_main = np.where(raw_vals > 0, z_norm, np.nan)
            # máscara para zeros: 1 onde zero, NaN caso contrário (será desenhada em cinza)
            z_zero = np.where(raw_vals == 0, 1.0, np.nan)

            fig = go.Figure()
            # Heatmap principal (gradiente para valores > 0)
            fig.add_trace(go.Heatmap(
                z=z_main,
                x=list(range(7,23)),
                y=list(horas_norm.index),
                colorscale=[(0.0, "rgb(49,130,189)"), (1.0, "rgb(220,20,60)")],
                zmin=0, zmax=1,
                colorbar=dict(title="Baixo ↔ Alto"),
                hoverongaps=False,
                showscale=True
            ))
            # Overlay para zeros (cor cinza)
            fig.add_trace(go.Heatmap(
                z=z_zero,
                x=list(range(7,23)),
                y=list(horas_norm.index),
                colorscale=[[0, "lightgray"], [1, "gray"]],
                zmin=0, zmax=1,
                showscale=False,
                hoverongaps=False
            ))

            # customdata para hover (usar valores brutos)
            fig.data[0].customdata = raw_vals[..., np.newaxis]
            fig.data[0].hovertemplate = "Linha: %{y}<br>Hora: %{x}h<br>Itens: %{customdata[0]:,.0f}<extra></extra>"
            fig.data[1].customdata = raw_vals[..., np.newaxis]
            fig.data[1].hovertemplate = "Linha: %{y}<br>Hora: %{x}h<br>Itens: %{customdata[0]:,.0f}<extra></extra>"

            fig.update_layout(
                height=altura, template="plotly_white", margin=dict(t=20, b=20, l=30, r=30),
                xaxis_title="Hora do dia", yaxis=dict(
                title="",
                tickfont=dict(size=10),
                autorange='reversed',
                categoryorder='array',
                categoryarray=top_names
            ))
            # manter gaps visuais
            fig.update_traces(xgap=1, ygap=2)
            st.plotly_chart(fig, use_container_width=True)

    elif escolha == "🗓️ Dias":
        if not tem_dias:
            st.info("Sem dados por dia da semana")
        else:
            weekday_labels = ["Seg","Ter","Qua","Qui","Sex","Sáb","Dom"]
            altura = max(300, min(750, 22 * len(dias_norm.index) + 140))

            # preparar matrizes
            z_norm = dias_norm.values.astype(float)
            raw_vals = np.array(dias_raw.values, dtype=float)
            z_main = np.where(raw_vals > 0, z_norm, np.nan)
            z_zero = np.where(raw_vals == 0, 1.0, np.nan)

            fig = go.Figure()
            fig.add_trace(go.Heatmap(
                z=z_main,
                x=weekday_labels,
                y=list(dias_norm.index),
                colorscale=[(0.0, "rgb(49,130,189)"), (1.0, "rgb(220,20,60)")],
                zmin=0, zmax=1,
                colorbar=dict(title="Baixo ↔ Alto"),
                hoverongaps=False,
                showscale=True
            ))
            fig.add_trace(go.Heatmap(
                z=z_zero,
                x=weekday_labels,
                y=list(dias_norm.index),
                colorscale=[[0, "lightgray"], [1, "gray"]],
                zmin=0, zmax=1,
                showscale=False,
                hoverongaps=False
            ))

            fig.data[0].customdata = raw_vals[..., np.newaxis]
            fig.data[0].hovertemplate = "Linha: %{y}<br>Dia: %{x}<br>Itens: %{customdata[0]:,.0f}<extra></extra>"
            fig.data[1].customdata = raw_vals[..., np.newaxis]
            fig.data[1].hovertemplate = "Linha: %{y}<br>Dia: %{x}<br>Itens: %{customdata[0]:,.0f}<extra></extra>"

            fig.update_layout(
                height=altura, template="plotly_white", margin=dict(t=20, b=20, l=30, r=30),
                xaxis_title="Dia da semana", yaxis=dict(
                    title="",
                    tickfont=dict(size=10),
                    autorange='reversed',
                    categoryorder='array',
                    categoryarray=top_names
                )
            )
            fig.update_xaxes(side="top")
            fig.update_traces(xgap=1, ygap=2)
            st.plotly_chart(fig, use_container_width=True)

def criar_conteudo_popover_ticket_vendedores_duck(filial_codigo: str | None = None, vendedores: list[str] | None = None, top_n: int = 10, data_ref: date | None = None) -> pd.DataFrame:
    """
    Popover: Ticket Médio por vendedor (visão com 4 pills).
    Segue a mesma estrutura do popover de vendas: total da loja MTD, ranking top_n, dados 90 dias,
    média por dia e heatmaps por hora/dia com foco em ticket médio.
    Retorna DataFrame com ['vendedor_nome','ticket_medio'].
    """
    # Datas
    if data_ref is None:
        data_ref = date.today() - timedelta(days=1)
    inicio_mes = data_ref.replace(day=1)
    jan_90 = data_ref - timedelta(days=89)
    dias_corridos = (data_ref - inicio_mes).days + 1

    cond_filial = _cond_filial(filial_codigo)
        
    # Âncora largura e título
    st.markdown("""
    <div style="width:650px; min-width:650px; height:1px; background:transparent; margin:0; padding:0; overflow:hidden;"></div>
    """, unsafe_allow_html=True)
    st.markdown(f"### 🎯 Ticket Médio - Filial {filial_codigo or 'Todas'}")

    # Total da loja MTD (para percentuais se necessário)
    sql_total_loja = f"""
        SELECT COALESCE(SUM(item_valortotal), 0) AS total_loja_mtd
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{inicio_mes}' AND DATE '{data_ref}'
        {cond_filial}
    """
    df_total = duck_query(sql_total_loja)
    total_loja_mtd = float(df_total.iloc[0]['total_loja_mtd']) if (df_total is not None and not df_total.empty) else 0.0

    # Ranking por valor (usado para selecionar top_n) e cálculo básico de ticket_medio
    sql_rank = f"""
        SELECT
            TRIM(vendedor_nome) AS vendedor_nome,
            COALESCE(SUM(item_valortotal),0) AS total_venda,
            COUNT(DISTINCT venda_id) AS num_vendas,
            CASE WHEN COUNT(DISTINCT venda_id) > 0 THEN SUM(item_valortotal) / COUNT(DISTINCT venda_id) ELSE 0 END AS ticket_medio
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{inicio_mes}' AND DATE '{data_ref}'
        {cond_filial}
                  AND vendedor_nome IS NOT NULL
          AND TRIM(vendedor_nome) != ''
          AND TRIM(vendedor_nome) != 'Sem Vendedor'
        GROUP BY 1
        ORDER BY 2 DESC
        LIMIT {top_n}
    """
    df_ticket = duck_query(sql_rank)
    if df_ticket is None or df_ticket.empty:
        st.info("Sem dados de ticket médio para exibir")
        return pd.DataFrame(columns=['vendedor_nome', 'ticket_medio'])

    # Percentual sobre total loja (opcional)
    df_ticket['percentual'] = (df_ticket['total_venda'] / total_loja_mtd * 100) if total_loja_mtd > 0 else 0.0
    top_names = df_ticket['vendedor_nome'].tolist()

    # Dados 90 dias (para média 90d)
    sql_90 = f"""
        SELECT
            TRIM(vendedor_nome) AS vendedor_nome,
            COALESCE(SUM(item_valortotal),0) AS total_90,
            COUNT(DISTINCT venda_id) AS num_vendas_90,
            CASE WHEN COUNT(DISTINCT venda_id) > 0 THEN SUM(item_valortotal) / COUNT(DISTINCT venda_id) ELSE 0 END AS ticket_medio_90
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{jan_90}' AND DATE '{data_ref}'
        {cond_filial}
          AND vendedor_nome IS NOT NULL
          AND TRIM(vendedor_nome) != ''
          AND TRIM(vendedor_nome) != 'Sem Vendedor'
        GROUP BY 1
    """
    df_90 = duck_query(sql_90)

    df_90 = df_90[df_90['vendedor_nome'].isin(top_names)]
    
    # Preparar heatmap horas (ticket médio por hora) — garante linhas para todos os top_names
    def preparar_heatmap_horas_ticket():
        sql_horas = f"""
            SELECT
                TRIM(vendedor_nome) AS vendedor_nome,
                EXTRACT(hour FROM datahora) AS hora,
                COALESCE(SUM(item_valortotal),0) AS soma_valor,
                COUNT(DISTINCT venda_id) AS num_vendas_h
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{inicio_mes}' AND DATE '{data_ref}'
            {cond_filial}
            
              AND vendedor_nome IS NOT NULL
              AND TRIM(vendedor_nome) != ''
              AND TRIM(vendedor_nome) != 'Sem Vendedor'
              AND EXTRACT(hour FROM datahora) BETWEEN 7 AND 22
            GROUP BY 1,2
        """
        df_h = duck_query(sql_horas)
        if df_h is None or df_h.empty:
            return None, None, False

        df_h['ticket_medio'] = df_h.apply(lambda r: (float(r['soma_valor']) / int(r['num_vendas_h'])) if int(r['num_vendas_h']) > 0 else 0.0, axis=1)
        mat = df_h.pivot_table(index='vendedor_nome', columns='hora', values='ticket_medio', fill_value=0.0)
        for h in range(7,23):
            if h not in mat.columns:
                mat[h] = 0.0
        mat = mat[list(range(7,23))]
        mat = mat.reindex(index=top_names).fillna(0.0)
        
        # Total loja por hora (ticket médio geral)
        sql_total_hora = f"""
            SELECT
            EXTRACT(hour FROM datahora) AS hora,
            COALESCE(SUM(item_valortotal),0) AS soma_valor,
            COUNT(DISTINCT venda_id) AS num_vendas_h
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{inicio_mes}' AND DATE '{data_ref}'
            {cond_filial}
              AND EXTRACT(hour FROM datahora) BETWEEN 7 AND 22
            GROUP BY 1
            HAVING COUNT(DISTINCT venda_id) > 10
        """
        df_mes_h = duck_query(sql_total_hora)
        if df_mes_h is None or df_mes_h.empty:
            total_por_hora = pd.Series([0.0]*len(range(7,23)), index=list(range(7,23)))
        else:
            df_mes_h['ticket_medio'] = df_mes_h.apply(lambda r: (float(r['soma_valor']) / int(r['num_vendas_h'])) if int(r['num_vendas_h']) > 0 else 0.0, axis=1)
            total_por_hora = df_mes_h.set_index('hora')['ticket_medio'].reindex(range(7,23), fill_value=0.0)

        row_total = pd.DataFrame([total_por_hora.values], index=['Total Loja'], columns=range(7,23))
        final_mat = pd.concat([row_total, mat], axis=0).fillna(0.0)

        # Normalização
        mat_norm = final_mat.copy()
        row_min = mat_norm.min(axis=1)
        row_max = mat_norm.max(axis=1)
        denom = (row_max - row_min).replace(0, 1)
        mat_norm = mat_norm.sub(row_min, axis=0).div(denom, axis=0)

        return final_mat, mat_norm, True
    
    # Preparar heatmap dias (ticket médio por weekday)
    def preparar_heatmap_dias_ticket():
        sql_dias = f"""
            SELECT
                TRIM(vendedor_nome) AS vendedor_nome,
                EXTRACT(dow FROM data_date) AS weekday,
                COALESCE(SUM(item_valortotal),0) AS soma_valor,
                COUNT(DISTINCT venda_id) AS num_vendas_w
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{inicio_mes}' AND DATE '{data_ref}'
            {cond_filial}
            
              AND vendedor_nome IS NOT NULL
              AND TRIM(vendedor_nome) != ''
              AND TRIM(vendedor_nome) != 'Sem Vendedor'
            GROUP BY 1,2
            HAVING COUNT(DISTINCT venda_id) > 10
        """
        df_d = duck_query(sql_dias)
        if df_d is None or df_d.empty:
            return None, None, False

        df_d['ticket_medio'] = df_d.apply(lambda r: (float(r['soma_valor']) / int(r['num_vendas_w'])) if int(r['num_vendas_w']) > 0 else 0.0, axis=1)
        mat = df_d.pivot_table(index='vendedor_nome', columns='weekday', values='ticket_medio', fill_value=0.0)
        for w in range(7):
            if w not in mat.columns:
                mat[w] = 0.0
        mat = mat[list(range(7))]
        mat = mat.reindex(index=top_names).fillna(0.0)

        # Total loja por weekday
        sql_total_dia = f"""
            SELECT
                EXTRACT(dow FROM data_date) AS weekday,
                COALESCE(SUM(item_valortotal),0) AS soma_valor,
                COUNT(DISTINCT venda_id) AS num_vendas_w
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{inicio_mes}' AND DATE '{data_ref}'
            {cond_filial}
            GROUP BY 1
        """
        df_mes_d = duck_query(sql_total_dia)
        if df_mes_d is None or df_mes_d.empty:
            total_por_dia = pd.Series([0.0]*7, index=list(range(7)))
        else:
            df_mes_d['ticket_medio'] = df_mes_d.apply(lambda r: (float(r['soma_valor']) / int(r['num_vendas_w'])) if int(r['num_vendas_w']) > 0 else 0.0, axis=1)
            total_por_dia = df_mes_d.set_index('weekday')['ticket_medio'].reindex(range(7), fill_value=0.0)

        row_total = pd.DataFrame([total_por_dia.values], index=['Total Loja'], columns=range(7))
        final_mat = pd.concat([row_total, mat], axis=0).fillna(0.0)

        mat_norm = final_mat.copy()
        row_min = mat_norm.min(axis=1)
        row_max = mat_norm.max(axis=1)
        denom = (row_max - row_min).replace(0, 1)
        mat_norm = mat_norm.sub(row_min, axis=0).div(denom, axis=0)

        return final_mat, mat_norm, True

    horas_raw, horas_norm, tem_horas = preparar_heatmap_horas_ticket()
    dias_raw, dias_norm, tem_dias = preparar_heatmap_dias_ticket()

    # Pills / UI
    opcoes = ["💵 Ticket Médio", "🕒 Horas", "🗓️ Dias"]
    state_key = f"pills_ticket_vendedores_{filial_codigo or 'todas'}_{','.join(top_names)[:60]}"
    if state_key not in st.session_state:
        st.session_state[state_key] = opcoes[0]
    escolha = st.pills("Escolha a visualização:", opcoes, key=state_key)

    if escolha == "💵 Ticket Médio":
        df_plot = df_ticket.sort_values('ticket_medio', ascending=False)
        fig = px.bar(df_plot, x='ticket_medio', y='vendedor_nome', orientation='h', text_auto='.2s')
        fig.update_traces(marker_color='darkslateblue', textangle=0, textposition="inside", textfont=dict(color='white', size=10))
        fig.add_trace(go.Scatter(
                x=df_90['ticket_medio_90'], y=df_90['vendedor_nome'], mode='markers',
                marker=dict(symbol='line-ns', size=12, color='black', line=dict(width=2, color='orange')),
                name='Média 90d', showlegend=True, hovertemplate="Vendedor: %{y}<br>Média 90d: R$ %{x:.2f}<extra></extra>"
            ))
        fig.update_layout(
            height=max(300, min(800, 28 * len(df_plot) + 120)),
            showlegend=False, template="plotly_white",
            margin=dict(t=20, b=20, l=30, r=30),
            xaxis=dict(title="Ticket Médio (R$)", tickfont=dict(size=10)),
            yaxis=dict(title="", tickfont=dict(size=10), autorange='reversed'),
            bargap=0.35
        )
        st.plotly_chart(fig, use_container_width=True)
    
    elif escolha == "🕒 Horas":
        if not tem_horas:
            st.info("Sem dados horários para exibir")
        else:
            altura = max(300, min(750, 22 * len(horas_norm.index) + 140))

            # preparar matrizes
            z_norm = horas_norm.values.astype(float)                # valores normalizados (0..1)
            raw_vals = np.array(horas_raw.values, dtype=float)     # valores brutos (R$)
            # main heatmap: apenas células > 0 (zeros viram NaN para não serem coloridas pelo gradiente)
            z_main = np.where(raw_vals > 0, z_norm, np.nan)
            # máscara para zeros: 1 onde zero, NaN caso contrário (será desenhada em cinza)
            z_zero = np.where(raw_vals == 0, 1.0, np.nan)

            fig = go.Figure()
            # Heatmap principal (gradiente para valores > 0)
            fig.add_trace(go.Heatmap(
                z=z_main,
                x=list(range(7,23)),
                y=list(horas_norm.index),
                colorscale=[(0.0, "rgb(49,130,189)"), (1.0, "rgb(220,20,60)")],
                zmin=0, zmax=1,
                colorbar=dict(title="Baixo ↔ Alto"),
                hoverongaps=False,
                showscale=True
            ))
            # Overlay para zeros (cor cinza)
            fig.add_trace(go.Heatmap(
                z=z_zero,
                x=list(range(7,23)),
                y=list(horas_norm.index),
                colorscale=[[0, "lightgray"], [1, "gray"]],
                zmin=0, zmax=1,
                showscale=False,
                hoverongaps=False
            ))

            # customdata para hover (usar valores brutos)
            fig.data[0].customdata = raw_vals[..., np.newaxis]
            fig.data[0].hovertemplate = "Linha: %{y}<br>Hora: %{x}h<br>Ticket Médio: R$ %{customdata[0]:.2f}<extra></extra>"
            fig.data[1].customdata = raw_vals[..., np.newaxis]
            fig.data[1].hovertemplate = "Linha: %{y}<br>Hora: %{x}h<br>Ticket Médio: R$ %{customdata[0]:.2f}<extra></extra>"

            fig.update_layout(
                height=altura, template="plotly_white", margin=dict(t=20, b=20, l=30, r=30),
                xaxis_title="Hora do dia", yaxis=dict(
                title="",
                tickfont=dict(size=10),
                autorange='reversed',
                categoryorder='array',
                categoryarray=top_names
            ))
            # manter gaps visuais
            fig.update_traces(xgap=1, ygap=2)
            st.plotly_chart(fig, use_container_width=True)

    elif escolha == "🗓️ Dias":
        if not tem_dias:
            st.info("Sem dados por dia da semana")
        else:
            weekday_labels = ["Seg","Ter","Qua","Qui","Sex","Sáb","Dom"]
            altura = max(300, min(750, 22 * len(dias_norm.index) + 140))

            # preparar matrizes
            z_norm = dias_norm.values.astype(float)
            raw_vals = np.array(dias_raw.values, dtype=float)
            z_main = np.where(raw_vals > 0, z_norm, np.nan)
            z_zero = np.where(raw_vals == 0, 1.0, np.nan)

            fig = go.Figure()
            fig.add_trace(go.Heatmap(
                z=z_main,
                x=weekday_labels,
                y=list(dias_norm.index),
                colorscale=[(0.0, "rgb(49,130,189)"), (1.0, "rgb(220,20,60)")],
                zmin=0, zmax=1,
                colorbar=dict(title="Baixo ↔ Alto"),
                hoverongaps=False,
                showscale=True
            ))
            fig.add_trace(go.Heatmap(
                z=z_zero,
                x=weekday_labels,
                y=list(dias_norm.index),
                colorscale=[[0, "lightgray"], [1, "gray"]],
                zmin=0, zmax=1,
                showscale=False,
                hoverongaps=False
            ))

            fig.data[0].customdata = raw_vals[..., np.newaxis]
            fig.data[0].hovertemplate = "Linha: %{y}<br>Dia: %{x}<br>Ticket Médio: R$ %{customdata[0]:.2f}<extra></extra>"
            fig.data[1].customdata = raw_vals[..., np.newaxis]
            fig.data[1].hovertemplate = "Linha: %{y}<br>Dia: %{x}<br>Ticket Médio: R$ %{customdata[0]:.2f}<extra></extra>"

            fig.update_layout(
                height=altura, template="plotly_white", margin=dict(t=20, b=20, l=30, r=30),
                xaxis_title="Dia da semana", yaxis=dict(
                title="",
                tickfont=dict(size=10),
                autorange='reversed',
                categoryorder='array',
                categoryarray=top_names
            ))
            fig.update_xaxes(side="top")
            fig.update_traces(xgap=1, ygap=2)
            st.plotly_chart(fig, use_container_width=True)

    # Retornar DataFrame com ticket médio (compatível com usos programáticos)
    return df_ticket[['vendedor_nome', 'ticket_medio']].reset_index(drop=True)

def criar_conteudo_popover_itens_vendedores_duck(filial_codigo: str | None = None, vendedores: list[str] | None = None, top_n: int = 10, data_ref: date | None = None) -> pd.DataFrame:
    """
    Popover: Itens por Nota por vendedor (visão com 3 pills).
    Segue a mesma estrutura do popover de ticket médio: total da loja MTD, ranking top_n, dados 90 dias,
    média por dia e heatmaps por hora/dia com foco em itens por nota.
    Retorna DataFrame com ['vendedor_nome','itens_por_nota'].
    """
    # Datas
    if data_ref is None:
        data_ref = date.today() - timedelta(days=1)
    inicio_mes = data_ref.replace(day=1)
    jan_90 = data_ref - timedelta(days=89)
    dias_corridos = (data_ref - inicio_mes).days + 1

    cond_filial = _cond_filial(filial_codigo)
    
    # Âncora largura e título
    st.markdown("""
    <div style="width:650px; min-width:650px; height:1px; background:transparent; margin:0; padding:0; overflow:hidden;"></div>
    """, unsafe_allow_html=True)
    st.markdown(f"### 🧾 Itens por Nota - Filial {filial_codigo or 'Todas'}")

    # Total da loja MTD (itens) para percentuais se necessário
    sql_total_loja = f"""
        SELECT COALESCE(SUM(item_quantidade), 0) AS total_loja_mtd
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{inicio_mes}' AND DATE '{data_ref}'
        {cond_filial}
    """
    df_total = duck_query(sql_total_loja)
    total_loja_mtd = float(df_total.iloc[0]['total_loja_mtd']) if (df_total is not None and not df_total.empty) else 0.0

    # Ranking por quantidade (usado para selecionar top_n) e cálculo de itens_por_nota
    sql_rank = f"""
        SELECT
            TRIM(vendedor_nome) AS vendedor_nome,
            COALESCE(SUM(item_quantidade),0) AS quantidade_total,
            COUNT(DISTINCT venda_id) AS num_vendas,
            CASE WHEN COUNT(DISTINCT venda_id) > 0 THEN SUM(item_quantidade) / COUNT(DISTINCT venda_id) ELSE 0 END AS itens_por_nota
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{inicio_mes}' AND DATE '{data_ref}'
        {cond_filial}
        AND vendedor_nome IS NOT NULL
          AND TRIM(vendedor_nome) != ''
          AND TRIM(vendedor_nome) != 'Sem Vendedor'
        GROUP BY 1
        ORDER BY 2 DESC
        LIMIT {top_n}
    """
    df_rank = duck_query(sql_rank)
    if df_rank is None or df_rank.empty:
        st.info("Sem dados de itens por nota para exibir")
        return pd.DataFrame(columns=['vendedor_nome', 'itens_por_nota'])

    df_rank['percentual'] = (df_rank['quantidade_total'] / total_loja_mtd * 100) if total_loja_mtd > 0 else 0.0
    top_names = df_rank['vendedor_nome'].tolist()

    # Dados 90 dias (para média 90d) - filtrar depois pelos top_names
    sql_90 = f"""
        SELECT
            TRIM(vendedor_nome) AS vendedor_nome,
            COALESCE(SUM(item_quantidade),0) AS total_90,
            COUNT(DISTINCT venda_id) AS num_vendas_90,
            CASE WHEN COUNT(DISTINCT venda_id) > 0 THEN SUM(item_quantidade) / COUNT(DISTINCT venda_id) ELSE 0 END AS itens_por_nota_90
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{jan_90}' AND DATE '{data_ref}'
        {cond_filial}
        AND vendedor_nome IS NOT NULL
          AND TRIM(vendedor_nome) != ''
          AND TRIM(vendedor_nome) != 'Sem Vendedor'
        GROUP BY 1
    """
    df_90 = duck_query(sql_90)
    if df_90 is None:
        df_90 = pd.DataFrame(columns=['vendedor_nome', 'total_90', 'num_vendas_90', 'itens_por_nota_90'])
    else:
        df_90 = df_90[df_90['vendedor_nome'].isin(top_names)].copy()

    # Média por dia (mês atual) — usar quantidade_total / dias_corridos (mesma lógica dos outros popovers)
    media_dia = df_rank[['vendedor_nome','quantidade_total']].copy()
    media_dia['media_dia'] = media_dia['quantidade_total'] / max(dias_corridos, 1)
    if not df_90.empty:
        rank90 = df_90.set_index('vendedor_nome')['total_90'].to_dict()
        media_dia['media_90d'] = media_dia['vendedor_nome'].map(lambda n: rank90.get(n, 0.0) / 90.0)
    else:
        media_dia['media_90d'] = 0.0

    media_dia = media_dia[media_dia['vendedor_nome'].isin(top_names)].copy()
    media_dia = media_dia.sort_values('media_dia', ascending=False)

    # Preparar heatmap horas (itens_por_nota por hora) — garante linhas para todos os top_names
    def preparar_heatmap_horas_itens():
        sql_horas = f"""
            SELECT
                TRIM(vendedor_nome) AS vendedor_nome,
                EXTRACT(hour FROM datahora) AS hora,
                COALESCE(SUM(item_quantidade),0) AS soma_itens,
                COUNT(DISTINCT venda_id) AS num_vendas_h
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{inicio_mes}' AND DATE '{data_ref}'
            {cond_filial}
            AND vendedor_nome IS NOT NULL
              AND TRIM(vendedor_nome) != ''
              AND TRIM(vendedor_nome) != 'Sem Vendedor'
              AND EXTRACT(hour FROM datahora) BETWEEN 7 AND 22
            GROUP BY 1,2
        """
        df_h = duck_query(sql_horas)
        if df_h is None or df_h.empty:
            return None, None, False

        df_h['itens_por_nota'] = df_h.apply(lambda r: (float(r['soma_itens']) / int(r['num_vendas_h'])) if int(r['num_vendas_h']) > 0 else 0.0, axis=1)
        mat = df_h.pivot_table(index='vendedor_nome', columns='hora', values='itens_por_nota', fill_value=0.0)
        for h in range(7,23):
            if h not in mat.columns:
                mat[h] = 0.0
        mat = mat[list(range(7,23))]
        mat = mat.reindex(index=top_names).fillna(0.0)

        # Total loja por hora (itens_por_nota geral)
        sql_total_hora = f"""
            SELECT
                EXTRACT(hour FROM datahora) AS hora,
                COALESCE(SUM(item_quantidade),0) AS soma_itens,
                COUNT(DISTINCT venda_id) AS num_vendas_h
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{inicio_mes}' AND DATE '{data_ref}'
            {cond_filial}
              AND EXTRACT(hour FROM datahora) BETWEEN 7 AND 22
            GROUP BY 1
        """
        df_mes_h = duck_query(sql_total_hora)
        if df_mes_h is None or df_mes_h.empty:
            total_por_hora = pd.Series([0.0]*len(range(7,23)), index=list(range(7,23)))
        else:
            df_mes_h['itens_por_nota'] = df_mes_h.apply(lambda r: (float(r['soma_itens']) / int(r['num_vendas_h'])) if int(r['num_vendas_h']) > 0 else 0.0, axis=1)
            total_por_hora = df_mes_h.set_index('hora')['itens_por_nota'].reindex(range(7,23), fill_value=0.0)

        row_total = pd.DataFrame([total_por_hora.values], index=['Total Loja'], columns=range(7,23))
        final_mat = pd.concat([row_total, mat], axis=0).fillna(0.0)

        # Normalização
        mat_norm = final_mat.copy()
        row_min = mat_norm.min(axis=1)
        row_max = mat_norm.max(axis=1)
        denom = (row_max - row_min).replace(0, 1)
        mat_norm = mat_norm.sub(row_min, axis=0).div(denom, axis=0)

        return final_mat, mat_norm, True

    # Preparar heatmap dias (itens_por_nota por weekday)
    def preparar_heatmap_dias_itens():
        sql_dias = f"""
            SELECT
                TRIM(vendedor_nome) AS vendedor_nome,
                EXTRACT(dow FROM data_date) AS weekday,
                COALESCE(SUM(item_quantidade),0) AS soma_itens,
                COUNT(DISTINCT venda_id) AS num_vendas_w
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{inicio_mes}' AND DATE '{data_ref}'
            {cond_filial}
            AND vendedor_nome IS NOT NULL
              AND TRIM(vendedor_nome) != ''
              AND TRIM(vendedor_nome) != 'Sem Vendedor'
            GROUP BY 1,2
        """
        df_d = duck_query(sql_dias)
        if df_d is None or df_d.empty:
            return None, None, False

        df_d['itens_por_nota'] = df_d.apply(lambda r: (float(r['soma_itens']) / int(r['num_vendas_w'])) if int(r['num_vendas_w']) > 0 else 0.0, axis=1)
        mat = df_d.pivot_table(index='vendedor_nome', columns='weekday', values='itens_por_nota', fill_value=0.0)
        for w in range(7):
            if w not in mat.columns:
                mat[w] = 0.0
        mat = mat[list(range(7))]
        mat = mat.reindex(index=top_names).fillna(0.0)

        # Total loja por weekday
        sql_total_dia = f"""
            SELECT
                EXTRACT(dow FROM data_date) AS weekday,
                COALESCE(SUM(item_quantidade),0) AS soma_itens,
                COUNT(DISTINCT venda_id) AS num_vendas_w
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{inicio_mes}' AND DATE '{data_ref}'
            {cond_filial}
            GROUP BY 1
        """
        df_mes_d = duck_query(sql_total_dia)
        if df_mes_d is None or df_mes_d.empty:
            total_por_dia = pd.Series([0.0]*7, index=list(range(7)))
        else:
            df_mes_d['itens_por_nota'] = df_mes_d.apply(lambda r: (float(r['soma_itens']) / int(r['num_vendas_w'])) if int(r['num_vendas_w']) > 0 else 0.0, axis=1)
            total_por_dia = df_mes_d.set_index('weekday')['itens_por_nota'].reindex(range(7), fill_value=0.0)

        row_total = pd.DataFrame([total_por_dia.values], index=['Total Loja'], columns=range(7))
        final_mat = pd.concat([row_total, mat], axis=0).fillna(0.0)

        mat_norm = final_mat.copy()
        row_min = mat_norm.min(axis=1)
        row_max = mat_norm.max(axis=1)
        denom = (row_max - row_min).replace(0, 1)
        mat_norm = mat_norm.sub(row_min, axis=0).div(denom, axis=0)

        return final_mat, mat_norm, True

    horas_raw, horas_norm, tem_horas = preparar_heatmap_horas_itens()
    dias_raw, dias_norm, tem_dias = preparar_heatmap_dias_itens()

    # Pills / UI (3 pills: Itens/Nota, Horas, Dias)
    opcoes = ["🔢 Itens/Nota", "🕒 Horas", "🗓️ Dias"]
    state_key = f"pills_itens_vendedores_{filial_codigo or 'todas'}_{','.join(top_names)[:60]}"
    if state_key not in st.session_state:
        st.session_state[state_key] = opcoes[0]
    escolha = st.pills("Escolha a visualização:", opcoes, key=state_key)

    if escolha == "🔢 Itens/Nota":
        df_plot = df_rank.sort_values('itens_por_nota', ascending=False)
        fig = px.bar(df_plot, x='itens_por_nota', y='vendedor_nome', orientation='h', text_auto='.2s')
        fig.update_traces(marker_color='darkslateblue', textangle=0, textposition="inside", textfont=dict(color='white', size=10))
        # adicionar média 90d de itens_por_nota se disponível
        if not df_90.empty and 'itens_por_nota_90' in df_90.columns:
            fig.add_trace(go.Scatter(
                x=df_90['itens_por_nota_90'], y=df_90['vendedor_nome'], mode='markers',
                marker=dict(symbol='line-ns', size=12, color='black', line=dict(width=2, color='orange')),
                name='Média 90d', showlegend=True, hovertemplate="Vendedor: %{y}<br>Média 90d itens/nota: %{x:.2f}<extra></extra>"
            ))
        fig.update_layout(
            height=max(300, min(800, 28 * len(df_plot) + 120)),
            showlegend=False, template="plotly_white",
            margin=dict(t=20, b=20, l=30, r=30),
            xaxis=dict(title="Itens por Nota", tickfont=dict(size=10)),
            yaxis=dict(title="", tickfont=dict(size=10), autorange='reversed'),
            bargap=0.35
        )
        st.plotly_chart(fig, use_container_width=True)

    elif escolha == "🕒 Horas":
        if not tem_horas:
            st.info("Sem dados horários para exibir")
        else:
            altura = max(300, min(750, 22 * len(horas_norm.index) + 140))

            # preparar matrizes
            z_norm = horas_norm.values.astype(float)                # valores normalizados (0..1)
            raw_vals = np.array(horas_raw.values, dtype=float)     # valores brutos (itens por nota)
            # main heatmap: apenas células > 0 (zeros viram NaN para não serem coloridas pelo gradiente)
            z_main = np.where(raw_vals > 0, z_norm, np.nan)
            # máscara para zeros: 1 onde zero, NaN caso contrário (será desenhada em cinza)
            z_zero = np.where(raw_vals == 0, 1.0, np.nan)

            fig = go.Figure()
            # Heatmap principal (gradiente para valores > 0)
            fig.add_trace(go.Heatmap(
                z=z_main,
                x=list(range(7,23)),
                y=list(horas_norm.index),
                colorscale=[(0.0, "rgb(49,130,189)"), (1.0, "rgb(220,20,60)")],
                zmin=0, zmax=1,
                colorbar=dict(title="Baixo ↔ Alto"),
                hoverongaps=False,
                showscale=True
            ))
            # Overlay para zeros (cor cinza)
            fig.add_trace(go.Heatmap(
                z=z_zero,
                x=list(range(7,23)),
                y=list(horas_norm.index),
                colorscale=[[0, "lightgray"], [1, "gray"]],
                zmin=0, zmax=1,
                showscale=False,
                hoverongaps=False
            ))

            # customdata para hover (usar valores brutos)
            fig.data[0].customdata = raw_vals[..., np.newaxis]
            fig.data[0].hovertemplate = "Linha: %{y}<br>Hora: %{x}h<br>Itens/Nota: %{customdata[0]:.2f}<extra></extra>"
            fig.data[1].customdata = raw_vals[..., np.newaxis]
            fig.data[1].hovertemplate = "Linha: %{y}<br>Hora: %{x}h<br>Itens/Nota: %{customdata[0]:.2f}<extra></extra>"

            fig.update_layout(
                height=altura, template="plotly_white", margin=dict(t=20, b=20, l=30, r=30),
                xaxis_title="Hora do dia", yaxis=dict(
                title="",
                tickfont=dict(size=10),
                autorange='reversed',
                categoryorder='array',
                categoryarray=top_names
            ))
            # manter gaps visuais
            fig.update_traces(xgap=1, ygap=2)
            st.plotly_chart(fig, use_container_width=True)

    elif escolha == "🗓️ Dias":
        if not tem_dias:
            st.info("Sem dados por dia da semana")
        else:
            weekday_labels = ["Seg","Ter","Qua","Qui","Sex","Sáb","Dom"]
            altura = max(300, min(750, 22 * len(dias_norm.index) + 140))

            # preparar matrizes
            z_norm = dias_norm.values.astype(float)
            raw_vals = np.array(dias_raw.values, dtype=float)     # valores brutos (itens por nota)
            z_main = np.where(raw_vals > 0, z_norm, np.nan)
            z_zero = np.where(raw_vals == 0, 1.0, np.nan)

            fig = go.Figure()
            fig.add_trace(go.Heatmap(
                z=z_main,
                x=weekday_labels,
                y=list(dias_norm.index),
                colorscale=[(0.0, "rgb(49,130,189)"), (1.0, "rgb(220,20,60)")],
                zmin=0, zmax=1,
                colorbar=dict(title="Baixo ↔ Alto"),
                hoverongaps=False,
                showscale=True
            ))
            fig.add_trace(go.Heatmap(
                z=z_zero,
                x=weekday_labels,
                y=list(dias_norm.index),
                colorscale=[[0, "lightgray"], [1, "gray"]],
                zmin=0, zmax=1,
                showscale=False,
                hoverongaps=False
            ))

            fig.data[0].customdata = raw_vals[..., np.newaxis]
            fig.data[0].hovertemplate = "Linha: %{y}<br>Dia: %{x}<br>Itens/Nota: %{customdata[0]:.2f}<extra></extra>"
            fig.data[1].customdata = raw_vals[..., np.newaxis]
            fig.data[1].hovertemplate = "Linha: %{y}<br>Dia: %{x}<br>Itens/Nota: %{customdata[0]:.2f}<extra></extra>"

            fig.update_layout(
                height=altura, template="plotly_white", margin=dict(t=20, b=20, l=30, r=30),
                xaxis_title="Dia da semana", yaxis=dict(
                title="",
                tickfont=dict(size=10),
                autorange='reversed',
                categoryorder='array',
                categoryarray=top_names
            ))
            fig.update_xaxes(side="top")
            fig.update_traces(xgap=1, ygap=2)
            st.plotly_chart(fig, use_container_width=True)

    # Retornar DataFrame com itens_por_nota (compatível com usos programáticos)
    return df_rank[['vendedor_nome', 'itens_por_nota']].reset_index(drop=True)

def criar_conteudo_popover_vitaminas_vendedores_duck(filial_selecionada: str | None = None, vendedores: list[str] | None = None, top_n: int = 10, data_ref: date | None = None) -> pd.DataFrame:
    """
    Popover: Vitaminas vendidas por vendedor (visão com 4 pills: Quantidade, Média/dia, Horas, Dias).
    Estrutura idêntica ao popover de itens/nº vendas, mas filtrando somente classificação_n2 = 'VITAMINAS'.
    Retorna DataFrame com ['vendedor_nome','quantidade_vitaminas'] (top_n).
    """
    # Datas
    if data_ref is None:
        data_ref = date.today() - timedelta(days=1)
    inicio_mes = data_ref.replace(day=1)
    jan_90 = data_ref - timedelta(days=89)
    dias_corridos = (data_ref - inicio_mes).days + 1

    # UI - âncora e título
    st.markdown("""
    <div style="width:650px; min-width:650px; height:1px; background:transparent; margin:0; padding:0; overflow:hidden;"></div>
    """, unsafe_allow_html=True)
    st.markdown(f"### 🍊 Vitaminas - Filial {filial_selecionada or 'Todas'}")

    cond_filial = _cond_filial(filial_selecionada)
    
    # Total loja (vitaminas) no mês
    sql_total_loja = f"""
        SELECT COALESCE(SUM(CASE WHEN UPPER(TRIM(COALESCE(classificacao_n2, ''))) = 'VITAMINAS' THEN item_quantidade ELSE 0 END), 0) AS total_loja_mtd
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{inicio_mes}' AND DATE '{data_ref}'
        {cond_filial}
    """
    df_total = duck_query(sql_total_loja)
    total_loja_mtd = float(df_total.iloc[0]['total_loja_mtd']) if (df_total is not None and not df_total.empty) else 0.0

    # Ranking por quantidade de vitaminas (top N)
    sql_rank_qtd = f"""
        SELECT
            TRIM(vendedor_nome) AS vendedor_nome,
            COALESCE(SUM(CASE WHEN UPPER(TRIM(COALESCE(classificacao_n2, ''))) = 'VITAMINAS' THEN item_quantidade ELSE 0 END),0) AS quantidade_vitaminas
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{inicio_mes}' AND DATE '{data_ref}'
        {cond_filial}
        
          AND vendedor_nome IS NOT NULL
          AND TRIM(vendedor_nome) != ''
          AND TRIM(vendedor_nome) != 'Sem Vendedor'
        GROUP BY 1
        ORDER BY 2 DESC
        LIMIT {top_n}
    """
    rank_qtd = duck_query(sql_rank_qtd)
    if rank_qtd is None or rank_qtd.empty:
        st.info("Sem vendedores para exibir")
        return pd.DataFrame(columns=['vendedor_nome', 'quantidade_vitaminas'])

    rank_qtd['percentual'] = (rank_qtd['quantidade_vitaminas'] / total_loja_mtd * 100) if total_loja_mtd > 0 else 0.0
    top_names = rank_qtd['vendedor_nome'].tolist()

    # Dados 90 dias (vitaminas)
    sql_90 = f"""
        SELECT
            TRIM(vendedor_nome) AS vendedor_nome,
            COALESCE(SUM(CASE WHEN UPPER(TRIM(COALESCE(classificacao_n2, ''))) = 'VITAMINAS' THEN item_quantidade ELSE 0 END),0) AS quantidade_total
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{jan_90}' AND DATE '{data_ref}'
        {cond_filial}
        
          AND vendedor_nome IS NOT NULL
          AND TRIM(vendedor_nome) != ''
          AND TRIM(vendedor_nome) != 'Sem Vendedor'
        GROUP BY 1
    """
    df_90 = duck_query(sql_90)
    if df_90 is None:
        df_90 = pd.DataFrame(columns=['vendedor_nome', 'quantidade_total'])
    else:
        df_90 = df_90[df_90['vendedor_nome'].isin(top_names)].copy()

    # Média por dia
    media_dia = rank_qtd[['vendedor_nome','quantidade_vitaminas']].copy()
    media_dia['media_dia'] = media_dia['quantidade_vitaminas'] / max(dias_corridos, 1)
    if not df_90.empty:
        rank90 = df_90.set_index('vendedor_nome')['quantidade_total'].to_dict()
        media_dia['media_90d'] = media_dia['vendedor_nome'].map(lambda n: rank90.get(n, 0.0) / 90.0)
    else:
        media_dia['media_90d'] = 0.0

    media_dia = media_dia[media_dia['vendedor_nome'].isin(top_names)].copy()
    media_dia = media_dia.sort_values('media_dia', ascending=False)

    # Heatmap horas (vitaminas por nota por hora)
    def preparar_heatmap_horas_vitaminas():
        sql_horas = f"""
            SELECT
                TRIM(vendedor_nome) AS vendedor_nome,
                EXTRACT(hour FROM datahora) AS hora,
                COALESCE(SUM(CASE WHEN UPPER(TRIM(COALESCE(classificacao_n2, ''))) = 'VITAMINAS' THEN item_quantidade ELSE 0 END),0) AS quantidade_vitaminas,
                COUNT(DISTINCT venda_id) AS num_vendas_h
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{inicio_mes}' AND DATE '{data_ref}'
            {cond_filial}
           
              AND vendedor_nome IS NOT NULL
              AND TRIM(vendedor_nome) != ''
              AND TRIM(vendedor_nome) != 'Sem Vendedor'
              AND EXTRACT(hour FROM datahora) BETWEEN 7 AND 22
            GROUP BY 1,2
        """
        df_h = duck_query(sql_horas)
        if df_h is None or df_h.empty:
            return None, None, False

        # Itens por nota de vitaminas por hora = quantidade_vitaminas / num_vendas_h
        df_h['itens_vitamina_por_nota'] = df_h.apply(lambda r: (float(r['quantidade_vitaminas']) / int(r['num_vendas_h'])) if int(r['num_vendas_h']) > 0 else 0.0, axis=1)
        mat = df_h.pivot_table(index='vendedor_nome', columns='hora', values='itens_vitamina_por_nota', fill_value=0.0)
        for h in range(7,23):
            if h not in mat.columns:
                mat[h] = 0.0
        mat = mat[list(range(7,23))]
        mat = mat.reindex(index=top_names).fillna(0.0)

        # Total loja por hora (itens vitamina por nota geral)
        sql_total_hora = f"""
            SELECT
                EXTRACT(hour FROM datahora) AS hora,
                COALESCE(SUM(CASE WHEN UPPER(TRIM(COALESCE(classificacao_n2, ''))) = 'VITAMINAS' THEN item_quantidade ELSE 0 END),0) AS quantidade_vitaminas,
                COUNT(DISTINCT venda_id) AS num_vendas_h
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{inicio_mes}' AND DATE '{data_ref}'
            {cond_filial}
              AND EXTRACT(hour FROM datahora) BETWEEN 7 AND 22
            GROUP BY 1
        """
        df_mes_h = duck_query(sql_total_hora)
        if df_mes_h is None or df_mes_h.empty:
            total_por_hora = pd.Series([0.0]*len(range(7,23)), index=list(range(7,23)))
        else:
            df_mes_h['itens_vitamina_por_nota'] = df_mes_h.apply(lambda r: (float(r['quantidade_vitaminas']) / int(r['num_vendas_h'])) if int(r['num_vendas_h']) > 0 else 0.0, axis=1)
            total_por_hora = df_mes_h.set_index('hora')['itens_vitamina_por_nota'].reindex(range(7,23), fill_value=0.0)

        row_total = pd.DataFrame([total_por_hora.values], index=['Total Loja'], columns=range(7,23))
        final_mat = pd.concat([row_total, mat], axis=0).fillna(0.0)

        # Normalização
        mat_norm = final_mat.copy()
        row_min = mat_norm.min(axis=1)
        row_max = mat_norm.max(axis=1)
        denom = (row_max - row_min).replace(0, 1)
        mat_norm = mat_norm.sub(row_min, axis=0).div(denom, axis=0)

        return final_mat, mat_norm, True

    # Heatmap dias (vitaminas por nota por weekday)
    def preparar_heatmap_dias_vitaminas():
        sql_dias = f"""
            SELECT
                TRIM(vendedor_nome) AS vendedor_nome,
                EXTRACT(dow FROM data_date) AS weekday,
                COALESCE(SUM(CASE WHEN UPPER(TRIM(COALESCE(classificacao_n2, ''))) = 'VITAMINAS' THEN item_quantidade ELSE 0 END),0) AS quantidade_vitaminas,
                COUNT(DISTINCT venda_id) AS num_vendas_w
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{inicio_mes}' AND DATE '{data_ref}'
            {cond_filial}
            
              AND vendedor_nome IS NOT NULL
              AND TRIM(vendedor_nome) != ''
              AND TRIM(vendedor_nome) != 'Sem Vendedor'
            GROUP BY 1,2
        """
        df_d = duck_query(sql_dias)
        if df_d is None or df_d.empty:
            return None, None, False

        df_d['itens_vitamina_por_nota'] = df_d.apply(lambda r: (float(r['quantidade_vitaminas']) / int(r['num_vendas_w'])) if int(r['num_vendas_w']) > 0 else 0.0, axis=1)
        mat = df_d.pivot_table(index='vendedor_nome', columns='weekday', values='itens_vitamina_por_nota', fill_value=0.0)
        for w in range(7):
            if w not in mat.columns:
                mat[w] = 0.0
        mat = mat[list(range(7))]
        mat = mat.reindex(index=top_names).fillna(0.0)

        sql_total_dia = f"""
            SELECT
                EXTRACT(dow FROM data_date) AS weekday,
                COALESCE(SUM(CASE WHEN UPPER(TRIM(COALESCE(classificacao_n2, ''))) = 'VITAMINAS' THEN item_quantidade ELSE 0 END),0) AS quantidade_vitaminas,
                COUNT(DISTINCT venda_id) AS num_vendas_w
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{inicio_mes}' AND DATE '{data_ref}'
            {cond_filial}
            GROUP BY 1
        """
        df_mes_d = duck_query(sql_total_dia)
        if df_mes_d is None or df_mes_d.empty:
            total_por_dia = pd.Series([0.0]*7, index=list(range(7)))
        else:
            df_mes_d['itens_vitamina_por_nota'] = df_mes_d.apply(lambda r: (float(r['quantidade_vitaminas']) / int(r['num_vendas_w'])) if int(r['num_vendas_w']) > 0 else 0.0, axis=1)
            total_por_dia = df_mes_d.set_index('weekday')['itens_vitamina_por_nota'].reindex(range(7), fill_value=0.0)

        row_total = pd.DataFrame([total_por_dia.values], index=['Total Loja'], columns=range(7))
        final_mat = pd.concat([row_total, mat], axis=0).fillna(0.0)

        mat_norm = final_mat.copy()
        row_min = mat_norm.min(axis=1)
        row_max = mat_norm.max(axis=1)
        denom = (row_max - row_min).replace(0, 1)
        mat_norm = mat_norm.sub(row_min, axis=0).div(denom, axis=0)

        return final_mat, mat_norm, True

    horas_raw, horas_norm, tem_horas = preparar_heatmap_horas_vitaminas()
    dias_raw, dias_norm, tem_dias = preparar_heatmap_dias_vitaminas()

    # Pills / UI
    opcoes = ["🔢 Quantidade", "📅 Média/dia", "🕒 Horas", "🗓️ Dias"]
    state_key = f"pills_vitaminas_vendedores_{filial_selecionada or 'todas'}"
    if state_key not in st.session_state:
        st.session_state[state_key] = opcoes[0]
    escolha = st.pills("Escolha a visualização:", opcoes, key=state_key)

    if escolha == "🔢 Quantidade":
        df_plot = rank_qtd.head(top_n).sort_values('quantidade_vitaminas', ascending=False)
        fig = px.bar(df_plot, x='quantidade_vitaminas', y='vendedor_nome', orientation='h')
        fig.update_traces(marker_color='darkslateblue', textangle=0, textposition="inside",
                          textfont=dict(color='white', size=10), texttemplate='%{x:,.0f}')
        fig.update_layout(
            height=max(300, min(800, 28 * len(df_plot) + 120)),
            showlegend=False, template="plotly_white",
            margin=dict(t=20, b=20, l=30, r=30),
            xaxis=dict(title="Quantidade de Vitaminas (Itens)", tickfont=dict(size=10)),
            yaxis=dict(title="", tickfont=dict(size=10), autorange='reversed'),
            bargap=0.35
        )
        st.plotly_chart(fig, use_container_width=True)

    elif escolha == "📅 Média/dia":
        if media_dia.empty:
            st.info("Sem dados para exibir")
        else:
            fig = px.bar(media_dia, x='media_dia', y='vendedor_nome', orientation='h')
            fig.update_traces(marker_color='indianred', textangle=0, textposition="inside",
                              textfont=dict(color='white', size=10), texttemplate='%{x:,.1f}')
            fig.add_trace(go.Scatter(
                x=media_dia['media_90d'], y=media_dia['vendedor_nome'], mode='markers',
                marker=dict(symbol='line-ns', size=14, color='black', line=dict(width=2, color='orange')),
                name='Média 90d', showlegend=True,
                hovertemplate="Vendedor: %{y}<br>Média 90d: %{x:.1f} itens<extra></extra>"
            ))
            fig.update_layout(
                height=max(300, min(800, 28 * len(media_dia) + 120)),
                template="plotly_white", margin=dict(t=20, b=20, l=30, r=30),
                showlegend=True, legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
                xaxis=dict(title="Média por dia (Vitaminas)", tickfont=dict(size=10)),
                yaxis=dict(title="", tickfont=dict(size=10), autorange='reversed'),
                bargap=0.35
            )
            st.plotly_chart(fig, use_container_width=True)

    elif escolha == "🕒 Horas":
        if not tem_horas:
            st.info("Sem dados horários para exibir")
        else:
            altura = max(300, min(750, 22 * len(horas_norm.index) + 140))

            # preparar matrizes
            z_norm = horas_norm.values.astype(float)                # valores normalizados (0..1)
            raw_vals = np.array(horas_raw.values, dtype=float)     # valores brutos (itens por nota)
            # main heatmap: apenas células > 0 (zeros viram NaN para não serem coloridas pelo gradiente)
            z_main = np.where(raw_vals > 0, z_norm, np.nan)
            # máscara para zeros: 1 onde zero, NaN caso contrário (será desenhada em cinza)
            z_zero = np.where(raw_vals == 0, 1.0, np.nan)

            fig = go.Figure()
            # Heatmap principal (gradiente para valores > 0)
            fig.add_trace(go.Heatmap(
                z=z_main,
                x=list(range(7,23)),
                y=list(horas_norm.index),
                colorscale=[(0.0, "rgb(49,130,189)"), (1.0, "rgb(220,20,60)")],
                zmin=0, zmax=1,
                colorbar=dict(title="Baixo ↔ Alto"),
                hoverongaps=False,
                showscale=True
            ))
            # Overlay para zeros (cor cinza)
            fig.add_trace(go.Heatmap(
                z=z_zero,
                x=list(range(7,23)),
                y=list(horas_norm.index),
                colorscale=[[0, "lightgray"], [1, "gray"]],
                zmin=0, zmax=1,
                showscale=False,
                hoverongaps=False
            ))

            # customdata para hover (usar valores brutos)
            fig.data[0].customdata = raw_vals[..., np.newaxis]
            fig.data[0].hovertemplate = "Linha: %{y}<br>Hora: %{x}h<br>Itens/Nota: %{customdata[0]:.2f}<extra></extra>"
            fig.data[1].customdata = raw_vals[..., np.newaxis]
            fig.data[1].hovertemplate = "Linha: %{y}<br>Hora: %{x}h<br>Itens/Nota: %{customdata[0]:.2f}<extra></extra>"

            fig.update_layout(
                height=altura, template="plotly_white", margin=dict(t=20, b=20, l=30, r=30),
                xaxis_title="Hora do dia", yaxis=dict(
                title="",
                tickfont=dict(size=10),
                autorange='reversed',
                categoryorder='array',
                categoryarray=top_names
            ))
            # manter gaps visuais
            fig.update_traces(xgap=1, ygap=2)
            st.plotly_chart(fig, use_container_width=True)

    elif escolha == "🗓️ Dias":
        if not tem_dias:
            st.info("Sem dados por dia da semana")
        else:
            weekday_labels = ["Seg","Ter","Qua","Qui","Sex","Sáb","Dom"]
            altura = max(300, min(750, 22 * len(dias_norm.index) + 140))

            # preparar matrizes
            z_norm = dias_norm.values.astype(float)
            raw_vals = np.array(dias_raw.values, dtype=float)     # valores brutos (itens por nota)
            z_main = np.where(raw_vals > 0, z_norm, np.nan)
            z_zero = np.where(raw_vals == 0, 1.0, np.nan)

            fig = go.Figure()
            fig.add_trace(go.Heatmap(
                z=z_main,
                x=weekday_labels,
                y=list(dias_norm.index),
                colorscale=[(0.0, "rgb(49,130,189)"), (1.0, "rgb(220,20,60)")],
                zmin=0, zmax=1,
                colorbar=dict(title="Baixo ↔ Alto"),
                hoverongaps=False,
                showscale=True
            ))
            fig.add_trace(go.Heatmap(
                z=z_zero,
                x=weekday_labels,
                y=list(dias_norm.index),
                colorscale=[[0, "lightgray"], [1, "gray"]],
                zmin=0, zmax=1,
                showscale=False,
                hoverongaps=False
            ))

            fig.data[0].customdata = raw_vals[..., np.newaxis]
            fig.data[0].hovertemplate = "Linha: %{y}<br>Dia: %{x}<br>Itens/Nota: %{customdata[0]:.2f}<extra></extra>"
            fig.data[1].customdata = raw_vals[..., np.newaxis]
            fig.data[1].hovertemplate = "Linha: %{y}<br>Dia: %{x}<br>Itens/Nota: %{customdata[0]:.2f}<extra></extra>"

            fig.update_layout(
                height=altura, template="plotly_white", margin=dict(t=20, b=20, l=30, r=30),
                xaxis_title="Dia da semana", yaxis=dict(
                title="",
                tickfont=dict(size=10),
                autorange='reversed',
                categoryorder='array',
                categoryarray=top_names
            ))
            fig.update_xaxes(side="top")
            fig.update_traces(xgap=1, ygap=2)
            st.plotly_chart(fig, use_container_width=True)

    # Retornar DataFrame com quantidade de vitaminas por vendedor (compatível com usos programáticos)
    return rank_qtd[['vendedor_nome', 'quantidade_vitaminas']].reset_index(drop=True)

def criar_conteudo_popover_taxa_conversao_vendedores_duck(filial_selecionada: str | None = None, vendedores: list[str] | None = None, top_n: int = 10, data_ref: date | None = None) -> pd.DataFrame:
    """
    Popover: Taxa de Conversão (num_vendas / vendas_com_vitaminas) por vendedor.
    Estrutura idêntica ao popover de vitaminas, mas calcula e exibe taxa_conversao (float, 1 casa decimal).
    Retorna DataFrame com ['vendedor_nome','taxa_conversao'].
    """
    # Datas
    if data_ref is None:
        data_ref = date.today() - timedelta(days=1)
    inicio_mes = data_ref.replace(day=1)
    jan_90 = data_ref - timedelta(days=89)
    dias_corridos = (data_ref - inicio_mes).days + 1

    # UI - âncora e título
    st.markdown("""
    <div style="width:650px; min-width:650px; height:1px; background:transparent; margin:0; padding:0; overflow:hidden;"></div>
    """, unsafe_allow_html=True)
    st.markdown(f"### 🔁 Taxa de Conversão - Filial {filial_selecionada or 'Todas'}")

    cond_filial = _cond_filial(filial_selecionada)
    
    # primeiro obter os top_n vendedores por quantidade de vitaminas (evita escolher vendedores com zero de vitaminas)
    sql_top_vit = f"""
        SELECT
            TRIM(vendedor_nome) AS vendedor_nome,
            COALESCE(SUM(CASE WHEN UPPER(TRIM(COALESCE(classificacao_n2, ''))) = 'VITAMINAS' THEN item_quantidade ELSE 0 END),0) AS quantidade_vitaminas
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{inicio_mes}' AND DATE '{data_ref}'
        {cond_filial}
          AND vendedor_nome IS NOT NULL
          AND TRIM(vendedor_nome) != ''
          AND TRIM(vendedor_nome) != 'Sem Vendedor'
        GROUP BY 1
        ORDER BY 2 DESC
        LIMIT {top_n}
    """
    df_top_vit = duck_query(sql_top_vit)
    if df_top_vit is None or df_top_vit.empty:
        st.info("Sem vendedores com vitaminas para exibir")
        return pd.DataFrame(columns=['vendedor_nome', 'taxa_conversao'])
    top_names = df_top_vit['vendedor_nome'].tolist()
    top_list_sql = "', '".join(_escape(n) for n in top_names)

    # agora calcular taxa de conversão apenas para esses top_names (número de vendas / número de vendas que tiveram pelo menos 1 vitamina)
    sql_rank = f"""
        WITH vendas_totais AS (
            SELECT TRIM(vendedor_nome) AS vendedor_nome,
                   COUNT(DISTINCT venda_id) AS total_vendas
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{inicio_mes}' AND DATE '{data_ref}'
            {cond_filial}
              AND TRIM(vendedor_nome) IN ('{top_list_sql}')
            GROUP BY 1
        ),
        vendas_com_vitaminas AS (
            SELECT TRIM(vendedor_nome) AS vendedor_nome,
                   COUNT(DISTINCT venda_id) AS vendas_com_vitaminas
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{inicio_mes}' AND DATE '{data_ref}'
            {cond_filial}
              AND UPPER(TRIM(COALESCE(classificacao_n2, ''))) = 'VITAMINAS'
              AND TRIM(vendedor_nome) IN ('{top_list_sql}')
            GROUP BY 1
        )
        SELECT
            t.vendedor_nome,
            t.total_vendas,
            COALESCE(v.vendas_com_vitaminas, 0) AS vendas_com_vitaminas,
            CASE WHEN COALESCE(v.vendas_com_vitaminas, 0) > 0
                 THEN CAST(t.total_vendas AS FLOAT) / COALESCE(v.vendas_com_vitaminas, 0)
                 ELSE 0 END AS taxa_conversao
        FROM vendas_totais t
        LEFT JOIN vendas_com_vitaminas v USING (vendedor_nome)
        ORDER BY taxa_conversao ASC
    """
    rank_taxa = duck_query(sql_rank)

    if rank_taxa is None or rank_taxa.empty:
        st.info("Sem vendedores para exibir")
        return pd.DataFrame(columns=['vendedor_nome', 'taxa_conversao'])

    # manter top_names
    top_names = rank_taxa['vendedor_nome'].tolist()

    # Dados 90 dias (para média 90d da taxa) - calcular taxa usando mesma lógica por vendedor no período de 90d
    sql_90 = f"""
        SELECT
            TRIM(vendedor_nome) AS vendedor_nome,
            COUNT(DISTINCT venda_id) AS total_vendas_90,
            COUNT(DISTINCT CASE WHEN UPPER(TRIM(COALESCE(classificacao_n2, ''))) = 'VITAMINAS' THEN venda_id END) AS vendas_com_vitaminas_90,
            CASE WHEN COUNT(DISTINCT CASE WHEN UPPER(TRIM(COALESCE(classificacao_n2, ''))) = 'VITAMINAS' THEN venda_id END) > 0
                 THEN CAST(COUNT(DISTINCT venda_id) AS FLOAT) / COUNT(DISTINCT CASE WHEN UPPER(TRIM(COALESCE(classificacao_n2, ''))) = 'VITAMINAS' THEN venda_id END)
                 ELSE 0 END AS taxa_conversao_90
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{jan_90}' AND DATE '{data_ref}'
        {cond_filial}
          AND vendedor_nome IS NOT NULL
          AND TRIM(vendedor_nome) != ''
          AND TRIM(vendedor_nome) != 'Sem Vendedor'
        GROUP BY 1
    """
    df_90 = duck_query(sql_90)
    if df_90 is None:
        df_90 = pd.DataFrame(columns=['vendedor_nome','total_vendas_90','vendas_com_vitaminas_90','taxa_conversao_90'])
    else:
        df_90 = df_90[df_90['vendedor_nome'].isin(top_names)].copy()

    # Média por dia (para esse indicador vamos mostrar a taxa do mês como 'media_dia' para consistência de UI)
    media_dia = rank_taxa[['vendedor_nome','taxa_conversao']].copy()
    # manter media_90d a partir de df_90 taxa_conversao_90 / 90? aqui taxa já é razão; manter como taxa média 90d (não dividir por dias)
    if not df_90.empty and 'taxa_conversao_90' in df_90.columns:
        rank90 = df_90.set_index('vendedor_nome')['taxa_conversao_90'].to_dict()
        media_dia['media_90d'] = media_dia['vendedor_nome'].map(lambda n: round(rank90.get(n, 0.0), 1))
    else:
        media_dia['media_90d'] = 0.0

    media_dia = media_dia[media_dia['vendedor_nome'].isin(top_names)].copy()
    media_dia = media_dia.sort_values('taxa_conversao', ascending=True)

    # Heatmap horas (taxa por hora) — garante linhas para todos os top_names
    def preparar_heatmap_horas_taxa():
        sql_horas = f"""
            SELECT
                TRIM(vendedor_nome) AS vendedor_nome,
                EXTRACT(hour FROM datahora) AS hora,
                COUNT(DISTINCT venda_id) AS total_vendas_h,
                COUNT(DISTINCT CASE WHEN UPPER(TRIM(COALESCE(classificacao_n2, ''))) = 'VITAMINAS' THEN venda_id END) AS vendas_com_vitaminas_h
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{inicio_mes}' AND DATE '{data_ref}'
            {cond_filial}
              AND vendedor_nome IS NOT NULL
              AND TRIM(vendedor_nome) != ''
              AND TRIM(vendedor_nome) != 'Sem Vendedor'
              AND EXTRACT(hour FROM datahora) BETWEEN 7 AND 22
            GROUP BY 1,2
        """
        df_h = duck_query(sql_horas)
        if df_h is None or df_h.empty:
            return None, None, False

        df_h['taxa_conversao'] = df_h.apply(lambda r: (float(r['total_vendas_h']) / int(r['vendas_com_vitaminas_h'])) if int(r['vendas_com_vitaminas_h']) > 0 else 0.0, axis=1)
        mat = df_h.pivot_table(index='vendedor_nome', columns='hora', values='taxa_conversao', fill_value=0.0)
        for h in range(7,23):
            if h not in mat.columns:
                mat[h] = 0.0
        mat = mat[list(range(7,23))]
        mat = mat.reindex(index=top_names).fillna(0.0)

        # Total loja por hora
        sql_total_hora = f"""
            SELECT
                EXTRACT(hour FROM datahora) AS hora,
                COUNT(DISTINCT venda_id) AS total_vendas_h,
                COUNT(DISTINCT CASE WHEN UPPER(TRIM(COALESCE(classificacao_n2, ''))) = 'VITAMINAS' THEN venda_id END) AS vendas_com_vitaminas_h
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{inicio_mes}' AND DATE '{data_ref}'
            {cond_filial}
              AND EXTRACT(hour FROM datahora) BETWEEN 7 AND 22
            GROUP BY 1
        """
        df_mes_h = duck_query(sql_total_hora)
        if df_mes_h is None or df_mes_h.empty:
            total_por_hora = pd.Series([0.0]*len(range(7,23)), index=list(range(7,23)))
        else:
            df_mes_h['taxa_conversao'] = df_mes_h.apply(lambda r: (float(r['total_vendas_h']) / int(r['vendas_com_vitaminas_h'])) if int(r['vendas_com_vitaminas_h']) > 0 else 0.0, axis=1)
            total_por_hora = df_mes_h.set_index('hora')['taxa_conversao'].reindex(range(7,23), fill_value=0.0)

        row_total = pd.DataFrame([total_por_hora.values], index=['Total Loja'], columns=range(7,23))
        final_mat = pd.concat([row_total, mat], axis=0).fillna(0.0)

        # Normalização
        mat_norm = final_mat.copy()
        row_min = mat_norm.min(axis=1)
        row_max = mat_norm.max(axis=1)
        denom = (row_max - row_min).replace(0, 1)
        mat_norm = mat_norm.sub(row_min, axis=0).div(denom, axis=0)

        return final_mat, mat_norm, True

    # Heatmap dias (taxa por weekday)
    def preparar_heatmap_dias_taxa():
        sql_dias = f"""
            SELECT
                TRIM(vendedor_nome) AS vendedor_nome,
                EXTRACT(dow FROM data_date) AS weekday,
                COUNT(DISTINCT venda_id) AS total_vendas_w,
                COUNT(DISTINCT CASE WHEN UPPER(TRIM(COALESCE(classificacao_n2, ''))) = 'VITAMINAS' THEN venda_id END) AS vendas_com_vitaminas_w
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{inicio_mes}' AND DATE '{data_ref}'
            {cond_filial}
              AND vendedor_nome IS NOT NULL
              AND TRIM(vendedor_nome) != ''
              AND TRIM(vendedor_nome) != 'Sem Vendedor'
            GROUP BY 1,2
        """
        df_d = duck_query(sql_dias)
        if df_d is None or df_d.empty:
            return None, None, False

        df_d['taxa_conversao'] = df_d.apply(lambda r: (float(r['total_vendas_w']) / int(r['vendas_com_vitaminas_w'])) if int(r['vendas_com_vitaminas_w']) > 0 else 0.0, axis=1)
        mat = df_d.pivot_table(index='vendedor_nome', columns='weekday', values='taxa_conversao', fill_value=0.0)
        for w in range(7):
            if w not in mat.columns:
                mat[w] = 0.0
        mat = mat[list(range(7))]
        mat = mat.reindex(index=top_names).fillna(0.0)

        sql_total_dia = f"""
            SELECT
                EXTRACT(dow FROM data_date) AS weekday,
                COUNT(DISTINCT venda_id) AS total_vendas_w,
                COUNT(DISTINCT CASE WHEN UPPER(TRIM(COALESCE(classificacao_n2, ''))) = 'VITAMINAS' THEN venda_id END) AS vendas_com_vitaminas_w
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{inicio_mes}' AND DATE '{data_ref}'
            {cond_filial}
            GROUP BY 1
        """
        df_mes_d = duck_query(sql_total_dia)
        if df_mes_d is None or df_mes_d.empty:
            total_por_dia = pd.Series([0.0]*7, index=list(range(7)))
        else:
            df_mes_d['taxa_conversao'] = df_mes_d.apply(lambda r: (float(r['total_vendas_w']) / int(r['vendas_com_vitaminas_w'])) if int(r['vendas_com_vitaminas_w']) > 0 else 0.0, axis=1)
            total_por_dia = df_mes_d.set_index('weekday')['taxa_conversao'].reindex(range(7), fill_value=0.0)

        row_total = pd.DataFrame([total_por_dia.values], index=['Total Loja'], columns=range(7))
        final_mat = pd.concat([row_total, mat], axis=0).fillna(0.0)

        mat_norm = final_mat.copy()
        row_min = mat_norm.min(axis=1)
        row_max = mat_norm.max(axis=1)
        denom = (row_max - row_min).replace(0, 1)
        mat_norm = mat_norm.sub(row_min, axis=0).div(denom, axis=0)

        return final_mat, mat_norm, True

    horas_raw, horas_norm, tem_horas = preparar_heatmap_horas_taxa()
    dias_raw, dias_norm, tem_dias = preparar_heatmap_dias_taxa()

    # Pills / UI
    opcoes = ["🔢 Mês Atual", "🕒 Horas", "🗓️ Dias"]
    state_key = f"pills_taxa_conversao_vendedores_{filial_selecionada or 'todas'}"
    if state_key not in st.session_state:
        st.session_state[state_key] = opcoes[0]
    escolha = st.pills("Escolha a visualização:", opcoes, key=state_key)

    if escolha == "🔢 Mês Atual":
        df_plot = rank_taxa.head(top_n).sort_values('taxa_conversao', ascending=True)
        fig = px.bar(df_plot, x='taxa_conversao', y='vendedor_nome', orientation='h', text_auto='.1f')
        fig.update_traces(marker_color='darkslateblue', textangle=0, textposition="inside", textfont=dict(color='white', size=10))
        if not df_90.empty and 'taxa_conversao_90' in df_90.columns:
            fig.add_trace(go.Scatter(
                x=df_90['taxa_conversao_90'], y=df_90['vendedor_nome'], mode='markers',
                marker=dict(symbol='line-ns', size=12, color='black', line=dict(width=2, color='orange')),
                name='Média 90d', showlegend=True, hovertemplate="Vendedor: %{y}<br>Média 90d: %{x:.1f}<extra></extra>"
            ))
        fig.update_layout(
            height=max(300, min(800, 28 * len(df_plot) + 120)),
            showlegend=False, template="plotly_white",
            margin=dict(t=20, b=20, l=30, r=30),
            xaxis=dict(title="Taxa de Conversão (float)", tickfont=dict(size=10)),
            yaxis=dict(title="", tickfont=dict(size=10), autorange='reversed'),
            bargap=0.35
        )
        st.plotly_chart(fig, use_container_width=True)
        
    elif escolha == "🕒 Horas":
        if not tem_horas:
            st.info("Sem dados horários para exibir")
        else:
            altura = max(300, min(750, 22 * len(horas_norm.index) + 140))

            # preparar matrizes
            z_norm = horas_norm.values.astype(float)                # valores normalizados (0..1)
            raw_vals = np.array(horas_raw.values, dtype=float)     # valores brutos (taxa)
            # main heatmap: apenas células > 0 (zeros viram NaN para não serem coloridas pelo gradiente)
            z_main = np.where(raw_vals > 0, z_norm, np.nan)
            # máscara para zeros: 1 onde zero, NaN caso contrário (será desenhada em cinza)
            z_zero = np.where(raw_vals == 0, 1.0, np.nan)

            fig = go.Figure()
            # Heatmap principal (gradiente para valores > 0)
            fig.add_trace(go.Heatmap(
                z=z_main,
                x=list(range(7,23)),
                y=list(horas_norm.index),
                colorscale=[(0.0, "rgb(49,130,189)"), (1.0, "rgb(220,20,60)")],
                zmin=0, zmax=1,
                colorbar=dict(title="Baixo ↔ Alto"),
                hoverongaps=False,
                showscale=True
            ))
            # Overlay para zeros (cor cinza)
            fig.add_trace(go.Heatmap(
                z=z_zero,
                x=list(range(7,23)),
                y=list(horas_norm.index),
                colorscale=[[0, "lightgray"], [1, "gray"]],
                zmin=0, zmax=1,
                showscale=False,
                hoverongaps=False
            ))


            # customdata para hover (usar valores brutos)
            fig.data[0].customdata = raw_vals[..., np.newaxis]
            fig.data[0].hovertemplate = "Linha: %{y}<br>Hora: %{x}h<br>Taxa: %{customdata:.1f}<extra></extra>"
            fig.data[1].customdata = raw_vals[..., np.newaxis]
            fig.data[1].hovertemplate = "Linha: %{y}<br>Hora: %{x}h<br>Taxa: %{customdata:.1f}<extra></extra>"

            fig.update_layout(
                height=altura, template="plotly_white", margin=dict(t=20, b=20, l=30, r=30),
                xaxis_title="Hora do dia", yaxis=dict(
                title="",
                tickfont=dict(size=10),
                autorange='reversed',
                categoryorder='array',
                categoryarray=top_names
            ))
            # manter gaps visuais
            fig.update_traces(xgap=1, ygap=2)
            st.plotly_chart(fig, use_container_width=True)

    elif escolha == "🗓️ Dias":
        if not tem_dias:
            st.info("Sem dados por dia da semana")
        else:
            weekday_labels = ["Seg","Ter","Qua","Qui","Sex","Sáb","Dom"]
            altura = max(300, min(750, 22 * len(dias_norm.index) + 140))

            # preparar matrizes
            z_norm = dias_norm.values.astype(float)
            raw_vals = np.array(dias_raw.values, dtype=float)
            z_main = np.where(raw_vals > 0, z_norm, np.nan)
            z_zero = np.where(raw_vals == 0, 1.0, np.nan)

            fig = go.Figure()
            fig.add_trace(go.Heatmap(
                z=z_main,
                x=weekday_labels,
                y=list(dias_norm.index),
                colorscale=[(0.0, "rgb(49,130,189)"), (1.0, "rgb(220,20,60)")],
                zmin=0, zmax=1,
                colorbar=dict(title="Baixo ↔ Alto"),
                hoverongaps=False,
                showscale=True
            ))
            fig.add_trace(go.Heatmap(
                z=z_zero,
                x=weekday_labels,
                y=list(dias_norm.index),
                colorscale=[[0, "lightgray"], [1, "gray"]],
                zmin=0, zmax=1,
                showscale=False,
                hoverongaps=False
            ))

            fig.data[0].customdata = raw_vals[..., np.newaxis]
            fig.data[0].hovertemplate = "Linha: %{y}<br>Dia: %{x}<br>Taxa: %{customdata:.1f}<extra></extra>"
            fig.data[1].customdata = raw_vals[..., np.newaxis]
            fig.data[1].hovertemplate = "Linha: %{y}<br>Dia: %{x}<br>Taxa: %{customdata:.1f}<extra></extra>"

            fig.update_layout(
                height=altura, template="plotly_white", margin=dict(t=20, b=20, l=30, r=30),
                xaxis_title="Dia da semana", yaxis=dict(
                    title="",
                    tickfont=dict(size=10),
                    autorange='reversed',
                    categoryorder='array',
                    categoryarray=top_names
                )
            )
            fig.update_xaxes(side="top")
            fig.update_traces(xgap=1, ygap=2)
            st.plotly_chart(fig, use_container_width=True)

    # Retornar DataFrame com taxa de conversão por vendedor (1 casa decimal para display, manter float)
    out = rank_taxa[['vendedor_nome','taxa_conversao']].copy()
    out['taxa_conversao'] = out['taxa_conversao'].astype(float).round(1)
    return out.reset_index(drop=True)

def criar_conteudo_popover_vendas_identificadas_vendedores_duck(filial_codigo: str | None = None, vendedores: list[str] | None = None, top_n: int = 10, data_ref: date | None = None) -> pd.DataFrame:
    """
    Popover: Vendas identificadas (%) por vendedor.
    Pills: ["🔢 Mês Atual", "🕒 Horas", "🗓️ Dias"]
    Seleciona top_n vendedores por valor total vendido e mostra percentual de vendas identificadas.
    Retorna DataFrame com ['vendedor_nome','vendas_identificadas_perc'].
    """
    # Datas
    if data_ref is None:
        data_ref = date.today() - timedelta(days=1)
    inicio_mes = data_ref.replace(day=1)
    jan_90 = data_ref - timedelta(days=89)

    # UI anchor + title
    st.markdown("""
    <div style="width:650px; min-width:650px; height:1px; background:transparent; margin:0; padding:0; overflow:hidden;"></div>
    """, unsafe_allow_html=True)
    st.markdown(f"### 🧾 Vendas Identificadas - Filial {filial_codigo or 'Todas'}")

    cond_filial = _cond_filial(filial_codigo)

    # 1) top_n por valor vendido (evita escolher vendedores sem relevância)
    sql_top_valor = f"""
        SELECT
            TRIM(vendedor_nome) AS vendedor_nome,
            SUM(item_valortotal) AS total_venda
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{inicio_mes}' AND DATE '{data_ref}'
        {cond_filial}
          AND vendedor_nome IS NOT NULL
          AND TRIM(vendedor_nome) != ''
          AND TRIM(vendedor_nome) != 'Sem Vendedor'
        GROUP BY 1
        ORDER BY 2 DESC
        LIMIT {top_n}
    """
    df_top = duck_query(sql_top_valor)
    if df_top is None or df_top.empty:
        st.info("Sem vendedores para exibir")
        return pd.DataFrame(columns=['vendedor_nome', 'vendas_identificadas_perc'])
    top_names = df_top['vendedor_nome'].tolist()
    top_list_sql = "', '".join(_escape(n) for n in top_names)

    # 2) calcular total vendas e vendas identificadas para esses top_names (mês atual)
    sql_rank = f"""
        WITH vendas_totais AS (
            SELECT TRIM(vendedor_nome) AS vendedor_nome,
                   COUNT(DISTINCT venda_id) AS total_vendas
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{inicio_mes}' AND DATE '{data_ref}'
            {cond_filial}
              AND TRIM(vendedor_nome) IN ('{top_list_sql}')
            GROUP BY 1
        ),
        vendas_identificadas AS (
            SELECT TRIM(vendedor_nome) AS vendedor_nome,
                   COUNT(DISTINCT CASE WHEN venda_pessoaid IS NOT NULL THEN venda_id END) AS vendas_identificadas_count
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{inicio_mes}' AND DATE '{data_ref}'
            {cond_filial}
              AND TRIM(vendedor_nome) IN ('{top_list_sql}')
            GROUP BY 1
        )
        SELECT
            t.vendedor_nome,
            t.total_vendas,
            COALESCE(v.vendas_identificadas_count, 0) AS vendas_identificadas_count,
            CASE WHEN t.total_vendas > 0 THEN (COALESCE(v.vendas_identificadas_count,0) * 100.0) / t.total_vendas ELSE 0 END AS vendas_identificadas_perc
        FROM vendas_totais t
        LEFT JOIN vendas_identificadas v USING (vendedor_nome)
        
    """
    df_rank = duck_query(sql_rank)
    if df_rank is None or df_rank.empty:
        st.info("Sem vendedores para exibir")
        return pd.DataFrame(columns=['vendedor_nome', 'vendas_identificadas_perc'])

    # Garantir que a ordem dos vendedores no df_rank siga a ordem de top_names (melhor -> pior por valor vendido).
    # Reindexa usando top_names (vendedores vindos da query 1) e preenche com zeros caso algum vendedor não tenha linhas.
    df_rank = df_rank.set_index('vendedor_nome').reindex(top_names).fillna({
        'total_vendas': 0,
        'vendas_identificadas_count': 0,
        'vendas_identificadas_perc': 0.0
    }).reset_index()


    # 3) dados 90 dias (opcional - para marcador média 90d)
    sql_90 = f"""
        SELECT
            TRIM(vendedor_nome) AS vendedor_nome,
            COUNT(DISTINCT venda_id) AS total_vendas_90,
            COUNT(DISTINCT CASE WHEN venda_pessoaid IS NOT NULL THEN venda_id END) AS vendas_identificadas_90,
            CASE WHEN COUNT(DISTINCT venda_id) > 0 THEN (COUNT(DISTINCT CASE WHEN venda_pessoaid IS NOT NULL THEN venda_id END) * 100.0) / COUNT(DISTINCT venda_id) ELSE 0 END AS vendas_identificadas_perc_90
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{jan_90}' AND DATE '{data_ref}'
        {cond_filial}
          AND vendedor_nome IS NOT NULL
          AND TRIM(vendedor_nome) != ''
          AND TRIM(vendedor_nome) != 'Sem Vendedor'
        GROUP BY 1
    """
    df_90 = duck_query(sql_90)
    if df_90 is None:
        df_90 = pd.DataFrame(columns=['vendedor_nome','total_vendas_90','vendas_identificadas_90','vendas_identificadas_perc_90'])
    else:
        df_90 = df_90[df_90['vendedor_nome'].isin(top_names)].copy()

    # 4) preparar media_dia (para UI compatível)
    media_dia = df_rank[['vendedor_nome','vendas_identificadas_perc']].copy()
    if not df_90.empty and 'vendas_identificadas_perc_90' in df_90.columns:
        rank90 = df_90.set_index('vendedor_nome')['vendas_identificadas_perc_90'].to_dict()
        media_dia['media_90d'] = media_dia['vendedor_nome'].map(lambda n: round(rank90.get(n, 0.0), 1))
    else:
        media_dia['media_90d'] = 0.0
    media_dia = media_dia[media_dia['vendedor_nome'].isin(top_names)].copy()
    media_dia = media_dia.sort_values('vendas_identificadas_perc', ascending=False)

    # 5) heatmaps — horas
    def preparar_heatmap_horas_identificadas():
        sql_horas = f"""
            SELECT
                TRIM(vendedor_nome) AS vendedor_nome,
                EXTRACT(hour FROM datahora) AS hora,
                COUNT(DISTINCT venda_id) AS total_vendas_h,
                COUNT(DISTINCT CASE WHEN venda_pessoaid IS NOT NULL THEN venda_id END) AS vendas_identificadas_h
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{inicio_mes}' AND DATE '{data_ref}'
            {cond_filial}
              AND TRIM(vendedor_nome) IN ('{top_list_sql}')
              AND EXTRACT(hour FROM datahora) BETWEEN 7 AND 22
            GROUP BY 1,2
        """
        df_h = duck_query(sql_horas)
        if df_h is None or df_h.empty:
            return None, None, False

        df_h['vendas_identificadas_perc'] = df_h.apply(lambda r: (float(r['vendas_identificadas_h']) * 100.0 / int(r['total_vendas_h'])) if int(r['total_vendas_h']) > 0 else 0.0, axis=1)
        mat = df_h.pivot_table(index='vendedor_nome', columns='hora', values='vendas_identificadas_perc', fill_value=0.0)
        for h in range(7,23):
            if h not in mat.columns:
                mat[h] = 0.0
        mat = mat[list(range(7,23))]
        mat = mat.reindex(index=top_names).fillna(0.0)

        # total loja por hora (percentual identificado)
        sql_total_hora = f"""
            SELECT
                EXTRACT(hour FROM datahora) AS hora,
                COUNT(DISTINCT venda_id) AS total_vendas_h,
                COUNT(DISTINCT CASE WHEN venda_pessoaid IS NOT NULL THEN venda_id END) AS vendas_identificadas_h
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{inicio_mes}' AND DATE '{data_ref}'
            {cond_filial}
              AND EXTRACT(hour FROM datahora) BETWEEN 7 AND 22
            GROUP BY 1
        """
        df_mes_h = duck_query(sql_total_hora)
        if df_mes_h is None or df_mes_h.empty:
            total_por_hora = pd.Series([0.0]*len(range(7,23)), index=list(range(7,23)))
        else:
            df_mes_h['vendas_identificadas_perc'] = df_mes_h.apply(lambda r: (float(r['vendas_identificadas_h']) * 100.0 / int(r['total_vendas_h'])) if int(r['total_vendas_h']) > 0 else 0.0, axis=1)
            total_por_hora = df_mes_h.set_index('hora')['vendas_identificadas_perc'].reindex(range(7,23), fill_value=0.0)

        row_total = pd.DataFrame([total_por_hora.values], index=['Total Loja'], columns=range(7,23))
        final_mat = pd.concat([row_total, mat], axis=0).fillna(0.0)

        # normalização (linha a linha)
        mat_norm = final_mat.copy()
        row_min = mat_norm.min(axis=1)
        row_max = mat_norm.max(axis=1)
        denom = (row_max - row_min).replace(0, 1)
        mat_norm = mat_norm.sub(row_min, axis=0).div(denom, axis=0)

        return final_mat, mat_norm, True

    # 6) heatmaps — dias
    def preparar_heatmap_dias_identificadas():
        sql_dias = f"""
            SELECT
                TRIM(vendedor_nome) AS vendedor_nome,
                EXTRACT(dow FROM data_date) AS weekday,
                COUNT(DISTINCT venda_id) AS total_vendas_w,
                COUNT(DISTINCT CASE WHEN venda_pessoaid IS NOT NULL THEN venda_id END) AS vendas_identificadas_w
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{inicio_mes}' AND DATE '{data_ref}'
            {cond_filial}
              AND TRIM(vendedor_nome) IN ('{top_list_sql}')
            GROUP BY 1,2
        """
        df_d = duck_query(sql_dias)
        if df_d is None or df_d.empty:
            return None, None, False

        df_d['vendas_identificadas_perc'] = df_d.apply(lambda r: (float(r['vendas_identificadas_w']) * 100.0 / int(r['total_vendas_w'])) if int(r['total_vendas_w']) > 0 else 0.0, axis=1)
        mat = df_d.pivot_table(index='vendedor_nome', columns='weekday', values='vendas_identificadas_perc', fill_value=0.0)
        for w in range(7):
            if w not in mat.columns:
                mat[w] = 0.0
        mat = mat[list(range(7))]
        mat = mat.reindex(index=top_names).fillna(0.0)

        sql_total_dia = f"""
            SELECT
                EXTRACT(dow FROM data_date) AS weekday,
                COUNT(DISTINCT venda_id) AS total_vendas_w,
                COUNT(DISTINCT CASE WHEN venda_pessoaid IS NOT NULL THEN venda_id END) AS vendas_identificadas_w
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{inicio_mes}' AND DATE '{data_ref}'
            {cond_filial}
            GROUP BY 1
        """
        df_mes_d = duck_query(sql_total_dia)
        if df_mes_d is None or df_mes_d.empty:
            total_por_dia = pd.Series([0.0]*7, index=list(range(7)))
        else:
            df_mes_d['vendas_identificadas_perc'] = df_mes_d.apply(lambda r: (float(r['vendas_identificadas_w']) * 100.0 / int(r['total_vendas_w'])) if int(r['total_vendas_w']) > 0 else 0.0, axis=1)
            total_por_dia = df_mes_d.set_index('weekday')['vendas_identificadas_perc'].reindex(range(7), fill_value=0.0)

        row_total = pd.DataFrame([total_por_dia.values], index=['Total Loja'], columns=range(7))
        final_mat = pd.concat([row_total, mat], axis=0).fillna(0.0)

        mat_norm = final_mat.copy()
        row_min = mat_norm.min(axis=1)
        row_max = mat_norm.max(axis=1)
        denom = (row_max - row_min).replace(0, 1)
        mat_norm = mat_norm.sub(row_min, axis=0).div(denom, axis=0)

        return final_mat, mat_norm, True

    horas_raw, horas_norm, tem_horas = preparar_heatmap_horas_identificadas()
    dias_raw, dias_norm, tem_dias = preparar_heatmap_dias_identificadas()

    # UI pills
    opcoes = ["🔢 Mês Atual", "🕒 Horas", "🗓️ Dias"]
    state_key = f"pills_vendas_identificadas_vendedores_{filial_codigo or 'todas'}"
    if state_key not in st.session_state:
        st.session_state[state_key] = opcoes[0]
    escolha = st.pills("Escolha a visualização:", opcoes, key=state_key)

    if escolha == "🔢 Mês Atual":
        df_plot = df_rank.head(top_n)#.sort_values('vendas_identificadas_perc', ascending=False)
        fig = px.bar(df_plot, x='vendas_identificadas_perc', y='vendedor_nome', orientation='h',
                     text_auto='.1f', category_orders={'vendedor_nome': top_names})
        fig.update_traces(marker_color='darkslateblue', textangle=0, textposition="inside", textfont=dict(color='white', size=10))
        if not df_90.empty and 'vendas_identificadas_perc_90' in df_90.columns:
            fig.add_trace(go.Scatter(
                x=df_90['vendas_identificadas_perc_90'], y=df_90['vendedor_nome'], mode='markers',
                marker=dict(symbol='line-ns', size=12, color='black', line=dict(width=2, color='orange')),
                name='Média 90d', showlegend=True, hovertemplate="Vendedor: %{y}<br>Média 90d: %{x:.1f}%<extra></extra>"
            ))
        fig.update_layout(
            height=max(300, min(800, 28 * len(df_plot) + 120)),
            showlegend=False, template="plotly_white",
            margin=dict(t=20, b=20, l=30, r=30),
            xaxis=dict(title="Vendas Identificadas (%)", tickfont=dict(size=10)),
            yaxis=dict(
                title="",
                tickfont=dict(size=10),
                autorange='reversed',
                categoryorder='array',
                categoryarray=top_names
            ),
            bargap=0.35
        )
        st.plotly_chart(fig, use_container_width=True)

    elif escolha == "🕒 Horas":
        if not tem_horas:
            st.info("Sem dados horários para exibir")
        else:
            altura = max(300, min(750, 22 * len(horas_norm.index) + 140))
            z_norm = horas_norm.values.astype(float)
            raw_vals = np.array(horas_raw.values, dtype=float)
            z_main = np.where(raw_vals > 0, z_norm, np.nan)
            z_zero = np.where(raw_vals == 0, 1.0, np.nan)

            fig = go.Figure()
            fig.add_trace(go.Heatmap(
                z=z_main, x=list(range(7,23)), y=list(horas_norm.index),
                colorscale=[(0.0, "rgb(49,130,189)"), (1.0, "rgb(220,20,60)")],
                zmin=0, zmax=1, colorbar=dict(title="Baixo ↔ Alto"), hoverongaps=False, showscale=True
            ))
            fig.add_trace(go.Heatmap(
                z=z_zero, x=list(range(7,23)), y=list(horas_norm.index),
                colorscale=[[0, "lightgray"], [1, "gray"]], zmin=0, zmax=1, showscale=False, hoverongaps=False
            ))
            fig.data[0].customdata = raw_vals[..., np.newaxis]
            fig.data[0].hovertemplate = "Linha: %{y}<br>Hora: %{x}h<br>Vendas Identificadas: %{customdata[0]:.1f}%<extra></extra>"
            fig.data[1].customdata = raw_vals[..., np.newaxis]
            fig.data[1].hovertemplate = "Linha: %{y}<br>Hora: %{x}h<br>Vendas Identificadas: %{customdata[0]:.1f}%<extra></extra>"

            fig.update_layout(height=altura, template="plotly_white", margin=dict(t=20,b=20,l=30,r=30),
                              xaxis_title="Hora do dia", yaxis=dict(
                title="",
                tickfont=dict(size=10),
                autorange='reversed',
                categoryorder='array',
                categoryarray=top_names
            ))
            fig.update_traces(xgap=1, ygap=2)
            st.plotly_chart(fig, use_container_width=True)

    elif escolha == "🗓️ Dias":
        if not tem_dias:
            st.info("Sem dados por dia da semana")
        else:
            weekday_labels = ["Seg","Ter","Qua","Qui","Sex","Sáb","Dom"]
            altura = max(300, min(750, 22 * len(dias_norm.index) + 140))
            z_norm = dias_norm.values.astype(float)
            raw_vals = np.array(dias_raw.values, dtype=float)
            z_main = np.where(raw_vals > 0, z_norm, np.nan)
            z_zero = np.where(raw_vals == 0, 1.0, np.nan)

            fig = go.Figure()
            fig.add_trace(go.Heatmap(
                z=z_main, x=weekday_labels, y=list(dias_norm.index),
                colorscale=[(0.0, "rgb(49,130,189)"), (1.0, "rgb(220,20,60)")],
                zmin=0, zmax=1, colorbar=dict(title="Baixo ↔ Alto"), hoverongaps=False, showscale=True
            ))
            fig.add_trace(go.Heatmap(
                z=z_zero, x=weekday_labels, y=list(dias_norm.index),
                colorscale=[[0, "lightgray"], [1, "gray"]], zmin=0, zmax=1, showscale=False, hoverongaps=False
            ))
            fig.data[0].customdata = raw_vals[..., np.newaxis]
            fig.data[0].hovertemplate = "Linha: %{y}<br>Dia: %{x}<br>Vendas Identificadas: %{customdata[0]:.1f}%<extra></extra>"
            fig.data[1].customdata = raw_vals[..., np.newaxis]
            fig.data[1].hovertemplate = "Linha: %{y}<br>Dia: %{x}<br>Vendas Identificadas: %{customdata[0]:.1f}%<extra></extra>"

            fig.update_layout(height=altura, template="plotly_white", margin=dict(t=20,b=20,l=30,r=30),
                              xaxis_title="Dia da semana",
                              yaxis=dict(
                title="",
                tickfont=dict(size=10),
                autorange='reversed',
                categoryorder='array',
                categoryarray=top_names
            ))
            fig.update_xaxes(side="top")
            fig.update_traces(xgap=1, ygap=2)
            st.plotly_chart(fig, use_container_width=True)

    # retornar DataFrame com percentual (1 casa decimal)
    out = df_rank[['vendedor_nome','vendas_identificadas_perc']].copy()
    out['vendas_identificadas_perc'] = out['vendas_identificadas_perc'].astype(float).round(1)
    return out.reset_index(drop=True)
