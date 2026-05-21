# `importscope config`

Use this to inspect or edit `.importscope.yml` programmatically.

```bash
importscope config show
importscope config show --effective
importscope config package set mypackage
importscope config exclude add 'tests/**'
importscope config forbid add mypackage.domain mypackage.persistence
```

## What it is for

Use `config` when you want to make common config changes without manually
editing YAML:

- set or unset the package filter
- add or remove discovery include/exclude globs
- enable or disable policy mode
- set or unset `module_group_depth`
- add or remove forbidden-import rules
- add or remove allowed private target prefixes
- print the current config

## Common commands

Show the file contents:

```bash
importscope config show
```

Show the merged effective config:

```bash
importscope config show --effective
```

Set the package:

```bash
importscope config package set omnipath
```

Exclude noisy paths:

```bash
importscope config exclude add 'docs/**' 'tests/**'
```

Narrow the run to a specific slice:

```bash
importscope config include add 'omnipath/_core/downloader/**'
```

Enable policy and add one direction rule:

```bash
importscope config policy enable
importscope config forbid add mypackage.api mypackage.persistence._
```

Allow intentionally shared private targets:

```bash
importscope config allowed-private add mypackage._
```

Tune module-level clustering:

```bash
importscope config module-group-depth set 3
```

## Notes

- `config` edits the file on disk immediately.
- When `--config` is omitted, `importscope` uses the auto-discovered config path
  or falls back to `.importscope.yml` in the repo root.
- For more advanced fields such as custom `display_groups` or custom output
  profiles, manual YAML is still the right tool.
