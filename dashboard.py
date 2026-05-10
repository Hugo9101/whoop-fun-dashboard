import json
import os
import pandas as pd
from pathlib import Path
from dash import Dash, dcc, html, Input, Output
from dotenv import load_dotenv
from sqlalchemy import create_engine
import plotly.graph_objects as go

load_dotenv()
DATA_DIR = Path("data")

def _get_engine():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL not set in .env")
    return create_engine(url)

# ── Theme ──────────────────────────────────────────────────────────────────────
DARK         = "#0d0d0d"
SURFACE      = "#141414"
CARD         = "#1e1e1e"
BORDER       = "#2a2a2a"
TEXT         = "#e8e8e8"
MUTED        = "#888888"
WHOOP_GREEN  = "#818cf8"
WHOOP_BLUE   = "#4c9fff"
WHOOP_RED    = "#ff4c4c"
WHOOP_YELLOW = "#f5c518"
TITLE_GREEN  = "#e2e8f0"


# ── Data ───────────────────────────────────────────────────────────────────────

def load_profile():
    p = DATA_DIR / "profile.json"
    if not p.exists():
        return "Athlete"
    with open(p) as f:
        d = json.load(f)
    return f"{d.get('first_name', '')} {d.get('last_name', '')}".strip()


def load_data():
    engine = _get_engine()

    def read(table):
        try:
            df = pd.read_sql(f"SELECT * FROM {table}", engine)
            print(f"[DB] {table}: {len(df)} rows")
            return df
        except Exception as e:
            print(f"[DB ERROR] {table}: {e}")
            return pd.DataFrame()

    sleep    = read("sleep")
    recovery = read("recovery")
    workouts = read("workouts")
    cycles   = read("cycles")

    for df, col in [(sleep, "start"), (workouts, "start"), (cycles, "start")]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], utc=True)
    if "created_at" in recovery.columns:
        recovery["created_at"] = pd.to_datetime(recovery["created_at"], utc=True)

    return sleep, recovery, workouts, cycles


def apply_date_filter(sleep, recovery, workouts, cycles, days):
    if not days:
        return sleep, recovery, workouts, cycles
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days)

    def clip(df, col):
        return df[df[col] >= cutoff] if col in df.columns and not df.empty else df

    return (
        clip(sleep,    "start"),
        clip(recovery, "created_at"),
        clip(workouts, "start"),
        clip(cycles,   "start"),
    )


# ── Chart builders ─────────────────────────────────────────────────────────────

def base_layout(title):
    return dict(
        title=dict(text=f"<b>{title}</b>", font=dict(color=TITLE_GREEN, size=14), x=0, xanchor="left"),
        paper_bgcolor=CARD,
        plot_bgcolor=CARD,
        font=dict(color=TEXT, family="Inter, system-ui, sans-serif"),
        xaxis=dict(showgrid=False, zeroline=False, color=MUTED),
        yaxis=dict(showgrid=True, gridcolor=BORDER, zeroline=False, color=MUTED),
        margin=dict(l=48, r=24, t=52, b=40),
        hovermode="x unified",
    )


def fig_recovery(recovery):
    s = recovery[recovery["score_state"] == "SCORED"].sort_values("created_at")
    fig = go.Figure(go.Scatter(
        x=s["created_at"], y=s["score_recovery_score"],
        mode="lines+markers", name="Recovery",
        line=dict(color=WHOOP_GREEN, width=2), marker=dict(size=5),
        hovertemplate="%{y:.0f}%<extra></extra>",
    ))
    fig.update_layout(**base_layout("Recovery Score %"))
    fig.update_yaxes(range=[0, 105])
    return fig


def fig_sleep_performance(sleep):
    s = sleep[sleep["score_state"] == "SCORED"].sort_values("start")
    fig = go.Figure(go.Scatter(
        x=s["start"], y=s["score_sleep_performance_percentage"],
        mode="lines+markers", name="Sleep Performance",
        line=dict(color=WHOOP_GREEN, width=2), marker=dict(size=5),
        hovertemplate="%{y:.0f}%<extra></extra>",
    ))
    fig.add_hline(y=85, line_dash="dot", line_color=MUTED,
                  annotation_text="85% target", annotation_font_color=MUTED)
    fig.update_layout(**base_layout("Sleep Performance %"))
    fig.update_yaxes(range=[0, 105])
    return fig


