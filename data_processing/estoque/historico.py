import os
from pathlib import Path
import pandas as pd
import datetime
from typing import Optional, List
from data_processing.estoque.funcoes_historico import (
    calcular_disponibilidade_historico,
    calcular_giro_historico,
    calcular_cobertura_historico,
    calcular_gmroi_historico,
    calcular_curvad_historico,
    calcular_desfazimento_curvad_historico
)

# Suporte quando executar diretamente via "python data_processing\estoque\historico.py"
if __package__ is None or __package__ == "":
    # garante que o diretório raiz (onde está data_processing) entre no sys.path
    import sys
    ROOT = Path(__file__).resolve().parents[2]  # sprintdfarma/
    if str(ROOT) not in sys.path:
        sys.path.append(str(ROOT))
    # agora podemos importar usando caminho relativo ao pacote
    from data_processing.estoque.funcoes_historico import (
        calcular_disponibilidade_historico,
        calcular_giro_historico,
        calcular_cobertura_historico,
        calcular_gmroi_historico,
        calcular_curvad_historico,
        calcular_desfazimento_curvad_historico
    )
else:
    # quando rodar com -m usa import relativo
    from .funcoes_historico import (
        calcular_disponibilidade_historico,
        calcular_giro_historico,
        calcular_cobertura_historico,
        calcular_gmroi_historico,
        calcular_curvad_historico,
        calcular_desfazimento_curvad_historico
    )

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HIST_DIR = PROJECT_ROOT / "historico_cache"
HIST_DIR.mkdir(exist_ok=True)

# Arquivos (disponibilidade)
PARQUET_PATH_DISP = HIST_DIR / "hist_disponibilidade.parquet"
MARKER_PATH_DISP = HIST_DIR / "last_closed_month_disp.txt"

# Arquivos (giro)
PARQUET_PATH_GIRO = HIST_DIR / "hist_giro.parquet"
MARKER_PATH_GIRO = HIST_DIR / "last_closed_month_giro.txt"

# Arquivos (cobertura)
PARQUET_PATH_COB = HIST_DIR / "hist_cobertura.parquet"
MARKER_PATH_COB = HIST_DIR / "last_closed_month_cobertura.txt"

# Arquivos (GMROI)
PARQUET_PATH_GMROI = HIST_DIR / "hist_gmroi.parquet"
MARKER_PATH_GMROI = HIST_DIR / "last_closed_month_gmroi.txt"

# Arquivos (Curva D)
PARQUET_PATH_CURVAD = HIST_DIR / "hist_curvad.parquet"
MARKER_PATH_CURVAD = HIST_DIR / "last_closed_month_curvad.txt"

# Arquivos (Desfazimento Curva D)
PARQUET_PATH_DESF = HIST_DIR / "hist_desfazimento_curvad.parquet"
MARKER_PATH_DESF = HIST_DIR / "last_closed_month_desfazimento_curvad.txt"

START_MONTH = "2024-10"  # inclusive

# ---------- Helpers comuns ----------
def _ultimo_mes_fechado(today: Optional[datetime.date] = None) -> datetime.date:
    today = today or datetime.date.today()
    first_this = today.replace(day=1)
    return first_this - datetime.timedelta(days=1)

