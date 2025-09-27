import streamlit as st
import pandas as pd

from data_processing.estoque.calculations import (
    calcular_disponibilidade_duck,
    calcular_giro_geral_e_combinacoes_duck,
    calcular_fator_cobertura_por_filial_duck,
    calcular_disponibilidade_por_curva_abc_duck,
    calcular_giro_por_curva_abc_duck,
    calcular_fator_cobertura_por_curva_abc_duck,
    calcular_disponibilidade_por_classificacao_n2_duck,
    calcular_giro_por_classificacao_n2_duck,
    calcular_fator_cobertura_por_classificacao_n2_duck

)

from business_logic.estoque.giro import (
    calcular_primeira_venda_geral,
    calcular_primeira_venda_geral_por_curva_abc,
    calcular_primeira_venda_por_classificacao_n2

)

from business_logic.estoque.curva_d import (
    calcular_indice_curva_d_geral,
    calcular_indice_desfazimento_curva_d_por_filial,
    calcular_indice_curva_d_por_classificacao_n1,
    calcular_indice_desfazimento_curva_d_por_classificacao_n1,
    calcular_indice_curva_d_por_classificacao_n2_geral,
    calcular_indice_desfazimento_curva_d_por_classificacao_n2
)

from business_logic.estoque.gmroi import (
    calcular_gmroi_baseado_vendas_duck,
    calcular_gmroi_por_curva_abc_duck,
    calcular_gmroi_por_curva_abc_n2_duck

)

from visualizations.charts.bar_charts import (
    criar_grafico_disponibilidade_por_filial_duck,
    criar_grafico_giro_por_filial_duck,
    criar_grafico_fator_cobertura_por_filial_duck,
    criar_grafico_curva_d_por_filial_duck,
    criar_grafico_desfazimento_curva_d_por_filial_duck,
    criar_grafico_disponibilidade_por_curva_abc_duck,
    criar_grafico_giro_por_curva_abc_duck,
    criar_grafico_fator_cobertura_por_curva_abc_duck,
    criar_grafico_primeira_venda_filial,
    criar_grafico_primeira_venda_por_curva_abc_duck,
    criar_grafico_disponibilidade_por_classificacao_n1,
    criar_grafico_giro_por_classificacao_n1,
    criar_grafico_fator_cobertura_por_classificacao_n1,
    criar_grafico_primeira_venda_por_classificacao_n1,
    criar_grafico_primeira_venda_30d_por_classificacao_n1,
    criar_grafico_curva_d_por_classificacao_n1,
    criar_grafico_desfazimento_curva_d_por_classificacao_n1,
    criar_grafico_disponibilidade_por_classificacao_n2,
    criar_grafico_giro_por_classificacao_n2,
    criar_grafico_fator_cobertura_por_classificacao_n2,
    criar_grafico_primeira_venda_por_classificacao_n2,
    criar_grafico_primeira_venda_30d_por_classificacao_n2,
    criar_grafico_curva_d_por_classificacao_n2,
    criar_grafico_desfazimento_curva_d_por_classificacao_n2,
    criar_grafico_gmroi_por_filial_ano,
    criar_grafico_gmroi_por_filial_90d,
    criar_grafico_gmroi_por_curva_abc_duck_90,
    criar_grafico_gmroi_por_curva_abc_duck_ano,
    criar_grafico_gmroi_class_n1_abc_duck_90,
    criar_grafico_gmroi_class_n1_duck_ano,
    criar_grafico_gmroi_class_n2_duck_90,
    criar_grafico_gmroi_class_n2_duck_ano
)

from data_processing.estoque.historico import (
    load_hist_disponibilidade,
    load_hist_giro,
    load_hist_cobertura,
    load_hist_gmroi,
    load_hist_curvad,
    load_hist_desfazimento
)

from visualizations.charts.historico_charts import (
    criar_grafico_disponibilidade_historico,
    criar_grafico_giro_historico,
    criar_grafico_cobertura_historico,
    criar_grafico_gmroi_historico,
    criar_grafico_curvad_historico,
    criar_grafico_desfazimento_historico
)