def fig_hrv_rhr(recovery):
    s = recovery[recovery["score_state"] == "SCORED"].sort_values("created_at")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=s["created_at"], y=s["score_hrv_rmssd_milli"],
        mode="lines+markers", name="HRV (ms)",
        line=dict(color=WHOOP_BLUE, width=2), marker=dict(size=5),
        hovertemplate="HRV %{y:.1f} ms<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=s["created_at"], y=s["score_resting_heart_rate"],
        mode="lines+markers", name="RHR (bpm)",
        line=dict(color=WHOOP_RED, width=2), marker=dict(size=5),
        yaxis="y2",
        hovertemplate="RHR %{y:.0f} bpm<extra></extra>",
    ))
    layout = base_layout("HRV & Resting Heart Rate")
    layout["yaxis2"] = dict(overlaying="y", side="right", showgrid=False,
                            zeroline=False, color=MUTED, title="RHR (bpm)")
    layout["legend"] = dict(orientation="h", y=-0.22, x=0.5, xanchor="center",
                            font=dict(color=TEXT))
    layout["margin"]["b"] = 72
    layout["yaxis"]["title"] = "HRV (ms)"
    fig.update_layout(**layout)
    return fig


def fig_sleep_stages(sleep):
    s = sleep[sleep["score_state"] == "SCORED"].sort_values("start")
    to_h = lambda col: s[col] / 3_600_000
    stages = [
        ("score_stage_summary_total_rem_sleep_time_milli",       "REM",   WHOOP_BLUE),
        ("score_stage_summary_total_slow_wave_sleep_time_milli", "SWS",   WHOOP_GREEN),
        ("score_stage_summary_total_light_sleep_time_milli",     "Light", "#a0a0ff"),
        ("score_stage_summary_total_awake_time_milli",           "Awake", WHOOP_RED),
    ]
    fig = go.Figure()
    for col, name, color in stages:
        if col in s.columns:
            fig.add_trace(go.Bar(
                x=s["start"], y=to_h(col), name=name,
                marker_color=color,
                hovertemplate=f"{name}: %{{y:.2f}} h<extra></extra>",
            ))
    fig.update_layout(**base_layout("Sleep Stages (hours)"))
    fig.update_layout(barmode="stack",
                      legend=dict(orientation="h", y=-0.22, x=0.5, xanchor="center",
                                  font=dict(color=TEXT)),
                      margin=dict(l=48, r=24, t=52, b=72))
    return fig


def fig_workout_strain(workouts):
    s = workouts[workouts["score_state"] == "SCORED"].sort_values("start")
    fig = go.Figure(go.Bar(
        x=s["start"], y=s["score_strain"], name="Strain",
        marker_color=WHOOP_YELLOW,
        hovertemplate="Strain %{y:.1f}<extra></extra>",
    ))
    fig.update_layout(**base_layout("Workout Strain"))
    fig.update_yaxes(range=[0, 21])
    return fig


def fig_cycle_strain(cycles):
    s = cycles[cycles["score_state"] == "SCORED"].sort_values("start")
    fig = go.Figure(go.Scatter(
        x=s["start"], y=s["score_strain"],
        mode="lines+markers", name="Day Strain",
        line=dict(color=WHOOP_YELLOW, width=2), marker=dict(size=5),
        hovertemplate="Day Strain %{y:.1f}<extra></extra>",
    ))
    fig.update_layout(**base_layout("Day Strain"))
    fig.update_yaxes(range=[0, 21])
    return fig


# ── UI components ──────────────────────────────────────────────────────────────

def chart_card(fig):
    return html.Div(
        dcc.Graph(figure=fig, config={"displayModeBar": False},
                  responsive=True, style={"minHeight": "280px"}),
        style={"background": CARD, "borderRadius": "12px",
               "border": f"1px solid {BORDER}", "padding": "8px",
               "flex": "1 1 300px", "minWidth": "0"},
    )


def def_section(color, title, rows):
    row_els = []
    for metric, desc in rows:
        row_els.append(html.Div([
            html.Div(metric, style={
                "color": TEXT, "fontWeight": "600", "fontSize": "13px",
                "width": "220px", "flexShrink": "0",
            }),
            html.Div(desc, style={"color": MUTED, "fontSize": "13px", "lineHeight": "1.5"}),
        ], style={
            "display": "flex", "gap": "16px", "padding": "12px 0",
            "borderBottom": f"1px solid {BORDER}",
        }))

    return html.Div([
        html.Div(title, style={
            "color": color, "fontWeight": "700", "fontSize": "11px",
            "letterSpacing": "0.1em", "textTransform": "uppercase",
            "marginBottom": "12px",
        }),
        *row_els,
    ], style={
        "background": CARD, "borderRadius": "12px",
        "border": f"1px solid {BORDER}", "padding": "24px",
        "flex": "1 1 280px", "minWidth": "0",
    })


