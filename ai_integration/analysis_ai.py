# components_duck/ia_duck.py
import pandas as pd
import streamlit as st
from datetime import date, timedelta, datetime
from core.database import duck_query  # ← IMPORTAR DO NOVO ARQUIVO
from ai_integration.gemini_integration import gerar_insight_gemini  # ← IMPORTAR DO NOVO ARQUIVO
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
from io import BytesIO
import base64
import numpy as np
from scipy import stats
from sklearn.linear_model import LinearRegression


def _calcular_variacoes(df, grupo_col=None):
    """
    Calcula variações percentuais para um DataFrame
    """
    if df.empty or len(df) < 2:
        return {}
    
    if grupo_col:
        # Calcular variações por grupo
        variacoes = {}
        for grupo in df[grupo_col].unique():
            df_grupo = df[df[grupo_col] == grupo].sort_values('data')
            if len(df_grupo) >= 2:
                valor_inicial = df_grupo.iloc[0]['venda']
                valor_final = df_grupo.iloc[-1]['venda']
                variacao = ((valor_final - valor_inicial) / valor_inicial) * 100
                variacoes[grupo] = {
                    'valor_inicial': valor_inicial,
                    'valor_final': valor_final,
                    'variacao_percentual': variacao
                }
        return variacoes
    else:
        # Calcular variação geral
        df_sorted = df.sort_values('data')
        valor_inicial = df_sorted.iloc[0]['venda']
        valor_final = df_sorted.iloc[-1]['venda']
        variacao = ((valor_final - valor_inicial) / valor_inicial) * 100
        
        return {
            'valor_inicial': valor_inicial,
            'valor_final': valor_final,
            'variacao_percentual': variacao
        }

class InsightManager:
    def __init__(self):
        self.cache = {}  # Guarda insights gerados para reutilização
    
    def get_insight(self, popover_type, data, context, level=1, aba_ativa="mes", sel_cls=None, force_refresh=False):
        """Obter insight para um tipo específico de popover"""
        cache_key = f"{popover_type}_{level}_{aba_ativa}_{sel_cls}"
        
        if force_refresh or cache_key not in self.cache:
            if level == 1:
                insight = self._basic_analysis(popover_type, data, aba_ativa, sel_cls)
            else:
                insight = self._ai_analysis(popover_type, data, context, level, aba_ativa, sel_cls)
            
            self.cache[cache_key] = insight
        
        return self.cache[cache_key]
    
    def _basic_analysis(self, popover_type, data, aba_ativa, sel_cls=None):
        """Análise básica que chama a API"""
        if popover_type == "vendas_acumuladas":
            return gerar_insight_vendas_acumuladas(None, aba_ativa, sel_cls=sel_cls)
        
        return "Análise não implementada para este tipo de dados."
    
    def _ai_analysis(self, popover_type, data, context, level, aba_ativa, sel_cls=None):
        """Análise avançada com IA"""
        return gerar_insight_gemini(data, context, level, aba_ativa)

def render_insight_controls(popover_type, data, context, aba_ativa="mes", sel_cls=None, codigo_filial=None):
    """Renderiza controles de insight para qualquer popover"""
    
    # Criar duas colunas: uma para os botões e outra pequena para o lado direito
    col1, col2, col3 = st.columns([8, 1, 1])  # 8:1:1 para posicionar os botões à direita
    
    with col2:
        # Botão Nível 1 (análise simples)
        button_key_1 = f"button_insight_1_{popover_type}_{aba_ativa}_{sel_cls}_{codigo_filial}"
        if st.button("💡", help="Insight Nível 1 (Básico)", use_container_width=True, key=button_key_1):
            show_insight_dialog_from_dict(popover_type, context, aba_ativa, sel_cls, codigo_filial, nivel=1)
    
    with col3:
        # Botão Nível 3 (análise abrangente)
        button_key_3 = f"button_insight_3_{popover_type}_{aba_ativa}_{sel_cls}_{codigo_filial}"
        if st.button("🔥", help="Insight Nível 3 (Abrangente)", use_container_width=True, key=button_key_3):
            show_insight_dialog_from_dict(popover_type, context, aba_ativa, sel_cls, codigo_filial, nivel=3)

@st.dialog("💡 ideIAs", width="large")
def show_insight_dialog_from_dict(popover_type, context, aba_ativa, sel_cls=None, codigo_filial=None, nivel=1):
    """Exibe o insight em um dialog modal com gráfico ACIMA para Nível 3"""
    
    # # Título baseado no nível
    # if nivel == 1:
    #     st.markdown("### 💡 Análise Básica (Nível 1)")
    # elif nivel == 3:
    #     st.markdown("### 🔥 Análise Abrangente (Nível 3)")
    
    # Spinner enquanto gera o insight
    with st.spinner("Analisando dados..."):
        if popover_type == "vendas_acumuladas":
            if nivel == 1:
                insight = gerar_insight_nivel1(codigo_filial, sel_cls, aba_ativa)
                img_base64 = None
            elif nivel == 3:
                insight, img_base64 = gerar_insight_nivel3(codigo_filial, sel_cls, aba_ativa)
            else:
                insight = f"Nível {nivel} ainda não implementado."
                img_base64 = None
        else:
            insight = f"Análise para {popover_type} ainda não implementada."
            img_base64 = None
    
    # ✅ EXIBIR GRÁFICO PRIMEIRO (se disponível)
    if img_base64 and nivel == 3:
        
        st.markdown(
            f'<img src="data:image/png;base64,{img_base64}" style="width:60%; border-radius:10px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">',
            unsafe_allow_html=True
        )
        st.markdown("---")
    
    # Exibir o insight
    # st.markdown("### 📊 Análise Inteligente")
    with st.container():
        st.markdown(
            f"""
            <div style="
                background-color: white; 
                padding: 20px; 
                border-radius: 10px; 
                border: 1px solid #e0e0e0;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                line-height: 1.6;
                color: #333;
            ">
            {insight.replace(chr(10), '<br>')}
            </div>
            """,
            unsafe_allow_html=True
        )
    
    # Botão para fechar
    if st.button("Fechar", type="secondary"):
        st.rerun()


########################################################################
# FUNÇÕES PARA OBTER DADOS DOS POPOVERS
#########################################################################

def preparar_dados_nivel1(filial_codigo=None, sel_cls=None, aba_ativa="mes"):
    """
    Prepara dados do nível 1 - APENAS VENDAS (sem transações/ticket)
    Retorna um dicionário com keys descritivas
    """
    dados = {}
    
    # Determinar contexto atual
    filial_nome = "GERAL" if (filial_codigo is None or filial_codigo == "Todas as Filiais") else f"FILIAL_{filial_codigo}"
    class_nome = "GERAL" if (sel_cls is None or sel_cls == "todas" or sel_cls == "Todas as Classificações") else f"CLASS_{sel_cls.replace(' ', '_').upper()}"
    
    # Datas de referência
    data_ref = date.today() - timedelta(days=1)
    ini_mes = data_ref.replace(day=1)
    ini_4m = (pd.Timestamp(ini_mes) - pd.DateOffset(months=3)).date()
    ini_12m = (pd.Timestamp(ini_mes) - pd.DateOffset(months=11)).date()
    
    # Condições para filtros PRINCIPAL
    cond_loja = "" if (filial_codigo is None or filial_codigo == "Todas as Filiais") else f"AND CAST(filial_codigo AS VARCHAR) = '{filial_codigo}'"
    cond_cls = "" if (sel_cls is None or sel_cls == "todas" or sel_cls == "Todas as Classificações") else f"AND UPPER(TRIM(classificacao_n1)) = '{sel_cls.upper()}'"
    
    # 1. DADOS CONFORME ABA ATIVA - PRINCIPAL (filtros aplicados)
    if aba_ativa == "dia":
        # ✅ DADOS PRINCIPAIS
        sql_principal = f"""
        SELECT CAST(data_date AS DATE) AS data_date, SUM(item_valortotal) AS valor
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{ini_mes}' AND DATE '{data_ref}'
          {cond_loja} {cond_cls}
        GROUP BY 1
        ORDER BY 1
        """
        
        df_principal = duck_query(sql_principal)
        if df_principal is not None and not df_principal.empty:
            df_principal["data_date"] = pd.to_datetime(df_principal["data_date"])
            df_principal["periodo"] = df_principal["data_date"].dt.strftime("%d/%m")
            
            dados[f"{filial_nome}_{class_nome}_DIA_PRINCIPAL"] = {
                "descricao": f"Vendas diárias PRINCIPAL - {filial_nome} - {class_nome}",
                "dados": df_principal,
                "total_vendas": df_principal['valor'].sum(),
                "dias_com_vendas": len(df_principal),
                "media_diaria": df_principal['valor'].mean(),
                "tipo": "principal"
            }
        
        # ✅ DADOS FILIAL 01 (sempre, independente do filtro)
        sql_filial01 = f"""
        SELECT CAST(data_date AS DATE) AS data_date, SUM(item_valortotal) AS valor
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{ini_mes}' AND DATE '{data_ref}'
          AND CAST(filial_codigo AS VARCHAR) = '01'
          {cond_cls}
        GROUP BY 1
        ORDER BY 1
        """
        
        df_filial01 = duck_query(sql_filial01)
        if df_filial01 is not None and not df_filial01.empty:
            df_filial01["data_date"] = pd.to_datetime(df_filial01["data_date"])
            df_filial01["periodo"] = df_filial01["data_date"].dt.strftime("%d/%m")
            
            dados["FILIAL_01_DIA_COMPARACAO"] = {
                "descricao": "Vendas diárias FILIAL 01 (comparação)",
                "dados": df_filial01,
                "total_vendas": df_filial01['valor'].sum(),
                "dias_com_vendas": len(df_filial01),
                "media_diaria": df_filial01['valor'].mean(),
                "tipo": "comparacao_filial"
            }
        
        # ✅ DADOS CLASSIFICAÇÃO SBB (sempre, independente do filtro)
        sql_sbb = f"""
        SELECT CAST(data_date AS DATE) AS data_date, SUM(item_valortotal) AS valor
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{ini_mes}' AND DATE '{data_ref}'
          AND UPPER(TRIM(classificacao_n1)) = 'SBB'
          {cond_loja}
        GROUP BY 1
        ORDER BY 1
        """
        
        df_sbb = duck_query(sql_sbb)
        if df_sbb is not None and not df_sbb.empty:
            df_sbb["data_date"] = pd.to_datetime(df_sbb["data_date"])
            df_sbb["periodo"] = df_sbb["data_date"].dt.strftime("%d/%m")
            
            dados["CLASS_SBB_DIA_COMPARACAO"] = {
                "descricao": "Vendas diárias CLASSIFICAÇÃO SBB (comparação)",
                "dados": df_sbb,
                "total_vendas": df_sbb['valor'].sum(),
                "dias_com_vendas": len(df_sbb),
                "media_diaria": df_sbb['valor'].mean(),
                "tipo": "comparacao_classe"
            }
    
    elif aba_ativa == "dezena":
        # ✅ DADOS PRINCIPAIS
        sql_principal = f"""
        SELECT CAST(data_date AS DATE) AS data_date, SUM(item_valortotal) AS valor
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{ini_4m}' AND DATE '{data_ref}'
          {cond_loja} {cond_cls}
        GROUP BY 1
        """
        
        df_raw_principal = duck_query(sql_principal)
        if df_raw_principal is not None and not df_raw_principal.empty:
            # Processar dezenas
            df_raw_principal["data_date"] = pd.to_datetime(df_raw_principal["data_date"])
            df_raw_principal["ano_mes_str"] = df_raw_principal["data_date"].dt.strftime("%Y-%m")
            dias = df_raw_principal["data_date"].dt.day
            df_raw_principal["dezena"] = pd.cut(dias, bins=[0,10,20,31], labels=["1ª Dezena", "2ª Dezena", "3ª Dezena"], right=True, include_lowest=True)
            
            agg_principal = df_raw_principal.groupby(["ano_mes_str","dezena"], as_index=False)["valor"].sum()
            ordem = ["1ª Dezena","2ª Dezena","3ª Dezena"]
            agg_principal["dezena"] = pd.Categorical(agg_principal["dezena"], categories=ordem, ordered=True)
            agg_principal = agg_principal.sort_values(["ano_mes_str","dezena"]).tail(12)
            agg_principal["dezena_formatada"] = pd.to_datetime(agg_principal["ano_mes_str"]).dt.strftime("%b/%y") + " - " + agg_principal["dezena"].astype(str)
            
            dados[f"{filial_nome}_{class_nome}_DEZENA_PRINCIPAL"] = {
                "descricao": f"Vendas por dezena PRINCIPAL - {filial_nome} - {class_nome}",
                "dados": agg_principal,
                "total_vendas": agg_principal['valor'].sum(),
                "dezenas_com_vendas": len(agg_principal),
                "media_dezena": agg_principal['valor'].mean(),
                "tipo": "principal"
            }
        
        # ✅ DADOS FILIAL 01
        sql_filial01 = f"""
        SELECT CAST(data_date AS DATE) AS data_date, SUM(item_valortotal) AS valor
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{ini_4m}' AND DATE '{data_ref}'
          AND CAST(filial_codigo AS VARCHAR) = '01'
          {cond_cls}
        GROUP BY 1
        """
        
        df_raw_filial01 = duck_query(sql_filial01)
        if df_raw_filial01 is not None and not df_raw_filial01.empty:
            # Processar dezenas
            df_raw_filial01["data_date"] = pd.to_datetime(df_raw_filial01["data_date"])
            df_raw_filial01["ano_mes_str"] = df_raw_filial01["data_date"].dt.strftime("%Y-%m")
            dias = df_raw_filial01["data_date"].dt.day
            df_raw_filial01["dezena"] = pd.cut(dias, bins=[0,10,20,31], labels=["1ª Dezena", "2ª Dezena", "3ª Dezena"], right=True, include_lowest=True)
            
            agg_filial01 = df_raw_filial01.groupby(["ano_mes_str","dezena"], as_index=False)["valor"].sum()
            agg_filial01["dezena"] = pd.Categorical(agg_filial01["dezena"], categories=ordem, ordered=True)
            agg_filial01 = agg_filial01.sort_values(["ano_mes_str","dezena"]).tail(12)
            agg_filial01["dezena_formatada"] = pd.to_datetime(agg_filial01["ano_mes_str"]).dt.strftime("%b/%y") + " - " + agg_filial01["dezena"].astype(str)
            
            dados["FILIAL_01_DEZENA_COMPARACAO"] = {
                "descricao": "Vendas por dezena FILIAL 01 (comparação)",
                "dados": agg_filial01,
                "total_vendas": agg_filial01['valor'].sum(),
                "dezenas_com_vendas": len(agg_filial01),
                "media_dezena": agg_filial01['valor'].mean(),
                "tipo": "comparacao_filial"
            }
        
        # ✅ DADOS CLASSIFICAÇÃO SBB
        sql_sbb = f"""
        SELECT CAST(data_date AS DATE) AS data_date, SUM(item_valortotal) AS valor
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{ini_4m}' AND DATE '{data_ref}'
          AND UPPER(TRIM(classificacao_n1)) = 'SBB'
          {cond_loja}
        GROUP BY 1
        """
        
        df_raw_sbb = duck_query(sql_sbb)
        if df_raw_sbb is not None and not df_raw_sbb.empty:
            # Processar dezenas
            df_raw_sbb["data_date"] = pd.to_datetime(df_raw_sbb["data_date"])
            df_raw_sbb["ano_mes_str"] = df_raw_sbb["data_date"].dt.strftime("%Y-%m")
            dias = df_raw_sbb["data_date"].dt.day
            df_raw_sbb["dezena"] = pd.cut(dias, bins=[0,10,20,31], labels=["1ª Dezena", "2ª Dezena", "3ª Dezena"], right=True, include_lowest=True)
            
            agg_sbb = df_raw_sbb.groupby(["ano_mes_str","dezena"], as_index=False)["valor"].sum()
            agg_sbb["dezena"] = pd.Categorical(agg_sbb["dezena"], categories=ordem, ordered=True)
            agg_sbb = agg_sbb.sort_values(["ano_mes_str","dezena"]).tail(12)
            agg_sbb["dezena_formatada"] = pd.to_datetime(agg_sbb["ano_mes_str"]).dt.strftime("%b/%y") + " - " + agg_sbb["dezena"].astype(str)
            
            dados["CLASS_SBB_DEZENA_COMPARACAO"] = {
                "descricao": "Vendas por dezena CLASSIFICAÇÃO SBB (comparação)",
                "dados": agg_sbb,
                "total_vendas": agg_sbb['valor'].sum(),
                "dezenas_com_vendas": len(agg_sbb),
                "media_dezena": agg_sbb['valor'].mean(),
                "tipo": "comparacao_classe"
            }
    
    elif aba_ativa == "mes":
        # ✅ DADOS PRINCIPAIS
        sql_principal = f"""
        SELECT DATE_TRUNC('month', data_date)::DATE AS mes, SUM(item_valortotal) AS valor
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{ini_12m}' AND DATE '{data_ref}'
          AND DATE_TRUNC('month', data_date) < DATE_TRUNC('month', CURRENT_DATE)
          {cond_loja} {cond_cls}
        GROUP BY 1
        ORDER BY 1
        """
        
        df_principal = duck_query(sql_principal)
        if df_principal is not None and not df_principal.empty:
            df_principal["mes"] = pd.to_datetime(df_principal["mes"])
            df_principal["mes_formatado"] = df_principal["mes"].dt.strftime("%Y-%m")
            df_principal = df_principal.tail(12)
            
            dados[f"{filial_nome}_{class_nome}_MES_PRINCIPAL"] = {
                "descricao": f"Vendas mensais PRINCIPAL - {filial_nome} - {class_nome}",
                "dados": df_principal,
                "total_vendas": df_principal['valor'].sum(),
                "meses_com_vendas": len(df_principal),
                "media_mensal": df_principal['valor'].mean(),
                "tipo": "principal"
            }
        
        # ✅ DADOS FILIAL 01
        sql_filial01 = f"""
        SELECT DATE_TRUNC('month', data_date)::DATE AS mes, SUM(item_valortotal) AS valor
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{ini_12m}' AND DATE '{data_ref}'
          AND DATE_TRUNC('month', data_date) < DATE_TRUNC('month', CURRENT_DATE)
          AND CAST(filial_codigo AS VARCHAR) = '01'
          {cond_cls}
        GROUP BY 1
        ORDER BY 1
        """
        
        df_filial01 = duck_query(sql_filial01)
        if df_filial01 is not None and not df_filial01.empty:
            df_filial01["mes"] = pd.to_datetime(df_filial01["mes"])
            df_filial01["mes_formatado"] = df_filial01["mes"].dt.strftime("%Y-%m")
            df_filial01 = df_filial01.tail(12)
            
            dados["FILIAL_01_MES_COMPARACAO"] = {
                "descricao": "Vendas mensais FILIAL 01 (comparação)",
                "dados": df_filial01,
                "total_vendas": df_filial01['valor'].sum(),
                "meses_com_vendas": len(df_filial01),
                "media_mensal": df_filial01['valor'].mean(),
                "tipo": "comparacao_filial"
            }
        
        # ✅ DADOS CLASSIFICAÇÃO SBB
        sql_sbb = f"""
        SELECT DATE_TRUNC('month', data_date)::DATE AS mes, SUM(item_valortotal) AS valor
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{ini_12m}' AND DATE '{data_ref}'
          AND DATE_TRUNC('month', data_date) < DATE_TRUNC('month', CURRENT_DATE)
          AND UPPER(TRIM(classificacao_n1)) = 'SBB'
          {cond_loja}
        GROUP BY 1
        ORDER BY 1
        """
        
        df_sbb = duck_query(sql_sbb)
        if df_sbb is not None and not df_sbb.empty:
            df_sbb["mes"] = pd.to_datetime(df_sbb["mes"])
            df_sbb["mes_formatado"] = df_sbb["mes"].dt.strftime("%Y-%m")
            df_sbb = df_sbb.tail(12)
            
            dados["CLASS_SBB_MES_COMPARACAO"] = {
                "descricao": "Vendas mensais CLASSIFICAÇÃO SBB (comparação)",
                "dados": df_sbb,
                "total_vendas": df_sbb['valor'].sum(),
                "meses_com_vendas": len(df_sbb),
                "media_mensal": df_sbb['valor'].mean(),
                "tipo": "comparacao_classe"
            }
    
    elif aba_ativa == "ritmo":
        d = data_ref.day
        
        # ✅ DADOS PRINCIPAIS
        sql_principal = f"""
        SELECT CAST(data_date AS DATE) AS data_date, SUM(item_valortotal) AS valor
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{ini_12m}' AND DATE '{data_ref}'
          {cond_loja} {cond_cls}
        GROUP BY 1
        """
        
        df_raw_principal = duck_query(sql_principal)
        if df_raw_principal is not None and not df_raw_principal.empty:
            df_raw_principal["data_date"] = pd.to_datetime(df_raw_principal["data_date"])
            df_raw_principal["ano_mes"] = df_raw_principal["data_date"].dt.to_period("M")
            df_raw_principal["dia"] = df_raw_principal["data_date"].dt.day
            
            df_corte_principal = df_raw_principal[df_raw_principal["dia"] <= d].groupby("ano_mes", as_index=False)["valor"].sum()
            df_corte_principal["periodo"] = df_corte_principal["ano_mes"].astype(str)
            df_corte_principal = df_corte_principal.tail(12)
            
            dados[f"{filial_nome}_{class_nome}_RITMO_PRINCIPAL"] = {
                "descricao": f"Vendas por ritmo PRINCIPAL (até dia {d}) - {filial_nome} - {class_nome}",
                "dados": df_corte_principal,
                "total_vendas": df_corte_principal['valor'].sum(),
                "periodos_com_vendas": len(df_corte_principal),
                "media_periodo": df_corte_principal['valor'].mean(),
                "tipo": "principal"
            }
        
        # ✅ DADOS FILIAL 01
        sql_filial01 = f"""
        SELECT CAST(data_date AS DATE) AS data_date, SUM(item_valortotal) AS valor
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{ini_12m}' AND DATE '{data_ref}'
          AND CAST(filial_codigo AS VARCHAR) = '01'
          {cond_cls}
        GROUP BY 1
        """
        
        df_raw_filial01 = duck_query(sql_filial01)
        if df_raw_filial01 is not None and not df_raw_filial01.empty:
            df_raw_filial01["data_date"] = pd.to_datetime(df_raw_filial01["data_date"])
            df_raw_filial01["ano_mes"] = df_raw_filial01["data_date"].dt.to_period("M")
            df_raw_filial01["dia"] = df_raw_filial01["data_date"].dt.day
            
            df_corte_filial01 = df_raw_filial01[df_raw_filial01["dia"] <= d].groupby("ano_mes", as_index=False)["valor"].sum()
            df_corte_filial01["periodo"] = df_corte_filial01["ano_mes"].astype(str)
            df_corte_filial01 = df_corte_filial01.tail(12)
            
            dados["FILIAL_01_RITMO_COMPARACAO"] = {
                "descricao": f"Vendas por ritmo FILIAL 01 (até dia {d}) - comparação",
                "dados": df_corte_filial01,
                "total_vendas": df_corte_filial01['valor'].sum(),
                "periodos_com_vendas": len(df_corte_filial01),
                "media_periodo": df_corte_filial01['valor'].mean(),
                "tipo": "comparacao_filial"
            }
        
        # ✅ DADOS CLASSIFICAÇÃO SBB
        sql_sbb = f"""
        SELECT CAST(data_date AS DATE) AS data_date, SUM(item_valortotal) AS valor
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{ini_12m}' AND DATE '{data_ref}'
          AND UPPER(TRIM(classificacao_n1)) = 'SBB'
          {cond_loja}
        GROUP BY 1
        """
        
        df_raw_sbb = duck_query(sql_sbb)
        if df_raw_sbb is not None and not df_raw_sbb.empty:
            df_raw_sbb["data_date"] = pd.to_datetime(df_raw_sbb["data_date"])
            df_raw_sbb["ano_mes"] = df_raw_sbb["data_date"].dt.to_period("M")
            df_raw_sbb["dia"] = df_raw_sbb["data_date"].dt.day
            
            df_corte_sbb = df_raw_sbb[df_raw_sbb["dia"] <= d].groupby("ano_mes", as_index=False)["valor"].sum()
            df_corte_sbb["periodo"] = df_corte_sbb["ano_mes"].astype(str)
            df_corte_sbb = df_corte_sbb.tail(12)
            
            dados["CLASS_SBB_RITMO_COMPARACAO"] = {
                "descricao": f"Vendas por ritmo CLASSIFICAÇÃO SBB (até dia {d}) - comparação",
                "dados": df_corte_sbb,
                "total_vendas": df_corte_sbb['valor'].sum(),
                "periodos_com_vendas": len(df_corte_sbb),
                "media_periodo": df_corte_sbb['valor'].mean(),
                "tipo": "comparacao_classe"
            }
    
    return dados

