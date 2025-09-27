
"""Funções utilitárias para formatação e helpers gerais"""

def formatar_moeda(valor):
    """Formata valor como moeda brasileira"""
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def formatar_numero(valor):
    """Formata número com separadores"""
    return f"{valor:,.0f}".replace(',', '.')

def formatar_numero_uma_casa(valor):
    """Formata número com separadores"""
    return f"{valor:,.1f}".replace(',', '.')


def formatar_percentual(valor):
    """Formata percentual"""
    return f"{valor:.1f}%"

def debug_totais_estoque_duck(data_limite='2025-09-19'):
    """
    Debug dos totais de estoque até a data especificada.
    """
    try:
        # Valor total do estoque (pelo custo médio)
        sql_valor_total = f"""
        WITH estoque_atual AS (
            SELECT
                filial_codigo,
                embalagemid,
                estoque,
                customedio,
                (customedio * estoque) AS valor_estoque,
                ROW_NUMBER() OVER (PARTITION BY filial_codigo, embalagemid ORDER BY datahora DESC) AS rn
            FROM fact_estoque_final
            WHERE datahora <= DATE '{data_limite}'
        )
        SELECT
            SUM(valor_estoque) AS valor_total_estoque
        FROM estoque_atual
        WHERE rn = 1
        """
        
        df_valor = duck_query(sql_valor_total)
        valor_total = df_valor['valor_total_estoque'].iloc[0] if df_valor is not None else 0
        
        # Quantidade de linhas
        sql_linhas = f"""
        SELECT COUNT(*) AS total_linhas
        FROM fact_estoque_final
        WHERE datahora <= DATE '{data_limite}'
        """
        
        df_linhas = duck_query(sql_linhas)
        total_linhas = df_linhas['total_linhas'].iloc[0] if df_linhas is not None else 0
        
        # Produtos únicos por filial
        sql_produtos_filial = f"""
        WITH estoque_atual AS (
            SELECT
                filial_codigo,
                embalagemid,
                ROW_NUMBER() OVER (PARTITION BY filial_codigo, embalagemid ORDER BY datahora DESC) AS rn
            FROM fact_estoque_final
            WHERE datahora <= DATE '{data_limite}'
        )
        SELECT
            filial_codigo,
            COUNT(DISTINCT embalagemid) AS produtos_unicos
        FROM estoque_atual
        WHERE rn = 1
        GROUP BY filial_codigo
        ORDER BY filial_codigo
        """
        
        df_produtos_filial = duck_query(sql_produtos_filial)
        
        # Exibir resultados
        st.markdown("### 🔍 Debug - Totais de Estoque até 19/09/2025")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                label="Valor Total do Estoque",
                value=f"R$ {valor_total:,.2f}" if valor_total else "R$ 0,00"
            )
        
        with col2:
            st.metric(
                label="Total de Linhas",
                value=f"{total_linhas:,}" if total_linhas else "0"
            )
        
        with col3:
            total_produtos_unicos = df_produtos_filial['produtos_unicos'].sum() if df_produtos_filial is not None else 0
            st.metric(
                label="Total Produtos Únicos",
                value=f"{total_produtos_unicos:,}" if total_produtos_unicos else "0"
            )
        
        # Tabela de produtos por filial
        if df_produtos_filial is not None and not df_produtos_filial.empty:
            st.markdown("#### Produtos Únicos por Filial:")
            st.dataframe(df_produtos_filial, use_container_width=True)
        
        return {
            'valor_total_estoque': valor_total,
            'total_linhas': total_linhas,
            'produtos_por_filial': df_produtos_filial
        }
        
    except Exception as e:
        st.error(f"Erro no debug de totais: {e}")
        return None







