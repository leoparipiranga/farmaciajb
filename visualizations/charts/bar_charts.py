"""
Componentes de gráficos de barras reutilizáveis
"""
import plotly.express as px
import plotly.graph_objects as go

def criar_grafico_disponibilidade_por_filial_duck(df_disponibilidade):
    """Gráfico de disponibilidade por filial - DuckDB"""
    # Filtrar apenas filiais (excluir 'Geral')
    df = df_disponibilidade[df_disponibilidade['filial_codigo'] != 'Geral'].copy()
    
    if df.empty:
        return go.Figure().update_layout(title_text='Disponibilidade por Filial (Sem dados)')
    
    df = df.sort_values('filial_codigo')
    # Cores baseadas no valor (DeepSkyBlue para bom, CadetBlue para ruim)
    bar_colors = ['DeepSkyBlue' if v >= 90 else 'CadetBlue' for v in df['disponibilidade_percent']]
    
    # Calcular range dinâmico: 10% abaixo do mínimo e 10% acima do máximo
    min_val = float(df['disponibilidade_percent'].min())
    max_val = float(df['disponibilidade_percent'].max())
    span = max_val - min_val
    if span == 0:
        pad = max(1.0, abs(max_val) * 0.1)
    else:
        pad = span * 0.1
    y_min = max_val - min_val
    y_max = max_val + pad * 4
    # Garantir limites razoáveis (não ficar negativos e não extrapolar muito)
    if y_min < 0:
        y_min = 0.0
    # mantemos um teto próximo de 105% para exibições percentuais
    if y_max > 105:
        y_max = 105.0

    fig = go.Figure(go.Bar(
        x=df['filial_codigo'],
        y=df['disponibilidade_percent'],
        marker_color=bar_colors,
        texttemplate='%{y:.1f}%',
        textposition='inside',
        textfont_color='white',
        textfont_size=12,
        textangle=0
    ))
    
    fig.update_layout(
        title_text='Disponibilidade de Estoque',  # <-- título aqui
        title={'x':0, 'xanchor':'left', 'yanchor':'top'},  # opcional: centraliza
        title_font={'size':14, 'family':'Arial'},
        width=600,
        height=120,
        template="plotly_white",
        showlegend=False,
        xaxis=dict(title=None, automargin=True),
        yaxis=dict(visible=False, range=[y_min, y_max], automargin=True),
        margin=dict(t=40, b=30, l=10, r=10),  # aumentar top margin para o título
        bargap=0.12,
        autosize=True
    )
    return fig

def criar_grafico_giro_por_filial_duck(df_giro):
    """Gráfico de estoque com giro por filial - DuckDB"""
    # Filtrar apenas filiais (excluir 'Geral')
    df = df_giro[df_giro['filial_codigo'] != 'Geral'].copy()
    
    if df.empty:
        return go.Figure().update_layout(title_text='Estoque com Giro por Filial (Sem dados)')
    
    df = df.sort_values('filial_codigo')
    # Cores baseadas no valor (DeepSkyBlue para bom, CadetBlue para ruim)
    bar_colors = ['DeepSkyBlue' if v >= 60 else 'CadetBlue' for v in df['giro']]
    
    # Calcular range dinâmico: 10% abaixo do mínimo e 10% acima do máximo
    min_val = float(df['giro'].min())
    max_val = float(df['giro'].max())
    span = max_val - min_val
    if span == 0:
        pad = max(1.0, abs(max_val) * 0.1)
    else:
        pad = span * 0.1
    y_min = max_val - min_val
    y_max = max_val + pad * 4

    fig = go.Figure(go.Bar(
        x=df['filial_codigo'],
        y=df['giro'],
        marker_color=bar_colors,
        texttemplate='%{y:.1f}%',
        textposition='inside',
        textfont_color='white',
        textfont_size=12,
        textangle=0
    ))
    
    fig.update_layout(
        title_text='Estoque com Giro',  # <-- título aqui
        title={'x':0, 'xanchor':'left', 'yanchor':'top'},  # opcional: centraliza
        title_font={'size':14, 'family':'Arial'},
        width=600,
        height=120,
        template="plotly_white",
        showlegend=False,
        xaxis=dict(title=None, automargin=True),
        yaxis=dict(visible=False, range=[y_min, y_max], automargin=True),
        margin=dict(t=10, b=30, l=10, r=10),
        bargap=0.12,
        autosize=True
    )
    return fig

def criar_grafico_fator_cobertura_por_filial_duck(df_cobertura):
    """Gráfico de fator de cobertura por filial - DuckDB"""
    # Filtrar apenas filiais (excluir 'Geral')
    df = df_cobertura[df_cobertura['filial_codigo'] != 'Geral'].copy()
    
    if df.empty:
        return go.Figure().update_layout(title_text='Fator de Cobertura por Filial (Sem dados)')
    
    df = df.sort_values('filial_codigo')
    # Cores baseadas no valor (DeepSkyBlue para bom, CadetBlue para ruim)
    bar_colors = ['DeepSkyBlue' if v >= 2.0 else 'CadetBlue' for v in df['cobertura_ratio']]
    
    fig = go.Figure(go.Bar(
        x=df['filial_codigo'],
        y=df['cobertura_ratio'],
        marker_color=bar_colors,
        texttemplate='%{y:.1f}',
        textposition='inside',
        textfont_color='white',
        textfont_size=12,
        textangle=0
    ))
    
    # Range adaptativo para o fator de cobertura
    max_value = df['cobertura_ratio'].max() if not df.empty else 5
    y_range = [0, max(max_value * 1.2, 5)]
    
    fig.update_layout(
        title_text='Fator de Cobertura',  # <-- título aqui
        title={'x':0, 'xanchor':'left', 'yanchor':'top'},  # opcional: centraliza
        title_font={'size':14, 'family':'Arial'},
        width=600,
        height=120,
        template="plotly_white",
        showlegend=False,
        xaxis=dict(title=None, automargin=True),
        yaxis=dict(visible=False, range=y_range, automargin=True),
        margin=dict(t=10, b=30, l=10, r=10),
        bargap=0.12,
        autosize=True
    )
    return fig

def criar_grafico_primeira_venda_filial(df):
    """Gráfico de tempo até a primeira venda por filial"""
            
    if df.empty:
        return go.Figure().update_layout(title_text='Tempo até a Primeira Venda por Filial (Sem dados)')

    df = df.sort_values('filial_codigo')
    # Cores baseadas no valor (DeepSkyBlue para bom, CadetBlue para ruim)
    bar_colors = ['DeepSkyBlue' if v >= 2.0 else 'CadetBlue' for v in df['tempo_primeira_venda_geral']]
    
    fig = go.Figure(go.Bar(
        x=df['filial_codigo'],
        y=df['tempo_primeira_venda_geral'],
        marker_color=bar_colors,
        texttemplate='%{y:.1f}',
        textposition='inside',
        textfont_color='white',
        textfont_size=12,
        textangle=0
    ))
    
    # Range adaptativo para o fator de cobertura
    max_value = df['tempo_primeira_venda_geral'].max() if not df.empty else 5
    y_range = [0, max(max_value * 1.2, 5)]
    
    fig.update_layout(
        title_text='Dias até a Primeira Venda',  # <-- título aqui
        title={'x':0, 'xanchor':'left', 'yanchor':'top'},  # opcional: centraliza
        title_font={'size':14, 'family':'Arial'},
        width=600,
        height=120,
        template="plotly_white",
        showlegend=False,
        xaxis=dict(title=None, automargin=True),
        yaxis=dict(visible=False, range=y_range, automargin=True),
        margin=dict(t=10, b=30, l=10, r=10),
        bargap=0.12,
        autosize=True
    )
    return fig