def preparar_prompt_nivel1(dados_dict, aba_ativa):
    """
    Prepara um prompt para análise COMPARATIVA focada em tendências
    """
    # Separar dados por tipo
    dados_principal = {}
    dados_filial01 = {}
    dados_sbb = {}
    
    for key, info in dados_dict.items():
        if info.get('tipo') == 'principal':
            dados_principal[key] = info
        elif info.get('tipo') == 'comparacao_filial':
            dados_filial01[key] = info
        elif info.get('tipo') == 'comparacao_classe':
            dados_sbb[key] = info
    
    prompt = f"""
    ANÁLISE COMPARATIVA DE TENDÊNCIAS - {aba_ativa.upper()}
    
    Você é um analista especializado em farmácias focado em análise de TENDÊNCIAS E COMPARAÇÕES.
    
    DADOS RECEBIDOS:
    
    ### 📊 DADOS PRINCIPAL (BASE DA ANÁLISE):
    """
    
    # Adicionar dados principais
    for key, info in dados_principal.items():
        prompt += f"""
    [{key}]:
    - Descrição: {info['descricao']}
    - Total de Vendas: R$ {info.get('total_vendas', 0):,.2f}
    - Registros: {info['dados']}
    """
    
    # Adicionar dados de comparação FILIAL 01
    if dados_filial01:
        prompt += f"""
    
    ### 🏪 DADOS FILIAL 01 (COMPARAÇÃO):
    """
        for key, info in dados_filial01.items():
            prompt += f"""
    [{key}]:
    - Descrição: {info['descricao']}
    - Total de Vendas: R$ {info.get('total_vendas', 0):,.2f}
    - Registros: {info['dados']}
    """
    
    # Adicionar dados de comparação SBB
    if dados_sbb:
        prompt += f"""
    
    ### 📋 DADOS CLASSIFICAÇÃO SBB (COMPARAÇÃO):
    """
        for key, info in dados_sbb.items():
            prompt += f"""
    [{key}]:
    - Descrição: {info['descricao']}
    - Total de Vendas: R$ {info.get('total_vendas', 0):,.2f}
    - Registros: {info['dados']}
    """
    
    prompt += f"""
    
    INSTRUÇÕES PARA ANÁLISE COMPARATIVA:
    
    1. **FOQUE EM TENDÊNCIAS, NÃO VALORES ABSOLUTOS**:
       - Analise se os dados CRESCERAM, DIMINUÍRAM ou ESTAGNARAM
       - Compare primeiro vs último período de cada conjunto
       - Identifique padrões: crescimento linear, exponencial, sazonalidade, "barriga", etc.
    
    2. **ANÁLISE PRINCIPAL PRIMEIRO**:
       - Comece analisando a tendência dos DADOS PRINCIPAL
       - Calcule a variação percentual do primeiro para o último período
       - Descreva o padrão observado (crescimento, queda, estagnação, sazonalidade)
    
    3. **COMPARAÇÕES CONTEXTUAIS**:
       - Compare FILIAL 01 vs DADOS PRINCIPAL: ela está puxando ou freando?
       - Compare CLASSIFICAÇÃO SBB vs DADOS PRINCIPAL: contribui ou prejudica?
       - Use frases como: "A filial 01 parece puxar o crescimento..." ou "SBB está estagnado..."
    
    4. **FORMATO DA RESPOSTA**:
       - 1º parágrafo: Tendência principal (crescimento/queda %)
       - 2º parágrafo: Análise da Filial 01 em função da principal
       - 3º parágrafo: Análise da Classificação SBB em função da principal
       - 4º parágrafo: Sugestões práticas baseadas nas comparações
       - Máximo 250 palavras
    
    5. **EXEMPLO DO ESTILO ESPERADO**:
       "As vendas têm crescido lentamente, apresentando aumento de 10% nos últimos meses. 
       A filial 01 parece puxar essa fila de crescimento, já que seu faturamento aumentou 18% no mesmo período. 
       A categoria SBB, por outro lado, está praticamente estagnada, tendo crescido apenas 2%."
    
    6. **SUGESTÕES PRÁTICAS**:
       - Se Filial 01 vai bem: estudar e replicar boas práticas
       - Se SBB vai mal: investigar causas e buscar soluções
       - Focar em ações concretas baseadas nas comparações
    
    ANALISE AS TENDÊNCIAS COMPARATIVAS:
    """
    
    return prompt

def gerar_insight_nivel1(filial_codigo=None, sel_cls=None, aba_ativa="mes"):
    """
    Gera insights de Nível 1 usando dicionários estruturados
    """
    try:
        # Preparar dados estruturados
        dados_dict = preparar_dados_nivel1(filial_codigo, sel_cls, aba_ativa)
        
        if not dados_dict:
            return "❌ Nenhum dado encontrado para análise."
        
        # Preparar prompt
        prompt = preparar_prompt_nivel1(dados_dict, aba_ativa)
        
        # Chamar Gemini usando a nova função
        from components_duck.gemini_duck import analisar_dados_gemini
        analise = analisar_dados_gemini(prompt, dados_dict)
        
        return analise
        
    except Exception as e:
        st.error(f"❌ Erro na análise Nível 1: {e}")
        return f"Erro ao gerar análise: {str(e)}"

