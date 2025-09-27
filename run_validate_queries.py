from data_processing.etl.validate_schemas import validate_queries, dry_run_build

probs = validate_queries()
if probs:
    print("❌ Faltam colunas:")
    for t, miss in probs.items():
        print(f"  - {t}: {miss}")
else:
    print("✅ Todas as colunas exigidas presentes. Testando build...")
    try:
        dry_run_build()
        print("✅ Build passou (sem baixar dados).")
    except Exception as e:
        print("❌ Falhou no build:", e)