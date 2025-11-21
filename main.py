import streamlit as st
import pandas as pd
import plotly.express as px
import io
import os
import base64
from PIL import Image

# Rutas de archivos
FILE_PATH = 'bds/BD.xlsx'
LOGO_PATH = 'estetica/logo-iiep-macro.png'
DH_PATH = 'estetica/DH.png'

# --- CONFIGURACIÓN DE PAGINA E ICONO ---
page_icon = None
if os.path.exists(LOGO_PATH):
    try:
        img = Image.open(LOGO_PATH).convert("RGBA")
        background = Image.new("RGBA", img.size, (255, 255, 255, 255))
        page_icon = Image.alpha_composite(background, img)
    except:
        pass

st.set_page_config(
    layout="wide", 
    page_title="Series Económicas de Argentina",
    page_icon=page_icon
)

# --- CONFIGURACIÓN DE COLORES ---
COLOR_FONDO_NEGRO = "#000000"
COLOR_FONDO_LOGO = "#D3D3D3"
COLOR_TEXTO_BLANCO = "#FFFFFF"
COLOR_BOTONES_RANGO_TEXTO = "#FFFFFF" 
COLOR_BOTONES_RANGO_FONDO = "#444444"
COLOR_BOTONES_ACTIVO = "#FF6B35"
COLOR_SLIDER_BORDE = "#FF6B35"
COLOR_SLIDER_FONDO = "#f0f2f6"

# Paleta
PALETA_NARANJAS = [
    "#FF6B35", "#F7C59F", "#EF233C", "#D90429", 
    "#FF9F1C", "#FFBF69", "#CB997E", "#DDbea9"
]

# --- FUNCIONES AUXILIARES ---
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return ""

@st.cache_data
def load_metadata():
    if not os.path.exists(FILE_PATH):
        st.error(f"No se encontró el archivo en {FILE_PATH}. Ejecuta primero generar_mock_data.py")
        return None
    df = pd.read_excel(FILE_PATH, sheet_name=0)
    df.insert(0, "Seleccionar", False)
    return df

@st.cache_data
def load_all_data():
    return pd.read_excel(FILE_PATH, sheet_name=None)

def filter_data(df, search_text, search_id, tema_filter, freq_filter):
    dff = df.copy()
    if search_text:
        mask = (
            dff['Variable'].astype(str).str.contains(search_text, case=False, na=False) | 
            dff['Pestaña'].astype(str).str.contains(search_text, case=False, na=False)
        )
        dff = dff[mask]
    if search_id:
        dff = dff[dff['ID'].astype(str).str.contains(search_id, case=False, na=False)]
    if tema_filter != "Todos":
        dff = dff[dff['Tema'] == tema_filter]
    if freq_filter != "Todas":
        dff = dff[dff['Frecuencia'] == freq_filter]
    return dff

def convert_df_to_excel_filtered(metadata_selected, data_dict):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        meta_to_save = metadata_selected.drop(columns=['Seleccionar'], errors='ignore')
        meta_to_save.to_excel(writer, sheet_name='Indice', index=False)
        grouped = metadata_selected.groupby('Pestaña')
        for tab_name, group in grouped:
            if tab_name in data_dict:
                full_df = data_dict[tab_name].copy()
                if 'Fecha' not in full_df.columns and not full_df.empty:
                    full_df.rename(columns={full_df.columns[0]: 'Fecha'}, inplace=True)
                if 'Fecha' in full_df.columns:
                     full_df['Fecha'] = pd.to_datetime(full_df['Fecha'], errors='coerce')
                vars_to_keep = ['Fecha'] + [v for v in group['Variable'] if v in full_df.columns]
                filtered_tab_df = full_df[vars_to_keep].copy()
                filtered_tab_df.to_excel(writer, sheet_name=tab_name, index=False)
    return output.getvalue()

def get_full_excel_bytes():
    with open(FILE_PATH, "rb") as f:
        return f.read()