def preparar_dados_nivel3(filial_codigo=None, sel_cls=None, aba_ativa="mes"):
    """
    Prepara dados do nível 3 - ANÁLISE ABRANGENTE
    Compara GERAL vs TODAS as filiais e TODAS as classificações
    """
    dados = {}
    
    # Datas de referência
    data_ref = date.today() - timedelta(days=1)
    ini_mes = data_ref.replace(day=1)
    ini_4m = (pd.Timestamp(ini_mes) - pd.DateOffset(months=3)).date()
    ini_12m = (pd.Timestamp(ini_mes) - pd.DateOffset(months=11)).date()
    
    # 1. DADOS GERAIS (SEM FILTROS)
    def processar_dados_por_aba(sql_result, aba_ativa):
        """Função auxiliar para processar dados conforme a aba"""
        if sql_result is None or sql_result.empty:
            return None
            
        if aba_ativa == "dia":
            sql_result["data_date"] = pd.to_datetime(sql_result["data_date"])
            sql_result["periodo"] = sql_result["data_date"].dt.strftime("%d/%m")
            return sql_result
            
        elif aba_ativa == "dezena":
            sql_result["data_date"] = pd.to_datetime(sql_result["data_date"])
            sql_result["ano_mes_str"] = sql_result["data_date"].dt.strftime("%Y-%m")
            dias = sql_result["data_date"].dt.day
            sql_result["dezena"] = pd.cut(dias, bins=[0,10,20,31], labels=["1ª Dezena", "2ª Dezena", "3ª Dezena"], right=True, include_lowest=True)
            
            agg = sql_result.groupby(["ano_mes_str","dezena"], as_index=False)["valor"].sum()
            ordem = ["1ª Dezena","2ª Dezena","3ª Dezena"]
            agg["dezena"] = pd.Categorical(agg["dezena"], categories=ordem, ordered=True)
            agg = agg.sort_values(["ano_mes_str","dezena"]).tail(12)
            agg["dezena_formatada"] = pd.to_datetime(agg["ano_mes_str"]).dt.strftime("%b/%y") + " - " + agg["dezena"].astype(str)
            return agg
            
        elif aba_ativa == "mes":
            sql_result["mes"] = pd.to_datetime(sql_result["mes"])
            sql_result["mes_formatado"] = sql_result["mes"].dt.strftime("%Y-%m")
            
            # ✅ CORREÇÃO: EXCLUIR O MÊS ATUAL INCOMPLETO
            mes_atual = pd.Timestamp.now().to_period("M")
            sql_result = sql_result[sql_result["mes"].dt.to_period("M") < mes_atual]
            
            return sql_result.tail(12)
            
        elif aba_ativa == "ritmo":
            d = data_ref.day
            sql_result["data_date"] = pd.to_datetime(sql_result["data_date"])
            sql_result["ano_mes"] = sql_result["data_date"].dt.to_period("M")
            sql_result["dia"] = sql_result["data_date"].dt.day
            
            # Excluir mês atual para ritmo
            mes_atual = pd.Timestamp.now().to_period("M")
            sql_result = sql_result[sql_result["ano_mes"] < mes_atual]
            
            df_corte = sql_result[sql_result["dia"] <= d].groupby("ano_mes", as_index=False)["valor"].sum()
            df_corte["periodo"] = df_corte["ano_mes"].astype(str)
            return df_corte.tail(12)
    
    # Definir consultas SQL base conforme aba ativa
    if aba_ativa == "dia":
        sql_base = f"""
        SELECT CAST(data_date AS DATE) AS data_date, SUM(item_valortotal) AS valor
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{ini_mes}' AND DATE '{data_ref}'
        """
        
    elif aba_ativa == "dezena":
        sql_base = f"""
        SELECT CAST(data_date AS DATE) AS data_date, SUM(item_valortotal) AS valor
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{ini_4m}' AND DATE '{data_ref}'
        """
        
    elif aba_ativa == "mes":
        # ✅ CORREÇÃO: Não incluir o mês atual na consulta SQL
        sql_base = f"""
        SELECT DATE_TRUNC('month', data_date)::DATE AS mes, SUM(item_valortotal) AS valor
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{ini_12m}' AND DATE '{data_ref}'
          AND DATE_TRUNC('month', data_date) < DATE_TRUNC('month', CURRENT_DATE)
        """
        
    elif aba_ativa == "ritmo":
        sql_base = f"""
        SELECT CAST(data_date AS DATE) AS data_date, SUM(item_valortotal) AS valor
        FROM fact_vendas_final
        WHERE data_date BETWEEN DATE '{ini_12m}' AND DATE '{data_ref}'
        """
    
    # 1. DADOS GERAIS
    if aba_ativa in ["dia", "dezena", "ritmo"]:
        sql_geral = sql_base + " GROUP BY 1 ORDER BY 1"
    else:  # mes
        sql_geral = sql_base + " GROUP BY 1 ORDER BY 1"
    
    df_geral = duck_query(sql_geral)
    df_geral_processado = processar_dados_por_aba(df_geral, aba_ativa)
    
    if df_geral_processado is not None:
        dados["GERAL"] = {
            "descricao": f"Vendas {aba_ativa} GERAL (todas filiais, todas classificações)",
            "dados": df_geral_processado,
            "total_vendas": df_geral_processado['valor'].sum(),
            "tipo": "geral"
        }
    
    # 2. DADOS POR FILIAL (todas as filiais, classificação geral)
    sql_filiais = f"""
    SELECT DISTINCT CAST(filial_codigo AS VARCHAR) as filial
    FROM fact_vendas_final 
    WHERE filial_codigo IS NOT NULL
    ORDER BY filial
    """
    df_filiais = duck_query(sql_filiais)
    
    if df_filiais is not None:
        for filial in df_filiais['filial'].tolist():
            if aba_ativa in ["dia", "dezena", "ritmo"]:
                sql_filial = sql_base + f" AND CAST(filial_codigo AS VARCHAR) = '{filial}' GROUP BY 1 ORDER BY 1"
            else:  # mes
                sql_filial = sql_base + f" AND CAST(filial_codigo AS VARCHAR) = '{filial}' GROUP BY 1 ORDER BY 1"
            
            df_filial = duck_query(sql_filial)
            df_filial_processado = processar_dados_por_aba(df_filial, aba_ativa)
            
            if df_filial_processado is not None and not df_filial_processado.empty:
                dados[f"FILIAL_{filial}"] = {
                    "descricao": f"Vendas {aba_ativa} FILIAL {filial} (todas classificações)",
                    "dados": df_filial_processado,
                    "total_vendas": df_filial_processado['valor'].sum(),
                    "tipo": "filial"
                }
    
    # 3. DADOS POR CLASSIFICAÇÃO (filial geral, excluindo 'USO CONSUMO E SERVIÇOS')
    sql_classificacoes = f"""
    SELECT DISTINCT UPPER(TRIM(classificacao_n1)) as classificacao
    FROM fact_vendas_final 
    WHERE classificacao_n1 IS NOT NULL 
      AND UPPER(TRIM(classificacao_n1)) != 'USO CONSUMO E SERVIÇOS'
    ORDER BY classificacao
    """
    df_classificacoes = duck_query(sql_classificacoes)
    
    if df_classificacoes is not None:
        for classificacao in df_classificacoes['classificacao'].tolist():
            if aba_ativa in ["dia", "dezena", "ritmo"]:
                sql_class = sql_base + f" AND UPPER(TRIM(classificacao_n1)) = '{classificacao}' GROUP BY 1 ORDER BY 1"
            else:  # mes
                sql_class = sql_base + f" AND UPPER(TRIM(classificacao_n1)) = '{classificacao}' GROUP BY 1 ORDER BY 1"
            
            df_class = duck_query(sql_class)
            df_class_processado = processar_dados_por_aba(df_class, aba_ativa)
            
            if df_class_processado is not None and not df_class_processado.empty:
                dados[f"CLASS_{classificacao.replace(' ', '_')}"] = {
                    "descricao": f"Vendas {aba_ativa} CLASSIFICAÇÃO {classificacao} (todas filiais)",
                    "dados": df_class_processado,
                    "total_vendas": df_class_processado['valor'].sum(),
                    "tipo": "classificacao"
                }
    
    return dados

def calcular_variacao_percentual(dados_df):
    """Calcula variação percentual entre primeiro e último período"""
    if dados_df is None or dados_df.empty or len(dados_df) < 2:
        return 0
    
    primeiro_valor = dados_df.iloc[0]['valor']
    ultimo_valor = dados_df.iloc[-1]['valor']
    
    if primeiro_valor == 0:
        return 0
    
    return ((ultimo_valor - primeiro_valor) / primeiro_valor) * 100

def preparar_prompt_nivel3(dados_dict, aba_ativa):
    """
    Prepara prompt para análise ABRANGENTE de TODAS as filiais e classificações
    """
    # Separar dados por tipo
    dados_geral = {}
    dados_filiais = {}
    dados_classificacoes = {}
    
    for key, info in dados_dict.items():
        if info.get('tipo') == 'geral':
            dados_geral[key] = info
        elif info.get('tipo') == 'filial':
            dados_filiais[key] = info
        elif info.get('tipo') == 'classificacao':
            dados_classificacoes[key] = info
    
    # Calcular variações para identificar destaques
    variacoes = {}
    
    # Variação geral
    if dados_geral:
        for key, info in dados_geral.items():
            variacao = calcular_variacao_percentual(info['dados'])
            variacoes[key] = {
                'variacao': variacao,
                'total': info['total_vendas'],
                'tipo': 'geral'
            }
    
    # Variações das filiais
    for key, info in dados_filiais.items():
        variacao = calcular_variacao_percentual(info['dados'])
        variacoes[key] = {
            'variacao': variacao,
            'total': info['total_vendas'],
            'tipo': 'filial'
        }
    
    # Variações das classificações
    for key, info in dados_classificacoes.items():
        variacao = calcular_variacao_percentual(info['dados'])
        variacoes[key] = {
            'variacao': variacao,
            'total': info['total_vendas'],
            'tipo': 'classificacao'
        }
    
    prompt = f"""
    ANÁLISE ABRANGENTE NÍVEL 3 - {aba_ativa.upper()}
    
    Você é um analista especializado em identificar DESTAQUES POSITIVOS e NEGATIVOS em uma rede de farmácias.
    
    DADOS RECEBIDOS ({len(dados_dict)} conjuntos):
    
    ### 📊 DADOS GERAL:
    """
    
    # Adicionar dados gerais
    for key, info in dados_geral.items():
        variacao = variacoes[key]['variacao']
        prompt += f"""
    [{key}] - Variação: {variacao:.1f}%
    - Total: R$ {info['total_vendas']:,.2f}
    - Dados: {info['dados']}
    """
    
    # Adicionar dados das filiais
    prompt += f"""
    
    ### 🏪 DADOS DAS FILIAIS ({len(dados_filiais)} filiais):
    """
    for key, info in dados_filiais.items():
        variacao = variacoes[key]['variacao']
        prompt += f"""
    [{key}] - Variação: {variacao:.1f}%
    - Total: R$ {info['total_vendas']:,.2f}
    - Dados: {info['dados']}
    """
    
    # Adicionar dados das classificações
    prompt += f"""
    
    ### 📋 DADOS DAS CLASSIFICAÇÕES ({len(dados_classificacoes)} classificações):
    """
    for key, info in dados_classificacoes.items():
        variacao = variacoes[key]['variacao']
        prompt += f"""
    [{key}] - Variação: {variacao:.1f}%
    - Total: R$ {info['total_vendas']:,.2f}
    - Dados: {info['dados']}
    """
    
    prompt += f"""
    
    INSTRUÇÕES PARA ANÁLISE NÍVEL 3:
    
    1. **IDENTIFIQUE A TENDÊNCIA GERAL PRIMEIRO**:
       - Comece analisando a variação percentual dos DADOS GERAL
       - Descreva se houve crescimento, queda ou estagnação
       - Use esse como BASE para todas as comparações
    
    2. **IDENTIFIQUE ATÉ 4 DESTAQUES PRINCIPAIS**:
       - 2 POSITIVOS: filiais/classificações que mais SUPERARAM a tendência geral
       - 2 NEGATIVOS: filiais/classificações que mais FICARAM ABAIXO da tendência geral
       - Priorize as maiores diferenças percentuais em relação ao geral
    
    3. **CRITÉRIOS PARA DESTAQUE**:
       - POSITIVO: variação muito acima da geral (ex: geral +10%, filial +18%)
       - NEGATIVO: variação muito abaixo da geral (ex: geral +10%, filial -2%)
       - Considere também o volume absoluto (filiais/classificações com maior faturamento)
    
    4. **FORMATO DA RESPOSTA**:
       - 1º parágrafo: Tendência geral da aba {aba_ativa}
       - 2º parágrafo: 2 destaques POSITIVOS (filiais/classificações que mais cresceram)
       - 3º parágrafo: 2 destaques NEGATIVOS (filiais/classificações com pior performance)
       - 4º parágrafo: Sugestões práticas baseadas nos destaques
       - Máximo 300 palavras
    
    5. **EXEMPLO DO ESTILO ESPERADO**:
       "As vendas têm crescido continuamente, apresentando aumento de 10% nos últimos meses. 
       Dentre as filiais, destacam-se a 01 e a 05, que parecem puxar o crescimento, com aumentos de 18% e 15%. 
       Negativamente, destacamos a filial 06 (queda de 2%) e a classificação PRESCRIÇÃO (queda de 5%)."
    
    6. **SUGESTÕES PRÁTICAS**:
       - Estudar e replicar boas práticas dos destaques positivos
       - Investigar causas dos destaques negativos
       - Focar em ações concretas baseadas nos contrastes identificados
    
    ANALISE E IDENTIFIQUE OS DESTAQUES:
    """
    
    return prompt

def gerar_insight_nivel3(filial_codigo=None, sel_cls=None, aba_ativa="mes"):
    """
    Gera insights de Nível 3 - Análise abrangente com CORE ANALYTICS EXPANDIDO
    """
    try:
        # 1. PREPARAR DADOS BÁSICOS (existente)
        dados_dict_basico = preparar_dados_nivel3(filial_codigo, sel_cls, aba_ativa)
        
        if not dados_dict_basico:
            st.error("❌ Nenhum dado encontrado!")
            return "❌ Nenhum dado encontrado para análise abrangente.", None
        
        # 2. EXPANDIR COM MÉTRICAS AVANÇADAS (novo)
        dados_expandidos = expandir_dados_nivel3(dados_dict_basico)
        
        # 3. GERAR GRÁFICO (existente)
        try:
            img_base64 = criar_grafico_comparativo_nivel3(dados_dict_basico, aba_ativa)
        except Exception as e_grafico:
            st.error(f"❌ Erro específico no gráfico: {e_grafico}")
            img_base64 = None
        
        # 4. PREPARAR PROMPT EXPANDIDO (novo)
        prompt = preparar_prompt_nivel3_expandido(dados_expandidos, aba_ativa, img_base64)
        
        # 5. CHAMAR IA
        from components_duck.gemini_duck import analisar_dados_gemini
        analise = analisar_dados_gemini(prompt, dados_expandidos)
        
        return analise, img_base64
        
    except Exception as e:
        st.error(f"❌ Erro geral na análise Nível 3: {e}")
        import traceback
        st.error(f"Traceback: {traceback.format_exc()}")
        return f"Erro ao gerar análise abrangente: {str(e)}", None


# ATUALIZAR A FUNÇÃO EXISTENTE para usar o novo sistema
def gerar_insight_vendas_acumuladas(filial_codigo=None, aba_ativa="mes", nivel=1, sel_cls=None):
    """
    Função de compatibilidade - redireciona para o novo sistema
    """
    if nivel == 1:
        return gerar_insight_nivel1(filial_codigo, sel_cls, aba_ativa)
    else:
        # Para níveis superiores, manter o sistema antigo por enquanto
        st.write("🔄 Níveis 2+ ainda em desenvolvimento com novo sistema de dicionários.")
        return "Níveis 2+ ainda em desenvolvimento com novo sistema de dicionários."

def verificar_dados_combinados(df_combinado):
    """Verifica se o df_combinado tem as colunas necessárias para análise"""
    
    st.write("### 🔍 Verificação dos Dados Combinados")
    
    # Verificar colunas
    colunas_necessarias = ['filial_codigo', 'classificacao_n1', 'tipo_view', 'venda']
    colunas_presentes = [col for col in colunas_necessarias if col in df_combinado.columns]
    colunas_ausentes = [col for col in colunas_necessarias if col not in df_combinado.columns]
    
    st.write(f"✅ Colunas presentes: {', '.join(colunas_presentes)}")
    if colunas_ausentes:
        st.write(f"❌ Colunas ausentes: {', '.join(colunas_ausentes)}")
    
    # Estatísticas por filial
    if 'filial_codigo' in df_combinado.columns:
        # Garantir que seja tratado como string
        df_combinado['filial_codigo'] = df_combinado['filial_codigo'].astype(str)
        filiais = df_combinado['filial_codigo'].unique()
        filiais_ordenadas = sorted([f for f in filiais if f != 'TODAS_FILIAIS']) + ['TODAS_FILIAIS']
        st.write(f"🏪 Filiais disponíveis: {len(filiais)} ({', '.join(filiais_ordenadas)})")
        
        # Mostrar distribuição por filial
        st.write("#### Distribuição por Filial:")
        filial_counts = df_combinado[df_combinado['filial_codigo'] != 'TODAS_FILIAIS']['filial_codigo'].value_counts()
        st.dataframe(filial_counts)
    
    # Estatísticas por classificação
    if 'classificacao_n1' in df_combinado.columns:
        classificacoes = df_combinado['classificacao_n1'].unique()
        classificacoes_ordenadas = sorted([c for c in classificacoes if c != 'TODAS_CLASSIFICACOES']) + ['TODAS_CLASSIFICACOES']
        st.write(f"📋 Classificações disponíveis: {len(classificacoes)} ({', '.join(classificacoes_ordenadas)})")
    
    # Amostra dos dados
    st.write("### 📊 Amostra dos Dados")
    st.dataframe(df_combinado.head(10))
    
    return df_combinado

def _validar_dados_para_ia(dados, aba_ativa):
    """
    Valida se os dados estão corretos antes de enviar para IA
    """
    if dados.empty:
        return False, "Dados vazios"
    
    if len(dados) < 2:
        return False, "Dados insuficientes para análise"
    
    # Verificar se os valores fazem sentido
    valores = dados['venda'].values
    if any(v < 0 for v in valores):
        return False, "Valores negativos detectados"
    
    # Verificar se há variação razoável (não queda de 98%)
    primeiro = valores[0]
    ultimo = valores[-1]
    if primeiro > 0:
        variacao = ((ultimo - primeiro) / primeiro) * 100
        if abs(variacao) > 50:  # Variação maior que 50% pode indicar erro
            return False, f"Variação suspeita: {variacao:.1f}%"
    
    return True, "Dados validados"