# ── Page content ───────────────────────────────────────────────────────────────

ROW = {"display": "flex", "flexWrap": "wrap", "gap": "16px", "marginBottom": "16px"}

def dashboard_page(sleep, recovery, workouts, cycles):
    return html.Div([
        html.Div([
            chart_card(fig_recovery(recovery)),
            chart_card(fig_sleep_performance(sleep)),
        ], style=ROW),
        html.Div([
            chart_card(fig_hrv_rhr(recovery)),
            chart_card(fig_cycle_strain(cycles)),
        ], style=ROW),
        html.Div([
            chart_card(fig_sleep_stages(sleep)),
            chart_card(fig_workout_strain(workouts)),
        ], style=ROW),
    ], style={"paddingTop": "16px"})


def definitions_page():
    return html.Div([
        html.P(
            "Definitions of every metric WHOOP tracks, how each is calculated, and what to aim for.",
            style={"color": MUTED, "fontSize": "13px", "marginBottom": "24px", "marginTop": "16px"},
        ),

        html.Div([
            def_section(WHOOP_GREEN, "Recovery", [
                ("Recovery Score",     "0–100%. Green ≥ 67%, Yellow 34–66%, Red ≤ 33%. Composite of HRV, RHR, SpO2, and skin temperature vs. your personal baseline."),
                ("HRV — RMSSD",        "Heart rate variability in milliseconds. Higher = better autonomic nervous system readiness. Trend matters more than absolute value; it is highly individual."),
                ("Resting Heart Rate", "Beats per minute measured during sleep. Lower generally signals better cardiovascular fitness and deeper recovery."),
                ("SpO2",               "Blood oxygen saturation %. Healthy range 95–100%. Drops during sleep can indicate breathing issues or sleep apnea."),
                ("Skin Temperature",   "Measured overnight relative to your baseline. Elevations often indicate illness, alcohol consumption, or physiological stress."),
            ]),
            def_section(WHOOP_BLUE, "Sleep", [
                ("Sleep Performance",  "How much sleep you got vs. how much WHOOP calculated you needed. 100% = you hit your exact target."),
                ("Sleep Efficiency",   "Time asleep ÷ time in bed. Above 85% is considered healthy. Low values can point to insomnia or frequent waking."),
                ("Sleep Consistency",  "Regularity of your sleep and wake times across days. High consistency supports circadian rhythm health."),
                ("REM",                "Rapid Eye Movement. Critical for memory consolidation, emotional regulation, and cognitive performance."),
                ("SWS — Deep Sleep",   "Slow Wave Sleep. The most physically restorative stage — growth hormone is released here and muscles repair."),
                ("Respiratory Rate",   "Breaths per minute during sleep. Elevated values can indicate illness, stress, or overtraining."),
            ]),
        ], style={"display": "flex", "flexWrap": "wrap", "gap": "16px", "marginBottom": "16px", "alignItems": "flex-start"}),

        html.Div([
            def_section(WHOOP_YELLOW, "Strain", [
                ("Day Strain",         "0–21 scale of total cardiovascular load across the full day based on time in each heart rate zone."),
                ("Workout Strain",     "Same 0–21 scale scoped to a single activity. Useful for comparing intensity across sessions."),
                ("Kilojoules",         "Total energy expended. 1 kcal ≈ 4.18 kJ. Useful for tracking caloric output trends."),
                ("Heart Rate Zones",   "Zone 0 (< 50% HRmax) through Zone 5 (> 90% HRmax). Higher zones contribute disproportionately more to strain."),
            ]),
            def_section(MUTED, "Scoring states & zones", [
                ("SCORED",             "Data was collected successfully — all metrics available."),
                ("PENDING_SCORE",      "Still processing. Check back in a few minutes."),
                ("UNSCORABLE",         "Not enough data collected (e.g. device removed) to generate a score."),
                ("Strain zones",       "1–10 Light  ·  10–14 Moderate  ·  14–18 Strenuous  ·  18–21 All Out"),
                ("Recovery zones",     "Green 67–100% = Push hard  ·  Yellow 34–66% = Caution  ·  Red 0–33% = Rest"),
            ]),
        ], style={"display": "flex", "flexWrap": "wrap", "gap": "16px", "alignItems": "flex-start"}),
    ])


