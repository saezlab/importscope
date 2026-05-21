# Examples

## How to run `importscope` on real repos

These guides are intentionally not the same analysis repeated on different
projects. They show a few different but coherent ways to use `importscope` once
you leave the small demo repo:

- whole-package structural view
- focused slice inside one package
- one subpackage extracted from a very large repo
- top-level package analysis with a starter config for grouping and policy

These pages are examples of usage, not claims that the repositories below have
bad architecture or poor design choices.

Each guide now shows the setup as `importscope init` plus a handful of
`importscope config ...` commands, so the checked-in example config files match
the documented command workflow exactly.

## Pick the guide by analysis style

- [Run `importscope` on `scverse/anndata`](./run-on-anndata.md)
  Whole-package view with one policy rule to highlight a cycle-relevant back-edge.
- [Run `importscope` on `saezlab/annnet`](./run-on-annnet.md)
  Focused cross-layer slice created by excluding unrelated areas.
- [Run `importscope` on `networkx/networkx`](./run-on-networkx.md)
  Subpackage-only analysis inside a much larger repository.
- [Run `importscope` on `saezlab/corneto`](./run-on-corneto.md)
  Small slice showing how the public package fans into graph, methods, and backends.
- [Run `importscope` on `saezlab/omnipath`](./run-on-omnipath.md)
  Small slice showing how `omnipath.requests` reaches the internal request engine.

## What stays consistent across all guides

Across all of them, the workflow is the same:

1. choose the package or slice that answers one architectural question
2. run a structural pass first
3. add grouping and policy only when it improves readability or review value
4. save JSON when you want follow-up `inspect` queries
