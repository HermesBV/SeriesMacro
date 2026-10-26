"""Vista Indicadores IIEP: grupos de series elaboradas por investigadores del IIEP."""
from dataclasses import dataclass, field
from html import escape
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import utils

MESES = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")
RANGOS = {"5 años": 5, "10 años": 10, "Todo": None}
FRECUENCIAS = {"Mensual": ("mensual", "mensuales"), "Diaria": ("diaria", "diarias"),
               "Trimestral": ("trimestral", "trimestrales"), "Anual": ("anual", "anuales")}


@dataclass(frozen=True)
class GrupoIIEP:
    clave: str
    titulo: str
    autores: str
    resumen: str
    descripcion: str
    # (Código fuente, ID) de las series del grupo, además de las de `codigos_fuente`.
    series: tuple = ()
    codigos_fuente: tuple = ()
    # ID -> etiqueta corta, en el orden de presentación.
    etiquetas: dict = field(default_factory=dict)
    destacadas: tuple = ()
    # ID -> color de línea: cada serie conserva su color al activar o desactivar otras.
    colores: dict = field(default_factory=dict)
    # Frase común a las descripciones del índice; se muestra una sola vez.
    nota_comun: str = ""
    # ID -> aclaración breve que se muestra en su tarjeta de último dato.
    notas_tarjeta: dict = field(default_factory=dict)
    color: str = utils.COLOR_SLIDER_BORDE
    documento: str = ""
    anexos: tuple = ()


GRUPOS = (
    GrupoIIEP(
        clave="reservas",
        titulo="Reservas Internacionales de la Argentina",
        autores="Franco Impávido, Ezequiel Monteforte y Miguel Romero",
        resumen="Brutas, propias, netas y líquidas del BCRA, mes a mes desde 2000.",
        descripcion=(
            "Descomposición mensual de las reservas del BCRA desde septiembre de 2000: brutas, custodia, propias, "
            "prestadas, netas y líquidas, junto con la RIN-EFF del programa con el FMI y las netas según la planilla "
            "IRFCL. Hasta agosto de 2026 es la base publicada por los autores; desde entonces se actualiza "
            "automáticamente con su método a partir de la planilla IRFCL del BCRA y el tipo de pase del yuan. "
            "La RIN-EFF no se publica: queda fija hasta julio de 2026."
        ),
        codigos_fuente=("iiep-rin",),
        etiquetas={
            "rin-brutas-m": "Brutas", "rin-custodia-m": "Custodia", "rin-propias-m": "Propias",
            "rin-prestadas-m": "Prestadas", "rin-netas-m": "Netas", "rin-netas-planilla-m": "Netas según planilla",
            "rin-rin-eff-m": "RIN-EFF", "rin-liquidas-m": "Líquidas", "rin-propias-liquidas-m": "Propias líquidas",
        },
        destacadas=("rin-brutas-m", "rin-netas-m", "rin-liquidas-m"),
        colores={
            "rin-brutas-m": "#f05f30", "rin-custodia-m": "#8c8c8c", "rin-propias-m": "#3774AC",
            "rin-prestadas-m": "#bc2f29", "rin-netas-m": "#049c82", "rin-netas-planilla-m": "#7cc9b8",
            "rin-rin-eff-m": "#7b4fa0", "rin-liquidas-m": "#1f3b73", "rin-propias-liquidas-m": "#c9961a",
        },
        nota_comun=(
            "Hasta 2026-08, base publicada por los autores; desde entonces se calcula con el mismo método a partir "
            "de la planilla IRFCL del BCRA (dataset IRFCL del FMI y notas del país) y del tipo de pase del yuan del BCRA."
        ),
        notas_tarjeta={
            "rin-netas-m": "Coincide con la planilla desde 2004, salvo en 2015.",
            "rin-netas-planilla-m": "Sin los ajustes de 2002–2004 y 2015.",
        },
        color="#f05f30",
        documento="https://ojs.economicas.uba.ar/DT-IIEP/article/view/3723",
        anexos=(("Metodología (PDF)", "anexos/IIEP/Metodologia_reservas_internacionales.pdf"),),
    ),
    GrupoIIEP(
        clave="itcrb",
        titulo="ITCRB Estados Unidos (1958 - Actualidad)",
        autores="Área Macro",
        resumen="Tipo de cambio real bilateral con Estados Unidos, serie mensual empalmada.",
        descripcion=(
            "Tipo de cambio real bilateral con Estados Unidos. Hasta diciembre de 1996 usa la serie histórica del IIEP "
            "(importación, implícito), reescalada en enero de 1997; desde entonces, el promedio mensual oficial del "
            "ITCRB Estados Unidos del BCRA. Es la serie que alimenta la vista Daniel Heymann."
        ),
        series=((utils.SOURCE_HEYMANN, utils.ID_HEYMANN),),
        etiquetas={utils.ID_HEYMANN: "ITCRB Estados Unidos"},
        destacadas=(utils.ID_HEYMANN,),
        colores={utils.ID_HEYMANN: "#3774AC"},
        color="#3774AC",
    ),
)
GRUPOS_POR_CLAVE = {grupo.clave: grupo for grupo in GRUPOS}