# ── App ────────────────────────────────────────────────────────────────────────

def build_app():
    sleep, recovery, workouts, cycles = load_data()
    athlete = load_profile()

    app = Dash(__name__, title="WHOOP Dashboard",
               meta_tags=[{"name": "viewport",
                            "content": "width=device-width, initial-scale=1"}])

    app.layout = html.Div(
        style={"background": DARK, "minHeight": "100vh",
               "padding": "clamp(16px, 4vw, 40px)",
               "fontFamily": "Inter, system-ui, sans-serif", "boxSizing": "border-box"},
        children=[

            # ── Header ────────────────────────────────────────────────────────
            html.Div([
                html.Div([
                    html.Span("WHOOP", style={
                        "color": WHOOP_GREEN, "fontWeight": "800",
                        "fontSize": "26px", "letterSpacing": "-0.5px",
                    }),
                    html.Span(" Dashboard", style={
                        "color": TEXT, "fontWeight": "300",
                        "fontSize": "26px",
                    }),
                ]),
                html.Div([
                    html.Span("Athlete: ", style={"color": MUTED, "fontSize": "15px"}),
                    html.Span(athlete, style={
                        "color": TEXT, "fontWeight": "600", "fontSize": "15px",
                    }),
                ], style={"marginTop": "6px"}),
            ], style={"marginBottom": "28px"}),

            # ── Nav tabs ──────────────────────────────────────────────────────
            html.Div([
                html.Button("Dashboard",          id="tab-dashboard",    n_clicks=0),
                html.Button("Metric Definitions", id="tab-definitions",  n_clicks=0),
            ], id="tab-bar", style={"display": "flex", "gap": "4px", "marginBottom": "16px"}),

            # ── Date filter ───────────────────────────────────────────────────
            html.Div([
                html.Span("Period:", style={
                    "color": MUTED, "fontSize": "13px",
                    "alignSelf": "center", "marginRight": "8px",
                }),
                dcc.Dropdown(
                    id="date-filter",
                    options=[
                        {"label": "Last 7 days",  "value": 7},
                        {"label": "Last 30 days", "value": 30},
                        {"label": "Last 90 days", "value": 90},
                        {"label": "All time",     "value": 0},
                    ],
                    value=7,
                    clearable=False,
                    style={
                        "width": "160px",
                        "background": SURFACE,
                        "color": TEXT,
                        "border": f"1px solid {BORDER}",
                        "borderRadius": "8px",
                        "fontSize": "13px",
                    },
                ),
            ], id="filter-bar", style={
                "display": "flex", "alignItems": "center",
                "marginBottom": "16px",
            }),

            # ── Content area ──────────────────────────────────────────────────
            html.Div(id="tab-content"),
        ],
    )

    @app.callback(
        Output("tab-content",     "children"),
        Output("tab-dashboard",   "style"),
        Output("tab-definitions", "style"),
        Output("filter-bar",      "style"),
        Input("tab-dashboard",    "n_clicks"),
        Input("tab-definitions",  "n_clicks"),
        Input("date-filter",      "value"),
    )
    def switch_tab(n_dash, n_def, filter_days):
        active_style = {
            "background": WHOOP_GREEN, "color": "#000", "border": "none",
            "borderRadius": "8px", "padding": "8px 20px", "fontSize": "13px",
            "fontWeight": "700", "cursor": "pointer",
        }
        inactive_style = {
            "background": SURFACE, "color": MUTED, "border": f"1px solid {BORDER}",
            "borderRadius": "8px", "padding": "8px 20px", "fontSize": "13px",
            "fontWeight": "500", "cursor": "pointer",
        }
        filter_visible = {"display": "flex", "alignItems": "center", "marginBottom": "16px"}
        filter_hidden  = {"display": "none"}

        if (n_def or 0) > (n_dash or 0):
            return definitions_page(), inactive_style, active_style, filter_hidden

        days = int(filter_days) if filter_days else 0
        fs, fr, fw, fc = apply_date_filter(sleep, recovery, workouts, cycles, days or None)
        return dashboard_page(fs, fr, fw, fc), active_style, inactive_style, filter_visible

    return app


if __name__ == "__main__":
    import subprocess, sys
    subprocess.run(
        f"lsof -ti :{8050} | xargs kill -9 2>/dev/null; true",
        shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    app = build_app()
    print("Dashboard running → http://127.0.0.1:8050")
    app.run(debug=False)
