import os
import re
import shutil
import time
import zipfile
from pathlib import Path
from threading import Lock

import telebot
from telebot import types

BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])
RDP_USERNAME = os.environ.get("RDP_USERNAME", "")

bot = telebot.TeleBot(BOT_TOKEN)
lock = Lock()

# The receiver runs as the GitHub Actions account, while RDP uses the local
# Windows account from user_name. The workflow passes the exact RDP profile
# path when possible so uploads land on the desktop you see in RDP.
if RDP_USERNAME:
    RDP_PROFILE = Path(os.environ.get("RDP_PROFILE", rf"C:\Users\{RDP_USERNAME}"))
    DESKTOP = Path(os.environ.get("RDP_DESKTOP", str(RDP_PROFILE / "Desktop")))
else:
    DESKTOP = Path.home() / "Desktop"

TELEGRAM_DIR = DESKTOP / "Telegram"
MOHAMED_DIR = DESKTOP / "محمد"
ANDROID_DIR = DESKTOP / "AndroidStudio"
ANDROID_PROJECTS = ANDROID_DIR / "Projects"
ANDROID_INCOMING = ANDROID_DIR / "Incoming"
ANDROID_APKS = ANDROID_DIR / "APKs"

for folder in (TELEGRAM_DIR, MOHAMED_DIR, ANDROID_PROJECTS, ANDROID_INCOMING, ANDROID_APKS):
    folder.mkdir(parents=True, exist_ok=True)

mode = {ADMIN_ID: "telegram"}


def allowed(message):
    return bool(message.from_user and message.from_user.id == ADMIN_ID)


def safe_name(name: str, fallback: str = "file") -> str:
    name = Path(name or fallback).name
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", name).strip(" .")
    return name or fallback


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    for i in range(1, 100000):
        candidate = path.with_name(f"{stem} ({i}){suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError("Could not create a unique filename")


def menu():
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("🤖 رفع ملف Android Studio", callback_data="mode:android"))
    kb.add(types.InlineKeyboardButton("📂 رفع ملف محمد", callback_data="mode:mohamed"))
    kb.add(types.InlineKeyboardButton("📁 رفع ملف Telegram Desktop", callback_data="mode:telegram"))
    kb.add(types.InlineKeyboardButton("📍 حالة التخزين", callback_data="status"))
    return kb


def current_mode(user_id):
    return mode.get(user_id, "telegram")


def zip_project_root(zf: zipfile.ZipFile):
    names = [n.replace("\\", "/").lstrip("/") for n in zf.namelist() if n and not n.endswith("/")]
    if not names:
        return None
    roots = {n.split("/", 1)[0] for n in names if "/" in n}
    if len(roots) == 1:
        root = next(iter(roots))
        if all(n == root or n.startswith(root + "/") for n in names):
            return root
    return None


def safe_extract_zip(zf: zipfile.ZipFile, destination: Path):
    destination = destination.resolve()
    for member in zf.infolist():
        raw = member.filename.replace("\\", "/")
        if not raw or raw.endswith("/"):
            continue
        p = Path(raw)
        if p.is_absolute() or ".." in p.parts:
            raise ValueError(f"Unsafe ZIP entry: {member.filename}")
        target = (destination / raw).resolve()
        if target != destination and destination not in target.parents:
            raise ValueError(f"Unsafe ZIP entry: {member.filename}")
        target.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(member, "r") as src, open(target, "wb") as dst:
            shutil.copyfileobj(src, dst)


def looks_like_android_project(folder: Path) -> bool:
    markers = (
        "settings.gradle", "settings.gradle.kts",
        "build.gradle", "build.gradle.kts",
        "gradlew", "gradlew.bat", "app",
    )
    return any((folder / marker).exists() for marker in markers)


def extract_android_project(zip_path: Path, project_name: str) -> Path:
    project_name = safe_name(project_name, "AndroidProject")
    final_dir = unique_path(ANDROID_PROJECTS / project_name)
    temp_dir = unique_path(ANDROID_INCOMING / f".{project_name}_extracting")
    temp_dir.mkdir(parents=True, exist_ok=False)
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            if zf.testzip() is not None:
                raise ValueError("ZIP file is corrupted")
            root = zip_project_root(zf)
            safe_extract_zip(zf, temp_dir)

        source = temp_dir / root if root and (temp_dir / root).is_dir() else temp_dir
        if not looks_like_android_project(source):
            # Keep non-standard projects rather than deleting anything.
            pass

        final_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(final_dir))
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        return final_dir
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise


