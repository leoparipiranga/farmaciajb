# components_duck/gemini_duck.py
import streamlit as st
import pandas as pd
from datetime import datetime
from google import genai

def analisar_dados_gemini(prompt, dados_dict):
    """
    Função principal para análise com Gemini usando dicionários estruturados
    """
    try:
        # Acessar chave da API
        GEMINI_API_KEY = st.secrets["gemini_api_key"]["gemini_api_key"]
        
        # Criar cliente
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # Fazer a chamada
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        
        # Acessar o texto da resposta
        try:
            texto = response.text
        except AttributeError:
            texto = response.candidates[0].content.parts[0].text
        
        return texto
        
    except Exception as e:
        st.error(f"❌ Erro na análise com Gemini: {str(e)}")
        return f"Erro ao gerar análise: {str(e)}"

def gerar_insight_gemini(dados, contexto, nivel=1, aba_ativa="mes", dados_analise=None):
    """
    Gera insights usando a API do Gemini (VERSÃO ATUAL)
    Mantém compatibilidade com o sistema existente
    """
    try:
        # Acessar chave da API
        GEMINI_API_KEY = st.secrets["gemini_api_key"]["gemini_api_key"]
        
        # Criar cliente
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # Instruções específicas por nível
        if nivel == 1:
            instrucoes = """
            ANÁLISE NIVEL 1 - INSIGHT BÁSICO:
            - Analise apenas os dados da aba ativa fornecida
            - Identifique a tendência principal (crescimento/queda)
            - Compare período atual vs anterior
            - Limite: 80-120 caracteres
            - Formato: Uma frase objetiva
            - Priorize: Impacto imediato nos negócios
            """
        elif nivel == 2:
            instrucoes = """
            ANÁLISE NIVEL 2 - ANÁLISE DETALHADA E CONTEXTUALIZADA:
            - USE APENAS OS DADOS FORNECIDOS NA SEÇÃO 'DADOS DA ABA ATIVA'
            - IGNORE QUALQUER OUTRA INFORMAÇÃO QUE NÃO ESTEJA NOS DADOS TABULARES
            - ANALISE O PERÍODO HISTÓRICO COMPLETO fornecido (NÃO apenas o mês mais recente)
            - O MÊS ATUAL (SETEMBRO/2025) DEVE SER COMPLETAMENTE IGNORADO
            - ANALISE APENAS DADOS DE OUTUBRO/2024 ATÉ AGOSTO/2025
            - Comece com o insight principal da aba ativa usando os DADOS CONSOLIDADOS
            - Para análise por filial: Use apenas os dados de 'por_filial' (evite somar duplicatas)
            - Para análise por classificação: Use apenas os dados de 'por_classificacao' (evite somar duplicatas)
            - NÃO SOME todos os dados disponíveis - use cada conjunto separadamente
            - ANALISE OBRIGATORIAMENTE as seguintes dimensões se os dados estiverem disponíveis:
              * PERFORMANCE POR FILIAL: Compare crescimento/queda de cada filial vs total da rede
                - Calcule variações percentuais entre períodos
                - Identifique filiais com melhor/pior performance
              * PERFORMANCE POR CLASSIFICAÇÃO: Analise vendas por categoria (classificacao_n1)
                - Compare variações entre classificações
                - Identifique tendências de crescimento/queda
              * TENDÊNCIAS GERAIS: Analise se vendas aumentaram/diminuíram no período
                - Compare primeiro vs último período disponível
                - Identifique padrões de crescimento/queda
            - IDENTIFIQUE INFORMAÇÕES RELEVANTES: Variações contrárias à tendência geral
            - USE DADOS CONCRETOS: Sempre cite percentuais e valores específicos
            - FORMATO: 3-4 parágrafos estruturados
            - EXEMPLOS DE INSIGHTS VALIOSOS:
              * "Vendas cresceram 15% de outubro/24 a agosto/25"
              * "Filial 12 cresceu 25% vs rede 15%" 
              * "Classificação PRESCRIÇÃO caiu 8% na contramão do crescimento geral"
            - Limite: 300-400 palavras
            - Priorize: Análise histórica completa, não apenas o mês mais recente
            
            INSTRUÇÕES CRÍTICAS PARA CÁLCULOS:
            - Para calcular variação percentual: ((valor_final - valor_inicial) / valor_inicial) * 100
            - Use sempre o primeiro e último período disponível nos dados
            - Não invente valores - use apenas os dados fornecidos
            - Seja preciso nos cálculos matemáticos
            - Cite valores absolutos e percentuais
            """
        
        # Preparar dados específicos para o prompt
        dados_texto = dados.describe().to_string()[:500]
        dados_amostra = dados.head(5).to_string()
        
        # Adicionar cálculos pré-calculados
        calculos_previos = ""
        if not dados.empty and len(dados) >= 2:
            primeiro_periodo = dados.iloc[0]
            ultimo_periodo = dados.iloc[-1]
            
            valor_inicial = primeiro_periodo['venda']
            valor_final = ultimo_periodo['venda']
            variacao_percentual = ((valor_final - valor_inicial) / valor_inicial) * 100
            
            calculos_previos = f"""
            
            CÁLCULOS PRÉVIOS (BASEADOS NOS DADOS):
            - Primeiro período: {primeiro_periodo['periodo']} - R$ {valor_inicial:,.2f}
            - Último período: {ultimo_periodo['periodo']} - R$ {valor_final:,.2f}
            - Variação calculada: {variacao_percentual:.1f}%
            - Fórmula usada: (({valor_final:,.2f} - {valor_inicial:,.2f}) / {valor_inicial:,.2f}) * 100 = {variacao_percentual:.1f}%
            """
        
        dados_complementares = ""
        if dados_analise is not None:
            # Dados por filial (estatísticas resumidas)
            if 'por_filial' in dados_analise:
                filial_stats = dados_analise['por_filial'].groupby('filial_codigo')['venda'].agg(['sum', 'mean', 'count']).to_string()
                dados_complementares += f"\nDADOS POR FILIAL:\n{filial_stats[:300]}"
            
            # Dados por classificação (estatísticas resumidas)
            if 'por_classificacao' in dados_analise:
                class_stats = dados_analise['por_classificacao'].groupby('classificacao_n1')['venda'].agg(['sum', 'mean', 'count']).to_string()
                dados_complementares += f"\nDADOS POR CLASSIFICAÇÃO:\n{class_stats[:300]}"
        
        # Adicionar informações sobre o período analisado
        periodo_info = ""
        if not dados.empty:
            periodo_min = dados['data'].min().strftime('%b/%Y') if pd.notna(dados['data'].min()) else 'N/A'
            periodo_max = dados['data'].max().strftime('%b/%Y') if pd.notna(dados['data'].max()) else 'N/A'
            periodo_info = f"""
            
            PERÍODO ANALISADO: {periodo_min} até {periodo_max}
            - Analise tendências e variações neste período completo
            - Não foque apenas no mês mais recente
            - IGNORE COMPLETAMENTE O MÊS ATUAL (SETEMBRO/2025)
            - IGNORE QUALQUER MÊS NÃO COMPLETO (ex: OUTUBRO/2024 se dados começarem em 15/10)
            """

        # Preparar o prompt completo
        prompt = f"""
        Você é um analista de dados sênior especializado em vendas de farmácias e redes varejistas.
        Você se dirige ao dono de uma farmácia de bairro, que não é especialista em dados.
        Seu objetivo é fornecer insights claros, acionáveis e relevantes para ajudar na tomada de decisões.
        
        Tenha em mente que o que mais importa para o dono é o impacto direto nos negócios:
        Minhas vendas estão aumentando ou diminuindo? Meu resultado está melhorando ou não?
        
        CONHECIMENTOS IMPORTANTES:
        - Vendas em farmácias seguem padrões sazonais (alta demanda de medicamentos sazonais)
        - Margens apertadas exigem foco em eficiência operacional
        - Clientes buscam conveniência e confiança
        - Concorrência inclui drogarias, supermercados e e-commerce
        
        SEU ESTILO:
        - Linguagem profissional mas acessível
        - Foco em insights acionáveis para gestores
        - Evite jargões técnicos desnecessários
        - Seja objetivo e direto ao ponto
        
        {instrucoes}
        
        CONTEXTO ESPECÍFICO:
        {contexto}
        {periodo_info}
        {calculos_previos}
        
        DADOS DA ABA ATIVA (USE APENAS ESTES):
        Estatísticas: {dados_texto}
        Amostra: {dados_amostra}
        {dados_complementares}
        
        INSTRUÇÕES FINAIS:
        - USE APENAS OS DADOS FORNECIDOS ACIMA
        - ANALISE O PERÍODO HISTÓRICO COMPLETO (não apenas o mês mais recente)
        - Foque em tendências de crescimento/queda no período disponível
        - Use dados complementares apenas para adicionar contexto relevante
        - Seja específico e evite generalizações
        - Priorize insights que impactem decisões de negócio
        - Use linguagem adequada para gestores de farmácia
        - USE OS CÁLCULOS PRÉVIOS FORNECIDOS - NÃO RECALCULE VALORES
        - IGNORE COMPLETAMENTE QUALQUER REFERÊNCIA AO MÊS ATUAL (SETEMBRO/2025)
        """
        
        # Fazer a chamada
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        
        # Acessar o texto da resposta
        try:
            texto = response.text
        except AttributeError:
            texto = response.candidates[0].content.parts[0].text
        
        return texto
        
    except Exception as e:
        st.error(f"❌ Erro na geração de insight: {str(e)}")
        return f"Erro ao gerar insight: {str(e)}"