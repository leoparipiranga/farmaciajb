# -------------------------
# Queries (ajustadas para conter TODAS as colunas usadas em transformations.build_fact_vendas_final / build_fact_estoque_final)
# Se remover algo aqui que é referenciado nos builds, a criação das fact_* quebra.
# -------------------------
query = {
    'venda': """
        SELECT DISTINCT 
            v.status            AS venda_status,
            v.id                AS venda_id,
            v.caixaid           AS venda_caixaid,
            v.unidadenegocioid  AS venda_unidadenegocioid,
            v.usuarioid         AS venda_usuarioid,
            v.pessoaid          AS venda_pessoaid,
            v.orcamentoid       AS venda_orcamentoid,
            v.datahoraabertura  AS venda_datahoraabertura,
            v.datahorafechamento AS venda_datahorafechamento
        FROM public.venda v
        WHERE v.datahorafechamento >= '2024-01-01 00:00:00'
          AND v.status = 'F'
    """,
    'orcamento': """
        SELECT DISTINCT 
            o.id                AS orcamento_id,
            o.codigo            AS orcamento_codigo,
            o.vendaid           AS orcamento_vendaid,
            o.datahora          AS orcamento_datahora,
            o.usuarioid         AS orcamento_usuarioid,
            o.unidadenegocioid  AS orcamento_unidadenegocioid,
            o.formapagamentoid  AS orcamento_formapagamentoid,
            o.pessoaid          AS orcamento_pessoaid,
            o.cpfcnpjconsumidor AS orcamento_cpfcnpjconsumidor
        FROM public.orcamento o
        WHERE o.datahora >= '2024-01-01 00:00:00'
    """,
    'estoque': """
        SELECT *
        FROM public.movimentacaoestoque
        WHERE datahora >= '2024-01-01 00:00:00'
    """,
    'item': """
        SELECT DISTINCT 
            i.sequencia          AS item_sequencia,
            i.vendaid            AS item_vendaid,
            i.embalagemid        AS item_embalagemid,
            i.status             AS item_status,
            i.quantidade         AS item_quantidade,
            i.valorunitario      AS item_valorunitario,
            i.origemdesconto     AS item_origemdesconto,
            i.tipodesconto       AS item_tipodesconto,
            i.desconto           AS item_desconto,
            i.valortotal         AS item_valortotal,
            i.cadernoofertaid    AS item_cadernoofertaid,
            i.valordesconto      AS item_valordesconto,
            i.movimentacaoestoqueid AS item_movimentacaoestoque
        FROM public.itemvenda i
        INNER JOIN public.venda v ON v.id = i.vendaid
        WHERE v.datahorafechamento >= '2024-01-01 00:00:00'
          AND i.status = 'F'
    """,
    'filial': """
        SELECT id, codigo, nome
        FROM public.unidadenegocio
        WHERE status = 'A' AND id <> 1
    """,
    'usuario': """
        SELECT id, apelido
        FROM public.usuario
    """,
    'pessoa': """
        SELECT id, nome, tipo, cpf, datanascimento, sexo, razaosocial, cnpj, status
        FROM public.pessoa
        WHERE status = 'A'
    """,
    'caixa': """
        SELECT DISTINCT 
            c.id        AS caixa_id,
            c.numero    AS caixa_numero,
            c.descricao AS caixa_descricao
        FROM public.caixa c
    """,
    'embalagem': """
        SELECT DISTINCT 
            e.id              AS embalagem_id,
            e.produtoid       AS embalagem_produtoid,
            e.codigobarras    AS embalagem_codigobarras,
            e.descricao       AS embalagem_descricao,
            e.precoreferencial AS embalagem_precoreferencial,
            e.markup          AS embalagem_markup,
            e.precovenda      AS embalagem_precovenda,
            -- Colunas adicionais usadas nas facts:
            e.etiqueta        AS embalagem_etiqueta,
            e.apresentacao    AS embalagem_apresentacao,
            e.precovendavariavel AS embalagem_precovendavariavel
        FROM public.embalagem e
    """,
    'produto': """
        SELECT DISTINCT 
            p.id                 AS produto_id,
            p.status             AS produto_status,
            p.codigo             AS produto_codigo,
            p.fabricanteid       AS produto_fabricanteid,
            p.movimentacaofracionada AS produto_movimentacaofracionada
        FROM public.produto p
    """,
    'caderno': """
        SELECT c.id, c.nome
        FROM public.cadernooferta c
    """,
    'classificacao': """
        SELECT
            c.id      AS classificacao_id,
            c.nome    AS classificacao_nome,
            c.caminho AS classificacao_caminho
        FROM public.classificacao c
    """,
    'classificacaoproduto': """
        SELECT
            cp.produtoid      AS classificacaoproduto_produtoid,
            cp.classificacaoid AS classificacaoproduto_classificacaoid
        FROM public.classificacaoproduto cp
        WHERE cp.classificacaoid <> 50000103706
    """,
    'tipomovimentacaoestoque': """
        SELECT
            t.id        AS tipomovestoque,
            t.descricao AS descricao_movimentacao
        FROM public.tipomovimentacaoestoque t
    """,
    'formapagamento': """
        SELECT
            f.id   AS formapagamento_id,
            f.nome AS formapagamento_nome
        FROM public.formapagamento f
    """,
    'custoproduto': """
        SELECT
            c.produtoid        AS custo_produtoid,
            c.unidadenegocioid AS custoproduto_unidadenegocioid,
            c.customedio
        FROM public.custoproduto c
    """,
    'cadernooferta': "SELECT * FROM public.cadernooferta",
    'fabricante': """
        SELECT
            f.id      AS fabricante_id,
            f.pessoaid AS pessoa_id_fabricante
        FROM public.fabricante f
    """,
}