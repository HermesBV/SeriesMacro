Proyecto del IIEP, área Macro
#SalierisDeHeymann

## Contrato de datos

La aplicación usa `bds/BD.xlsx`. El esquema actual de SeriesScraper define:

- `Codificacion`: inventario maestro multi-fuente. `ID` usa `Código fuente::ID origen` y conserva la ubicación física de cada serie.
- Las demás hojas contienen datos y deben tener una columna `fecha`; cada serie se localiza mediante `Pestaña BD` y `Columna BD`.

La base publicada contiene únicamente series graficables. Las fuentes documentales se incorporarán más adelante con un esquema específico. La vista Daniel Heymann solo se muestra cuando existe la hoja `ITCRB M`.
