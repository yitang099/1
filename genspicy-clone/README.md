# Genspicy Clone (Local v2)

Local feature clone of [genspicy.ai](https://genspicy.ai) — **no payment / Stripe**.

## v2 includes

- Full public template catalog import (~10k templates)
- Explore with search + infinite scroll, Drama, Videos, Create modes
- Tools / category landing pages (tag filters)
- Guest + email sign-in, profile, demo diamond grants
- Generate, extend, like, favorites, creations (persisted to `server/data/runtime-store.json`)
- Affiliate link + click/signup stats (no payout)
- Pricing / terms / privacy (checkout disabled)

Generation remains **mock** (sample output media, timed progress).

## Setup

```bash
cd genspicy-clone
pnpm install
pnpm import:templates   # once — downloads catalog to server/data/templates.catalog.json
pnpm dev
```

Open **http://localhost:3000**

Without import, only 4 seed templates are available.

## API

Nitro routes mirror Genspicy-style RPC: `/api/v1/user.whoami`, `generation-template.list`, `user-generation-content.create`, etc.

Payment-related upstream calls are not implemented; `wallet.*` only exposes local demo grants.