def criar_grafico_curva_d_por_filial_duck(df):
    """Gráfico de Curva D por filial - DuckDB"""
    # Filtrar apenas filiais (excluir 'Geral')
    
    if df.empty:
        return go.Figure().update_layout(title_text='Curva D por Filial (Sem dados)')
    
    df = df.sort_values('filial_codigo')
    # Para Curva D, valores menores são melhores (CadetBlue para alto, DeepSkyBlue para baixo)
    bar_colors = ['CadetBlue' if v >= 10 else 'DeepSkyBlue' for v in df['pct_value']]
    
    threshold = max(df['pct_value']) * 0.4
    text_positions = ['inside' if v >= threshold else 'outside' for v in df['pct_value']]
    text_colors = ['white' if pos == 'inside' else 'darkgrey' for pos in text_positions]
    
    fig = go.Figure(go.Bar(
        x=df['filial_codigo'],
        y=df['pct_value'],
        marker_color=bar_colors,
        texttemplate='%{y:.1f}%',
        textposition=text_positions,
        textfont_color=text_colors,
        textfont_size=12,
        textangle=0
    ))

    max_value = df['pct_value'].max() if not df.empty else 5
    y_range = [0, max(max_value * 1.2, 5)]
    
    fig.update_layout(
        title_text='Conversão para Curva D',  # <-- título aqui
        title={'x':0, 'xanchor':'left', 'yanchor':'top'},  # opcional: centraliza
        title_font={'size':14, 'family':'Arial'},
        width=600,
        height=120,
        template="plotly_white",
        showlegend=False,
        xaxis=dict(title=None, automargin=True),
        yaxis=dict(visible=False, range=y_range, automargin=True),
        margin=dict(t=10, b=30, l=10, r=10),
        bargap=0.12,
        autosize=True
    )
    return fig

def criar_grafico_desfazimento_curva_d_por_filial_duck(df_desfazimento):
    """Gráfico de Desfazimento da Curva D por filial - DuckDB"""
    # Filtrar apenas filiais (excluir 'Geral')
    df = df_desfazimento[df_desfazimento['filial_codigo'] != 'Geral'].copy()
    
    if df.empty:
        return go.Figure().update_layout(title_text='Desfazimento da Curva D por Filial (Sem dados)')
    
    df = df.sort_values('filial_codigo')
    # Para desfazimento, valores maiores são melhores (DeepSkyBlue para alto, CadetBlue para baixo)
    bar_colors = ['DeepSkyBlue' if v >= 6 else 'CadetBlue' for v in df['pct_value']]
    
    threshold = max(df['pct_value']) * 0.4
    text_positions = ['inside' if v >= threshold else 'outside' for v in df['pct_value']]
    text_colors = ['white' if pos == 'inside' else 'darkgrey' for pos in text_positions]

    fig = go.Figure(go.Bar(
        x=df['filial_codigo'],
        y=df['pct_value'],
        marker_color=bar_colors,
        texttemplate='%{y:.1f}%',
        textposition=text_positions,
        textfont_color=text_colors,
        textfont_size=12,
        textangle=0
    ))

    max_value = df['pct_value'].max() if not df.empty else 5
    y_range = [0, max(max_value * 1.2, 5)]
    
    fig.update_layout(
        title_text='Venda de Curva D (30 dias)',  # <-- título aqui
        title={'x':0, 'xanchor':'left', 'yanchor':'top'},  # opcional: centraliza
        title_font={'size':14, 'family':'Arial'},
        width=600,
        height=120,
        template="plotly_white",
        showlegend=False,
        xaxis=dict(title=None, automargin=True),
        yaxis=dict(visible=False, range=y_range, automargin=True),
        margin=dict(t=10, b=30, l=10, r=10),
        bargap=0.12,
        autosize=True
    )
    return fig

def criar_grafico_disponibilidade_por_curva_abc_duck(df_disponibilidade):
    """Gráfico de disponibilidade por curva ABC - DuckDB"""
    df = df_disponibilidade.copy()
    
    if df.empty:
        return go.Figure().update_layout(title_text='Disponibilidade por Curva ABC (Sem dados)')
    
    # Ordenar por curva ABC (A, B, C, D)
    curva_order = {'A': 1, 'B': 2, 'C': 3, 'D': 4}
    df['order'] = df['curvaABC'].map(curva_order)
    df = df[df['disponibilidade']>0]
    df = df.sort_values('order')
    
    # Cores baseadas no valor (DeepSkyBlue para bom, CadetBlue para ruim)
    bar_colors = ['DeepSkyBlue' if v >= 90 else 'CadetBlue' for v in df['disponibilidade']]
    
    fig = go.Figure(go.Bar(
        x=df['curvaABC'],
        y=df['disponibilidade'],
        marker_color=bar_colors,
        texttemplate='%{y:.1f}%',
        textposition='inside',
        textfont_color='white',
        textfont_size=12,
        textangle=0
    ))
    
    fig.update_layout(
        title_text='Disponibilidade de Estoque',
        title={'x':0, 'xanchor':'left', 'yanchor':'top'},
        title_font={'size':14, 'family':'Arial'},
        width=600,
        height=180,
        template="plotly_white",
        showlegend=False,
        xaxis=dict(title=None, automargin=True),
        yaxis=dict(visible=False, range=[50, 105], automargin=True),
        margin=dict(t=20, b=20, l=10, r=10),
        bargap=0.12,
        autosize=True
    )
    return fig

def criar_grafico_giro_por_curva_abc_duck(df_giro):
    """Gráfico de estoque com giro por curva ABC - DuckDB"""
    df = df_giro.copy()
    
    if df.empty:
        return go.Figure().update_layout(title_text='Estoque com Giro por Curva ABC (Sem dados)')
    
    # Ordenar por curva ABC (A, B, C, D) 
    curva_order = {'A': 1, 'B': 2, 'C': 3, 'D': 4}
    df['order'] = df['curvaABC'].map(curva_order)
    df = df[df['giro_medio_anual']>0]
    df = df.sort_values('order')
    
    # Cores baseadas no valor (DeepSkyBlue para bom, CadetBlue para ruim)
    bar_colors = ['DeepSkyBlue' if v >= 60 else 'CadetBlue' for v in df['giro_medio_anual']]
    
    fig = go.Figure(go.Bar(
        x=df['curvaABC'],
        y=df['giro_medio_anual'],
        marker_color=bar_colors,
        texttemplate='%{y:.1f}%',
        textposition='inside',
        textfont_color='white',
        textfont_size=12,
        textangle=0
    ))
    
    fig.update_layout(
        title_text='Estoque com Giro',
        title={'x':0, 'xanchor':'left', 'yanchor':'top'},
        title_font={'size':14, 'family':'Arial'},
        width=600,
        height=180,
        template="plotly_white",
        showlegend=False,
        xaxis=dict(title=None, automargin=True),
        yaxis=dict(visible=False, range=[50, 105], automargin=True),
        margin=dict(t=20, b=20, l=10, r=10),
        bargap=0.12,
        autosize=True
    )
    return fig

