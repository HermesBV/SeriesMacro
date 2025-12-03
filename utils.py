import streamlit as st
import pandas as pd
import os
import base64
import io

# --- CONFIGURACIÓN DE RUTAS Y CONSTANTES ---
FILE_PATH = 'bds/BD.xlsx'
LOGO_PATH = 'estetica/logo-iiep-macro.png'
ID_HEYMANN = "ITCRB_USA_M"
SHEET_HEYMANN = "ITCRB M"

# --- CONFIGURACIÓN DE COLORES ---
COLOR_FONDO_PAGINA = "#000000"
COLOR_TEXTO_PRINCIPAL = "#FFFFFF"
COLOR_FONDO_LOGO = "#F0F0F0" 
COLOR_BOTONES_ACTIVO = "#FF6B35"
COLOR_SLIDER_BORDE = "#FF6B35"
COLOR_BOTONES_RANGO_FONDO = "#444444"
COLOR_BOTONES_RANGO_TEXTO = "#FFFFFF"

# Paleta Inicial
PALETA_NARANJAS = [
    "#FF6B35", "#F7C59F", "#EF233C", "#D90429", 
    "#FF9F1C", "#FFBF69", "#CB997E", "#DDbea9",
    "#3D5A80", "#98C1D9"
]

# --- FUNCIONES DE CARGA DE DATOS ---
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return ""

@st.cache_data
def load_metadata():
    if not os.path.exists(FILE_PATH):
        st.error(f"No se encontró el archivo en {FILE_PATH}.")
        return None
    df = pd.read_excel(FILE_PATH, sheet_name=0)
    df['ID'] = df['ID'].astype(str)
    return df

@st.cache_data
def load_all_data():
    return pd.read_excel(FILE_PATH, sheet_name=None)

def get_full_excel_bytes():
    with open(FILE_PATH, "rb") as f:
        return f.read()

# --- FUNCIONES DE FILTRADO Y EXPORTACIÓN ---
def filter_data(df, search_text, tema_filter, freq_filter):
    # Exclusión de la serie Heymann del buscador general
    dff = df[df['ID'] != ID_HEYMANN].copy()
    
    if search_text:
        mask = (
            dff['Variable'].astype(str).str.contains(search_text, case=False, na=False) | 
            dff['Pestaña'].astype(str).str.contains(search_text, case=False, na=False)
        )
        dff = dff[mask]
    if tema_filter != "Todos":
        dff = dff[dff['Tema'] == tema_filter]
    if freq_filter != "Todas":
        dff = dff[dff['Frecuencia'] == freq_filter]
    return dff

def convert_df_to_excel_filtered(metadata_selected, data_dict):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        meta_to_save = metadata_selected.drop(columns=['Seleccionar', 'Fuente_Label'], errors='ignore')
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

def convert_single_sheet_to_excel(df, sheet_name):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
    return output.getvalue()