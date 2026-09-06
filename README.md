Proyecto del IIEP, área Macro
#SalierisDeHeymann

## Contrato de datos

La aplicación usa `bds/BD.xlsx`. El esquema actual de SeriesScraper define:

- `Codificacion`: inventario maestro multi-fuente. `ID` usa `Código fuente::ID origen` y conserva la ubicación física de cada serie.
- Las demás hojas contienen datos y deben tener una columna `fecha`; cada serie se localiza mediante `Pestaña BD` y `Columna BD`.

El buscador muestra `Título`, `Detalle`, unidades, valoración, tema y frecuencia, además de la cantidad total o filtrada de series. `Valoración` distingue precios corrientes y constantes sólo cuando los metadatos contienen evidencia inequívoca. Si dos series conservan exactamente los mismos metadatos visibles, `Detalle` agrega su ID de origen para que nunca resulten indistinguibles.

La base publicada contiene únicamente series graficables. Las fuentes documentales se incorporarán más adelante con un esquema específico. La vista Daniel Heymann solo se muestra cuando existe la hoja `ITCRB M`.