def render_content_filial(data_atual):
    """Renderiza conteúdo dos indicadores por Filial"""

    df_disponibilidade = calcular_disponibilidade_duck(data_atual)
    df_giro, _ = calcular_giro_geral_e_combinacoes_duck(data_atual)
    df_fator_cobertura = calcular_fator_cobertura_por_filial_duck(data_atual)
    _, df_primeira_venda, _ = calcular_primeira_venda_geral(data_atual)
    _, df_filial, _ = calcular_indice_curva_d_geral(data_atual)
    df_desfazimento = calcular_indice_desfazimento_curva_d_por_filial(data_atual)
    df_gmroi_filial_ano = calcular_gmroi_baseado_vendas_duck(data_atual, periodo_vendas=360)
    df_gmroi_filial_90 = calcular_gmroi_baseado_vendas_duck(data_atual)
    
    st.markdown("##### Indicadores por Filial")

    # Grid 2x2 de gráficos
    col1, col2 = st.columns(2, gap="medium")
    
    with col1:
        
        # GRÁFICO POR DISPONIBILIDADE
        df_disp_filial = df_disponibilidade[
            (df_disponibilidade['filial_codigo'] != 'Geral')            
        ].copy()
        
        if not df_disp_filial.empty:
            fig = criar_grafico_disponibilidade_por_filial_duck(df_disp_filial)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Nenhum dado disponível")
        
        # GRÁFICO POR GIRO DE ESTOQUE
        df_giro_filial = df_giro[
            (df_giro['filial_codigo'] != 'Geral') &
            (df_giro['filial_codigo'] != 'Geral_90d') &
            (df_giro['classificacao_n1'] == 'Geral')
        ].copy()
        
        if not df_giro_filial.empty:
            df_giro_filial['giro'] = df_giro_filial['giro_medio_anual']
            fig = criar_grafico_giro_por_filial_duck(df_giro_filial)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Nenhum dado disponível")

        # GRÁFICO POR FATOR DE COBERTURA
        if not df_fator_cobertura.empty:
            fig = criar_grafico_fator_cobertura_por_filial_duck(df_fator_cobertura)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Nenhum dado disponível")

        # GRÁFICO POR GMROI (ANO)
        if not df_gmroi_filial_ano.empty:
            fig = criar_grafico_gmroi_por_filial_ano(df_gmroi_filial_ano)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Nenhum dado disponível")

    with col2:
        
        if not df_filial.empty:
            fig = criar_grafico_primeira_venda_filial(df_primeira_venda)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Nenhum dado disponível")
        
        if not df_filial.empty:
            fig = criar_grafico_curva_d_por_filial_duck(df_filial)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Nenhum dado disponível")
    
        if not df_desfazimento.empty:
            fig = criar_grafico_desfazimento_curva_d_por_filial_duck(df_desfazimento)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Nenhum dado disponível")
        
        # GRÁFICO POR GMROI 90 DIAS
        if not df_gmroi_filial_90.empty:
            fig = criar_grafico_gmroi_por_filial_90d(df_gmroi_filial_90)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Nenhum dado disponível")

