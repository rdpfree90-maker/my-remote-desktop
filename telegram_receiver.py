import os, re
from pathlib import Path
import telebot

bot = telebot.TeleBot(os.environ["BOT_TOKEN"])
ADMIN_ID = int(os.environ["ADMIN_ID"])

target = Path.home() / "Desktop" / "Telegram"
target.mkdir(parents=True, exist_ok=True)

def ok(m):
    return m.from_user.id == ADMIN_ID

def safe(n):
    return re.sub(r'[\\/:*?"<>|]', "_", n)

@bot.message_handler(content_types=["document"])
def files(m):
    if not ok(m): return
    info = bot.get_file(m.document.file_id)
    data = bot.download_file(info.file_path)
    name = safe(m.document.file_name or "file")
    (target/name).write_bytes(data)
    bot.reply_to(m, f"✅ تم حفظ الملف\n\n📄 {name}\n📂 Desktop\\Telegram")

@bot.message_handler(func=lambda m: bool(m.text))
def links(m):
    if not ok(m): return
    t=m.text.strip()
    if t.startswith("http://") or t.startswith("https://"):
        name="Telegram_Link.url"
        (target/name).write_text("[InternetShortcut]\nURL="+t, encoding="utf-8")
        bot.reply_to(m, "🔗 تم إنشاء اختصار الرابط داخل Desktop\\Telegram")

bot.infinity_polling()
