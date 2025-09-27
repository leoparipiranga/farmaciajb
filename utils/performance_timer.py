import time
import streamlit as st

BAR_LOADING_HTML = (
    "<div style='position:sticky;top:0;z-index:999;"
    "background:#222;padding:4px 10px;border-radius:4px;"
    "font-size:12px;color:#bbb;'>⏳ Carregando...</div>"
)
BAR_DONE_HTML = (
    "<div style='position:sticky;top:0;z-index:999;"
    "background:#1b4332;padding:4px 10px;border-radius:4px;"
    "font-size:12px;color:#d8f3dc;'>🕒 Tempo de carregamento: "
    "{elapsed:.2f}s • {contexto}</div>"
)

def _ensure_bar():
    ss = st.session_state
    if 'perf_bar' not in ss:
        # Coloque sempre no topo (chame perf_bar_init logo no início da página)
        ss['perf_bar'] = st.empty()
    return ss['perf_bar']

def perf_bar_init():
    """Chamar no início da página (antes de montar layout)."""
    _ensure_bar()
    # Se há medição em andamento (ex.: após rerun), mostra estado "Carregando..."
    ss = st.session_state
    if ss.get('perf_running'):
        ss['perf_bar'].markdown(BAR_LOADING_HTML, unsafe_allow_html=True)

def perf_prepare(contexto: str):
    """
    Marcar intenção de iniciar medição após o rerun.
    Use antes de alterar estado que provoca st.rerun().
    """
    st.session_state['_perf_pending_context'] = contexto

def perf_maybe_start():
    """
    Inicia medição se foi previamente preparado com perf_prepare().
    Chamar logo após perf_bar_init().
    """
    ss = st.session_state
    if '_perf_pending_context' in ss:
        contexto = ss.pop('_perf_pending_context')
        perf_start(contexto)

def perf_start(contexto: str):
    """Inicia medição imediatamente (sem necessidade de rerun)."""
    ss = st.session_state
    placeholder = _ensure_bar()
    ss['perf_contexto'] = contexto
    ss['perf_start_time'] = time.perf_counter()
    ss['perf_running'] = True
    placeholder.markdown(BAR_LOADING_HTML, unsafe_allow_html=True)

def perf_end():
    """Finaliza; chamar após todo o conteúdo pesado ser renderizado."""
    ss = st.session_state
    if not ss.get('perf_running'):
        return
    if 'perf_start_time' not in ss:
        return
    elapsed = time.perf_counter() - ss['perf_start_time']
    contexto = ss.get('perf_contexto', '')
    placeholder = _ensure_bar()
    placeholder.markdown(
        BAR_DONE_HTML.format(elapsed=elapsed, contexto=contexto),
        unsafe_allow_html=True
    )
    ss['perf_running'] = False

def perf_track_filters(key: str, filtros: dict, contexto: str, auto_rerun=True):
    """
    Detecta mudança de filtros. Se mudou:
      - prepara medição
      - opcionalmente força st.rerun()
    Retorna True se mudou.
    """
    ss = st.session_state
    sig = repr(sorted(filtros.items()))
    sig_key = f'_perf_sig_{key}'
    if ss.get(sig_key) != sig:
        ss[sig_key] = sig
        perf_prepare(contexto)
        if auto_rerun:
            st.rerun()
        return True
    return False