Proyecto del IIEP, área Macro
#SalierisDeHeymann

## Ejecutar en Windows

Desde la carpeta del proyecto, instala las dependencias una vez y ejecuta la aplicación:

```powershell
py -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\run.cmd
```

`run.cmd` usa el Python del entorno virtual mediante `-m streamlit`, así que no depende de la ruta absoluta guardada en el ejecutable `streamlit.exe`. Si mueves la carpeta a otra unidad, vuelve a crear el entorno virtual e instala las dependencias desde la nueva ubicación.

## Contrato de datos

La aplicación usa `bds/BD.xlsx` para los datos y `bds/IndiceSeries.xlsx` para el inventario. El esquema actual de SeriesScraper define:

- `Codificacion`, dentro de `IndiceSeries.xlsx`: inventario maestro multi-fuente. La clave es (`Código fuente`, `ID`); `ID` conserva el identificador nativo o uno estable asignado cuando la fuente no publica identificadores.
- Las demás hojas contienen datos y deben tener una columna `fecha`; cada serie se localiza mediante `Pestaña BD` y `Columna BD`.

El índice `Codificacion` conserva los metadatos de origen y la clasificación de cada serie: `Institución`, `Área`, `Subárea 1`, `Subárea 2`, `Subárea 3` y `Tema`. La clasificación jerárquica se registra en el índice y los filtros muestran sólo las opciones que corresponden a la institución y a los niveles anteriores. Los selectores permiten buscar escribiendo.

El buscador muestra `Título`, `Detalle`, `Unidad`, `Valoración`, frecuencia, `Desde`, `Hasta`, tema, institución, área y subáreas. Las fechas se expresan con la precisión de la serie: año para frecuencia anual, año y mes para mensual, y año, mes y día para diaria o irregular. `Valoración` distingue precios corrientes y constantes sólo cuando los metadatos contienen evidencia inequívoca. Las unidades físicas, tasas e índices se marcan `No aplica`; las unidades monetarias sin evidencia se marcan `No informado`. Si dos series conservan exactamente los mismos metadatos visibles, `Detalle` agrega su ID de origen para que nunca resulten indistinguibles.

Los campos descriptivos y de procedencia que también conserva cada registro son `ID`, `Código fuente`, `Variable`, `Descripción`, `Pestaña BD`, `Columna BD`, `Archivo origen`, `Hoja origen`, `Origen`, `Fuente`, `Catálogo ID`, `Dataset ID`, `Distribución ID`, `Título dataset`, `Tema dataset`, `Responsable dataset`, `Fuente de valores` y `Estado`.

La base publicada contiene únicamente series graficables. Las fuentes documentales se incorporarán más adelante con un esquema específico. La vista Daniel Heymann se alimenta de la serie mensual histórica del IIEP: usa `Importación (implícito)` reescalada antes de enero de 1997 y el promedio mensual oficial `ITCRB Estados Unidos` del BCRA desde esa fecha. SeriesMacro la localiza por su ID estable en `Codificacion`.

Las series de Hacienda están temporalmente excluidas de la búsqueda hasta que se reemplace su scraper.