def render_content_curva_abc(data_atual):
    """Renderiza conteúdo dos indicadores por Curva ABC"""

    # Calcular dados iniciais para preencher os filtros
    df_disponibilidade = calcular_disponibilidade_por_curva_abc_duck(data_atual)
    df_giro = calcular_giro_por_curva_abc_duck(data_atual)
    df_fator_cobertura = calcular_fator_cobertura_por_curva_abc_duck(data_atual)
    _, df_primeira_curva, _ = calcular_primeira_venda_geral_por_curva_abc(data_atual)
    df_gmroi_curva_ano = calcular_gmroi_por_curva_abc_duck(data_atual, periodo_vendas=360)
    df_gmroi_curva_90 = calcular_gmroi_por_curva_abc_duck(data_atual, periodo_vendas=90)

    st.markdown("##### Indicadores por Curva ABC")

    # Obter opções para os filtros
    filiais_disponiveis = sorted([f for f in df_disponibilidade['filial_codigo'].unique() if f != 'Geral'])
    classificacoes_disponiveis = sorted([c for c in df_disponibilidade['classificacao_n1'].unique() if c != 'Geral' and c is not None])

    # Filtros na parte superior
    col_filter1, col_filter2 = st.columns(2)
    
    with col_filter1:
        # Filtro de Filial
        opcoes_filial = ['Geral'] + filiais_disponiveis
        filial_selecionada = st.selectbox(
            "🏢 Filtrar por Filial:",
            options=opcoes_filial,
            index=0,  # 'Geral' por padrão
            key="curva_abc_filial_filter"
        )
    
    with col_filter2:
        # Filtro de Classificação N1
        opcoes_classif = ['Geral'] + classificacoes_disponiveis
        classif_selecionada = st.selectbox(
            "🏷️ Filtrar por Grupo:",
            options=opcoes_classif,
            index=0,  # 'Geral' por padrão
            key="curva_abc_classif_filter"
        )
    
    # Grid de gráficos
    col1, col2, col3 = st.columns(3, gap="small")

    with col1:
        
        # GRÁFICO DE DISPONIBILIDADE
        df_disp_curva = df_disponibilidade[
            (df_disponibilidade['filial_codigo'] == filial_selecionada) &
            (df_disponibilidade['curvaABC'] != 'Geral') &
            (df_disponibilidade['classificacao_n1'] == classif_selecionada)
        ].copy()

        if not df_disp_curva.empty:
            fig = criar_grafico_disponibilidade_por_curva_abc_duck(df_disp_curva)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Nenhum dado disponível para os filtros selecionados")

        # GRÁFICO DE PRIMEIRA VENDA
        df_primeira_curva_filtrada = df_primeira_curva[
            (df_primeira_curva['filial_codigo'] == filial_selecionada) &
            (df_primeira_curva['curvaABC'] != 'Geral') &
            (df_primeira_curva['classificacao_n1'] == classif_selecionada)
        ].copy()

        if not df_primeira_curva_filtrada.empty:
            fig = criar_grafico_primeira_venda_por_curva_abc_duck(df_primeira_curva_filtrada)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Nenhum dado disponível para os filtros selecionados")
               
    with col2:
        # Filtrar dados de giro por curva ABC com filtros aplicados
        # Correção: filial_selecionada => filial_codigo, classif_selecionada => classificacao_n1
        if filial_selecionada == 'Geral' and classif_selecionada == 'Geral':
            # Ambos gerais: usar agregados gerais
            df_giro_curva = df_giro[
                (df_giro['filial_codigo'] == 'Geral') &
                (df_giro['curvaABC'] != 'Geral') &
                (df_giro['classificacao_n1'] == 'Geral')
            ].copy()
        elif filial_selecionada == 'Geral' and classif_selecionada != 'Geral':
            # Filial agregada, classificação específica (ex.: INDICAÇÃO, PRESCRIÇÃO...)
            df_giro_curva = df_giro[
                (df_giro['filial_codigo'] == 'Geral') &
                (df_giro['curvaABC'] != 'Geral') &
                (df_giro['classificacao_n1'] == classif_selecionada)
            ].copy()
        elif filial_selecionada != 'Geral' and classif_selecionada == 'Geral':
            # Filial específica (01..13), classificação agregada
            df_giro_curva = df_giro[
                (df_giro['filial_codigo'] == filial_selecionada) &
                (df_giro['curvaABC'] != 'Geral') &
                (df_giro['classificacao_n1'] == 'Geral')
            ].copy()
        else:
            # Ambos específicos: filial X e classificação Y
            df_giro_curva = df_giro[
                (df_giro['filial_codigo'] == filial_selecionada) &
                (df_giro['curvaABC'] != 'Geral') &
                (df_giro['classificacao_n1'] == classif_selecionada)
            ].copy()
        
        if not df_giro_curva.empty:
            df_giro_curva['giro'] = df_giro_curva['giro_medio_anual']
            fig = criar_grafico_giro_por_curva_abc_duck(df_giro_curva)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Nenhum dado disponível para os filtros selecionados")
        
        # GRÁFICO DE RETORNO POR MARGEM BRUTA (ANO)
        df_gmroi_curva_filtrado_ano = df_gmroi_curva_ano[
            (df_gmroi_curva_ano['filial_codigo'] == filial_selecionada) &
            (df_gmroi_curva_ano['curvaABC'] != 'Geral') &
            (df_gmroi_curva_ano['classificacao_n1'] == classif_selecionada)
        ].copy()

        if not df_gmroi_curva_filtrado_ano.empty:
            fig = criar_grafico_gmroi_por_curva_abc_duck_ano(df_gmroi_curva_filtrado_ano)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Nenhum dado disponível para os filtros selecionados")

    with col3:
        # Filtrar dados de fator cobertura por curva ABC com filtros aplicados
        df_cobertura_curva = df_fator_cobertura[
            (df_fator_cobertura['filial_codigo'] == filial_selecionada) &
            (df_fator_cobertura['curvaABC'] != 'Geral') &
            (df_fator_cobertura['classificacao_n1'] == classif_selecionada)
        ].copy()
        
        if not df_cobertura_curva.empty:
            fig = criar_grafico_fator_cobertura_por_curva_abc_duck(df_cobertura_curva)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Nenhum dado disponível para os filtros selecionados")
        
        # GRÁFICO DE RETORNO POR MARGEM BRUTA (90 DIAS)
        df_gmroi_curva_filtrado_90_dias = df_gmroi_curva_90[
            (df_gmroi_curva_90['filial_codigo'] == filial_selecionada) &
            (df_gmroi_curva_90['curvaABC'] != 'Geral') &
            (df_gmroi_curva_90['classificacao_n1'] == classif_selecionada)
        ].copy()

        if not df_gmroi_curva_filtrado_90_dias.empty:
            fig = criar_grafico_gmroi_por_curva_abc_duck_90(df_gmroi_curva_filtrado_90_dias)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Nenhum dado disponível para os filtros selecionados")
        
    # Informações sobre os filtros aplicados
    if filial_selecionada != 'Geral' or classif_selecionada != 'Geral':
        st.markdown("---")
        filtros_info = []
        if filial_selecionada != 'Geral':
            filtros_info.append(f"**Filial:** {filial_selecionada}")
        if classif_selecionada != 'Geral':
            filtros_info.append(f"**Grupo:** {classif_selecionada}")