def criar_grafico_comparativo_nivel3(dados_dict, aba_ativa):
    """
    Cria gráfico de BARRAS VERTICAIS simples mostrando variação percentual
    Barra GERAL em cor sólida + barras selecionadas com transparência
    """
    try:
        # Verificar se matplotlib está disponível
        try:
            import matplotlib.pyplot as plt
        except ImportError as e:
            return None
        
        # Separar dados por tipo
        dados_geral = {}
        dados_filiais = {}
        dados_classificacoes = {}
        
        for key, info in dados_dict.items():
            if info.get('tipo') == 'geral':
                dados_geral[key] = info
            elif info.get('tipo') == 'filial':
                dados_filiais[key] = info
            elif info.get('tipo') == 'classificacao':
                dados_classificacoes[key] = info
        
        # Calcular variações e identificar destaques
        variacoes = {}
        variacao_geral = 0
        
        # Variação geral
        if dados_geral:
            for key, info in dados_geral.items():
                variacao_geral = calcular_variacao_percentual(info['dados'])
                variacoes[key] = {'variacao': variacao_geral, 'total': info['total_vendas'], 'tipo': 'geral'}
        
        # Variações das filiais
        for key, info in dados_filiais.items():
            variacao = calcular_variacao_percentual(info['dados'])
            variacoes[key] = {'variacao': variacao, 'total': info['total_vendas'], 'tipo': 'filial'}
        
        # Variações das classificações
        for key, info in dados_classificacoes.items():
            variacao = calcular_variacao_percentual(info['dados'])
            variacoes[key] = {'variacao': variacao, 'total': info['total_vendas'], 'tipo': 'classificacao'}
        
        # Identificar destaques (2 melhores e 2 piores)
        filiais_ordenadas = sorted([(k, v) for k, v in variacoes.items() if v['tipo'] == 'filial'], 
                                 key=lambda x: x[1]['variacao'], reverse=True)
        classificacoes_ordenadas = sorted([(k, v) for k, v in variacoes.items() if v['tipo'] == 'classificacao'], 
                                        key=lambda x: x[1]['variacao'], reverse=True)
        
        # Selecionar dados para o gráfico
        dados_para_grafico = []
        
        # 1. SEMPRE INCLUIR GERAL (destaque principal)
        if dados_geral:
            dados_para_grafico.append({
                'nome': 'GERAL',
                'variacao': variacao_geral,
                'tipo': 'geral',
                'cor': '#2E86AB',  # Azul sólido
                'alpha': 1.0,      # Sem transparência
                'destaque': True
            })
        
        # 2. INCLUIR MELHOR E PIOR FILIAL
        if len(filiais_ordenadas) >= 2:
            # Melhor filial
            melhor_filial = filiais_ordenadas[0]
            nome_melhor = melhor_filial[0].replace('FILIAL_', 'Filial ')
            dados_para_grafico.append({
                'nome': nome_melhor,
                'variacao': melhor_filial[1]['variacao'],
                'tipo': 'filial',
                'cor': '#A23B72',  # Rosa/roxo com transparência
                'alpha': 0.7,
                'destaque': False
            })
            
            # Pior filial
            pior_filial = filiais_ordenadas[-1]
            nome_pior = pior_filial[0].replace('FILIAL_', 'Filial ')
            dados_para_grafico.append({
                'nome': nome_pior,
                'variacao': pior_filial[1]['variacao'],
                'tipo': 'filial',
                'cor': '#A23B72',  # Mesma cor, mesma transparência
                'alpha': 0.7,
                'destaque': False
            })
        
        # 3. INCLUIR MELHOR E PIOR CLASSIFICAÇÃO
        if len(classificacoes_ordenadas) >= 2:
            # Melhor classificação
            melhor_class = classificacoes_ordenadas[0]
            nome_melhor_class = melhor_class[0].replace('CLASS_', '').replace('_', ' ')
            dados_para_grafico.append({
                'nome': nome_melhor_class,
                'variacao': melhor_class[1]['variacao'],
                'tipo': 'classificacao',
                'cor': '#F18F01',  # Laranja com transparência
                'alpha': 0.7,
                'destaque': False
            })
            
            # Pior classificação
            pior_class = classificacoes_ordenadas[-1]
            nome_pior_class = pior_class[0].replace('CLASS_', '').replace('_', ' ')
            dados_para_grafico.append({
                'nome': nome_pior_class,
                'variacao': pior_class[1]['variacao'],
                'tipo': 'classificacao',
                'cor': '#F18F01',  # Mesma cor, mesma transparência
                'alpha': 0.7,
                'destaque': False
            })
        
        # Verificar se temos dados suficientes
        if len(dados_para_grafico) == 0:
            return None
        
        # Criar o gráfico de barras
        plt.style.use('default')
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Extrair dados para plotar
        nomes = [item['nome'] for item in dados_para_grafico]
        variacoes_plot = [item['variacao'] for item in dados_para_grafico]
        cores = [item['cor'] for item in dados_para_grafico]
        alphas = [item['alpha'] for item in dados_para_grafico]
        
        # ✅ CORREÇÃO: Criar barras individualmente para diferentes alphas
        bars = []
        for i, (nome, variacao, cor, alpha) in enumerate(zip(nomes, variacoes_plot, cores, alphas)):
            bar = ax.bar(i, variacao, color=cor, alpha=alpha, 
                        edgecolor='white', linewidth=2, width=0.8)
            bars.extend(bar)  # bar retorna lista de patches
        
        # Configurar nomes no eixo X
        ax.set_xticks(range(len(nomes)))
        ax.set_xticklabels(nomes)
        
        # Adicionar valores nas barras
        for i, (bar, variacao) in enumerate(zip(bars, variacoes_plot)):
            height = bar.get_height()
            
            # Posição do texto (acima da barra se positiva, abaixo se negativa)
            y_pos = height + (1 if height >= 0 else -3)
            ha = 'center'
            va = 'bottom' if height >= 0 else 'top'
            
            # Cor do texto (mais escura para geral, padrão para outros)
            text_color = 'black' if dados_para_grafico[i]['destaque'] else '#444444'
            font_weight = 'bold' if dados_para_grafico[i]['destaque'] else 'normal'
            font_size = 12 if dados_para_grafico[i]['destaque'] else 10
            
            ax.text(bar.get_x() + bar.get_width()/2, y_pos, f'{variacao:+.1f}%',
                   ha=ha, va=va, fontweight=font_weight, fontsize=font_size, color=text_color)
        
        # Configurar gráfico
        ax.set_title('Variação de Vendas (%)', fontsize=16, fontweight='bold', pad=20)
        ax.set_ylabel('Variação (%)', fontsize=12)
        
        # Linha horizontal no zero para referência
        ax.axhline(y=0, color='gray', linestyle='-', alpha=0.3, linewidth=1)
        
        # Formatar eixo Y com percentuais
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:+.0f}%'))
        
        # Rotacionar labels do eixo X se necessário
        if len(nomes) > 3:
            plt.xticks(rotation=45, ha='right')
        
        # Grid sutil apenas no eixo Y
        ax.grid(True, axis='y', alpha=0.3, linestyle=':', linewidth=0.5)
        ax.set_axisbelow(True)
        
        # Remover spines superiores e direitas para visual mais limpo
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        # Destacar a barra GERAL com borda mais grossa
        for i, item in enumerate(dados_para_grafico):
            if item['destaque']:
                bars[i].set_linewidth(3)
                bars[i].set_edgecolor('#1a5176')  # Azul mais escuro para a borda
        
        # Ajustar layout
        plt.tight_layout()
        
        # Converter para base64
        try:
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=120, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            buffer.seek(0)
            
            # Codificar em base64
            img_base64 = base64.b64encode(buffer.getvalue()).decode()
            plt.close()
            
            return img_base64
            
        except Exception as e_save:
            plt.close()
            return None
        
    except Exception as e:
        return None

def preparar_prompt_nivel3_com_grafico(dados_dict, aba_ativa, img_base64=None):
    """
    Prepara prompt para análise ABRANGENTE (SEM referência ao gráfico integrado)
    """
    # Usar o prompt padrão sem menções ao gráfico
    prompt = preparar_prompt_nivel3(dados_dict, aba_ativa)
    
    # Apenas adicionar uma nota sobre o gráfico disponível
    if img_base64:
        prompt += f"""
    
    ### 📈 INFORMAÇÃO ADICIONAL:
    Um gráfico comparativo foi gerado mostrando as tendências visuais dos principais destaques vs dados gerais.
    O gráfico será exibido acima da análise para referência visual.
    """
    
    return prompt

def preparar_prompt_nivel3_expandido(dados_expandidos, aba_ativa, img_base64=None):
    """
    Prepara prompt EQUILIBRADO: básico primeiro + padrões complexos selecionados
    """
    
    # 1. EXTRAIR E ORGANIZAR DADOS BÁSICOS
    dados_basicos = dados_expandidos.get("metricas_basicas", {})
    
    # Separar por tipo e calcular variações
    geral_info = None
    filiais_variacoes = []
    classificacoes_variacoes = []
    
    for key, info in dados_basicos.items():
        if 'dados' in info:
            variacao = calcular_variacao_percentual(info['dados'])
            
            if info.get('tipo') == 'geral':
                geral_info = {'nome': key, 'variacao': variacao, 'total': info.get('total_vendas', 0)}
            elif info.get('tipo') == 'filial':
                nome_limpo = key.replace('FILIAL_', 'Filial ')
                filiais_variacoes.append({'nome': nome_limpo, 'variacao': variacao, 'total': info.get('total_vendas', 0)})
            elif info.get('tipo') == 'classificacao':
                nome_limpo = key.replace('CLASS_', '').replace('_', ' ')
                classificacoes_variacoes.append({'nome': nome_limpo, 'variacao': variacao, 'total': info.get('total_vendas', 0)})
    
    # Ordenar por variação para identificar outliers
    filiais_variacoes.sort(key=lambda x: x['variacao'], reverse=True)
    classificacoes_variacoes.sort(key=lambda x: x['variacao'], reverse=True)
    
    # 2. SELECIONAR PADRÕES COMPLEXOS MAIS RELEVANTES
    padroes_complexos_selecionados = []
    
    # Sistema de pontuação para priorizar padrões
    padroes_candidatos = []
    
    # A. PADRÕES DE TENDÊNCIA (com pesos diferenciados)
    if "metricas_tendencia" in dados_expandidos:
        for key, tendencia in dados_expandidos["metricas_tendencia"].items():
            if tendencia and tendencia.get("tipo_tendencia") != "dados_insuficientes":
                peso = 0
                descricao = ""
                
                if tendencia['tipo_tendencia'] == 'barriga':
                    peso = 5  # PESO MÉDIO - padrão não tão crítico
                    nome_entidade = key.replace('FILIAL_', 'Filial ').replace('CLASS_', '').replace('_', ' ')
                    crescimento = tendencia.get('crescimento_ate_pico', 0)
                    queda = tendencia.get('queda_do_pico', 0)
                    descricao = f"PADRÃO BARRIGA: {nome_entidade} cresceu {crescimento:.1f}% mas depois caiu {queda:.1f}%"
                
                elif tendencia['tipo_tendencia'] == 'crescimento_exponencial':
                    peso = 10  # PESO ALTO - crescimento acelerado é importante
                    nome_entidade = key.replace('FILIAL_', 'Filial ').replace('CLASS_', '').replace('_', ' ')
                    descricao = f"CRESCIMENTO EXPONENCIAL: {nome_entidade} em aceleração"
                
                elif tendencia['tipo_tendencia'] == 'estagnacao':
                    peso = 3  # PESO BAIXO - menos prioritário
                    nome_entidade = key.replace('FILIAL_', 'Filial ').replace('CLASS_', '').replace('_', ' ')
                    periodos = tendencia.get('periodos_estagnados', 0)
                    descricao = f"ESTAGNAÇÃO: {nome_entidade} sem crescimento há {periodos} períodos"
                
                if peso > 0:
                    padroes_candidatos.append({
                        'tipo': 'tendencia',
                        'peso': peso,
                        'descricao': descricao,
                        'dados': tendencia
                    })
    
    # B. MUDANÇAS DE MARKET SHARE (peso alto)
    if "metricas_participacao" in dados_expandidos:
        participacao = dados_expandidos["metricas_participacao"]
        
        # Market share de filiais
        if "market_share_filiais" in participacao:
            for key, share_info in participacao["market_share_filiais"].items():
                variacao_share = abs(share_info.get('variacao_share', 0))
                if variacao_share > 2:  # Mudança significativa (>2 pontos)
                    peso = 10  # PESO ALTO
                    nome_entidade = key.replace('FILIAL_', 'Filial ')
                    direcao = "ganhou" if share_info['variacao_share'] > 0 else "perdeu"
                    descricao = f"MUDANÇA MARKET SHARE: {nome_entidade} {direcao} {variacao_share:.1f} pontos de participação"
                    
                    padroes_candidatos.append({
                        'tipo': 'market_share_filial',
                        'peso': peso,
                        'descricao': descricao,
                        'dados': share_info
                    })
        
        # Market share de classificações
        if "market_share_classificacoes" in participacao:
            for key, share_info in participacao["market_share_classificacoes"].items():
                variacao_share = abs(share_info.get('variacao_share', 0))
                if variacao_share > 3:  # Mudança muito significativa (>3 pontos)
                    peso = 10  # PESO MÉDIO-ALTO
                    nome_entidade = key.replace('CLASS_', '').replace('_', ' ')
                    direcao = "ganhou" if share_info['variacao_share'] > 0 else "perdeu"
                    descricao = f"MUDANÇA ESTRUTURAL: {nome_entidade} {direcao} {variacao_share:.1f} pontos de participação"
                    
                    padroes_candidatos.append({
                        'tipo': 'market_share_class',
                        'peso': peso,
                        'descricao': descricao,
                        'dados': share_info
                    })
    
    # C. ANOMALIAS CRÍTICAS (peso muito alto)
    if "anomalias_detectadas" in dados_expandidos and dados_expandidos["anomalias_detectadas"]:
        for anomalia in dados_expandidos["anomalias_detectadas"]:
            z_score = anomalia.get('z_score', 0)
            if z_score > 2:  # Anomalia significativa
                peso = 9  # PESO MUITO ALTO - anomalias são críticas
                descricao = f"ANOMALIA CRÍTICA: {anomalia['descricao']}"
                
                padroes_candidatos.append({
                    'tipo': 'anomalia',
                    'peso': peso,
                    'descricao': descricao,
                    'dados': anomalia
                })
    
    # SELECIONAR OS 2 PADRÕES MAIS RELEVANTES
    padroes_candidatos.sort(key=lambda x: x['peso'], reverse=True)
    padroes_complexos_selecionados = padroes_candidatos[:2]  # Máximo 2
    
    # 3. MONTAR O PROMPT REFORMULADO
    prompt = f"""
    ANÁLISE EXECUTIVA NÍVEL 3 - {aba_ativa.upper()} [HÍBRIDO INTELIGENTE]
    
    Você é um consultor sênior especializado em farmácias, focado em INSIGHTS PRÁTICOS para tomada de decisão.
    
    === DESEMPENHO GERAL E DESTAQUES ===
    
    **VENDAS GERAIS:**
    """
    
    if geral_info:
        prompt += f"""
    - Tendência Geral: {geral_info['variacao']:+.1f}% | Total: R$ {geral_info['total']:,.2f}
    """
    
    prompt += f"""
    
    **TOP PERFORMERS (FILIAIS):**
    """
    
    for i, filial in enumerate(filiais_variacoes[:3], 1):  # Top 3
        emoji = "🏆" if i == 1 else "📈" if filial['variacao'] > 0 else "📉"
        prompt += f"""
    {i}. {emoji} {filial['nome']}: {filial['variacao']:+.1f}% | R$ {filial['total']:,.2f}
    """
    
    prompt += f"""
    
    **CLASSIFICAÇÕES PRINCIPAIS:**
    """
    
    for i, classe in enumerate(classificacoes_variacoes[:3], 1):  # Top 3
        emoji = "⭐" if i == 1 else "📊" if classe['variacao'] > 0 else "⚠️"
        prompt += f"""
    {i}. {emoji} {classe['nome']}: {classe['variacao']:+.1f}% | R$ {classe['total']:,.2f}
    """
    
    # 4. PADRÕES COMPLEXOS SELECIONADOS
    if padroes_complexos_selecionados:
        prompt += f"""
    
    === PADRÕES COMPLEXOS IDENTIFICADOS ===
    
    **OS {len(padroes_complexos_selecionados)} PADRÕES MAIS CRÍTICOS DETECTADOS:**
    """
        
        for i, padrao in enumerate(padroes_complexos_selecionados, 1):
            prompt += f"""
    
    {i}. {padrao['descricao']} (Criticidade: {padrao['peso']}/10)
    """
    
    # 5. INSTRUÇÕES FINAIS REFORMULADAS
    prompt += f"""
    
    === INSTRUÇÕES PARA ANÁLISE EXECUTIVA ===
    
    Gere uma análise CONCISA e ACIONÁVEL seguindo EXATAMENTE esta estrutura:
    
    **ESTRUTURA OBRIGATÓRIA (3 parágrafos):**
    
    **1º PARÁGRAFO - PANORAMA GERAL:**
    - Comece com a tendência geral das vendas ({geral_info['variacao']:+.1f}% se disponível)
    - Destaque 2-3 outliers principais (filiais ou classificações com performance muito diferente)
    - Use linguagem direta: "As vendas cresceram X%, com destaque para..."
    
    **2º PARÁGRAFO - PADRÕES CRÍTICOS:**
    - Foque APENAS nos {len(padroes_complexos_selecionados)} padrões complexos selecionados acima
    - Explique rapidamente o que cada padrão significa para o negócio
    - Priorize por ordem de criticidade (peso mais alto primeiro)
    - Sempre apresente pelo menos dois tipos de padrões diferentes nesse parágrafo. 
    (Selecione dois entre barriga, anomalia, crescimento exponencial, market share e estagnação, 
    priorizando pelo peso).
    Por exemplo, se houve efeito barriga para três filiais, mencione apenas as duas mais críticas
    e traga o tipo seguinte de padrão mais relevante, como mudança de market share para alguma classificação ou filial.
    - INSTRUÇÃO ESPECÍFICA PARA PADRÃO BARRIGA: Questionar se não é efeito da sazonalidade.
    - Este deve ser o maior parágrafo do texto.
    
    **3º PARÁGRAFO - ESTRATÉGIAS E AÇÕES:**
    - Para cada padrão mencionado, sugira UMA ação específica e prática
    - Priorize ações de maior impacto/menor esforço
    - Use linguagem de consultoria: "Recomendo..." ou "Sugiro..."
    
    **CRITÉRIOS DE QUALIDADE:**
    - Máximo 300 palavras total
    - Faça uma mistura de Linguagem executiva (evite jargões técnicos) e tom informal (evite soar como um robô)
    - Foco em AÇÕES, não apenas descrições
    - Seja específico nos números quando relevante
    
    **EXEMPLO DO TOM ESPERADO:**
    "As vendas cresceram 8% no período, com a Filial 05 puxando o crescimento (+18%) enquanto a Filial 02 preocupa (-5%). 
    
    Identificamos dois padrões críticos: a Filial 05 apresenta crescimento exponencial, mas SBB perdeu 6 pontos de participação para Prescrição. 
    
    Recomendo documentar as práticas da Filial 05 para replicar em outras unidades, e investigar por que SBB está perdendo espaço - pode ser mudança no perfil dos clientes ou falta de sortimento."
    
    GERE SUA ANÁLISE EXECUTIVA AGORA:
    """
    
    return prompt

