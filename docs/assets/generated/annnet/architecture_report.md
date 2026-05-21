# Import graph report

- Repo: `/home/daniele/annnet`
- Modules parsed: `26`
- Internal import edges: `40`
- Lazy local edges: `6`
- Lazy dynamic edges: `0`
- Strongly connected components >1: `0`
- Private import edges: `36`
- Cross-area private import edges: `0`
- Boundary/helper cleanup candidate edges: `2`
- Coverage gaps: `5`

## Findings summary

- `boundary_helper`: `2`
- `forbidden_import`: `2`

## Cycles

No module-level circular imports detected.

## Cross-area private imports

No cross-area private imports detected.

## Boundary/helper cleanup candidates

- `annnet.core.graph` -> `annnet._support.dataframe_backend` at line `33` importing `empty_dataframe, dataframe_height, dataframe_columns, dataframe_to_rows, dataframe_drop_rows, is_polars_dataframe, dataframe_upsert_rows, polars_upsert_vertices, select_dataframe_backend`
- `annnet.core.graph` -> `annnet.algorithms.traversal` at line `32` importing `Traversal`

## Hotspots

### Highest fan-in
- `annnet._support.dataframe_backend` imported by `12` edge(s)
- `annnet.core._records` imported by `6` edge(s)
- `annnet._support.optional_components` imported by `3` edge(s)
- `annnet.core.backend_accessors._base` imported by `3` edge(s)
- `annnet` imported by `2` edge(s)

### Highest fan-out
- `annnet.core.graph` imports `15` edge(s)
- `annnet.core._Slices` imports `3` edge(s)
- `annnet` imports `2` edge(s)
- `annnet.core` imports `2` edge(s)
- `annnet.core._Layers` imports `2` edge(s)

## Coverage gaps

- `annnet._support.lazy_exports` at line `13`: `dynamic_import_unresolved`
- `annnet._support.lazy_exports` at line `40`: `dynamic_import_unresolved`
- `annnet._support.lazy_exports` at line `43`: `dynamic_import_unresolved`
- `annnet.algorithms` at line `18`: `dynamic_import_unresolved`
- `annnet.core.backend_accessors._base` at line `201`: `dynamic_import_unresolved`