# --- Datos -------------------------------------------------------------------

def _texto(valor):
    """Texto de una celda del inventario; vacío si falta (NaN es verdadero en booleano)."""
    return "" if valor is None or pd.isna(valor) else str(valor).strip()


def series_del_grupo(grupo, df_index):
    """Filas del inventario que integran el grupo, en el orden de `etiquetas`.

    `Etiqueta` es única: si dos series terminan con el mismo nombre se agrega su ID.
    """
    codigo = df_index["Código fuente"].astype(str).str.strip()
    ids = df_index["ID"].astype(str).str.strip()
    mascara = codigo.isin(grupo.codigos_fuente)
    for fuente, id_serie in grupo.series:
        mascara |= codigo.eq(fuente) & ids.eq(id_serie)
    filas = df_index.loc[mascara].copy()
    orden = {id_serie: posicion for posicion, id_serie in enumerate(grupo.etiquetas)}
    filas["_orden"] = filas["ID"].astype(str).str.strip().map(orden).fillna(len(orden))
    filas = filas.sort_values(["_orden", "Pestaña", "Columna BD"], kind="stable").drop(columns="_orden")
    etiquetas = [grupo.etiquetas.get(i, nombre) for i, nombre in zip(filas["ID"], filas["Nombre serie"])]
    repetidas = {etiqueta for etiqueta in etiquetas if etiquetas.count(etiqueta) > 1}
    filas["Etiqueta"] = [
        f"{etiqueta} ({id_serie})" if etiqueta in repetidas else etiqueta
        for etiqueta, id_serie in zip(etiquetas, filas["ID"])
    ]
    return filas


def tabla_valores(filas, hojas):
    """Una columna por serie (con su etiqueta), indexada por fecha."""
    columnas = {}
    for _, fila in filas.iterrows():
        hoja = hojas.get(fila["Pestaña"])
        if hoja is None or fila["Columna BD"] not in hoja.columns:
            continue
        fechas = pd.to_datetime(hoja.iloc[:, 0], errors="coerce")
        valores = pd.to_numeric(hoja[fila["Columna BD"]], errors="coerce")
        columnas[fila["Etiqueta"]] = pd.Series(valores.values, index=fechas).dropna()
    if not columnas:
        return pd.DataFrame()
    return pd.DataFrame(columnas).sort_index()


def resumen_ultimos(tabla):
    """Último dato de cada serie y su valor doce meses antes."""
    filas = []
    for nombre, serie in tabla.items():
        serie = serie.dropna()
        if serie.empty:
            continue
        fecha = serie.index[-1]
        filas.append({
            "Serie": nombre, "Fecha": fecha, "Valor": serie.iloc[-1],
            "Un año antes": serie.get(fecha - pd.DateOffset(years=1)),
        })
    return pd.DataFrame(filas)


