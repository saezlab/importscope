# Import graph report

- Repo: `/tmp/importscope-example-repos/omnipath`
- Modules parsed: `19`
- Internal import edges: `57`
- Lazy local edges: `8`
- Lazy dynamic edges: `0`
- Strongly connected components >1: `1`
- Private import edges: `45`
- Cross-area private import edges: `0`
- Boundary/helper cleanup candidate edges: `0`
- Coverage gaps: `0`

## Findings summary

No policy findings detected.

## Cycles

### Component 1
- `omnipath`
- `omnipath._core.downloader._downloader`
- `omnipath._core.query`
- `omnipath._core.query._query`
- `omnipath._core.query._query_validator`
- `omnipath._core.requests`
- `omnipath._core.requests._annotations`
- `omnipath._core.requests._complexes`
- `omnipath._core.requests._intercell`
- `omnipath._core.requests._request`
- `omnipath._core.requests._utils`
- `omnipath._core.utils`
- `omnipath._core.utils._static`
- `omnipath.interactions`
- `omnipath.requests`


## Cross-area private imports

No cross-area private imports detected.

## Boundary/helper cleanup candidates

No boundary/helper cleanup candidates detected.

## Hotspots

### Highest fan-in
- `omnipath._core.utils` imported by `8` edge(s)
- `omnipath._core.query` imported by `6` edge(s)
- `omnipath.constants._pkg_constants` imported by `6` edge(s)
- `omnipath` imported by `5` edge(s)
- `omnipath._core.downloader._downloader` imported by `4` edge(s)

### Highest fan-out
- `omnipath._core.requests._request` imports `9` edge(s)
- `omnipath._core.query._query_validator` imports `7` edge(s)
- `omnipath` imports `5` edge(s)
- `omnipath._core.requests._annotations` imports `5` edge(s)
- `omnipath._core.requests._intercell` imports `5` edge(s)
