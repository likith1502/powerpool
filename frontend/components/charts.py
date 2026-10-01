"""
Plotly chart components for PowerPool Streamlit application.
"""

import plotly.graph_objects as go
from typing import List, Dict, Any


def render_forecast_chart(slots: List[Dict[str, Any]]) -> go.Figure:
    """
    Renders 24-hour demand, solar, and feeder capacity chart with shaded stress region.
    """
    times = [s["time"] for s in slots]
    demand = [s["demand_kw"] for s in slots]
    solar = [s["solar_kw"] for s in slots]
    capacity = [s["capacity_kw"] for s in slots]
    
    fig = go.Figure()

    # Solar area fill
    fig.add_trace(go.Scatter(
        x=times, y=solar,
        name="Solar Generation",
        mode="lines",
        line=dict(color="#F59E0B", width=2),
        fill="tozeroy",
        fillcolor="rgba(245, 158, 11, 0.15)",
    ))

    # Total demand line
    fig.add_trace(go.Scatter(
        x=times, y=demand,
        name="Household Demand",
        mode="lines",
        line=dict(color="#38BDF8", width=3),
    ))

    # Feeder capacity threshold line
    fig.add_trace(go.Scatter(
        x=times, y=capacity,
        name="Feeder Capacity (170 kW)",
        mode="lines",
        line=dict(color="#EF4444", width=2, dash="dash"),
    ))

    # Highlight evening stress window (18:30 to 22:00 -> indices 74 to 88)
    fig.add_vrect(
        x0=times[74], x1=times[88],
        fillcolor="rgba(239, 68, 68, 0.18)",
        layer="below",
        line_width=0,
        annotation_text="Stress Window",
        annotation_position="top left",
        annotation_font=dict(color="#FCA5A5", size=11),
    )

    fig.update_layout(
        title="24-Hour Feeder Demand & Solar Generation",
        xaxis_title="Time of Day",
        yaxis_title="Power (kW)",
        template="plotly_dark",
        paper_bgcolor="#0F172A",
        plot_bgcolor="#0F172A",
        height=380,
        margin=dict(l=40, r=40, t=50, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def render_before_after_chart(
    before_slots: List[Dict[str, Any]],
    after_slots: List[Dict[str, Any]],
    peak_reduction_pct: float = 19.1
) -> go.Figure:
    """
    Renders main DISCOM Before vs After PowerPool demand curve.
    """
    times = [s["time"] for s in before_slots]
    before_demand = [s["demand_kw"] for s in before_slots]
    after_demand = [s["demand_kw"] for s in after_slots]
    capacity = [s["capacity_kw"] for s in before_slots]
    solar = [s["solar_kw"] for s in before_slots]

    fig = go.Figure()

    # Solar generation
    fig.add_trace(go.Scatter(
        x=times, y=solar,
        name="Solar Generation",
        mode="lines",
        line=dict(color="#F59E0B", width=1.5),
        fill="tozeroy",
        fillcolor="rgba(245, 158, 11, 0.1)",
    ))

    # Before PowerPool Demand
    fig.add_trace(go.Scatter(
        x=times, y=before_demand,
        name="Before PowerPool (Unmanaged)",
        mode="lines",
        line=dict(color="#EF4444", width=2.5, dash="dot"),
    ))

    # After PowerPool Demand
    fig.add_trace(go.Scatter(
        x=times, y=after_demand,
        name="After PowerPool (Shifted)",
        mode="lines",
        line=dict(color="#10B981", width=3),
    ))

    # Transformer Capacity
    fig.add_trace(go.Scatter(
        x=times, y=capacity,
        name="Feeder Limit",
        mode="lines",
        line=dict(color="#64748B", width=1.5, dash="dash"),
    ))

    # Annotation for Peak Reduction
    peak_slot_idx = before_demand.index(max(before_demand))
    fig.add_annotation(
        x=times[peak_slot_idx],
        y=max(before_demand),
        text=f"Peak Reduced by {peak_reduction_pct}%",
        showarrow=True,
        arrowhead=2,
        arrowcolor="#10B981",
        arrowsize=1.2,
        ax=0,
        ay=-40,
        font=dict(size=12, color="#10B981", family="Arial Black"),
        bgcolor="#064E3B",
        bordercolor="#10B981",
        borderpad=6,
    )

    fig.update_layout(
        title="Feeder Demand Load Curve — Before vs After Optimization",
        xaxis_title="Time of Day",
        yaxis_title="Demand (kW)",
        template="plotly_dark",
        paper_bgcolor="#0F172A",
        plot_bgcolor="#0F172A",
        height=420,
        margin=dict(l=40, r=40, t=60, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def render_gap_chart(slots: List[Dict[str, Any]]) -> go.Figure:
    """
    Renders Feeder Net Demand Gap (Demand - Capacity) chart.
    """
    times = [s["time"] for s in slots]
    gaps = [s["gap_kw"] for s in slots]
    colors = ["#EF4444" if g > 0 else "#10B981" for g in gaps]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=times, y=gaps,
        marker_color=colors,
        name="Demand Gap (kW)",
    ))

    fig.update_layout(
        title="Feeder Capacity Margin / Overload Gap (kW)",
        xaxis_title="Time of Day",
        yaxis_title="Margin / Gap (kW)",
        template="plotly_dark",
        paper_bgcolor="#0F172A",
        plot_bgcolor="#0F172A",
        height=280,
        margin=dict(l=40, r=40, t=50, b=40),
    )
    return fig