#########################################################################
# FUNÇÕES PARA CÁLCULO DE MÉTRICAS AVANÇADAS (NÍVEL 3 EXPANDIDO)
#########################################################################

def detectar_tipo_tendencia(df_dados):
    """
    Identifica o tipo de tendência em uma série temporal
    Retorna: crescimento_linear, exponencial, estagnacao, barriga, queda
    """
    if df_dados is None or df_dados.empty or len(df_dados) < 3:
        return {
            "tipo_tendencia": "dados_insuficientes",
            "pico_periodo": None,
            "vale_periodo": None,
            "volatilidade": 0,
            "momentum_atual": 0,
            "periodos_estagnados": 0,
            "confianca": 0
        }
    
    valores = df_dados['valor'].values
    periodos = np.arange(len(valores))
    
    # 1. DETECTAR PICOS E VALES
    pico_idx = np.argmax(valores)
    vale_idx = np.argmin(valores)
    
    pico_periodo = df_dados.iloc[pico_idx].get('periodo', df_dados.iloc[pico_idx].name)
    vale_periodo = df_dados.iloc[vale_idx].get('periodo', df_dados.iloc[vale_idx].name)
    
    # 2. CALCULAR VOLATILIDADE (desvio padrão normalizado)
    volatilidade = np.std(valores) / np.mean(valores) if np.mean(valores) > 0 else 0
    
    # 3. DETECTAR ESTAGNAÇÃO
    # Contar períodos consecutivos com variação < 5%
    variacoes = np.diff(valores) / valores[:-1] * 100
    periodos_estagnados = 0
    max_estagnacao = 0
    
    for var in variacoes:
        if abs(var) < 5:  # Variação menor que 5%
            periodos_estagnados += 1
            max_estagnacao = max(max_estagnacao, periodos_estagnados)
        else:
            periodos_estagnados = 0
    
    # 4. CALCULAR MOMENTUM ATUAL (tendência dos últimos 3 períodos)
    if len(valores) >= 3:
        ultimos_3 = valores[-3:]
        x_momentum = np.arange(len(ultimos_3))
        slope_momentum, _, r_value_momentum, _, _ = stats.linregress(x_momentum, ultimos_3)
        momentum_atual = r_value_momentum ** 2  # R² como força da tendência
    else:
        momentum_atual = 0
    
    # 5. DETECTAR TIPO DE TENDÊNCIA
    # Regressão linear geral
    slope, intercept, r_value, p_value, std_err = stats.linregress(periodos, valores)
    r_squared = r_value ** 2
    
    # DETECTAR BARRIGA (crescimento seguido de queda)
    if len(valores) >= 4:
        # Verificar se o pico está no meio (não no início nem no fim)
        if 1 <= pico_idx <= len(valores) - 2:
            crescimento_ate_pico = (valores[pico_idx] - valores[0]) / valores[0] * 100
            queda_do_pico = (valores[-1] - valores[pico_idx]) / valores[pico_idx] * 100
            
            # Critério para barriga: cresceu >10% e depois caiu >5%
            if crescimento_ate_pico > 10 and queda_do_pico < -5:
                return {
                    "tipo_tendencia": "barriga",
                    "pico_periodo": pico_periodo,
                    "vale_periodo": vale_periodo,
                    "volatilidade": volatilidade,
                    "momentum_atual": momentum_atual,
                    "periodos_estagnados": max_estagnacao,
                    "confianca": r_squared,
                    "crescimento_ate_pico": crescimento_ate_pico,
                    "queda_do_pico": queda_do_pico
                }
    
    # DETECTAR ESTAGNAÇÃO
    if max_estagnacao >= 3 or volatilidade < 0.05:
        return {
            "tipo_tendencia": "estagnacao",
            "pico_periodo": pico_periodo,
            "vale_periodo": vale_periodo,
            "volatilidade": volatilidade,
            "momentum_atual": momentum_atual,
            "periodos_estagnados": max_estagnacao,
            "confianca": 1 - volatilidade  # Baixa volatilidade = alta confiança na estagnação
        }
    
    # DETECTAR CRESCIMENTO/QUEDA
    if r_squared > 0.7:  # Tendência forte
        if slope > 0:
            # Verificar se é exponencial
            try:
                # Tentar ajuste exponencial
                log_valores = np.log(valores + 1)  # +1 para evitar log(0)
                slope_exp, _, r_exp, _, _ = stats.linregress(periodos, log_valores)
                
                if r_exp ** 2 > r_squared and slope_exp > slope:
                    tipo = "crescimento_exponencial"
                else:
                    tipo = "crescimento_linear"
            except:
                tipo = "crescimento_linear"
        else:
            tipo = "queda"
    else:
        tipo = "indefinido"
    
    return {
        "tipo_tendencia": tipo,
        "pico_periodo": pico_periodo,
        "vale_periodo": vale_periodo,
        "volatilidade": volatilidade,
        "momentum_atual": momentum_atual,
        "periodos_estagnados": max_estagnacao,
        "confianca": r_squared,
        "slope": slope
    }

def calcular_market_share_evolution(dados_dict):
    """
    Calcula evolução do market share para filiais e classificações
    """
    market_share_filiais = {}
    market_share_classificacoes = {}
    
    # Separar dados por tipo
    dados_filiais = {k: v for k, v in dados_dict.items() if v.get('tipo') == 'filial'}
    dados_classificacoes = {k: v for k, v in dados_dict.items() if v.get('tipo') == 'classificacao'}
    dados_geral = {k: v for k, v in dados_dict.items() if v.get('tipo') == 'geral'}
    
    # Obter total geral para calcular shares
    if dados_geral:
        dados_geral_key = list(dados_geral.keys())[0]
        df_geral = dados_geral[dados_geral_key]['dados']
        
        if not df_geral.empty and len(df_geral) >= 2:
            total_inicial = df_geral.iloc[0]['valor']
            total_final = df_geral.iloc[-1]['valor']
            
            # CALCULAR SHARES DAS FILIAIS
            for key, info in dados_filiais.items():
                df_filial = info['dados']
                if not df_filial.empty and len(df_filial) >= 2:
                    filial_inicial = df_filial.iloc[0]['valor']
                    filial_final = df_filial.iloc[-1]['valor']
                    
                    share_inicial = (filial_inicial / total_inicial) * 100 if total_inicial > 0 else 0
                    share_final = (filial_final / total_final) * 100 if total_final > 0 else 0
                    variacao_share = share_final - share_inicial
                    
                    market_share_filiais[key] = {
                        "share_inicial": share_inicial,
                        "share_final": share_final,
                        "variacao_share": variacao_share,
                        "ganhou_de": [],  # Será preenchido depois
                        "perdeu_para": []  # Será preenchido depois
                    }
            
            # CALCULAR SHARES DAS CLASSIFICAÇÕES
            for key, info in dados_classificacoes.items():
                df_class = info['dados']
                if not df_class.empty and len(df_class) >= 2:
                    class_inicial = df_class.iloc[0]['valor']
                    class_final = df_class.iloc[-1]['valor']
                    
                    share_inicial = (class_inicial / total_inicial) * 100 if total_inicial > 0 else 0
                    share_final = (class_final / total_final) * 100 if total_final > 0 else 0
                    variacao_share = share_final - share_inicial
                    
                    market_share_classificacoes[key] = {
                        "share_inicial": share_inicial,
                        "share_final": share_final,
                        "variacao_share": variacao_share,
                        "substituida_por": [],  # Será preenchido depois
                        "substituiu": []  # Será preenchido depois
                    }
            
            # IDENTIFICAR TRANSFERÊNCIAS DE SHARE
            # Para filiais: quem ganhou/perdeu share
            filiais_ganhadoras = [(k, v) for k, v in market_share_filiais.items() if v['variacao_share'] > 1]
            filiais_perdedoras = [(k, v) for k, v in market_share_filiais.items() if v['variacao_share'] < -1]
            
            for k_ganha, v_ganha in filiais_ganhadoras:
                market_share_filiais[k_ganha]['ganhou_de'] = [k for k, v in filiais_perdedoras]
            
            for k_perde, v_perde in filiais_perdedoras:
                market_share_filiais[k_perde]['perdeu_para'] = [k for k, v in filiais_ganhadoras]
            
            # Para classificações: substituições
            class_ganhadoras = [(k, v) for k, v in market_share_classificacoes.items() if v['variacao_share'] > 2]
            class_perdedoras = [(k, v) for k, v in market_share_classificacoes.items() if v['variacao_share'] < -2]
            
            for k_ganha, v_ganha in class_ganhadoras:
                market_share_classificacoes[k_ganha]['substituiu'] = [k for k, v in class_perdedoras]
            
            for k_perde, v_perde in class_perdedoras:
                market_share_classificacoes[k_perde]['substituida_por'] = [k for k, v in class_ganhadoras]
    
    return {
        "market_share_filiais": market_share_filiais,
        "market_share_classificacoes": market_share_classificacoes
    }

def detectar_anomalias_cruzadas(dados_dict):
    """
    Detecta anomalias onde uma entidade se comporta diferente das outras
    """
    anomalias_detectadas = []
    
    # Separar por tipo
    dados_filiais = {k: v for k, v in dados_dict.items() if v.get('tipo') == 'filial'}
    dados_classificacoes = {k: v for k, v in dados_dict.items() if v.get('tipo') == 'classificacao'}
    
    # DETECTAR ANOMALIAS NAS FILIAIS
    if len(dados_filiais) > 2:  # Precisa de pelo menos 3 filiais para detectar anomalia
        variacoes_filiais = []
        nomes_filiais = []
        
        for key, info in dados_filiais.items():
            variacao = calcular_variacao_percentual(info['dados'])
            variacoes_filiais.append(variacao)
            nomes_filiais.append(key)
        
        if len(variacoes_filiais) > 0:
            # Calcular Z-score
            media_var = np.mean(variacoes_filiais)
            desvio_var = np.std(variacoes_filiais)
            
            if desvio_var > 0:
                for i, (nome, variacao) in enumerate(zip(nomes_filiais, variacoes_filiais)):
                    z_score = abs(variacao - media_var) / desvio_var
                    
                    # Anomalia se Z-score > 2 (muito diferente da média)
                    if z_score > 2:
                        anomalias_detectadas.append({
                            "tipo": "filial_isolada",
                            "entidade": nome,
                            "variacao": variacao,
                            "variacao_media_outras": media_var,
                            "z_score": z_score,
                            "descricao": f"{nome} teve variação de {variacao:.1f}% vs média de {media_var:.1f}% nas outras filiais",
                            "impacto": "alto" if z_score > 3 else "médio",
                            "acao_sugerida": f"Investigar práticas específicas em {nome.replace('FILIAL_', 'Filial ')}"
                        })
    
    # DETECTAR ANOMALIAS NAS CLASSIFICAÇÕES
    if len(dados_classificacoes) > 2:
        variacoes_class = []
        nomes_class = []
        
        for key, info in dados_classificacoes.items():
            variacao = calcular_variacao_percentual(info['dados'])
            variacoes_class.append(variacao)
            nomes_class.append(key)
        
        if len(variacoes_class) > 0:
            media_var = np.mean(variacoes_class)
            desvio_var = np.std(variacoes_class)
            
            if desvio_var > 0:
                for nome, variacao in zip(nomes_class, variacoes_class):
                    z_score = abs(variacao - media_var) / desvio_var
                    
                    if z_score > 2:
                        anomalias_detectadas.append({
                            "tipo": "classificacao_isolada",
                            "entidade": nome,
                            "variacao": variacao,
                            "variacao_media_outras": media_var,
                            "z_score": z_score,
                            "descricao": f"{nome.replace('CLASS_', '').replace('_', ' ')} teve variação de {variacao:.1f}% vs média de {media_var:.1f}% nas outras classificações",
                            "impacto": "alto" if z_score > 3 else "médio",
                            "acao_sugerida": f"Analisar fatores específicos da categoria {nome.replace('CLASS_', '').replace('_', ' ')}"
                        })
    
    return anomalias_detectadas


def expandir_dados_nivel3(dados_dict_basico):
    """
    Expande o dicionário básico com métricas avançadas de tendência,
    participação e anomalias cruzadas
    """
    try:
        # 1. COMEÇAR COM MÉTRICAS BÁSICAS
        dados_expandidos = {
            "metricas_basicas": dados_dict_basico.copy()
        }
        
        # 2. CALCULAR MÉTRICAS DE TENDÊNCIA
        metricas_tendencia = {}
        
        for key, info in dados_dict_basico.items():
            if 'dados' in info and not info['dados'].empty:
                tendencia = detectar_tipo_tendencia(info['dados'])
                metricas_tendencia[key] = tendencia
        
        dados_expandidos["metricas_tendencia"] = metricas_tendencia
        
        # 3. CALCULAR MÉTRICAS DE PARTICIPAÇÃO
        metricas_participacao = calcular_market_share_evolution(dados_dict_basico)
        dados_expandidos["metricas_participacao"] = metricas_participacao
        
        # 4. DETECTAR ANOMALIAS CRUZADAS
        anomalias = detectar_anomalias_cruzadas(dados_dict_basico)
        dados_expandidos["anomalias_detectadas"] = anomalias
        
        # 5. ADICIONAR MÉTRICAS CRUZADAS (placeholder para futuro)
        dados_expandidos["metricas_cruzadas"] = {
            "filial_x_classificacao": {},  # Será implementado em versão futura
            "correlacoes": []  # Será implementado em versão futura
        }
        
        return dados_expandidos
        
    except Exception as e:
        st.error(f"Erro ao expandir dados: {str(e)}")
        # Retornar versão básica se der erro
        return {"metricas_basicas": dados_dict_basico}
    

#########################################################################
# ETAPA 2: PATTERN DISCOVERY ENGINE
#########################################################################

