import time
import pandas as pd
import streamlit as st
from run_views import _build_cache_curva_abc_90d

USE_PERSISTENT_VIEWS = True  # agora padrão

def _materializar_bases(data_atual: str):
    dt_ontem = (pd.Timestamp(data_atual) - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
    dt_30 = (pd.Timestamp(dt_ontem) - pd.Timedelta(days=30)).strftime('%Y-%m-%d')
    dt_90 = (pd.Timestamp(dt_ontem) - pd.Timedelta(days=90)).strftime('%Y-%m-%d')
    dt_120 = (pd.Timestamp(dt_ontem) - pd.Timedelta(days=120)).strftime('%Y-%m-%d')
    dt_121 = (pd.Timestamp(dt_ontem) - pd.Timedelta(days=121)).strftime('%Y-%m-%d')
    return {
        "data_base": dt_ontem,
        "dt_30": dt_30,
        "dt_90": dt_90,
        "dt_120": dt_120,
        "dt_121": dt_121
    }

@st.cache_data(show_spinner=False)
def preparar_bases_estoque(data_atual: str):
    return _materializar_bases(data_atual)

def ensure_bases_estoque(data_atual: str, force: bool = False):
    key_flag = "bases_estoque_data"
    if force or key_flag not in st.session_state or st.session_state[key_flag] != data_atual:
        t0 = time.perf_counter()
        meta = preparar_bases_estoque(data_atual)
        st.session_state[key_flag] = data_atual
        st.session_state["bases_estoque_meta"] = meta
        st.session_state["bases_estoque_build_time"] = round(time.perf_counter() - t0, 3)
        _build_cache_curva_abc_90d(data_atual)
    return st.session_state.get("bases_estoque_meta", {})