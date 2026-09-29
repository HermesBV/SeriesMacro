"""Mapa visual del inventario de series disponible en la aplicación."""

from __future__ import annotations

from collections import Counter
import math
import textwrap

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


LEVELS = ("Institución", "Área", "Subárea 1", "Subárea 2", "Subárea 3")
COLORS = (
    "#0B6E69", "#F05F30", "#3774AC", "#6E52A3", "#B95B78",
    "#BF8B2A", "#2D8A55", "#8A5A44", "#4D6F91", "#66757F",
)
NODE_SEP = "\x1f"


def _clean(value: object) -> str:
    if pd.isna(value):
        return ""
    result = " ".join(str(value).split()).strip()
    return "" if result.casefold() in {"nan", "none", "null"} else result


def topic_counts(df: pd.DataFrame) -> pd.DataFrame:
    """Una fila por tema, contada con las series visibles en la web."""
    topics = df["Tema"].map(_clean).replace("", "Sin clasificar")
    result = topics.value_counts().rename_axis("Tema").reset_index(name="Series")
    return result.sort_values(["Series", "Tema"], ascending=[False, True]).reset_index(drop=True)


def hierarchy_nodes(df: pd.DataFrame) -> pd.DataFrame:
    """Agrupa institución → área → subáreas y conserva series sin nivel inferior."""
    prefix_counts: Counter[tuple[str, ...]] = Counter()
    terminal_counts: Counter[tuple[str, ...]] = Counter()
    columns = [df[level].map(_clean) if level in df else pd.Series("", index=df.index) for level in LEVELS]
    for values in zip(*columns):
        path = []
        last_filled = max((i for i, value in enumerate(values) if value), default=-1)
        if last_filled < 0:
            values = ("Sin clasificar", "", "", "", "")
            last_filled = 0
        for level in range(last_filled + 1):
            path.append(values[level] or "Sin clasificar")
            prefix_counts[tuple(path)] += 1
        terminal_counts[tuple(path)] += 1

    records = []
    for path, count in sorted(prefix_counts.items(), key=lambda item: (len(item[0]), item[0])):
        records.append({"id": NODE_SEP.join(path), "parent": NODE_SEP.join(path[:-1]),
                        "label": path[-1], "count": count, "level": len(path) - 1})
    for path, count in terminal_counts.items():
        if len(path) < len(LEVELS):
            records.append({"id": NODE_SEP.join((*path, "Sin mayor detalle")),
                            "parent": NODE_SEP.join(path), "label": "Sin mayor detalle",
                            "count": count, "level": len(path)})
    return pd.DataFrame(records)


def _bubble_figure(counts: pd.DataFrame) -> go.Figure:
    count = len(counts)
    columns = 4 if count >= 8 else 3 if count >= 5 else min(count, 2)
    rows = max(1, math.ceil(count / columns))
    max_count = int(counts["Series"].max())
    fig = go.Figure()
    for number, item in counts.iterrows():
        x, y = number % columns, -(number // columns)
        diameter = 112 + 92 * math.sqrt(int(item["Series"]) / max_count)
        wrapped = "<br>".join(textwrap.wrap(str(item["Tema"]), width=17, break_long_words=False))
        fig.add_trace(go.Scatter(
            x=[x], y=[y], mode="markers+text",
            marker={"size": diameter, "color": COLORS[number % len(COLORS)],
                    "line": {"color": "#FFFFFF", "width": 3}, "opacity": 0.94},
            text=[f"<b>{wrapped}</b><br>{int(item['Series']):,} series"],
            textposition="middle center", textfont={"color": "#FFFFFF", "size": 12},
            customdata=[[str(item["Tema"]), int(item["Series"])]],
            hovertemplate="%{customdata[0]}<br>%{customdata[1]:,} series<extra></extra>",
            showlegend=False,
        ))
    fig.update_layout(
        height=max(420, rows * 245), margin={"l": 24, "r": 24, "t": 20, "b": 20},
        paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF", hoverlabel={"bgcolor": "#FFFFFF"},
        xaxis={"visible": False, "range": [-0.5, columns - 0.5], "fixedrange": True},
        yaxis={"visible": False, "range": [-rows + 0.5, 0.5], "fixedrange": True},
        dragmode=False,
    )
    return fig


def _treemap_figure(nodes: pd.DataFrame, total: int) -> go.Figure:
    top = nodes[nodes["level"].eq(0)]
    color_by_institution = {name: COLORS[i % len(COLORS)] for i, name in enumerate(top["label"])}
    def root_name(node_id: str) -> str:
        return node_id.split(NODE_SEP, 1)[0]
    ids = ["Todas las series", *nodes["id"].tolist()]
    parents = ["", *[parent or "Todas las series" for parent in nodes["parent"]]]
    labels = ["Todas las series", *nodes["label"].tolist()]
    values = [total, *nodes["count"].tolist()]
    colors = ["#E9F0EF", *[color_by_institution[root_name(value)] for value in nodes["id"]]]
    fig = go.Figure(go.Treemap(
        ids=ids, parents=parents, labels=labels, values=values,
        branchvalues="total", maxdepth=3,
        marker={"colors": colors, "line": {"color": "#FFFFFF", "width": 2}},
        texttemplate="%{label}<br>%{value:,} series",
        hovertemplate="%{label}<br>%{value:,} series<extra></extra>",
        pathbar={"visible": True},
        root={"color": "#E9F0EF"},
    ))
    fig.update_layout(height=690, margin={"l": 8, "r": 8, "t": 14, "b": 8},
                      paper_bgcolor="#FFFFFF", uniformtext={"minsize": 11, "mode": "hide"})
    return fig


def show(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("Todavía no hay series disponibles para mostrar en el mapa.")
        return
    choice = st.selectbox("Visualización", ("Tema", "Institución"), key="mapa_visualizacion")
    st.caption(f"{len(df):,} series disponibles".replace(",", "."))
    if choice == "Tema":
        counts = topic_counts(df)
        st.plotly_chart(_bubble_figure(counts), width="stretch", config={"displayModeBar": False})
    else:
        st.caption("Hacé clic en un bloque para avanzar por institución, área y subáreas.")
        nodes = hierarchy_nodes(df)
        st.plotly_chart(_treemap_figure(nodes, len(df)), width="stretch", config={"displayModeBar": False})