class PatternDiscoveryEngine:
    """
    Motor de descoberta de padrões não-programados
    Analisa dados e identifica automaticamente:
    - Anomalias temporais
    - Mudanças estruturais
    - Correlações ocultas
    - Sazonalidades
    """
    
    def __init__(self, dados_expandidos):
        self.dados = dados_expandidos
        self.padroes_descobertos = {}
    
    def descobrir_todos_padroes(self):
        """Executa todos os detectores de padrões"""
        self.padroes_descobertos = {
            "padroes_barriga_contextuais": self.detectar_padroes_barriga_contextuais(),
            "mudancas_momentum": self.detectar_mudancas_momentum(),
            "correlacoes_ocultas": self.detectar_correlacoes_ocultas(),
            "estagnacoes_criticas": self.detectar_estagnacoes_criticas(),
            "substituicoes_mercado": self.detectar_substituicoes_mercado()
        }
        return self.padroes_descobertos
    
    def detectar_padroes_barriga_contextuais(self):
        """
        Detecta padrões barriga considerando contexto:
        - Volume da entidade
        - Sazonalidade esperada
        - Comparação com pares
        """
        padroes_barriga = []
        
        # Obter dados básicos
        dados_basicos = self.dados.get("metricas_basicas", {})
        tendencias = self.dados.get("metricas_tendencia", {})
        
        # Calcular volumes para contextualizar
        volumes = {k: v.get('total_vendas', 0) for k, v in dados_basicos.items()}
        volume_mediano = np.median(list(volumes.values())) if volumes else 0
        
        for key, tendencia in tendencias.items():
            if tendencia.get('tipo_tendencia') == 'barriga':
                # Obter contexto adicional
                volume_entidade = volumes.get(key, 0)
                crescimento = tendencia.get('crescimento_ate_pico', 0)
                queda = tendencia.get('queda_do_pico', 0)
                
                # ANÁLISE CONTEXTUAL
                relevancia = "baixa"
                contexto = "sazonalidade_possivel"
                
                # Volume alto = mais relevante
                if volume_entidade > volume_mediano * 1.5:
                    relevancia = "alta"
                elif volume_entidade > volume_mediano:
                    relevancia = "media"
                
                # Padrão extremo = menos provável ser sazonalidade
                if abs(crescimento) > 25 or abs(queda) > 15:
                    contexto = "mudanca_estrutural"
                    relevancia = "critica"
                
                # Calcular score de impacto
                score_impacto = self._calcular_score_contexto(
                    volume_entidade, volume_mediano, crescimento, queda
                )
                
                padroes_barriga.append({
                    "entidade": key,
                    "tipo_padrao": "barriga_contextual",
                    "relevancia": relevancia,
                    "contexto_provavel": contexto,
                    "score_impacto": score_impacto,
                    "crescimento_ate_pico": crescimento,
                    "queda_do_pico": queda,
                    "volume_relativo": volume_entidade / volume_mediano if volume_mediano > 0 else 0,
                    "insight": self._gerar_insight_barriga_contextual(key, crescimento, queda, contexto, relevancia),
                    "acao_sugerida": self._gerar_acao_barriga_contextual(key, contexto, relevancia)
                })
        
        # Ordenar por score de impacto
        padroes_barriga.sort(key=lambda x: x['score_impacto'], reverse=True)
        return padroes_barriga[:3]  # Top 3 mais relevantes
    
    def detectar_mudancas_momentum(self):
        """
        Detecta mudanças na aceleração/desaceleração:
        - Crescimento que estava acelerando mas freou
        - Queda que estava se agravando mas estabilizou
        """
        mudancas_momentum = []
        dados_basicos = self.dados.get("metricas_basicas", {})
        
        for key, info in dados_basicos.items():
            df_dados = info.get('dados')
            if df_dados is None or df_dados.empty or len(df_dados) < 4:
                continue
            
            valores = df_dados['valor'].values
            
            # Calcular aceleração em 3 janelas
            if len(valores) >= 6:
                # Primeira metade vs segunda metade
                meio = len(valores) // 2
                primeira_metade = valores[:meio]
                segunda_metade = valores[meio:]
                
                # Tendência de cada metade
                x1 = np.arange(len(primeira_metade))
                x2 = np.arange(len(segunda_metade))
                
                try:
                    slope1, _, r1, _, _ = stats.linregress(x1, primeira_metade)
                    slope2, _, r2, _, _ = stats.linregress(x2, segunda_metade)
                    
                    # Detectar mudança significativa no momentum
                    delta_slope = slope2 - slope1
                    confianca = min(r1**2, r2**2)  # Confiança baseada no menor R²
                    
                    if confianca > 0.5 and abs(delta_slope) > np.std(valores) * 0.1:
                        tipo_mudanca = ""
                        if slope1 > 0 and slope2 < slope1 * 0.5:
                            tipo_mudanca = "desaceleracao_crescimento"
                        elif slope1 < 0 and slope2 > slope1 * 0.5:
                            tipo_mudanca = "atenuacao_queda"
                        elif slope1 > 0 and slope2 > slope1 * 1.5:
                            tipo_mudanca = "aceleracao_crescimento"
                        elif slope1 < 0 and slope2 < slope1 * 1.5:
                            tipo_mudanca = "agravamento_queda"
                        
                        if tipo_mudanca:
                            mudancas_momentum.append({
                                "entidade": key,
                                "tipo_padrao": tipo_mudanca,
                                "slope_inicial": slope1,
                                "slope_final": slope2,
                                "delta_momentum": delta_slope,
                                "confianca": confianca,
                                "score_impacto": abs(delta_slope) * confianca * info.get('total_vendas', 0) / 1000000,
                                "insight": self._gerar_insight_momentum(key, tipo_mudanca, slope1, slope2),
                                "acao_sugerida": self._gerar_acao_momentum(key, tipo_mudanca)
                            })
                
                except Exception:
                    continue
        
        mudancas_momentum.sort(key=lambda x: x['score_impacto'], reverse=True)
        return mudancas_momentum[:2]  # Top 2
    
    def detectar_correlacoes_ocultas(self):
        """
        Detecta correlações entre entidades que não são óbvias:
        - Filial que sempre vai contra a tendência geral
        - Classificação que substitui outra sistematicamente
        """
        correlacoes = []
        dados_basicos = self.dados.get("metricas_basicas", {})
        
        # Obter dados gerais como baseline
        dados_geral = {k: v for k, v in dados_basicos.items() if v.get('tipo') == 'geral'}
        if not dados_geral:
            return correlacoes
        
        geral_key = list(dados_geral.keys())[0]
        geral_valores = dados_geral[geral_key]['dados']['valor'].values
        
        # Analisar correlação de cada entidade com o geral
        for key, info in dados_basicos.items():
            if info.get('tipo') in ['filial', 'classificacao']:
                valores_entidade = info['dados']['valor'].values
                
                # Alinhar tamanhos se necessário
                min_len = min(len(geral_valores), len(valores_entidade))
                if min_len < 3:
                    continue
                
                geral_slice = geral_valores[:min_len]
                entidade_slice = valores_entidade[:min_len]
                
                # Calcular correlação
                try:
                    correlacao, p_value = stats.pearsonr(geral_slice, entidade_slice)
                    
                    # Detectar padrões interessantes
                    tipo_correlacao = ""
                    
                    if correlacao < -0.7 and p_value < 0.05:
                        tipo_correlacao = "contratrend_sistematico"
                    elif correlacao > 0.9 and p_value < 0.05:
                        tipo_correlacao = "follow_leader_perfeito"
                    elif 0.3 < correlacao < 0.7 and p_value < 0.05:
                        tipo_correlacao = "parcialmente_acoplado"
                    
                    if tipo_correlacao:
                        correlacoes.append({
                            "entidade": key,
                            "tipo_padrao": tipo_correlacao,
                            "correlacao": correlacao,
                            "p_value": p_value,
                            "score_impacto": abs(correlacao) * (1 - p_value) * 10,
                            "insight": self._gerar_insight_correlacao(key, tipo_correlacao, correlacao),
                            "acao_sugerida": self._gerar_acao_correlacao(key, tipo_correlacao)
                        })
                
                except Exception:
                    continue
        
        correlacoes.sort(key=lambda x: x['score_impacto'], reverse=True)
        return correlacoes[:2]  # Top 2
    
    def detectar_estagnacoes_criticas(self):
        """
        Detecta estagnações considerando contexto do mercado
        """
        estagnacoes = []
        tendencias = self.dados.get("metricas_tendencia", {})
        dados_basicos = self.dados.get("metricas_basicos", {})
        
        for key, tendencia in tendencias.items():
            if tendencia.get('tipo_tendencia') == 'estagnacao':
                periodos_estagnados = tendencia.get('periodos_estagnados', 0)
                volume = dados_basicos.get(key, {}).get('total_vendas', 0)
                
                # Criticidade baseada em volume e duração
                if periodos_estagnados >= 4 and volume > 500000:  # Alto volume + longa estagnação
                    criticidade = "critica"
                elif periodos_estagnados >= 3:
                    criticidade = "alta"
                else:
                    criticidade = "media"
                
                estagnacoes.append({
                    "entidade": key,
                    "tipo_padrao": "estagnacao_critica",
                    "periodos_estagnados": periodos_estagnados,
                    "criticidade": criticidade,
                    "volume": volume,
                    "score_impacto": periodos_estagnados * (volume / 100000),
                    "insight": f"{key.replace('FILIAL_', 'Filial ').replace('CLASS_', '')} está estagnado há {periodos_estagnados} períodos",
                    "acao_sugerida": self._gerar_acao_estagnacao(key, criticidade)
                })
        
        estagnacoes.sort(key=lambda x: x['score_impacto'], reverse=True)
        return estagnacoes[:2]
    
    def detectar_substituicoes_mercado(self):
        """
        Detecta quando uma categoria/filial cresce às custas de outra
        """
        substituicoes = []
        participacao = self.dados.get("metricas_participacao", {})
        
        # Analisar classificações
        class_shares = participacao.get("market_share_classificacoes", {})
        
        ganhadoras = [(k, v) for k, v in class_shares.items() if v.get('variacao_share', 0) > 3]
        perdedoras = [(k, v) for k, v in class_shares.items() if v.get('variacao_share', 0) < -3]
        
        for k_ganha, v_ganha in ganhadoras:
            for k_perde, v_perde in perdedoras:
                # Verificar se a soma das variações é próxima de zero (transferência)
                soma_variacao = v_ganha['variacao_share'] + v_perde['variacao_share']
                
                if abs(soma_variacao) < 2:  # Transferência direta
                    substituicoes.append({
                        "entidade_ganhadora": k_ganha,
                        "entidade_perdedora": k_perde,
                        "tipo_padrao": "substituicao_direta",
                        "transferencia_share": v_ganha['variacao_share'],
                        "score_impacto": abs(v_ganha['variacao_share']) + abs(v_perde['variacao_share']),
                        "insight": f"{k_ganha.replace('CLASS_', '')} está substituindo {k_perde.replace('CLASS_', '')} ({v_ganha['variacao_share']:+.1f} pontos)",
                        "acao_sugerida": f"Investigar por que clientes migraram de {k_perde.replace('CLASS_', '')} para {k_ganha.replace('CLASS_', '')}"
                    })
        
        substituicoes.sort(key=lambda x: x['score_impacto'], reverse=True)
        return substituicoes[:1]  # Top 1
    
    # MÉTODOS AUXILIARES
    def _calcular_score_contexto(self, volume, volume_mediano, crescimento, queda):
        score = abs(crescimento) + abs(queda)  # Base: magnitude da variação
        
        # Ajustar por volume
        if volume > volume_mediano * 2:
            score *= 1.5
        elif volume > volume_mediano:
            score *= 1.2
        
        # Penalizar padrões que podem ser sazonalidade
        if 10 < abs(crescimento) < 20 and 5 < abs(queda) < 15:
            score *= 0.7  # Pode ser sazonal
        
        return score
    
    def _gerar_insight_barriga_contextual(self, key, crescimento, queda, contexto, relevancia):
        nome = key.replace('FILIAL_', 'Filial ').replace('CLASS_', '').replace('_', ' ')
        
        if contexto == "sazonalidade_possivel":
            return f"{nome} teve padrão barriga ({crescimento:+.1f}% → {queda:+.1f}%) - pode ser sazonalidade"
        else:
            return f"{nome} teve padrão barriga significativo ({crescimento:+.1f}% → {queda:+.1f}%) - mudança estrutural"
    
    def _gerar_acao_barriga_contextual(self, key, contexto, relevancia):
        nome = key.replace('FILIAL_', 'Filial ').replace('CLASS_', '').replace('_', ' ')
        
        if contexto == "sazonalidade_possivel":
            return f"Verificar se padrão de {nome} é sazonal ou estrutural"
        elif relevancia == "critica":
            return f"Investigação urgente em {nome} - mudança estrutural crítica"
        else:
            return f"Monitorar {nome} - padrão preocupante"
    
    def _gerar_insight_momentum(self, key, tipo, slope1, slope2):
        nome = key.replace('FILIAL_', 'Filial ').replace('CLASS_', '').replace('_', ' ')
        
        if tipo == "desaceleracao_crescimento":
            return f"{nome} estava crescendo bem mas perdeu ritmo"
        elif tipo == "atenuacao_queda":
            return f"{nome} estava caindo mas se estabilizou"
        elif tipo == "aceleracao_crescimento":
            return f"{nome} acelerou o crescimento"
        else:
            return f"{nome} teve mudança de momentum"
    
    def _gerar_acao_momentum(self, key, tipo):
        nome = key.replace('FILIAL_', 'Filial ').replace('CLASS_', '').replace('_', ' ')
        
        if tipo == "desaceleracao_crescimento":
            return f"Identificar o que mudou em {nome} para recuperar ritmo"
        elif tipo == "aceleracao_crescimento":
            return f"Documentar práticas de {nome} para replicar"
        else:
            return f"Monitorar evolução de {nome}"
    
    def _gerar_insight_correlacao(self, key, tipo, correlacao):
        nome = key.replace('FILIAL_', 'Filial ').replace('CLASS_', '').replace('_', ' ')
        
        if tipo == "contratrend_sistematico":
            return f"{nome} sempre vai contra a tendência geral (correlação: {correlacao:.2f})"
        elif tipo == "follow_leader_perfeito":
            return f"{nome} segue perfeitamente a tendência geral (correlação: {correlacao:.2f})"
        else:
            return f"{nome} tem correlação parcial com geral (correlação: {correlacao:.2f})"
    
    def _gerar_acao_correlacao(self, key, tipo):
        nome = key.replace('FILIAL_', 'Filial ').replace('CLASS_', '').replace('_', ' ')
        
        if tipo == "contratrend_sistematico":
            return f"Investigar por que {nome} sempre vai contra a tendência"
        elif tipo == "follow_leader_perfeito":
            return f"Usar {nome} como indicador confiável da tendência geral"
        else:
            return f"Analisar fatores específicos que influenciam {nome}"
    
    def _gerar_acao_estagnacao(self, key, criticidade):
        nome = key.replace('FILIAL_', 'Filial ').replace('CLASS_', '').replace('_', ' ')
        
        if criticidade == "critica":
            return f"Ação imediata necessária para reativar {nome}"
        else:
            return f"Plano de reativação para {nome}"

def priorizar_padroes_descobertos(padroes_descobertos):
    """
    Prioriza padrões por impacto no negócio usando score dinâmico
    """
    todos_padroes = []
    
    # Coletar todos os padrões com seus scores
    for tipo_padrao, lista_padroes in padroes_descobertos.items():
        for padrao in lista_padroes:
            padrao['categoria_descoberta'] = tipo_padrao
            todos_padroes.append(padrao)
    
    # Ordenar por score de impacto
    todos_padroes.sort(key=lambda x: x.get('score_impacto', 0), reverse=True)
    
    # Retornar top 3 mais importantes
    return todos_padroes[:3]

def gerar_insight_nivel3_hibrido(filial_codigo=None, sel_cls=None, aba_ativa="mes"):
    """
    Versão híbrida que combina Core Analytics (Etapa 1) + Pattern Discovery (Etapa 2)
    """
    try:
        # ETAPA 1: Core Analytics (atual)
        dados_dict = preparar_dados_nivel3(filial_codigo, sel_cls, aba_ativa)
        if not dados_dict:
            return "❌ Nenhum dado encontrado para análise híbrida.", None
        
        dados_expandidos = expandir_dados_nivel3(dados_dict)
        
        # ETAPA 2: Pattern Discovery (novo)
        engine = PatternDiscoveryEngine(dados_expandidos)
        padroes = engine.descobrir_todos_padroes()
        padroes_prioritarios = priorizar_padroes_descobertos(padroes)
        
        # Gerar gráfico (atual)
        try:
            img_base64 = criar_grafico_comparativo_nivel3(dados_dict, aba_ativa)
        except Exception as e_grafico:
            st.error(f"❌ Erro no gráfico: {e_grafico}")
            img_base64 = None
        
        # Combinar para prompt híbrido
        prompt_hibrido = preparar_prompt_hibrido(dados_expandidos, padroes_prioritarios, aba_ativa)
        
        # Chamar IA para gerar narrativa final
        from components_duck.gemini_duck import analisar_dados_gemini
        analise = analisar_dados_gemini(prompt_hibrido, dados_expandidos)
        
        return analise, img_base64
        
    except Exception as e:
        st.error(f"❌ Erro na análise híbrida: {e}")
        import traceback
        st.error(f"Traceback: {traceback.format_exc()}")
        return f"Erro ao gerar análise híbrida: {str(e)}", None

