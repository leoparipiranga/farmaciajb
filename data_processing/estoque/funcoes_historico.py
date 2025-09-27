import pandas as pd
import streamlit as st
from business_logic.estoque.base_sets import ensure_bases_estoque
from core.database import duck_query
import datetime
import re

def calcular_disponibilidade_historico(start_month: str = "2024-10",
                                       end_month: str | None = None) -> pd.DataFrame:
    """
    Gera histórico mensal de disponibilidade agregando por:
      - Geral (rede)
      - Filial
      - Curva ABC
      - Classificacao N1
      - Classificacao N2
      - Todas as combinações (filial, curvaABC, classificacao_n1, classificacao_n2)
    Estrutura de saída (uma linha por combinação por mês):
      ano_mes, filial_codigo, curvaABC, classificacao_n1, classificacao_n2,
      total_itens, itens_disponiveis, disponibilidade_percent

    Regras:
      - Denominador: produtos com compra (Recebimento Físico) nos últimos 90d
                     E venda nos últimos 30d (mesma janela usada hoje).
      - Disponível: estoque > 0 no snapshot mais recente (<= data_ref) dentro dos 90d.
      - Curva ABC por quantidade 90d (A=50%, B=80%, C=resto; D se sem venda 90d).
      - data_ref de cada mês = último dia do mês.
    """
    # --- Normalização de formatos (aceita 'YYYY-MM' ou 'YYYY-MM-DD') ---
    def _to_ym(val) -> str:
        # Aceita datetime/date
        if isinstance(val, (datetime.date, datetime.datetime)):
            return val.strftime("%Y-%m")
        val = str(val)
        # Converte 'MM-YYYY' -> 'YYYY-MM'
        if re.fullmatch(r"\d{2}-\d{4}", val):
            mm, yyyy = val.split('-')
            return f"{yyyy}-{mm}"
        # Captura 'YYYY-MM' ou 'YYYY-MM-DD'
        return val[:7]

    today = datetime.date.today()
    if end_month is None:
        first_this = today.replace(day=1)
        last_closed = first_this - datetime.timedelta(days=1)
        end_month = last_closed.strftime("%Y-%m")

    start_month = _to_ym(start_month)
    end_month = _to_ym(end_month)

    # Helpers de datas
    def _month_ends(start_ym: str, end_ym: str) -> list[datetime.date]:
        sy, sm = map(int, start_ym.split("-"))
        ey, em = map(int, end_ym.split("-"))
        cur = datetime.date(sy, sm, 1)
        end = datetime.date(ey, em, 1)
        out = []
        while cur <= end:
            nxt = (cur.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
            last = nxt - datetime.timedelta(days=1)
            out.append(last)
            cur = nxt
        return out

    today = datetime.date.today()
    if end_month is None:
        # último mês completo (não inclui mês corrente se ainda não fechou)
        first_this = today.replace(day=1)
        last_closed = first_this - datetime.timedelta(days=1)
        end_month = last_closed.strftime("%Y-%m")

    # Lista de últimos dias de mês
    meses = _month_ends(start_month, end_month)
    if not meses:
        return pd.DataFrame(columns=[
            "ano_mes","filial_codigo","curvaABC","classificacao_n1","classificacao_n2",
            "total_itens","itens_disponiveis","disponibilidade_percent"
        ])

    historicos: list[pd.DataFrame] = []

    for mes_end in meses:
        data_ref = mes_end
        d_30 = data_ref - datetime.timedelta(days=30)
        d_90 = data_ref - datetime.timedelta(days=90)

        # SQL base: um registro por (filial, embalagem) no denominador + dims + flag disponivel + curva
        sql_base = f"""
        WITH vendas_90d AS (
            SELECT filial_codigo,
                   item_embalagemid AS embalagemid,
                   classificacao_n3,
                   SUM(ABS(item_quantidade)) AS qtd_vendida_90d
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{d_90}' AND DATE '{data_ref}'
            GROUP BY filial_codigo, classificacao_n3, item_embalagemid
        ),
        curva_rank AS (
            SELECT *,
                   SUM(qtd_vendida_90d) OVER (
                       PARTITION BY filial_codigo, classificacao_n3
                       ORDER BY qtd_vendida_90d DESC
                   ) AS acum,
                   SUM(qtd_vendida_90d) OVER (
                       PARTITION BY filial_codigo, classificacao_n3
                   ) AS total_grp
            FROM vendas_90d
        ),
        curva_abc AS (
            SELECT filial_codigo,
                   embalagemid,
                   CASE
                     WHEN total_grp>0 AND (acum*100.0/total_grp)<=50 THEN 'A'
                     WHEN total_grp>0 AND (acum*100.0/total_grp)<=80 THEN 'B'
                     WHEN total_grp>0 THEN 'C'
                     ELSE 'D'
                   END AS curvaABC
            FROM curva_rank
        ),
        comprados_90d AS (
            SELECT DISTINCT filial_codigo, embalagemid
            FROM fact_estoque_final
            WHERE descricao_movimentacao = 'Recebimento Físico'
              AND datahora BETWEEN DATE '{d_90}' AND DATE '{data_ref}'
        ),
        vendidos_30d AS (
            SELECT DISTINCT filial_codigo, item_embalagemid AS embalagemid
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{d_30}' AND DATE '{data_ref}'
        ),
        denominador AS (
            SELECT c.filial_codigo, c.embalagemid
            FROM comprados_90d c
            INNER JOIN vendidos_30d v
              ON c.filial_codigo = v.filial_codigo
             AND c.embalagemid = v.embalagemid
        ),
        snapshot AS (
            SELECT *
            FROM (
                SELECT
                    filial_codigo,
                    embalagemid,
                    estoque,
                    classificacao_n1,
                    classificacao_n2,
                    ROW_NUMBER() OVER (PARTITION BY filial_codigo, embalagemid ORDER BY datahora DESC) rn
                FROM fact_estoque_final
                WHERE datahora BETWEEN DATE '{d_90}' AND DATE '{data_ref}'
            )
            WHERE rn = 1
        ),
        base AS (
            SELECT
                d.filial_codigo,
                d.embalagemid,
                COALESCE(s.estoque,0) AS estoque,
                CASE WHEN COALESCE(s.estoque,0) > 0 THEN 1 ELSE 0 END AS disponivel,
                s.classificacao_n1,
                s.classificacao_n2,
                COALESCE(c.curvaABC,'D') AS curvaABC
            FROM denominador d
            LEFT JOIN snapshot s
              ON d.filial_codigo = s.filial_codigo
             AND d.embalagemid = s.embalagemid
            LEFT JOIN curva_abc c
              ON d.filial_codigo = c.filial_codigo
             AND d.embalagemid = c.embalagemid
        )
        SELECT
            filial_codigo,
            curvaABC,
            classificacao_n1,
            classificacao_n2,
            disponivel
        FROM base
        """
        base_df = duck_query(sql_base)
        if base_df is None or base_df.empty:
            continue

        # Normaliza classificações nulas
        for col in ["curvaABC","classificacao_n1","classificacao_n2"]:
            if col in base_df:
                base_df[col] = base_df[col].fillna("SemClass")

        # Lista de conjuntos de dimensões (granularidades)
        dims = [
            (),  # Geral
            ("filial_codigo",),
            ("curvaABC",),
            ("classificacao_n1",),
            ("classificacao_n2",),
            ("filial_codigo","curvaABC"),
            ("filial_codigo","classificacao_n1"),
            ("filial_codigo","classificacao_n2"),
            ("curvaABC","classificacao_n1"),
            ("curvaABC","classificacao_n2"),
            ("classificacao_n1","classificacao_n2"),
            ("filial_codigo","curvaABC","classificacao_n1"),
            ("filial_codigo","curvaABC","classificacao_n2"),
            ("filial_codigo","classificacao_n1","classificacao_n2"),
            ("curvaABC","classificacao_n1","classificacao_n2"),
            ("filial_codigo","curvaABC","classificacao_n1","classificacao_n2"),
        ]

        registros = []
        for g in dims:
            group_cols = list(g)

            if group_cols:  # caso normal: agrega pelas colunas escolhidas
                grouped = (
                    base_df
                    .groupby(group_cols, dropna=False)["disponivel"]
                    .agg(total_itens="count", itens_disponiveis="sum")
                    .reset_index()
                )
            else:
                # g == ()  -> linha "Geral" (sem chaves). Agrupa tudo.
                totals = base_df["disponivel"].agg(
                    total_itens="count",
                    itens_disponiveis="sum"
                )
                grouped = pd.DataFrame([totals])
                # Nenhuma dimensão presente; adicionamos colunas depois.

            # Preenche colunas ausentes com 'Geral'
            for col in ["filial_codigo", "curvaABC", "classificacao_n1", "classificacao_n2"]:
                if col not in group_cols:
                    grouped[col] = "Geral"

            # Garante presença das colunas (caso g == ())
            for col in ["filial_codigo", "curvaABC", "classificacao_n1", "classificacao_n2"]:
                if col not in grouped.columns:
                    grouped[col] = "Geral"

            grouped = grouped[[
                "filial_codigo", "curvaABC", "classificacao_n1", "classificacao_n2",
                "total_itens", "itens_disponiveis"
            ]]

            registros.append(grouped)

        aggs = pd.concat(registros, ignore_index=True)

        # Remove duplicados que podem aparecer (ex: mesma combinação gerada por caminhos diferentes)
        aggs = aggs.drop_duplicates()

        aggs["disponibilidade_percent"] = (aggs["itens_disponiveis"] * 100.0 / aggs["total_itens"]).round(2)
        aggs["ano_mes"] = data_ref.strftime("%Y-%m")

        historicos.append(aggs)

    if not historicos:
        return pd.DataFrame(columns=[
            "ano_mes","filial_codigo","curvaABC","classificacao_n1","classificacao_n2",
            "total_itens","itens_disponiveis","disponibilidade_percent"
        ])

    out = pd.concat(historicos, ignore_index=True)

    # Ordenação final
    out = out[[
        "ano_mes","filial_codigo","curvaABC","classificacao_n1","classificacao_n2",
        "total_itens","itens_disponiveis","disponibilidade_percent"
    ]].sort_values(["ano_mes","filial_codigo","curvaABC","classificacao_n1","classificacao_n2"])

    return out

def calcular_giro_historico(start_month: str = "2024-10",
                            end_month: str | None = None) -> pd.DataFrame:
    """
    Histórico mensal de GIRO (90d / 30d) agregando todas as combinações de:
      - filial_codigo
      - curvaABC (90 dias por quantidade)
      - classificacao_n1
      - classificacao_n2

    Para cada mês (último dia do mês = data_ref):
      Universo (denominador) = itens com:
        - snapshot mais recente nos 90d (estoque > =0)
        - pelo menos 1 'Recebimento Físico' nos 90d (compra)
      Giro (numerador) = subset com venda nos últimos 30d.
      Curva ABC calculada sobre vendas dos 90d (quantidade):
         A: até 50% acumulado, B: 50–80%, C: restante, D: sem vendas

    Métricas por combinação:
      total_produtos (itens no denominador)
      total_valor_estoque (soma valor_estoque)
      valor_estoque_com_giro (itens com venda 30d)
      valor_estoque_sem_giro
      giro_percent = (valor_estoque_com_giro / total_valor_estoque)*100 (0 se denom 0)

    Saída:
      ano_mes, filial_codigo, curvaABC, classificacao_n1, classificacao_n2,
      total_produtos, total_valor_estoque, valor_estoque_com_giro,
      valor_estoque_sem_giro, giro_percent
    """
    def _to_ym(val) -> str:
        if isinstance(val, (datetime.date, datetime.datetime)):
            return val.strftime("%Y-%m")
        s = str(val)
        if re.fullmatch(r"\d{2}-\d{4}", s):  # MM-YYYY -> YYYY-MM
            mm, yyyy = s.split("-")
            return f"{yyyy}-{mm}"
        return s[:7]

    today = datetime.date.today()
    if end_month is None:
        first_this = today.replace(day=1)
        end_month = (first_this - datetime.timedelta(days=1)).strftime("%Y-%m")

    start_month = _to_ym(start_month)
    end_month = _to_ym(end_month)

    def _month_ends(s_ym: str, e_ym: str):
        sy, sm = map(int, s_ym.split("-"))
        ey, em = map(int, e_ym.split("-"))
        cur = datetime.date(sy, sm, 1)
        end = datetime.date(ey, em, 1)
        out = []
        while cur <= end:
            nxt = (cur.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
            out.append(nxt - datetime.timedelta(days=1))
            cur = nxt
        return out

    month_ends = _month_ends(start_month, end_month)
    if not month_ends:
        return pd.DataFrame(columns=[
            "ano_mes","filial_codigo","curvaABC","classificacao_n1","classificacao_n2",
            "total_produtos","total_valor_estoque","valor_estoque_com_giro",
            "valor_estoque_sem_giro","giro_percent"
        ])

    resultados = []

    for ref_day in month_ends:
        d30 = ref_day - datetime.timedelta(days=30)
        d90 = ref_day - datetime.timedelta(days=90)

        # SQL base: uma linha por (filial, embalagem) com valor_estoque + dims + curvaABC + flag giro
        sql = f"""
        WITH vendas_90d AS (
            SELECT filial_codigo,
                   item_embalagemid AS embalagemid,
                   classificacao_n3,
                   SUM(ABS(item_quantidade)) AS qtd_vendida_90d
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{d90}' AND DATE '{ref_day}'
            GROUP BY filial_codigo, classificacao_n3, item_embalagemid
        ),
        curva_rank AS (
            SELECT *,
                   SUM(qtd_vendida_90d) OVER (
                       PARTITION BY filial_codigo, classificacao_n3
                       ORDER BY qtd_vendida_90d DESC
                   ) AS acum,
                   SUM(qtd_vendida_90d) OVER (
                       PARTITION BY filial_codigo, classificacao_n3
                   ) AS total_grp
            FROM vendas_90d
        ),
        curva_abc AS (
            SELECT filial_codigo,
                   embalagemid,
                   CASE
                     WHEN total_grp>0 AND (acum*100.0/total_grp)<=50 THEN 'A'
                     WHEN total_grp>0 AND (acum*100.0/total_grp)<=80 THEN 'B'
                     WHEN total_grp>0 THEN 'C'
                     ELSE 'D'
                   END AS curvaABC
            FROM curva_rank
        ),
        comprados_90d AS (
            SELECT DISTINCT filial_codigo, embalagemid
            FROM fact_estoque_final
            WHERE descricao_movimentacao = 'Recebimento Físico'
              AND datahora BETWEEN DATE '{d90}' AND DATE '{ref_day}'
        ),
        vendas_30d_ids AS (
            SELECT DISTINCT filial_codigo, item_embalagemid AS embalagemid
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{d30}' AND DATE '{ref_day}'
        ),
        snapshot AS (
            SELECT *
            FROM (
                SELECT
                    filial_codigo,
                    embalagemid,
                    estoque,
                    customedio,
                    classificacao_n1,
                    classificacao_n2,
                    classificacao_n3,
                    ROW_NUMBER() OVER (PARTITION BY filial_codigo, embalagemid ORDER BY datahora DESC) rn
                FROM fact_estoque_final
                WHERE datahora BETWEEN DATE '{d90}' AND DATE '{ref_day}'
            )
            WHERE rn=1
        ),
        base AS (
            SELECT
                s.filial_codigo,
                s.embalagemid,
                COALESCE(s.customedio*s.estoque,0) AS valor_estoque,
                s.classificacao_n1,
                s.classificacao_n2,
                s.classificacao_n3,
                COALESCE(c.curvaABC,'D') AS curvaABC,
                CASE WHEN v.embalagemid IS NOT NULL THEN 1 ELSE 0 END AS teve_giro
            FROM snapshot s
            INNER JOIN comprados_90d cpt
              ON s.filial_codigo = cpt.filial_codigo
             AND s.embalagemid = cpt.embalagemid
            LEFT JOIN vendas_30d_ids v
              ON s.filial_codigo = v.filial_codigo
             AND s.embalagemid = v.embalagemid
            LEFT JOIN curva_abc c
              ON s.filial_codigo = c.filial_codigo
             AND s.embalagemid = c.embalagemid
        )
        SELECT
            filial_codigo,
            curvaABC,
            classificacao_n1,
            classificacao_n2,
            embalagemid,
            valor_estoque,
            CASE WHEN teve_giro=1 THEN valor_estoque ELSE 0 END AS valor_estoque_com_giro
        FROM base
        """

        base_df = duck_query(sql)
        if base_df is None or base_df.empty:
            continue

        # Normaliza valores nulos
        for col in ["curvaABC","classificacao_n1","classificacao_n2"]:
            if col in base_df:
                base_df[col] = base_df[col].fillna("SemClass")

        # Dimensões para agregação (como na disponibilidade)
        dims = [
            (),  # Geral
            ("filial_codigo",),
            ("curvaABC",),
            ("classificacao_n1",),
            ("classificacao_n2",),
            ("filial_codigo","curvaABC"),
            ("filial_codigo","classificacao_n1"),
            ("filial_codigo","classificacao_n2"),
            ("curvaABC","classificacao_n1"),
            ("curvaABC","classificacao_n2"),
            ("classificacao_n1","classificacao_n2"),
            ("filial_codigo","curvaABC","classificacao_n1"),
            ("filial_codigo","curvaABC","classificacao_n2"),
            ("filial_codigo","classificacao_n1","classificacao_n2"),
            ("curvaABC","classificacao_n1","classificacao_n2"),
            ("filial_codigo","curvaABC","classificacao_n1","classificacao_n2"),
        ]

        registros = []
        for g in dims:
            group_cols = list(g)

            if group_cols:
                grouped = (
                    base_df
                    .groupby(group_cols, dropna=False)
                    .agg(
                        total_valor_estoque=("valor_estoque","sum"),
                        valor_estoque_com_giro=("valor_estoque_com_giro","sum"),
                        total_produtos=("embalagemid","nunique")
                    )
                    .reset_index()
                )
            else:
                # Geral
                totals = {
                    "total_valor_estoque": base_df["valor_estoque"].sum(),
                    "valor_estoque_com_giro": base_df["valor_estoque_com_giro"].sum(),
                    "total_produtos": base_df["embalagemid"].nunique()
                }
                grouped = pd.DataFrame([totals])

            # Preenche dimensões ausentes com 'Geral'
            for col in ["filial_codigo","curvaABC","classificacao_n1","classificacao_n2"]:
                if col not in grouped.columns:
                    grouped[col] = "Geral"

            grouped = grouped[[
                "filial_codigo","curvaABC","classificacao_n1","classificacao_n2",
                "total_produtos","total_valor_estoque","valor_estoque_com_giro"
            ]]

            registros.append(grouped)

        aggs = pd.concat(registros, ignore_index=True).drop_duplicates()

        aggs["valor_estoque_sem_giro"] = aggs["total_valor_estoque"] - aggs["valor_estoque_com_giro"]
        aggs["giro_percent"] = aggs.apply(
            lambda r: (r["valor_estoque_com_giro"] * 100.0 / r["total_valor_estoque"]) if r["total_valor_estoque"] > 0 else 0,
            axis=1
        )
        aggs["ano_mes"] = ref_day.strftime("%Y-%m")

        resultados.append(aggs)

    if not resultados:
        return pd.DataFrame(columns=[
            "ano_mes","filial_codigo","curvaABC","classificacao_n1","classificacao_n2",
            "total_produtos","total_valor_estoque","valor_estoque_com_giro",
            "valor_estoque_sem_giro","giro_percent"
        ])

    out = pd.concat(resultados, ignore_index=True)

    # Arredondamentos
    for c in ["total_valor_estoque","valor_estoque_com_giro","valor_estoque_sem_giro"]:
        out[c] = out[c].round(2)
    out["giro_percent"] = out["giro_percent"].round(2)

    # Ordena
    out = out.sort_values(["ano_mes","filial_codigo","curvaABC","classificacao_n1","classificacao_n2"])

    return out

def calcular_cobertura_historico(start_month: str = "2024-10",
                                 end_month: str | None = None) -> pd.DataFrame:
    """
    Histórico mensal do Fator de Cobertura agregando combinações de:
      - filial_codigo
      - curvaABC
      - classificacao_n1
      - classificacao_n2

    Para cada mês (data_ref = último dia do mês):
      stock_cmv       = soma (customedio * estoque) do snapshot mais recente <= data_ref (por item)
      cmv_vendido_30d = soma do custo vendido 30d (coluna customedio, ver abaixo)
      cobertura_ratio = stock_cmv / cmv_vendido_30d  (0 se cmv_vendido_30d = 0)

    Observações:
      - Assume que fact_vendas_final possui UMA das colunas de custo: customedio.
        Ajuste a expressão cmv_origem se necessário para refletir o campo correto.
      - Curva ABC calculada sobre quantidade vendida 90d (A=50%, B=80%, C=resto, D=sem venda).
    Saída:
      ano_mes, filial_codigo, curvaABC, classificacao_n1, classificacao_n2,
      stock_cmv, cmv_vendido_30d, cobertura_ratio
    """
    def _to_ym(val) -> str:
        if isinstance(val, (datetime.date, datetime.datetime)):
            return val.strftime("%Y-%m")
        s = str(val)
        if re.fullmatch(r"\d{2}-\d{4}", s):  # MM-YYYY -> YYYY-MM
            mm, yyyy = s.split("-")
            return f"{yyyy}-{mm}"
        return s[:7]

    today = datetime.date.today()
    if end_month is None:
        first_this = today.replace(day=1)
        end_month = (first_this - datetime.timedelta(days=1)).strftime("%Y-%m")

    start_month = _to_ym(start_month)
    end_month = _to_ym(end_month)

    def _month_ends(s_ym: str, e_ym: str):
        sy, sm = map(int, s_ym.split("-"))
        ey, em = map(int, e_ym.split("-"))
        cur = datetime.date(sy, sm, 1)
        end = datetime.date(ey, em, 1)
        out = []
        while cur <= end:
            nxt = (cur.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
            out.append(nxt - datetime.timedelta(days=1))
            cur = nxt
        return out

    month_ends = _month_ends(start_month, end_month)
    if not month_ends:
        return pd.DataFrame(columns=[
            "ano_mes","filial_codigo","curvaABC","classificacao_n1","classificacao_n2",
            "stock_cmv","cmv_vendido_30d","cobertura_ratio"
        ])

    resultados = []

    # Campo de custo utilizado nas vendas (ajuste se necessário)
    cmv_origem = "COALESCE(customedio, 0)"

    for ref_day in month_ends:
        d30 = ref_day - datetime.timedelta(days=30)
        d90 = ref_day - datetime.timedelta(days=90)

        sql = f"""
        WITH vendas_90d AS (
            SELECT filial_codigo,
                   item_embalagemid AS embalagemid,
                   classificacao_n3,
                   SUM(ABS(item_quantidade)) AS qtd_vendida_90d
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{d90}' AND DATE '{ref_day}'
            GROUP BY filial_codigo, classificacao_n3, item_embalagemid
        ),
        curva_rank AS (
            SELECT *,
                   SUM(qtd_vendida_90d) OVER (
                       PARTITION BY filial_codigo, classificacao_n3
                       ORDER BY qtd_vendida_90d DESC
                   ) AS acum,
                   SUM(qtd_vendida_90d) OVER (
                       PARTITION BY filial_codigo, classificacao_n3
                   ) AS total_grp
            FROM vendas_90d
        ),
        curva_abc AS (
            SELECT filial_codigo,
                   embalagemid,
                   CASE
                     WHEN total_grp>0 AND (acum*100.0/total_grp)<=50 THEN 'A'
                     WHEN total_grp>0 AND (acum*100.0/total_grp)<=80 THEN 'B'
                     WHEN total_grp>0 THEN 'C'
                     ELSE 'D'
                   END AS curvaABC
            FROM curva_rank
        ),
        vendas_30d AS (
            SELECT
                filial_codigo,
                item_embalagemid AS embalagemid,
                SUM({cmv_origem}) AS cmv_vendido_30d
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{d30}' AND DATE '{ref_day}'
            GROUP BY filial_codigo, item_embalagemid
        ),
        snapshot AS (
            SELECT *
            FROM (
                SELECT
                    filial_codigo,
                    embalagemid,
                    estoque,
                    customedio,
                    classificacao_n1,
                    classificacao_n2,
                    ROW_NUMBER() OVER (PARTITION BY filial_codigo, embalagemid ORDER BY datahora DESC) rn
                FROM fact_estoque_final
                WHERE datahora <= DATE '{ref_day}'
            )
            WHERE rn=1
        ),
        base AS (
            SELECT
                s.filial_codigo,
                s.embalagemid,
                COALESCE(s.customedio * s.estoque,0) AS stock_cmv,
                COALESCE(v.cmv_vendido_30d,0) AS cmv_vendido_30d,
                s.classificacao_n1,
                s.classificacao_n2,
                COALESCE(c.curvaABC,'D') AS curvaABC
            FROM snapshot s
            LEFT JOIN vendas_30d v
              ON s.filial_codigo = v.filial_codigo
             AND s.embalagemid = v.embalagemid
            LEFT JOIN curva_abc c
              ON s.filial_codigo = c.filial_codigo
             AND s.embalagemid = c.embalagemid
        )
        SELECT
            filial_codigo,
            curvaABC,
            classificacao_n1,
            classificacao_n2,
            stock_cmv,
            cmv_vendido_30d
        FROM base
        """

        base_df = duck_query(sql)
        if base_df is None or base_df.empty:
            continue

        for col in ["curvaABC","classificacao_n1","classificacao_n2"]:
            if col in base_df:
                base_df[col] = base_df[col].fillna("SemClass")

        dims = [
            (),  # Geral
            ("filial_codigo",),
            ("curvaABC",),
            ("classificacao_n1",),
            ("classificacao_n2",),
            ("filial_codigo","curvaABC"),
            ("filial_codigo","classificacao_n1"),
            ("filial_codigo","classificacao_n2"),
            ("curvaABC","classificacao_n1"),
            ("curvaABC","classificacao_n2"),
            ("classificacao_n1","classificacao_n2"),
            ("filial_codigo","curvaABC","classificacao_n1"),
            ("filial_codigo","curvaABC","classificacao_n2"),
            ("filial_codigo","classificacao_n1","classificacao_n2"),
            ("curvaABC","classificacao_n1","classificacao_n2"),
            ("filial_codigo","curvaABC","classificacao_n1","classificacao_n2"),
        ]

        registros = []
        for g in dims:
            group_cols = list(g)
            if group_cols:
                grouped = (
                    base_df
                    .groupby(group_cols, dropna=False)
                    .agg(
                        stock_cmv=("stock_cmv","sum"),
                        cmv_vendido_30d=("cmv_vendido_30d","sum")
                    )
                    .reset_index()
                )
            else:
                grouped = pd.DataFrame([{
                    "stock_cmv": base_df["stock_cmv"].sum(),
                    "cmv_vendido_30d": base_df["cmv_vendido_30d"].sum()
                }])

            for col in ["filial_codigo","curvaABC","classificacao_n1","classificacao_n2"]:
                if col not in grouped.columns:
                    grouped[col] = "Geral"

            grouped = grouped[[
                "filial_codigo","curvaABC","classificacao_n1","classificacao_n2",
                "stock_cmv","cmv_vendido_30d"
            ]]
            registros.append(grouped)

        aggs = pd.concat(registros, ignore_index=True).drop_duplicates()
        aggs["cobertura_ratio"] = aggs.apply(
            lambda r: (r["stock_cmv"] / r["cmv_vendido_30d"]) if r["cmv_vendido_30d"] > 0 else 0,
            axis=1
        )
        aggs["ano_mes"] = ref_day.strftime("%Y-%m")
        resultados.append(aggs)

    if not resultados:
        return pd.DataFrame(columns=[
            "ano_mes","filial_codigo","curvaABC","classificacao_n1","classificacao_n2",
            "stock_cmv","cmv_vendido_30d","cobertura_ratio"
        ])

    out = pd.concat(resultados, ignore_index=True)
    out["stock_cmv"] = out["stock_cmv"].round(2)
    out["cmv_vendido_30d"] = out["cmv_vendido_30d"].round(2)
    out["cobertura_ratio"] = out["cobertura_ratio"].round(4)
    out = out.sort_values(["ano_mes","filial_codigo","curvaABC","classificacao_n1","classificacao_n2"])
    return out


def calcular_gmroi_historico(start_month: str = "2024-10",
                             end_month: str | None = None,
                             periodo_vendas: int = 90) -> pd.DataFrame:
    """
    Histórico mensal de GMROI (Baseado em Vendas Reais) agregando combinações de:
      - filial_codigo
      - curvaABC (derivada da quantidade vendida no período de vendas - default 90d)
      - classificacao_n1
      - classificacao_n2

    Para cada mês (referência = último dia do mês = data_ref):
      Janela de vendas / estoque médio: [data_ref - (periodo_vendas - 1) , data_ref]
      Vendas:
        receita_real_vendas  = (item_valorunitario - desconto) * |qtd|
        cmv_vendas           = customedio * |qtd|
        margem_bruta_vendas  = receita_real_vendas - cmv_vendas
      Estoque médio por item:
        - Usa cache_estoque_diario se existir (valor_estoque_dia já calculado)
        - Senão deriva último registro de cada dia em fact_estoque_final
        - valor_estoque_medio_item = AVG(valor_estoque_dia) na janela
      GMROI:
        gmroi_ratio       = margem_bruta_vendas / valor_medio_estoque
        gmroi_percentual  = gmroi_ratio * 100

    Saída (uma linha por combinação de dimensões por mês):
      ano_mes, filial_codigo, curvaABC, classificacao_n1, classificacao_n2,
      receita_real_vendas, cmv_vendas, margem_bruta_vendas,
      valor_medio_estoque, gmroi_percentual, gmroi_ratio,
      total_transacoes, total_quantidade_vendida, total_produtos_estoque
    """
    def _to_ym(val) -> str:
        if isinstance(val, (datetime.date, datetime.datetime)):
            return val.strftime("%Y-%m")
        s = str(val)
        if re.fullmatch(r"\d{2}-\d{4}", s):  # MM-YYYY -> YYYY-MM
            mm, yyyy = s.split("-")
            return f"{yyyy}-{mm}"
        return s[:7]

    today = datetime.date.today()
    if end_month is None:
        first_this = today.replace(day=1)
        end_month = (first_this - datetime.timedelta(days=1)).strftime("%Y-%m")

    start_month = _to_ym(start_month)
    end_month = _to_ym(end_month)

    def _month_ends(s_ym: str, e_ym: str):
        sy, sm = map(int, s_ym.split("-"))
        ey, em = map(int, e_ym.split("-"))
        cur = datetime.date(sy, sm, 1)
        end = datetime.date(ey, em, 1)
        out = []
        while cur <= end:
            nxt = (cur.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
            out.append(nxt - datetime.timedelta(days=1))
            cur = nxt
        return out

    month_ends = _month_ends(start_month, end_month)
    if not month_ends:
        return pd.DataFrame(columns=[
            "ano_mes","filial_codigo","curvaABC","classificacao_n1","classificacao_n2",
            "receita_real_vendas","cmv_vendas","margem_bruta_vendas",
            "valor_medio_estoque","gmroi_percentual","gmroi_ratio",
            "total_transacoes","total_quantidade_vendida","total_produtos_estoque"
        ])

    resultados = []

    # Detecta se cache_estoque_diario existe (uma única vez)
    try:
        _tmp = duck_query("SELECT 1 FROM information_schema.tables WHERE table_name='cache_estoque_diario' LIMIT 1;")
        has_cache_diario = not (_tmp is None or _tmp.empty)
    except:
        has_cache_diario = False

    for ref_day in month_ends:
        ini_vendas = ref_day - datetime.timedelta(days=periodo_vendas - 1)
        # CTE para estoque diário (cache ou fallback)
        if has_cache_diario:
            estoque_diario_cte = f"""
            estoque_diario AS (
                SELECT
                    filial_codigo,
                    embalagemid,
                    data_dia,
                    valor_estoque_dia AS valor_dia
                FROM cache_estoque_diario
                WHERE data_dia BETWEEN DATE '{ini_vendas}' AND DATE '{ref_day}'
                  AND valor_estoque_dia >= 0
            ),
            """
        else:
            estoque_diario_cte = f"""
            estoque_diario_raw AS (
                SELECT
                    filial_codigo,
                    embalagemid,
                    DATE(datahora) AS data_dia,
                    customedio,
                    estoque,
                    ROW_NUMBER() OVER (
                        PARTITION BY filial_codigo, embalagemid, DATE(datahora)
                        ORDER BY datahora DESC
                    ) AS rn_dia
                FROM fact_estoque_final
                WHERE DATE(datahora) BETWEEN DATE '{ini_vendas}' AND DATE '{ref_day}'
                  AND estoque >= 0
                  AND customedio > 0
            ),
            estoque_diario AS (
                SELECT
                    filial_codigo,
                    embalagemid,
                    data_dia,
                    customedio * estoque AS valor_dia
                FROM estoque_diario_raw
                WHERE rn_dia = 1
            ),
            """

        sql = f"""
        WITH vendas_periodo AS (
            SELECT
                filial_codigo,
                item_embalagemid AS embalagemid,
                SUM( (item_valorunitario - COALESCE(item_desconto,0)) * ABS(item_quantidade) ) AS receita_real_vendas,
                SUM( customedio * ABS(item_quantidade) ) AS cmv_vendas,
                SUM( ((item_valorunitario - COALESCE(item_desconto,0)) - customedio) * ABS(item_quantidade) ) AS margem_bruta_vendas,
                COUNT(*) AS total_transacoes,
                SUM(ABS(item_quantidade)) AS total_quantidade_vendida
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{ini_vendas}' AND DATE '{ref_day}'
              AND customedio > 0
              AND item_valorunitario > 0
            GROUP BY filial_codigo, item_embalagemid
        ),
        -- Curva ABC (mesma janela de vendas para consistência)
        vendas_qtd AS (
            SELECT
                filial_codigo,
                item_embalagemid AS embalagemid,
                classificacao_n3,
                SUM(ABS(item_quantidade)) AS qtd
            FROM fact_vendas_final
            WHERE data_date BETWEEN DATE '{ini_vendas}' AND DATE '{ref_day}'
            GROUP BY filial_codigo, classificacao_n3, item_embalagemid
        ),
        curva_rank AS (
            SELECT *,
                   SUM(qtd) OVER (PARTITION BY filial_codigo, classificacao_n3 ORDER BY qtd DESC) AS acum,
                   SUM(qtd) OVER (PARTITION BY filial_codigo, classificacao_n3) AS total_grp
            FROM vendas_qtd
        ),
        curva_abc AS (
            SELECT
                filial_codigo,
                embalagemid,
                CASE
                  WHEN total_grp>0 AND (acum*100.0/total_grp)<=50 THEN 'A'
                  WHEN total_grp>0 AND (acum*100.0/total_grp)<=80 THEN 'B'
                  WHEN total_grp>0 THEN 'C'
                  ELSE 'D'
                END AS curvaABC
            FROM curva_rank
        ),
        -- Classificações (pega o último registro dentro da janela para N1/N2)
        classificacao_ref_raw AS (
            SELECT
                filial_codigo,
                embalagemid,
                classificacao_n1,
                classificacao_n2,
                ROW_NUMBER() OVER (
                    PARTITION BY filial_codigo, embalagemid
                    ORDER BY datahora DESC
                ) AS rn
            FROM fact_estoque_final
            WHERE DATE(datahora) BETWEEN DATE '{ini_vendas}' AND DATE '{ref_day}'
        ),
        classificacao_ref AS (
            SELECT filial_codigo, embalagemid,
                   classificacao_n1, classificacao_n2
            FROM classificacao_ref_raw
            WHERE rn = 1
        ),
        {estoque_diario_cte}
        estoque_medio_item AS (
            SELECT
                filial_codigo,
                embalagemid,
                AVG(valor_dia) AS valor_estoque_medio
            FROM estoque_diario
            GROUP BY filial_codigo, embalagemid
        ),
        base AS (
            SELECT
                COALESCE(em.filial_codigo, vp.filial_codigo) AS filial_codigo,
                COALESCE(em.embalagemid, vp.embalagemid) AS embalagemid,
                COALESCE(vp.receita_real_vendas,0) AS receita_real_vendas,
                COALESCE(vp.cmv_vendas,0) AS cmv_vendas,
                COALESCE(vp.margem_bruta_vendas,0) AS margem_bruta_vendas,
                COALESCE(vp.total_transacoes,0) AS total_transacoes,
                COALESCE(vp.total_quantidade_vendida,0) AS total_quantidade_vendida,
                COALESCE(em.valor_estoque_medio,0) AS valor_estoque_medio,
                COALESCE(cr.classificacao_n1,'SemClass') AS classificacao_n1,
                COALESCE(cr.classificacao_n2,'SemClass') AS classificacao_n2,
                COALESCE(ca.curvaABC,'D') AS curvaABC
            FROM estoque_medio_item em
            FULL OUTER JOIN vendas_periodo vp
              ON em.filial_codigo = vp.filial_codigo
             AND em.embalagemid = vp.embalagemid
            LEFT JOIN classificacao_ref cr
              ON COALESCE(em.filial_codigo, vp.filial_codigo) = cr.filial_codigo
             AND COALESCE(em.embalagemid, vp.embalagemid) = cr.embalagemid
            LEFT JOIN curva_abc ca
              ON COALESCE(em.filial_codigo, vp.filial_codigo) = ca.filial_codigo
             AND COALESCE(em.embalagemid, vp.embalagemid) = ca.embalagemid
        )
        SELECT *
        FROM base
        """

        base_df = duck_query(sql)
        if base_df is None or base_df.empty:
            continue

        # Garante tipos numéricos
        for c in ["receita_real_vendas","cmv_vendas","margem_bruta_vendas",
                  "total_transacoes","total_quantidade_vendida","valor_estoque_medio"]:
            if c in base_df:
                base_df[c] = pd.to_numeric(base_df[c], errors="coerce").fillna(0)

        # Lista de dimensões (igual padrão anterior)
        dims = [
            (),  # Geral
            ("filial_codigo",),
            ("curvaABC",),
            ("classificacao_n1",),
            ("classificacao_n2",),
            ("filial_codigo","curvaABC"),
            ("filial_codigo","classificacao_n1"),
            ("filial_codigo","classificacao_n2"),
            ("curvaABC","classificacao_n1"),
            ("curvaABC","classificacao_n2"),
            ("classificacao_n1","classificacao_n2"),
            ("filial_codigo","curvaABC","classificacao_n1"),
            ("filial_codigo","curvaABC","classificacao_n2"),
            ("filial_codigo","classificacao_n1","classificacao_n2"),
            ("curvaABC","classificacao_n1","classificacao_n2"),
            ("filial_codigo","curvaABC","classificacao_n1","classificacao_n2"),
        ]

        registros = []
        for g in dims:
            group_cols = list(g)
            if group_cols:
                grouped = (
                    base_df
                    .groupby(group_cols, dropna=False)
                    .agg(
                        receita_real_vendas=("receita_real_vendas","sum"),
                        cmv_vendas=("cmv_vendas","sum"),
                        margem_bruta_vendas=("margem_bruta_vendas","sum"),
                        valor_medio_estoque=("valor_estoque_medio","sum"),
                        total_transacoes=("total_transacoes","sum"),
                        total_quantidade_vendida=("total_quantidade_vendida","sum"),
                        total_produtos_estoque=("embalagemid","nunique")
                    )
                    .reset_index()
                )
            else:
                grouped = pd.DataFrame([{
                    "receita_real_vendas": base_df["receita_real_vendas"].sum(),
                    "cmv_vendas": base_df["cmv_vendas"].sum(),
                    "margem_bruta_vendas": base_df["margem_bruta_vendas"].sum(),
                    "valor_medio_estoque": base_df["valor_estoque_medio"].sum(),
                    "total_transacoes": base_df["total_transacoes"].sum(),
                    "total_quantidade_vendida": base_df["total_quantidade_vendida"].sum(),
                    "total_produtos_estoque": base_df["embalagemid"].nunique()
                }])

            # Preenche dimensões ausentes
            for col in ["filial_codigo","curvaABC","classificacao_n1","classificacao_n2"]:
                if col not in grouped.columns:
                    grouped[col] = "Geral"

            grouped = grouped[[
                "filial_codigo","curvaABC","classificacao_n1","classificacao_n2",
                "receita_real_vendas","cmv_vendas","margem_bruta_vendas",
                "valor_medio_estoque","total_transacoes",
                "total_quantidade_vendida","total_produtos_estoque"
            ]]
            registros.append(grouped)

        aggs = pd.concat(registros, ignore_index=True).drop_duplicates()

        aggs["gmroi_ratio"] = aggs.apply(
            lambda r: (r["margem_bruta_vendas"] / r["valor_medio_estoque"]) if r["valor_medio_estoque"] > 0 else 0,
            axis=1
        )
        aggs["gmroi_percentual"] = (aggs["gmroi_ratio"] * 100).round(4)
        aggs["ano_mes"] = ref_day.strftime("%Y-%m")

        resultados.append(aggs)

    if not resultados:
        return pd.DataFrame(columns=[
            "ano_mes","filial_codigo","curvaABC","classificacao_n1","classificacao_n2",
            "receita_real_vendas","cmv_vendas","margem_bruta_vendas",
            "valor_medio_estoque","gmroi_percentual","gmroi_ratio",
            "total_transacoes","total_quantidade_vendida","total_produtos_estoque"
        ])

    out = pd.concat(resultados, ignore_index=True)

    # Arredondamentos finais
    for c in ["receita_real_vendas","cmv_vendas","margem_bruta_vendas","valor_medio_estoque","gmroi_ratio"]:
        if c in out:
            out[c] = out[c].round(2 if c != "gmroi_ratio" else 4)
    for c in ["gmroi_percentual"]:
        if c in out:
            out[c] = out[c].round(4)

    # Inteiros
    for c in ["total_transacoes","total_quantidade_vendida","total_produtos_estoque"]:
        if c in out:
            out[c] = out[c].fillna(0).astype(int)

    out = out.sort_values(["ano_mes","filial_codigo","curvaABC","classificacao_n1","classificacao_n2"])
    return out

def calcular_curvad_historico(start_month: str = "2024-10",
                              end_month: str | None = None) -> pd.DataFrame:
    """
    Histórico mensal do índice Curva D (mesma lógica da função diária
    calcular_indice_curva_d_por_curva_abc) gerando QUATRO agrupamentos:
      1) curvaABC (Geral rede / classificacao_n1='Geral')
      2) curvaABC + filial (classificacao_n1='Geral')
      3) curvaABC + classificacao_n1 (filial='Geral')
      4) curvaABC + filial + classificacao_n1

    Para cada mês usa o último dia do mês como data de referência (ref_day) e
    constrói a janela de 30 pares (day, purchase_date = day-91) exatamente
    como a função base, produzindo as mesmas métricas:

      total_unicos_denom        (COUNT DISTINCT embalagemid)
      produtos_unicos_curva_d   (COUNT DISTINCT embalagemid sem venda no período)
      total_qtde_all / total_qtde_curva_d
      total_val_all / total_val_curva_d
      indice_curva_d = produtos_unicos_curva_d*100/total_unicos_denom

    Saída:
      ano_mes, filial_codigo, curvaABC, classificacao_n1,
      total_unicos_denom, produtos_unicos_curva_d,
      total_qtde_all, total_qtde_curva_d,
      total_val_all, total_val_curva_d, indice_curva_d
    """
    def _to_ym(val) -> str:
        if isinstance(val, (datetime.date, datetime.datetime)):
            return val.strftime("%Y-%m")
        s = str(val)
        if re.fullmatch(r"\d{2}-\d{4}", s):
            mm, yyyy = s.split("-")
            return f"{yyyy}-{mm}"
        return s[:7]

    today = datetime.date.today()
    if end_month is None:
        first_this = today.replace(day=1)
        end_month = (first_this - datetime.timedelta(days=1)).strftime("%Y-%m")

    start_month = _to_ym(start_month)
    end_month = _to_ym(end_month)

    def _month_ends(s_ym: str, e_ym: str):
        sy, sm = map(int, s_ym.split("-"))
        ey, em = map(int, e_ym.split("-"))
        cur = datetime.date(sy, sm, 1)
        end = datetime.date(ey, em, 1)
        out = []
        while cur <= end:
            nxt = (cur.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
            out.append(nxt - datetime.timedelta(days=1))
            cur = nxt
        return out

    month_ends = _month_ends(start_month, end_month)
    if not month_ends:
        return pd.DataFrame(columns=[
            "ano_mes","filial_codigo","curvaABC","classificacao_n1",
            "total_unicos_denom","produtos_unicos_curva_d",
            "total_qtde_all","total_qtde_curva_d",
            "total_val_all","total_val_curva_d","indice_curva_d"
        ])

    resultados = []

    for ref_day in month_ends:
        data = ref_day  # equivalente à 'data' usada na função base

        # Pares (day, purchase_date) últimos 30 dias (day = data - (1..30))
        pairs = []
        for offset in range(30):
            day = data - datetime.timedelta(days=1 + offset)
            purchase_date = day - datetime.timedelta(days=91)
            pairs.append((day.strftime('%Y-%m-%d'), purchase_date.strftime('%Y-%m-%d')))

        values_sql = ",\n        ".join(f"(DATE '{d}', DATE '{p}')" for d, p in pairs)

        sql = f"""
        WITH days(day, purchase_date) AS (
            VALUES
            {values_sql}
        ),
        compras AS (
            SELECT
                d.day,
                d.purchase_date,
                f.filial_codigo,
                f.embalagemid,
                SUM(ABS(f.quantidade)) AS total_qtde,
                SUM(ABS(f.quantidade) * COALESCE(f.customedio,0)) AS total_valor,
                CASE WHEN SUM(ABS(f.quantidade)) = 0 THEN 0
                     ELSE SUM(ABS(f.quantidade) * COALESCE(f.customedio,0)) / SUM(ABS(f.quantidade))
                END AS customedio_med,
                f.classificacao_n1,
                f.classificacao_n2,
                f.classificacao_n3
            FROM days d
            JOIN fact_estoque_final f
              ON DATE(f.datahora) = d.purchase_date
             AND f.descricao_movimentacao = 'Recebimento Físico'
            GROUP BY d.day, d.purchase_date, f.filial_codigo, f.embalagemid,
                     f.classificacao_n1, f.classificacao_n2, f.classificacao_n3
        ),
        vendas_90d_abc AS (
            SELECT 
                filial_codigo,
                classificacao_n3,
                item_embalagemid AS embalagemid,
                SUM(ABS(item_quantidade)) AS quantidade_vendida
            FROM fact_vendas_final
            WHERE data_date >= DATE '{(data - datetime.timedelta(days=90)).strftime('%Y-%m-%d')}'
              AND data_date <= DATE '{data.strftime('%Y-%m-%d')}'
            GROUP BY filial_codigo, classificacao_n3, item_embalagemid
        ),
        vendas_com_acumulado AS (
            SELECT 
                filial_codigo,
                classificacao_n3,
                embalagemid,
                quantidade_vendida,
                SUM(quantidade_vendida) OVER (
                    PARTITION BY filial_codigo, classificacao_n3 
                    ORDER BY quantidade_vendida DESC
                ) AS quantidade_acum,
                SUM(quantidade_vendida) OVER (PARTITION BY filial_codigo, classificacao_n3) AS total_vendas_grupo
            FROM vendas_90d_abc
        ),
        produtos_com_curva AS (
            SELECT 
                filial_codigo,
                embalagemid,
                CASE 
                    WHEN total_vendas_grupo > 0 AND (quantidade_acum * 100.0 / total_vendas_grupo) <= 50 THEN 'A'
                    WHEN total_vendas_grupo > 0 AND (quantidade_acum * 100.0 / total_vendas_grupo) <= 80 THEN 'B'
                    WHEN total_vendas_grupo > 0 THEN 'C'
                    ELSE 'D'
                END AS curvaABC
            FROM vendas_com_acumulado
        ),
        compras_com_curva AS (
            SELECT
                c.day,
                c.purchase_date,
                c.filial_codigo,
                c.embalagemid,
                c.total_qtde,
                c.total_valor,
                c.customedio_med,
                c.classificacao_n1,
                c.classificacao_n2,
                c.classificacao_n3,
                COALESCE(pc.curvaABC, 'D') AS curvaABC
            FROM compras c
            LEFT JOIN produtos_com_curva pc
              ON c.filial_codigo = pc.filial_codigo AND c.embalagemid = pc.embalagemid
        ),
        vendas_por_compra AS (
            SELECT
                c.day,
                c.purchase_date,
                c.filial_codigo,
                c.embalagemid,
                c.total_qtde,
                c.total_valor,
                c.customedio_med,
                c.classificacao_n1,
                c.classificacao_n2,
                c.classificacao_n3,
                c.curvaABC,
                SUM(CASE WHEN v.data_date BETWEEN c.purchase_date AND c.day THEN 1 ELSE 0 END) AS vendas_cnt,
                SUM(CASE WHEN v.data_date BETWEEN c.purchase_date AND c.day THEN ABS(v.item_quantidade) ELSE 0 END) AS vendas_qtde
            FROM compras_com_curva c
            LEFT JOIN fact_vendas_final v
              ON v.filial_codigo = c.filial_codigo
             AND v.item_embalagemid = c.embalagemid
            GROUP BY c.day, c.purchase_date, c.filial_codigo, c.embalagemid,
                     c.total_qtde, c.total_valor, c.customedio_med,
                     c.classificacao_n1, c.classificacao_n2, c.classificacao_n3, c.curvaABC
        )
        -- 1) curvaABC (rede)
        SELECT
            'Geral' AS filial_codigo,
            curvaABC,
            'Geral' AS classificacao_n1,
            COUNT(DISTINCT embalagemid) AS total_unicos_denom,
            COUNT(DISTINCT CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN embalagemid END) AS produtos_unicos_curva_d,
            SUM(total_qtde) AS total_qtde_all,
            SUM(CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN total_qtde ELSE 0 END) AS total_qtde_curva_d,
            SUM(total_valor) AS total_val_all,
            SUM(CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN total_valor ELSE 0 END) AS total_val_curva_d,
            CASE WHEN COUNT(DISTINCT embalagemid) > 0
                 THEN (COUNT(DISTINCT CASE WHEN vendas_cnt=0 OR vendas_cnt IS NULL THEN embalagemid END)*100.0/COUNT(DISTINCT embalagemid))
                 ELSE 0 END AS indice_curva_d
        FROM vendas_por_compra
        WHERE curvaABC IS NOT NULL
        GROUP BY curvaABC

        UNION ALL
        -- 2) curvaABC + filial
        SELECT
            filial_codigo,
            curvaABC,
            'Geral' AS classificacao_n1,
            COUNT(DISTINCT embalagemid) AS total_unicos_denom,
            COUNT(DISTINCT CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN embalagemid END) AS produtos_unicos_curva_d,
            SUM(total_qtde) AS total_qtde_all,
            SUM(CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN total_qtde ELSE 0 END) AS total_qtde_curva_d,
            SUM(total_valor) AS total_val_all,
            SUM(CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN total_valor ELSE 0 END) AS total_val_curva_d,
            CASE WHEN COUNT(DISTINCT embalagemid) > 0
                 THEN (COUNT(DISTINCT CASE WHEN vendas_cnt=0 OR vendas_cnt IS NULL THEN embalagemid END)*100.0/COUNT(DISTINCT embalagemid))
                 ELSE 0 END AS indice_curva_d
        FROM vendas_por_compra
        WHERE curvaABC IS NOT NULL
        GROUP BY filial_codigo, curvaABC

        UNION ALL
        -- 3) curvaABC + classificacao_n1 (rede)
        SELECT
            'Geral' AS filial_codigo,
            curvaABC,
            classificacao_n1,
            COUNT(DISTINCT embalagemid) AS total_unicos_denom,
            COUNT(DISTINCT CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN embalagemid END) AS produtos_unicos_curva_d,
            SUM(total_qtde) AS total_qtde_all,
            SUM(CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN total_qtde ELSE 0 END) AS total_qtde_curva_d,
            SUM(total_valor) AS total_val_all,
            SUM(CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN total_valor ELSE 0 END) AS total_val_curva_d,
            CASE WHEN COUNT(DISTINCT embalagemid) > 0
                 THEN (COUNT(DISTINCT CASE WHEN vendas_cnt=0 OR vendas_cnt IS NULL THEN embalagemid END)*100.0/COUNT(DISTINCT embalagemid))
                 ELSE 0 END AS indice_curva_d
        FROM vendas_por_compra
        WHERE curvaABC IS NOT NULL AND classificacao_n1 IS NOT NULL
        GROUP BY curvaABC, classificacao_n1

        UNION ALL
        -- 4) curvaABC + filial + classificacao_n1
        SELECT
            filial_codigo,
            curvaABC,
            classificacao_n1,
            COUNT(DISTINCT embalagemid) AS total_unicos_denom,
            COUNT(DISTINCT CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN embalagemid END) AS produtos_unicos_curva_d,
            SUM(total_qtde) AS total_qtde_all,
            SUM(CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN total_qtde ELSE 0 END) AS total_qtde_curva_d,
            SUM(total_valor) AS total_val_all,
            SUM(CASE WHEN vendas_cnt = 0 OR vendas_cnt IS NULL THEN total_valor ELSE 0 END) AS total_val_curva_d,
            CASE WHEN COUNT(DISTINCT embalagemid) > 0
                 THEN (COUNT(DISTINCT CASE WHEN vendas_cnt=0 OR vendas_cnt IS NULL THEN embalagemid END)*100.0/COUNT(DISTINCT embalagemid))
                 ELSE 0 END AS indice_curva_d
        FROM vendas_por_compra
        WHERE curvaABC IS NOT NULL AND classificacao_n1 IS NOT NULL
        GROUP BY filial_codigo, curvaABC, classificacao_n1

        ORDER BY filial_codigo, curvaABC, classificacao_n1
        """

        df = duck_query(sql)
        if df is None or df.empty:
            continue

        df["ano_mes"] = ref_day.strftime("%Y-%m")
        resultados.append(df)

    if not resultados:
        return pd.DataFrame(columns=[
            "ano_mes","filial_codigo","curvaABC","classificacao_n1",
            "total_unicos_denom","produtos_unicos_curva_d",
            "total_qtde_all","total_qtde_curva_d",
            "total_val_all","total_val_curva_d","indice_curva_d"
        ])

    out = pd.concat(resultados, ignore_index=True)

    # Tipagem / arredondamentos
    for c in ["total_unicos_denom","produtos_unicos_curva_d","total_qtde_all","total_qtde_curva_d"]:
        if c in out:
            out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0).astype(int)
    for c in ["total_val_all","total_val_curva_d","indice_curva_d"]:
        if c in out:
            out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0.0)
    out["total_val_all"] = out["total_val_all"].round(2)
    out["total_val_curva_d"] = out["total_val_curva_d"].round(2)
    out["indice_curva_d"] = out["indice_curva_d"].round(4)

    out = out.sort_values(["ano_mes","filial_codigo","curvaABC","classificacao_n1"]).reset_index(drop=True)
    return out

def calcular_desfazimento_curvad_historico(start_month: str = "2024-10",
                                           end_month: str | None = None) -> pd.DataFrame:
    """
    Histórico mensal do indicador de 'desfazimento' Curva D por Curva ABC
    (mesma lógica da função diária calcular_indice_desfazimento_curva_d_por_curva_abc),
    gerando quatro agrupamentos para cada mês (referência = último dia do mês):

      1) curvaABC (filial='Geral', classificacao_n1='Geral')
      2) curvaABC + filial (classificacao_n1='Geral')
      3) curvaABC + classificacao_n1 (filial='Geral')
      4) curvaABC + filial + classificacao_n1

    Métricas:
      total_denom  = DISTINCT embalagemid (candidatos) no agrupamento
      total_numer  = DISTINCT embalagemid vendidos no dia de avaliação (sold_flag=1)
      indice_30d_pct = total_numer * 100 / total_denom (0 se denom 0)

    Saída:
      ano_mes, filial_codigo, curvaABC, classificacao_n1,
      total_denom, total_numer, indice_30d_pct
    """
    def _to_ym(val) -> str:
        if isinstance(val, (datetime.date, datetime.datetime)):
            return val.strftime("%Y-%m")
        s = str(val)
        if re.fullmatch(r"\d{2}-\d{4}", s):
            mm, yyyy = s.split("-")
            return f"{yyyy}-{mm}"
        return s[:7]

    today = datetime.date.today()
    if end_month is None:
        first_this = today.replace(day=1)
        end_month = (first_this - datetime.timedelta(days=1)).strftime("%Y-%m")

    start_month = _to_ym(start_month)
    end_month = _to_ym(end_month)

    def _month_ends(s_ym: str, e_ym: str):
        sy, sm = map(int, s_ym.split("-"))
        ey, em = map(int, e_ym.split("-"))
        cur = datetime.date(sy, sm, 1)
        end = datetime.date(ey, em, 1)
        out = []
        while cur <= end:
            nxt = (cur.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
            out.append(nxt - datetime.timedelta(days=1))
            cur = nxt
        return out

    month_ends = _month_ends(start_month, end_month)
    if not month_ends:
        return pd.DataFrame(columns=[
            "ano_mes","filial_codigo","curvaABC","classificacao_n1",
            "total_denom","total_numer","indice_30d_pct"
        ])

    resultados = []

    for ref_day in month_ends:
        data = ref_day  # mês de referência

        # Construir pares (day, window_start, window_end) últimos 30 dias relativos ao mês
        values = []
        for offset in range(30):
            day = data - datetime.timedelta(days=1 + offset)
            window_start = (day - datetime.timedelta(days=90)).strftime('%Y-%m-%d')
            window_end = (day - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
            values.append((day.strftime('%Y-%m-%d'), window_start, window_end))

        values_sql = ",\n            ".join(
            f"(DATE '{d}', DATE '{ws}', DATE '{we}')" for d, ws, we in values
        )

        sql = f"""
        WITH days(day, window_start, window_end) AS (
            VALUES
            {values_sql}
        ),
        produtos_existentes AS (
            SELECT DISTINCT filial_codigo, embalagemid
            FROM fact_estoque_final
            WHERE filial_codigo IS NOT NULL
        ),
        vendas_90d_abc AS (
            SELECT 
                filial_codigo,
                classificacao_n3,
                item_embalagemid AS embalagemid,
                SUM(ABS(item_quantidade)) AS quantidade_vendida
            FROM fact_vendas_final
            WHERE data_date >= DATE '{(data - datetime.timedelta(days=90)).strftime('%Y-%m-%d')}'
              AND data_date <= DATE '{data.strftime('%Y-%m-%d')}'
            GROUP BY filial_codigo, classificacao_n3, item_embalagemid
        ),
        vendas_com_acumulado AS (
            SELECT
                filial_codigo,
                classificacao_n3,
                embalagemid,
                quantidade_vendida,
                SUM(quantidade_vendida) OVER (
                    PARTITION BY filial_codigo, classificacao_n3
                    ORDER BY quantidade_vendida DESC
                ) AS quantidade_acum,
                SUM(quantidade_vendida) OVER (
                    PARTITION BY filial_codigo, classificacao_n3
                ) AS total_vendas_grupo
            FROM vendas_90d_abc
        ),
        produtos_com_curva AS (
            SELECT
                filial_codigo,
                embalagemid,
                CASE
                    WHEN total_vendas_grupo > 0
                         AND (quantidade_acum * 100.0 / total_vendas_grupo) <= 50 THEN 'A'
                    WHEN total_vendas_grupo > 0
                         AND (quantidade_acum * 100.0 / total_vendas_grupo) <= 80 THEN 'B'
                    WHEN total_vendas_grupo > 0 THEN 'C'
                    ELSE 'D'
                END AS curvaABC
            FROM vendas_com_acumulado
        ),
        todas_compras AS (
            SELECT filial_codigo, embalagemid, DATE(datahora) AS data_compra
            FROM fact_estoque_final
            WHERE descricao_movimentacao = 'Recebimento Físico'
              AND DATE(datahora) >= (SELECT MIN(window_start) FROM days)
              AND DATE(datahora) <= (SELECT MAX(day) FROM days)
        ),
        todas_vendas AS (
            SELECT filial_codigo, item_embalagemid AS embalagemid, data_date AS data_venda
            FROM fact_vendas_final
            WHERE data_date >= (SELECT MIN(window_start) FROM days)
              AND data_date <= (SELECT MAX(day) FROM days)
        ),
        candidatos_por_dia AS (
            SELECT DISTINCT
                d.day,
                p.filial_codigo,
                p.embalagemid,
                COALESCE(pc.curvaABC,'D') AS curvaABC
            FROM days d
            CROSS JOIN produtos_existentes p
            LEFT JOIN produtos_com_curva pc
              ON p.filial_codigo = pc.filial_codigo
             AND p.embalagemid = pc.embalagemid
            WHERE NOT EXISTS (
                SELECT 1 FROM todas_compras c
                 WHERE c.filial_codigo = p.filial_codigo
                   AND c.embalagemid = p.embalagemid
                   AND c.data_compra BETWEEN d.window_start AND d.window_end
            )
              AND NOT EXISTS (
                SELECT 1 FROM todas_vendas v
                 WHERE v.filial_codigo = p.filial_codigo
                   AND v.embalagemid = p.embalagemid
                   AND v.data_venda BETWEEN d.window_start AND d.window_end
            )
        ),
        candidatos_com_classificacao AS (
            SELECT DISTINCT
                c.day,
                c.filial_codigo,
                c.embalagemid,
                c.curvaABC,
                e.classificacao_n1
            FROM candidatos_por_dia c
            LEFT JOIN (
                SELECT
                    filial_codigo,
                    embalagemid,
                    classificacao_n1,
                    ROW_NUMBER() OVER (
                        PARTITION BY filial_codigo, embalagemid
                        ORDER BY datahora DESC
                    ) AS rn
                FROM fact_estoque_final
                WHERE datahora <= DATE '{data.strftime('%Y-%m-%d')}'
            ) e
              ON c.filial_codigo = e.filial_codigo
             AND c.embalagemid = e.embalagemid
             AND e.rn = 1
        ),
        candidatos_vendidos AS (
            SELECT DISTINCT
                c.day,
                c.filial_codigo,
                c.embalagemid,
                c.curvaABC,
                c.classificacao_n1,
                CASE WHEN v.embalagemid IS NOT NULL THEN 1 ELSE 0 END AS sold_flag
            FROM candidatos_com_classificacao c
            LEFT JOIN todas_vendas v
              ON v.filial_codigo = c.filial_codigo
             AND v.embalagemid = c.embalagemid
             AND v.data_venda = c.day
        )
        -- 1) curvaABC (rede)
        SELECT
            'Geral' AS filial_codigo,
            curvaABC,
            'Geral' AS classificacao_n1,
            COUNT(DISTINCT embalagemid) AS total_denom,
            COUNT(DISTINCT CASE WHEN sold_flag=1 THEN embalagemid END) AS total_numer,
            CASE WHEN COUNT(DISTINCT embalagemid)>0
                 THEN (COUNT(DISTINCT CASE WHEN sold_flag=1 THEN embalagemid END)*100.0/
                       COUNT(DISTINCT embalagemid))
                 ELSE 0 END AS indice_30d_pct
        FROM candidatos_vendidos
        WHERE curvaABC IS NOT NULL
        GROUP BY curvaABC

        UNION ALL
        -- 2) curvaABC + filial
        SELECT
            filial_codigo,
            curvaABC,
            'Geral' AS classificacao_n1,
            COUNT(DISTINCT embalagemid) AS total_denom,
            COUNT(DISTINCT CASE WHEN sold_flag=1 THEN embalagemid END) AS total_numer,
            CASE WHEN COUNT(DISTINCT embalagemid)>0
                 THEN (COUNT(DISTINCT CASE WHEN sold_flag=1 THEN embalagemid END)*100.0/
                       COUNT(DISTINCT embalagemid))
                 ELSE 0 END AS indice_30d_pct
        FROM candidatos_vendidos
        WHERE curvaABC IS NOT NULL
        GROUP BY filial_codigo, curvaABC

        UNION ALL
        -- 3) curvaABC + classificacao_n1 (rede)
        SELECT
            'Geral' AS filial_codigo,
            curvaABC,
            classificacao_n1,
            COUNT(DISTINCT embalagemid) AS total_denom,
            COUNT(DISTINCT CASE WHEN sold_flag=1 THEN embalagemid END) AS total_numer,
            CASE WHEN COUNT(DISTINCT embalagemid)>0
                 THEN (COUNT(DISTINCT CASE WHEN sold_flag=1 THEN embalagemid END)*100.0/
                       COUNT(DISTINCT embalagemid))
                 ELSE 0 END AS indice_30d_pct
        FROM candidatos_vendidos
        WHERE curvaABC IS NOT NULL AND classificacao_n1 IS NOT NULL
        GROUP BY curvaABC, classificacao_n1

        UNION ALL
        -- 4) curvaABC + filial + classificacao_n1
        SELECT
            filial_codigo,
            curvaABC,
            classificacao_n1,
            COUNT(DISTINCT embalagemid) AS total_denom,
            COUNT(DISTINCT CASE WHEN sold_flag=1 THEN embalagemid END) AS total_numer,
            CASE WHEN COUNT(DISTINCT embalagemid)>0
                 THEN (COUNT(DISTINCT CASE WHEN sold_flag=1 THEN embalagemid END)*100.0/
                       COUNT(DISTINCT embalagemid))
                 ELSE 0 END AS indice_30d_pct
        FROM candidatos_vendidos
        WHERE curvaABC IS NOT NULL AND classificacao_n1 IS NOT NULL
        GROUP BY filial_codigo, curvaABC, classificacao_n1

        ORDER BY filial_codigo, curvaABC, classificacao_n1
        """

        df_mes = duck_query(sql)
        if df_mes is None or df_mes.empty:
            continue

        df_mes["ano_mes"] = ref_day.strftime("%Y-%m")
        resultados.append(df_mes)

    if not resultados:
        return pd.DataFrame(columns=[
            "ano_mes","filial_codigo","curvaABC","classificacao_n1",
            "total_denom","total_numer","indice_30d_pct"
        ])

    out = pd.concat(resultados, ignore_index=True)

    # Tipos / ajustes
    for c in ["total_denom","total_numer"]:
        if c in out:
            out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0).astype(int)
    if "indice_30d_pct" in out:
        out["indice_30d_pct"] = pd.to_numeric(out["indice_30d_pct"], errors="coerce").fillna(0.0).round(4)

    out = out.sort_values(["ano_mes","filial_codigo","curvaABC","classificacao_n1"]).reset_index(drop=True)
    return out