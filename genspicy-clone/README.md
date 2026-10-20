# Genspicy Clone (Local v1)

Feature-oriented local clone of [genspicy.ai](https://genspicy.ai) for development and demos.

**v1 scope:** guest auth, template feed, favorites, mock generation (diamond balance, no Stripe).

## Run locally

```bash
cd genspicy-clone
pnpm install
pnpm dev
```

Open **http://localhost:3000**

1. Click **Continue as Guest** and pick gender (500 diamonds, VIP 2).
2. Open a template → **Generate** (mock ~3s progress, sample WebM output).
3. **My Creations** lists jobs; **Affiliate** shows a mock referral link.

API shape mirrors `/api/v1/*.method` RPC routes under this app’s Nitro server.
