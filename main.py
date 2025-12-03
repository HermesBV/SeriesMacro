import streamlit as st
import locale
from PIL import Image
import os

# Importamos nuestros nuevos módulos
import utils
import view_macro
import view_heymann

# Configuración Locale
try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'es_ES')
    except:
        pass

# --- CONFIGURACIÓN DE PÁGINA ---
page_icon = None
if os.path.exists(utils.LOGO_PATH):
    try:
        img = Image.open(utils.LOGO_PATH).convert("RGBA")
        background = Image.new("RGBA", img.size, (255, 255, 255, 255))
        page_icon = Image.alpha_composite(background, img)
    except:
        pass

st.set_page_config(
    layout="wide", 
    page_title="Series Macro IIEP",
    page_icon=page_icon
)

# --- MAIN ---
def main():
    if 'view' not in st.session_state:
        st.session_state['view'] = 'macro'
    
    # --- ESTADO PERSISTENTE ---
    if 'selected_ids' not in st.session_state: st.session_state['selected_ids'] = set()
    for key in ['axes_config', 'visibility_map', 'color_map', 'chart_type_map']:
        if key not in st.session_state: st.session_state[key] = {}

    logo_b64 = utils.get_base64_image(utils.LOGO_PATH)

    # --- CSS GLOBAL ---
    st.markdown(f"""
        <style>
        header[data-testid="stHeader"] {{ visibility: hidden; height: 0px; }}
        div[data-testid="stDecoration"] {{ visibility: hidden; height: 0px; }}
        div[data-testid="stToolbar"] {{ visibility: hidden; height: 0px; }}

        .block-container {{
            padding-top: 0rem !important;
            padding-bottom: 5rem !important;
            margin-top: 1rem !important;
            background-color: {utils.COLOR_FONDO_PAGINA};
        }}
        
        [data-testid="stHorizontalBlock"] {{
            background-color: {utils.COLOR_FONDO_PAGINA};
            padding: 5px 10px;
            align-items: center !important; 
            min-height: 60px;
        }}
        
        .custom-header-title {{
            font-family: 'Source Sans Pro', sans-serif;
            font-weight: 700;
            font-size: 38px !important; 
            color: {utils.COLOR_TEXTO_PRINCIPAL} !important;
            margin: 0;
            padding-left: 15px;
            line-height: 1.1; 
        }}
        
        .logo-container {{
            background-color: {utils.COLOR_FONDO_LOGO}; 
            border-radius: 6px; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            height: 80px;
            width: 100%;
            padding: 5px;
        }}
        
        div[data-baseweb="input"] {{
            background-color: #333333 !important; color: white !important; border-color: #555 !important;
        }}
        
        div[data-testid="column"] button {{
           min-height: 35px; border: none; padding: 0px 5px;
        }}

        /* REGLA ESPECÍFICA PARA EL BOTÓN DEL ENCABEZADO (DANIEL HEYMANN / SERIES MACRO) */
        /* Apuntamos al tercer botón del primer bloque horizontal visible para hacerlo más grande */
        div[data-testid="stHorizontalBlock"]:nth-of-type(1) div[data-testid="column"]:nth-of-type(3) button p {{
            font-size: 1.6rem !important; /* Aumentado ~60% */
            font-weight: 600 !important;
        }}
        
        div[data-baseweb="popover"], div[data-testid="stColorPicker"] {{ padding: 0px; }}
        
        div[data-testid="stColorPicker"] > div {{
            padding: 0px; display: flex; align-items: center; justify-content: center;
        }}
        
        div[data-testid="stSelectbox"] > div > div {{
            min-height: 30px; padding-top: 0px; padding-bottom: 0px;
            background-color: transparent; border: 1px solid #444;
        }}

        .footer {{ position: fixed; left: 0; bottom: 0; width: 100%; background-color: {utils.COLOR_FONDO_PAGINA}; color: #888; text-align: center; padding: 5px; font-size: 0.8rem; border-top: 1px solid #333; z-index: 999; }}
        </style>
    """, unsafe_allow_html=True)

    # --- HEADER DINÁMICO ---
    if st.session_state['view'] == 'macro':
        title_text = "Series Macro IIEP"
        btn_text = "Daniel Heymann"
    else:
        title_text = "🐫" # Título actualizado con emoji
        btn_text = "Series Macro"
    
    try:
        c_logo, c_title, c_btn = st.columns([1.2, 7.8, 1.5], gap="medium", vertical_alignment="center")
    except TypeError:
        c_logo, c_title, c_btn = st.columns([1.2, 7.8, 1.5], gap="medium")

    with c_logo:
        if logo_b64:
            st.markdown(f"""<div class="logo-container"><img src="data:image/png;base64,{logo_b64}" style="max-height: 70px; width: auto;"></div>""", unsafe_allow_html=True)

    with c_title:
        st.markdown(f'<div class="custom-header-title">{title_text}</div>', unsafe_allow_html=True)
    
    with c_btn:
        if st.button(btn_text, use_container_width=True):
            st.session_state['view'] = 'other' if st.session_state['view'] == 'macro' else 'macro'
            st.rerun()

    st.markdown("---") 

    # --- CARGA DE DATOS CENTRALIZADA ---
    # Cargamos los datos una vez aquí y los pasamos a las vistas
    df_index = utils.load_metadata()
    if df_index is None: return
    all_data_sheets = utils.load_all_data()

    # --- ENRUTAMIENTO DE VISTAS ---
    if st.session_state['view'] == 'other':
        view_heymann.show(all_data_sheets)
    else:
        view_macro.show(df_index, all_data_sheets)

    st.markdown(f"""<div class="footer"><a href="https://github.com/HermesBV" target="_blank">Salieris de Heymann (2025) GitHub/HermesBV</a></div>""", unsafe_allow_html=True)

if __name__ == "__main__":
    main()