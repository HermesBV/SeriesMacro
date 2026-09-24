import streamlit as st
import pandas as pd
import os
import base64
import io
import zipfile

# --- CONFIGURACIÓN DE RUTAS Y CONSTANTES ---
FILE_PATH = 'bds/BD.xlsx'
INDEX_PATH = 'bds/IndiceSeries.xlsx'
LOGO_PATH = 'estetica/logo-iiep-macro.png'
SOURCE_HEYMANN = "iiep"
ID_HEYMANN = "itcrb-eeuu-empalmado-importacion-m"
SHEET_HEYMANN = "IIEP ITCRB EEUU M"

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
    'ID', 'Código fuente', 'Nombre serie', 'Variable', 'Unidades', 'Valoración', 'Descripción',
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
    def institucion(row):
        by_code = {
            'datos.gob.ar': 'INDEC / BCRA / otros organismos',
            'indec-sipm': 'INDEC', 'indec-emae': 'INDEC', 'indec-supermercados': 'INDEC',
            'indec-isac': 'INDEC', 'indec-ipi-manufacturero': 'INDEC', 'indec-ica': 'INDEC',
            'mecon-hacienda-caja': 'MECON', 'bcra-dmd': 'BCRA',
            'bcra-pas': 'BCRA', 'bcra-itc': 'BCRA', 'bcra-mc-bc': 'BCRA',
            'bcra-com3500': 'BCRA', 'bcra-bandas': 'BCRA', 'bcra': 'BCRA',
            'iiep': 'IIEP-UBA-CONICET',
        }
        source_code = str(row.get('Código fuente', '')).strip()
        if source_code in by_code and by_code[source_code] != 'INDEC / BCRA / otros organismos':
            return by_code[source_code]
        text = ' '.join(str(row.get(c, '')) for c in ['Responsable dataset', 'Origen']).casefold()
        if 'indec' in text or 'estadística y censos' in text:
            return 'INDEC'
        if 'banco central' in text or 'bcra' in text:
            return 'BCRA'
        if 'ministerio de econom' in text or 'secretaría de hacienda' in text or 'secretaria de hacienda' in text:
            return 'Ministerio de Economía'
        if 'iiep' in text or 'interdisciplinario de econom' in text:
            return 'IIEP-UBA-CONICET'
        value = row.get('Responsable dataset') or row.get('Origen')
        return str(value).strip() if pd.notna(value) and str(value).strip() else 'Sin informar'

    source = df['Código fuente'].fillna('').astype(str)
    broad = df['Tema dataset'].fillna('Sin clasificar').astype(str).str.strip()
    specific = df['Título dataset'].fillna('').astype(str).str.strip()
    df['Institución'] = df.apply(institucion, axis=1)
    def split_hierarchy(row):
        broad_value = str(row.get('Tema dataset') or '').strip()
        specific_value = str(row.get('Título dataset') or '').strip()
        code = str(row.get('Código fuente') or '').strip()
        if '/' in broad_value:
            parts = [part.strip() for part in broad_value.split('/') if part.strip()]
            institution_value = str(row.get('Institución') or '').strip()
            if parts and parts[0].casefold() == institution_value.casefold():
                parts = parts[1:]
            if not parts:
                return ('Sin clasificar', 'Sin clasificar')
            return (' / '.join(parts[:-1]) or parts[0], parts[-1])
        if code in {'bcra-dmd', 'bcra-pas'}:
            return (specific_value or broad_value, broad_value or specific_value)
        area = broad_value or 'Sin clasificar'
        # El título del dataset mantiene la separación de apéndices y productos.
        topic = specific_value or broad_value or 'Sin clasificar'
        return area, topic

    hierarchy = df.apply(split_hierarchy, axis=1, result_type='expand')
    df['Área'] = hierarchy[0]
    df['Tema'] = hierarchy[1]
    df['Frecuencia código'] = df['Frecuencia'].astype(str).str.strip()
    df['Frecuencia'] = df['Frecuencia código'].map(frequency_names).fillna(df['Frecuencia código'])
    df = df.rename(columns={'Pestaña BD': 'Pestaña'})
    df['Detalle'] = df['Descripción'].fillna('').astype(str).str.strip()

    # Algunos catálogos publican dos series con exactamente los mismos metadatos
    # visibles. En esos casos el ID nativo es la única diferencia verificable.
    visible_columns = [
        'Nombre serie', 'Detalle', 'Unidades', 'Valoración', 'Tema', 'Frecuencia',
    ]
    visual_key = df[visible_columns].fillna('').astype(str).apply(
        lambda column: column.str.replace(r'\s+', ' ', regex=True).str.strip().str.casefold()
    )
    ambiguous = visual_key.duplicated(keep=False)
    suffix = ' · ID: ' + df['ID'].astype(str).str.strip()
    df.loc[ambiguous, 'Detalle'] = df.loc[ambiguous, 'Detalle'] + suffix.loc[ambiguous]
    df['_Clave'] = df['Código fuente'].astype(str).str.strip() + '::' + df['ID'].astype(str).str.strip()
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


