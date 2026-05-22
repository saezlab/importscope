# importscope demo: `demo-shop`

A deliberately small Python codebase for demonstrating `importscope`.

The package is a toy order-processing service with clear layers:

```text
api -> services -> domain
               -> persistence
               -> infra
```

It also contains a few intentional import smells so graph and report output are
more interesting:

- `demo_shop.api.routes` imports the private module `demo_shop.persistence._sql`
- `demo_shop.domain.models` performs a lazy import from `demo_shop.persistence.repository`
- `demo_shop.services.notifications` performs a lazy import of `demo_shop.infra.email`
- `demo_shop.services.orders` has symbol imports from several internal modules
- `demo_shop.__init__` re-exports public symbols
