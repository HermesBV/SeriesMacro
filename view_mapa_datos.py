"""Mapa visual del inventario de series disponible en la aplicación."""

from __future__ import annotations

from collections import Counter
from html import escape
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
    result["Sin clasificar al final"] = result["Tema"].str.casefold().eq("sin clasificar")
    return result.sort_values(
        ["Sin clasificar al final", "Series", "Tema"], ascending=[True, False, True]
    ).drop(columns="Sin clasificar al final").reset_index(drop=True)


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


def _branch_html(nodes: pd.DataFrame) -> str:
    """Árbol expandible; instituciones y áreas aparecen desde el inicio."""
    children: dict[str, list[dict]] = {}
    for node in nodes.to_dict("records"):
        children.setdefault(node["parent"], []).append(node)
    for siblings in children.values():
        siblings.sort(key=lambda node: (
            node["label"].casefold() in {"sin clasificar", "sin mayor detalle"},
            node["label"].casefold(),
        ))

    def render(node: dict) -> str:
        label = escape(str(node["label"]))
        count = f'{int(node["count"]):,}'.replace(",", ".")
        content = f'<span class="tree-name">{label}</span><span class="tree-count">{count} series</span>'
        descendants = children.get(node["id"], [])
        if not descendants:
            return f'<div class="tree-leaf">{content}</div>'
        opened = " open" if node["level"] == 0 else ""
        return (f'<details class="tree-branch"{opened}><summary>{content}</summary>'
                f'<div class="tree-children">{"".join(render(child) for child in descendants)}</div>'
                '</details>')

    roots = "".join(render(node) for node in children.get("", []))
    return """<style>
    .classification-tree {display: flex; flex-direction: column; gap: 12px; padding: 8px 0 24px;}
    .classification-tree summary, .classification-tree .tree-leaf {
        box-sizing: border-box; display: flex; align-items: center; justify-content: space-between;
        gap: 16px; width: min(100%, 420px); min-height: 46px; padding: 10px 14px;
        border: 1px solid #c9d9d7; border-radius: 9px; background: #f7fbfa;
        color: #173d3a; font-size: 14px;
    }
    .classification-tree summary {cursor: pointer; font-weight: 600;}
    .classification-tree summary:hover {background: #e7f3f0;}
    .classification-tree .tree-name {min-width: 0; overflow-wrap: anywhere;}
    .classification-tree .tree-count {flex: none; color: #52716c; font-size: 12px; white-space: nowrap;}
    .classification-tree .tree-children {
        display: flex; flex-direction: column; gap: 8px; margin: 8px 0 4px 22px;
        padding-left: 18px; border-left: 2px solid #c9d9d7;
    }
    .classification-tree > .tree-branch > summary {background: #dceeea; border-color: #9fc5bc;}
    .classification-tree .tree-leaf {background: #fff;}
    @media (max-width: 600px) {
        .classification-tree .tree-children {margin-left: 8px; padding-left: 10px;}
        .classification-tree summary, .classification-tree .tree-leaf {gap: 8px; padding: 8px;}
    }
    </style><div class="classification-tree">""" + roots + "</div>"


def show(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("Todavía no hay series disponibles para mostrar en el mapa.")
        return
    by_institution = st.toggle("Ver por institución", key="mapa_por_institucion",
                               help="Desactivado: Tema. Activado: Institución.")
    st.caption(f"{len(df):,} series disponibles".replace(",", "."))
    if not by_institution:
        counts = topic_counts(df)
        st.plotly_chart(_bubble_figure(counts), width="stretch", config={"displayModeBar": False})
    else:
        st.caption("Instituciones y áreas visibles. Hacé clic en un área para desplegar sus subáreas.")
        nodes = hierarchy_nodes(df)
        st.html(_branch_html(nodes))