def render_content_grupo(data_atual):
    """Renderiza conteúdo dos indicadores por Grupo (Classificação N1)"""
    
    # Calcular dados iniciais para preencher os filtros
    df_disponibilidade = calcular_disponibilidade_por_curva_abc_duck(data_atual)
    df_giro = calcular_giro_por_curva_abc_duck(data_atual)
    df_fator_cobertura = calcular_fator_cobertura_por_curva_abc_duck(data_atual)
    _, df_primeira_venda, _ = calcular_primeira_venda_geral_por_curva_abc(data_atual)
    df_curvad_class = calcular_indice_curva_d_por_classificacao_n1(data_atual)
    df_desfazimento_class = calcular_indice_desfazimento_curva_d_por_classificacao_n1(data_atual)
    df_gmroi_class_ano = calcular_gmroi_por_curva_abc_duck(data_atual, periodo_vendas=360)
    df_gmroi_class_90 = calcular_gmroi_por_curva_abc_duck(data_atual, periodo_vendas=90)
    
    st.markdown("##### Indicadores por Grupo Principal (Classificação N1)")

    # Obter opções para os filtros
    filiais_disponiveis = sorted([f for f in df_disponibilidade['filial_codigo'].unique() if f != 'Geral'])
    grupos_disponiveis = sorted([c for c in df_disponibilidade['curvaABC'].unique() if c != 'Geral' and c is not None])
    
    # Filtros na parte superior
    col_filter1, col_filter2 = st.columns(2)
    
    with col_filter1:
        # Filtro de Filial
        opcoes_filial = ['Geral'] + filiais_disponiveis
        filial_selecionada = st.selectbox(
            "🏢 Filtrar por Filial:",
            options=opcoes_filial,
            index=0,  # 'Geral' por padrão
            key="classif_filial_filter"
        )
    
    with col_filter2:
        # Filtro de curva ABC
        opcoes_curva = ['Geral'] + grupos_disponiveis
        curva_selecionada = st.selectbox(
            "🏷️ Filtrar por Curva ABC:",
            options=opcoes_curva,
            index=0,  # 'Geral' por padrão
            key="classif_curva_filter"
        )
        
    # Grid de gráficos
    col1, col2, col3 = st.columns(3, gap="small")

    with col1:
        
        # GRÁFICO POR DISPONIBILIDADE

        df_disp_classif = df_disponibilidade[
            (df_disponibilidade['filial_codigo'] == filial_selecionada) &
            (df_disponibilidade['classificacao_n1'] != 'Geral') &
            (df_disponibilidade['curvaABC'] == curva_selecionada)
        ].copy()

        if not df_disp_classif.empty:
            fig = criar_grafico_disponibilidade_por_classificacao_n1(df_disp_classif)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Nenhum dado disponível para os filtros selecionados")
        
        # GRÁFICO DE RETORNO POR MARGEM BRUTA (ANO)
        df_gmroi_class_ano_filtrado = df_gmroi_class_ano[
            (df_gmroi_class_ano['filial_codigo'] == filial_selecionada) &
            (df_gmroi_class_ano['classificacao_n1'] != 'Geral') &
            (df_gmroi_class_ano['curvaABC'] == curva_selecionada)
        ].copy()

        if not df_gmroi_class_ano_filtrado.empty:
            fig = criar_grafico_gmroi_class_n1_duck_ano(df_gmroi_class_ano_filtrado)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Nenhum dado disponível para os filtros selecionados")

        # GRÁFICO POR PRIMEIRA VENDA
        
        df_primeira_class_filtrada = df_primeira_venda[
            (df_primeira_venda['filial_codigo'] == filial_selecionada) &
            (df_primeira_venda['classificacao_n1'] != 'Geral') &
            (df_primeira_venda['curvaABC'] == curva_selecionada)
        ].copy()

        if not df_primeira_class_filtrada.empty:
            fig = criar_grafico_primeira_venda_por_classificacao_n1(df_primeira_class_filtrada)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Nenhum dado disponível para os filtros selecionados")
                       
    with col2:
        
        # GRÁFICO POR GIRO
        df_giro_classif = df_giro[
            (df_giro['filial_codigo'] == filial_selecionada) &
            (df_giro['classificacao_n1'] != 'Geral') &
            (df_giro['curvaABC'] == curva_selecionada)
        ].copy()

        if not df_giro_classif.empty:
            fig = criar_grafico_giro_por_classificacao_n1(df_giro_classif)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Nenhum dado disponível para os filtros selecionados")
        
        # GRÁFICO DE RETORNO POR MARGEM BRUTA (90 DIAS)
        df_gmroi_class_90_filtrado = df_gmroi_class_90[
            (df_gmroi_class_90['filial_codigo'] == filial_selecionada) &
            (df_gmroi_class_90['classificacao_n1'] != 'Geral') &
            (df_gmroi_class_90['curvaABC'] == curva_selecionada)
        ].copy()

        if not df_gmroi_class_90_filtrado.empty:
            fig = criar_grafico_gmroi_class_n1_abc_duck_90(df_gmroi_class_90_filtrado)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Nenhum dado disponível para os filtros selecionados")

        # GRÁFICO POR PRIMEIRA VENDA APÓS 30 DIAS
        
        df_primeira_class_filtrada = df_primeira_venda[
            (df_primeira_venda['filial_codigo'] == filial_selecionada) &
            (df_primeira_venda['classificacao_n1'] != 'Geral') &
            (df_primeira_venda['curvaABC'] == curva_selecionada)
        ].copy()

        if not df_primeira_class_filtrada.empty:
            fig = criar_grafico_primeira_venda_30d_por_classificacao_n1(df_primeira_class_filtrada)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Nenhum dado disponível para os filtros selecionados")

    with col3:
        
        # GRÁFICO POR FATOR COBERTURA
        df_cobertura_classif = df_fator_cobertura[
            (df_fator_cobertura['filial_codigo'] == filial_selecionada) &
            (df_fator_cobertura['classificacao_n1'] != 'Geral') &
            (df_fator_cobertura['curvaABC'] == curva_selecionada)
        ].copy()

        if not df_cobertura_classif.empty:
            fig = criar_grafico_fator_cobertura_por_classificacao_n1(df_cobertura_classif)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Nenhum dado disponível para os filtros selecionados")
        
        # GRÁFICO POR CURVA D
        df_curvad_class_filtrada = df_curvad_class[
            (df_curvad_class['filial_codigo'] == filial_selecionada) &
            (df_curvad_class['classificacao_n1'] != 'Geral') &
            (df_curvad_class['curvaABC'] == curva_selecionada)
        ].copy()

        if not df_curvad_class_filtrada.empty:
            fig = criar_grafico_curva_d_por_classificacao_n1(df_curvad_class_filtrada)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Nenhum dado disponível para os filtros selecionados")
        
        # GRÁFICO POR DESFAZIMENTO
        df_desfazimento_classif = df_desfazimento_class[
            (df_desfazimento_class['filial_codigo'] == filial_selecionada) &
            (df_desfazimento_class['classificacao_n1'] != 'Geral') &
            (df_desfazimento_class['curvaABC'] == curva_selecionada)
        ].copy()

        if not df_desfazimento_classif.empty:
            fig = criar_grafico_desfazimento_curva_d_por_classificacao_n1(df_desfazimento_classif)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Nenhum dado disponível para os filtros selecionados")