def periodo_y_frecuencia(filas):
    """Texto «9 series mensuales · sep-2000 a sep-2026» para la tarjeta del mosaico."""
    cantidad = len(filas)
    frecuencias = filas.get("Frecuencia", pd.Series(dtype=object)).dropna().astype(str).unique()
    singular, plural = FRECUENCIAS.get(frecuencias[0], ("", "")) if len(frecuencias) == 1 else ("", "")
    texto = f"{cantidad} serie" + ("s" if cantidad != 1 else "")
    adjetivo = plural if cantidad != 1 else singular
    if adjetivo:
        texto += f" {adjetivo}"
    desde = pd.to_datetime(filas.get("Fecha inicio", pd.Series(dtype=object)), errors="coerce").min()
    hasta = pd.to_datetime(filas.get("Fecha fin", pd.Series(dtype=object)), errors="coerce").max()
    if pd.notna(desde) and pd.notna(hasta):
        texto += f" · {mes_anio(desde)} a {mes_anio(hasta)}"
    return texto


# --- Formato -----------------------------------------------------------------

def numero(valor, decimales=1):
    """1234.5 -> 1.234,5 (convención argentina); nunca «−0,0»."""
    if valor is None or pd.isna(valor):
        return "s/d"
    valor = round(float(valor), decimales) + 0.0
    texto = f"{valor:,.{decimales}f}"
    return texto.replace(",", "§").replace(".", ",").replace("§", ".").replace("-", "−")


def mes_anio(fecha):
    fecha = pd.to_datetime(fecha, errors="coerce")
    if pd.isna(fecha):
        return "s/d"
    return f"{MESES[fecha.month - 1]}-{fecha.year}"


def titulo_html(titulo):
    """Escapa el título y mantiene unido el paréntesis final, p. ej. «(1958 - Actualidad)»."""
    texto = escape(titulo)
    if texto.endswith(")") and "(" in texto:
        base, parentesis = texto.rsplit("(", 1)
        texto = f"{base}<span style='white-space:nowrap'>({parentesis}</span>"
    return texto


def unidad_corta(unidad):
    texto = _texto(unidad)
    if "millones de dólares" in texto.casefold():
        return "M USD"
    return texto


@st.cache_data(show_spinner=False)
def _excel(datos, hoja):
    return utils.convert_single_sheet_to_excel(datos, hoja)


# --- Presentación ------------------------------------------------------------

