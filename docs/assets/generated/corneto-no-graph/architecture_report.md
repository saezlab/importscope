# Import graph report

- Repo: `/tmp/importscope-example-repos/corneto`
- Modules parsed: `14`
- Internal import edges: `57`
- Lazy local edges: `4`
- Lazy dynamic edges: `0`
- Strongly connected components >1: `1`
- Private import edges: `28`
- Cross-area private import edges: `0`
- Boundary/helper cleanup candidate edges: `0`
- Coverage gaps: `0`

## Findings summary

No policy findings detected.

## Cycles

### Component 1
- `corneto`
- `corneto.backend`
- `corneto.backend._base`
- `corneto.backend._cvxpy_backend`
- `corneto.backend._picos_backend`
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
- `corneto` imported by `13` edge(s)
- `corneto._settings` imported by `10` edge(s)
- `corneto.backend._base` imported by `8` edge(s)
- `corneto._constants` imported by `7` edge(s)
- `corneto.backend` imported by `6` edge(s)

### Highest fan-out
- `corneto.methods` imports `7` edge(s)
- `corneto.methods.method` imports `7` edge(s)
- `corneto` imports `6` edge(s)
- `corneto.backend._base` imports `6` edge(s)
- `corneto.methods.carnival` imports `6` edge(s)
