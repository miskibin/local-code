---
name: e2e-screenshot
description: Start the local-code app (FastAPI backend + Next.js frontend) in the sandbox, send a sample query via browser automation, and capture a screenshot of the result. Use when the user asks to "take a screenshot", "show the app running", or "test e2e in the browser".
---

# E2E Screenshot Skill

Spin up the full stack, send a chat query that exercises SQL + Python tools, wait for the streaming response to finish, and capture a full-page screenshot.

## Workflow

### 1. Check / create env files

Backend needs `backend/.env`:
```
google_api_key=<KEY>
```

Frontend needs `frontend/.env.local`:
```
NEXT_PUBLIC_BACKEND_URL_BASE=http://localhost:8000
```

If either is missing and the user hasn't provided a key, ask for `GOOGLE_API_KEY` before continuing.

### 2. Fix pydantic / Python 3.14 RC2 compatibility (if needed)

This repo uses Python 3.14 RC2. Pydantic 2.13.x passes `prefer_fwd_module=True` to `typing._eval_type`, which doesn't exist yet in RC2. Check and patch if needed:

```bash
grep -n "prefer_fwd_module" backend/.venv/lib/python3.14/site-packages/pydantic/_internal/_typing_extra.py | head -5
```

If the patch is NOT present (output doesn't contain `co_varnames`), apply it. Find the block that looks like:

```python
if sys.version_info >= (3, 14):
    evaluated = typing._eval_type(value, globalns, localns, type_params=type_params, prefer_fwd_module=True)
```

And replace it with the safe version:

```python
if sys.version_info >= (3, 14):
    _eval_type_kwargs: dict = {'type_params': type_params}
    if 'prefer_fwd_module' in typing._eval_type.__code__.co_varnames:  # type: ignore
        _eval_type_kwargs['prefer_fwd_module'] = True
    evaluated = typing._eval_type(value, globalns, localns, **_eval_type_kwargs)
    if evaluated is None:
        evaluated = type(None)
    return evaluated
```

Verify the fix works: `cd backend && uv run python -c "import app.main; print('OK')"`

### 3. Start the backend

```bash
cd /home/user/local-code/backend
uv run uvicorn app.main:app --port 8000 > /tmp/backend.log 2>&1 &
```

Wait up to 20 s, poll until `curl -s http://localhost:8000/` returns JSON:
```bash
for i in $(seq 1 20); do sleep 1; curl -s http://localhost:8000/ && break; done
```

If it never responds check `/tmp/backend.log` for errors.

### 4. Start the frontend

```bash
cd /home/user/local-code/frontend
npm run dev > /tmp/frontend.log 2>&1 &
```

Poll until HTTP 307 (redirect to `/chat/…`):
```bash
for i in $(seq 1 30); do sleep 1; CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/); [ "$CODE" = "307" ] && break; done
```

### 5. Locate the Playwright Chromium binary

The network-downloadable chromium often fails in sandboxes. Use the pre-installed binary:

```bash
ls /opt/pw-browsers/chromium_headless_shell-*/chrome-linux/headless_shell 2>/dev/null | tail -1
```

Use whatever path is returned as `executablePath` in the Playwright launch config.  
If nothing is found, fall back to: `ls /opt/pw-browsers/chromium-*/chrome-linux/chrome 2>/dev/null | tail -1`

### 6. Write and run the Playwright screenshot script

Write to `/tmp/e2e_screenshot.mjs`:

```js
import { chromium } from '/home/user/local-code/frontend/node_modules/playwright/index.mjs';

const QUERY = process.argv[2] ?? 'Show me the top 5 best-selling artists from the database, then calculate their total revenue using Python.';
const OUT = process.argv[3] ?? '/tmp/e2e_result.png';
const BINARY = process.argv[4] ?? '/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell';

const browser = await chromium.launch({ headless: true, executablePath: BINARY });
const page = await browser.newPage();
await page.setViewportSize({ width: 1400, height: 900 });

// IMPORTANT: use 'load', not 'networkidle' — Next.js dev mode keeps HMR connections open
await page.goto('http://localhost:3000', { waitUntil: 'load', timeout: 30000 });
await page.waitForTimeout(3000);

const input = await page.waitForSelector('textarea', { timeout: 15000 });
await input.click();
await input.fill(QUERY);

const btn = await page.$('button[type="submit"]');
if (btn) await btn.click(); else await page.keyboard.press('Enter');
console.log('Query sent. Waiting for streaming to finish...');

// Poll until the "stop" button disappears (streaming done)
for (let i = 0; i < 60; i++) {
  await page.waitForTimeout(2000);
  const stop = await page.$('button:has-text("stop")');
  if (!stop) { console.log(`Done after ~${(i+1)*2}s`); break; }
  if (i % 5 === 4) console.log(`Still streaming... ${(i+1)*2}s`);
}

await page.waitForTimeout(1500);
await page.screenshot({ path: OUT, fullPage: true });
console.log('Screenshot saved:', OUT);
await browser.close();
```

Run it:
```bash
node /tmp/e2e_screenshot.mjs 2>&1
```

To pass a custom query:
```bash
node /tmp/e2e_screenshot.mjs "Which genre has the most revenue? Use SQL then rank with Python." /tmp/e2e_genre.png
```

### 7. Show the screenshot

Read the PNG with the Read tool — it renders inline in the Claude Code output.

```
Read /tmp/e2e_result.png
```

## Known issues

| Problem | Cause | Fix |
|---|---|---|
| `prefer_fwd_module` TypeError | pydantic 2.13.x + Python 3.14 RC2 | Step 2 patch |
| `networkidle` timeout | Next.js dev HMR never closes | Use `waitUntil: 'load'` |
| Chromium download fails | No outbound HTTP in sandbox | Use binary from `/opt/pw-browsers/` |
| Backend stuck at "reloader process" | Worker import error | Check `/tmp/backend.log`, run step 2 |
| `ERR_CONNECTION_REFUSED` on 3000 | Frontend not running | Check `/tmp/frontend.log` |

## Wrap up

Show the screenshot and include:
- Query sent
- Tools called (sql_query, python_exec)
- Final answer from the model
- Model name shown in the bottom bar
