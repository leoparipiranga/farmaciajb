import duckdb
from data_processing.etl.transformations import build_fact_vendas_final, build_fact_estoque_final
from data_processing.etl.queries import query

# Mapear colunas esperadas (alias) por base conforme transformations.py
REQUIRED = {
    'venda': [
        'venda_status','venda_id','venda_caixaid','venda_unidadenegocioid',
        'venda_usuarioid','venda_pessoaid','venda_orcamentoid',
        'venda_datahoraabertura','venda_datahorafechamento'
    ],
    'item': [
        'item_sequencia','item_vendaid','item_embalagemid','item_status',
        'item_quantidade','item_valorunitario','item_origemdesconto',
        'item_tipodesconto','item_desconto','item_valortotal',
        'item_cadernoofertaid','item_valordesconto','item_movimentacaoestoque'
    ],
    'orcamento': [
        'orcamento_id','orcamento_codigo','orcamento_vendaid','orcamento_datahora',
        'orcamento_usuarioid','orcamento_unidadenegocioid','orcamento_formapagamentoid',
        'orcamento_pessoaid','orcamento_cpfcnpjconsumidor'
    ],
    'embalagem': [
        'embalagem_id','embalagem_produtoid','embalagem_codigobarras',
        'embalagem_descricao','embalagem_precoreferencial','embalagem_markup',
        'embalagem_precovenda','embalagem_etiqueta','embalagem_apresentacao',
        'embalagem_precovendavariavel'
    ],
    'produto': [
        'produto_id','produto_status','produto_codigo','produto_fabricanteid','produto_movimentacaofracionada'
    ],
    'filial': ['id','codigo','nome'],
    'usuario': ['id','apelido'],
    'formapagamento': ['formapagamento_id','formapagamento_nome'],
    'custoproduto': ['custo_produtoid','custoproduto_unidadenegocioid','customedio'],
    'classificacao': ['classificacao_id','classificacao_nome','classificacao_caminho'],
    'classificacaoproduto': ['classificacaoproduto_produtoid','classificacaoproduto_classificacaoid'],
    'estoque': ['*'],  # usado com SELECT * (mantemos sem testes finos)
    'tipomovimentacaoestoque': ['tipomovestoque','descricao_movimentacao'],
    'fabricante': ['fabricante_id','pessoa_id_fabricante'],
    'pessoa': ['id','nome','tipo','cpf','datanascimento','sexo','razaosocial','cnpj','status'],
    'cadernooferta': ['*']
}

def _extract_aliases(sql: str):
    # Simples: pega tokens "AS alias" (case-insensitive)
    import re
    return [m.group(1) for m in re.finditer(r'\bAS\s+([a-zA-Z0-9_]+)', sql, flags=re.IGNORECASE)]

def validate_queries():
    problems = {}
    for name, sql in query.items():
        if name not in REQUIRED:
            continue
        if REQUIRED[name] == ['*']:
            continue
        aliases = set(_extract_aliases(sql))
        missing = [c for c in REQUIRED[name] if c not in aliases]
        if missing:
            problems[name] = missing
    return problems

def dry_run_build():
    """
    Cria tabelas vazias com colunas mínimas (tipos genéricos) e executa os builds.
    Se algum alias estiver faltando, DuckDB levantará erro.
    """
    con = duckdb.connect(":memory:")
    for table, cols in REQUIRED.items():
        if cols == ['*']:
            # Criar placeholder simplificado
            con.execute(f"CREATE TABLE {table} (dummy INTEGER);")
            continue
        cols_def = ", ".join(f"{c} VARCHAR" for c in cols)
        con.execute(f"CREATE TABLE {table} ({cols_def});")
    # Wrap em objeto simples com atributo conn
    class WH: pass
    wh = WH()
    wh.conn = con
    build_fact_vendas_final(wh)
    build_fact_estoque_final(wh)
    return True

if __name__ == "__main__":
    probs = validate_queries()
    if probs:
        print("❌ Inconsistências encontradas:")
        for t, miss in probs.items():
            print(f"  - {t}: faltando {miss}")
    else:
        print("✅ Alias: OK. Testando build em memória...")
        try:
            dry_run_build()
            print("✅ Build de fact tables concluído (schemas válidos).")
        except Exception as e:
            print("❌ Erro no build:", e)