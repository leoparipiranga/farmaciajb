from core.database import init_duck_warehouse
from data_processing.etl.transformations import refresh_facts_final
import time

print("🔄 Iniciando atualização do warehouse DuckDB...")
start_time = time.time()

# 1. Carregar todas as tabelas do PostgreSQL para o DuckDB
wh = init_duck_warehouse(load_from_pg=True)  # carrega todas as tabelas

# 2. Criar tabelas de fatos finais
print("\n🔧 Criando tabelas finais...")
results = refresh_facts_final(wh)

# 3. Mostrar resultados
print("\n✅ Warehouse atualizado com sucesso!")
print(f"    - fact_vendas_final: {results['fact_vendas_final']:,} linhas")
print(f"    - fact_estoque_final: {results['fact_estoque_final']:,} linhas")
print(f"\n⏱️ Tempo total: {(time.time() - start_time):.1f} segundos")

# 4. Fechar conexão
wh.close()