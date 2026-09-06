import streamlit as st
import locale
from PIL import Image
import os
import utils
import view_macro
import view_heymann

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

def main():
    if 'view' not in st.session_state: st.session_state['view'] = 'macro'
    if 'selected_ids' not in st.session_state: st.session_state['selected_ids'] = set()
    for key in ['axes_config', 'visibility_map', 'color_map', 'chart_type_map']:
        if key not in st.session_state: st.session_state[key] = {}

    logo_b64 = utils.get_base64_image(utils.LOGO_PATH)

    # --- CSS GLOBAL ACTUALIZADO ---
    st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
        
        * {{ font-family: 'Poppins', sans-serif !important; }}

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
        
        /* Banner Superior Blanco */
        [data-testid="stHorizontalBlock"]:first-of-type {{
            background-color: {utils.COLOR_BANNER_SUPERIOR} !important;
            padding: 10px 20px;
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
        div[data-baseweb="input"] > div {{
            background-color: #FFFFFF !important; border: 1px solid #545454 !important;
        }}
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

        /* REGLA ESPECÍFICA BOTÓN DEL ENCABEZADO */
        div[data-testid="stHorizontalBlock"]:nth-of-type(1) div[data-testid="column"]:nth-of-type(3) button p {{
            font-size: 1.6rem !important; font-weight: 600 !important;
        }}
        
        div[data-baseweb="popover"], div[data-testid="stColorPicker"] {{ padding: 0px; }}
        div[data-testid="stColorPicker"] > div {{ padding: 0px; display: flex; align-items: center; justify-content: center; }}

        .logo-link {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border-radius: 8px;
            padding: 3px 5px;
            transition: background-color 0.18s ease, transform 0.18s ease, opacity 0.18s ease;
        }}
        .logo-link:hover {{
            background-color: rgba(4, 156, 130, 0.08);
            transform: translateY(-1px);
            opacity: 0.92;
        }}
        .logo-link img {{
            display: block;
            max-height: 70px;
            width: auto;
        }}
        
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
    has_heymann_data = utils.SHEET_HEYMANN in sheet_names
    if st.session_state['view'] == 'other' and not has_heymann_data:
        st.session_state['view'] = 'macro'

    if st.session_state['view'] == 'macro':
        title_text = "Series Macro IIEP"
        btn_text = "Daniel Heymann"
    else:
        title_text = "🐫" 
        btn_text = "Series Macro"
    
    try: c_logo, c_title, c_btn = st.columns([1.2, 7.8, 1.5], gap="medium", vertical_alignment="center")
    except TypeError: c_logo, c_title, c_btn = st.columns([1.2, 7.8, 1.5], gap="medium")

    with c_logo:
        if logo_b64:
            st.markdown(
                f"""
                <div class="logo-container" style="display: flex; align-items: center; justify-content: center;">
                    <a class="logo-link" href="https://www.economicas.uba.ar/iiep/macro/" target="_blank" rel="noopener noreferrer" title="Ir a Macro IIEP">
                        <img src="data:image/png;base64,{logo_b64}" alt="Macro IIEP">
                    </a>
                </div>
                """,
                unsafe_allow_html=True
            )

    with c_title: st.markdown(f'<div class="custom-header-title">{title_text}</div>', unsafe_allow_html=True)
    with c_btn:
        if has_heymann_data and st.button(btn_text, width="stretch"):
            st.session_state['view'] = 'other' if st.session_state['view'] == 'macro' else 'macro'
            st.rerun()

    if st.session_state['view'] == 'other':
        view_heymann.show(utils.load_data_sheets((utils.SHEET_HEYMANN,)))
    else:
        view_macro.show(df_index)

    st.markdown(f"""<div class="footer">Salieris de Heymann (2025) - <a href="https://github.com/HermesBV" target="_blank">GitHub/HermesBV</a></div>""", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
