# Ionity Claude Web Bridge (no API key)

Relays the Edge Brain's prompts to **claude.ai using YOUR Google login** — no Anthropic API
key, your own subscription. The Edge Brain calls it as the **primary brain**; if it's not
running or not signed in, the Edge Brain falls back to the local `gemma4:e2b` model, so the
assistant always works.

## Run

```bat
:: Windows — double-click, or:
cd bridge\claude-web
START-BRIDGE.bat
```

First run installs Playwright + Chromium and opens a browser at claude.ai. **Sign in with
Google once** — the session is saved in `.profile/` (git-ignored). Leave the window open.

Then point the Edge Brain at it (already the default):

```
BRIDGE_MODE=http
BRIDGE_URL=http://127.0.0.1:8799/ask
```

## Contract

- `POST /ask  {"prompt": "...", "context": {}}` → `{"text": "...", "ok": true}`
- `GET  /health` → `{"ok":true,"loggedIn":bool,"busy":bool}`

## Env

| var | default | meaning |
|---|---|---|
| `BRIDGE_PORT` | `8799` | HTTP port |
| `BRIDGE_PROFILE` | `./.profile` | persistent browser profile (holds your login) |
| `BRIDGE_HEADLESS` | `0` | set `1` to hide the window after you've logged in once |

## Notes / limits

- This drives claude.ai's web UI with Playwright. If claude.ai changes its markup, the
  selectors in `server.js` (`ask()`) may need a tweak — the Edge Brain keeps working on
  `gemma4:e2b` meanwhile.
- Nothing here is committed except source: `node_modules/` and `.profile/` are git-ignored.

© Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
