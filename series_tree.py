"""Árbol desplegable del inventario para el buscador de series."""

from __future__ import annotations

from collections import Counter
import hashlib
import re

import pandas as pd
import streamlit as st


LEVELS = (
    "Institución", "Área", "Subárea 1", "Subárea 2", "Subárea 3",
    "Grupo de hojas", "Hoja origen",
    "Grupo de series 1", "Grupo de series 2",
)
SHEET_LEVEL = LEVELS.index("Hoja origen")
FISCAL_SHEETS = {
    "SPN": "Sector Público Nacional", "APN": "Administración Pública Nacional",
    "OD": "Organismos descentralizados", "TN": "Tesoro Nacional",
    "RA": "Recursos afectados", "ISS": "Instituciones de la seguridad social",
    "EP_PAMI_FF": "Empresas públicas, PAMI y fondos fiduciarios",
    "Ex_CP": "Ex cajas provinciales",
    "AC_Dev_61": "Administración Central", "AN_Dev_61": "Administración Nacional",
    "CE_Dev_61": "Cuentas especiales", "EP_Dev_61": "Empresas públicas",
    "ISS_Dev_61": "Instituciones de la seguridad social",
    "OD_Dev_61": "Organismos descentralizados",
    "PROV_MCBA_Dev_61": "Provincias y CABA",
    "SPA_Dev_61": "Sector Público Argentino",
}
PAS_SHEETS = {
    "Estra_dia": "Total", "Estra_dia_bancos": "Bancos",
    "Estra_dia_bcos.priv": "Bancos privados", "Estra_dia_bcos.pub": "Bancos públicos",
    "Estra_dia_ext": "Residentes en el exterior", "Estra_dia_fin": "Servicios financieros",
    "Estra_dia_fis": "Personas físicas", "Estra_dia_jur": "Personas jurídicas",
    "Estra_dia_no_banc.": "Entidades no bancarias", "Estra_dia_pri": "Sector privado",
    "Estra_dia_pub": "Sector público", "Estra_dia_res": "Otras personas jurídicas",
    "Series_diarias": "Total", "Series_diarias_Bancos": "Bancos",
    "Series_diarias_bcos.privados": "Bancos privados",
    "Series_diarias_bcos.publicos": "Bancos públicos",
    "Series_diarias_no_bancarias": "Entidades no bancarias",
    "Totales_diarios": "Totales diarios", "UVA_UVI": "Plazos fijos UVA y UVI",
}


def _clean(value: object) -> str:
    if pd.isna(value):
        return ""
    text = " ".join(str(value).split()).strip()
    return "" if text.casefold() in {"nan", "none", "sin mayor detalle"} else text


def _sheet_label(source: str, sheet: str, dataset: str, ancestors: list[str]) -> str:
    if source == "bcra-pas":
        return PAS_SHEETS.get(sheet, sheet)
    if source == "datos.gob.ar" and sheet in FISCAL_SHEETS:
        return FISCAL_SHEETS[sheet]
    if source == "indec-cin":
        label = re.sub(r"^Cuadro\s+\d+\s*:\s*", "", dataset, flags=re.IGNORECASE)
    elif source == "indec-pib":
        label = dataset
        family = ancestors[SHEET_LEVEL - 1]
        if family and label.casefold().startswith(family.casefold()):
            label = label[len(family):].lstrip(" .,:") or dataset
    elif source == "indec-supermercados":
        label = re.sub(r"^Encuesta de supermercados\.\s*", "", dataset, flags=re.IGNORECASE)
        label = re.sub(r"\.\s*Enero\s+\d{4}.*$", "", label, flags=re.IGNORECASE)
    elif source == "datos.gob.ar" and re.match(r"^\d+(?:\.\d+)*(?:\s|$)", sheet):
        label = re.sub(r"^\d+(?:\.\d+)*\s*", "", sheet).strip(" .") or dataset
    else:
        return sheet
    label = _clean(label) or sheet
    return "" if label.casefold().strip(" .") in {part.casefold().strip(" .") for part in ancestors} else label


def series_path(row: pd.Series) -> tuple[str, ...]:
    """Omite niveles sin información y conserva el orden del inventario."""
    return _path_values((row.get(column) for column in LEVELS),
                        row.get("Código fuente"), row.get("Título dataset"))


def _path_values(values, source: object = None, dataset: object = None) -> tuple[str, ...]:
    parts = [_clean(value) for value in values]
    if not parts[0]:
        parts[0] = "Sin clasificar"
    parts[SHEET_LEVEL] = _sheet_label(_clean(source), parts[SHEET_LEVEL],
                                      _clean(dataset), parts[:SHEET_LEVEL]) if parts[SHEET_LEVEL] else ""
    return tuple(value for value in parts if value)


def _paths(df: pd.DataFrame) -> list[tuple[str, ...]]:
    columns = [df[column].array if column in df else [""] * len(df) for column in LEVELS]
    sources = df["Código fuente"].array if "Código fuente" in df else [""] * len(df)
    datasets = df["Título dataset"].array if "Título dataset" in df else [""] * len(df)
    return [_path_values(values, source, dataset)
            for *values, source, dataset in zip(*columns, sources, datasets)]


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


def _build_tree(paths: list[tuple[str, ...]]) -> tuple[dict, dict]:
    branches: dict[tuple[str, ...], dict[str, int]] = {}
    leaves: dict[tuple[str, ...], list[int]] = {}
    for position, path in enumerate(paths):
        for depth, label in enumerate(path):
            parent = path[:depth]
            children = branches.setdefault(parent, {})
            children[label] = children.get(label, 0) + 1
        leaves.setdefault(path, []).append(position)
    return branches, leaves


def _toggle_branch(path: tuple[str, ...]) -> None:
    opened = st.session_state.setdefault("series_tree_open", set())
    if path in opened:
        opened.remove(path)
    else:
        opened.add(path)


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
        if st.session_state["series_tree_sync_selection"] and key in st.session_state:
            st.session_state[key] = selected
        title = _clean(row.get("Nombre serie")) or series_id
        detail = " · ".join(value for value in (
            _clean(row.get("Frecuencia")), _clean(row.get("Unidad")),
            f"ID: {_clean(row.get('ID'))}",
        ) if value)
        checked = st.checkbox(f"{'　' * depth}{title}  ·  {detail}", value=selected, key=key)
        if checked != selected:
            if checked:
                st.session_state["selected_ids"].add(series_id)
            else:
                st.session_state["selected_ids"].discard(series_id)
            st.session_state["series_tree_selected_snapshot"] = frozenset(
                st.session_state["selected_ids"])
            st.rerun()


@st.fragment
def show(df: pd.DataFrame, cache_key: tuple | None = None) -> None:
    """Abre ramas en línea y marca las series mediante casillas."""
    if df.empty:
        st.info("No hay series para los filtros actuales.")
        return
    cached = st.session_state.get("series_tree_cache")
    if cached is not None and cached[0] == cache_key:
        branches, leaves = cached[1:]
    else:
        branches, leaves = _build_tree(_paths(df))
        if cache_key is not None:
            st.session_state["series_tree_cache"] = cache_key, branches, leaves

    opened = st.session_state.setdefault("series_tree_open", set())
    selected_snapshot = frozenset(st.session_state["selected_ids"])
    st.session_state["series_tree_sync_selection"] = (
        st.session_state.get("series_tree_selected_snapshot") != selected_snapshot)
    st.session_state["series_tree_selected_snapshot"] = selected_snapshot
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