def render_content_nivel2(data_atual):
    """Renderiza conteúdo dos indicadores por Nível 2 (Classificação N2)"""
    # Calcular dados iniciais para preencher os filtros
    df_disp_class_n2 = calcular_disponibilidade_por_classificacao_n2_duck(data_atual)
    df_giro_class_n2 = calcular_giro_por_classificacao_n2_duck(data_atual)
    df_cobertura_class_n2 = calcular_fator_cobertura_por_classificacao_n2_duck(data_atual)
    _, df_primeira_venda_class_n2, _ = calcular_primeira_venda_por_classificacao_n2(data_atual)
    _, df_curvad_class_n2 = calcular_indice_curva_d_por_classificacao_n2_geral(data_atual)
    df_desfazimento_class_n2 = calcular_indice_desfazimento_curva_d_por_classificacao_n2(data_atual)
    df_gmroi_class_n2_ano = calcular_gmroi_por_curva_abc_n2_duck(data_atual, periodo_vendas=360)
    df_gmroi_class_n2_90 = calcular_gmroi_por_curva_abc_n2_duck(data_atual, periodo_vendas=90)

    st.markdown("##### Indicadores por Subgrupo (Classificação N2)")

    # Obter opções para os filtros
    filiais_disponiveis = sorted([f for f in df_disp_class_n2['filial_codigo'].unique() if f != 'Geral'])
    grupos_disponiveis = sorted([c for c in df_disp_class_n2['curvaABC'].unique() if c != 'Geral' and c is not None])

    # Filtros na parte superior
    col_filter1, col_filter2 = st.columns(2)
    
    with col_filter1:
        # Filtro de Filial
        opcoes_filial = ['Geral'] + filiais_disponiveis
        filial_selecionada = st.selectbox(
            "🏢 Filtrar por Filial:",
            options=opcoes_filial,
            index=0,  # 'Geral' por padrão
            key="classif_filial_filter"
        )
    
    with col_filter2:
        # Filtro de curva ABC
        opcoes_curva = ['Geral'] + grupos_disponiveis
        curva_selecionada = st.selectbox(
            "🏷️ Filtrar por Curva ABC:",
            options=opcoes_curva,
            index=0,  # 'Geral' por padrão
            key="classif_curva_filter"
        )
    
    # Grid de gráficos
    col1, col2, col3, col4 = st.columns(4, gap="small")

    with col1:
        
        # GRÁFICO POR DISPONIBILIDADE
        df_disp_classif = df_disp_class_n2[
            (df_disp_class_n2['filial_codigo'] == filial_selecionada) &
            (df_disp_class_n2['classificacao_n2'] != 'Geral') &
            (df_disp_class_n2['curvaABC'] == curva_selecionada)
        ].copy()

        if not df_disp_classif.empty:
            fig = criar_grafico_disponibilidade_por_classificacao_n2(df_disp_classif)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Nenhum dado disponível para os filtros selecionados")
        
        # GRÁFICO DE GMROI (ANO)
        df_gmroi_class_n2_ano_filtrado = df_gmroi_class_n2_ano[
            (df_gmroi_class_n2_ano['filial_codigo'] == filial_selecionada) &
            (df_gmroi_class_n2_ano['classificacao_n2'] != 'Geral') &
            (df_gmroi_class_n2_ano['curvaABC'] == curva_selecionada)
        ].copy()

        if not df_gmroi_class_n2_ano_filtrado.empty:
            fig = criar_grafico_gmroi_class_n2_duck_ano(df_gmroi_class_n2_ano_filtrado)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Nenhum dado disponível para os filtros selecionados")
                       
    with col2:
        
        # GRÁFICO POR GIRO
        df_giro_classif_n2 = df_giro_class_n2[
            (df_giro_class_n2['filial_codigo'] == filial_selecionada) &
            (df_giro_class_n2['classificacao_n2'] != 'Geral') &
            (df_giro_class_n2['curvaABC'] == curva_selecionada)
        ].copy()

        if not df_giro_classif_n2.empty:
            fig = criar_grafico_giro_por_classificacao_n2(df_giro_classif_n2)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Nenhum dado disponível para os filtros selecionados")
        
        # GRÁFICO DE GMROI (90 DIAS)
        df_gmroi_class_n2_90_filtrado = df_gmroi_class_n2_90[
            (df_gmroi_class_n2_90['filial_codigo'] == filial_selecionada) &
            (df_gmroi_class_n2_90['classificacao_n2'] != 'Geral') &
            (df_gmroi_class_n2_90['curvaABC'] == curva_selecionada)
        ].copy()

        if not df_gmroi_class_n2_90_filtrado.empty:
            fig = criar_grafico_gmroi_class_n2_duck_90(df_gmroi_class_n2_90_filtrado)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Nenhum dado disponível para os filtros selecionados")

    with col3:
        
        # GRÁFICO POR FATOR COBERTURA
        df_cobertura_classif_n2 = df_cobertura_class_n2[
            (df_cobertura_class_n2['filial_codigo'] == filial_selecionada) &
            (df_cobertura_class_n2['classificacao_n2'] != 'Geral') &
            (df_cobertura_class_n2['curvaABC'] == curva_selecionada)
        ].copy()

        if not df_cobertura_classif_n2.empty:
            fig = criar_grafico_fator_cobertura_por_classificacao_n2(df_cobertura_classif_n2)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Nenhum dado disponível para os filtros selecionados")
        
        # GRÁFICO POR PRIMEIRA VENDA
        
        df_primeira_venda_class_n2_filtrada = df_primeira_venda_class_n2[
            (df_primeira_venda_class_n2['filial_codigo'] == filial_selecionada) &
            (df_primeira_venda_class_n2['classificacao_n2'] != 'Geral') &
            (df_primeira_venda_class_n2['curvaABC'] == curva_selecionada)
        ].copy()

        if not df_primeira_venda_class_n2_filtrada.empty:
            fig = criar_grafico_primeira_venda_por_classificacao_n2(df_primeira_venda_class_n2_filtrada)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Nenhum dado disponível para os filtros selecionados")
    
    with col4:
        
        # GRÁFICO POR CURVA D
        df_curvad_class_n2_filtrada = df_curvad_class_n2[
            (df_curvad_class_n2['filial_codigo'] == filial_selecionada) &
            (df_curvad_class_n2['classificacao_n2'] != 'Geral') &
            (df_curvad_class_n2['curvaABC'] == curva_selecionada)
        ].copy()

        if not df_curvad_class_n2_filtrada.empty:
            fig = criar_grafico_curva_d_por_classificacao_n2(df_curvad_class_n2_filtrada)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Nenhum dado disponível para os filtros selecionados")    

        # GRÁFICO POR DESFAZIMENTO
        df_desfazimento_classif_n2 = df_desfazimento_class_n2[
            (df_desfazimento_class_n2['filial_codigo'] == filial_selecionada) &
            (df_desfazimento_class_n2['classificacao_n2'] != 'Geral') &
            (df_desfazimento_class_n2['curvaABC'] == curva_selecionada)
        ].copy()

        if not df_desfazimento_classif_n2.empty:
            fig = criar_grafico_desfazimento_curva_d_por_classificacao_n2(df_desfazimento_classif_n2)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Nenhum dado disponível para os filtros selecionados")

