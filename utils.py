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
    'ID', 'Código fuente', 'Nombre serie', 'Variable', 'Valoración', 'Descripción',
    'Frecuencia', 'Pestaña BD', 'Columna BD', 'Origen', 'Tema dataset', 'Estado', 'Fuente',
}


def _load_coded_metadata(excel_file):
    """Carga el inventario plano generado por SeriesScraper."""
    if 'Codificacion' not in excel_file.sheet_names:
        return None

    df = pd.read_excel(excel_file, sheet_name='Codificacion')

    if not CODED_METADATA_COLUMNS.issubset(df.columns):
        return None

    if 'Unidad' not in df.columns and 'Unidades' not in df.columns:
        return None

    frequency_names = {
        'A': 'Anual', 'S': 'Semestral', 'T': 'Trimestral',
        'M': 'Mensual', 'D': 'Diaria', 'I': 'Irregular',
    }
    # La clasificación se registra en Codificacion y no se infiere de títulos de dataset.
    if 'Institución' not in df.columns:
        code = df['Código fuente'].fillna('').astype(str).str.strip()
        owners = df.get('Responsable dataset', pd.Series('', index=df.index)).fillna('').astype(str).str.casefold()
        df['Institución'] = 'Sin clasificar'
        df.loc[code.str.startswith('indec-') | owners.str.contains('indec'), 'Institución'] = 'INDEC'
        df.loc[code.str.startswith('bcra') | owners.str.contains('banco central'), 'Institución'] = 'BCRA'
        df.loc[code.str.startswith('mecon-') | owners.str.contains('hacienda|ministerio de econom'), 'Institución'] = 'MECON'
        df.loc[code.eq('iiep'), 'Institución'] = 'IIEP'
    for column in ['Área', 'Subárea 1', 'Subárea 2', 'Subárea 3']:
        if column not in df.columns:
            df[column] = ''
    if 'Tema' not in df.columns:
        df['Tema'] = df['Tema dataset'].fillna('Sin clasificar').astype(str).str.strip()
    df['Tema'] = df['Tema'].fillna('').astype(str).str.strip()
    df.loc[df['Tema'].str.casefold().eq('tipo de cambio'), 'Tema'] = 'Sector externo'
    df.loc[df['Tema'].eq(''), 'Tema'] = 'Sin clasificar'
    df['Frecuencia código'] = df['Frecuencia'].astype(str).str.strip()
    df['Frecuencia'] = df['Frecuencia código'].map(frequency_names).fillna(df['Frecuencia código'])
    df = df.rename(columns={'Pestaña BD': 'Pestaña', 'Unidades': 'Unidad'})
    def format_period(value, code):
        date = pd.to_datetime(value, errors='coerce')
        if pd.isna(date):
            return ''
        if code == 'A':
            return date.strftime('%Y')
        if code == 'S':
            return date.strftime('%Y-01' if date.month <= 6 else '%Y-07')
        if code == 'T':
            month = ((date.month - 1) // 3) * 3 + 1
            return f'{date.year:04d}-{month:02d}'
        if code == 'M':
            return date.strftime('%Y-%m')
        return date.strftime('%Y-%m-%d')
    codes = df['Frecuencia código'].astype(str).str.strip()
    if 'Desde' not in df.columns:
        df['Desde'] = [format_period(value, code) for value, code in zip(df.get('Fecha inicio'), codes)]
    if 'Hasta' not in df.columns:
        df['Hasta'] = [format_period(value, code) for value, code in zip(df.get('Fecha fin'), codes)]

    def build_detail(row):
        description = str(row['Descripción']).strip() if pd.notna(row['Descripción']) else ''
        if len(description) >= 45:
            return description
        parts = [description] if description else []
        dataset = str(row['Título dataset']).strip() if pd.notna(row.get('Título dataset')) else ''
        unit = str(row['Unidad']).strip() if pd.notna(row.get('Unidad')) else ''
        start = str(row['Desde']).strip() if pd.notna(row.get('Desde')) else ''
        end = str(row['Hasta']).strip() if pd.notna(row.get('Hasta')) else ''
        if dataset and dataset.casefold() not in description.casefold():
            parts.append(f'Conjunto: {dataset}')
        if unit and unit.casefold() not in description.casefold() and unit != 'Ver descripción de la serie':
            parts.append(f'Unidad: {unit}')
        if start and end and start != end:
            parts.append(f'Período: {start}–{end}')
        return ' · '.join(parts)

    df['Detalle'] = df.apply(build_detail, axis=1)

    # Algunos catálogos publican dos series con exactamente los mismos metadatos
    # visibles. En esos casos el ID nativo es la única diferencia verificable.
    visible_columns = [
        'Nombre serie', 'Detalle', 'Unidad', 'Valoración', 'Tema', 'Frecuencia',
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
    chartable = df[
        df['Pestaña'].isin(sheet_names)
        & df['Columna BD'].notna()
        & df['Columna BD'].astype(str).str.strip().ne('')
    ].copy()
    # Hacienda queda en pausa hasta que se reemplace su scraper. Mantener
    # registros y datos locales permite retomarlos, pero no ofrecerlos en la web.
    source_code = chartable['Código fuente'].fillna('').astype(str).str.casefold()
    catalog_id = chartable.get('Catálogo ID', pd.Series('', index=chartable.index)).fillna('').astype(str).str.casefold()
    dataset_id = chartable.get('Dataset ID', pd.Series('', index=chartable.index)).fillna('').astype(str).str.casefold()
    dataset_title = chartable.get('Título dataset', pd.Series('', index=chartable.index)).fillna('').astype(str).str.casefold()
    owner = chartable.get('Responsable dataset', pd.Series('', index=chartable.index)).fillna('').astype(str).str.casefold()
    paused_hacienda = (
        source_code.eq('mecon-hacienda-caja')
        | (catalog_id.eq('sspm') & dataset_id.eq('452'))
        | dataset_title.str.contains('informe mensual de ingresos y gastos del sector público nacional no financiero', regex=False)
        | owner.str.contains('secretaría de hacienda', regex=False)
    )
    return chartable.loc[~paused_hacienda].copy()


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


def sort_classification_values(values):
    """Ubica los valores sin clasificación al final de los selectores."""
    return sorted(values, key=lambda value: (str(value).casefold() == 'sin clasificar', str(value).casefold()))


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
def filter_data(df, search_text, institution_filter, hierarchy_filters, topic_filter, freq_filter, valuation_filter="Todas"):
    dff = df.copy()
    if search_text:
        mask = (
            dff['Nombre serie'].astype(str).str.contains(search_text, case=False, na=False) |
            dff['Detalle'].astype(str).str.contains(search_text, case=False, na=False) |
            dff['Institución'].astype(str).str.contains(search_text, case=False, na=False) |
            dff['Área'].astype(str).str.contains(search_text, case=False, na=False) |
            dff['Subárea 1'].astype(str).str.contains(search_text, case=False, na=False) |
            dff['Subárea 2'].astype(str).str.contains(search_text, case=False, na=False) |
            dff['Subárea 3'].astype(str).str.contains(search_text, case=False, na=False)
        )
        dff = dff[mask]
    if institution_filter != "Todas":
        dff = dff[dff['Institución'] == institution_filter]
    for column, selected in zip(['Área', 'Subárea 1', 'Subárea 2', 'Subárea 3'], hierarchy_filters):
        if selected != 'Todas':
            dff = dff[dff[column] == selected]
    if topic_filter != "Todos":
        dff = dff[dff['Tema'] == topic_filter]
    if freq_filter != "Todas":
        dff = dff[dff['Frecuencia'] == freq_filter]
    if valuation_filter != "Todas":
        dff = dff[dff['Valoración'] == valuation_filter]
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
