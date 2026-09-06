# VIEW_MACRO_RESET_V15: botones macro en una linea con fuente pareja y mas legible. Solo view_macro.
import re
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import utils

EJE_IZQUIERDO = "Izquierdo"
EJE_DERECHO = "Derecho"
TIPOS_GRAFICO = ["Línea", "Área", "Puntos"]
HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _normalizar_tipo(tipo):
    tipo = str(tipo).strip()
    mapa = {
        "Linea": "Línea",
        "Línea": "Línea",
        "Area": "Área",
        "Área": "Área",
        "Puntos": "Puntos",
    }
    return mapa.get(tipo, "Línea")


def _validar_color_hex(valor, fallback):
    valor = str(valor).strip()
    return valor if HEX_COLOR_RE.match(valor) else fallback


def _preparar_serie(sheet_df, var_name, var_id):
    """Devuelve datos limpios: fecha unica, valor numerico y orden cronologico."""
    if sheet_df is None or sheet_df.empty:
        return pd.DataFrame(columns=[var_id])

    df = sheet_df.copy()
    if "Fecha" not in df.columns and not df.empty:
        df.rename(columns={df.columns[0]: "Fecha"}, inplace=True)

    if "Fecha" not in df.columns or var_name not in df.columns:
        return pd.DataFrame(columns=[var_id])

    serie = df[["Fecha", var_name]].copy()
    serie["Fecha"] = pd.to_datetime(serie["Fecha"], errors="coerce")
    serie[var_name] = pd.to_numeric(serie[var_name], errors="coerce")
    serie = serie.dropna(subset=["Fecha", var_name])

    if serie.empty:
        return pd.DataFrame(columns=[var_id])

    # Evita duplicaciones por horas distintas dentro del mismo dia.
    serie["Fecha"] = serie["Fecha"].dt.normalize()

    # Si hay fechas repetidas, deja un solo valor por fecha.
    # Esto evita que una misma barra se dibuje varias veces.
    serie = (
        serie.sort_values("Fecha")
        .drop_duplicates(subset="Fecha", keep="last")
        .set_index("Fecha")
        .sort_index()
    )
    serie.columns = [var_id]
    return serie


def _inferir_ancho_barras(fechas):
    fechas = pd.Series(pd.to_datetime(fechas)).dropna().drop_duplicates().sort_values()
    if len(fechas) >= 2:
        diffs = fechas.diff().dropna()
        diffs = diffs[diffs > pd.Timedelta(0)]
        if not diffs.empty:
            return diffs.median() * 0.72
    return pd.Timedelta(days=22)


def _agregar_barras_con_shapes(fig, serie, var_id, var_name, color, use_secondary, bar_index, bar_count):
    """Dibuja barras como rectangulos de layout para impedir apilados visuales inesperados."""
    clean = serie[[var_id]].dropna().copy()
    if clean.empty:
        return []

    base_width = _inferir_ancho_barras(clean.index)
    bar_count = max(1, int(bar_count))
    bar_index = max(0, int(bar_index))

    # Si hay varias series de barras en el mismo eje, las separa dentro del periodo.
    slot_width = base_width / bar_count
    visible_width = slot_width * 0.78
    offset = (bar_index - (bar_count - 1) / 2) * slot_width
    yref = "y2" if use_secondary else "y"

    for fecha, valor in clean[var_id].items():
        centro = fecha + offset
        x0 = centro - visible_width / 2
        x1 = centro + visible_width / 2
        y0 = 0
        y1 = float(valor)
        fig.add_shape(
            type="rect",
            xref="x",
            yref=yref,
            x0=x0,
            x1=x1,
            y0=y0,
            y1=y1,
            fillcolor=color,
            opacity=0.95,
            line=dict(color=color, width=0.5),
            layer="below",
        )

    # Trazo invisible solo para que el hover muestre el valor de la barra.
    fig.add_trace(
        go.Scatter(
            x=clean.index,
            y=clean[var_id],
            name=var_name,
            mode="markers",
            marker=dict(color=color, size=8, opacity=0),
            hovertemplate="%{x|%d/%m/%Y}<br>%{y:,.2f}<extra></extra>",
            showlegend=False,
        ),
        secondary_y=use_secondary,
    )
    return clean[var_id].tolist()