def criar_grafico_fator_cobertura_por_curva_abc_duck(df_cobertura):
    """Gráfico de fator de cobertura por curva ABC - DuckDB"""
    df = df_cobertura.copy()
    
    if df.empty:
        return go.Figure().update_layout(title_text='Fator de Cobertura por Curva ABC (Sem dados)')
    
    # Ordenar por curva ABC (A, B, C, D)
    curva_order = {'A': 1, 'B': 2, 'C': 3, 'D': 4}
    df['order'] = df['curvaABC'].map(curva_order)
    df = df[df['curvaABC']!='D']
    df = df.sort_values('order')
    
    # Cores baseadas no valor (DeepSkyBlue para bom, CadetBlue para ruim)
    bar_colors = ['DeepSkyBlue' if v >= 2.0 else 'CadetBlue' for v in df['cobertura_ratio']]
    
    fig = go.Figure(go.Bar(
        x=df['curvaABC'],
        y=df['cobertura_ratio'],
        marker_color=bar_colors,
        texttemplate='%{y:.1f}',
        textposition='inside',
        textfont_color='white',
        textfont_size=12,
        textangle=0
    ))
    
    # Range adaptativo para o fator de cobertura
    max_value = df['cobertura_ratio'].max() if not df.empty else 5
    y_range = [0, max(max_value * 1.2, 5)]
    
    fig.update_layout(
        title_text='Fator de Cobertura',
        title={'x':0, 'xanchor':'left', 'yanchor':'top'},
        title_font={'size':14, 'family':'Arial'},
        width=600,
        height=180,
        template="plotly_white",
        showlegend=False,
        xaxis=dict(title=None, automargin=True),
        yaxis=dict(visible=False, range=y_range, automargin=True),
        margin=dict(t=20, b=20, l=10, r=10),
        bargap=0.12,
        autosize=True
    )
    return fig

def criar_grafico_primeira_venda_por_curva_abc_duck(df_primeira_venda):
    """Gráfico de primeira venda por curva ABC - DuckDB"""
    df = df_primeira_venda.copy()

    if df.empty:
        return go.Figure().update_layout(title_text='Primeira Venda por Curva ABC (Sem dados)')

    # Ordenar por curva ABC (A, B, C, D)
    curva_order = {'A': 1, 'B': 2, 'C': 3, 'D': 4}
    df['order'] = df['curvaABC'].map(curva_order)
    df = df[df['tempo_primeira_venda_geral']>0]
    df = df.sort_values('order')
    
    # Cores baseadas no valor (DeepSkyBlue para bom, CadetBlue para ruim)
    bar_colors = ['DeepSkyBlue' if v >= 2.0 else 'CadetBlue' for v in df['tempo_primeira_venda_geral']]

    fig = go.Figure(go.Bar(
        x=df['curvaABC'],
        y=df['tempo_primeira_venda_geral'],
        marker_color=bar_colors,
        texttemplate='%{y:.1f}',
        textposition='inside',
        textfont_color='white',
        textfont_size=12,
        textangle=0
    ))

    # Range adaptativo para a primeira venda
    max_value = df['tempo_primeira_venda_geral'].max() if not df.empty else 5
    y_range = [0, max(max_value * 1.2, 5)]
    
    fig.update_layout(
        title_text='Dias para a 1ª Venda',
        title={'x':0, 'xanchor':'left', 'yanchor':'top'},
        title_font={'size':14, 'family':'Arial'},
        width=600,
        height=180,
        template="plotly_white",
        showlegend=False,
        xaxis=dict(title=None, automargin=True),
        yaxis=dict(visible=False, range=y_range, automargin=True),
        margin=dict(t=20, b=20, l=10, r=10),
        bargap=0.12,
        autosize=True
    )
    return fig

def render_bar(df_base, y_col, tipo_fmt, cor, altura):
    """
    Renderiza gráfico de barras para séries mensais
    """
    base = df_base[['mes_label', y_col]].copy()
    
    # Formatação de valores
    def format_val(valor, tipo):
        if tipo == 'moeda':
            return f"R$ {valor:,.0f}"
        if tipo == 'int':
            return f"{int(round(valor))}"
        if tipo == 'num1':
            return f"{float(round(valor, 1)):.1f}"
        if tipo == 'perc1':
            return f"{valor:.1f}%"
        return f"{valor}"
    
    fig = px.bar(
        base,
        x='mes_label',
        y=y_col,
        text=base[y_col].apply(lambda v: format_val(v, tipo_fmt)),
        color_discrete_sequence=[cor]
    )
    fig.update_traces(
        textposition="outside",
        cliponaxis=False,
        marker_line_color=cor,
        marker_line_width=1
    )
    fig.update_layout(
        height=altura,
        margin=dict(t=32, b=10, l=25, r=5),
        showlegend=False,
        xaxis=dict(title="", tickfont=dict(size=10)),
        yaxis=dict(title="", tickfont=dict(size=10))
    )
    return fig


def criar_grafico_disponibilidade_por_classificacao_n1(df_disponibilidade):
    """Gráfico de disponibilidade por classificação N1 - DuckDB"""
    df = df_disponibilidade.copy()
    
    if df.empty:
        return go.Figure().update_layout(title_text='Disponibilidade por Classificação N1 (Sem dados)')

    # Ordenar por classificação N1
    df = df[df['disponibilidade']>0]
        
    # Cores baseadas no valor (DeepSkyBlue para bom, CadetBlue para ruim)
    bar_colors = ['DeepSkyBlue' if v >= 90 else 'CadetBlue' for v in df['disponibilidade']]
    
    fig = go.Figure(go.Bar(
        x=df['classificacao_n1'],
        y=df['disponibilidade'],
        marker_color=bar_colors,
        texttemplate='%{y:.1f}%',
        textposition='inside',
        textfont_color='white',
        textfont_size=12,
        textangle=0
    ))
    
    fig.update_layout(
        title_text='Disponibilidade de Estoque',
        title={'x':0, 'xanchor':'left', 'yanchor':'top'},
        title_font={'size':14, 'family':'Arial'},
        width=600,
        height=180,
        template="plotly_white",
        showlegend=False,
        xaxis=dict(title=None, automargin=True),
        yaxis=dict(visible=False, range=[50, 105], automargin=True),
        margin=dict(t=20, b=20, l=10, r=10),
        bargap=0.12,
        autosize=True
    )
    return fig

def criar_grafico_giro_por_classificacao_n1(df_giro):
    """Gráfico de estoque com giro por classificação N1 - DuckDB"""
    df = df_giro.copy()
    
    if df.empty:
        return go.Figure().update_layout(title_text='Estoque com Giro por Classificação N1 (Sem dados)')

    # Ordenar por classificação N1
    df = df[df['giro_medio_anual']>0]
       
    # Cores baseadas no valor (DeepSkyBlue para bom, CadetBlue para ruim)
    bar_colors = ['DeepSkyBlue' if v >= 60 else 'CadetBlue' for v in df['giro_medio_anual']]
    
    fig = go.Figure(go.Bar(
        x=df['classificacao_n1'],
        y=df['giro_medio_anual'],
        marker_color=bar_colors,
        texttemplate='%{y:.1f}%',
        textposition='inside',
        textfont_color='white',
        textfont_size=12,
        textangle=0
    ))
    
    fig.update_layout(
        title_text='Estoque com Giro',
        title={'x':0, 'xanchor':'left', 'yanchor':'top'},
        title_font={'size':14, 'family':'Arial'},
        width=600,
        height=180,
        template="plotly_white",
        showlegend=False,
        xaxis=dict(title=None, automargin=True),
        yaxis=dict(visible=False, range=[50, 105], automargin=True),
        margin=dict(t=20, b=20, l=10, r=10),
        bargap=0.12,
        autosize=True
    )
    return fig

