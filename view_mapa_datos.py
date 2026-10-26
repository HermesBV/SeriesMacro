"""Mapa visual del inventario de series disponible en la aplicación."""

from __future__ import annotations

from collections import Counter
from html import escape
import math

import pandas as pd
import streamlit as st


LEVELS = ("Institución", "Área", "Subárea 1", "Subárea 2", "Subárea 3")
COLORS = (
    "#0B6E69", "#C2410C", "#3774AC", "#6E52A3", "#A3445F",
    "#9A6B12", "#237347", "#8A5A44", "#4D6F91", "#66757F",
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
    """Agrupa institución → área → subáreas hasta el último nivel real."""
    prefix_counts: Counter[tuple[str, ...]] = Counter()
    columns = [df[level].map(_clean) if level in df else pd.Series("", index=df.index) for level in LEVELS]
    for values in zip(*columns):
        # Estos textos son relleno del inventario, no niveles navegables.
        values = tuple(
            "" if level and value.casefold() in {"sin mayor detalle", "sin clasificar"} else value
            for level, value in enumerate(values)
        )
        path = []
        last_filled = max((i for i, value in enumerate(values) if value), default=-1)
        if last_filled < 0:
            values = ("Sin clasificar", "", "", "", "")
            last_filled = 0
        for level in range(last_filled + 1):
            path.append(values[level] or "Sin clasificar")
            prefix_counts[tuple(path)] += 1

    records = []
    for path, count in sorted(prefix_counts.items(), key=lambda item: (len(item[0]), item[0])):
        records.append({"id": NODE_SEP.join(path), "parent": NODE_SEP.join(path[:-1]),
                        "label": path[-1], "count": count, "level": len(path) - 1})
    return pd.DataFrame(records)


def _bubble_html(counts: pd.DataFrame) -> str:
    """Burbujas por tema en una grilla que se adapta al ancho de la pantalla.

    El diámetro es proporcional a la raíz de la cantidad de series y se expresa como
    fracción de la celda, de modo que las burbujas nunca se pisan en pantallas angostas.
    """
    max_count = max(int(counts["Series"].max()), 1)
    bubbles = []
    for number, item in counts.reset_index(drop=True).iterrows():
        series = int(item["Series"])
        scale = 0.58 + 0.42 * math.sqrt(series / max_count)
        color = "#5F6B73" if str(item["Tema"]).casefold() == "sin clasificar" else COLORS[number % len(COLORS)]
        theme = escape(str(item["Tema"]))
        amount = f"{series:,}".replace(",", ".")
        bubbles.append(
            f'<div class="topic-cell"><div class="topic-bubble" style="--scale:{scale:.3f};--color:{color}" '
            f'title="{theme}: {amount} series"><span class="topic-name">{theme}</span>'
            f'<span class="topic-count">{amount} series</span></div></div>'
        )
    return """<style>
    .topic-bubbles {
        display: flex; flex-wrap: wrap; justify-content: center;
        gap: 12px; padding: 8px 0 24px; max-width: 1040px; margin: 0 auto;
    }
    .topic-cell {
        display: flex; align-items: center; justify-content: center; aspect-ratio: 1;
        flex: 0 0 calc((100% - 36px) / 4);
    }
    .topic-bubble {
        width: calc(var(--scale) * 100%); aspect-ratio: 1; border-radius: 50%;
        background: var(--color); color: #fff; box-shadow: 0 0 0 3px #fff, 0 2px 8px rgba(0,0,0,0.12);
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        text-align: center; padding: 8%; box-sizing: border-box; line-height: 1.2;
    }
    .topic-name {font-weight: 700; font-size: clamp(13px, 1.2vw, 16px); overflow-wrap: anywhere;}
    .topic-count {font-size: clamp(12px, 1.05vw, 15px); font-weight: 500; margin-top: 4px;}
    @media (max-width: 900px) {
        .topic-cell {flex-basis: calc((100% - 24px) / 3);}
        .topic-name {font-size: 13px;} .topic-count {font-size: 12px;}
    }
    @media (max-width: 560px) {
        .topic-bubbles {gap: 8px;} .topic-cell {flex-basis: calc((100% - 8px) / 2);}
        .topic-name {font-size: 12px;} .topic-count {font-size: 12px;}
    }
    </style><div class="topic-bubbles">""" + "".join(bubbles) + "</div>"


def _branch_html(nodes: pd.DataFrame) -> str:
    """Árbol expandible; instituciones y áreas aparecen desde el inicio."""
    children: dict[str, list[dict]] = {}
    for node in nodes.to_dict("records"):
        children.setdefault(node["parent"], []).append(node)
    for siblings in children.values():
        siblings.sort(key=lambda node: (
            node["label"].casefold() == "sin clasificar",
            -int(node["count"]),
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
        content += '<span class="tree-expand" aria-hidden="true">+</span>'
        root_class = " tree-root" if node["level"] == 0 else ""
        return (f'<details class="tree-branch{root_class}"{opened}><summary>{content}</summary>'
                f'<div class="tree-children">{"".join(render(child) for child in descendants)}</div>'
                '</details>')

    institutions = sorted(children.get("", []), key=lambda node: (
        node["label"].casefold() == "sin clasificar", -int(node["count"]), node["label"].casefold()
    ))
    roots = "".join(
        f'<div class="tree-institution" style="--tree-accent:{COLORS[i % 4]}">{render(node)}</div>'
        for i, node in enumerate(institutions)
    )
    return """<style>
    .classification-tree {
        display: grid; grid-template-columns: repeat(4, minmax(0, 1fr));
        align-items: start; gap: 16px; padding: 8px 0 24px;
    }
    .classification-tree .tree-institution {min-width: 0;}
    .classification-tree summary, .classification-tree .tree-leaf {
        box-sizing: border-box; display: flex; align-items: center; justify-content: space-between;
        gap: 10px; width: 100%; min-height: 46px; padding: 10px 12px;
        border: 1px solid #c9d9d7; border-radius: 9px; background: #f7fbfa;
        color: #173d3a; font-size: 14px;
    }
    .classification-tree summary {cursor: pointer; font-weight: 600;}
    .classification-tree summary:hover {background: #e7f3f0;}
    .classification-tree summary::marker {content: "";}
    .classification-tree summary::-webkit-details-marker {display: none;}
    .classification-tree .tree-name {min-width: 0; overflow-wrap: anywhere;}
    .classification-tree .tree-count {flex: none; color: #52716c; font-size: 12px; white-space: nowrap;}
    .classification-tree .tree-expand {flex: none; margin-left: auto; font-size: 20px; line-height: 1;}
    .classification-tree .tree-children {
        display: flex; flex-direction: column; gap: 8px; margin: 8px 0 4px 8px;
        padding-left: 10px; border-left: 2px solid var(--tree-accent);
    }
    .classification-tree .tree-root > summary {
        background: var(--tree-accent); border-color: var(--tree-accent); color: #fff;
    }
    .classification-tree .tree-root > summary .tree-count {color: #fff;}
    .classification-tree .tree-root > summary:hover {filter: brightness(1.08);}
    .classification-tree .tree-children summary {border-left: 4px solid var(--tree-accent);}
    .classification-tree .tree-leaf {background: #fff;}
    @media (max-width: 1100px) {
        .classification-tree {grid-template-columns: repeat(2, minmax(0, 1fr));}
    }
    @media (max-width: 650px) {
        .classification-tree {grid-template-columns: minmax(0, 1fr);}
        .classification-tree .tree-children {margin-left: 8px; padding-left: 10px;}
        .classification-tree summary, .classification-tree .tree-leaf {gap: 8px; padding: 8px;}
    }
    </style><div class="classification-tree">""" + roots + "</div>"


def show(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("Todavía no hay series disponibles para mostrar en el mapa.")
        return
    by_institution = st.toggle("Ver por Tema/Institución", key="mapa_por_institucion",
                               help="Desactivado: Tema. Activado: Institución.")
    st.caption(f"{len(df):,} series disponibles".replace(",", "."))
    if not by_institution:
        counts = topic_counts(df)
        st.html(_bubble_html(counts))
    else:
        nodes = hierarchy_nodes(df)
        st.html(_branch_html(nodes))
