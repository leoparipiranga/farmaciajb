def build_fact_vendas_final(wh):
    """
    Recria a tabela final de vendas (equivalente ao DataMerger.create_vendas_completas).
    Requer tabelas base no DuckDB: venda, item, orcamento, usuario, embalagem, produto,
    filial, pessoa, formapagamento, custoproduto, classificacao, classificacaoproduto.
    """
    sql = """
    CREATE OR REPLACE TABLE fact_vendas_final AS
    WITH v AS (
        SELECT 
            venda_id,
            venda_status,
            venda_caixaid,
            venda_unidadenegocioid,
            venda_usuarioid,
            venda_pessoaid,
            venda_orcamentoid,
            venda_datahoraabertura,
            venda_datahorafechamento
        FROM venda
        WHERE venda_status = 'F'
    ),
    i AS (
        SELECT 
            item_vendaid,
            item_sequencia,
            item_embalagemid,
            item_quantidade,
            item_valorunitario,
            item_origemdesconto,
            item_tipodesconto,
            item_desconto,
            item_valortotal,
            item_cadernoofertaid,
            item_valordesconto,
            item_movimentacaoestoque            
        FROM item
        WHERE item_status = 'F'
    ),
    o AS (
        SELECT 
            orcamento_id,
            orcamento_codigo,
            orcamento_datahora,
            orcamento_usuarioid,
            orcamento_unidadenegocioid,
            orcamento_formapagamentoid,
            orcamento_pessoaid,
            orcamento_cpfcnpjconsumidor,
            orcamento_vendaid
        FROM orcamento
    ),
    emb AS (
        SELECT *
        FROM embalagem
    ),
    p AS (
        SELECT *
        FROM produto
    ),
    fil AS (
        SELECT 
            id AS filial_id,
            CAST(codigo AS VARCHAR) AS filial_codigo,
            nome AS filial_nome
        FROM filial
    ),
    usr AS (
        SELECT 
            id AS usuario_orcamento_id,
            apelido AS vendedor_nome
        FROM usuario
    ),
    fp AS (
        SELECT 
            formapagamento_id,
            formapagamento_nome
        FROM formapagamento
    ),
    cp AS (
        SELECT 
            custoproduto_unidadenegocioid,
            custo_produtoid,
            customedio
        FROM custoproduto
    ),
    cprod AS (
        SELECT
            classificacaoproduto_produtoid,
            classificacaoproduto_classificacaoid
        FROM classificacaoproduto
    ),
    cls AS (
        SELECT
            classificacao_id,
            classificacao_nome,
            classificacao_caminho
        FROM classificacao
    )
    SELECT
        -- venda
        v.*,
        -- item
        i.item_sequencia,
        i.item_embalagemid,
        i.item_quantidade,
        i.item_valorunitario,
        i.item_origemdesconto,
        i.item_tipodesconto,
        i.item_desconto,
        i.item_valortotal,
        i.item_cadernoofertaid,
        i.item_valordesconto,
        i.item_movimentacaoestoque,
        -- orcamento
        o.orcamento_id,
        o.orcamento_codigo,
        o.orcamento_datahora,
        o.orcamento_usuarioid,
        o.orcamento_unidadenegocioid,
        o.orcamento_formapagamentoid,
        o.orcamento_pessoaid,
        o.orcamento_cpfcnpjconsumidor,
        -- embalagem
        emb.embalagem_codigobarras,
        emb.embalagem_etiqueta,
        emb.embalagem_descricao,
        emb.embalagem_apresentacao,
        emb.embalagem_precoreferencial,
        emb.embalagem_markup,
        emb.embalagem_precovenda,
        emb.embalagem_precovendavariavel,
        -- produto
        p.produto_id,
        p.produto_status,
        p.produto_codigo,
        p.produto_fabricanteid,
        -- custo
        cp.customedio,
        -- filial
        fil.filial_id,
        fil.filial_codigo,
        fil.filial_nome,
        -- vendedor
        usr.vendedor_nome,
        -- forma de pagamento
        fp.formapagamento_nome,
        -- classificação
        cls.classificacao_id,
        cls.classificacao_nome,
        cls.classificacao_caminho,
        -- derivadas de data
        CAST(v.venda_datahorafechamento AS DATE) AS data_venda_apenas,
        v.venda_datahorafechamento AS datahora,
        CAST(v.venda_datahorafechamento AS DATE) AS data_date,
        -- derivadas de classificação (padrão do pandas: ignora o primeiro segmento)
        TRIM(split_part(cls.classificacao_caminho, '>', 2)) AS classificacao_n1,
        TRIM(split_part(cls.classificacao_caminho, '>', 3)) AS classificacao_n2,
        TRIM(split_part(cls.classificacao_caminho, '>', 4)) AS classificacao_n3,
        -- derivadas de valores
        (COALESCE(cp.customedio, 0) * COALESCE(i.item_quantidade, 0)) AS customediototal,
        (COALESCE(i.item_valordesconto, 0) * COALESCE(i.item_quantidade, 0)) AS valordescontototal
    FROM v
    JOIN i    ON i.item_vendaid = v.venda_id
    LEFT JOIN o   ON o.orcamento_id = v.venda_orcamentoid
    LEFT JOIN emb ON emb.embalagem_id = i.item_embalagemid
    LEFT JOIN p   ON p.produto_id = emb.embalagem_produtoid
    LEFT JOIN cp  ON cp.custoproduto_unidadenegocioid = v.venda_unidadenegocioid
                 AND cp.custo_produtoid = p.produto_id
    LEFT JOIN fil ON fil.filial_id = v.venda_unidadenegocioid
    LEFT JOIN usr ON usr.usuario_orcamento_id = o.orcamento_usuarioid
    LEFT JOIN fp  ON fp.formapagamento_id = o.orcamento_formapagamentoid
    LEFT JOIN cprod ON cprod.classificacaoproduto_produtoid = p.produto_id
    LEFT JOIN cls   ON cls.classificacao_id = cprod.classificacaoproduto_classificacaoid
    ORDER BY data_date, v.venda_id, i.item_sequencia
    ;
    """
    wh.conn.execute(sql)
    wh.conn.execute("ANALYZE fact_vendas_final")

