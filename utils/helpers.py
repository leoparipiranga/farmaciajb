import pandas as pd
from datetime import date

def _escape(v: str) -> str:
    return str(v).replace("'", "''")

def _bounds_mes_atual(data_ref: date | None):
    # D-1 por padrão
    if data_ref is None:
        data_ref = pd.Timestamp("today").date() - pd.Timedelta(days=1)
    data_ref = pd.Timestamp(data_ref).date()
    data_ini = pd.Timestamp(data_ref).replace(day=1).date()
    return data_ini, data_ref

def _cond_filial(filial_codigo: str | None) -> str:
    if filial_codigo and str(filial_codigo).strip().lower() != "todas as filiais":
        return f"AND CAST(filial_codigo AS VARCHAR) = '{_escape(filial_codigo)}'"
    return ""

def _extract_codigo_from_nome(nome: str) -> str:
    return nome.split()[0].zfill(2) if nome else "00"

def _weekday_labels(cols_idx):
    mapa = {0: "Seg", 1: "Ter", 2: "Qua", 3: "Qui", 4: "Sex", 5: "Sáb", 6: "Dom"}
    return [mapa.get(i, str(i)) for i in cols_idx]

def _make_pivot_for_filial(base_df, horas_range):
    # Helper to create pivot from grouped data
    pivot = base_df.pivot_table(index='hora', columns='weekday', values='qtd', aggfunc='sum', fill_value=0)
    pivot = pivot.reindex(index=horas_range, fill_value=0)
    for wd in range(7):
        if wd not in pivot.columns:
            pivot[wd] = 0
    pivot = pivot[sorted(pivot.columns)]
    return pivot

# Constantes
EMPREGADOS_POR_FILIAL = {
    "01":15,"02":10,"03":19,"04":20,"05":9,"06":8,"07":8,"08":10,"09":12,"10":7,"11":12,"12":8,"13":5
}