def criar_grafico_fator_cobertura_por_classificacao_n1(df_cobertura):
    """Gráfico de fator de cobertura por classificação N1 - DuckDB"""
    df = df_cobertura.copy()
    
    if df.empty:
        return go.Figure().update_layout(title_text='Fator de Cobertura por Classificação N1 (Sem dados)')

    # Ordenar por classificação N1
    df = df[df['cobertura_ratio']>0]
        
    # Cores baseadas no valor (DeepSkyBlue para bom, CadetBlue para ruim)
    bar_colors = ['DeepSkyBlue' if v >= 2.0 else 'CadetBlue' for v in df['cobertura_ratio']]
    
    fig = go.Figure(go.Bar(
        x=df['classificacao_n1'],
        y=df['cobertura_ratio'],
        marker_color=bar_colors,
        texttemplate='%{y:.1f}',
        textposition='inside',
        textfont_color='white',
        textfont_size=12,
        textangle=0
    ))
    
    # Range adaptativo para o fator de cobertura
    max_value = df['cobertura_ratio'].max() if not df.empty else 5
    y_range = [0, max(max_value * 1.2, 5)]
    
    fig.update_layout(
        title_text='Fator de Cobertura',
        title={'x':0, 'xanchor':'left', 'yanchor':'top'},
        title_font={'size':14, 'family':'Arial'},
        width=600,
        height=180,
        template="plotly_white",
        showlegend=False,
        xaxis=dict(title=None, automargin=True),
        yaxis=dict(visible=False, range=y_range, automargin=True),
        margin=dict(t=20, b=20, l=10, r=10),
        bargap=0.12,
        autosize=True
    )
    return fig

def criar_grafico_primeira_venda_por_classificacao_n1(df_primeira_venda):
    """Gráfico de primeira venda por classificação N1 - DuckDB"""
    df = df_primeira_venda.copy()

    if df.empty:
        return go.Figure().update_layout(title_text='Primeira Venda por Classificação N1 (Sem dados)')

    # Ordenar por classificação N1
    df = df[df['tempo_primeira_venda_geral']>0]
        
    # Cores baseadas no valor (DeepSkyBlue para bom, CadetBlue para ruim)
    bar_colors = ['DeepSkyBlue' if v >= 2.0 else 'CadetBlue' for v in df['tempo_primeira_venda_geral']]

    fig = go.Figure(go.Bar(
        x=df['classificacao_n1'],
        y=df['tempo_primeira_venda_geral'],
        marker_color=bar_colors,
        texttemplate='%{y:.1f}',
        textposition='inside',
        textfont_color='white',
        textfont_size=12,
        textangle=0
    ))

    # Range adaptativo para a primeira venda
    max_value = df['tempo_primeira_venda_geral'].max() if not df.empty else 5
    y_range = [0, max(max_value * 1.2, 5)]
    
    fig.update_layout(
        title_text='Dias para a 1ª Venda',
        title={'x':0, 'xanchor':'left', 'yanchor':'top'},
        title_font={'size':14, 'family':'Arial'},
        width=600,
        height=180,
        template="plotly_white",
        showlegend=False,
        xaxis=dict(title=None, automargin=True),
        yaxis=dict(visible=False, range=y_range, automargin=True),
        margin=dict(t=20, b=20, l=10, r=10),
        bargap=0.12,
        autosize=True
    )
    return fig

def criar_grafico_primeira_venda_30d_por_classificacao_n1(df_primeira_venda):
    """Gráfico de primeira venda após 30 dias por classificação N1 - DuckDB"""
    df = df_primeira_venda.copy()

    if df.empty:
        return go.Figure().update_layout(title_text='Primeira Venda Após 30 dias por Classificação N1 (Sem dados)')

    # Ordenar por classificação N1
    df = df[df['tempo_primeira_venda_apos_30d']>0]
        
    # Cores baseadas no valor (DeepSkyBlue para bom, CadetBlue para ruim)
    bar_colors = ['DeepSkyBlue' if v >= 2.0 else 'CadetBlue' for v in df['tempo_primeira_venda_apos_30d']]

    fig = go.Figure(go.Bar(
        x=df['classificacao_n1'],
        y=df['tempo_primeira_venda_apos_30d'],
        marker_color=bar_colors,
        texttemplate='%{y:.1f}',
        textposition='inside',
        textfont_color='white',
        textfont_size=12,
        textangle=0
    ))

    # Range adaptativo para a primeira venda
    max_value = df['tempo_primeira_venda_apos_30d'].max() if not df.empty else 5
    y_range = [0, max(max_value * 1.2, 5)]
    
    fig.update_layout(
        title_text='Dias para a 1ª Venda (Após 30d)',
        title={'x':0, 'xanchor':'left', 'yanchor':'top'},
        title_font={'size':14, 'family':'Arial'},
        width=600,
        height=180,
        template="plotly_white",
        showlegend=False,
        xaxis=dict(title=None, automargin=True),
        yaxis=dict(visible=False, range=y_range, automargin=True),
        margin=dict(t=20, b=20, l=10, r=10),
        bargap=0.12,
        autosize=True
    )
    return fig

def criar_grafico_curva_d_por_classificacao_n1(df):
    """Gráfico de Nascimento de Curva D por classificação n1 - DuckDB"""
        
    if df.empty:
        return go.Figure().update_layout(title_text='Curva D por Classificação N1 (Sem dados)')

    df = df.sort_values('classificacao_n1')
    # Para Curva D, valores menores são melhores (CadetBlue para alto, DeepSkyBlue para baixo)
    bar_colors = ['CadetBlue' if v >= 10 else 'DeepSkyBlue' for v in df['indice_curva_d']]
    
    fig = go.Figure(go.Bar(
        x=df['classificacao_n1'],
        y=df['indice_curva_d'],
        marker_color=bar_colors,
        texttemplate='%{y:.1f}%',
        textposition='inside',
        textfont_color='white',
        textfont_size=12,
        textangle=0
    ))

    max_value = df['indice_curva_d'].max() if not df.empty else 5
    y_range = [0, max(max_value * 1.2, 5)]
    
    fig.update_layout(
        title_text='Conversão para Curva D',  # <-- título aqui
        title={'x':0, 'xanchor':'left', 'yanchor':'top'},  # opcional: centraliza
        title_font={'size':14, 'family':'Arial'},
        width=600,
        height=180,
        template="plotly_white",
        showlegend=False,
        xaxis=dict(title=None, automargin=True),
        yaxis=dict(visible=False, range=y_range, automargin=True),
        margin=dict(t=20, b=20, l=10, r=10),
        bargap=0.12,
        autosize=True
    )
    
    return fig

