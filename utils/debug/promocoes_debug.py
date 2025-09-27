"""
Utilitários de debug e teste para módulo de promoções
"""
import streamlit as st
from core.database import duck_query

def debug_tables_promocoes():
    """
    Função de debug para verificar as tabelas necessárias.
    """
    st.subheader("🔍 Debug - Tabelas de Promoções")
    
    # Verificar fact_vendas_final
    st.markdown("### 📊 Fact Vendas Final")
    try:
        sql_vendas = """
            SELECT 
                COUNT(*) AS total_registros,
                COUNT(DISTINCT venda_id) AS total_vendas,
                COUNT(DISTINCT embalagem_id) AS total_produtos,
                COUNT(DISTINCT filial_codigo) AS total_filiais,
                MIN(data_date) AS data_min,
                MAX(data_date) AS data_max,
                SUM(CASE WHEN item_cadernoofertaid IS NOT NULL THEN 1 ELSE 0 END) AS vendas_com_promocao
            FROM fact_vendas_final
        """
        df_vendas = duck_query(sql_vendas)
        if df_vendas is not None and not df_vendas.empty:
            row = df_vendas.iloc[0]
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"✅ Total de registros: {row['total_registros']:,}")
                st.write(f"✅ Total de vendas: {row['total_vendas']:,}")
                st.write(f"✅ Total de produtos: {row['total_produtos']:,}")
            with col2:
                st.write(f"✅ Total de filiais: {row['total_filiais']:,}")
                st.write(f"✅ Período: {row['data_min']} a {row['data_max']}")
                st.write(f"✅ Vendas c/ promoção: {row['vendas_com_promocao']:,}")
        else:
            st.error("❌ Tabela fact_vendas_final vazia ou não encontrada")
    except Exception as e:
        st.error(f"❌ Erro ao acessar fact_vendas_final: {e}")
    
    st.markdown("---")
    
    # Verificar cadernooferta
    st.markdown("### 🏷️ Caderno de Ofertas")
    try:
        sql_caderno = """
            SELECT 
                COUNT(*) AS total_promocoes,
                COUNT(CASE WHEN status = 'A' THEN 1 END) AS promocoes_ativas,
                MIN(datahorainicial) AS data_min_inicio,
                MAX(datahorafinal) AS data_max_fim
            FROM cadernooferta
            WHERE datahorainicial IS NOT NULL AND datahorafinal IS NOT NULL
        """
        df_caderno = duck_query(sql_caderno)
        if df_caderno is not None and not df_caderno.empty:
            row = df_caderno.iloc[0]
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"✅ Total de promoções: {row['total_promocoes']:,}")
                st.write(f"✅ Promoções ativas: {row['promocoes_ativas']:,}")
            with col2:
                st.write(f"✅ Período: {row['data_min_inicio']} a {row['data_max_fim']}")
        else:
            st.error("❌ Tabela cadernooferta vazia ou não encontrada")
    except Exception as e:
        st.error(f"❌ Erro ao acessar cadernooferta: {e}")


def test_promocoes_connection():
    """
    Testa conexões e consultas básicas.
    """
    st.subheader("🔌 Teste de Conexão")
    
    tabelas_necessarias = ['fact_vendas_final', 'cadernooferta']
    
    for tabela in tabelas_necessarias:
        try:
            sql = f"SELECT COUNT(*) as total FROM {tabela} LIMIT 1"
            result = duck_query(sql)
            if result is not None and not result.empty:
                total = result['total'].iloc[0]
                st.success(f"✅ {tabela}: {total:,} registros")
            else:
                st.error(f"❌ {tabela}: Sem dados")
        except Exception as e:
            st.error(f"❌ {tabela}: Erro - {e}")