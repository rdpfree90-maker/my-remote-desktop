Windows RDP + Tailscale + Telegram + Android Studio

Telegram menu:
- 🤖 رفع ملف Android Studio: ZIP projects are extracted to Desktop\AndroidStudio\Projects; APK files go to Desktop\AndroidStudio\APKs.
- 📁 رفع ملف Telegram: files go to Desktop\Telegram.
- 📂 رفع ملف عادي: files go to Desktop\ملفات عادية.
- 📍 حالة التخزين: shows the exact paths used by the bot.

Android Studio is checked first. It is installed only if no Android Studio executable is found.
A separate C:\RDPTools folder is used for tools/cache so repository files are not mixed with tools.

Note: GitHub-hosted Windows runners are temporary. Actions cache is repository-scoped; deleting the repository does not guarantee that cached tools remain available. For persistence beyond repository deletion, use a separate tools repository or external storage.
