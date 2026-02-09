"""
Visualization Charts Module for Streamlit Dashboard
Provides real-time and historical chart components.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, List, Any, Optional
from datetime import datetime


# ============================================== #
# CHART CONFIGURATION
# ============================================== #

# Color schemes
COLORS = {
    'primary': '#667eea',
    'secondary': '#764ba2',
    'success': '#10b981',
    'warning': '#f59e0b',
    'danger': '#ef4444',
    'info': '#3b82f6',
    'north': '#ef4444',
    'south': '#10b981',
    'east': '#3b82f6',
    'west': '#f59e0b',
    'adaptive': '#10b981',
    'fixed': '#ef4444',
}

CHART_CONFIG = {
    'displayModeBar': False,
    'scrollZoom': False,
}


# ============================================== #
# REAL-TIME CHARTS
# ============================================== #

def create_waiting_time_chart(data: List[Dict], title: str = "Average Waiting Time") -> go.Figure:
    """
    Create a real-time line chart for waiting time.
    
    Args:
        data: List of {time, value} dictionaries
        title: Chart title
        
    Returns:
        Plotly figure
    """
    if not data:
        return _create_empty_chart(title, "Waiting Time (s)")
    
    df = pd.DataFrame(data)
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['time'],
        y=df['value'],
        mode='lines+markers',
        name='Waiting Time',
        line=dict(color=COLORS['primary'], width=2),
        marker=dict(size=4),
        fill='tozeroy',
        fillcolor='rgba(102, 126, 234, 0.1)',
    ))
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=16)),
        xaxis_title='Simulation Time (s)',
        yaxis_title='Waiting Time (s)',
        hovermode='x unified',
        showlegend=False,
        margin=dict(l=50, r=20, t=50, b=50),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )
    
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.1)')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.1)')
    
    return fig


def create_queue_length_chart(data: List[Dict], title: str = "Queue Length") -> go.Figure:
    """
    Create a real-time line chart for queue length.
    
    Args:
        data: List of {time, value} dictionaries
        title: Chart title
        
    Returns:
        Plotly figure
    """
    if not data:
        return _create_empty_chart(title, "Vehicles")
    
    df = pd.DataFrame(data)
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['time'],
        y=df['value'],
        mode='lines+markers',
        name='Queue Length',
        line=dict(color=COLORS['warning'], width=2),
        marker=dict(size=4),
        fill='tozeroy',
        fillcolor='rgba(245, 158, 11, 0.1)',
    ))
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=16)),
        xaxis_title='Simulation Time (s)',
        yaxis_title='Queue Length (vehicles)',
        hovermode='x unified',
        showlegend=False,
        margin=dict(l=50, r=20, t=50, b=50),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )
    
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.1)')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.1)')
    
    return fig


def create_approach_pressure_chart(approach_data: Dict[str, Dict]) -> go.Figure:
    """
    Create a bar chart showing pressure for each approach.
    
    Args:
        approach_data: Dictionary with approach direction data
        
    Returns:
        Plotly figure
    """
    directions = ['north', 'south', 'east', 'west']
    pressures = [approach_data.get(d, {}).get('pressure', 0) for d in directions]
    colors = [COLORS[d] for d in directions]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=['North', 'South', 'East', 'West'],
        y=pressures,
        marker=dict(
            color=colors,
            line=dict(color='white', width=2)
        ),
        text=[f'{p:.1f}' for p in pressures],
        textposition='outside',
    ))
    
    fig.update_layout(
        title=dict(text='Traffic Pressure by Approach', font=dict(size=16)),
        xaxis_title='Approach',
        yaxis_title='Pressure',
        showlegend=False,
        margin=dict(l=50, r=20, t=60, b=50),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )
    
    return fig


# ============================================== #
# COMPARISON CHARTS
# ============================================== #

def create_comparison_bar_chart(fixed_value: float, adaptive_value: float, 
                                 metric_name: str) -> go.Figure:
    """
    Create a comparison bar chart between fixed and adaptive modes.
    
    Args:
        fixed_value: Value for fixed-time mode
        adaptive_value: Value for adaptive mode
        metric_name: Name of the metric
        
    Returns:
        Plotly figure
    """
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=['Fixed-Time', 'Adaptive'],
        y=[fixed_value, adaptive_value],
        marker=dict(
            color=[COLORS['fixed'], COLORS['adaptive']],
            line=dict(color='white', width=2)
        ),
        text=[f'{fixed_value:.2f}', f'{adaptive_value:.2f}'],
        textposition='outside',
    ))
    
    fig.update_layout(
        title=dict(text=f'{metric_name} Comparison', font=dict(size=16)),
        xaxis_title='Control Mode',
        yaxis_title=metric_name,
        showlegend=False,
        margin=dict(l=50, r=20, t=60, b=50),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )
    
    return fig


def create_efficiency_gauge(score: float) -> go.Figure:
    """
    Create a gauge chart for efficiency score.
    
    Args:
        score: Efficiency score (positive = adaptive is better)
        
    Returns:
        Plotly figure
    """
    # Normalize score to 0-100 range for display
    display_score = min(max(score, -50), 50) + 50  # Map -50,50 to 0,100
    
    color = COLORS['success'] if score > 0 else COLORS['danger']
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=display_score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "System Efficiency Score", 'font': {'size': 18}},
        delta={'reference': 50, 'increasing': {'color': COLORS['success']}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "white"},
            'bar': {'color': color},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 30], 'color': 'rgba(239, 68, 68, 0.3)'},
                {'range': [30, 50], 'color': 'rgba(245, 158, 11, 0.3)'},
                {'range': [50, 70], 'color': 'rgba(245, 158, 11, 0.3)'},
                {'range': [70, 100], 'color': 'rgba(16, 185, 129, 0.3)'}
            ],
            'threshold': {
                'line': {'color': "white", 'width': 4},
                'thickness': 0.75,
                'value': 50
            }
        }
    ))
    
    fig.update_layout(
        margin=dict(l=20, r=20, t=60, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
    )
    
    return fig


def create_improvement_chart(comparison_data: Dict) -> go.Figure:
    """
    Create a chart showing improvement percentages.
    
    Args:
        comparison_data: Comparison results dictionary
        
    Returns:
        Plotly figure
    """
    comp = comparison_data.get('comparison', {})
    
    metrics = ['Waiting Time', 'Queue Length']
    improvements = [
        comp.get('waiting_time_improvement_percent', 0),
        comp.get('queue_length_improvement_percent', 0),
    ]
    
    colors = [COLORS['success'] if v > 0 else COLORS['danger'] for v in improvements]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=metrics,
        y=improvements,
        marker=dict(color=colors),
        text=[f'{v:+.1f}%' for v in improvements],
        textposition='outside',
    ))
    
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    
    fig.update_layout(
        title=dict(text='Improvement with Adaptive Control', font=dict(size=16)),
        xaxis_title='Metric',
        yaxis_title='Improvement (%)',
        showlegend=False,
        margin=dict(l=50, r=20, t=60, b=50),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )
    
    return fig


# ============================================== #
# HISTORICAL ANALYSIS CHARTS
# ============================================== #

def create_timeline_chart(snapshots: List[Dict]) -> go.Figure:
    """
    Create a combined timeline chart showing multiple metrics.
    
    Args:
        snapshots: List of simulation snapshots
        
    Returns:
        Plotly figure
    """
    if not snapshots:
        return _create_empty_chart("Timeline", "Value")
    
    df = pd.DataFrame(snapshots)
    
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        subplot_titles=('Waiting Time', 'Queue Length'),
        vertical_spacing=0.12
    )
    
    # Waiting Time
    fig.add_trace(
        go.Scatter(
            x=df['simulation_time'],
            y=df['average_waiting_time'],
            mode='lines',
            name='Waiting Time',
            line=dict(color=COLORS['primary'], width=2),
        ),
        row=1, col=1
    )
    
    # Queue Length
    fig.add_trace(
        go.Scatter(
            x=df['simulation_time'],
            y=df['total_queue_length'],
            mode='lines',
            name='Queue Length',
            line=dict(color=COLORS['warning'], width=2),
        ),
        row=2, col=1
    )
    
    fig.update_layout(
        title=dict(text='Simulation Timeline', font=dict(size=18)),
        showlegend=True,
        height=500,
        margin=dict(l=50, r=20, t=80, b=50),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )
    
    fig.update_xaxes(title_text='Simulation Time (s)', row=2, col=1)
    fig.update_yaxes(title_text='Seconds', row=1, col=1)
    fig.update_yaxes(title_text='Vehicles', row=2, col=1)
    
    return fig


def create_phase_distribution_chart(phase_changes: List[Dict]) -> go.Figure:
    """
    Create a pie chart showing phase distribution.
    
    Args:
        phase_changes: List of phase change records
        
    Returns:
        Plotly figure
    """
    if not phase_changes:
        return _create_empty_chart("Phase Distribution", "")
    
    # Count phases
    ns_count = sum(1 for p in phase_changes if p.get('to_phase', 0) in [0])
    ew_count = sum(1 for p in phase_changes if p.get('to_phase', 0) in [3])
    
    fig = go.Figure(data=[go.Pie(
        labels=['North-South', 'East-West'],
        values=[ns_count, ew_count],
        hole=0.4,
        marker=dict(colors=[COLORS['info'], COLORS['warning']]),
    )])
    
    fig.update_layout(
        title=dict(text='Green Phase Distribution', font=dict(size=16)),
        margin=dict(l=20, r=20, t=60, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
    )
    
    return fig


# ============================================== #
# HELPER FUNCTIONS
# ============================================== #

def _create_empty_chart(title: str, yaxis_title: str) -> go.Figure:
    """Create an empty chart placeholder."""
    fig = go.Figure()
    
    fig.add_annotation(
        text="No data available",
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=16, color="gray")
    )
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=16)),
        xaxis_title='Time (s)',
        yaxis_title=yaxis_title,
        margin=dict(l=50, r=20, t=50, b=50),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )
    
    return fig


def render_metric_card(label: str, value: Any, delta: Optional[float] = None,
                       delta_color: str = 'normal'):
    """
    Render a metric card in Streamlit.
    
    Args:
        label: Metric label
        value: Metric value
        delta: Optional delta value
        delta_color: Delta color ('normal', 'inverse', 'off')
    """
    st.metric(label=label, value=value, delta=delta, delta_color=delta_color)


def render_status_indicator(status: str, is_active: bool = True):
    """
    Render a status indicator.
    
    Args:
        status: Status text
        is_active: Whether active (green) or inactive (gray)
    """
    color = "🟢" if is_active else "⚫"
    st.markdown(f"{color} **{status}**")
