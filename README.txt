Windows RDP via Tailscale - Minimal

This version intentionally contains only:
- Windows GitHub Actions runner
- Tailscale connection
- Windows Remote Desktop setup
- Telegram message with Tailscale IP, port, username and password
- Keep-alive for the workflow

Removed:
- Android Studio installation
- Android Studio project/file uploads
- Telegram file receiver
- Telegram upload buttons
- Tools/cache folders
- Extra desktop folders and shortcuts
- Other automation features

Required GitHub Secrets:
- TAILSCALE_AUTHKEY
- BOT_TOKEN
- ADMIN_ID
- user_name
- PASSWORD
