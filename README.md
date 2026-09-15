Proyecto del IIEP, área Macro
#SalierisDeHeymann

## Contrato de datos

La aplicación usa `bds/BD.xlsx`. El esquema actual de SeriesScraper define:

- `Codificacion`: inventario maestro multi-fuente. La clave es (`Código fuente`, `ID`); `ID` conserva el identificador nativo o uno estable asignado cuando la fuente no publica identificadores.
- Las demás hojas contienen datos y deben tener una columna `fecha`; cada serie se localiza mediante `Pestaña BD` y `Columna BD`.

El buscador muestra `Título`, `Detalle`, unidades, valoración, tema y frecuencia, además de la cantidad total o filtrada de series. `Valoración` distingue precios corrientes y constantes sólo cuando los metadatos contienen evidencia inequívoca. Si dos series conservan exactamente los mismos metadatos visibles, `Detalle` agrega su ID de origen para que nunca resulten indistinguibles.

La base publicada contiene únicamente series graficables. Las fuentes documentales se incorporarán más adelante con un esquema específico. La vista Daniel Heymann se alimenta de la serie mensual histórica del IIEP: usa `Importación (implícito)` reescalada antes de enero de 1997 y el promedio mensual oficial `ITCRB Estados Unidos` del BCRA desde esa fecha. SeriesMacro la localiza por su ID estable en `Codificacion`.
