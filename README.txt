# Windows RDP + Tailscale + Telegram + Android Studio

This workflow creates a temporary Windows GitHub Actions runner, enables RDP,
connects it to Tailscale, sends RDP details to Telegram, and runs a Telegram
file receiver.

Required GitHub Secrets:
- BOT_TOKEN
- ADMIN_ID
- TAILSCALE_AUTHKEY
- PASSWORD
- user_name

Telegram buttons:
- 🤖 رفع ملف Android Studio: ZIP projects are extracted to Desktop\\AndroidStudio\\Projects; APKs go to APKs.
- 📂 رفع ملف محمد: files go to Desktop\\محمد.
- 📁 رفع ملف Telegram Desktop: files go to Desktop\\Telegram.
- 📍 حالة التخزين: shows actual paths.

The receiver is started using an absolute workspace path and the workflow can
re-create telegram_receiver.py if it is missing from the repository.

Tools:
- A `tools` directory is created for downloaded/helper tools.
- GitHub Actions cache is enabled for that directory, so repeated runs of this
  repository can reuse cached tool data when the cache key matches.
- IMPORTANT: GitHub-hosted runners are temporary. A folder on the runner does
  not survive the job. GitHub Actions cache is repository-scoped; deleting the
  repository also removes its cache. If tools must survive deletion of this
  repository, store them in a separate GitHub repository or external storage.

The workflow intentionally does not expose RDP port 3389 to the public internet;
Tailscale is used for access.
