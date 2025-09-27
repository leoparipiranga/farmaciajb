"""
Interface de alertas de vendas - subpágina do módulo de lojas
"""
import streamlit as st
import duckdb
import pandas as pd
from datetime import date, timedelta
from pathlib import Path
from typing import Callable, Optional

from core.database import duck_query
from data_processing.alertas.alertas import (
    calculate_expected_values,
    detect_volume_anomalies_count,
    detect_identification_anomalies_count,
    detect_cmv_anomalies_count
)
from visualizations.components.alert_components import (
    render_alert_card,
    render_cmv_card,
    render_alert_page_css
)

def render_alertas_duck(
    filial_sel: str,
    on_voltar: Callable[[], None],
    conn: Optional[duckdb.DuckDBPyConnection] = None
) -> None:
    """
    Renderiza a página de alertas de vendas
    
    Args:
        filial_sel: Filial selecionada
        on_voltar: Função callback para voltar à página anterior
        conn: Conexão DuckDB (opcional)
    """
    
    # Header com botão Voltar
    col_back, col_title = st.columns([1, 9])
    with col_back:
        if st.button("⬅ Voltar para Lojas", use_container_width=True):
            on_voltar()
    
    with col_title:
        st.markdown("## 🔔 Central de Alertas")
        st.caption(f"Filial: {filial_sel}")
    
    # Conectar ao DuckDB se não foi passada conexão
    if conn is None:
        db_path = Path("duck_cache/warehouse.duckdb")
        if not db_path.exists():
            st.error(f"❌ Banco de dados não encontrado: {db_path}")
            st.info("Execute o script de importação primeiro.")
            return
        conn = duckdb.connect(str(db_path), read_only=True)
    
    # Verificar estrutura da tabela
    try:
        tables = conn.execute("SHOW TABLES").fetchall()
        if not any('fact_vendas_final' in str(t) for t in tables):
            st.error("❌ Tabela 'fact_vendas_final' não encontrada no banco de dados")
            st.info("Execute refresh_facts_final() para criar a tabela.")
            return
    except Exception as e:
        st.error(f"❌ Erro ao verificar banco de dados: {e}")
        return
    
    # Data de referência (ontem)
    yesterday = date.today() - timedelta(days=1)
    
    # Calcular badges (números de anomalias)
    n_anoms_qtd = detect_volume_anomalies_count(conn, yesterday)
    n_anoms_cli = detect_identification_anomalies_count(conn, yesterday)
    n_anoms_cmv = detect_cmv_anomalies_count(conn, yesterday)
    
    # Aplicar CSS dos cards
    render_alert_page_css(n_anoms_qtd, n_anoms_cli, n_anoms_cmv)
    
    st.caption("Clique em um card para abrir o conteúdo.")
    
    c1, c2, c3 = st.columns([1, 1, 1], gap="large")
    
    # ====== CARD 1: Volume de Vendas ======
    with c1:
        render_volume_alerts_card(conn, yesterday)
    
    # ====== CARD 2: Vendas Identificadas ======
    with c2:
        render_identification_alerts_card(conn, yesterday)
    
    # ====== CARD 3: CMV ======
    with c3:
        render_cmv_alerts_card(conn, yesterday)