def criar_grafico_desfazimento_curva_d_por_classificacao_n1(df):
    """Gráfico de Desfazimento da Curva D por classificação n1 - DuckDB"""
    
    df = df[df['classificacao_n1']!='USO CONSUMO E SERVIÇOS']
    
    if df.empty:
        return go.Figure().update_layout(title_text='Desfazimento da Curva D por Classificação N1 (Sem dados)')

    # Para desfazimento, valores maiores são melhores (DeepSkyBlue para alto, CadetBlue para baixo)
    bar_colors = ['DeepSkyBlue' if v >= 6 else 'CadetBlue' for v in df['pct_value']]
    
    fig = go.Figure(go.Bar(
        x=df['classificacao_n1'],
        y=df['pct_value'],
        marker_color=bar_colors,
        texttemplate='%{y:.1f}%',
        textposition='inside',
        textfont_color='white',
        textfont_size=12,
        textangle=0
    ))

    max_value = df['pct_value'].max() if not df.empty else 5
    y_range = [0, max(max_value * 1.2, 5)]
    
    fig.update_layout(
        title_text='Venda Curva D (30 dias)',  # <-- título aqui
        title={'x':0, 'xanchor':'left', 'yanchor':'top'},  # opcional: centraliza
        title_font={'size':14, 'family':'Arial'},
        width=600,
        height=180,
        template="plotly_white",
        showlegend=False,
        xaxis=dict(title=None, automargin=True),
        yaxis=dict(visible=False, range=y_range, automargin=True),
        margin=dict(t=20, b=20, l=10, r=10),
        bargap=0.12,
        autosize=True
    )
    
    return fig

def criar_grafico_disponibilidade_por_classificacao_n2(df_disponibilidade):
    """Gráfico de disponibilidade por classificação N2 - DuckDB"""
    df = df_disponibilidade.copy()
    
    if df.empty:
        return go.Figure().update_layout(title_text='Disponibilidade por Classificação N2 (Sem dados)')

    # Ordenar por classificação N2
    df = df[df['disponibilidade']>0]
        
    # Ordenar por disponibilidade desc para mostrar maiores no topo
    df = df.sort_values('disponibilidade', ascending=True)

    # Cores baseadas no valor (DeepSkyBlue para bom, CadetBlue para ruim)
    bar_colors = ['DeepSkyBlue' if v >= 90 else 'CadetBlue' for v in df['disponibilidade']]
    
    fig = go.Figure(go.Bar(
        x=df['disponibilidade'],
        y=df['classificacao_n2'],
        orientation='h',
        marker_color=bar_colors,
        texttemplate='%{x:.1f}%',
        textposition='outside',
        textfont_color='darkgrey',
        textfont_size=13,
        textangle=0
    ))
    
    # Garantir que o texto posicionado fora das barras seja renderizado (não cortado pelo eixo)
    fig.update_traces(cliponaxis=False)
    
    fig.update_layout(
        title_text='Disponibilidade de Estoque',
        title_font={'size':14, 'family':'Arial'},
        width=450,
        height=600,
        template="plotly_white",
        showlegend=False,
        xaxis=dict(visible=False, range=[0, 105], automargin=True),
        yaxis=dict(
            title=None,
            automargin=True,
            categoryorder='array',
            categoryarray=df['classificacao_n2']  # garante a ordem decrescente (maior no topo)
        ),
        margin=dict(t=50, b=20, l=120, r=60),
        bargap=0.12,
        autosize=True
    )
    return fig


def criar_grafico_giro_por_classificacao_n2(df_giro):
    """Gráfico de giro por classificação N2 - DuckDB"""
    df = df_giro.copy()

    if df.empty:
        return go.Figure().update_layout(title_text='Giro por Classificação N2 (Sem dados)')

    # Ordenar por classificação N2
    df = df[df['giro_medio_anual']>0]

    # Ordenar por giro desc para mostrar maiores no topo
    df = df.sort_values('giro_medio_anual', ascending=True)

    # Cores baseadas no valor (DeepSkyBlue para bom, CadetBlue para ruim)
    bar_colors = ['DeepSkyBlue' if v >= 90 else 'CadetBlue' for v in df['giro_medio_anual']]

    fig = go.Figure(go.Bar(
        x=df['giro_medio_anual'],
        y=df['classificacao_n2'],
        orientation='h',
        marker_color=bar_colors,
        texttemplate='%{x:.1f}%',
        textposition='outside',
        textfont_color='darkgrey',
        textfont_size=13,
        textangle=0
    ))
    
    # Garantir que o texto posicionado fora das barras seja renderizado (não cortado pelo eixo)
    fig.update_traces(cliponaxis=False)
    
    fig.update_layout(
        title_text='Giro de Estoque',
        title_font={'size':14, 'family':'Arial'},
        width=450,
        height=600,
        template="plotly_white",
        showlegend=False,
        xaxis=dict(visible=False, range=[0, 105], automargin=True),
        yaxis=dict(
            title=None,
            automargin=True,
            categoryorder='array',
            categoryarray=df['classificacao_n2']  # garante a ordem decrescente (maior no topo)
        ),
        margin=dict(t=50, b=20, l=120, r=60),
        bargap=0.12,
        autosize=True
    )
    return fig

def criar_grafico_fator_cobertura_por_classificacao_n2(df_fator_cobertura):
    """Gráfico de fator de cobertura por classificação N2 - DuckDB"""
    df = df_fator_cobertura.copy()

    if df.empty:
        return go.Figure().update_layout(title_text='Fator de Cobertura por Classificação N2 (Sem dados)')

    # Ordenar por classificação N2
    df = df[df['cobertura_ratio']>0]

    # Ordenar por cobertura desc para mostrar maiores no topo
    df = df.sort_values('cobertura_ratio', ascending=True)

    # Cores baseadas no valor (DeepSkyBlue para bom, CadetBlue para ruim)
    bar_colors = ['DeepSkyBlue' if v >= 3 else 'CadetBlue' for v in df['cobertura_ratio']]

    fig = go.Figure(go.Bar(
        x=df['cobertura_ratio'],
        y=df['classificacao_n2'],
        orientation='h',
        marker_color=bar_colors,
        texttemplate='%{x:.1f}',
        textposition='outside',
        textfont_color='darkgrey',
        textfont_size=13,
        textangle=0
    ))
    
    # Garantir que o texto posicionado fora das barras seja renderizado (não cortado pelo eixo)
    fig.update_traces(cliponaxis=False)
    
    fig.update_layout(
        title_text='Fator de Cobertura',
        title_font={'size':14, 'family':'Arial'},
        width=450,
        height=600,
        template="plotly_white",
        showlegend=False,
        xaxis=dict(visible=False, range=[0, 25], automargin=True),
        yaxis=dict(
            title=None,
            automargin=True,
            categoryorder='array',
            categoryarray=df['classificacao_n2']  # garante a ordem decrescente (maior no topo)
        ),
        margin=dict(t=50, b=20, l=120, r=60),
        bargap=0.12,
        autosize=True
    )
    return fig

