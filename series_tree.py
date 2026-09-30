"""Árbol desplegable del inventario para el buscador de series."""

from __future__ import annotations

from collections import Counter
import hashlib

import pandas as pd
import streamlit as st


LEVELS = (
    "Institución", "Área", "Subárea 1", "Subárea 2", "Subárea 3",
    "Grupo de hojas", "Hoja origen",
    "Grupo de series 1", "Grupo de series 2",
)


def _clean(value: object) -> str:
    if pd.isna(value):
        return ""
    text = " ".join(str(value).split()).strip()
    return "" if text.casefold() in {"nan", "none", "sin mayor detalle"} else text


def series_path(row: pd.Series) -> tuple[str, ...]:
    """Omite niveles sin información y conserva el orden del inventario."""
    return _path_values(row.get(column) for column in LEVELS)


def _path_values(values) -> tuple[str, ...]:
    parts = [_clean(value) for value in values]
    if not parts[0]:
        parts[0] = "Sin clasificar"
    return tuple(value for value in parts if value)


def _paths(df: pd.DataFrame) -> list[tuple[str, ...]]:
    columns = [df[column].array if column in df else [""] * len(df) for column in LEVELS]
    return [_path_values(values) for values in zip(*columns)]


def next_groups(df: pd.DataFrame, prefix: tuple[str, ...]) -> list[tuple[str, int]]:
    """Cuenta sólo hijos directos del nivel abierto."""
    return _next_groups(_paths(df), prefix)


def _next_groups(paths: list[tuple[str, ...]], prefix: tuple[str, ...]) -> list[tuple[str, int]]:
    counts: Counter[str] = Counter()
    for path in paths:
        if path[:len(prefix)] == prefix and len(path) > len(prefix):
            counts[path[len(prefix)]] += 1
    return sorted(counts.items(), key=lambda item: (-item[1], item[0].casefold()))


def _key(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]


def _toggle_branch(path: tuple[str, ...]) -> None:
    opened = st.session_state.setdefault("series_tree_open", set())
    if path in opened:
        opened.remove(path)
    else:
        opened.add(path)


def _select_series(series_id: str, key: str) -> None:
    selected = st.session_state["selected_ids"]
    if st.session_state[key]:
        selected.add(series_id)
    else:
        selected.discard(series_id)


def _render_rows(rows: pd.DataFrame, path: tuple[str, ...], depth: int) -> None:
    rows = rows.sort_values("Nombre serie", kind="stable")
    page_size = 60
    pages = (len(rows) + page_size - 1) // page_size
    page = (st.number_input("Página", min_value=1, max_value=pages, value=1,
                            key=f"tree_page_{_key(repr(path))}") if pages > 1 else 1)
    for _, row in rows.iloc[(page - 1) * page_size:page * page_size].iterrows():
        series_id = str(row["_Clave"])
        key = f"series_{_key(series_id)}"
        selected = series_id in st.session_state["selected_ids"]
        if key in st.session_state and st.session_state[key] != selected:
            st.session_state[key] = selected
        title = _clean(row.get("Nombre serie")) or series_id
        detail = " · ".join(value for value in (
            _clean(row.get("Frecuencia")), _clean(row.get("Unidad")),
            f"ID: {_clean(row.get('ID'))}",
        ) if value)
        st.checkbox(f"{'　' * depth}{title}  ·  {detail}", value=selected,
                    key=key, on_change=_select_series, args=(series_id, key))


def show(df: pd.DataFrame) -> None:
    """Abre ramas en línea y marca las series mediante casillas."""
    if df.empty:
        st.info("No hay series para los filtros actuales.")
        return
    paths = _paths(df)
    branches: dict[tuple[str, ...], dict[str, int]] = {}
    leaves: dict[tuple[str, ...], list[int]] = {}
    for position, path in enumerate(paths):
        for depth, label in enumerate(path):
            parent = path[:depth]
            children = branches.setdefault(parent, {})
            children[label] = children.get(label, 0) + 1
        leaves.setdefault(path, []).append(position)

    opened = st.session_state.setdefault("series_tree_open", set())
    st.html("""<style>
    .st-key-series_tree div.stButton > button {
        background: transparent !important; color: #23352f !important;
        border: 0 !important; text-align: left !important;
        justify-content: flex-start !important;
    }
    .st-key-series_tree div.stButton > button:hover {
        background: #e6f2ed !important; color: #184e3a !important;
    }
    .st-key-series_tree div.stButton > button p { color: inherit !important; }
    </style>""")

    def render(path: tuple[str, ...]) -> None:
        children = branches.get(path, {})
        for label, count in sorted(children.items(), key=lambda item: (-item[1], item[0].casefold())):
            child = path + (label,)
            arrow = "▾" if child in opened else "▸"
            amount = f"{count:,}".replace(",", ".")
            st.button(f"{'　' * len(path)}{arrow}  {label}  ({amount})",
                      key=f"tree_{_key(repr(child))}", type="tertiary",
                      on_click=_toggle_branch, args=(child,))
            if child in opened:
                render(child)
        positions = leaves.get(path, [])
        if positions:
            _render_rows(df.iloc[positions], path, len(path))

    with st.container(key="series_tree"):
        render(())