def render_volume_alerts_card(conn: duckdb.DuckDBPyConnection, yesterday: date):
    """Renderiza o card completo de alertas de volume"""
    with st.popover("🧮 Volume de Vendas", use_container_width=True):
        st.subheader("📊 Volume de Vendas")
        st.caption("Detecta variações anormais no volume de vendas por categoria")
        
        # Filtros
        colf = st.columns([1, 1, 1.4])
        with colf[0]:
            # Obter lista de filiais
            try:
                filiais_df = conn.execute("""
                    SELECT DISTINCT CAST(filial_codigo AS VARCHAR) as codigo 
                    FROM fact_vendas_final 
                    WHERE filial_codigo IS NOT NULL 
                    ORDER BY codigo
                """).df()
                if not filiais_df.empty:
                    codigos = ["TODAS"] + filiais_df['codigo'].tolist()
                else:
                    codigos = ["TODAS"]
            except Exception as e:
                st.warning(f"Erro ao buscar filiais: {e}")
                codigos = ["TODAS"]
                
            codigo_sel_vol = st.selectbox("Filial", options=codigos, index=0, key="vol_filial")
        
        with colf[1]:
            # Threshold com apenas 4 opções, padrão 50%
            thr_opts = [25, 50, 75, 100]
            thr_pct = st.select_slider(
                "Threshold (±%)", 
                options=thr_opts,
                value=50,  # Padrão 50%
                key="vol_thr"
            )
            thr = thr_pct / 100.0
        
        with colf[2]:
            st.caption(f"Data de avaliação: {yesterday.strftime('%d/%m/%Y')} (ontem)")
        
        # Seleção de níveis - todos selecionados por padrão
        niveis_disponiveis = ["classificacao_n1", "classificacao_n2", "classificacao_n3", "produto_id"]
        niveis_selecionados = st.multiselect(
            "Níveis para análise",
            options=niveis_disponiveis,
            default=niveis_disponiveis,  # Todos selecionados por padrão
            key="vol_niveis"
        )
        
        # Seleção de período
        cols_win = st.columns([1, 2, 1])
        with cols_win[0]:
            periodo_opts = {"Ontem": 1, "Últimos 3 dias": 3, "Últimos 7 dias": 7}
            periodo_label = st.radio("Período", options=list(periodo_opts.keys()), 
                                    index=0, horizontal=True, key="vol_periodo")
            janela_sel = periodo_opts[periodo_label]
        
        with cols_win[2]:
            min_expected = st.slider("Qtd mínima esperada", min_value=10, max_value=100, 
                                    value=20, step=10, key="vol_minexp")
        
        # Calcular e exibir alertas
        st.markdown("#### Resultados")
        st.caption("Mostrando somente anomalias (esperado ≥ mínimo). Verde = acima, Vermelho = abaixo")
        
        codigo_filtro = None if codigo_sel_vol == "TODAS" else codigo_sel_vol
        
        # Lista para acumular todas as anomalias
        todas_anomalias = []
        
        for nivel in niveis_selecionados:
            # Calcular valores esperados vs obtidos
            df_alerts = calculate_expected_values(
                conn, nivel, yesterday, janela_sel, codigo_filtro
            )
            
            if df_alerts.empty:
                continue
            
            # Filtrar por threshold e mínimo esperado
            df_alerts = df_alerts[df_alerts['esperado'] >= min_expected].copy()
            
            # Determinar status
            df_alerts['status'] = 'normal'
            df_alerts.loc[df_alerts['variacao_pct'] >= thr, 'status'] = 'acima'
            df_alerts.loc[df_alerts['variacao_pct'] <= -thr, 'status'] = 'abaixo'
            
            # Filtrar apenas anomalias
            anomalias = df_alerts[df_alerts['status'] != 'normal'].copy()
            
            if not anomalias.empty:
                anomalias['nivel'] = nivel
                todas_anomalias.append(anomalias)
        
        if todas_anomalias:
            # Concatenar todas as anomalias
            df_todas_anomalias = pd.concat(todas_anomalias, ignore_index=True)
            
            # Mapear produto_id para embalagem_descricao
            if 'produto_id' in niveis_selecionados:
                try:
                    # Buscar mapeamento produto_id -> embalagem_descricao
                    mapping_query = """
                    SELECT DISTINCT 
                        CAST(produto_id AS VARCHAR) as produto_id,
                        embalagem_descricao
                    FROM fact_vendas_final
                    WHERE produto_id IS NOT NULL 
                      AND embalagem_descricao IS NOT NULL
                    """
                    df_mapping = conn.execute(mapping_query).df()
                    
                    if not df_mapping.empty:
                        # Criar dicionário de mapeamento
                        produto_mapping = dict(zip(
                            df_mapping['produto_id'].astype(str),
                            df_mapping['embalagem_descricao']
                        ))
                        
                        # Adicionar coluna label para produtos
                        df_todas_anomalias['label'] = df_todas_anomalias.apply(
                            lambda row: produto_mapping.get(str(row['categoria']), str(row['categoria']))
                            if row['nivel'] == 'produto_id' else str(row['categoria']),
                            axis=1
                        )
                    else:
                        df_todas_anomalias['label'] = df_todas_anomalias['categoria'].astype(str)
                except Exception as e:
                    st.warning(f"Erro ao mapear produtos: {e}")
                    df_todas_anomalias['label'] = df_todas_anomalias['categoria'].astype(str)
            else:
                df_todas_anomalias['label'] = df_todas_anomalias['categoria'].astype(str)
            
            # Ordenar por variação percentual (maior para menor)
            df_todas_anomalias = df_todas_anomalias.sort_values('variacao_pct', ascending=False)
            
            # Agrupar por nível para exibição
            for nivel in niveis_selecionados:
                nivel_anomalias = df_todas_anomalias[df_todas_anomalias['nivel'] == nivel]
                
                if not nivel_anomalias.empty:
                    st.markdown(f"**Nível: {nivel}**")
                    
                    # Renderizar cards em grid
                    cols = st.columns(3)
                    for idx, (_, data) in enumerate(nivel_anomalias.iterrows()):
                        with cols[idx % 3]:
                            render_alert_card(
                                categoria=str(data['categoria']),
                                nivel=nivel,
                                janela=int(data['janela']),
                                obtido=float(data['obtido']),
                                esperado=float(data['esperado']),
                                variacao_pct=float(data['variacao_pct']),
                                status=data['status'],
                                label=data.get('label', str(data['categoria']))
                            )
        else:
            st.success("✅ Nenhuma anomalia detectada nos níveis selecionados")


