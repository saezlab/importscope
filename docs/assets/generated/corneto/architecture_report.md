# Import graph report

- Repo: `/tmp/importscope-example-repos/corneto`
- Modules parsed: `19`
- Internal import edges: `84`
- Lazy local edges: `17`
- Lazy dynamic edges: `0`
- Strongly connected components >1: `1`
- Private import edges: `42`
- Cross-area private import edges: `0`
- Boundary/helper cleanup candidate edges: `0`
- Coverage gaps: `0`

## Findings summary

No policy findings detected.

## Cycles

### Component 1
- `corneto`
- `corneto._graph`
- `corneto.backend`
- `corneto.backend._base`
- `corneto.backend._cvxpy_backend`
- `corneto.backend._picos_backend`
- `corneto.graph`
- `corneto.graph._base`
- `corneto.graph._graph`
- `corneto.methods`
- `corneto.methods.carnival`
- `corneto.methods.shortest_path`
- `corneto.methods.signaling`


## Cross-area private imports

No cross-area private imports detected.

## Boundary/helper cleanup candidates

No boundary/helper cleanup candidates detected.

## Hotspots

### Highest fan-in
- `corneto` imported by `29` edge(s)
- `corneto._settings` imported by `10` edge(s)
- `corneto.backend._base` imported by `8` edge(s)
- `corneto._constants` imported by `7` edge(s)
- `corneto._graph` imported by `6` edge(s)

### Highest fan-out
- `corneto._graph` imports `9` edge(s)
- `corneto.graph._base` imports `8` edge(s)
- `corneto` imports `7` edge(s)
- `corneto.methods` imports `7` edge(s)
- `corneto.methods.method` imports `7` edge(s)
