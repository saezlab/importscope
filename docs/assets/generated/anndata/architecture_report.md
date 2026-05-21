# Import graph report

- Repo: `/tmp/importscope-example-repos/anndata`
- Modules parsed: `49`
- Internal import edges: `278`
- Lazy local edges: `54`
- Lazy dynamic edges: `0`
- Strongly connected components >1: `1`
- Private import edges: `166`
- Cross-area private import edges: `0`
- Boundary/helper cleanup candidate edges: `2`
- Coverage gaps: `0`

## Findings summary

- `boundary_helper`: `2`
- `forbidden_import`: `2`

## Cycles

### Component 1
- `anndata`
- `anndata._core.aligned_df`
- `anndata._core.aligned_mapping`
- `anndata._core.anndata`
- `anndata._core.extensions`
- `anndata._core.file_backing`
- `anndata._core.index`
- `anndata._core.merge`
- `anndata._core.raw`
- `anndata._core.sparse_dataset`
- `anndata._core.storage`
- `anndata._core.views`
- `anndata._core.xarray`
- `anndata._io`
- `anndata._io.h5ad`
- `anndata._io.read`
- `anndata._io.specs`
- `anndata._io.specs.lazy_methods`
- `anndata._io.specs.methods`
- `anndata._io.specs.registry`
- `anndata._io.utils`
- `anndata._io.write`
- `anndata._io.zarr`
- `anndata._types`
- `anndata.acc`
- `anndata.acc._parse_json`
- `anndata.acc._parse_str`
- `anndata.compat`
- `anndata.experimental`
- `anndata.experimental._dispatch_io`
- `anndata.experimental.backed`
- `anndata.experimental.backed._compat`
- `anndata.experimental.backed._io`
- `anndata.experimental.backed._lazy_arrays`
- `anndata.experimental.merge`
- `anndata.experimental.multi_files`
- `anndata.experimental.multi_files._anncollection`
- `anndata.experimental.pytorch`
- `anndata.experimental.pytorch._annloader`
- `anndata.io`
- `anndata.logging`
- `anndata.types`
- `anndata.typing`
- `anndata.utils`


## Cross-area private imports

No cross-area private imports detected.

## Boundary/helper cleanup candidates

- `anndata.experimental._dispatch_io` -> `anndata._io.specs` at line `35` importing `_REGISTRY, Reader`
- `anndata.experimental._dispatch_io` -> `anndata._io.specs` at line `70` importing `_REGISTRY, Writer`

## Hotspots

### Highest fan-in
- `anndata.compat` imported by `42` edge(s)
- `anndata.utils` imported by `21` edge(s)
- `anndata._core.xarray` imported by `15` edge(s)
- `anndata._warnings` imported by `14` edge(s)
- `anndata.acc` imported by `14` edge(s)

### Highest fan-out
- `anndata._core.anndata` imports `29` edge(s)
- `anndata._io.specs.methods` imports `19` edge(s)
- `anndata._core.merge` imports `17` edge(s)
- `anndata` imports `15` edge(s)
- `anndata._io.h5ad` imports `10` edge(s)
