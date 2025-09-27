import streamlit as st
import time
import functools
from datetime import datetime

class PerformanceLogger:
    def __init__(self):
        self.timers = {}
    
    def start_timer(self, label):
        """Inicia timer para uma operação"""
        self.timers[label] = time.time()
        st.write(f"⏳ Iniciando: {label} - {datetime.now().strftime('%H:%M:%S')}")
    
    def end_timer(self, label):
        """Finaliza timer e mostra tempo decorrido"""
        if label in self.timers:
            elapsed = time.time() - self.timers[label]
            st.write(f"✅ {label}: {elapsed:.2f}s")
            del self.timers[label]
    
    def log_cache_info(self, function_name, cache_hit=True):
        """Log informações de cache"""
        status = "🎯 CACHE HIT" if cache_hit else "🔄 CACHE MISS"
        st.write(f"{status}: {function_name}")

# Instância global
perf_logger = PerformanceLogger()

def debug_function_time(func):
    """Decorator para medir tempo de execução de funções"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        # Mostrar no sidebar se estiver em debug
        if st.session_state.get('debug_mode', False):
            with st.sidebar:
                st.caption(f"⚡ {func.__name__}: {end_time - start_time:.2f}s")
        
        return result
    return wrapper