def _rango_con_cero(valores):
    vals = pd.Series(valores, dtype="float64").dropna()
    if vals.empty:
        return None
    minimo = min(0, vals.min())
    maximo = max(0, vals.max())
    if minimo == maximo:
        pad = abs(maximo) * 0.1 if maximo else 1
    else:
        pad = (maximo - minimo) * 0.08
    return [minimo - pad, maximo + pad]


def _render_controles_series(series_metadata):
    """Grilla horizontal de ancho completo para controlar las series ya seleccionadas."""
    if not series_metadata:
        return

    st.markdown(
        """
        <style>
        .series-grid-header {
            margin-top: 0.75rem;
            font-size: 0.76rem;
            font-weight: 700;
            color: #444444;
            padding-bottom: 0.12rem;
            border-bottom: 1px solid #E6E6E6;
            margin-bottom: 0.12rem;
        }
        .series-grid-name {
            font-size: 0.98rem;
            font-weight: 600;
            color: #222222;
            line-height: 1.22;
            padding-top: 0.30rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .series-grid-row-spacer {
            height: 0.16rem;
        }
        /* Controles de la grilla: mas chicos que el nombre de la serie. */
        div[data-baseweb="select"] span,
        div[data-baseweb="select"] div {
            font-size: 0.76rem !important;
        }
        div[data-baseweb="select"] > div {
            min-height: 31px !important;
        }
        div[data-testid="stCheckbox"] label,
        div[data-testid="stCheckbox"] p {
            font-size: 0.76rem !important;
        }
        /* Color picker compacto para que no domine la fila. */
        div[data-testid="stColorPicker"] {
            padding-top: 0px !important;
            transform: scale(0.84);
            transform-origin: left center;
        }
        div[data-testid="stColorPicker"] button {
            min-height: 26px !important;
            height: 26px !important;
            width: 26px !important;
            padding: 0px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Encabezados de la grilla: una columna por tipo de control.
    h_serie, h_tipo, h_eje, h_color, h_visible = st.columns([6.0, 1.15, 1.15, 0.75, 0.85], gap="small")
    with h_serie:
        st.markdown('<div class="series-grid-header">Serie</div>', unsafe_allow_html=True)
    with h_tipo:
        st.markdown('<div class="series-grid-header">Tipo</div>', unsafe_allow_html=True)
    with h_eje:
        st.markdown('<div class="series-grid-header">Eje</div>', unsafe_allow_html=True)
    with h_color:
        st.markdown('<div class="series-grid-header">Color</div>', unsafe_allow_html=True)
    with h_visible:
        st.markdown('<div class="series-grid-header">Visible</div>', unsafe_allow_html=True)

    changed = False

    for item in series_metadata:
        var_id = str(item["id"])
        serie_txt = str(item["name"])
        tipo_actual = _normalizar_tipo(item["type"])
        eje_actual = item["axis"] if item["axis"] in [EJE_IZQUIERDO, EJE_DERECHO] else EJE_IZQUIERDO
        color_actual = _validar_color_hex(item["color"], utils.PALETA_COLORES[0])
        visible_actual = bool(item["visible"])

        c_serie, c_tipo, c_eje, c_color, c_visible = st.columns([6.0, 1.15, 1.15, 0.75, 0.85], gap="small")

        with c_serie:
            st.markdown(f'<div class="series-grid-name" title="{serie_txt}">{serie_txt}</div>', unsafe_allow_html=True)

        with c_tipo:
            try:
                tipo_index = TIPOS_GRAFICO.index(tipo_actual)
            except ValueError:
                tipo_index = 0
            nuevo_tipo = st.selectbox(
                "Tipo",
                TIPOS_GRAFICO,
                index=tipo_index,
                key=f"series_grid_tipo_v13_{var_id}",
                label_visibility="collapsed",
            )

        with c_eje:
            eje_opciones = [EJE_IZQUIERDO, EJE_DERECHO]
            eje_index = eje_opciones.index(eje_actual) if eje_actual in eje_opciones else 0
            nuevo_eje = st.selectbox(
                "Eje",
                eje_opciones,
                index=eje_index,
                key=f"series_grid_eje_v13_{var_id}",
                label_visibility="collapsed",
            )

        with c_color:
            nuevo_color = st.color_picker(
                "Color",
                value=color_actual,
                key=f"series_grid_color_v13_{var_id}",
                label_visibility="collapsed",
            )
            nuevo_color = _validar_color_hex(nuevo_color, color_actual)

        with c_visible:
            nuevo_visible = st.checkbox(
                "Visible",
                value=visible_actual,
                key=f"series_grid_visible_v13_{var_id}",
                label_visibility="collapsed",
            )

        st.markdown('<div class="series-grid-row-spacer"></div>', unsafe_allow_html=True)

        if nuevo_tipo != tipo_actual:
            st.session_state["chart_type_map"][var_id] = nuevo_tipo
            changed = True
        if nuevo_eje != eje_actual:
            st.session_state["axes_config"][var_id] = nuevo_eje
            changed = True
        if nuevo_color != color_actual:
            st.session_state["color_map"][var_id] = nuevo_color
            changed = True
        if nuevo_visible != visible_actual:
            st.session_state["visibility_map"][var_id] = nuevo_visible
            changed = True

    # Aire entre la grilla y los botones de accion/descarga.
    st.markdown('<div style="height: 1.1rem;"></div>', unsafe_allow_html=True)

    if changed:
        st.rerun()

def _render_botones_descarga(selected_rows_global, all_data_sheets):
    st.markdown(
        """
        <style>
        /* Botones de accion/descarga de Macro: texto en una sola linea, fuente pareja y legible. */
        div[data-testid="stDownloadButton"] button,
        div[data-testid="stButton"] button {
            padding-left: 0.38rem !important;
            padding-right: 0.38rem !important;
            min-height: 2.35rem !important;
            white-space: nowrap !important;
        }
        div[data-testid="stDownloadButton"] button p,
        div[data-testid="stDownloadButton"] button span,
        div[data-testid="stDownloadButton"] button div,
        div[data-testid="stButton"] button p,
        div[data-testid="stButton"] button span,
        div[data-testid="stButton"] button div {
            font-size: 0.82rem !important;
            line-height: 1.08 !important;
            white-space: nowrap !important;
            overflow: visible !important;
            text-overflow: clip !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    excel_filtered = utils.convert_df_to_excel_filtered(selected_rows_global, all_data_sheets)
    excel_full = utils.get_full_excel_bytes()

    b_col1, b_void, b_col3, b_col4 = st.columns([1.9, 2.7, 2.7, 2.7], gap="small")

    with b_col1:
        if st.button("Limpiar búsqueda", width="stretch"):
            st.session_state["selected_ids"] = set()
            st.session_state["axes_config"] = {}
            st.session_state["visibility_map"] = {}
            st.session_state["color_map"] = {}
            st.session_state["chart_type_map"] = {}
            for k in ["s_text", "s_tema", "s_freq"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()

    with b_col3:
        st.download_button(
            label="Descargar Datos (Filtrados)",
            data=excel_filtered,
            file_name="series_seleccion.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )
    with b_col4:
        st.download_button(
            label="Descargar Base (Completa)",
            data=excel_full,
            file_name="BD_completa.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )


def _render_buscador(df_index):
    """Buscador inferior y sincronizacion de seleccion."""
    st.markdown("### Buscador General")
    col1, col3, col4 = st.columns([2, 1, 1])

    with col1:
        search_text = st.text_input("Buscar", placeholder="ej. PIB, Argentina...", key="s_text")
    with col3:
        temas = ["Todos"] + sorted(list(df_index["Tema"].unique()))
        tema_sel = st.selectbox("Filtrar por Tema", temas, key="s_tema")
    with col4:
        freqs = ["Todas"] + sorted(list(df_index["Frecuencia"].unique()))
        freq_sel = st.selectbox("Filtrar por Frecuencia", freqs, key="s_freq")

    df_filtered_view = utils.filter_data(df_index, search_text, tema_sel, freq_sel)
    st.caption(
        f"Cantidad de series: {len(df_filtered_view):,} de {len(df_index):,}"
        .replace(",", ".")
    )
    df_filtered_view["Seleccionar"] = df_filtered_view["ID"].isin(st.session_state["selected_ids"])
    df_filtered_view["Fuente_Label"] = df_filtered_view["Fuente"].apply(
        lambda x: "MECON" if str(x).startswith("https://www.economia.gob.ar") else x
    )

    stable_key = f"editor_v2_{search_text}_{tema_sel}_{freq_sel}"

    edited_df = st.data_editor(
        df_filtered_view,
        column_config={
            "Seleccionar": st.column_config.CheckboxColumn("Seleccionar", default=False),
            "Nombre serie": st.column_config.TextColumn("Título"),
            "Descripción": st.column_config.TextColumn("Detalle"),
        },
        column_order=[
            "Seleccionar", "Nombre serie", "Descripción", "Unidades",
            "Valoración", "Tema", "Frecuencia",
        ],
        disabled=[
            "Nombre serie", "Descripción", "Unidades", "Valoración",
            "Tema", "Frecuencia", "ID",
        ],
        hide_index=True,
        width="stretch",
        height=300,
        key=stable_key,
    )

    new_selection = set(edited_df[edited_df["Seleccionar"]]["ID"])
    old_selection_in_view = set(df_filtered_view[df_filtered_view["Seleccionar"]]["ID"])

    added_ids = new_selection - old_selection_in_view
    removed_ids = old_selection_in_view - new_selection

    if added_ids or removed_ids:
        st.session_state["selected_ids"].update(added_ids)
        st.session_state["selected_ids"].difference_update(removed_ids)
        st.rerun()


def _construir_items_series(selected_rows_global, all_data_sheets):
    items = []

    for idx, row in selected_rows_global.iterrows():
        var_id = str(row["ID"])

        if var_id not in st.session_state["axes_config"]:
            st.session_state["axes_config"][var_id] = EJE_IZQUIERDO
        if var_id not in st.session_state["visibility_map"]:
            st.session_state["visibility_map"][var_id] = True
        if var_id not in st.session_state["chart_type_map"]:
            st.session_state["chart_type_map"][var_id] = "Línea"

        default_color = utils.PALETA_COLORES[idx % len(utils.PALETA_COLORES)]
        color_final = st.session_state["color_map"].get(var_id, default_color)
        color_final = _validar_color_hex(color_final, default_color)

        eje_pref = st.session_state["axes_config"][var_id]
        is_visible = st.session_state["visibility_map"][var_id]
        chart_type = _normalizar_tipo(st.session_state["chart_type_map"][var_id])

        tab_name = row["Pestaña"]
        var_name = row["Nombre serie"]
        column_name = row["Columna BD"]
        if tab_name not in all_data_sheets:
            continue

        serie = _preparar_serie(all_data_sheets[tab_name], column_name, var_id)
        if serie.empty:
            continue

        items.append(
            {
                "id": var_id,
                "name": var_name,
                "serie": serie,
                "color": color_final,
                "axis": eje_pref,
                "visible": is_visible,
                "type": chart_type,
            }
        )

    return items


def _render_grafico(items):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    plot_data_full = pd.DataFrame()

    for item in items:
        var_id = item["id"]
        var_name = item["name"]
        serie = item["serie"]
        color = item["color"]
        use_secondary = item["axis"] == EJE_DERECHO
        chart_type = item["type"]

        plot_data_full = serie if plot_data_full.empty else plot_data_full.join(serie, how="outer")

        if not item["visible"]:
            continue

        if chart_type == "Área":
            fig.add_trace(
                go.Scatter(
                    x=serie.index,
                    y=serie[var_id],
                    name=var_name,
                    fill="tozeroy",
                    mode="lines",
                    connectgaps=True,
                    line=dict(color=color, width=2),
                    hovertemplate="%{x|%d/%m/%Y}<br>%{y:,.2f}<extra></extra>",
                ),
                secondary_y=use_secondary,
            )
        elif chart_type == "Puntos":
            fig.add_trace(
                go.Scatter(
                    x=serie.index,
                    y=serie[var_id],
                    name=var_name,
                    mode="markers",
                    marker=dict(color=color, size=6),
                    hovertemplate="%{x|%d/%m/%Y}<br>%{y:,.2f}<extra></extra>",
                ),
                secondary_y=use_secondary,
            )
        else:
            fig.add_trace(
                go.Scatter(
                    x=serie.index,
                    y=serie[var_id],
                    name=var_name,
                    line=dict(color=color, width=2),
                    mode="lines",
                    connectgaps=True,
                    hovertemplate="%{x|%d/%m/%Y}<br>%{y:,.2f}<extra></extra>",
                ),
                secondary_y=use_secondary,
            )

    if plot_data_full.empty:
        st.info("No hay datos validos para las series seleccionadas")
        return

    fig.update_layout(
        hovermode="x unified",
        template="plotly_white",
        showlegend=False,
        margin=dict(l=0, r=0, t=30, b=0),
        height=500,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#000000"),
    )
    fig.update_xaxes(
        tickmode="auto",
        nticks=15,
        showspikes=True,
        spikemode="across",
        spikesnap="cursor",
        showline=True,
        spikecolor="gray",
        spikethickness=1,
        rangeslider=dict(
            visible=True,
            bgcolor="#F0F0F0",
            thickness=0.05,
            bordercolor=utils.COLOR_SLIDER_BORDE,
            borderwidth=1,
        ),
        rangeselector=dict(
            buttons=list(
                [
                    dict(count=6, label="6m", step="month", stepmode="backward"),
                    dict(count=1, label="1y", step="year", stepmode="backward"),
                    dict(step="all", label="Todo"),
                ]
            ),
            bgcolor="#FFFFFF",
            activecolor="#EAEAEA",
            font=dict(color="#000000"),
        ),
        type="date",
        showgrid=True,
        gridcolor="#EAEAEA",
    )
    fig.update_yaxes(title_text="", secondary_y=False, showgrid=True, gridcolor="#EAEAEA")
    fig.update_yaxes(title_text="", secondary_y=True, showgrid=False)

    st.plotly_chart(fig, width="stretch", config={"displayModeBar": True, "displaylogo": False})


def show(df_index):
    """Vista Macro. Orden real: grafico, grilla de series, botones y buscador."""
    selected_rows_global = df_index[df_index["ID"].isin(st.session_state["selected_ids"])].copy()
    selected_sheets = tuple(selected_rows_global["Pestaña"].dropna().astype(str).unique())
    all_data_sheets = utils.load_data_sheets(selected_sheets)

    if selected_rows_global.empty:
        st.info("Selecciona series en el buscador de abajo para graficar")
    else:
        st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
        items = _construir_items_series(selected_rows_global, all_data_sheets)
        _render_grafico(items)
        _render_controles_series([{k: v for k, v in item.items() if k != "serie"} for item in items])
        _render_botones_descarga(selected_rows_global, all_data_sheets)

    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)
    _render_buscador(df_index)