def debug_tabelas_estoque():
    """Debug das tabelas de estoque para verificar estrutura e dados."""
    st.markdown("### 🔍 Debug - Estrutura das Tabelas")
    
    # Debug fact_estoque_final
    st.markdown("#### Tabela: fact_estoque_final")
    try:
        sql_info = """
        SELECT 
            COUNT(*) as total_linhas,
            COUNT(DISTINCT filial_codigo) as filiais_distintas,
            COUNT(DISTINCT embalagemid) as produtos_distintos,
            MIN(datahora) as data_mais_antiga,
            MAX(datahora) as data_mais_recente
        FROM fact_estoque_final
        """
        df_info = duck_query(sql_info)
        if df_info is not None:
            st.dataframe(df_info)
        
        # Amostra de dados
        sql_sample = "SELECT * FROM fact_estoque_final LIMIT 5"
        df_sample = duck_query(sql_sample)
        if df_sample is not None:
            st.markdown("**Amostra de dados:**")
            st.dataframe(df_sample)
            st.markdown(f"**Colunas:** {list(df_sample.columns)}")
        
    except Exception as e:
        st.error(f"Erro ao debugar fact_estoque_final: {e}")
    
    # Debug fact_vendas_final
    st.markdown("#### Tabela: fact_vendas_final")
    try:
        sql_info = """
        SELECT 
            COUNT(*) as total_linhas,
            COUNT(DISTINCT filial_codigo) as filiais_distintas,
            COUNT(DISTINCT item_embalagemid) as produtos_distintos,
            MIN(data_date) as data_mais_antiga,
            MAX(data_date) as data_mais_recente
        FROM fact_vendas_final
        """
        df_info = duck_query(sql_info)
        if df_info is not None:
            st.dataframe(df_info)
        
        # Amostra de dados
        sql_sample = "SELECT * FROM fact_vendas_final LIMIT 5"
        df_sample = duck_query(sql_sample)
        if df_sample is not None:
            st.markdown("**Amostra de dados:**")
            st.dataframe(df_sample)
            st.markdown(f"**Colunas:** {list(df_sample.columns)}")
        
    except Exception as e:
        st.error(f"Erro ao debugar fact_vendas_final: {e}")

def test_estoque_connection():
    """Testa conexão e consultas básicas."""
    st.markdown("### 🔧 Teste de Conexão")
    
    try:
        sql_test = "SELECT 1 as teste"
        result = duck_query(sql_test)
        if result is not None:
            st.success("✅ Conexão DuckDB funcionando")
        else:
            st.error("❌ Falha na conexão DuckDB")
    except Exception as e:
        st.error(f"❌ Erro na conexão: {e}")

def debug_curva_abc_duck(data_atual):
    """Debug específico da função de curva ABC."""
    st.markdown("### 🔍 Debug - Curva ABC")
    
    data_limite_90 = (pd.Timestamp(data_atual) - pd.Timedelta(days=90)).strftime('%Y-%m-%d')
    st.write(f"Data limite (90 dias): {data_limite_90}")
    
    # Testar vendas dos últimos 90 dias
    sql_vendas = f"""
    SELECT 
        COUNT(*) as total_vendas,
        COUNT(DISTINCT filial_codigo) as filiais,
        COUNT(DISTINCT item_embalagemid) as produtos,
        SUM(ABS(item_quantidade)) as quantidade_total
    FROM fact_vendas_final
    WHERE data_date >= DATE '{data_limite_90}'
    """
    
    try:
        df_vendas = duck_query(sql_vendas)
        if df_vendas is not None:
            st.markdown("**Vendas últimos 90 dias:**")
            st.dataframe(df_vendas)
        
        # Executar função completa
        df_curva = calcular_curva_abc_duck(data_atual)
        st.markdown(f"**Resultado curva ABC - Linhas:** {len(df_curva)}")
        if not df_curva.empty:
            st.dataframe(df_curva.head(10))
            
            # Distribuição por curva
            distribuicao = df_curva['curvaABC'].value_counts()
            st.markdown("**Distribuição por curva:**")
            st.dataframe(distribuicao)
        
    except Exception as e:
        st.error(f"Erro no debug curva ABC: {e}")