def criar_grafico_primeira_venda_por_classificacao_n2(df_primeira_venda_class_n2):
    """Gráfico de primeira venda por classificação N2 - DuckDB"""
    df = df_primeira_venda_class_n2.copy()

    if df.empty:
        return go.Figure().update_layout(title_text='Primeira Venda por Classificação N2 (Sem dados)')

    # Ordenar por classificação N2
    df = df[df['tempo_primeira_venda_geral']>0]

    # Ordenar por cobertura desc para mostrar maiores no topo
    df = df.sort_values('tempo_primeira_venda_geral', ascending=False)

    # Cores baseadas no valor (DeepSkyBlue para bom, CadetBlue para ruim)
    bar_colors = ['DeepSkyBlue' if v <= 10 else 'CadetBlue' for v in df['tempo_primeira_venda_geral']]

    fig = go.Figure(go.Bar(
        x=df['tempo_primeira_venda_geral'],
        y=df['classificacao_n2'],
        orientation='h',
        marker_color=bar_colors,
        texttemplate='%{x:.1f}',
        textposition='outside',
        textfont_color='darkgrey',
        textfont_size=13,
        textangle=0
    ))
    
    # Garantir que o texto posicionado fora das barras seja renderizado (não cortado pelo eixo)
    fig.update_traces(cliponaxis=False)
    
    fig.update_layout(
        title_text='Dias para a 1ª Venda',
        title_font={'size':14, 'family':'Arial'},
        width=450,
        height=600,
        template="plotly_white",
        showlegend=False,
        xaxis=dict(visible=False, range=[0, 30], automargin=True),
        yaxis=dict(
            title=None,
            automargin=True,
            categoryorder='array',
            categoryarray=df['classificacao_n2']  # garante a ordem decrescente (maior no topo)
        ),
        margin=dict(t=50, b=20, l=120, r=60),
        bargap=0.12,
        autosize=True
    )
    return fig


def criar_grafico_primeira_venda_30d_por_classificacao_n2(df_primeira_venda_class_n2):
    """Gráfico de primeira venda após 30 dias por classificação N2 - DuckDB"""
    df = df_primeira_venda_class_n2.copy()

    if df.empty:
        return go.Figure().update_layout(title_text='Primeira Venda Após 30 dias por Classificação N2 (Sem dados)')

    # Ordenar por classificação N2
    df = df[df['tempo_primeira_venda_apos_30d']>0]

    # Ordenar por cobertura desc para mostrar maiores no topo
    df = df.sort_values('tempo_primeira_venda_apos_30d', ascending=False)

    # Cores baseadas no valor (DeepSkyBlue para bom, CadetBlue para ruim)
    bar_colors = ['DeepSkyBlue' if v <= 45 else 'CadetBlue' for v in df['tempo_primeira_venda_apos_30d']]

    fig = go.Figure(go.Bar(
        x=df['tempo_primeira_venda_apos_30d'],
        y=df['classificacao_n2'],
        orientation='h',
        marker_color=bar_colors,
        texttemplate='%{x:.1f}',
        textposition='outside',
        textfont_color='darkgrey',
        textfont_size=13,
        textangle=0
    ))
    
    # Garantir que o texto posicionado fora das barras seja renderizado (não cortado pelo eixo)
    fig.update_traces(cliponaxis=False)
    
    fig.update_layout(
        title_text='Dias para a 1ª Venda (30 dias)',
        title_font={'size':14, 'family':'Arial'},
        width=450,
        height=600,
        template="plotly_white",
        showlegend=False,
        xaxis=dict(visible=False, range=[0, 90], automargin=True),
        yaxis=dict(
            title=None,
            automargin=True,
            categoryorder='array',
            categoryarray=df['classificacao_n2']  # garante a ordem decrescente (maior no topo)
        ),
        margin=dict(t=50, b=20, l=120, r=60),
        bargap=0.12,
        autosize=True
    )
    return fig

def criar_grafico_curva_d_por_classificacao_n2(df_curva_d):
    """Gráfico de Nascimento de Curva D por classificação N2 - DuckDB"""
    df = df_curva_d.copy()

    if df.empty:
        return go.Figure().update_layout(title_text='Nascimento de Curva D por Classificação N2 (Sem dados)')

    # Ordenar por classificação N2
    df = df[df['pct_value']>0]

    # Ordenar por giro desc para mostrar maiores no topo
    df = df.sort_values('pct_value', ascending=False)

    # Cores baseadas no valor (DeepSkyBlue para bom, CadetBlue para ruim)
    bar_colors = ['DeepSkyBlue' if v <= 10 else 'CadetBlue' for v in df['pct_value']]

    fig = go.Figure(go.Bar(
        x=df['pct_value'],
        y=df['classificacao_n2'],
        orientation='h',
        marker_color=bar_colors,
        texttemplate='%{x:.1f}%',
        textposition='outside',
        textfont_color='darkgrey',
        textfont_size=13,
        textangle=0
    ))
    
    # Garantir que o texto posicionado fora das barras seja renderizado (não cortado pelo eixo)
    fig.update_traces(cliponaxis=False)
    
    fig.update_layout(
        title_text='Conversão para Curva D',
        title_font={'size':14, 'family':'Arial'},
        width=450,
        height=600,
        template="plotly_white",
        showlegend=False,
        xaxis=dict(visible=False, range=[0, 105], automargin=True),
        yaxis=dict(
            title=None,
            automargin=True,
            categoryorder='array',
            categoryarray=df['classificacao_n2']  # garante a ordem decrescente (maior no topo)
        ),
        margin=dict(t=50, b=20, l=120, r=60),
        bargap=0.12,
        autosize=True
    )
    return fig


def criar_grafico_desfazimento_curva_d_por_classificacao_n2(df_desfazimento_curva_d):
    """Gráfico de Desfazimento de Curva D por classificação N2 - DuckDB"""
    df = df_desfazimento_curva_d.copy()

    if df.empty:
        return go.Figure().update_layout(title_text='Desfazimento de Curva D por Classificação N2 (Sem dados)')

    # Ordenar por classificação N2
    df = df[df['pct_value']>0]

    # Ordenar por giro desc para mostrar maiores no topo
    df = df.sort_values('pct_value', ascending=True)

    # Cores baseadas no valor (DeepSkyBlue para bom, CadetBlue para ruim)
    bar_colors = ['DeepSkyBlue' if v >= 10 else 'CadetBlue' for v in df['pct_value']]
    
    fig = go.Figure(go.Bar(
        x=df['pct_value'],
        y=df['classificacao_n2'],
        orientation='h',
        marker_color=bar_colors,
        texttemplate='%{x:.1f}%',
        textposition='outside',
        textfont_color='darkgrey',
        textfont_size=13,
        textangle=0
    ))
    
    # Garantir que o texto posicionado fora das barras seja renderizado (não cortado pelo eixo)
    fig.update_traces(cliponaxis=False)
    
    fig.update_layout(
        title_text='Venda  Curva D (30 dias)',
        title_font={'size':14, 'family':'Arial'},
        width=450,
        height=600,
        template="plotly_white",
        showlegend=False,
        xaxis=dict(visible=False, range=[0, 105], automargin=True),
        yaxis=dict(
            title=None,
            automargin=True,
            categoryorder='array',
            categoryarray=df['classificacao_n2']  # garante a ordem decrescente (maior no topo)
        ),
        margin=dict(t=50, b=20, l=120, r=60),
        bargap=0.12,
        autosize=True
    )
    return fig

