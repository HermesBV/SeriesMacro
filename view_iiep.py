"""Vista Indicadores IIEP: grupos de series elaboradas por investigadores del IIEP."""
from dataclasses import dataclass, field
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import utils


@dataclass(frozen=True)
class GrupoIIEP:
    clave: str
    titulo: str
    autores: str
    descripcion: str
    # (Código fuente, ID) de las series del grupo, en el orden en que se presentan.
    series: tuple = ()
    codigos_fuente: tuple = ()
    destacadas: tuple = ()
    # IDs en el orden de presentación; las demás series van al final.
    orden: tuple = ()
    documento: str = ""
    anexos: tuple = field(default_factory=tuple)


GRUPOS = (
    GrupoIIEP(
        clave="reservas",
        titulo="Reservas Internacionales de la Argentina",
        autores="Franco Impávido, Ezequiel Monteforte y Miguel Romero",
        descripcion=(
            "Descomposición mensual de las reservas del BCRA desde septiembre de 2000: brutas, custodia, propias, "
            "prestadas, netas y líquidas, junto con la RIN-EFF del programa con el FMI y las netas según la planilla "
            "IRFCL. Hasta agosto de 2026 es la base publicada por los autores; desde entonces se actualiza "
            "automáticamente con su método a partir de la planilla IRFCL del BCRA y el tipo de pase del yuan. "
            "La RIN-EFF no se publica y queda fija hasta julio de 2026."
        ),
        codigos_fuente=("iiep-rin",),
        destacadas=("rin-brutas-m", "rin-netas-m", "rin-liquidas-m"),
        orden=(
            "rin-brutas-m", "rin-custodia-m", "rin-propias-m", "rin-prestadas-m", "rin-netas-m",
            "rin-netas-planilla-m", "rin-rin-eff-m", "rin-liquidas-m", "rin-propias-liquidas-m",
        ),
        documento="https://ojs.economicas.uba.ar/DT-IIEP/article/view/3723",
        anexos=(("Metodología de la base (PDF)", "anexos/IIEP/Metodologia_reservas_internacionales.pdf"),),
    ),
    GrupoIIEP(
        clave="itcrb",
        titulo="ITCRB Estados Unidos (1958 - Actualidad)",
        autores="Área Macro",
        descripcion=(
            "Tipo de cambio real bilateral con Estados Unidos. Hasta diciembre de 1996 usa la serie histórica del IIEP "
            "(importación, implícito), reescalada en enero de 1997; desde entonces, el promedio mensual oficial del "
            "ITCRB Estados Unidos del BCRA. Es la serie que alimenta la vista Daniel Heymann."
        ),
        series=((utils.SOURCE_HEYMANN, utils.ID_HEYMANN),),
        destacadas=(utils.ID_HEYMANN,),
    ),
)


def series_del_grupo(grupo, df_index):
    """Filas del inventario que integran el grupo, en el orden definido."""
    codigo = df_index["Código fuente"].astype(str).str.strip()
    ids = df_index["ID"].astype(str).str.strip()
    mascara = codigo.isin(grupo.codigos_fuente)
    for fuente, id_serie in grupo.series:
        mascara |= codigo.eq(fuente) & ids.eq(id_serie)
    filas = df_index.loc[mascara].copy()
    orden = {id_serie: posicion for posicion, id_serie in enumerate(grupo.orden or tuple(i for _, i in grupo.series))}
    filas["_orden"] = filas["ID"].astype(str).str.strip().map(orden).fillna(len(orden))
    return filas.sort_values(["_orden", "Pestaña", "Columna BD"], kind="stable").drop(columns="_orden")


def tabla_valores(filas, hojas):
    """Una columna por serie, indexada por fecha."""
    columnas = {}
    for _, fila in filas.iterrows():
        hoja = hojas.get(fila["Pestaña"])
        if hoja is None or fila["Columna BD"] not in hoja.columns:
            continue
        fechas = pd.to_datetime(hoja.iloc[:, 0], errors="coerce")
        valores = pd.to_numeric(hoja[fila["Columna BD"]], errors="coerce")
        columnas[fila["Nombre serie"]] = pd.Series(valores.values, index=fechas).dropna()
    if not columnas:
        return pd.DataFrame()
    return pd.DataFrame(columnas).sort_index()


def resumen_ultimos(tabla):
    filas = []
    for nombre, serie in tabla.items():
        serie = serie.dropna()
        if serie.empty:
            continue
        fecha = serie.index[-1]
        hace_un_anio = serie.get(fecha - pd.DateOffset(years=1))
        filas.append({
            "Serie": nombre,
            "Último dato": fecha.strftime("%Y-%m"),
            "Valor": serie.iloc[-1],
            "Un año antes": hace_un_anio,
        })
    return pd.DataFrame(filas)