def build_fact_estoque_final(wh):
    """
    Recria a tabela final de estoque (equivalente ao DataMerger.create_estoque_completo).
    Requer tabelas base no DuckDB: estoque (movimentacaoestoque), embalagem, produto, filial,
    tipomovimentacaoestoque, classificacao, classificacaoproduto, fabricante, pessoa.
    """
    sql = """
    CREATE OR REPLACE TABLE fact_estoque_final AS
    WITH me AS (
        SELECT *
        FROM estoque
    ),
    emb AS (
        SELECT *
        FROM embalagem
    ),
    p AS (
        SELECT *
        FROM produto
    ),
    fil AS (
        SELECT 
            id AS filial_id,
            CAST(codigo AS VARCHAR) AS filial_codigo,
            nome AS filial_nome
        FROM filial
    ),
    tme AS (
        SELECT 
            tipomovestoque,
            descricao_movimentacao
        FROM tipomovimentacaoestoque
    ),
    cprod AS (
        SELECT
            classificacaoproduto_produtoid,
            classificacaoproduto_classificacaoid
        FROM classificacaoproduto
    ),
    cls AS (
        SELECT
            classificacao_id,
            classificacao_nome,
            classificacao_caminho
        FROM classificacao
    ),
    fab AS (
        SELECT 
            fabricante_id,
            pessoa_id_fabricante
        FROM fabricante
    ),
    pes AS (
        SELECT 
            id AS pessoa_id,
            nome AS pessoa_nome
        FROM pessoa
    )
    SELECT
        -- estoque (movimentação)
        me.*,
        -- embalagem
        emb.embalagem_id,
        emb.embalagem_codigobarras,
        emb.embalagem_etiqueta,
        emb.embalagem_descricao,
        emb.embalagem_apresentacao,
        emb.embalagem_precoreferencial,
        emb.embalagem_markup,
        emb.embalagem_precovenda,
        emb.embalagem_precovendavariavel,
        -- produto
        p.produto_id,
        p.produto_codigo,
        p.produto_fabricanteid,
        -- filial
        fil.filial_id,
        fil.filial_codigo,
        fil.filial_nome,
        -- tipo de movimentação
        tme.descricao_movimentacao,
        -- classificação
        cls.classificacao_id,
        cls.classificacao_nome,
        cls.classificacao_caminho,
        TRIM(split_part(cls.classificacao_caminho, '>', 2)) AS classificacao_n1,
        TRIM(split_part(cls.classificacao_caminho, '>', 3)) AS classificacao_n2,
        TRIM(split_part(cls.classificacao_caminho, '>', 4)) AS classificacao_n3,
        -- fabricante (nome)
        pes.pessoa_nome AS fabricante_nome
    FROM me
    LEFT JOIN emb ON emb.embalagem_id = me.embalagemid
    LEFT JOIN p   ON p.produto_id = emb.embalagem_produtoid
    LEFT JOIN fil ON fil.filial_id = me.unidadenegocioid
    LEFT JOIN tme ON tme.tipomovestoque = me.tipomovimentacaoestoqueid
    LEFT JOIN cprod ON cprod.classificacaoproduto_produtoid = p.produto_id
    LEFT JOIN cls   ON cls.classificacao_id = cprod.classificacaoproduto_classificacaoid
    LEFT JOIN fab   ON fab.fabricante_id = p.produto_fabricanteid
    LEFT JOIN pes   ON pes.pessoa_id = fab.pessoa_id_fabricante
    ;
    """
    wh.conn.execute(sql)
    wh.conn.execute("ANALYZE fact_estoque_final")

def refresh_facts_final(wh):
    """
    Recria as duas bases finais. Carregue antes as tabelas base no DuckDB.
    """
    build_fact_vendas_final(wh)
    build_fact_estoque_final(wh)
    # Retorna contagens para sanity check
    vendas_cnt = wh.conn.execute("SELECT COUNT(*) FROM fact_vendas_final").fetchone()[0]
    estoque_cnt = wh.conn.execute("SELECT COUNT(*) FROM fact_estoque_final").fetchone()[0]
    return {'fact_vendas_final': vendas_cnt, 'fact_estoque_final': estoque_cnt}