def criar_grafico_gmroi_por_filial_ano(df_gmroi):
    """Gráfico de GMROI por filial - DuckDB"""
    # Filtrar apenas filiais (excluir 'Geral')
    df = df_gmroi[df_gmroi['filial_codigo'] != 'Geral'].copy()
    
    if df.empty:
        return go.Figure().update_layout(title_text='GMROI por Filial (Sem dados)')

    df = df.sort_values('filial_codigo')
    # Cores baseadas no valor (DeepSkyBlue para bom, CadetBlue para ruim)
    bar_colors = ['DeepSkyBlue' if v >= 1 else 'CadetBlue' for v in df['gmroi_ratio']]

    # Calcular range dinâmico: 10% abaixo do mínimo e 10% acima do máximo
    min_val = float(df['gmroi_ratio'].min())
    max_val = float(df['gmroi_ratio'].max())
    span = max_val - min_val
    if span == 0:
        pad = max(1.0, abs(max_val) * 0.1)
    else:
        pad = span * 0.1
    y_min = 0
    y_max = max_val + pad * 4

    fig = go.Figure(go.Bar(
        x=df['filial_codigo'],
        y=df['gmroi_ratio'],
        marker_color=bar_colors,
        texttemplate='%{y:.2f}',
        textposition='inside',
        textfont_color='white',
        textfont_size=12,
        textangle=0
    ))
    
    fig.update_layout(
        title_text='GMROI - Retorno de Margem Bruta (360 dias)',  # <-- título aqui
        title={'x':0, 'xanchor':'left', 'yanchor':'top'},  # opcional: centraliza
        title_font={'size':14, 'family':'Arial'},
        width=600,
        height=120,
        template="plotly_white",
        showlegend=False,
        xaxis=dict(title=None, automargin=True),
        yaxis=dict(visible=False, range=[y_min, y_max], automargin=True),
        margin=dict(t=10, b=30, l=10, r=10),
        bargap=0.12,
        autosize=True
    )
    return fig

def criar_grafico_gmroi_por_filial_90d(df_gmroi):
    """Gráfico de GMROI por filial - DuckDB"""
    # Filtrar apenas filiais (excluir 'Geral')
    df = df_gmroi[df_gmroi['filial_codigo'] != 'Geral'].copy()
    
    if df.empty:
        return go.Figure().update_layout(title_text='GMROI por Filial (Sem dados)')

    df = df.sort_values('filial_codigo')
    # Cores baseadas no valor (DeepSkyBlue para bom, CadetBlue para ruim)
    bar_colors = ['DeepSkyBlue' if v >= 1 else 'CadetBlue' for v in df['gmroi_ratio']]

    # Calcular range dinâmico: 10% abaixo do mínimo e 10% acima do máximo
    min_val = float(df['gmroi_ratio'].min())
    max_val = float(df['gmroi_ratio'].max())
    span = max_val - min_val
    if span == 0:
        pad = max(1.0, abs(max_val) * 0.1)
    else:
        pad = span * 0.1
    y_min = 0
    y_max = max_val + pad * 4

    fig = go.Figure(go.Bar(
        x=df['filial_codigo'],
        y=df['gmroi_ratio'],
        marker_color=bar_colors,
        texttemplate='%{y:.2f}',
        textposition='inside',
        textfont_color='white',
        textfont_size=12,
        textangle=0
    ))
    
    fig.update_layout(
        title_text='GMROI - Retorno de Margem Bruta (90 dias)',  # <-- título aqui
        title={'x':0, 'xanchor':'left', 'yanchor':'top'},  # opcional: centraliza
        title_font={'size':14, 'family':'Arial'},
        width=600,
        height=120,
        template="plotly_white",
        showlegend=False,
        xaxis=dict(title=None, automargin=True),
        yaxis=dict(visible=False, range=[y_min, y_max], automargin=True),
        margin=dict(t=10, b=30, l=10, r=10),
        bargap=0.12,
        autosize=True
    )
    return fig

def criar_grafico_gmroi_por_curva_abc_duck_ano(df_gmroi):
    """Gráfico de GMROI por curva ABC - DuckDB"""
    df = df_gmroi.copy()
    
    if df.empty:
        return go.Figure().update_layout(title_text='GMROI por Curva ABC (Sem dados)')
    
    # Ordenar por curva ABC (A, B, C, D)
    curva_order = {'A': 1, 'B': 2, 'C': 3, 'D': 4}
    df['order'] = df['curvaABC'].map(curva_order)
    df = df[df['gmroi_ratio']>0]
    df = df.sort_values('order')
    
    # Cores baseadas no valor (DeepSkyBlue para bom, CadetBlue para ruim)
    bar_colors = ['DeepSkyBlue' if v >= 1 else 'CadetBlue' for v in df['gmroi_ratio']]

    threshold = max(df['gmroi_ratio']) * 0.4
    text_positions = ['inside' if v >= threshold else 'outside' for v in df['gmroi_ratio']]
    text_colors = ['white' if pos == 'inside' else 'darkgrey' for pos in text_positions]

    fig = go.Figure(go.Bar(
        x=df['curvaABC'],
        y=df['gmroi_ratio'],
        marker_color=bar_colors,
        texttemplate='%{y:.2f}',
        textposition=text_positions,
        textfont_color=text_colors,
        textfont_size=12,
        textangle=0,
        cliponaxis=False
    ))
    
    fig.update_layout(
        title_text='GMROI - Retorno da Margem Bruta (360 dias)',  # <-- título aqui
        title={'x':0, 'xanchor':'left', 'yanchor':'top'},
        title_font={'size':14, 'family':'Arial'},
        width=600,
        height=180,
        template="plotly_white",
        showlegend=False,
        xaxis=dict(title=None, automargin=True),
        yaxis=dict(visible=False, automargin=True),
        margin=dict(t=20, b=20, l=10, r=10),
        bargap=0.12,
        autosize=True
    )
    return fig

def criar_grafico_gmroi_por_curva_abc_duck_90(df_gmroi):
    """Gráfico de GMROI por curva ABC - DuckDB"""
    df = df_gmroi.copy()
    
    if df.empty:
        return go.Figure().update_layout(title_text='GMROI por Curva ABC (Sem dados)')
    
    # Ordenar por curva ABC (A, B, C, D)
    curva_order = {'A': 1, 'B': 2, 'C': 3, 'D': 4}
    df['order'] = df['curvaABC'].map(curva_order)
    df = df[df['gmroi_ratio']>0]
    df = df.sort_values('order')
    
    # Cores baseadas no valor (DeepSkyBlue para bom, CadetBlue para ruim)
    bar_colors = ['DeepSkyBlue' if v >= 1 else 'CadetBlue' for v in df['gmroi_ratio']]

    threshold = max(df['gmroi_ratio']) * 0.4
    text_positions = ['inside' if v >= threshold else 'outside' for v in df['gmroi_ratio']]
    text_colors = ['white' if pos == 'inside' else 'darkgrey' for pos in text_positions]

    fig = go.Figure(go.Bar(
        x=df['curvaABC'],
        y=df['gmroi_ratio'],
        marker_color=bar_colors,
        texttemplate='%{y:.2f}',
        textposition=text_positions,
        textfont_color=text_colors,
        textfont_size=12,
        textangle=0,
        cliponaxis=False
    ))
    
    fig.update_layout(
        title_text='GMROI - Retorno da Margem Bruta (90 dias)',  # <-- título aqui
        title={'x':0, 'xanchor':'left', 'yanchor':'top'},
        title_font={'size':14, 'family':'Arial'},
        width=600,
        height=180,
        template="plotly_white",
        showlegend=False,
        xaxis=dict(title=None, automargin=True),
        yaxis=dict(visible=False, automargin=True),
        margin=dict(t=20, b=20, l=10, r=10),
        bargap=0.12,
        autosize=True
    )
    return fig

