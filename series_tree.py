"""Navegación progresiva del inventario para el buscador de series."""

from __future__ import annotations

from collections import Counter
import hashlib

import pandas as pd
import streamlit as st


LEVELS = (
    "Institución", "Área", "Subárea 1", "Subárea 2", "Subárea 3",
    "Archivo origen", "Grupo de hojas", "Hoja origen",
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


def show(df: pd.DataFrame) -> None:
    """Presenta un nivel por vez y permite seleccionar las series al final."""
    if df.empty:
        st.info("No hay series para los filtros actuales.")
        return
    prefix = tuple(st.session_state.get("series_tree_path", ()))
    paths = _paths(df)
    if not any(path[:len(prefix)] == prefix for path in paths):
        prefix = ()
        st.session_state["series_tree_path"] = prefix
    st.caption(" / ".join(prefix) if prefix else "Todas las instituciones")
    if prefix and st.button("← Volver", key="series_tree_back"):
        st.session_state["series_tree_path"] = prefix[:-1]
        st.rerun()

    children = _next_groups(paths, prefix)
    if children:
        for label, count in children:
            path = prefix + (label,)
            amount = f"{count:,}".replace(",", ".")
            if st.button(f"{label}  ·  {amount} series  ›", key=f"tree_{_key(repr(path))}",
                         width="stretch"):
                st.session_state["series_tree_path"] = path
                st.rerun()

    rows = df[[path == prefix for path in paths]].sort_values("Nombre serie", kind="stable")
    if rows.empty:
        if not children:
            st.info("No hay series en este grupo.")
        return
    page_size = 60
    pages = (len(rows) + page_size - 1) // page_size
    page = st.number_input("Página", min_value=1, max_value=pages, value=1,
                           key=f"tree_page_{_key(repr(prefix))}") if pages > 1 else 1
    for _, row in rows.iloc[(page - 1) * page_size:page * page_size].iterrows():
        series_id = str(row["_Clave"])
        selected = series_id in st.session_state["selected_ids"]
        title = _clean(row.get("Nombre serie")) or series_id
        detail = " · ".join(value for value in (
            _clean(row.get("Frecuencia")), _clean(row.get("Unidad")),
            f"ID: {_clean(row.get('ID'))}",
        ) if value)
        if st.button(f"{'☑' if selected else '□'}  {title}  ·  {detail}",
                     key=f"series_{_key(series_id)}", width="stretch"):
            if selected:
                st.session_state["selected_ids"].remove(series_id)
            else:
                st.session_state["selected_ids"].add(series_id)
            st.rerun()