def _iter_month_ends(start_ym: str, end_date: datetime.date) -> List[datetime.date]:
    y, m = map(int, start_ym.split("-"))
    current = datetime.date(y, m, 1)
    out = []
    while current <= end_date.replace(day=1):
        nxt = (current.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
        month_end = nxt - datetime.timedelta(days=1)
        if month_end <= end_date:
            out.append(month_end)
        current = nxt
    return out

def _read_marker(path: Path) -> Optional[str]:
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return None

def _write_marker(path: Path, ym: str):
    path.write_text(ym, encoding="utf-8")

def _load_existing(path: Path) -> pd.DataFrame:
    if path.exists():
        return pd.read_parquet(path)
    return pd.DataFrame()

# ---------- Disponibilidade ----------
def build_or_update_hist_disponibilidade(force_full: bool = False) -> pd.DataFrame:
    ultimo_fechado = _ultimo_mes_fechado()
    ultimo_ym = ultimo_fechado.strftime("%Y-%m")
    existing = _load_existing(PARQUET_PATH_DISP)

    # Rebuild completo
    if force_full or existing.empty:
        hist = calcular_disponibilidade_historico(START_MONTH, ultimo_ym)
        if not hist.empty:
            hist.to_parquet(PARQUET_PATH_DISP, index=False)
            _write_marker(MARKER_PATH_DISP, ultimo_ym)
        return hist

    marker = _read_marker(MARKER_PATH_DISP)
    if marker is None:
        return build_or_update_hist_disponibilidade(force_full=True)

    if marker >= ultimo_ym:
        return existing  # nada novo

    # Incremental: meses após marker
    y, m = map(int, marker.split("-"))
    next_month_first = (datetime.date(y, m, 28) + datetime.timedelta(days=4)).replace(day=1)
    months_missing = _iter_month_ends(next_month_first.strftime("%Y-%m"), ultimo_fechado)

    new_parts = []
    for me in months_missing:
        ym = me.strftime("%Y-%m")
        df_one = calcular_disponibilidade_historico(ym, ym)  # apenas o mês
        if not df_one.empty:
            new_parts.append(df_one)

    if new_parts:
        new_df = pd.concat(new_parts, ignore_index=True)
        hist = pd.concat([existing, new_df], ignore_index=True)
        hist.to_parquet(PARQUET_PATH_DISP, index=False)
        _write_marker(MARKER_PATH_DISP, ultimo_ym)
        return hist

    return existing

def load_hist_disponibilidade(include_current_partial: bool = False) -> pd.DataFrame:
    hist = _load_existing(PARQUET_PATH_DISP)
    if include_current_partial:
        today = datetime.date.today()
        current_ym = today.strftime("%Y-%m")
        # Se já materializado (após fechamento), não recalcula
        if current_ym not in hist.get("ano_mes", pd.Series(dtype=str)).unique():
            parcial = calcular_disponibilidade_historico(current_ym, current_ym)
            if not parcial.empty:
                hist = pd.concat([hist, parcial], ignore_index=True)
    return hist

# ---------- Giro ----------
def build_or_update_hist_giro(force_full: bool = False) -> pd.DataFrame:
    ultimo_fechado = _ultimo_mes_fechado()
    ultimo_ym = ultimo_fechado.strftime("%Y-%m")
    existing = _load_existing(PARQUET_PATH_GIRO)

    if force_full or existing.empty:
        hist = calcular_giro_historico(START_MONTH, ultimo_ym)
        if not hist.empty:
            hist.to_parquet(PARQUET_PATH_GIRO, index=False)
            _write_marker(MARKER_PATH_GIRO, ultimo_ym)
        return hist

    marker = _read_marker(MARKER_PATH_GIRO)
    if marker is None:
        return build_or_update_hist_giro(force_full=True)

    if marker >= ultimo_ym:
        return existing

    y, m = map(int, marker.split("-"))
    next_month_first = (datetime.date(y, m, 28) + datetime.timedelta(days=4)).replace(day=1)
    months_missing = _iter_month_ends(next_month_first.strftime("%Y-%m"), ultimo_fechado)

    new_parts = []
    for me in months_missing:
        ym = me.strftime("%Y-%m")
        df_one = calcular_giro_historico(ym, ym)
        if not df_one.empty:
            new_parts.append(df_one)

    if new_parts:
        new_df = pd.concat(new_parts, ignore_index=True)
        hist = pd.concat([existing, new_df], ignore_index=True)
        hist.to_parquet(PARQUET_PATH_GIRO, index=False)
        _write_marker(MARKER_PATH_GIRO, ultimo_ym)
        return hist

    return existing

def load_hist_giro(include_current_partial: bool = False) -> pd.DataFrame:
    hist = _load_existing(PARQUET_PATH_GIRO)
    if include_current_partial:
        today = datetime.date.today()
        current_ym = today.strftime("%Y-%m")
        if current_ym not in hist.get("ano_mes", pd.Series(dtype=str)).unique():
            parcial = calcular_giro_historico(current_ym, current_ym)
            if not parcial.empty:
                hist = pd.concat([hist, parcial], ignore_index=True)
    return hist

# ---------- Cobertura ----------
def build_or_update_hist_cobertura(force_full: bool = False) -> pd.DataFrame:
    ultimo_fechado = _ultimo_mes_fechado()
    ultimo_ym = ultimo_fechado.strftime("%Y-%m")
    existing = _load_existing(PARQUET_PATH_COB)

    if force_full or existing.empty:
        hist = calcular_cobertura_historico(START_MONTH, ultimo_ym)
        if not hist.empty:
            hist.to_parquet(PARQUET_PATH_COB, index=False)
            _write_marker(MARKER_PATH_COB, ultimo_ym)
        return hist

    marker = _read_marker(MARKER_PATH_COB)
    if marker is None:
        return build_or_update_hist_cobertura(force_full=True)

    if marker >= ultimo_ym:
        return existing

    y, m = map(int, marker.split("-"))
    next_month_first = (datetime.date(y, m, 28) + datetime.timedelta(days=4)).replace(day=1)
    months_missing = _iter_month_ends(next_month_first.strftime("%Y-%m"), ultimo_fechado)

    new_parts = []
    for me in months_missing:
        ym = me.strftime("%Y-%m")
        df_one = calcular_cobertura_historico(ym, ym)
        if not df_one.empty:
            new_parts.append(df_one)

    if new_parts:
        new_df = pd.concat(new_parts, ignore_index=True)
        hist = pd.concat([existing, new_df], ignore_index=True)
        hist.to_parquet(PARQUET_PATH_COB, index=False)
        _write_marker(MARKER_PATH_COB, ultimo_ym)
        return hist

    return existing

def load_hist_cobertura(include_current_partial: bool = False) -> pd.DataFrame:
    hist = _load_existing(PARQUET_PATH_COB)
    if include_current_partial:
        today = datetime.date.today()
        current_ym = today.strftime("%Y-%m")
        if current_ym not in hist.get("ano_mes", pd.Series(dtype=str)).unique():
            parcial = calcular_cobertura_historico(current_ym, current_ym)
            if not parcial.empty:
                hist = pd.concat([hist, parcial], ignore_index=True)
    return hist

# ---------- GMROI ----------
def build_or_update_hist_gmroi(force_full: bool = False) -> pd.DataFrame:
    ultimo_fechado = _ultimo_mes_fechado()
    ultimo_ym = ultimo_fechado.strftime("%Y-%m")
    existing = _load_existing(PARQUET_PATH_GMROI)

    if force_full or existing.empty:
        hist = calcular_gmroi_historico(START_MONTH, ultimo_ym)
        if not hist.empty:
            hist.to_parquet(PARQUET_PATH_GMROI, index=False)
            _write_marker(MARKER_PATH_GMROI, ultimo_ym)
        return hist

    marker = _read_marker(MARKER_PATH_GMROI)
    if marker is None:
        return build_or_update_hist_gmroi(force_full=True)

    if marker >= ultimo_ym:
        return existing

    y, m = map(int, marker.split("-"))
    next_month_first = (datetime.date(y, m, 28) + datetime.timedelta(days=4)).replace(day=1)
    months_missing = _iter_month_ends(next_month_first.strftime("%Y-%m"), ultimo_fechado)

    new_parts = []
    for me in months_missing:
        ym = me.strftime("%Y-%m")
        df_one = calcular_gmroi_historico(ym, ym)
        if not df_one.empty:
            new_parts.append(df_one)

    if new_parts:
        new_df = pd.concat(new_parts, ignore_index=True)
        hist = pd.concat([existing, new_df], ignore_index=True)
        hist.to_parquet(PARQUET_PATH_GMROI, index=False)
        _write_marker(MARKER_PATH_GMROI, ultimo_ym)
        return hist

    return existing

def load_hist_gmroi(include_current_partial: bool = False) -> pd.DataFrame:
    hist = _load_existing(PARQUET_PATH_GMROI)
    if include_current_partial:
        today = datetime.date.today()
        current_ym = today.strftime("%Y-%m")
        if current_ym not in hist.get("ano_mes", pd.Series(dtype=str)).unique():
            parcial = calcular_gmroi_historico(current_ym, current_ym)
            if not parcial.empty:
                hist = pd.concat([hist, parcial], ignore_index=True)
    return hist

# ---------- Curva D ----------
def build_or_update_hist_curvad(force_full: bool = False) -> pd.DataFrame:
    ultimo_fechado = _ultimo_mes_fechado()
    ultimo_ym = ultimo_fechado.strftime("%Y-%m")
    existing = _load_existing(PARQUET_PATH_CURVAD)

    if force_full or existing.empty:
        hist = calcular_curvad_historico(START_MONTH, ultimo_ym)
        if not hist.empty:
            hist.to_parquet(PARQUET_PATH_CURVAD, index=False)
            _write_marker(MARKER_PATH_CURVAD, ultimo_ym)
        return hist

    marker = _read_marker(MARKER_PATH_CURVAD)
    if marker is None:
        return build_or_update_hist_curvad(force_full=True)

    if marker >= ultimo_ym:
        return existing

    y, m = map(int, marker.split("-"))
    next_month_first = (datetime.date(y, m, 28) + datetime.timedelta(days=4)).replace(day=1)
    months_missing = _iter_month_ends(next_month_first.strftime("%Y-%m"), ultimo_fechado)

    new_parts = []
    for me in months_missing:
        ym = me.strftime("%Y-%m")
        df_one = calcular_curvad_historico(ym, ym)
        if not df_one.empty:
            new_parts.append(df_one)

    if new_parts:
        new_df = pd.concat(new_parts, ignore_index=True)
        hist = pd.concat([existing, new_df], ignore_index=True)
        hist.to_parquet(PARQUET_PATH_CURVAD, index=False)
        _write_marker(MARKER_PATH_CURVAD, ultimo_ym)
        return hist

    return existing

def load_hist_curvad(include_current_partial: bool = False) -> pd.DataFrame:
    hist = _load_existing(PARQUET_PATH_CURVAD)
    if include_current_partial:
        today = datetime.date.today()
        current_ym = today.strftime("%Y-%m")
        if current_ym not in hist.get("ano_mes", pd.Series(dtype=str)).unique():
            parcial = calcular_curvad_historico(current_ym, current_ym)
            if not parcial.empty:
                hist = pd.concat([hist, parcial], ignore_index=True)
    return hist

# ---------- Desfazimento da Curva D ----------
def build_or_update_hist_desfazimento(force_full: bool = False) -> pd.DataFrame:
    ultimo_fechado = _ultimo_mes_fechado()
    ultimo_ym = ultimo_fechado.strftime("%Y-%m")
    existing = _load_existing(PARQUET_PATH_DESF)

    if force_full or existing.empty:
        hist = calcular_desfazimento_curvad_historico(START_MONTH, ultimo_ym)
        if not hist.empty:
            hist.to_parquet(PARQUET_PATH_DESF, index=False)
            _write_marker(MARKER_PATH_DESF, ultimo_ym)
        return hist

    marker = _read_marker(MARKER_PATH_DESF)
    if marker is None:
        return build_or_update_hist_desfazimento(force_full=True)

    if marker >= ultimo_ym:
        return existing

    y, m = map(int, marker.split("-"))
    next_month_first = (datetime.date(y, m, 28) + datetime.timedelta(days=4)).replace(day=1)
    months_missing = _iter_month_ends(next_month_first.strftime("%Y-%m"), ultimo_fechado)

    new_parts = []
    for me in months_missing:
        ym = me.strftime("%Y-%m")
        df_one = calcular_desfazimento_curvad_historico(ym, ym)
        if not df_one.empty:
            new_parts.append(df_one)

    if new_parts:
        new_df = pd.concat(new_parts, ignore_index=True)
        hist = pd.concat([existing, new_df], ignore_index=True)
        hist.to_parquet(PARQUET_PATH_DESF, index=False)
        _write_marker(MARKER_PATH_DESF, ultimo_ym)
        return hist

    return existing

def load_hist_desfazimento(include_current_partial: bool = False) -> pd.DataFrame:
    hist = _load_existing(PARQUET_PATH_DESF)
    if include_current_partial:
        today = datetime.date.today()
        current_ym = today.strftime("%Y-%m")
        if current_ym not in hist.get("ano_mes", pd.Series(dtype=str)).unique():
            parcial = calcular_desfazimento_curvad_historico(current_ym, current_ym)
            if not parcial.empty:
                hist = pd.concat([hist, parcial], ignore_index=True)
    return hist


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Construção / atualização de históricos de estoque")
    parser.add_argument("--disp", action="store_true", help="Atualiza histórico de disponibilidade")
    parser.add_argument("--giro", action="store_true", help="Atualiza histórico de giro")
    parser.add_argument("--cobertura", "--cob", dest="cobertura", action="store_true",
                        help="Atualiza histórico de cobertura")
    parser.add_argument("--gmroi", "--g", dest="gmroi", action="store_true",
                        help="Atualiza histórico de GMROI")
    parser.add_argument("--curvad", "--d", dest="curvad", action="store_true",
                        help="Atualiza histórico de Curva D")
    parser.add_argument("--desfazimento", "--df", dest="desfazimento", action="store_true",
                        help="Atualiza histórico de Desfazimento Curva D")

    parser.add_argument("--all", action="store_true", help="Atualiza ambos (disponibilidade + giro)")
    parser.add_argument("--force-full", action="store_true", help="Rebuild completo (ignora parquet existente)")
    parser.add_argument("--include-current", action="store_true", help="Mostra mês corrente parcial após build")

    args = parser.parse_args()
    
    do_disp = args.disp or args.all or (not any([args.giro, args.cobertura, args.disp, args.all]))
    do_giro = args.giro or args.all
    do_cob = args.cobertura or args.all
    do_gmroi = args.gmroi or args.all
    do_curvad = args.curvad or args.all
    do_desfazimento = args.desfazimento or args.all
    
    if do_disp:
        hist_disp = build_or_update_hist_disponibilidade(force_full=args.force_full)
        if args.include_current:
            hist_disp = load_hist_disponibilidade(include_current_partial=True)
        print(f"[DISP] Linhas: {len(hist_disp)}  Últimos meses: {hist_disp['ano_mes'].drop_duplicates().sort_values().tail(3).tolist() if not hist_disp.empty else 'vazio'}")

    if do_giro:
        hist_giro = build_or_update_hist_giro(force_full=args.force_full)
        if args.include_current:
            hist_giro = load_hist_giro(include_current_partial=True)
        print(f"[GIRO] Linhas: {len(hist_giro)}  Últimos meses: {hist_giro['ano_mes'].drop_duplicates().sort_values().tail(3).tolist() if not hist_giro.empty else 'vazio'}")

    if do_cob:
        hist_cob = build_or_update_hist_cobertura(force_full=args.force_full)
        if args.include_current:
            hist_cob = load_hist_cobertura(include_current_partial=True)
        print(f"[COB] Linhas: {len(hist_cob)}  Últimos meses: {hist_cob['ano_mes'].drop_duplicates().sort_values().tail(3).tolist() if not hist_cob.empty else 'vazio'}")
    
    if do_gmroi:
        hist_gmroi = build_or_update_hist_gmroi(force_full=args.force_full)
        if args.include_current:
            hist_gmroi = load_hist_gmroi(include_current_partial=True)
        print(f"[GMROI] Linhas: {len(hist_gmroi)}  Últimos meses: {hist_gmroi['ano_mes'].drop_duplicates().sort_values().tail(3).tolist() if not hist_gmroi.empty else 'vazio'}")
    
    if do_curvad:
        hist_curvad = build_or_update_hist_curvad(force_full=args.force_full)
        if args.include_current:
            hist_curvad = load_hist_curvad(include_current_partial=True)
        print(f"[CURVAD] Linhas: {len(hist_curvad)}  Últimos meses: {hist_curvad['ano_mes'].drop_duplicates().sort_values().tail(3).tolist() if not hist_curvad.empty else 'vazio'}")

    if do_desfazimento:
        hist_desfazimento = build_or_update_hist_desfazimento(force_full=args.force_full)
        if args.include_current:
            hist_desfazimento = load_hist_desfazimento(include_current_partial=True)
        print(f"[DESFAZIMENTO] Linhas: {len(hist_desfazimento)}  Últimos meses: {hist_desfazimento['ano_mes'].drop_duplicates().sort_values().tail(3).tolist() if not hist_desfazimento.empty else 'vazio'}")