# Windows RDP + Tailscale + Telegram

This workflow creates a temporary Windows GitHub Actions runner, enables RDP,
connects it to Tailscale, and sends the connection details to Telegram.

Required GitHub Secrets:

- `BOT_TOKEN`       = Telegram bot token
- `ADMIN_ID`        = Telegram chat/user ID that should receive the message
- `TAILSCALE_AUTHKEY` = Tailscale auth key
- `PASSWORD`        = Windows RDP password
- `user_name`       = Windows RDP username

The workflow does not contain any token/password directly.

Run:
GitHub -> Actions -> Windows RDP via Tailscale -> Run workflow.

The Telegram message is a complete connection card containing:
- Tailscale IP
- RDP port 3389
- username from `user_name`
- password from `PASSWORD`
- connection instructions
- Tailscale-only warning
- reminder to keep the workflow running
- Windows/RDP/Tailscale ready status

The Windows machine is temporary and disappears when the GitHub Actions job
ends or reaches its execution limit. Do not expose RDP port 3389 to the public
internet; the intended connection is through Tailscale.


FIX:
The keep-alive step uses a parser-safe PowerShell `for (;;) { ... }` loop.


Telegram formatting:
The IP, username, password, and port are each placed in separate Telegram
inline-code fields so they are visually separated and easy to copy individually.


The Telegram connection message is intentionally compact to avoid taking up unnecessary screen space while keeping every connection value easy to copy.

Display: portrait RDP is preserved; desktop icons are reduced and spacing tightened.