def render_identification_alerts_card(conn: duckdb.DuckDBPyConnection, yesterday: date):
    """Renderiza o card completo de alertas de identificação"""
    with st.popover("👥 Vendas Identificadas", use_container_width=True):
        st.subheader("👥 Vendas Identificadas")
        st.caption("Monitora o percentual de vendas com cliente identificado")
        
        # Filtros
        cols_fil = st.columns([1, 2, 2])
        with cols_fil[0]:
            # Lista de filiais
            try:
                filiais_df = conn.execute("""
                    SELECT DISTINCT CAST(filial_codigo AS VARCHAR) as codigo 
                    FROM fact_vendas_final 
                    WHERE filial_codigo IS NOT NULL 
                    ORDER BY codigo
                """).df()
                if not filiais_df.empty:
                    codigos_cli = ["TODAS"] + filiais_df['codigo'].tolist()
                else:
                    codigos_cli = ["TODAS"]
            except:
                codigos_cli = ["TODAS"]
            
            codigo_sel_cli = st.selectbox("Filial", options=codigos_cli, index=0, key="cli_filial")
        
        with cols_fil[1]:
            # Período de análise
            periodo_opts_cli = {"Ontem": 1, "Últimos 3 dias": 3, "Últimos 7 dias": 7}
            win_label = st.radio("Período", options=list(periodo_opts_cli.keys()), 
                               index=0, horizontal=True, key="cli_win")
            win = periodo_opts_cli[win_label]
        
        with cols_fil[2]:
            st.caption(f"Data referência: {yesterday.strftime('%d/%m/%Y')}")
            st.caption("🔴 <60% | 🟡 60-95% | 🟢 ≥95%")
        
        # Calcular identificação por loja
        st.markdown("#### 🏪 Por Loja")
        
        # Query para calcular vendas identificadas
        filial_filter = f"AND filial_codigo = '{codigo_sel_cli}'" if codigo_sel_cli != "TODAS" else ""
        
        query_loja = f"""
        WITH vendas_periodo AS (
            SELECT 
                COUNT(DISTINCT venda_id) as total_vendas,
                COUNT(DISTINCT CASE WHEN venda_pessoaid IS NOT NULL THEN venda_id END) as vendas_identificadas
            FROM fact_vendas_final
            WHERE data_date > DATE '{yesterday}' - INTERVAL '{win} days'
              AND data_date <= DATE '{yesterday}'
              {filial_filter}
        )
        SELECT 
            total_vendas,
            vendas_identificadas,
            CASE 
                WHEN total_vendas > 0 
                THEN ROUND(vendas_identificadas * 100.0 / total_vendas, 1)
                ELSE 0 
            END as percentual
        FROM vendas_periodo
        """
        
        try:
            result_loja = conn.execute(query_loja).fetchone()
            if result_loja:
                total_vendas, vendas_ident, pct_ident = result_loja
                
                if total_vendas == 0:
                    st.info(f"Sem vendas no período de {win} dia(s)")
                else:
                    # Determinar cor baseado no percentual
                    if pct_ident < 60:
                        st.error(f"🔴 Loja: {pct_ident:.1f}% identificadas ({vendas_ident}/{total_vendas})")
                    elif pct_ident >= 95:
                        st.success(f"🟢 Loja: {pct_ident:.1f}% identificadas ({vendas_ident}/{total_vendas})")
                    else:
                        st.warning(f"🟡 Loja: {pct_ident:.1f}% identificadas ({vendas_ident}/{total_vendas})")
            else:
                st.info("Sem dados para o período")
        except Exception as e:
            st.error(f"Erro ao calcular identificação da loja: {e}")
        
        # Calcular identificação por vendedor
        st.divider()
        st.markdown(f"#### 👤 Por Vendedor (mín. 20 vendas)")
        
        query_vendedores = f"""
        WITH vendas_vendedor AS (
            SELECT 
                vendedor_nome,
                COUNT(DISTINCT venda_id) as total_vendas,
                COUNT(DISTINCT CASE WHEN venda_pessoaid IS NOT NULL THEN venda_id END) as vendas_identificadas
            FROM fact_vendas_final
            WHERE data_date > DATE '{yesterday}' - INTERVAL '{win} days'
              AND data_date <= DATE '{yesterday}'
              AND vendedor_nome IS NOT NULL
              {filial_filter}
            GROUP BY vendedor_nome
            HAVING COUNT(DISTINCT venda_id) >= 20  -- Mínimo de 20 vendas
        )
        SELECT 
            vendedor_nome,
            total_vendas,
            vendas_identificadas,
            ROUND(vendas_identificadas * 100.0 / total_vendas, 1) as percentual
        FROM vendas_vendedor
        ORDER BY percentual DESC
        """
        
        try:
            df_vendedores = conn.execute(query_vendedores).df()
            
            if df_vendedores.empty:
                st.info("Nenhum vendedor com 20+ vendas no período")
            else:
                # Separar vendedores por categoria
                neg_vendedores = df_vendedores[df_vendedores['percentual'] < 60]
                pos_vendedores = df_vendedores[df_vendedores['percentual'] >= 95]
                
                c_neg, c_pos = st.columns(2)
                
                with c_neg:
                    st.markdown("**🔴 Abaixo de 60%**")
                    if neg_vendedores.empty:
                        st.success("✅ Nenhum vendedor abaixo de 60%")
                    else:
                        for _, row in neg_vendedores.iterrows():
                            st.error(
                                f"{row['vendedor_nome']}: {row['percentual']:.1f}% "
                                f"({int(row['vendas_identificadas'])}/{int(row['total_vendas'])})"
                            )
                
                with c_pos:
                    st.markdown("**🟢 Acima de 95%**")
                    if pos_vendedores.empty:
                        st.info("Nenhum vendedor ≥95%")
                    else:
                        for _, row in pos_vendedores.head(5).iterrows():  # Limitar a 5 para não poluir
                            st.success(
                                f"{row['vendedor_nome']}: {row['percentual']:.1f}% "
                                f"({int(row['vendas_identificadas'])}/{int(row['total_vendas'])})"
                            )
                        if len(pos_vendedores) > 5:
                            st.caption(f"... e mais {len(pos_vendedores) - 5} vendedores")
                
                # Estatísticas gerais
                st.divider()
                col_stats = st.columns(3)
                with col_stats[0]:
                    st.metric("Total Vendedores", len(df_vendedores))
                with col_stats[1]:
                    st.metric("Média Identificação", f"{df_vendedores['percentual'].mean():.1f}%")
                with col_stats[2]:
                    st.metric("Vendedores <60%", len(neg_vendedores))
                    
        except Exception as e:
            st.error(f"Erro ao calcular vendedores: {e}")


