# Import graph report

- Repo: `/tmp/importscope-example-repos/networkx`
- Modules parsed: `23`
- Internal import edges: `21`
- Lazy local edges: `0`
- Lazy dynamic edges: `0`
- Strongly connected components >1: `0`
- Private import edges: `0`
- Cross-area private import edges: `0`
- Boundary/helper cleanup candidate edges: `0`
- Coverage gaps: `0`

## Findings summary

No policy findings detected.

## Cycles

No module-level circular imports detected.

## Cross-area private imports

No cross-area private imports detected.

## Boundary/helper cleanup candidates

No boundary/helper cleanup candidates detected.

## Hotspots

### Highest fan-in
- `networkx.readwrite.json_graph` imported by `5` edge(s)
- `networkx.readwrite.graph6` imported by `2` edge(s)
- `networkx.readwrite.adjlist` imported by `1` edge(s)
- `networkx.readwrite.edgelist` imported by `1` edge(s)
- `networkx.readwrite.gexf` imported by `1` edge(s)

### Highest fan-out
- `networkx.readwrite` imports `12` edge(s)
- `networkx.readwrite.json_graph` imports `4` edge(s)
- `networkx.readwrite.json_graph.tests.test_adjacency` imports `1` edge(s)
- `networkx.readwrite.json_graph.tests.test_cytoscape` imports `1` edge(s)
- `networkx.readwrite.json_graph.tests.test_node_link` imports `1` edge(s)