def debug_ruptura_duck(data_atual):
    """Debug específico da função de ruptura."""
    st.markdown("### 🔍 Debug - Índice de Ruptura")
    
    data_limite_90 = (pd.Timestamp(data_atual) - pd.Timedelta(days=90)).strftime('%Y-%m-%d')
    data_limite_30 = (pd.Timestamp(data_atual) - pd.Timedelta(days=30)).strftime('%Y-%m-%d')
    
    st.write(f"Data limite 90 dias: {data_limite_90}")
    st.write(f"Data limite 30 dias: {data_limite_30}")
    
    # Testar produtos comprados
    sql_comprados = f"""
    SELECT 
        COUNT(DISTINCT filial_codigo || '-' || embalagemid) as produtos_comprados,
        COUNT(DISTINCT filial_codigo) as filiais
    FROM fact_estoque_final
    WHERE datahora >= DATE '{data_limite_90}'
    AND descricao_movimentacao = 'Recebimento Físico'
    """
    
    try:
        df_comprados = duck_query(sql_comprados)
        st.markdown("**Produtos comprados (90d):**")
        st.dataframe(df_comprados)
        
        # Testar produtos vendidos
        sql_vendidos = f"""
        SELECT 
            COUNT(DISTINCT filial_codigo || '-' || item_embalagemid) as produtos_vendidos,
            COUNT(DISTINCT filial_codigo) as filiais
        FROM fact_vendas_final
        WHERE data_date >= DATE '{data_limite_30}'
        """
        
        df_vendidos = duck_query(sql_vendidos)
        st.markdown("**Produtos vendidos (30d):**")
        st.dataframe(df_vendidos)
        
        # Executar função completa
        df_ruptura = calcular_disponibilidade_duck(data_atual)
        st.markdown(f"**Resultado ruptura - Linhas:** {len(df_ruptura)}")
        if not df_ruptura.empty:
            st.dataframe(df_ruptura)
        
    except Exception as e:
        st.error(f"Erro no debug ruptura: {e}")

def debug_giro_duck(data_atual):
    """Debug específico da função de giro."""
    st.markdown("### 🔍 Debug - Giro de Estoque")
    
    data_limite_90 = (pd.Timestamp(data_atual) - pd.Timedelta(days=90)).strftime('%Y-%m-%d')
    
    # Testar vendas com CMV
    sql_vendas_cmv = f"""
    SELECT 
        COUNT(*) as total_vendas,
        SUM(ABS(item_quantidade * item_cmv)) as cmv_total,
        AVG(item_cmv) as cmv_medio
    FROM fact_vendas_final
    WHERE data_date >= DATE '{data_limite_90}'
    AND item_cmv IS NOT NULL AND item_cmv > 0
    """
    
    try:
        df_vendas_cmv = duck_query(sql_vendas_cmv)
        st.markdown("**Vendas com CMV (90d):**")
        st.dataframe(df_vendas_cmv)
        
        # Testar estoque atual
        sql_estoque = f"""
        SELECT 
            COUNT(*) as total_registros,
            COUNT(DISTINCT filial_codigo || '-' || embalagemid) as produtos_unicos,
            SUM(estoque * cmv) as valor_estoque_total,
            AVG(cmv) as cmv_medio
        FROM (
            SELECT 
                filial_codigo, embalagemid, estoque, cmv,
                ROW_NUMBER() OVER (PARTITION BY filial_codigo, embalagemid ORDER BY datahora DESC) as rn
            FROM fact_estoque_final
            WHERE datahora >= DATE '{data_limite_90}'
        ) e
        WHERE e.rn = 1 AND cmv IS NOT NULL AND cmv > 0
        """
        
        df_estoque = duck_query(sql_estoque)
        st.markdown("**Estoque atual:**")
        st.dataframe(df_estoque)
        
        # Executar função completa
        df_giros, kpis_giro = calcular_giro_geral_e_combinacoes_duck(data_atual)
        st.markdown(f"**Resultado giro - Linhas:** {len(df_giros)}")
        if not df_giros.empty:
            st.dataframe(df_giros)
        
        st.markdown("**KPIs de Giro:**")
        st.json(kpis_giro)
        
    except Exception as e:
        st.error(f"Erro no debug giro: {e}")