def preparar_prompt_hibrido(dados_expandidos, padroes_prioritarios, aba_ativa):
    """
    Combina métricas core com padrões descobertos automaticamente
    """
    # Usar base do prompt expandido atual
    prompt_base = preparar_prompt_nivel3_expandido(dados_expandidos, aba_ativa)
    
    # Adicionar seção de padrões descobertos
    if padroes_prioritarios:
        prompt_hibrido = prompt_base + f"""
    
    === PADRÕES DESCOBERTOS AUTOMATICAMENTE ===
    
    **TOP {len(padroes_prioritarios)} DESCOBERTAS MAIS IMPORTANTES:**
    """
        
        for i, padrao in enumerate(padroes_prioritarios, 1):
            score = padrao.get('score_impacto', 0)
            tipo = padrao.get('categoria_descoberta', 'desconhecido')
            insight = padrao.get('insight', 'Sem insight disponível')
            acao = padrao.get('acao_sugerida', 'Investigar')
            
            prompt_hibrido += f"""
    
    {i}. {insight}
       - Categoria: {tipo.replace('_', ' ').title()}
       - Score de Impacto: {score:.1f}
       - Ação Sugerida: {acao}
    """
        
        prompt_hibrido += """
    
    **INSTRUÇÕES PARA ANÁLISE HÍBRIDA:**
    1. Combine as métricas básicas com os padrões descobertos automaticamente
    2. Priorize os padrões com maior score de impacto
    3. Use as descobertas automáticas para dar profundidade à análise
    4. Mantenha foco em ações práticas baseadas nas descobertas mais relevantes
    5. Se houver padrões de "barriga", questione sempre se pode ser sazonalidade
    
    GERE SUA ANÁLISE HÍBRIDA FINAL:
    """
    else:
        prompt_hibrido = prompt_base + """
    
    === PADRÕES DESCOBERTOS ===
    Nenhum padrão crítico foi descoberto automaticamente. Foque na análise das métricas básicas.
    """
    
    return prompt_hibrido

# ATUALIZAR A FUNÇÃO PRINCIPAL PARA USAR VERSÃO HÍBRIDA
def gerar_insight_nivel3_original(filial_codigo=None, sel_cls=None, aba_ativa="mes"):
    """Versão original da Etapa 1 (backup)"""
    return gerar_insight_nivel3_expandido_original(filial_codigo, sel_cls, aba_ativa)

# Renomear função atual para backup
gerar_insight_nivel3_expandido_original = gerar_insight_nivel3

# Substituir por versão híbrida
gerar_insight_nivel3 = gerar_insight_nivel3_hibrido


