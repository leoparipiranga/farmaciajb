from core.database import init_duck_warehouse
from data_processing.etl.transformations import refresh_facts_final
from run_views import build_views
from data_processing.estoque import historico as hist
from datetime import date
import time

print("🔄 Iniciando atualização do warehouse DuckDB...")
start_time = time.time()

# 1. Carregar todas as tabelas do PostgreSQL para o DuckDB
wh = init_duck_warehouse(load_from_pg=True)

# 2. Criar tabelas de fatos finais
print("\n🔧 Criando tabelas finais...")
results = refresh_facts_final(wh)

# Fecha a conexão usada no ETL antes de abrir novas conexões (run_views, histórico, etc.)
wh.close()

# 3. Regenerar views
data_ref = date.today().isoformat()
print("\n🧱 Regenerando views auxiliares...")
build_views(data_ref)

# 4. Atualizar caches históricos
print("\n📚 Atualizando históricos de estoque...")
hist_funcs = [
    ("Disponibilidade", hist.build_or_update_hist_disponibilidade),
    ("Giro", hist.build_or_update_hist_giro),
    ("Cobertura", hist.build_or_update_hist_cobertura),
    ("GMROI", hist.build_or_update_hist_gmroi),
    ("Curva D", hist.build_or_update_hist_curvad),
    ("Desfazimento Curva D", hist.build_or_update_hist_desfazimento),
]

for nome, func in hist_funcs:
    linhas = len(func(force_full=False))
    print(f"    - {nome}: {linhas:,} registros")

# 5. Mostrar resultados finais
print("\n✅ Warehouse atualizado com sucesso!")
print(f"    - fact_vendas_final: {results['fact_vendas_final']:,} linhas")
print(f"    - fact_estoque_final: {results['fact_estoque_final']:,} linhas")
print(f"\n⏱️ Tempo total: {(time.time() - start_time):.1f} segundos")

wh.close()