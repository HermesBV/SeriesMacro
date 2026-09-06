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

# --- CONFIGURACIÓN DE COLORES (NUEVA PALETA) ---
COLOR_FONDO_PAGINA = "#FFFFFF"     
COLOR_BANNER_SUPERIOR = "#FFFFFF"  
COLOR_TEXTO_PRINCIPAL = "#000000"  
COLOR_BOTONES_ACTIVO = "#f05f30"   
COLOR_SLIDER_BORDE = "#049c82"     
COLOR_BOTONES_RANGO_FONDO = "#FFFFFF"
COLOR_BOTONES_RANGO_TEXTO = "#000000"

# Paleta Principal: Naranja, Verde, Azul, Rojo, Amarillo
PALETA_COLORES = [
    "#f05f30", "#049c82", "#3774AC", "#bc2f29", "#d5cd65"
]

# --- FUNCIONES DE CARGA DE DATOS ---
CODED_METADATA_COLUMNS = {
    'ID', 'Código fuente', 'ID origen', 'Nombre serie', 'Variable', 'Unidades', 'Valoración', 'Descripción',
    'Frecuencia', 'Pestaña BD', 'Columna BD', 'Origen', 'Tema dataset', 'Estado', 'Fuente',
}


def _load_coded_metadata(excel_file):
    """Carga el inventario plano generado por SeriesScraper."""
    if 'Codificacion' not in excel_file.sheet_names:
        return None

    df = pd.read_excel(excel_file, sheet_name='Codificacion')

    if not CODED_METADATA_COLUMNS.issubset(df.columns):
        return None

    frequency_names = {
        'A': 'Anual', 'S': 'Semestral', 'T': 'Trimestral',
        'M': 'Mensual', 'D': 'Diaria', 'I': 'Irregular',
    }
    df['Tema'] = df['Tema dataset'].fillna(df['Origen']).fillna('Sin clasificar')
    df['Frecuencia código'] = df['Frecuencia'].astype(str).str.strip()
    df['Frecuencia'] = df['Frecuencia código'].map(frequency_names).fillna(df['Frecuencia código'])
    df = df.rename(columns={'Pestaña BD': 'Pestaña'})
    return df


def _only_chartable_series(df, excel_file):
    """Separa series numéricas de entradas documentales como Comunicaciones BCRA."""
    sheet_names = set(excel_file.sheet_names)
    return df[
        df['Pestaña'].isin(sheet_names)
        & df['Columna BD'].notna()
        & df['Columna BD'].astype(str).str.strip().ne('')
    ].copy()


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
    with pd.ExcelFile(FILE_PATH) as excel_file:
        df = _load_coded_metadata(excel_file)
        if df is None:
            raise ValueError(
                "El Excel no contiene la hoja 'Codificacion' con el esquema esperado."
            )
        df = _only_chartable_series(df, excel_file)
    df['ID'] = df['ID'].astype(str).str.strip()
    if df['ID'].eq('').any() or df['ID'].duplicated().any():
        raise ValueError("La hoja de codificación contiene IDs vacíos o duplicados.")
    return df

@st.cache_data
def load_sheet_names():
    with pd.ExcelFile(FILE_PATH) as excel_file:
        return tuple(excel_file.sheet_names)


@st.cache_data
def load_data_sheets(sheet_names):
    names = [name for name in dict.fromkeys(sheet_names) if name]
    return pd.read_excel(FILE_PATH, sheet_name=names) if names else {}

def get_full_excel_bytes():
    with open(FILE_PATH, "rb") as f:
        return f.read()

# --- FUNCIONES DE FILTRADO Y EXPORTACIÓN ---
def filter_data(df, search_text, tema_filter, freq_filter):
    dff = df[df['ID'] != ID_HEYMANN].copy()
    if search_text:
        mask = (
            dff['Nombre serie'].astype(str).str.contains(search_text, case=False, na=False) |
            dff['Variable'].astype(str).str.contains(search_text, case=False, na=False) |
            dff['Descripción'].astype(str).str.contains(search_text, case=False, na=False) |
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
                vars_to_keep = ['Fecha'] + [v for v in group['Columna BD'] if v in full_df.columns]
                filtered_tab_df = full_df[vars_to_keep].copy()
                filtered_tab_df.to_excel(writer, sheet_name=tab_name, index=False)
    return output.getvalue()

def convert_single_sheet_to_excel(df, sheet_name):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
    return output.getvalue()
