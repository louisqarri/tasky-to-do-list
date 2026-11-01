import plotly.express as px

# 👇 copy these from your style.css so the charts match the page
ACCENT = "#6366f1"    # your main button/accent color
TEXT = "#334155"      # your normal text color
MUTED = "#e2e8f0"     # a light grey from your page

FONT = dict(family="Inter, system-ui, sans-serif", size=13, color=TEXT)


def clean_layout(fig, height):
    fig.update_layout(
        height=height,
        margin=dict(t=10, b=10, l=10, r=10),
        paper_bgcolor="rgba(0,0,0,0)",   # transparent outside
        plot_bgcolor="rgba(0,0,0,0)",    # transparent inside
        font=FONT,
        showlegend=False,
    )

def status_chart(stats):
    fig = px.pie(
        names=["To Do", "In Progress", "Done"],
        values=[stats["status_todo"], stats["status_progress"], stats["status_done"]],
        hole=0.6,
        color_discrete_sequence=[MUTED, "#f59e0b", ACCENT],
    )
    fig.update_traces(textinfo="label+value", textposition="outside")
    clean_layout(fig, 220)
    return fig.to_html(full_html=False, include_plotlyjs="cdn",
                       config={"displayModeBar": False})


def user_chart(team):
    members = [m for m in team]# if not m["user"].is_manager]
    names = [m["user"].name for m in members]
    values = [m["stats"]["completion"] for m in members]

    fig = px.bar(x=values, y=names, orientation="h", range_x=[0, 100])
    fig.update_traces(
        marker_color=ACCENT,
        text=[f"{v}%" for v in values],
        textposition="outside",
        width=0.5,   # thinner bars
    )
    fig.update_xaxes(visible=False)   # hide the 0–100 axis
    fig.update_yaxes(title="", showgrid=False, ticks="")
    clean_layout(fig, 220)
    return fig.to_html(full_html=False, include_plotlyjs=False,
                       config={"displayModeBar": False})