def render_content_historico(data_atual):
    """Renderiza conteúdo dos indicadores por Histórico"""
    
    df_disp_historico = load_hist_disponibilidade(True)
    df_giro_historico = load_hist_giro(True)
    df_cobertura_historico = load_hist_cobertura(True)
    df_gmroi_historico = load_hist_gmroi(True)
    df_curvad_historico = load_hist_curvad(True)
    df_desfazimento_historico = load_hist_desfazimento(True)

    if df_disp_historico.empty:
        st.warning("Histórico vazio.")
        return

    lista_filiais = ['Geral', '01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12', '13']
    lista_curvas = ['Geral', 'A', 'B', 'C', 'D']
    lista_n1 = ['Geral', 'INDICAÇÃO', 'PRESCRIÇÃO', 'SBB', 'VAREJO']
    lista_n2 = ['Geral'] + sorted([c for c in df_disp_historico["classificacao_n2"].unique() if c not in ("Geral", None)])

    fcol1, fcol2, fcol3, fcol4 = st.columns(4)
    with fcol1:
        filial_sel = st.selectbox("Filial", lista_filiais, key="hist_filial")
    with fcol2:
        curva_sel = st.selectbox("Curva ABC", lista_curvas, key="hist_curva")
    with fcol3:
        n1_sel = st.selectbox("Classificação N1", lista_n1, key="hist_n1")
    with fcol4:
        n2_sel = st.selectbox("Classificação N2", lista_n2, key="hist_n2")

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Disponibilidade", "Giro de Estoque","Fator de Cobertura","Retorno de Margem Bruta (GMROI)", "Conversão para Curva D", "Venda Curva D (30 dias)"])

    with tab1:

        df = df_disp_historico.copy()
        if filial_sel != "Geral":
            df = df[df.filial_codigo == filial_sel]
        if curva_sel != "Geral":
            df = df[df.curvaABC == curva_sel]
        if n1_sel != "Geral":
            df = df[df.classificacao_n1 == n1_sel]
        if n2_sel != "Geral":
            df = df[df.classificacao_n2 == n2_sel]

        if df.empty:
            st.warning("Sem dados para os filtros.")
            return
    
        # Agregação mensal (média ponderada)
        df_plot = (
            df.groupby("ano_mes", as_index=False)
          .agg(total_itens=("total_itens", "sum"),
               itens_disponiveis=("itens_disponiveis", "sum"))
    )
        df_plot["disponibilidade_percent"] = (
            (df_plot["itens_disponiveis"] * 100.0 / df_plot["total_itens"]).round(2)
        )

        # Passa apenas linhas agregadas
        fig = criar_grafico_disponibilidade_historico(df_plot)
        st.plotly_chart(fig, use_container_width=True)   

    with tab2:
        
        df = df_giro_historico.copy()
        if filial_sel != "Geral":
            df = df[df.filial_codigo == filial_sel]
        if curva_sel != "Geral":
            df = df[df.curvaABC == curva_sel]
        if n1_sel != "Geral":
            df = df[df.classificacao_n1 == n1_sel]
        if n2_sel != "Geral":
            df = df[df.classificacao_n2 == n2_sel]

        if df.empty:
            st.warning("Sem dados para os filtros.")
            return

        # AGREGAÇÃO MENSAL (soma valores e recalcula %)
        df_plot = (
            df.groupby("ano_mes", as_index=False)
              .agg(
                  total_valor_estoque=("total_valor_estoque", "sum"),
                  valor_estoque_com_giro=("valor_estoque_com_giro", "sum")
              )
        )
        df_plot["valor_estoque_sem_giro"] = (
            df_plot["total_valor_estoque"] - df_plot["valor_estoque_com_giro"]
        )
        df_plot["giro_percent"] = (
            (df_plot["valor_estoque_com_giro"] * 100.0 / df_plot["total_valor_estoque"])
            .where(df_plot["total_valor_estoque"] > 0, 0)
            .round(2)
        )

        if df_plot.empty:
            st.warning("Sem dados agregados.")
            return

        fig = criar_grafico_giro_historico(df_plot)
        st.plotly_chart(fig, use_container_width=True)

    with tab3:

        df = df_cobertura_historico.copy()
        if filial_sel != "Geral":
            df = df[df.filial_codigo == filial_sel]
        if curva_sel != "Geral":
            df = df[df.curvaABC == curva_sel]
        if n1_sel != "Geral":
            df = df[df.classificacao_n1 == n1_sel]
        if n2_sel != "Geral":
            df = df[df.classificacao_n2 == n2_sel]

        if df.empty:
            st.warning("Sem dados para os filtros.")
            return

        # AGREGAÇÃO MENSAL (soma valores e recalcula %)
        df_plot = (
            df.groupby("ano_mes", as_index=False)
              .agg(
                  stock_cmv=("stock_cmv", "sum"),
                  cmv_vendido_30d=("cmv_vendido_30d", "sum")
              )
        )
        df_plot["cobertura_ratio"] = (
            (df_plot["stock_cmv"]  / df_plot["cmv_vendido_30d"])
            .where(df_plot["cmv_vendido_30d"] > 0, 0)
            .round(2)
        )

        if df_plot.empty:
            st.warning("Sem dados agregados.")
            return

        fig = criar_grafico_cobertura_historico(df_plot)
        st.plotly_chart(fig, use_container_width=True)

    with tab4:
        
        df = df_gmroi_historico.copy()
        if filial_sel != "Geral":
            df = df[df.filial_codigo == filial_sel]
        if curva_sel != "Geral":
            df = df[df.curvaABC == curva_sel]
        if n1_sel != "Geral":
            df = df[df.classificacao_n1 == n1_sel]
        if n2_sel != "Geral":
            df = df[df.classificacao_n2 == n2_sel]

        if df.empty:
            st.warning("Sem dados para os filtros.")
            return

        # AGREGAÇÃO MENSAL (soma valores e recalcula %)
        df_plot = (
            df.groupby("ano_mes", as_index=False)
              .agg(
                  margem_bruta=("margem_bruta_vendas", "sum"),
                  valor_estoque=("valor_medio_estoque", "sum")
              )
        )
        df_plot["gmroi_ratio"] = (
            (df_plot["margem_bruta"] / df_plot["valor_estoque"])
            .where(df_plot["valor_estoque"] > 0, 0)
            .round(2)
        )

        if df_plot.empty:
            st.warning("Sem dados agregados.")
            return

        fig = criar_grafico_gmroi_historico(df_plot)
        st.plotly_chart(fig, use_container_width=True)
    
    with tab5:
        df = df_curvad_historico.copy()
        if filial_sel != "Geral":
            df = df[df.filial_codigo == filial_sel]
        if curva_sel != "Geral":
            df = df[df.curvaABC == curva_sel]
        if n1_sel != "Geral":
            df = df[df.classificacao_n1 == n1_sel]
        if n2_sel != "Geral":
            df = df[df.classificacao_n2 == n2_sel]

        if df.empty:
            st.warning("Sem dados para os filtros.")
            return

        # AGREGAÇÃO MENSAL (soma valores e recalcula %)
        df_plot = (
            df.groupby("ano_mes", as_index=False)
              .agg(
                  total_val_curva_d=("total_val_curva_d", "sum"),
                  total_val_all=("total_val_all", "sum")
              )
        )
        df_plot["indice_curva_d"] = (
            (df_plot["total_val_curva_d"] * 100.0 / df_plot["total_val_all"])
            .where(df_plot["total_val_all"] > 0, 0)
            .round(2)
        )

        if df_plot.empty:
            st.warning("Sem dados agregados.")
            return

        fig = criar_grafico_curvad_historico(df_plot)
        st.plotly_chart(fig, use_container_width=True)
    
    with tab6:
        df = df_desfazimento_historico.copy()
        if filial_sel != "Geral":
            df = df[df.filial_codigo == filial_sel]
        if curva_sel != "Geral":
            df = df[df.curvaABC == curva_sel]
        if n1_sel != "Geral":
            df = df[df.classificacao_n1 == n1_sel]
        if n2_sel != "Geral":
            df = df[df.classificacao_n2 == n2_sel]

        if df.empty:
            st.warning("Sem dados para os filtros.")
            return

        # AGREGAÇÃO MENSAL (soma valores e recalcula %)
        df_plot = (
            df.groupby("ano_mes", as_index=False)
              .agg(
                  total_numer=("total_numer", "sum"),
                  total_denom=("total_denom", "sum")
              )
        )
        df_plot["indice_30d_pct"] = (
            (df_plot["total_numer"] * 100.0 / df_plot["total_denom"])
            .where(df_plot["total_denom"] > 0, 0)
            .round(2)
        )

        if df_plot.empty:
            st.warning("Sem dados agregados.")
            return

        fig = criar_grafico_desfazimento_historico(df_plot)
        st.plotly_chart(fig, use_container_width=True)