def save_bytes(data: bytes, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination = unique_path(destination)
    destination.write_bytes(data)
    return destination


def download_document(message):
    info = bot.get_file(message.document.file_id)
    return message.document.file_name or "file", bot.download_file(info.file_path)


@bot.message_handler(commands=["start", "menu", "help"])
def start(message):
    if not allowed(message):
        return
    bot.send_message(
        message.chat.id,
        "🖥️ <b>Windows RDP File Manager</b>\n\n"
        "اختار مكان الرفع:\n\n"
        "🤖 <b>Android Studio</b> → ZIP مشروع Android / APK / ملفات التطوير\n"
        "📂 <b>محمد</b> → أي ملفات عادية داخل مجلد محمد\n"
        "📁 <b>Telegram Desktop</b> → ملفات وروابط Telegram\n\n"
        "وزر <b>حالة التخزين</b> يجيب لك كل المسارات الفعلية على جهاز RDP.",
        parse_mode="HTML",
        reply_markup=menu(),
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("mode:"))
def change_mode(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "غير مسموح")
        return
    selected = call.data.split(":", 1)[1]
    mode[ADMIN_ID] = selected
    if selected == "android":
        text = (
            "🤖 <b>رفع ملف Android Studio</b>\n\n"
            "📦 ZIP مشروع Android → يتفك تلقائيًا داخل Projects.\n"
            "📱 APK → داخل APKs.\n"
            "📄 أي ملف آخر → داخل Incoming.\n\n"
            "📂 <code>Desktop\\AndroidStudio\\Projects</code>"
        )
    elif selected == "mohamed":
        text = (
            "📂 <b>رفع ملف محمد</b>\n\n"
            "أي ملف ترسله الآن سيتم حفظه داخل:\n"
            "<code>Desktop\\محمد</code>"
        )
    else:
        text = (
            "📁 <b>رفع ملف Telegram Desktop</b>\n\n"
            "أي ملف أو رابط ترسله الآن سيتم حفظه داخل:\n"
            "<code>Desktop\\Telegram</code>"
        )
    bot.answer_callback_query(call.id, "تم التغيير")
    try:
        bot.edit_message_text(
            text, call.message.chat.id, call.message.message_id,
            parse_mode="HTML", reply_markup=menu()
        )
    except Exception:
        bot.send_message(call.message.chat.id, text, parse_mode="HTML", reply_markup=menu())


@bot.callback_query_handler(func=lambda call: call.data == "status")
def status(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "غير مسموح")
        return
    text = (
        "📍 <b>حالة التخزين</b>\n\n"
        f"🖥️ RDP Desktop:\n<code>{DESKTOP}</code>\n\n"
        f"📁 Telegram Desktop:\n<code>{TELEGRAM_DIR}</code>\n\n"
        f"📂 محمد:\n<code>{MOHAMED_DIR}</code>\n\n"
        f"🤖 Android Projects:\n<code>{ANDROID_PROJECTS}</code>\n\n"
        f"📱 APKs:\n<code>{ANDROID_APKS}</code>"
    )
    bot.answer_callback_query(call.id, "تم")
    bot.send_message(call.message.chat.id, text, parse_mode="HTML", reply_markup=menu())


@bot.message_handler(content_types=["document"])
def documents(message):
    if not allowed(message):
        return
    try:
        original, data = download_document(message)
        original = safe_name(original)
        selected = current_mode(ADMIN_ID)

        with lock:
            if selected == "android":
                if original.lower().endswith(".zip"):
                    incoming = save_bytes(data, ANDROID_INCOMING / original)
                    project = extract_android_project(incoming, Path(original).stem)
                    bot.reply_to(
                        message,
                        "✅ <b>تم رفع مشروع Android وتجهيزه</b>\n\n"
                        f"📦 النسخة الأصلية: <code>{incoming}</code>\n"
                        f"📂 المشروع الجاهز: <code>{project}</code>\n\n"
                        "🤖 افتح Android Studio → Open → اختار مجلد المشروع.\n"
                        "وسيبدأ Gradle Sync عند فتحه.",
                        parse_mode="HTML",
                    )
                    return

                if original.lower().endswith(".apk"):
                    dest = save_bytes(data, ANDROID_APKS / original)
                    bot.reply_to(message, f"✅ تم رفع APK\n\n📱 {dest.name}\n📂 Desktop\\AndroidStudio\\APKs")
                    return

                dest = save_bytes(data, ANDROID_INCOMING / original)
                bot.reply_to(message, f"✅ تم رفع الملف\n\n📄 {dest.name}\n📂 Desktop\\AndroidStudio\\Incoming")
                return

            if selected == "mohamed":
                dest = save_bytes(data, MOHAMED_DIR / original)
                bot.reply_to(message, f"✅ تم رفع الملف\n\n📄 الاسم: {dest.name}\n\n📂 المكان: Desktop\\محمد")
                return

            dest = save_bytes(data, TELEGRAM_DIR / original)
            bot.reply_to(message, f"✅ تم استلام الملف\n\n📄 الاسم: {dest.name}\n\n📂 المكان: Desktop\\Telegram")
    except Exception as exc:
        bot.reply_to(message, f"❌ حصل خطأ أثناء حفظ الملف:\n{exc}")


@bot.message_handler(func=lambda m: bool(m.text) and not m.text.startswith("/"))
def links(message):
    if not allowed(message):
        return
    text = message.text.strip()
    if not re.match(r"^https?://", text, re.I):
        return
    selected = current_mode(ADMIN_ID)
    link_dir = MOHAMED_DIR if selected == "mohamed" else TELEGRAM_DIR
    dest = unique_path(link_dir / "Telegram_Link.url")
    dest.write_text("[InternetShortcut]\nURL=" + text + "\n", encoding="utf-8")
    shown = "Desktop\\محمد" if selected == "mohamed" else "Desktop\\Telegram"
    bot.reply_to(message, f"🔗 تم إنشاء اختصار للرابط\n\n📂 {shown}\\{dest.name}")


# Keep polling alive if Telegram temporarily drops the connection.
while True:
    try:
        bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=30)
    except Exception as exc:
        print(f"Telegram polling error: {exc!r}", flush=True)
        time.sleep(5)
