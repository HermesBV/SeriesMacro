# VIEW_HEYMANN_RESET_V14: botones de descarga compactos en una linea.
import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import base64
import io
import utils  # Importamos nuestro módulo de utilidades

def plot_heymann_camel(df, compacto=False):
    """Genera el gráfico de densidad kernel (Camello).

    `compacto` arma una versión más alta y angosta, con letra proporcionada, para
    celulares: la versión ancha reducida a 360 px queda ilegible.
    """
    if df.empty: return None

    # Preprocesamiento
    df = df.copy()
    cols = df.columns
    df.rename(columns={cols[0]: 'Fecha', cols[1]: 'Valor'}, inplace=True)

    df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
    df = df.dropna(subset=['Fecha', 'Valor'])

    if df.empty: return None

    # Estadísticas
    mean_val = df['Valor'].mean()
    last_row = df.iloc[-1]
    last_val = last_row['Valor']
    last_date = last_row['Fecha']

    # Fecha y decimales con la convención del resto de la app (ago-2026, 92,70).
    meses = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")
    last_date_str = f"{meses[last_date.month - 1]}-{last_date.year}"

    # --- AJUSTADO PARA FONDO BLANCO ---
    plt.style.use('default')

    fig, ax = plt.subplots(figsize=(6.4, 5.6) if compacto else (12, 5.2))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')

    # Plot
    sns.kdeplot(df['Valor'], color='#4da6ff', fill=True, alpha=0.3, linewidth=2, ax=ax, label='Densidad')

    # Líneas de referencia
    ax.axvline(mean_val, linestyle='--', color=utils.PALETA_COLORES[0], label=f'Promedio ({mean_val:.2f})'.replace('.', ','))
    ax.axvline(last_val, linestyle='--', color='#049c82', label=f'{last_date_str} ({last_val:.2f})'.replace('.', ','))

    # Textos (Actualizado con colores oscuros)
    titulo = 'Estimación de Densidad Kernel para ITCRB Estados Unidos 17-dic-2015=100'
    if compacto:
        titulo = 'Estimación de Densidad Kernel para\nITCRB Estados Unidos 17-dic-2015=100'
    ax.set_title(titulo, color='black', fontsize=15 if compacto else 14, pad=15)
    ax.set_xlabel('Valor del Índice', color='black')
    ax.set_ylabel('Densidad', color='black')

    # Ajustes visuales: coma decimal en los ejes, como en el resto de la app.
    from matplotlib.ticker import FuncFormatter
    ax.yaxis.set_major_formatter(FuncFormatter(lambda valor, _: f"{valor:.3f}".replace('.', ',')))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda valor, _: f"{valor:g}".replace('.', ',')))
    ax.tick_params(colors='black', labelsize=13 if compacto else 12)
    if compacto:
        ax.xaxis.label.set_size(13)
        ax.yaxis.label.set_size(13)
        legend = ax.legend(frameon=False, fontsize=12, loc='upper center', bbox_to_anchor=(0.5, -0.16), ncol=1)
    else:
        legend = ax.legend(frameon=False, fontsize=12)
    plt.setp(legend.get_texts(), color='black')
    ax.grid(True, linestyle=':', alpha=0.5, color='gray') # Grilla un poco más visible
    sns.despine(left=True, bottom=True)

    # Reducimos márgenes para maximizar espacio
    plt.tight_layout()

    return fig


@st.cache_data(show_spinner=False)
def _heymann_chart_png(database_version, compacto=False):
    data = utils.load_heymann_data()
    if data is None:
        return None
    fig = plot_heymann_camel(data, compacto=compacto)
    if fig is None:
        return None
    output = io.BytesIO()
    try:
        fig.savefig(output, format="png", transparent=False, facecolor="white", bbox_inches="tight")
        return output.getvalue()
    finally:
        plt.close(fig)


def preload_chart():
    """Prepara el gráfico una vez por versión de la base al iniciar la página."""
    return _heymann_chart_png(utils._database_version())

def show(df_heymann):
    """Función principal para renderizar la vista de Heymann"""
    # Sin título Markdown superior
    st.markdown(
        """
        <style>
        /* Heymann: botones de descarga angostos pero legibles en una linea. */
        div[data-testid="stDownloadButton"] button {
            padding-left: 0.22rem !important;
            padding-right: 0.22rem !important;
            min-height: 2.20rem !important;
            white-space: nowrap !important;
        }
        .heymann-espacio { height: 9rem; }
        .heymann-grafico img { display: block; width: 100%; height: auto; }
        @media (max-width: 700px) { .heymann-espacio { height: 0; } }
        div[data-testid="stDownloadButton"] button p,
        div[data-testid="stDownloadButton"] button span,
        div[data-testid="stDownloadButton"] button div {
            font-size: 0.78rem !important;
            line-height: 1.05 !important;
            white-space: nowrap !important;
            overflow: visible !important;
            text-overflow: clip !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if df_heymann is not None:
        chart_png = preload_chart()

        if chart_png:
            # Layout: 6 partes gráfico, 1 parte botones (para que sean angostos)
            col_graph, col_buttons = st.columns([6, 1.18], gap="medium")

            with col_graph:
                # El navegador elige la versión según el ancho de la pantalla.
                compacto = _heymann_chart_png(utils._database_version(), compacto=True) or chart_png
                st.markdown(
                    "<picture class='heymann-grafico'>"
                    f"<source media='(max-width: 700px)' srcset='data:image/png;base64,{base64.b64encode(compacto).decode()}'>"
                    f"<img src='data:image/png;base64,{base64.b64encode(chart_png).decode()}' "
                    "alt='Densidad del ITCRB Estados Unidos'></picture>",
                    unsafe_allow_html=True,
                )

            with col_buttons:
                # El margen superior (sólo en pantallas anchas) centra los botones respecto al gráfico.
                st.html("<div class='heymann-espacio'></div>")

                # Botón Descargar Gráfico
                st.download_button(
                    label="Descargar Gráfico",
                    data=chart_png,
                    file_name="camello_heymann.png",
                    mime="image/png",
                    width="stretch"
                )

                st.write("") # Pequeño espacio entre botones

                # Botón Descargar Excel
                excel_single = utils.convert_single_sheet_to_excel(df_heymann, utils.SHEET_HEYMANN)
                st.download_button(
                    label="Descargar Datos",
                    data=excel_single,
                    file_name="ITCRB_Heymann.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    width="stretch"
                )
        else:
            st.error("Error al procesar los datos para el gráfico.")
    else:
        st.error("No se encontró en el inventario la serie mensual ITCRB Estados Unidos empalmada por el IIEP.")
