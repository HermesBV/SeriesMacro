import streamlit as st
import locale
from PIL import Image
import os
import utils
import view_macro
import view_heymann
import view_mapa_datos
import view_iiep

try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except:
    try: locale.setlocale(locale.LC_TIME, 'es_ES')
    except: pass

page_icon = None
if os.path.exists(utils.LOGO_PATH):
    try:
        img = Image.open(utils.LOGO_PATH).convert("RGBA")
        background = Image.new("RGBA", img.size, (255, 255, 255, 255))
        page_icon = Image.alpha_composite(background, img)
    except: pass

st.set_page_config(layout="wide", page_title="Series Macro IIEP", page_icon=page_icon)

VIEWS = ('macro', 'iiep', 'other', 'map')


def main():
    if 'view' not in st.session_state:
        # Enlace directo: ?vista=iiep&grupo=reservas abre esa vista al cargar.
        requested = st.query_params.get('vista')
        st.session_state['view'] = requested if requested in VIEWS else 'macro'
    if 'selected_ids' not in st.session_state: st.session_state['selected_ids'] = set()
    for key in ['axes_config', 'visibility_map', 'color_map', 'chart_type_map']:
        if key not in st.session_state: st.session_state[key] = {}

    logo_b64 = utils.get_base64_image(utils.LOGO_PATH)

    # --- CSS GLOBAL ACTUALIZADO ---
    st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
        
        * {{ font-family: 'Poppins', sans-serif !important; }}
        /* Los íconos de Streamlit usan una fuente de símbolos: sin esta excepción se ve
           el nombre del ícono (p. ej. «keyboard_arrow_right») encima del texto. */
        [data-testid="stIconMaterial"], .material-symbols-rounded {{
            font-family: 'Material Symbols Rounded' !important;
        }}

        header[data-testid="stHeader"], div[data-testid="stDecoration"], div[data-testid="stToolbar"] {{ 
            visibility: hidden; height: 0px; 
        }}

        /* Fondo general Gris de la página */
        .stApp {{ background-color: {utils.COLOR_FONDO_PAGINA}; }}
        
        .block-container {{
            padding-top: 0rem !important;
            padding-bottom: 1.5rem !important;
            margin-top: 1rem !important;
            background-color: transparent; 
        }}
        
        /* Banner Superior Blanco. Se limita al contenedor del encabezado: el selector
           «stHorizontalBlock:first-of-type» también tomaba el primer bloque de columnas
           de cada sección (filtros, tarjetas, descargas) y los desplazaba. */
        .st-key-encabezado {{
            background-color: {utils.COLOR_BANNER_SUPERIOR} !important;
            padding: 10px 0;
            border-radius: 0px;
            margin-top: -4rem;
            padding-top: 3rem;
            margin-bottom: 1.35rem;
        }}
        
        .custom-header-title {{
            font-weight: 700; font-size: 38px !important; color: {utils.COLOR_TEXTO_PRINCIPAL} !important;
            margin: 0; padding-left: 15px; line-height: 1.1; 
        }}
        
        /* Buscadores: Fondo blanco, texto negro, placeholder gris */
        div[data-baseweb="input"] {{
            border: 1px solid #545454 !important; border-radius: 0.5rem !important;
            background-color: #FFFFFF !important; min-height: 40px;
        }}
        div[data-baseweb="input"] > div {{ background-color: #FFFFFF !important; border: none !important; }}
        div[data-baseweb="input"] input {{
            color: #000000 !important;
        }}
        div[data-baseweb="input"] input::placeholder {{
            color: #545454 !important;
        }}
        
        /* Selectbox buscadores */
        div[data-baseweb="select"] > div {{
            background-color: #FFFFFF !important; color: #000000 !important; border: 1px solid #545454 !important;
        }}
        div[data-baseweb="popover"] [role="option"],
        div[data-baseweb="popover"] [role="listbox"] {{
            font-family: 'Poppins', sans-serif !important;
            font-size: 0.9rem !important;
            line-height: 1.35 !important;
            font-weight: 400 !important;
            filter: none !important;
            transform: none !important;
        }}
        [role="menu"] {{ min-width: 210px !important; padding: 6px !important; }}
        [role="menuitem"] {{
            min-height: 34px !important;
            padding: 7px 12px !important;
            font-family: 'Poppins', sans-serif !important;
            font-size: 0.9rem !important;
            line-height: 1.25 !important;
            white-space: nowrap !important;
            filter: none !important;
            transform: none !important;
        }}
        
        /* Botones Verdes por defecto */
        div.stButton > button,
        div.stDownloadButton > button {{
            background-color: {utils.COLOR_SLIDER_BORDE} !important;
            color: #FFFFFF !important;
            border: none !important;
        }}
        div.stButton > button:hover,
        div.stDownloadButton > button:hover {{
            background-color: #037a66 !important;
            color: #FFFFFF !important;
            border: none !important;
        }}
        div.stButton > button p,
        div.stDownloadButton > button p {{
            color: #FFFFFF !important;
        }}

        /* Hacking visual para DataFrames de Streamlit (Forzar fondo blanco y texto negro) */
        [data-testid="stDataFrame"], div[data-testid="stDataEditor"] {{
            background-color: #FFFFFF !important;
        }}
        /* Nota: Para que el interior de la tabla sea completamente claro, es recomendable asegurar que el Theme 
           en Configuración de Streamlit esté en 'Light', ya que Glide Data Grid usa un Canvas HTML. */

        div[data-baseweb="popover"], div[data-testid="stColorPicker"] {{ padding: 0px; }}
        div[data-testid="stColorPicker"] > div {{ padding: 0px; display: flex; align-items: center; justify-content: center; }}

        .logo-link {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border-radius: 8px;
            padding: 3px 0;
            transition: background-color 0.18s ease, transform 0.18s ease, opacity 0.18s ease;
        }}
        .logo-link:hover {{
            background-color: rgba(4, 156, 130, 0.08);
            transform: translateY(-1px);
            opacity: 0.92;
        }}
        /* Logo de ancho fijo: no depende de la proporción de la columna en cada ancho. */
        .logo-link img {{
            display: block;
            height: 58px;
            width: auto;
            max-width: none !important;
        }}

        /* Navegación del encabezado: las cuatro vistas siempre en el mismo orden,
           sin cortar palabras y con la vista actual marcada. */
        .st-key-navegacion div.stButton > button {{
            min-height: 2.6rem; padding: 0.3rem 0.6rem; white-space: nowrap;
        }}
        .st-key-navegacion div.stButton > button p {{
            font-size: 1rem !important; font-weight: 600 !important; white-space: nowrap !important;
        }}
        /* Hasta 1320 px la navegación no entra al lado del título: pasa a una fila propia. */
        @media (max-width: 1320px) {{
            .st-key-encabezado [data-testid="stHorizontalBlock"] {{
                flex-wrap: wrap !important; flex-direction: row !important; row-gap: 0.9rem !important;
            }}
            .st-key-encabezado [data-testid="stColumn"] {{ min-width: 0 !important; width: auto !important; }}
            .st-key-encabezado [data-testid="stColumn"]:has(.logo-link) {{ flex: 0 0 auto !important; }}
            .st-key-encabezado [data-testid="stColumn"]:has(.custom-header-title) {{ flex: 1 1 60% !important; }}
            .st-key-encabezado [data-testid="stColumn"]:has(.st-key-navegacion) {{ flex: 1 1 100% !important; }}
            .st-key-navegacion [data-testid="stHorizontalBlock"] {{ flex-wrap: wrap !important; gap: 0.5rem !important; }}
            .st-key-navegacion [data-testid="stColumn"] {{ flex: 1 1 20% !important; min-width: 0 !important; }}
        }}
        /* En celulares: título más chico y navegación en grilla de 2×2. */
        @media (max-width: 640px) {{
            .st-key-encabezado {{ margin-bottom: 0.6rem; }}
            .main h2, .main h3, [data-testid="stHeading"] h2, [data-testid="stHeading"] h3 {{ font-size: 1.3rem !important; }}
            .st-key-encabezado [data-testid="stColumn"]:has(.logo-link) {{ flex: 0 0 auto !important; }}
            .st-key-navegacion [data-testid="stColumn"] {{ flex: 1 1 45% !important; }}
            .custom-header-title {{ font-size: 1.55rem !important; padding-left: 0.2rem; line-height: 1.15; }}
            .logo-link img {{ height: 44px; }}
            .st-key-encabezado [data-testid="stColumn"]:has(.logo-link) {{ margin-bottom: 0.3rem; }}
            .st-key-navegacion div.stButton > button {{ min-height: 2.3rem; padding: 0.2rem 0.3rem; }}
            .st-key-navegacion div.stButton > button p {{ font-size: 0.85rem !important; }}
        }}
        /* Textos auxiliares (contadores, ayudas) con contraste suficiente. */
        [data-testid="stCaptionContainer"] {{ opacity: 1 !important; }}
        [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {{ color: #5f6368 !important; }}
        /* Footer al final de la pagina */
        .footer {{ 
            position: relative;
            width: 100%;
            box-sizing: border-box;
            background-color: #FFFFFF;
            color: #555555;
            text-align: center; 
            padding: 10px;
            margin-top: 2rem;
            font-size: 0.85rem;
            border: 1px solid #E0E0E0;
            border-radius: 2px;
        }}
        .footer a {{
            color: {utils.COLOR_SLIDER_BORDE} !important;
            font-weight: 600;
            text-decoration: none;
        }}
        .footer a:hover {{ text-decoration: underline; }}
        </style>
    """, unsafe_allow_html=True)

    df_index = utils.load_metadata()
    if df_index is None:
        return
    sheet_names = utils.load_sheet_names()
    has_heymann_data = (
        df_index['Código fuente'].astype(str).eq(utils.SOURCE_HEYMANN)
        & df_index['ID'].astype(str).eq(utils.ID_HEYMANN)
    ).any()
    if has_heymann_data:
        view_heymann.preload_chart()
    if st.session_state['view'] == 'other' and not has_heymann_data:
        st.session_state['view'] = 'macro'
    # La URL refleja lo que se ve: sin vistas inválidas ni grupos fuera de Indicadores IIEP.
    if st.session_state['view'] == 'macro':
        st.query_params.pop('vista', None)
    elif st.query_params.get('vista') != st.session_state['view']:
        st.query_params['vista'] = st.session_state['view']
    if st.session_state['view'] != 'iiep':
        st.query_params.pop('grupo', None)

    current_view = st.session_state['view']
    title_text = {
        'macro': "Series Macro IIEP",
        'other': "🐫",
        'map': "Mapa de Datos",
        'iiep': "Indicadores IIEP",
    }.get(current_view, "Series Macro IIEP")
    nav_labels = {
        'macro': "Series Macro", 'iiep': "Indicadores IIEP",
        'other': "Daniel Heymann", 'map': "Mapa de Datos",
    }
    nav_targets = [target for target in nav_labels if target != 'other' or has_heymann_data]

    # La vista actual queda marcada (contorno verde) en lugar de desaparecer de la barra.
    st.markdown(f"""<style>
        .st-key-nav_{current_view} div.stButton > button,
        .st-key-nav_{current_view} div.stButton > button:hover {{
            background-color: #FFFFFF !important; border: 2px solid {utils.COLOR_SLIDER_BORDE} !important;
            cursor: default !important; opacity: 1 !important;
        }}
        .st-key-nav_{current_view} div.stButton > button p {{ color: {utils.COLOR_SLIDER_BORDE} !important; }}
        </style>""", unsafe_allow_html=True)

    header = st.container(key="encabezado")
    with header:
        try: c_logo, c_title, c_nav = st.columns([1.1, 3.9, 6.6], gap="medium", vertical_alignment="center")
        except TypeError: c_logo, c_title, c_nav = st.columns([1.1, 3.9, 6.6], gap="medium")

    with c_logo:
        if logo_b64:
            st.markdown(
                f"""
                <div class="logo-container" style="display: flex; align-items: center; justify-content: flex-start;">
                    <a class="logo-link" href="https://www.economicas.uba.ar/iiep/macro/" target="_blank" rel="noopener noreferrer" title="Ir a Macro IIEP">
                        <img src="data:image/png;base64,{logo_b64}" alt="Macro IIEP">
                    </a>
                </div>
                """,
                unsafe_allow_html=True
            )

    with c_title: st.markdown(f'<div class="custom-header-title">{title_text}</div>', unsafe_allow_html=True)
    with c_nav:
        with st.container(key="navegacion"):
            for column, target in zip(st.columns(len(nav_targets), gap="small"), nav_targets):
                with column:
                    if st.button(nav_labels[target], width="stretch", key=f"nav_{target}",
                                 disabled=target == current_view):
                        st.session_state['view'] = target
                        st.query_params.clear()
                        if target != 'macro':
                            st.query_params['vista'] = target
                        st.rerun()

    if st.session_state['view'] == 'other':
        view_heymann.show(utils.load_heymann_data())
    elif st.session_state['view'] == 'map':
        view_mapa_datos.show(df_index)
    elif st.session_state['view'] == 'iiep':
        view_iiep.show(df_index)
    else:
        view_macro.show(df_index)

    st.markdown(f"""<div class="footer">Salieris de Heymann (2025) - <a href="https://github.com/HermesBV" target="_blank">GitHub/HermesBV</a></div>""", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