def _estilos():
    verde = utils.COLOR_SLIDER_BORDE
    st.markdown(
        f"""
        <style>
        .iiep-intro {{ color: #545454; font-size: 0.95rem; margin: 0.2rem 0 1.4rem 0; max-width: 60rem; }}
        .iiep-tarjeta {{ border-top: 4px solid var(--acento); padding-top: 0.9rem; }}
        .iiep-tarjeta-titulo {{ font-weight: 700; font-size: 1.2rem; line-height: 1.3; color: #000000; }}
        @media (min-width: 641px) and (max-width: 1320px) {{ .iiep-tarjeta-titulo {{ min-height: 2.6em; }} }}
        .iiep-tarjeta-autores {{ font-size: 0.8rem; color: #6b6b6b; margin-top: 0.25rem; }}
        .iiep-tarjeta-resumen {{ font-size: 0.9rem; color: #2b2b2b; margin-top: 0.7rem; line-height: 1.5; min-height: 3em; }}
        .iiep-tarjeta-meta {{ font-size: 0.78rem; color: #6b6b6b; margin: 0.5rem 0 0.9rem 0; }}
        .iiep-cabecera {{ border-left: 5px solid var(--acento); padding: 0.1rem 0 0.1rem 1rem; margin: 0.4rem 0 1.4rem 0; }}
        .iiep-grupo-titulo {{ font-weight: 700; font-size: 1.75rem; line-height: 1.2; color: #000000; }}
        .iiep-grupo-autores {{ font-size: 0.9rem; color: #6b6b6b; margin-top: 0.3rem; }}
        .iiep-grupo-descripcion {{ font-size: 0.93rem; color: #2b2b2b; line-height: 1.6; max-width: 62rem; margin-top: 0.7rem; }}
        .iiep-grupo-descripcion a {{ color: {verde}; font-weight: 600; text-decoration: none; white-space: nowrap; }}
        .iiep-grupo-descripcion a:hover {{ text-decoration: underline; }}
        .iiep-seccion {{ font-weight: 600; font-size: 1.1rem; color: #31333F; margin: 0.4rem 0 0.6rem 0; }}
        .iiep-seccion-fecha {{ font-weight: 400; font-size: 0.9rem; color: #6b6b6b; margin-left: 0.4rem; }}
        .iiep-otra-fecha {{ color: #7b4fa0; font-weight: 600; }}
        .iiep-kpis {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 0.75rem; margin: 0 0 1.8rem 0; }}
        .iiep-kpis.iiep-unica {{ grid-template-columns: minmax(0, 340px); }}
        .iiep-kpi {{ border: 1px solid #E3E3E3; border-left: 4px solid var(--color); border-radius: 8px;
                     padding: 0.7rem 0.9rem; background: #FFFFFF; min-width: 0; }}
        .iiep-kpi-nombre {{ font-size: 0.8rem; color: #545454; font-weight: 600; }}
        .iiep-kpi-valor {{ font-size: 1.4rem; font-weight: 700; color: #000000; line-height: 1.25; margin-top: 0.15rem; }}
        .iiep-kpi-valor small {{ font-size: 0.72rem; font-weight: 400; color: #6b6b6b; margin-left: 0.3rem; }}
        .iiep-kpi-unidad {{ font-size: 0.72rem; color: #6b6b6b; overflow-wrap: anywhere; }}
        .iiep-kpi-nota {{ font-size: 0.72rem; color: #6b6b6b; margin-top: 0.3rem; font-style: italic; }}
        .iiep-kpi-pie {{ font-size: 0.76rem; color: #6b6b6b; margin-top: 0.25rem; line-height: 1.45; }}
        .iiep-sube {{ color: {verde}; font-weight: 600; }}
        .iiep-baja {{ color: #bc2f29; font-weight: 600; }}
        .iiep-unidad-grafico {{ font-size: 0.8rem; color: #545454; margin: 0.2rem 0 -0.6rem 0; }}
        .iiep-nota {{ font-size: 0.84rem; color: #545454; margin: 0.2rem 0 0.4rem 0; }}
        .iiep-definiciones dt {{ font-weight: 600; color: #000000; margin-top: 0.8rem; font-size: 0.9rem; }}
        .iiep-definiciones dd {{ margin: 0.15rem 0 0 0; color: #2b2b2b; font-size: 0.86rem; line-height: 1.55; }}
        .iiep-definiciones dd span {{ color: #6b6b6b; }}
        /* Píldoras: la selección activa en verde lleno; sin el gris del foco en las inactivas. */
        [data-testid="stBaseButton-pillsActive"] {{
            background-color: {verde} !important; border-color: {verde} !important; color: #FFFFFF !important;
        }}
        [data-testid="stBaseButton-pillsActive"] p {{ color: #FFFFFF !important; }}
        [data-testid="stBaseButton-pills"],
        [data-testid="stBaseButton-pills"]:hover,
        [data-testid="stBaseButton-pills"]:focus:not(:focus-visible) {{
            background-color: #FFFFFF !important; color: #31333F !important;
        }}
        [data-testid="stBaseButton-pills"] p {{ color: #31333F !important; }}
        [data-testid="stBaseButton-pills"]:focus:not(:focus-visible) {{ border-color: rgba(49, 51, 63, 0.2) !important; }}
        @media (hover: hover) {{
            [data-testid="stBaseButton-pills"]:hover {{ border-color: #9E9E9E !important; }}
        }}
        /* Descargas: botones secundarios (contorno), de una sola línea. */
        .st-key-iiep_descargas div.stDownloadButton > button {{
            background-color: #FFFFFF !important; border: 1.5px solid {verde} !important; white-space: nowrap;
        }}
        .st-key-iiep_descargas div.stDownloadButton > button:hover {{ background-color: #E6F4F1 !important; }}
        .st-key-iiep_descargas div.stDownloadButton > button p,
        .st-key-iiep_descargas div.stDownloadButton > button span {{ color: {verde} !important; white-space: nowrap; }}
        .st-key-iiep_descargas {{ margin: 1.2rem 0 0.6rem 0; }}
        /* «Volver» como enlace: gana a la regla global que pinta de verde los botones. */
        .st-key-iiep_volver div.stButton > button,
        .st-key-iiep_volver div.stButton > button:hover {{
            background: transparent !important; border: none !important; padding: 0 !important;
            box-shadow: none !important; min-height: 0 !important;
        }}
        .st-key-iiep_volver div.stButton > button p {{
            color: {verde} !important; font-weight: 600 !important; font-size: 0.95rem !important;
        }}
        .st-key-iiep_volver div.stButton > button:hover p {{ text-decoration: underline; }}
        @media (max-width: 900px) {{
            .iiep-kpis {{ grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.5rem; }}
        }}
        @media (max-width: 640px) {{
            .iiep-kpis.iiep-unica {{ grid-template-columns: minmax(0, 1fr); }}
            .iiep-kpi {{ padding: 0.55rem 0.6rem; }}
            .iiep-kpi-valor {{ font-size: 1.15rem; }}
            .iiep-grupo-titulo {{ font-size: 1.35rem; }}
            .iiep-cabecera {{ padding-left: 0.7rem; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# El grupo abierto vive sólo en la URL (?grupo=...): al navegar con el encabezado se
# limpia, y un enlace copiado siempre muestra lo que se estaba viendo.
def _abrir(clave):
    st.query_params["grupo"] = clave


def _cerrar():
    st.query_params.pop("grupo", None)


def _guardar_seleccion(clave):
    st.session_state[f"iiep_seleccion_{clave}"] = st.session_state.get(f"iiep_series_{clave}", [])


def _mosaico(df_index):
    st.markdown(
        "<div class='iiep-intro'>Series elaboradas por investigadores del IIEP. También se encuentran en el "
        "buscador de Series Macro con institución IIEP.</div>",
        unsafe_allow_html=True,
    )
    columnas = st.columns(2, gap="medium")
    for posicion, grupo in enumerate(GRUPOS):
        filas = series_del_grupo(grupo, df_index)
        with columnas[posicion % 2]:
            with st.container(border=True):
                st.markdown(
                    f"<div class='iiep-tarjeta' style='--acento:{grupo.color}'>"
                    f"<div class='iiep-tarjeta-titulo'>{titulo_html(grupo.titulo)}</div>"
                    f"<div class='iiep-tarjeta-autores'>{escape(grupo.autores)}</div>"
                    f"<div class='iiep-tarjeta-resumen'>{escape(grupo.resumen)}</div>"
                    f"<div class='iiep-tarjeta-meta'>{escape(periodo_y_frecuencia(filas))}</div></div>",
                    unsafe_allow_html=True,
                )
                st.button("Abrir", key=f"iiep_abrir_{grupo.clave}", disabled=filas.empty,
                          on_click=_abrir, args=(grupo.clave,), width="stretch")


def _kpis(resumen, filas, colores, notas=None):
    unidades = dict(zip(filas["Etiqueta"], filas["Unidad"]))
    notas = notas or {}
    fecha_comun = resumen["Fecha"].mode().iloc[0] if not resumen.empty else None
    tarjetas = []
    for _, fila in resumen.iterrows():
        unidad = unidad_corta(unidades.get(fila["Serie"]))
        # Las unidades largas (p. ej. «Índice 17-dic-2015=100») van debajo del valor.
        unidad_html = (f"<small>{escape(unidad)}</small></div>" if len(unidad) <= 8
                       else f"</div><div class='iiep-kpi-unidad'>{escape(unidad)}</div>")
        anterior = fila["Un año antes"]
        fecha = "" if fila["Fecha"] == fecha_comun else f"<span class='iiep-otra-fecha'>Dato a {mes_anio(fila['Fecha'])}</span><br>"
        if anterior is None or pd.isna(anterior):
            pie = fecha or "&nbsp;"
        else:
            cambio = fila["Valor"] - anterior
            clase, flecha = ("iiep-sube", "▲") if cambio >= 0 else ("iiep-baja", "▼")
            pie = f"{fecha}<span class='{clase}'>{flecha} {numero(abs(cambio))}</span> en 12 meses"
        tarjetas.append(
            f"<div class='iiep-kpi' style='--color:{colores.get(fila['Serie'], '#E3E3E3')}'>"
            f"<div class='iiep-kpi-nombre'>{escape(fila['Serie'])}</div>"
            f"<div class='iiep-kpi-valor'>{numero(fila['Valor'])}{unidad_html}"
            f"<div class='iiep-kpi-pie'>{pie}</div>"
            + (f"<div class='iiep-kpi-nota'>{escape(notas[fila['Serie']])}</div>" if fila["Serie"] in notas else "")
            + "</div>"
        )
    clase = "iiep-kpis iiep-unica" if len(tarjetas) == 1 else "iiep-kpis"
    st.markdown(f"<div class='{clase}'>{''.join(tarjetas)}</div>", unsafe_allow_html=True)


def recortar(tabla, anios):
    """Últimos `anios` años contados desde el último dato; todo si `anios` es None."""
    if anios is None or tabla.empty:
        return tabla
    return tabla[tabla.index >= tabla.index.max() - pd.DateOffset(years=anios)]


def _grafico(tabla, colores):
    una_serie = tabla.shape[1] == 1
    fig = go.Figure()
    for nombre, serie in tabla.items():
        serie = serie.dropna()
        fig.add_trace(go.Scatter(
            x=serie.index, y=serie.values, name=nombre, mode="lines",
            line=dict(color=colores[nombre], width=2.2), hovertemplate="%{y:,.1f}",
        ))
    fig.update_layout(
        separators=",.", hovermode="x unified", template="plotly_white", height=460,
        margin=dict(l=0, r=0, t=12 if una_serie else 30, b=10), showlegend=not una_serie, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Poppins, sans-serif", color="#000000", size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0, font=dict(size=12)),
        hoverlabel=dict(bgcolor="#FFFFFF", font=dict(color="#000000")),
    )
    fig.update_xaxes(
        # Mes/año numérico: el nombre del mes de Plotly saldría en inglés.
        type="date", showgrid=True, gridcolor="#EFEFEF", hoverformat="%m/%Y", nticks=8,
    )
    fig.update_yaxes(
        showgrid=True, gridcolor="#EFEFEF", zeroline=True, zerolinecolor="#9E9E9E", zerolinewidth=1,
        tickformat=",.0f",
    )
    st.plotly_chart(fig, width="stretch", config={
        "displaylogo": False, "locale": "es", "modeBarButtons": [["toImage", "resetScale2d"]],
        "toImageButtonOptions": {"format": "png", "scale": 2},
    })


def _definiciones(filas, nota_comun=""):
    if nota_comun:
        st.markdown(f"<div class='iiep-nota'>{escape(nota_comun)}</div>", unsafe_allow_html=True)
    items = []
    for _, fila in filas.iterrows():
        descripcion = _texto(fila.get("Descripción"))
        if nota_comun:
            descripcion = descripcion.replace(nota_comun, "").strip()
        cobertura = f"{mes_anio(fila.get('Fecha inicio'))} a {mes_anio(fila.get('Fecha fin'))}"
        unidad = _texto(fila.get("Unidad"))
        detalle = f"Cobertura: {cobertura}." + (f" Unidad: {unidad}." if unidad else "")
        items.append(
            f"<dt>{escape(_texto(fila['Nombre serie']))}</dt>"
            f"<dd>{escape(descripcion)} <span>{escape(detalle)}</span></dd>"
        )
    st.markdown(f"<dl class='iiep-definiciones'>{''.join(items)}</dl>", unsafe_allow_html=True)


def _detalle(grupo, df_index):
    st.button("← Indicadores IIEP", key="iiep_volver", on_click=_cerrar)
    enlace = (f" <a href='{grupo.documento}' target='_blank' rel='noopener noreferrer'>Documento de trabajo ↗</a>"
              if grupo.documento else "")
    st.markdown(
        f"<div class='iiep-cabecera' style='--acento:{grupo.color}'>"
        f"<div class='iiep-grupo-titulo'>{titulo_html(grupo.titulo)}</div>"
        f"<div class='iiep-grupo-autores'>{escape(grupo.autores)}</div>"
        f"<div class='iiep-grupo-descripcion'>{escape(grupo.descripcion)}{enlace}</div></div>",
        unsafe_allow_html=True,
    )

    filas = series_del_grupo(grupo, df_index)
    if filas.empty:
        st.info("Las series de este grupo todavía no están en la base publicada.")
        return
    hojas = utils.load_data_sheets(tuple(filas["Pestaña"].dropna().astype(str).unique()))
    tabla = tabla_valores(filas, hojas)
    if tabla.empty:
        st.info("No hay datos para las series de este grupo.")
        return

    nombres = list(tabla.columns)
    paleta = utils.PALETA_COLORES + ["#6b6b6b", "#7b4fa0", "#1f3b73", "#c9961a"]
    por_id = dict(zip(filas["Etiqueta"], filas["ID"]))
    colores = {
        nombre: grupo.colores.get(por_id.get(nombre), paleta[posicion % len(paleta)])
        for posicion, nombre in enumerate(nombres)
    }

    resumen = resumen_ultimos(tabla)
    st.markdown(
        f"<div class='iiep-seccion'>Último dato <span class='iiep-seccion-fecha'>"
        f"{mes_anio(resumen['Fecha'].mode().iloc[0])}</span></div>",
        unsafe_allow_html=True,
    )
    etiqueta_de = dict(zip(filas["ID"], filas["Etiqueta"]))
    _kpis(resumen, filas, colores, {etiqueta_de[i]: nota for i, nota in grupo.notas_tarjeta.items() if i in etiqueta_de})

    st.markdown("<div class='iiep-seccion'>Evolución</div>", unsafe_allow_html=True)
    if len(nombres) > 1:
        etiqueta_por_id = dict(zip(filas["ID"], filas["Etiqueta"]))
        destacadas = [etiqueta_por_id[i] for i in grupo.destacadas if etiqueta_por_id.get(i) in nombres]
        # La selección se guarda aparte: Streamlit borra el estado del widget cuando la
        # vista no se dibuja, y así se conserva al ir a otra vista y volver.
        guardada = [n for n in st.session_state.get(f"iiep_seleccion_{grupo.clave}", destacadas or nombres[:1])
                    if n in nombres]
        elegidas = st.pills(
            "Series en el gráfico", nombres, selection_mode="multi", default=guardada,
            key=f"iiep_series_{grupo.clave}", on_change=_guardar_seleccion, args=(grupo.clave,),
        )
    else:
        elegidas = nombres
    elegidas = [nombre for nombre in nombres if nombre in (elegidas or [])]
    if elegidas:
        rango = st.radio("Período", list(RANGOS), index=len(RANGOS) - 1, horizontal=True,
                         key=f"iiep_rango_{grupo.clave}", label_visibility="collapsed")
        unidades = {unidad_corta(u) for u in filas.loc[filas["Etiqueta"].isin(elegidas), "Unidad"]}
        unidades.discard("")
        if len(unidades) == 1:
            unidad = unidades.pop()
            texto_unidad = "En millones de dólares estadounidenses" if unidad == "M USD" else unidad
            st.markdown(f"<div class='iiep-unidad-grafico'>{escape(texto_unidad)}</div>", unsafe_allow_html=True)
        _grafico(recortar(tabla[elegidas], RANGOS[rango]), colores)
    else:
        st.info("Elegí al menos una serie para graficar.")

    anexos = [(etiqueta, ruta) for etiqueta, ruta in grupo.anexos if os.path.exists(ruta)]
    with st.container(key="iiep_descargas"):
        columnas = st.columns([1] * (1 + len(anexos)) + [max(1, 3 - len(anexos))], gap="small")
        with columnas[0]:
            datos = tabla.rename_axis("Fecha").reset_index()
            st.download_button(
                "Datos (Excel)", data=_excel(datos, grupo.clave[:31]), icon=":material/download:",
                file_name=f"IIEP_{grupo.clave}.xlsx", width="stretch",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        for columna, (etiqueta, ruta) in zip(columnas[1:], anexos):
            with columna:
                with open(ruta, "rb") as archivo:
                    st.download_button(etiqueta, data=archivo.read(), file_name=os.path.basename(ruta),
                                       icon=":material/description:", mime="application/pdf", width="stretch")

    with st.expander("Definición de cada serie" if len(filas) > 1 else "Definición de la serie"):
        _definiciones(filas, grupo.nota_comun)


def show(df_index):
    _estilos()
    clave = st.query_params.get("grupo")
    grupo = GRUPOS_POR_CLAVE.get(clave)
    if clave is not None and grupo is None:
        st.query_params.pop("grupo", None)
    if grupo is None:
        _mosaico(df_index)
    else:
        _detalle(grupo, df_index)