def _database_version():
    """Devuelve una huella barata que cambia cuando se reemplaza la base."""
    data_stat = os.stat(FILE_PATH)
    index_stat = os.stat(INDEX_PATH)
    return data_stat.st_mtime_ns, data_stat.st_size, index_stat.st_mtime_ns, index_stat.st_size


@st.cache_data
def _load_metadata(database_version):
    if not os.path.exists(FILE_PATH):
        st.error(f"No se encontró el archivo en {FILE_PATH}.")
        return None
    if not os.path.exists(INDEX_PATH):
        st.error(f"No se encontró el índice en {INDEX_PATH}.")
        return None
    with pd.ExcelFile(FILE_PATH) as excel_file, pd.ExcelFile(INDEX_PATH) as index_file:
        df = _load_coded_metadata(index_file)
        if df is None:
            raise ValueError(
                "El índice no contiene la hoja 'Codificacion' con el esquema esperado."
            )
        df = _only_chartable_series(df, excel_file)
    df['ID'] = df['ID'].astype(str).str.strip()
    if df['ID'].eq('').any() or df.duplicated(['Código fuente', 'ID']).any():
        raise ValueError("La hoja de codificación contiene claves de fuente e ID vacías o duplicadas.")
    return df


def load_metadata():
    return _load_metadata(_database_version())


@st.cache_data
def _load_sheet_names(database_version):
    with pd.ExcelFile(FILE_PATH) as excel_file:
        return tuple(excel_file.sheet_names)


def load_sheet_names():
    return _load_sheet_names(_database_version())


@st.cache_data
def _load_data_sheets(sheet_names, database_version):
    names = [name for name in dict.fromkeys(sheet_names) if name]
    return pd.read_excel(FILE_PATH, sheet_name=names) if names else {}


def load_data_sheets(sheet_names):
    return _load_data_sheets(sheet_names, _database_version())


@st.cache_data
def _load_heymann_data(database_version):
    """Obtiene la serie mensual bilateral con EE.UU. desde el inventario maestro."""
    with pd.ExcelFile(FILE_PATH) as excel_file:
        metadata = pd.read_excel(INDEX_PATH, sheet_name='Codificacion')
        row = metadata.loc[
            metadata['Código fuente'].astype(str).str.strip().eq(SOURCE_HEYMANN)
            & metadata['ID'].astype(str).str.strip().eq(ID_HEYMANN)
        ]
        if len(row) != 1:
            return None
        sheet = str(row.iloc[0]['Pestaña BD']).strip()
        column = str(row.iloc[0]['Columna BD']).strip()
        if sheet not in excel_file.sheet_names:
            return None
        data = pd.read_excel(excel_file, sheet_name=sheet)
    if data.empty or column not in data.columns:
        return None
    result = data.iloc[:, [0]].copy()
    result[column] = pd.to_numeric(data[column], errors='coerce')
    result.iloc[:, 0] = pd.to_datetime(result.iloc[:, 0], errors='coerce')
    return result.dropna().sort_values(result.columns[0]).reset_index(drop=True)


def load_heymann_data():
    return _load_heymann_data(_database_version())

def get_full_database_archive():
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(FILE_PATH, arcname='BD.xlsx')
        archive.write(INDEX_PATH, arcname='IndiceSeries.xlsx')
    return output.getvalue()

# --- FUNCIONES DE FILTRADO Y EXPORTACIÓN ---
def filter_data(df, search_text, institution_filter, area_filter, topic_filter, freq_filter):
    dff = df.copy()
    if search_text:
        mask = (
            dff['Nombre serie'].astype(str).str.contains(search_text, case=False, na=False) |
            dff['Variable'].astype(str).str.contains(search_text, case=False, na=False) |
            dff['Detalle'].astype(str).str.contains(search_text, case=False, na=False) |
            dff['Pestaña'].astype(str).str.contains(search_text, case=False, na=False) |
            dff['Institución'].astype(str).str.contains(search_text, case=False, na=False) |
            dff['Área'].astype(str).str.contains(search_text, case=False, na=False) |
            dff['Tema'].astype(str).str.contains(search_text, case=False, na=False)
        )
        dff = dff[mask]
    if institution_filter != "Todas":
        dff = dff[dff['Institución'] == institution_filter]
    if area_filter != "Todas":
        dff = dff[dff['Área'] == area_filter]
    if topic_filter != "Todos":
        dff = dff[dff['Tema'] == topic_filter]
    if freq_filter != "Todas":
        dff = dff[dff['Frecuencia'] == freq_filter]
    return dff

def convert_df_to_excel_filtered(metadata_selected, data_dict):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        meta_to_save = metadata_selected.drop(columns=['Seleccionar', 'Fuente_Label', '_Clave'], errors='ignore')
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
