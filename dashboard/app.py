"""
Modern Traffic Management Dashboard
Professional, minimalistic design with real-time monitoring.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Optional, Dict

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit.components.v1 as components

# Add project paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

OUTPUT_DIR = PROJECT_ROOT / 'output'
HISTORY_DIR = OUTPUT_DIR / 'history'
ASSETS_DIR = PROJECT_ROOT / 'dashboard' / 'assets'

# ============================================== #
# UI CONFIGURATION & STYLES
# ============================================== #

st.set_page_config(
    page_title="AI Traffic Control",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded"
)

import base64

def load_custom_css():
    """Simple custom CSS."""
    st.markdown("""
        <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 5rem;
        }
        </style>
    """, unsafe_allow_html=True)

def load_shader_background():
    pass

def load_shader_background():
    """Deprecated: Replaced with CSS-only background for stability."""
    pass
    return None


# ============================================== #
# DATA LOADING
# ============================================== #

def load_results(mode: str, base_dir: Optional[Path] = None) -> Optional[Dict]:
    """Load simulation results."""
    directory = base_dir or OUTPUT_DIR
    filepath = directory / f"{mode}_summary.json"
    if filepath.exists():
        with open(filepath, 'r') as f:
            return json.load(f)
    return None

def load_csv_data(mode: str, base_dir: Optional[Path] = None) -> Optional[pd.DataFrame]:
    """Load simulation CSV data."""
    directory = base_dir or OUTPUT_DIR
    filepath = directory / f"{mode}_simulation_metrics.csv"
    if filepath.exists():
        return pd.read_csv(filepath)
    return None

def load_history() -> list:
    """Load simulation history index."""
    filepath = HISTORY_DIR / 'index.json'
    if filepath.exists():
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def load_comparison() -> Optional[Dict]:
    """Load comparison results."""
    filepath = OUTPUT_DIR / 'mode_comparison.json'
    if filepath.exists():
        with open(filepath, 'r') as f:
            return json.load(f)
    return None


# ============================================== #
# CHART COMPONENTS
# ============================================== #

def create_line_chart(df: pd.DataFrame, y_col: str, title: str, color: str = "#00d4ff"):
    """Create a modern line chart."""
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['simulation_time'],
        y=df[y_col],
        mode='lines',
        line=dict(color=color, width=2),
        fill='tozeroy',
        fillcolor=f'rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.1)'
    ))
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color='white')),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='rgba(255,255,255,0.7)'),
        xaxis=dict(
            title='Time (s)',
            gridcolor='rgba(255,255,255,0.1)',
            showgrid=True
        ),
        yaxis=dict(
            title='',
            gridcolor='rgba(255,255,255,0.1)',
            showgrid=True
        ),
        margin=dict(l=40, r=40, t=60, b=40),
        height=300
    )
    
    return fig

def create_comparison_bars(fixed_val: float, adaptive_val: float, title: str):
    """Create comparison bar chart."""
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=['Fixed-Time', 'Adaptive'],
        y=[fixed_val, adaptive_val],
        marker_color=['#ff6b6b', '#00d4ff'],
        text=[f'{fixed_val:.1f}', f'{adaptive_val:.1f}'],
        textposition='outside',
        textfont=dict(color='white', size=14)
    ))
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color='white')),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='rgba(255,255,255,0.7)'),
        yaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
        margin=dict(l=40, r=40, t=60, b=40),
        height=300,
        showlegend=False
    )
    
    return fig

def create_gauge(value: float, title: str):
    """Create efficiency gauge."""
    color = '#10b981' if value > 0 else '#ef4444'
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        title=dict(text=title, font=dict(size=16, color='white')),
        number=dict(suffix='%', font=dict(color='white', size=40)),
        gauge=dict(
            axis=dict(range=[-50, 100], tickcolor='white'),
            bar=dict(color=color),
            bgcolor='rgba(255,255,255,0.1)',
            bordercolor='rgba(255,255,255,0.2)',
            steps=[
                dict(range=[-50, 0], color='rgba(239,68,68,0.3)'),
                dict(range=[0, 50], color='rgba(251,191,36,0.3)'),
                dict(range=[50, 100], color='rgba(16,185,129,0.3)')
            ]
        )
    ))
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        height=250,
        margin=dict(l=30, r=30, t=60, b=30)
    )
    
    return fig


# ============================================== #
# SIDEBAR
# ============================================== #

def render_sidebar():
    """Render sidebar controls."""
    with st.sidebar:
        st.markdown("## 🎛️ Control Panel")
        st.divider()
        
        # Mode selection
        mode = st.selectbox(
            "🚦 Control Mode",
            ['adaptive', 'fixed', 'comparison'],
            format_func=lambda x: {
                'adaptive': '🧠 Adaptive AI',
                'fixed': '⏱️ Fixed-Time',
                'comparison': '📊 Compare Both'
            }[x]
        )
        
        # Duration
        duration = st.slider("⏱️ Duration", 300, 7200, 3600, 300)
        st.caption(f"📍 {duration // 60} minutes")
        
        # GUI toggle
        use_gui = st.toggle("🖥️ Show SUMO GUI", value=True)
        
        st.divider()
        
        # Run button
        if st.button("▶️ Run Simulation", use_container_width=True, type="primary"):
            cmd = [sys.executable, str(PROJECT_ROOT / 'src' / 'main.py')]
            
            if mode == 'comparison':
                cmd.append('--compare')
            else:
                cmd.extend(['--mode', mode])
            
            cmd.extend(['--duration', str(duration)])
            
            if not use_gui:
                cmd.append('--no-gui')
            
            subprocess.Popen(cmd, cwd=str(PROJECT_ROOT))
            st.success("✅ Simulation started!")
        
        st.divider()
        
        # History Selection
        st.markdown("### 📜 History")
        
        history = load_history()
        # Create mapping of display label to run info
        history_map = {
            f"{h['timestamp']} ({h['mode'].upper()})": h 
            for h in history
        }
        
        options = ["Latest Run (Local)"] + list(history_map.keys())
        selected_option = st.selectbox("Select Run", options)
        
        selected_run_info = None
        if selected_option != "Latest Run (Local)":
            selected_run_info = history_map[selected_option]
            
        st.divider()
        
        # Refresh data
        st.markdown("### 📁 Data Actions")
        
        if st.button("🔄 Reload Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
            
        return mode, selected_run_info


# ============================================== #
# MAIN CONTENT
# ============================================== #

def render_header():
    """Render main header."""
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        st.markdown("""
        <div style='text-align: center; padding: 20px 0;'>
            <h1 style='font-size: 2.5rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>
                🚦 Intelligent Traffic Control
            </h1>
            <p style='color: rgba(255,255,255,0.6); font-size: 1.1rem;'>
                AI-Powered Traffic Management System
            </p>
        </div>
        """, unsafe_allow_html=True)


def render_overview(selected_run_info):
    """Render overview section."""
    
    # Determine what to load
    adaptive = None
    fixed = None
    
    if selected_run_info:
        # Load historical run
        run_mode = selected_run_info['mode']
        run_dir = HISTORY_DIR / selected_run_info['run_id']
        
        if run_mode == 'adaptive':
            adaptive = load_results('adaptive', run_dir)
        else:
            fixed = load_results('fixed', run_dir)
            
        st.info(f"📂 Viewing historical run: **{selected_run_info['timestamp']}** (Mode: {run_mode.upper()})")
        
    else:
        # Load latest local data (default behavior)
        adaptive = load_results('adaptive')
        fixed = load_results('fixed')
    
    st.session_state.adaptive_data = adaptive
    st.session_state.fixed_data = fixed
    
    # Adaptive metrics
    st.markdown("### 🧠 Adaptive Control Performance")
    cols = st.columns(4)
    
    if adaptive:
        with cols[0]:
            st.metric("Avg Wait Time", f"{adaptive.get('average_waiting_time', 0):.1f}s")
        with cols[1]:
            st.metric("Max Wait Time", f"{adaptive.get('max_waiting_time', 0):.1f}s")
        with cols[2]:
            st.metric("Avg Queue", f"{adaptive.get('average_queue_length', 0):.0f}")
        with cols[3]:
            st.metric("Phase Changes", adaptive.get('total_phase_changes', 0))
    else:
        for col in cols:
            with col:
                st.metric("--", "--")
        st.info("💡 Run an adaptive simulation to see results")
    
    # Fixed metrics
    st.markdown("### ⏱️ Fixed-Time Control Performance")
    cols = st.columns(4)
    
    if fixed:
        with cols[0]:
            st.metric("Avg Wait Time", f"{fixed.get('average_waiting_time', 0):.1f}s")
        with cols[1]:
            st.metric("Max Wait Time", f"{fixed.get('max_waiting_time', 0):.1f}s")
        with cols[2]:
            st.metric("Avg Queue", f"{fixed.get('average_queue_length', 0):.0f}")
        with cols[3]:
            st.metric("Phase Changes", fixed.get('total_phase_changes', 0))
    else:
        for col in cols:
            with col:
                st.metric("--", "--")
        st.info("💡 Run a fixed-time simulation to see results")
    
    # Improvement summary
    if adaptive and fixed:
        improvement = ((fixed.get('average_waiting_time', 0) - adaptive.get('average_waiting_time', 0)) 
                       / max(fixed.get('average_waiting_time', 0), 0.1)) * 100
        
        if improvement > 0:
            st.success(f"🎉 **Adaptive control is {improvement:.1f}% more efficient!**")
        else:
            st.warning(f"⚠️ Fixed-time performed {-improvement:.1f}% better in this scenario")


def render_realtime_tab(selected_run_info):
    """Render real-time monitoring tab."""
    st.markdown("### 📈 Time Series Analysis")
    
    # Mode selector
    view_mode = st.radio(
        "Select data to view",
        ['adaptive', 'fixed', 'both'],
        horizontal=True,
        format_func=lambda x: {'adaptive': '🧠 Adaptive', 'fixed': '⏱️ Fixed', 'both': '📊 Compare Both'}[x]
    )
    
    # Load CSV data properly
    adaptive_csv = None
    fixed_csv = None
    
    if selected_run_info:
        run_mode = selected_run_info['mode']
        run_dir = HISTORY_DIR / selected_run_info['run_id']
        if run_mode == 'adaptive':
            adaptive_csv = load_csv_data('adaptive', run_dir)
        else:
            fixed_csv = load_csv_data('fixed', run_dir)
    else:
        adaptive_csv = load_csv_data('adaptive')
        fixed_csv = load_csv_data('fixed')
        
    st.session_state.adaptive_csv = adaptive_csv
    st.session_state.fixed_csv = fixed_csv
    
    if view_mode == 'both':
        # Side by side comparison
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🧠 Adaptive")
            if adaptive_csv is not None and not adaptive_csv.empty:
                st.plotly_chart(create_line_chart(adaptive_csv, 'average_waiting_time', 'Waiting Time', '#00d4ff'), use_container_width=True)
            else:
                st.info("No adaptive data")
        
        with col2:
            st.markdown("#### ⏱️ Fixed-Time")
            if fixed_csv is not None and not fixed_csv.empty:
                st.plotly_chart(create_line_chart(fixed_csv, 'average_waiting_time', 'Waiting Time', '#ff6b6b'), use_container_width=True)
            else:
                st.info("No fixed data")
    else:
        df = adaptive_csv if view_mode == 'adaptive' else fixed_csv
        color = '#00d4ff' if view_mode == 'adaptive' else '#ff6b6b'
        
        if df is not None and not df.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                st.plotly_chart(create_line_chart(df, 'average_waiting_time', '⏱️ Average Waiting Time (s)', color), use_container_width=True)
            
            with col2:
                st.plotly_chart(create_line_chart(df, 'total_queue_length', '📊 Queue Length', color), use_container_width=True)
        else:
            st.info(f"💡 Run a {view_mode} simulation to see time series data")


def render_comparison_tab():
    """Render comparison analysis tab."""
    st.markdown("### 📊 Comparison Analysis")
    
    comparison = st.session_state.get('comparison') or load_comparison()
    st.session_state.comparison = comparison
    
    adaptive = st.session_state.get('adaptive_data') or load_results('adaptive')
    fixed = st.session_state.get('fixed_data') or load_results('fixed')
    
    if not (adaptive and fixed):
        st.info("💡 Run both adaptive and fixed simulations, or run a comparison to see analysis")
        return
    
    # Efficiency gauge
    col1, col2 = st.columns([1, 2])
    
    with col1:
        if comparison:
            score = comparison.get('comparison', {}).get('overall_efficiency_score', 0)
        else:
            score = ((fixed.get('average_waiting_time', 0) - adaptive.get('average_waiting_time', 0)) 
                    / max(fixed.get('average_waiting_time', 0), 0.1)) * 100
        
        st.plotly_chart(create_gauge(score, "Efficiency Score"), use_container_width=True)
        
        if score > 0:
            st.success("✅ Adaptive control recommended")
        else:
            st.warning("⚠️ Consider tuning parameters")
    
    with col2:
        # Comparison bars
        col2a, col2b = st.columns(2)
        
        with col2a:
            st.plotly_chart(
                create_comparison_bars(
                    fixed.get('average_waiting_time', 0),
                    adaptive.get('average_waiting_time', 0),
                    '⏱️ Avg Wait Time (s)'
                ),
                use_container_width=True
            )
        
        with col2b:
            st.plotly_chart(
                create_comparison_bars(
                    fixed.get('average_queue_length', 0),
                    adaptive.get('average_queue_length', 0),
                    '📊 Avg Queue Length'
                ),
                use_container_width=True
            )
    
    # Detailed metrics table
    st.markdown("#### 📋 Detailed Metrics")
    
    metrics_data = {
        'Metric': ['Avg Waiting Time', 'Max Waiting Time', 'Avg Queue Length', 'Max Queue Length', 'Phase Changes'],
        'Fixed-Time': [
            f"{fixed.get('average_waiting_time', 0):.2f}s",
            f"{fixed.get('max_waiting_time', 0):.2f}s",
            f"{fixed.get('average_queue_length', 0):.1f}",
            f"{fixed.get('max_queue_length', 0)}",
            f"{fixed.get('total_phase_changes', 0)}"
        ],
        'Adaptive': [
            f"{adaptive.get('average_waiting_time', 0):.2f}s",
            f"{adaptive.get('max_waiting_time', 0):.2f}s",
            f"{adaptive.get('average_queue_length', 0):.1f}",
            f"{adaptive.get('max_queue_length', 0)}",
            f"{adaptive.get('total_phase_changes', 0)}"
        ],
        'Improvement': [
            f"{((fixed.get('average_waiting_time', 0) - adaptive.get('average_waiting_time', 0)) / max(fixed.get('average_waiting_time', 0), 0.1) * 100):.1f}%",
            f"{((fixed.get('max_waiting_time', 0) - adaptive.get('max_waiting_time', 0)) / max(fixed.get('max_waiting_time', 0), 0.1) * 100):.1f}%",
            f"{((fixed.get('average_queue_length', 0) - adaptive.get('average_queue_length', 0)) / max(fixed.get('average_queue_length', 0), 0.1) * 100):.1f}%",
            f"{((fixed.get('max_queue_length', 0) - adaptive.get('max_queue_length', 0)) / max(fixed.get('max_queue_length', 0), 0.1) * 100):.1f}%",
            "--"
        ]
    }
    
    st.dataframe(pd.DataFrame(metrics_data), use_container_width=True, hide_index=True)


def render_data_tab():
    """Render raw data tab."""
    st.markdown("### 📁 Raw Data Explorer")
    
    data_mode = st.radio(
        "Select dataset",
        ['adaptive', 'fixed'],
        horizontal=True,
        format_func=lambda x: '🧠 Adaptive' if x == 'adaptive' else '⏱️ Fixed-Time'
    )
    
    df = load_csv_data(data_mode)
    
    if df is not None and not df.empty:
        st.markdown(f"**{len(df)} data points collected**")
        st.dataframe(df, use_container_width=True, height=400)
        
        # Download button
        csv = df.to_csv(index=False)
        st.download_button(
            "📥 Download CSV",
            csv,
            f"{data_mode}_data.csv",
            "text/csv"
        )
    else:
        st.info(f"💡 No {data_mode} data available.")

        
# ============================================== #
# MAIN APP
# ============================================== #

def main():
    """Main application."""
    mode, selected_run_info = render_sidebar()
    render_header()
    
    st.divider()
    render_overview(selected_run_info)
    
    st.divider()
    
    # Tabs
    tab1, tab2, tab3 = st.tabs([
        "📈 Time Series",
        "📊 Comparison", 
        "📁 Raw Data"
    ])
    
    with tab1:
        render_realtime_tab(selected_run_info)
    
    with tab2:
        render_comparison_tab()
    
    with tab3:
        render_data_tab()


if __name__ == '__main__':
    main()