def _estilos():
    st.markdown(
        f"""
        <style>
        .iiep-tarjeta-titulo {{ font-weight: 700; font-size: 1.25rem; line-height: 1.25; color: #000000; }}
        .iiep-tarjeta-autores {{ font-size: 0.8rem; color: #545454; margin-top: 4px; min-height: 2.2em; }}
        .iiep-grupo-titulo {{ font-weight: 700; font-size: 1.7rem; color: #000000; margin-bottom: 0; }}
        .iiep-grupo-autores {{ font-size: 0.9rem; color: #545454; margin-bottom: 0.6rem; }}
        .iiep-grupo-descripcion {{ font-size: 0.92rem; color: #222222; max-width: 70rem; }}
        .iiep-grupo-descripcion a {{ color: {utils.COLOR_SLIDER_BORDE}; font-weight: 600; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _mosaico(df_index):
    st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)
    columnas = st.columns(2, gap="medium")
    for posicion, grupo in enumerate(GRUPOS):
        cantidad = len(series_del_grupo(grupo, df_index))
        with columnas[posicion % 2]:
            with st.container(border=True):
                st.markdown(
                    f"<div class='iiep-tarjeta-titulo'>{grupo.titulo}</div>"
                    f"<div class='iiep-tarjeta-autores'>{grupo.autores}</div>",
                    unsafe_allow_html=True,
                )
                etiqueta = f"Ver {cantidad} serie" + ("s" if cantidad != 1 else "")
                if st.button(etiqueta, key=f"iiep_abrir_{grupo.clave}", disabled=cantidad == 0):
                    st.session_state["iiep_grupo"] = grupo.clave
                    st.rerun()


def _grafico(tabla):
    fig = go.Figure()
    for posicion, (nombre, serie) in enumerate(tabla.items()):
        serie = serie.dropna()
        fig.add_trace(go.Scatter(
            x=serie.index, y=serie.values, name=nombre, mode="lines", connectgaps=False,
            line=dict(color=utils.PALETA_COLORES[posicion % len(utils.PALETA_COLORES)], width=2),
            hovertemplate="%{x|%Y-%m}<br>%{y:,.1f}<extra>" + nombre + "</extra>",
        ))
    fig.update_layout(
        hovermode="x unified", template="plotly_white", height=460, margin=dict(l=0, r=0, t=30, b=0),
        legend=dict(orientation="h", y=-0.12), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#000000"),
    )
    fig.update_xaxes(type="date", showgrid=True, gridcolor="#EAEAEA")
    fig.update_yaxes(showgrid=True, gridcolor="#EAEAEA", zeroline=True, zerolinecolor="#BBBBBB")
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": True, "displaylogo": False})


def _detalle(grupo, df_index):
    if st.button("← Volver a Indicadores IIEP", key="iiep_volver"):
        st.session_state.pop("iiep_grupo", None)
        st.rerun()
    enlace = f" <a href='{grupo.documento}' target='_blank' rel='noopener noreferrer'>Documento de trabajo</a>" if grupo.documento else ""
    st.markdown(
        f"<div class='iiep-grupo-titulo'>{grupo.titulo}</div>"
        f"<div class='iiep-grupo-autores'>{grupo.autores}</div>"
        f"<div class='iiep-grupo-descripcion'>{grupo.descripcion}{enlace}</div>",
        unsafe_allow_html=True,
    )

    filas = series_del_grupo(grupo, df_index)
    if filas.empty:
        st.info("Las series de este grupo todavía no están en la base publicada.")
        return
    hojas = utils.load_data_sheets(tuple(filas["Pestaña"].dropna().astype(str).unique()))
    tabla = tabla_valores(filas, hojas)
    nombres = list(tabla.columns)
    destacadas = filas.loc[filas["ID"].isin(grupo.destacadas), "Nombre serie"].tolist() or nombres[:3]
    elegidas = st.multiselect("Series", nombres, default=[n for n in destacadas if n in nombres], key=f"iiep_series_{grupo.clave}")
    if elegidas:
        _grafico(tabla[elegidas])

    resumen = resumen_ultimos(tabla)
    st.dataframe(
        resumen, hide_index=True, width="stretch",
        column_config={
            "Valor": st.column_config.NumberColumn(format="%.1f"),
            "Un año antes": st.column_config.NumberColumn(format="%.1f"),
        },
    )
    with st.expander("Detalle de cada serie"):
        detalle = filas[["Nombre serie", "Unidad", "Desde", "Hasta", "Detalle"]].rename(columns={"Nombre serie": "Serie"})
        st.dataframe(detalle, hide_index=True, width="stretch")

    columnas = st.columns([1, 1, 3])
    with columnas[0]:
        datos = tabla.reset_index().rename(columns={"index": "Fecha"})
        st.download_button(
            "Descargar datos", data=utils.convert_single_sheet_to_excel(datos, grupo.clave[:31]),
            file_name=f"IIEP_{grupo.clave}.xlsx", width="stretch",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    for posicion, (etiqueta, ruta) in enumerate(grupo.anexos, start=1):
        if posicion < len(columnas) and os.path.exists(ruta):
            with columnas[posicion]:
                with open(ruta, "rb") as archivo:
                    st.download_button(etiqueta, data=archivo.read(), file_name=os.path.basename(ruta),
                                       mime="application/pdf", width="stretch")


def show(df_index):
    _estilos()
    clave = st.session_state.get("iiep_grupo")
    grupo = next((g for g in GRUPOS if g.clave == clave), None)
    if grupo is None:
        _mosaico(df_index)
    else:
        _detalle(grupo, df_index)