# --- MAIN ---
def main():
    # Manejo de estado
    if 'show_dh' not in st.session_state:
        st.session_state['show_dh'] = False
    if 'last_selection_hash' not in st.session_state:
        st.session_state['last_selection_hash'] = ""

    logo_b64 = get_base64_image(LOGO_PATH)

    # --- CSS ---
    st.markdown(f"""
        <style>
        /* --- OCULTAR ELEMENTOS NATIVOS DE STREAMLIT --- */
        
        /* Ocultar el Header superior (Menú hamburguesa, barra de estado, etc) */
        header[data-testid="stHeader"] {{
            visibility: hidden;
            height: 0px;
        }}
        
        /* Ocultar la decoración de colores superior */
        div[data-testid="stDecoration"] {{
            visibility: hidden;
            height: 0px;
        }}

        /* Ocultar el toolbar de opciones si aparece */
        div[data-testid="stToolbar"] {{
            visibility: hidden;
            height: 0px;
        }}

        /* --- AJUSTES DE ESPACIADO --- */
        
        /* Eliminar padding superior para que nuestra barra toque el techo */
        .block-container {{
            padding-top: 0rem !important;
            padding-bottom: 5rem !important; /* Espacio para footer */
            margin-top: 1rem !important; /* Pequeño margen para separar del borde físico del navegador */
        }}
        
        /* --- BARRA SUPERIOR PERSONALIZADA --- */
        [data-testid="stHorizontalBlock"] {{
            background-color: {COLOR_FONDO_NEGRO};
            padding: 5px 10px;
            border-radius: 6px;
            align-items: center !important; 
            min-height: 50px;
        }}
        
        div[data-testid="column"] {{
            display: flex !important;
            flex-direction: row !important;
            align-items: center !important; 
            height: 100%;
        }}

        .custom-header-title {{
            font-family: 'Source Sans Pro', sans-serif;
            font-weight: 600;
            font-size: 18px !important;
            color: {COLOR_TEXTO_BLANCO} !important;
            margin: 0;
            padding-left: 10px;
            line-height: 1; 
        }}
        
        div[data-testid="column"]:nth-of-type(3) button {{
            background-color: {COLOR_FONDO_NEGRO} !important; 
            color: {COLOR_TEXTO_BLANCO} !important;
            border: 1px solid {COLOR_TEXTO_BLANCO} !important; 
            font-size: 13px !important;
            padding: 4px 12px !important;
            margin: 0 !important;
            height: auto !important;
            min-height: 30px !important;
            line-height: 1 !important;
            white-space: nowrap;
        }}
        div[data-testid="column"]:nth-of-type(3) button:hover {{
            background-color: {COLOR_TEXTO_BLANCO} !important;
            color: {COLOR_FONDO_NEGRO} !important;
        }}

        .stDownloadButton button {{
            font-size: 14px !important;
            padding: 0.4rem 0.8rem !important; 
            height: auto !important;
            min-height: 0px !important;
            white-space: nowrap !important; 
        }}
        </style>
    """, unsafe_allow_html=True)

    # --- HEADER ---
    try:
        c_logo, c_title, c_btn = st.columns([0.8, 8, 1.5], gap="small", vertical_alignment="center")
    except TypeError:
        c_logo, c_title, c_btn = st.columns([0.8, 8, 1.5], gap="small")

    with c_logo:
        if logo_b64:
            st.markdown(f"""
                <div style="background-color: {COLOR_FONDO_LOGO}; border-radius: 4px; padding: 2px; display: flex; align-items: center; justify-content: center; height: 32px; width: 100%;">
                    <img src="data:image/png;base64,{logo_b64}" style="max-height: 28px; width: auto;">
                </div>
            """, unsafe_allow_html=True)
        else:
             st.markdown(f'<div style="background-color: {COLOR_FONDO_LOGO}; height: 32px; width: 100%; border-radius: 4px;"></div>', unsafe_allow_html=True)

    with c_title:
        st.markdown('<div class="custom-header-title">Series Económicas de Argentina</div>', unsafe_allow_html=True)
    
    with c_btn:
        if st.button("Daniel Heymann", use_container_width=True):
            st.session_state['show_dh'] = not st.session_state['show_dh']
            st.rerun()

    # Carga de datos
    df_index = load_metadata()
    if df_index is None: return
    all_data_sheets = load_all_data()

    chart_container = st.container()
    st.markdown("---") 

    # Filtros
    col1, col2, col3, col4 = st.columns(4)
    with col1: search_text = st.text_input("🔍 Buscar (Variable/Pestaña)", placeholder="ej. PBI...")
    with col2: search_id = st.text_input("🆔 Buscar por ID", placeholder="ej. PBI_NOM")
    with col3:
        temas = ["Todos"] + sorted(list(df_index['Tema'].unique()))
        tema_sel = st.selectbox("📂 Filtrar por Tema", temas)
    with col4:
        freqs = ["Todas"] + sorted(list(df_index['Frecuencia'].unique()))
        freq_sel = st.selectbox("⏰ Filtrar por Frecuencia", freqs)

    df_filtered = filter_data(df_index, search_text, search_id, tema_sel, freq_sel)
    edited_df = st.data_editor(
        df_filtered,
        column_config={
            "Seleccionar": st.column_config.CheckboxColumn("Graficar", default=False),
            "Fuente": st.column_config.LinkColumn("Fuente"),
        },
        disabled=["Tema", "Variable", "Frecuencia", "ID", "Pestaña", "Fuente"],
        hide_index=True, use_container_width=True, height=300
    )

    selected_rows = edited_df[edited_df["Seleccionar"] == True]
    
    current_selection_ids = sorted(selected_rows['ID'].astype(str).tolist())
    current_selection_hash = ",".join(current_selection_ids)
    
    if current_selection_hash != st.session_state['last_selection_hash']:
        st.session_state['show_dh'] = False
        st.session_state['last_selection_hash'] = current_selection_hash

    with chart_container:
        if st.session_state['show_dh']:
            if os.path.exists(DH_PATH):
                c1, c2, c3 = st.columns([1, 1, 1])
                with c2: st.image(DH_PATH, use_container_width=True)
            else: st.warning(f"No se encontró la imagen en {DH_PATH}")
        else:
            if not selected_rows.empty:
                plot_data = pd.DataFrame()
                for index, row in selected_rows.iterrows():
                    tab_name = row['Pestaña']
                    var_name = row['Variable']
                    if tab_name in all_data_sheets:
                        sheet_df = all_data_sheets[tab_name].copy()
                        if 'Fecha' not in sheet_df.columns and not sheet_df.empty:
                            sheet_df.rename(columns={sheet_df.columns[0]: 'Fecha'}, inplace=True)
                        if 'Fecha' in sheet_df.columns:
                            sheet_df['Fecha'] = pd.to_datetime(sheet_df['Fecha'], errors='coerce')
                            sheet_df = sheet_df.dropna(subset=['Fecha'])
                            if var_name in sheet_df.columns:
                                serie = sheet_df[['Fecha', var_name]].set_index('Fecha')
                                plot_data = serie if plot_data.empty else plot_data.join(serie, how='outer')
                
                if not plot_data.empty:
                    plot_data = plot_data.sort_index()
                    fig = px.line(plot_data, x=plot_data.index, y=plot_data.columns, color_discrete_sequence=PALETA_NARANJAS)
                    fig.update_layout(
                        hovermode="x unified", xaxis_title="", yaxis_title=None, legend_title="Variables",
                        template="plotly_white", margin=dict(l=0, r=0, t=20, b=0),
                        legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02),
                        xaxis=dict(
                            rangeslider=dict(visible=True, bgcolor=COLOR_SLIDER_FONDO, thickness=0.05, bordercolor=COLOR_SLIDER_BORDE, borderwidth=1),
                            type="date",
                            rangeselector=dict(
                                buttons=list([
                                    dict(count=1, label="1m", step="month", stepmode="backward"),
                                    dict(count=6, label="6m", step="month", stepmode="backward"),
                                    dict(count=1, label="YTD", step="year", stepmode="todate"),
                                    dict(count=1, label="1y", step="year", stepmode="backward"),
                                    dict(step="all", label="Todo")
                                ]),
                                bgcolor=COLOR_BOTONES_RANGO_FONDO, activecolor=COLOR_BOTONES_ACTIVO, font=dict(color=COLOR_BOTONES_RANGO_TEXTO)
                            )
                        )
                    )
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True, 'toImageButtonOptions': {'format': 'png', 'filename': 'grafico_series', 'height': 600, 'width': 1000, 'scale': 2}, 'displaylogo': False})
                    
                    excel_filtered = convert_df_to_excel_filtered(selected_rows, all_data_sheets)
                    excel_full = get_full_excel_bytes()
                    
                    b_void, b_col1, b_col2 = st.columns([6, 2, 2], gap="small") 
                    
                    with b_col1: st.download_button(label="Descargar Datos (Filtrados)", data=excel_filtered, file_name="series_filtradas.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
                    with b_col2: st.download_button(label="Descargar Datos (Completos)", data=excel_full, file_name="BD_completa.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
                else: st.warning("Las series seleccionadas no contienen datos válidos.")
            else: st.info("👆 Selecciona series abajo para comenzar.")

    st.markdown(f"""
        <style>
        .footer {{ position: fixed; left: 0; bottom: 0; width: 100%; background-color: {COLOR_FONDO_NEGRO}; color: #808080; text-align: center; padding: 5px; font-size: 0.8rem; border-top: 1px solid #333; z-index: 999; }}
        .footer a {{ color: #808080; text-decoration: none; font-weight: bold; }}
        .footer a:hover {{ color: #FFFFFF; text-decoration: underline; }}
        .main .block-container {{ padding-bottom: 40px; }}
        </style>
        <div class="footer"><a href="https://github.com/HermesBV" target="_blank">Salieris de Heymann (2025) GitHub/HermesBV</a></div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()