def preparar_prompt_narrativa_inteligente(dados_expandidos, padroes_prioritarios, aba_ativa):
    """
    Prepara prompt INTELIGENTE para IA gerar narrativa contextualizada
    (SEM templates fixos - deixa a IA criar livremente)
    """
    
    # 1. CONTEXTO DOS DADOS BÁSICOS
    dados_basicos = dados_expandidos.get("metricas_basicas", {})
    
    # Extrair informações gerais
    geral_info = None
    filiais_info = []
    classificacoes_info = []
    
    for key, info in dados_basicos.items():
        variacao = calcular_variacao_percentual(info['dados'])
        
        if info.get('tipo') == 'geral':
            geral_info = {'nome': key, 'variacao': variacao, 'total': info.get('total_vendas', 0)}
        elif info.get('tipo') == 'filial':
            nome_limpo = key.replace('FILIAL_', 'Filial ')
            filiais_info.append({'nome': nome_limpo, 'variacao': variacao, 'total': info.get('total_vendas', 0)})
        elif info.get('tipo') == 'classificacao':
            nome_limpo = key.replace('CLASS_', '').replace('_', ' ')
            classificacoes_info.append({'nome': nome_limpo, 'variacao': variacao, 'total': info.get('total_vendas', 0)})
    
    # Ordenar por performance
    filiais_info.sort(key=lambda x: x['variacao'], reverse=True)
    classificacoes_info.sort(key=lambda x: x['variacao'], reverse=True)
    
    # 2. MONTAR PROMPT INTELIGENTE PARA IA
    prompt = f"""
    ANÁLISE EXECUTIVA FARMACÊUTICA - NÍVEL 3 AVANÇADO
    PERÍODO: {aba_ativa.upper()}
    
    Você é um consultor sênior especializado em farmácias com 15 anos de experiência. 
    Sua missão é transformar dados complexos em insights acionáveis para o dono da farmácia.
    
    ═══════════════════════════════════════════════════════════════
    📊 DADOS CONSOLIDADOS PARA ANÁLISE
    ═══════════════════════════════════════════════════════════════
    
    ## PERFORMANCE GERAL:
    """
    
    if geral_info:
        prompt += f"""
    - Tendência Geral: {geral_info['variacao']:+.1f}%
    - Faturamento Total: R$ {geral_info['total']:,.2f}
    """
    
    prompt += f"""
    
    ## TOP 5 FILIAIS (por performance):
    """
    for i, filial in enumerate(filiais_info[:5], 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "📊"
        prompt += f"""
    {emoji} {filial['nome']}: {filial['variacao']:+.1f}% | R$ {filial['total']:,.2f}
    """
    
    prompt += f"""
    
    ## TOP 5 CLASSIFICAÇÕES (por performance):
    """
    for i, classe in enumerate(classificacoes_info[:5], 1):
        emoji = "⭐" if i == 1 else "📈" if classe['variacao'] > 0 else "📉"
        prompt += f"""
    {emoji} {classe['nome']}: {classe['variacao']:+.1f}% | R$ {classe['total']:,.2f}
    """
    
    # 3. ADICIONAR PADRÕES DESCOBERTOS (se houver)
    if padroes_prioritarios:
        prompt += f"""
    
    ═══════════════════════════════════════════════════════════════
    🔍 PADRÕES CRÍTICOS IDENTIFICADOS AUTOMATICAMENTE
    ═══════════════════════════════════════════════════════════════
    
    O sistema de IA detectou {len(padroes_prioritarios)} padrões importantes:
    """
        
        for i, padrao in enumerate(padroes_prioritarios, 1):
            score = padrao.get('score_impacto', 0)
            insight = padrao.get('insight', 'Padrão detectado')
            acao = padrao.get('acao_sugerida', 'Investigar')
            
            criticidade = "🔴 CRÍTICO" if score >= 8 else "🟡 IMPORTANTE" if score >= 5 else "🔵 OBSERVAR"
            
            prompt += f"""
    
    {i}. {criticidade} - Score: {score:.1f}/10
       Descoberta: {insight}
       Ação Sugerida: {acao}
    """
    
    # 4. INSTRUÇÕES INTELIGENTES PARA A IA
    prompt += f"""
    
    ═══════════════════════════════════════════════════════════════
    🎯 SUAS INSTRUÇÕES COMO CONSULTOR ESPECIALISTA
    ═══════════════════════════════════════════════════════════════
    
    ## CONTEXTO DO CLIENTE:
    - Dono de rede de farmácias
    - Precisa de insights PRÁTICOS e ACIONÁVEIS
    - Tempo limitado (prefere análises concisas)
    - Foco em ROI e resultados mensuráveis
    
    ## SUA MISSÃO:
    Analise todos os dados acima e gere um relatório executivo que responda:
    
    1. **QUAL É O CENÁRIO REAL?** 
       - Onde estamos? (performance geral)
       - Quem está indo bem/mal? (destaques positivos e negativos)
    
    2. **O QUE ESTÁ ACONTECENDO DE DIFERENTE?**
       - Analise os padrões críticos detectados
       - Explique o que cada padrão significa na prática
       - Contextualize com conhecimento farmacêutico
    
    3. **O QUE FAZER AGORA?**
       - 2-3 ações específicas e priorizadas
       - Foque no que tem maior impacto vs menor esforço
       - Seja específico (quem, o que, quando)
    
    ## DIRETRIZES DE COMUNICAÇÃO:
    - Linguagem executiva MAS acessível (evite jargões)
    - Tom consultivo e propositivo
    - Use números específicos quando relevante
    - Máximo 400 palavras
    - Estruture em 3 blocos claros: Cenário + Descobertas + Ações
    
    ## CONHECIMENTO SETORIAL PARA USAR:
    - Sazonalidade farmacêutica (inverno = antigripais, etc)
    - Margem típica: Prescrição ~28%, Genéricos ~35%, Perfumaria ~45%
    - Crescimento saudável: 8-12% ao ano
    - Prescrição geralmente representa 60-70% do faturamento
    - Padrões "barriga" podem ser sazonais ou estruturais
    
    ## EXEMPLO DO TOM ESPERADO:
    "A rede cresceu 12% no período, puxada principalmente pela Filial 03 (+28%). 
    Preocupa a Filial 01, que caiu 8% e está perdendo participação. 
    
    O sistema detectou um padrão crítico: SBB perdeu 6 pontos de market share para Prescrição, 
    sugerindo mudança no perfil dos clientes ou maior procura por medicamentos prescritos.
    
    Recomendo três ações imediatas: 1) Investigar causas da queda na Filial 01, 
    2) Replicar práticas da Filial 03 nas demais, e 3) Ajustar mix da categoria SBB 
    para acompanhar a migração dos clientes."
    
    ═══════════════════════════════════════════════════════════════
    
    AGORA GERE SUA ANÁLISE EXECUTIVA COMO CONSULTOR ESPECIALISTA:
    """
    
    return prompt

# FUNÇÃO PRINCIPAL CORRIGIDA (VERSÃO INTELIGENTE)
def gerar_insight_nivel3_narrativa_inteligente(filial_codigo=None, sel_cls=None, aba_ativa="mes"):
    """
    Versão INTELIGENTE que usa IA para gerar narrativas (NÃO templates fixos)
    """
    try:
        # ETAPA 1: Core Analytics
        dados_dict = preparar_dados_nivel3(filial_codigo, sel_cls, aba_ativa)
        if not dados_dict:
            return "❌ Nenhum dado encontrado para análise narrativa.", None
        
        dados_expandidos = expandir_dados_nivel3(dados_dict)
        
        # ETAPA 2: Pattern Discovery
        engine = PatternDiscoveryEngine(dados_expandidos)
        padroes = engine.descobrir_todos_padroes()
        padroes_prioritarios = priorizar_padroes_descobertos(padroes)
        
        # ETAPA 3: PROMPT INTELIGENTE PARA IA (NÃO templates)
        prompt_narrativa = preparar_prompt_narrativa_inteligente(
            dados_expandidos, 
            padroes_prioritarios, 
            aba_ativa
        )
        
        # CHAMAR IA COM PROMPT INTELIGENTE
        from components_duck.gemini_duck import analisar_dados_gemini
        analise_ia = analisar_dados_gemini(prompt_narrativa, dados_expandidos)
        
        # Gerar gráfico
        try:
            img_base64 = criar_grafico_comparativo_nivel3(dados_dict, aba_ativa)
        except Exception as e_grafico:
            st.error(f"❌ Erro no gráfico: {e_grafico}")
            img_base64 = None
        
        return analise_ia, img_base64
        
    except Exception as e:
        st.error(f"❌ Erro na análise narrativa: {e}")
        import traceback
        st.error(f"Traceback: {traceback.format_exc()}")
        return f"Erro ao gerar análise narrativa: {str(e)}", None

# SUBSTITUIR A FUNÇÃO PRINCIPAL
gerar_insight_nivel3 = gerar_insight_nivel3_narrativa_inteligente

#########################################################################
# CONTEXTO FARMACÊUTICO - BASE DE CONHECIMENTO CONSULTIVA
#########################################################################

class ContextoFarmaceutico:
    """
    Base de conhecimento farmacêutico atualizável
    Serve como CONSULTORIA OPCIONAL para a IA, não como regra obrigatória
    """
    
    def __init__(self):
        self.conhecimento_setor = {
            "sazonalidades": {
                "verao": {
                    "categorias": ["PROTETOR SOLAR", "HIDRATANTES", "REPELENTES", "BRONZEADORES"],
                    "periodo": "Dezembro-Fevereiro",
                    "impacto_esperado": "+15% a +30%",
                    "observacoes": "Pico em dezembro/janeiro. Atenção para entrada antecipada (outubro/novembro)"
                },
                "inverno": {
                    "categorias": ["ANTIGRIPAIS", "VITAMINAS", "XAROPES", "DESCONGESTIONANTES"],
                    "periodo": "Junho-Agosto",
                    "impacto_esperado": "+20% a +40%",
                    "observacoes": "Maior pico em junho/julho. Categoria mais previsível"
                },
                "volta_aulas": {
                    "categorias": ["VITAMINAS", "PARASITOSES", "SUPLEMENTOS INFANTIS"],
                    "periodo": "Janeiro-Março",
                    "impacto_esperado": "+10% a +25%",
                    "observacoes": "Foco em produtos infantis. Campanhas educativas funcionam"
                },
                "fim_ano": {
                    "categorias": ["PERFUMARIA", "COSMÉTICOS", "PRESENTES", "KITS"],
                    "periodo": "Outubro-Dezembro",
                    "impacto_esperado": "+25% a +50%",
                    "observacoes": "Maior sazonalidade. Require planejamento de estoque antecipado"
                }
            },
            
            "drivers_categoria": {
                "PRESCRIÇÃO": {
                    "fatores_criticos": ["Proximidade de clínicas", "Médicos parceiros", "Convênios ativos", "Estoque sempre disponível"],
                    "margem_tipica": "25-30%",
                    "participacao_ideal": "60-70%",
                    "riscos": ["Ruptura de estoque", "Vencimento próximo", "Relacionamento médico"],
                    "oportunidades": ["Novos convênios", "Parcerias médicas", "Programa de fidelidade"]
                },
                "INDICAÇÃO": {
                    "fatores_criticos": ["Preço competitivo", "Orientação farmacêutica ativa", "Conscientização do cliente"],
                    "margem_tipica": "30-40%",
                    "participacao_ideal": "15-25%",
                    "riscos": ["Guerra de preços", "Resistência do consumidor"],
                    "oportunidades": ["Educação sobre equivalência", "Programas de desconto"]
                },
                "SBB": {
                    "fatores_criticos": ["Mix variado", "Exposição adequada", "Promoções regulares", "Disponibilidade constante"],
                    "margem_tipica": "35-45%",
                    "participacao_ideal": "10-20%",
                    "riscos": ["Concorrência supermercados", "Margem baixa"],
                    "oportunidades": ["Cross-selling", "Produtos exclusivos", "Conveniência"]
                },
                "PERFUMARIA": {
                    "fatores_criticos": ["Datas comemorativas", "Lançamentos", "Exposição visual atrativa", "Demonstração/teste"],
                    "margem_tipica": "40-55%",
                    "participacao_ideal": "8-15%",
                    "riscos": ["Alto investimento", "Sazonalidade extrema", "Produtos sensíveis"],
                    "oportunidades": ["Eventos especiais", "Parcerias com marcas", "Consultoria de beleza"]
                }
            },
            
            "benchmarks_setor": {
                "crescimento": {
                    "anual_saudavel": "8-12%",
                    "mensal_normal": "0.5-1.0%",
                    "trimestral_bom": "2-3%",
                    "observacoes": "Farmácias crescem acima da inflação + envelhecimento populacional"
                },
                "participacao_mercado": {
                    "prescricao_ideal": "60-70%",
                    "genericos_ideal": "15-25%",
                    "sbb_ideal": "10-20%",
                    "perfumaria_ideal": "5-15%",
                    "observacoes": "Varia por região e perfil socioeconômico"
                },
                "indicadores_alerta": {
                    "estagnacao_preocupante": "> 3 meses sem crescimento",
                    "queda_critica": "> 10% em qualquer categoria principal",
                    "volatilidade_alta": "> 20% variação mês a mês",
                    "market_share_loss": "> 5 pontos perdidos"
                }
            },
            
            "padroes_tipicos": {
                "barriga_sazonal": {
                    "quando_normal": "Dezembro/Janeiro (fim de ano) ou Junho/Julho (inverno)",
                    "quando_preocupante": "Outros períodos sem justificativa sazonal",
                    "acao_recomendada": "Investigar causas se fora da sazonalidade esperada"
                },
                "crescimento_sustentavel": {
                    "caracteristicas": ["Crescimento gradual 8-12% ao ano", "Baixa volatilidade", "Aumento em múltiplas categorias"],
                    "alertas": ["Crescimento > 30% (pode ser insustentável)", "Crescimento concentrado em 1 categoria"]
                },
                "substituicao_normal": {
                    "prescricao_para_genericos": "Normal se acompanhado de orientação farmacêutica",
                    "sbb_para_perfumaria": "Normal em períodos sazonais",
                    "alertas": "Substituições muito rápidas podem indicar problemas de estoque ou preço"
                }
            }
        }
    
    def obter_contexto_consultivo(self, dados_expandidos, padroes_descobertos, aba_ativa):
        """
        Gera contexto consultivo baseado nos dados e padrões identificados
        RETORNA: String com insights contextuais OPCIONAIS para a IA
        """
        insights_contextuais = []
        
        # 1. ANÁLISE DE SAZONALIDADE
        estacao_atual = self._identificar_estacao_atual()
        contexto_sazonal = self._analisar_contexto_sazonal(dados_expandidos, estacao_atual)
        if contexto_sazonal:
            insights_contextuais.append(f"🌱 **CONTEXTO SAZONAL ({estacao_atual.upper()}):** {contexto_sazonal}")
        
        # 2. ANÁLISE DE CATEGORIAS ESPECÍFICAS
        contexto_categorias = self._analisar_categorias_especificas(dados_expandidos)
        if contexto_categorias:
            insights_contextuais.extend(contexto_categorias)
        
        # 3. ANÁLISE DE PADRÕES vs CONHECIMENTO SETORIAL
        contexto_padroes = self._analisar_padroes_vs_conhecimento(padroes_descobertos)
        if contexto_padroes:
            insights_contextuais.extend(contexto_padroes)
        
        # 4. BENCHMARKS E ALERTAS
        contexto_benchmarks = self._analisar_benchmarks(dados_expandidos, aba_ativa)
        if contexto_benchmarks:
            insights_contextuais.extend(contexto_benchmarks)
        
        return insights_contextuais
    
    def _identificar_estacao_atual(self):
        """Identifica estação atual (hemisfério sul)"""
        mes_atual = datetime.now().month
        
        if mes_atual in [12, 1, 2]:
            return "verao"
        elif mes_atual in [3, 4, 5]:
            return "volta_aulas"
        elif mes_atual in [6, 7, 8]:
            return "inverno"
        else:
            return "fim_ano"
    
    def _analisar_contexto_sazonal(self, dados_expandidos, estacao_atual):
        """Analisa se padrões encontrados fazem sentido sazonalmente"""
        
        if estacao_atual not in self.conhecimento_setor['sazonalidades']:
            return None
        
        info_estacao = self.conhecimento_setor['sazonalidades'][estacao_atual]
        categorias_esperadas = info_estacao['categorias']
        
        # Verificar se alguma categoria esperada aparece nos dados
        dados_basicos = dados_expandidos.get("metricas_basicas", {})
        categorias_encontradas = []
        
        for key, info in dados_basicos.items():
            if info.get('tipo') == 'classificacao':
                nome_categoria = key.replace('CLASS_', '').replace('_', ' ')
                for cat_esperada in categorias_esperadas:
                    if cat_esperada.upper() in nome_categoria.upper() or nome_categoria.upper() in cat_esperada.upper():
                        variacao = calcular_variacao_percentual(info['dados'])
                        categorias_encontradas.append({
                            'categoria': nome_categoria,
                            'variacao': variacao,
                            'esperado': cat_esperada
                        })
        
        if categorias_encontradas:
            return f"Estação {estacao_atual} - categorias esperadas: {', '.join(categorias_esperadas[:3])}. Impacto típico: {info_estacao['impacto_esperado']}"
        
        return None
    
    def _analisar_categorias_especificas(self, dados_expandidos):
        """Analisa categorias específicas vs conhecimento setorial"""
        insights = []
        dados_basicos = dados_expandidos.get("metricas_basicas", {})
        
        for key, info in dados_basicos.items():
            if info.get('tipo') == 'classificacao':
                nome_categoria = key.replace('CLASS_', '').replace('_', ' ')
                
                # Buscar categoria correspondente no conhecimento
                categoria_conhecida = None
                for cat_codigo, cat_info in self.conhecimento_setor['drivers_categoria'].items():
                    if cat_codigo.upper() in nome_categoria.upper() or nome_categoria.upper() in cat_codigo.upper():
                        categoria_conhecida = cat_codigo
                        break
                
                if categoria_conhecida:
                    variacao = calcular_variacao_percentual(info['dados'])
                    cat_info = self.conhecimento_setor['drivers_categoria'][categoria_conhecida]
                    
                    # Gerar insight contextual
                    fatores = cat_info['fatores_criticos'][:2]  # Pegar só os 2 principais
                    margem = cat_info['margem_tipica']
                    
                    insight = f"💡 **{categoria_conhecida}** (variação: {variacao:+.1f}%): Fatores-chave: {', '.join(fatores)}. Margem típica: {margem}"
                    insights.append(insight)
        
        return insights
    
    def _analisar_padroes_vs_conhecimento(self, padroes_descobertos):
        """Analisa padrões descobertos vs conhecimento setorial"""
        insights = []
        
        for padrao in padroes_descobertos:
            tipo_padrao = padrao.get('tipo_padrao', '')
            entidade = padrao.get('entidade', '')
            
            # Análise de padrões "barriga"
            if 'barriga' in tipo_padrao:
                estacao_atual = self._identificar_estacao_atual()
                info_barriga = self.conhecimento_setor['padroes_tipicos']['barriga_sazonal']
                
                if estacao_atual in ['verao', 'inverno']:
                    insight = f"🔍 **PADRÃO BARRIGA:** {info_barriga['quando_normal']} - pode ser sazonalidade normal"
                else:
                    insight = f"⚠️ **PADRÃO BARRIGA:** {info_barriga['quando_preocupante']} - investigar causas"
                
                insights.append(insight)
            
            # Análise de crescimento extremo
            if 'crescimento' in tipo_padrao:
                crescimento_info = self.conhecimento_setor['padroes_tipicos']['crescimento_sustentavel']
                insight = f"📈 **CRESCIMENTO:** {crescimento_info['caracteristicas'][0]} é o ideal. Avaliar sustentabilidade"
                insights.append(insight)
        
        return insights
    
    def _analisar_benchmarks(self, dados_expandidos, aba_ativa):
        """Compara performance vs benchmarks setoriais"""
        insights = []
        
        # Analisar crescimento geral
        dados_basicos = dados_expandidos.get("metricas_basicas", {})
        dados_geral = {k: v for k, v in dados_basicos.items() if v.get('tipo') == 'geral'}
        
        if dados_geral:
            geral_key = list(dados_geral.keys())[0]
            variacao_geral = calcular_variacao_percentual(dados_geral[geral_key]['dados'])
            
            # Comparar com benchmarks
            benchmarks = self.conhecimento_setor['benchmarks_setor']
            
            if aba_ativa == "mes":
                benchmark_mensal = 1.0  # 1% mensal = 12% anual
                if variacao_geral > benchmark_mensal * 2:
                    insights.append(f"🚀 **BENCHMARK:** Crescimento {variacao_geral:+.1f}% muito acima do normal ({benchmark_mensal}% mensal)")
                elif variacao_geral < benchmark_mensal * 0.5:
                    insights.append(f"⚠️ **BENCHMARK:** Crescimento {variacao_geral:+.1f}% abaixo do esperado ({benchmark_mensal}% mensal)")
            
            # Alertas críticos
            alertas = benchmarks['indicadores_alerta']
            if abs(variacao_geral) > 20:
                insights.append(f"🔴 **ALERTA:** Volatilidade alta detectada - {alertas['volatilidade_alta']}")
        
        return insights
    
    def obter_resumo_conhecimento(self):
        """
        Retorna resumo do conhecimento para exibição/edição
        ÚTIL para interface de administração futura
        """
        return {
            "total_sazonalidades": len(self.conhecimento_setor['sazonalidades']),
            "total_categorias": len(self.conhecimento_setor['drivers_categoria']),
            "ultima_atualizacao": "Manual - revisar periodicamente",
            "proxima_revisao_sugerida": "A cada 6 meses ou mudanças significativas no mercado"
        }
    
    def atualizar_conhecimento(self, secao, chave, novos_dados):
        """
        Método para atualizar conhecimento setorial
        FUTURO: Interface administrativa para edição
        """
        if secao in self.conhecimento_setor and chave in self.conhecimento_setor[secao]:
            self.conhecimento_setor[secao][chave].update(novos_dados)
            return f"✅ Conhecimento atualizado: {secao}.{chave}"
        return f"❌ Seção ou chave não encontrada: {secao}.{chave}"

def preparar_prompt_narrativa_inteligente(dados_expandidos, padroes_prioritarios, aba_ativa):
    """
    Prepara prompt INTELIGENTE para IA gerar narrativa contextualizada
    AGORA COM CONTEXTO FARMACÊUTICO CONSULTIVO
    """
    
    # 1. CONTEXTO DOS DADOS BÁSICOS (já existente)
    dados_basicos = dados_expandidos.get("metricas_basicas", {})
    
    # Extrair informações gerais
    geral_info = None
    filiais_info = []
    classificacoes_info = []
    
    for key, info in dados_basicos.items():
        variacao = calcular_variacao_percentual(info['dados'])
        
        if info.get('tipo') == 'geral':
            geral_info = {'nome': key, 'variacao': variacao, 'total': info.get('total_vendas', 0)}
        elif info.get('tipo') == 'filial':
            nome_limpo = key.replace('FILIAL_', 'Filial ')
            filiais_info.append({'nome': nome_limpo, 'variacao': variacao, 'total': info.get('total_vendas', 0)})
        elif info.get('tipo') == 'classificacao':
            nome_limpo = key.replace('CLASS_', '').replace('_', ' ')
            classificacoes_info.append({'nome': nome_limpo, 'variacao': variacao, 'total': info.get('total_vendas', 0)})
    
    # Ordenar por performance
    filiais_info.sort(key=lambda x: x['variacao'], reverse=True)
    classificacoes_info.sort(key=lambda x: x['variacao'], reverse=True)
    
    # 2. OBTER CONTEXTO FARMACÊUTICO CONSULTIVO (NOVO)
    contexto_farma = ContextoFarmaceutico()
    insights_consultivos = contexto_farma.obter_contexto_consultivo(dados_expandidos, padroes_prioritarios, aba_ativa)
    
    # 3. MONTAR PROMPT INTELIGENTE PARA IA
    prompt = f"""
    ANÁLISE EXECUTIVA FARMACÊUTICA - NÍVEL 3 AVANÇADO
    PERÍODO: {aba_ativa.upper()}
    
    Você é um consultor sênior especializado em farmácias com 15 anos de experiência. 
    Sua missão é transformar dados complexos em insights acionáveis para o dono da farmácia.
    
    ═══════════════════════════════════════════════════════════════
    📊 DADOS CONSOLIDADOS PARA ANÁLISE
    ═══════════════════════════════════════════════════════════════
    
    ## PERFORMANCE GERAL:
    """
    
    if geral_info:
        prompt += f"""
    - Tendência Geral: {geral_info['variacao']:+.1f}%
    - Faturamento Total: R$ {geral_info['total']:,.2f}
    """
    
    prompt += f"""
    
    ## TOP 5 FILIAIS (por performance):
    """
    for i, filial in enumerate(filiais_info[:5], 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "📊"
        prompt += f"""
    {emoji} {filial['nome']}: {filial['variacao']:+.1f}% | R$ {filial['total']:,.2f}
    """
    
    prompt += f"""
    
    ## TOP 5 CLASSIFICAÇÕES (por performance):
    """
    for i, classe in enumerate(classificacoes_info[:5], 1):
        emoji = "⭐" if i == 1 else "📈" if classe['variacao'] > 0 else "📉"
        prompt += f"""
    {emoji} {classe['nome']}: {classe['variacao']:+.1f}% | R$ {classe['total']:,.2f}
    """
    
    # 4. ADICIONAR PADRÕES DESCOBERTOS (já existente)
    if padroes_prioritarios:
        prompt += f"""
    
    ═══════════════════════════════════════════════════════════════
    🔍 PADRÕES CRÍTICOS IDENTIFICADOS AUTOMATICAMENTE
    ═══════════════════════════════════════════════════════════════
    
    O sistema de IA detectou {len(padroes_prioritarios)} padrões importantes:
    """
        
        for i, padrao in enumerate(padroes_prioritarios, 1):
            score = padrao.get('score_impacto', 0)
            insight = padrao.get('insight', 'Padrão detectado')
            acao = padrao.get('acao_sugerida', 'Investigar')
            
            criticidade = "🔴 CRÍTICO" if score >= 8 else "🟡 IMPORTANTE" if score >= 5 else "🔵 OBSERVAR"
            
            prompt += f"""
    
    {i}. {criticidade} - Score: {score:.1f}/10
       Descoberta: {insight}
       Ação Sugerida: {acao}
    """
    
    # 5. ADICIONAR CONTEXTO FARMACÊUTICO CONSULTIVO (NOVO)
    if insights_consultivos:
        prompt += f"""
    
    ═══════════════════════════════════════════════════════════════
    🧠 CONTEXTO FARMACÊUTICO CONSULTIVO
    ═══════════════════════════════════════════════════════════════
    
    Com base no conhecimento setorial acumulado, considere estes insights OPCIONAIS:
    """
        
        for insight in insights_consultivos:
            prompt += f"""
    
    {insight}
    """
        
        prompt += f"""
    
    **IMPORTANTE:** Use estes contextos como REFERÊNCIA, não como verdade absoluta. 
    Eles são baseados em padrões típicos do setor, mas cada farmácia é única.
    """
    
    # 6. INSTRUÇÕES INTELIGENTES PARA A IA (já existente, mas aprimorada)
    prompt += f"""
    
    ═══════════════════════════════════════════════════════════════
    🎯 SUAS INSTRUÇÕES COMO CONSULTOR ESPECIALISTA
    ═══════════════════════════════════════════════════════════════
    
    ## CONTEXTO DO CLIENTE:
    - Dono de rede de farmácias
    - Precisa de insights PRÁTICOS e ACIONÁVEIS
    - Tempo limitado (prefere análises concisas)
    - Foco em ROI e resultados mensuráveis
    
    ## SUA MISSÃO:
    Analise todos os dados acima e gere um relatório executivo que responda:
    
    1. **QUAL É O CENÁRIO REAL?** 
       - Onde estamos? (performance geral)
       - Quem está indo bem/mal? (destaques positivos e negativos)
    
    2. **O QUE ESTÁ ACONTECENDO DE DIFERENTE?**
       - Analise os padrões críticos detectados
       - Use o contexto farmacêutico como REFERÊNCIA (não regra)
       - Explique o que cada padrão significa na prática
    
    3. **O QUE FAZER AGORA?**
       - 2-3 ações específicas e priorizadas
       - Considere as sugestões do contexto farmacêutico
       - Foque no que tem maior impacto vs menor esforço
       - Seja específico (quem, o que, quando)
    
    ## DIRETRIZES DE COMUNICAÇÃO:
    - Linguagem executiva MAS acessível (evite jargões)
    - Tom consultivo e propositivo
    - Use números específicos quando relevante
    - Máximo 400 palavras
    - Estruture em 3 blocos claros: Cenário + Descobertas + Ações
    
    ## COMO USAR O CONTEXTO FARMACÊUTICO:
    - Use como SUBSÍDIO para enriquecer sua análise
    - Não repita informações óbvias do contexto
    - Questione se os padrões fazem sentido sazonalmente
    - Compare performance vs benchmarks quando relevante
    - Adapte sugestões para a realidade específica dos dados
    
    ## EXEMPLO DO TOM ESPERADO:
    "A rede cresceu 12% no período, puxada principalmente pela Filial 03 (+28%). 
    Preocupa a Filial 01, que caiu 8% e está perdendo participação. 
    
    O sistema detectou um padrão crítico: SBB perdeu 6 pontos de market share para Prescrição, 
    o que pode ser natural dado que estamos na época de maior procura por medicamentos.
    
    Recomendo três ações imediatas: 1) Investigar causas específicas da queda na Filial 01, 
    2) Replicar práticas da Filial 03 nas demais, e 3) Aproveitar o momento sazonal 
    para fortalecer ainda mais a categoria Prescrição com parcerias médicas."
    
    ═══════════════════════════════════════════════════════════════
    
    AGORA GERE SUA ANÁLISE EXECUTIVA COMO CONSULTOR ESPECIALISTA:
    """
    
    return prompt