def render_cmv_alerts_card(conn: duckdb.DuckDBPyConnection, yesterday: date):
    """Renderiza o card completo de alertas de CMV"""
    with st.popover("📊 Custos (CMV)", use_container_width=True):
        st.subheader("💰 Custos (CMV)")
        st.caption("Detecta quando o CMV ultrapassa 75% das vendas")
        
        # Filtros
        cols_cmv = st.columns([1, 3])
        with cols_cmv[0]:
            # Período de análise
            periodo_opts_cmv = {"Ontem": 1, "Últimos 3 dias": 3, "Últimos 7 dias": 7}
            win_cmv_label = st.radio("Período", options=list(periodo_opts_cmv.keys()), 
                                    index=0, horizontal=True, key="cmv_win")
            win_cmv = periodo_opts_cmv[win_cmv_label]
        
        with cols_cmv[1]:
            st.caption(f"Data referência: {yesterday.strftime('%d/%m/%Y')}")
            st.caption("🔴 CMV > 75% | 🟡 CMV 60-75% | 🟢 CMV < 60%")
        
        st.markdown("#### 📊 CMV por Filial")
        st.caption("Mostrando APENAS filiais com CMV > 75%")
        
        # Query para calcular CMV por filial
        query_cmv = f"""
        WITH cmv_periodo AS (
            -- Agregado de todas as filiais
            SELECT 
                'TODAS' as filial,
                SUM(customediototal) as custo_total,
                SUM(item_valortotal) as venda_total
            FROM fact_vendas_final
            WHERE data_date > DATE '{yesterday}' - INTERVAL '{win_cmv} days'
              AND data_date <= DATE '{yesterday}'
              AND customediototal IS NOT NULL
              AND item_valortotal IS NOT NULL
              AND item_valortotal > 0
            
            UNION ALL
            
            -- Por filial
            SELECT 
                CAST(filial_codigo AS VARCHAR) as filial,
                SUM(customediototal) as custo_total,
                SUM(item_valortotal) as venda_total
            FROM fact_vendas_final
            WHERE data_date > DATE '{yesterday}' - INTERVAL '{win_cmv} days'
              AND data_date <= DATE '{yesterday}'
              AND customediototal IS NOT NULL
              AND item_valortotal IS NOT NULL
              AND item_valortotal > 0
              AND filial_codigo IS NOT NULL
            GROUP BY filial_codigo
        )
        SELECT 
            filial,
            custo_total,
            venda_total,
            ROUND((custo_total / venda_total) * 100, 1) as cmv_pct
        FROM cmv_periodo
        WHERE venda_total > 0
        ORDER BY cmv_pct DESC
        """
        
        try:
            df_cmv = conn.execute(query_cmv).df()
            
            if df_cmv.empty:
                st.info("Sem dados para o período")
            else:
                # Filtrar apenas CMV > 75%
                df_cmv_alto = df_cmv[df_cmv['cmv_pct'] > 75]
                
                if df_cmv_alto.empty:
                    st.success("✅ Nenhuma filial com CMV acima de 75%")
                else:
                    # Mostrar primeiro o agregado "TODAS" se estiver acima de 75%
                    todas_row = df_cmv_alto[df_cmv_alto['filial'] == 'TODAS']
                    if not todas_row.empty:
                        row = todas_row.iloc[0]
                        render_cmv_card(
                            filial=row['filial'],
                            cmv_pct=row['cmv_pct'],
                            custo=row['custo_total'],
                            venda=row['venda_total']
                        )
                        st.divider()
                    
                    # Mostrar filiais individuais em grid
                    filiais_individuais = df_cmv_alto[df_cmv_alto['filial'] != 'TODAS']
                    
                    if not filiais_individuais.empty:
                        st.markdown("**Por Filial:**")
                        
                        # Criar grid de 2 colunas para as filiais
                        cols = st.columns(2)
                        for idx, (_, row) in enumerate(filiais_individuais.iterrows()):
                            with cols[idx % 2]:
                                render_cmv_card(
                                    filial=row['filial'],
                                    cmv_pct=row['cmv_pct'],
                                    custo=row['custo_total'],
                                    venda=row['venda_total']
                                )
                
                # Estatísticas gerais
                st.divider()
                st.markdown("#### 📈 Estatísticas Gerais")
                
                # Remover linha "TODAS" para estatísticas de filiais
                df_filiais = df_cmv[df_cmv['filial'] != 'TODAS']
                
                if not df_filiais.empty:
                    col_stats = st.columns(4)
                    with col_stats[0]:
                        st.metric("Total Filiais", len(df_filiais))
                    with col_stats[1]:
                        st.metric("CMV Médio", f"{df_filiais['cmv_pct'].mean():.1f}%")
                    with col_stats[2]:
                        st.metric("CMV Mínimo", f"{df_filiais['cmv_pct'].min():.1f}%")
                    with col_stats[3]:
                        st.metric("CMV Máximo", f"{df_filiais['cmv_pct'].max():.1f}%")
                    
                    # Distribuição por faixas
                    st.markdown("**Distribuição por Faixas:**")
                    col_dist = st.columns(3)
                    with col_dist[0]:
                        baixo = len(df_filiais[df_filiais['cmv_pct'] < 60])
                        st.success(f"🟢 CMV < 60%: {baixo} filiais")
                    with col_dist[1]:
                        medio = len(df_filiais[(df_filiais['cmv_pct'] >= 60) & (df_filiais['cmv_pct'] <= 75)])
                        st.warning(f"🟡 CMV 60-75%: {medio} filiais")
                    with col_dist[2]:
                        alto = len(df_filiais[df_filiais['cmv_pct'] > 75])
                        st.error(f"🔴 CMV > 75%: {alto} filiais")
                
        except Exception as e:
            st.error(f"Erro ao calcular CMV: {e}")