def criar_grafico_gmroi_class_n1_duck_ano(df_gmroi):
    """Gráfico de GMROI por Classificação N1 (Ano) - DuckDB"""
    df = df_gmroi[df_gmroi['classificacao_n1'] != 'USO CONSUMO E SERVIÇOS'].copy()
    
    if df.empty:
        return go.Figure().update_layout(title_text='GMROI por Classificação N1 (Sem dados)')

    # Ordenar por Classificação N1
    df = df[df['classificacao_n1'].notnull()]
    df = df[df['gmroi_ratio']>0]
    df = df.sort_values('classificacao_n1')
    
    # Cores baseadas no valor (DeepSkyBlue para bom, CadetBlue para ruim)
    bar_colors = ['DeepSkyBlue' if v >= 1 else 'CadetBlue' for v in df['gmroi_ratio']]

    threshold = max(df['gmroi_ratio']) * 0.4
    text_positions = ['inside' if v >= threshold else 'outside' for v in df['gmroi_ratio']]
    text_colors = ['white' if pos == 'inside' else 'darkgrey' for pos in text_positions]

    fig = go.Figure(go.Bar(
        x=df['classificacao_n1'],
        y=df['gmroi_ratio'],
        marker_color=bar_colors,
        texttemplate='%{y:.2f}',
        textposition=text_positions,
        textfont_color=text_colors,
        textfont_size=12,
        textangle=0,
        cliponaxis=False
    ))
    
    fig.update_layout(
        title_text='GMROI - Retorno da Margem Bruta (360 dias)',  # <-- título aqui
        title={'x':0, 'xanchor':'left', 'yanchor':'top'},
        title_font={'size':14, 'family':'Arial'},
        width=600,
        height=180,
        template="plotly_white",
        showlegend=False,
        xaxis=dict(title=None, automargin=True),
        yaxis=dict(visible=False, automargin=True),
        margin=dict(t=20, b=20, l=10, r=10),
        bargap=0.12,
        autosize=True
    )
    return fig

def criar_grafico_gmroi_class_n1_abc_duck_90(df_gmroi):
    """Gráfico de GMROI por Classificação N1 (90 dias) - DuckDB"""
    df = df_gmroi[df_gmroi['classificacao_n1'] != 'USO CONSUMO E SERVIÇOS'].copy()
    
    if df.empty:
        return go.Figure().update_layout(title_text='GMROI por Classificação N1 (Sem dados)')

    # Ordenar por Classificação N1
    df = df[df['classificacao_n1'].notnull()]
    df = df[df['gmroi_ratio']>0]
    df = df.sort_values('classificacao_n1')

    # Cores baseadas no valor (DeepSkyBlue para bom, CadetBlue para ruim)
    bar_colors = ['DeepSkyBlue' if v >= 1 else 'CadetBlue' for v in df['gmroi_ratio']]

    threshold = max(df['gmroi_ratio']) * 0.4
    text_positions = ['inside' if v >= threshold else 'outside' for v in df['gmroi_ratio']]
    text_colors = ['white' if pos == 'inside' else 'darkgrey' for pos in text_positions]

    fig = go.Figure(go.Bar(
        x=df['classificacao_n1'],
        y=df['gmroi_ratio'],
        marker_color=bar_colors,
        texttemplate='%{y:.2f}',
        textposition=text_positions,
        textfont_color=text_colors,
        textfont_size=12,
        textangle=0,
        cliponaxis=False
    ))
    
    fig.update_layout(
        title_text='GMROI - Retorno da Margem Bruta (90 dias)',  # <-- título aqui
        title={'x':0, 'xanchor':'left', 'yanchor':'top'},
        title_font={'size':14, 'family':'Arial'},
        width=600,
        height=180,
        template="plotly_white",
        showlegend=False,
        xaxis=dict(title=None, automargin=True),
        yaxis=dict(visible=False, automargin=True),
        margin=dict(t=20, b=20, l=10, r=10),
        bargap=0.12,
        autosize=True
    )
    return fig

def criar_grafico_gmroi_class_n2_duck_ano(df_gmroi):
    """Gráfico de GMROI por Classificação N2 (Ano) - DuckDB"""
    df = df_gmroi[df_gmroi['classificacao_n2'] != 'USO CONSUMO E SERVIÇOS'].copy()

    if df.empty:
        return go.Figure().update_layout(title_text='GMROI por Classificação N2 (Sem dados)')

    # Ordenar por Classificação N2
    df = df[df['classificacao_n2'].notnull()]
    df = df[df['gmroi_ratio']>0]
    df = df.sort_values('gmroi_ratio', ascending=True)
    
    # Cores baseadas no valor (DeepSkyBlue para bom, CadetBlue para ruim)
    bar_colors = ['DeepSkyBlue' if v >= 1 else 'CadetBlue' for v in df['gmroi_ratio']]

    fig = go.Figure(go.Bar(
        x=df['gmroi_ratio'],
        y=df['classificacao_n2'],
        orientation='h',
        marker_color=bar_colors,
        texttemplate='%{x:.2f}',
        textposition='outside',
        textfont_color='darkgrey',
        textfont_size=12,
        textangle=0,
        cliponaxis=False
    ))
    
    fig.update_layout(
        title_text='GMROI - Retorno<br>da Margem Bruta (360 dias)',  # <-- título aqui
        title={'x':0, 'xanchor':'left', 'yanchor':'top'},
        title_font={'size':14, 'family':'Arial'},
        width=450,
        height=600,
        template="plotly_white",
        showlegend=False,
        xaxis=dict(visible=False, automargin=True),
        yaxis=dict(
            title=None,
            automargin=True,
            categoryorder='array',
            categoryarray=df['classificacao_n2']
        ),
        margin=dict(t=50, b=20, l=120, r=60),
        bargap=0.12,
        autosize=True
    )
    return fig
    
def criar_grafico_gmroi_class_n2_duck_90(df_gmroi):
    """Gráfico de GMROI por Classificação N2 (90 dias) - DuckDB"""
    df = df_gmroi[df_gmroi['classificacao_n2'] != 'USO CONSUMO E SERVIÇOS'].copy()

    if df.empty:
        return go.Figure().update_layout(title_text='GMROI por Classificação N2 (Sem dados)')

    df = df[df['classificacao_n2'].notnull()]
    df = df[df['gmroi_ratio'] > 0]
    df = df.sort_values('gmroi_ratio', ascending=True)

    bar_colors = ['DeepSkyBlue' if v >= 1 else 'CadetBlue' for v in df['gmroi_ratio']]

    fig = go.Figure(go.Bar(
        x=df['gmroi_ratio'],
        y=df['classificacao_n2'],
        orientation='h',
        marker_color=bar_colors,
        texttemplate='%{x:.2f}',
        textposition='outside',
        textfont_color='darkgrey',
        textfont_size=12,
        textangle=0,
        cliponaxis=False
    ))

    fig.update_layout(
        title_text='GMROI - Retorno<br>da Margem Bruta (90 dias)',
        title={'x': 0, 'xanchor': 'left', 'yanchor': 'top'},
        title_font={'size': 14, 'family': 'Arial'},
        width=450,
        height=600,
        template="plotly_white",
        showlegend=False,
        xaxis=dict(visible=False, automargin=True),
        yaxis=dict(
            title=None,
            automargin=True,
            categoryorder='array',
            categoryarray=df['classificacao_n2']
        ),
        margin=dict(t=50, b=20, l=120, r=60),
        bargap=0.12,
        autosize=True
    )
    return fig