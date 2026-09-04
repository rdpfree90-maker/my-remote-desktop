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

# The workflow passes the real RDP user's Desktop.  The bot itself may run
# under the GitHub runner account, so we never rely on Path.home().
DESKTOP = Path(os.environ.get("RDP_DESKTOP", str(Path.home() / "Desktop"))).resolve()
TELEGRAM_DIR = DESKTOP / "Telegram"
NORMAL_DIR = DESKTOP / "ملفات عادية"
ANDROID_DIR = DESKTOP / "AndroidStudio"
ANDROID_PROJECTS = ANDROID_DIR / "Projects"
ANDROID_INCOMING = ANDROID_DIR / "Incoming"
ANDROID_APKS = ANDROID_DIR / "APKs"

for folder in (
    TELEGRAM_DIR,
    NORMAL_DIR,
    ANDROID_PROJECTS,
    ANDROID_INCOMING,
    ANDROID_APKS,
):
    folder.mkdir(parents=True, exist_ok=True)

bot = telebot.TeleBot(BOT_TOKEN)
lock = Lock()
mode = {ADMIN_ID: "normal"}


def allowed(message):
    return bool(message.from_user and message.from_user.id == ADMIN_ID)


def safe_name(name: str, fallback: str = "file") -> str:
    name = Path(name or fallback).name
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", name).strip(" .")
    return name or fallback


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    for i in range(1, 100000):
        candidate = path.with_name(f"{path.stem} ({i}){path.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError("Could not create a unique filename")


def menu():
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("🤖 رفع ملف Android Studio", callback_data="mode:android"))
    kb.add(types.InlineKeyboardButton("📁 رفع ملف Telegram", callback_data="mode:telegram"))
    kb.add(types.InlineKeyboardButton("📂 رفع ملف عادي", callback_data="mode:normal"))
    kb.add(types.InlineKeyboardButton("📍 حالة التخزين", callback_data="status"))
    return kb


def current_mode():
    return mode.get(ADMIN_ID, "normal")


def safe_extract_zip(zf: zipfile.ZipFile, destination: Path):
    destination = destination.resolve()
    total_uncompressed = 0
    max_total = 2 * 1024 * 1024 * 1024  # 2 GiB safety ceiling
    for member in zf.infolist():
        raw = member.filename.replace("\\", "/")
        if not raw or raw.endswith("/"):
            continue
        parts = Path(raw).parts
        if Path(raw).is_absolute() or ".." in parts:
            raise ValueError(f"Unsafe ZIP entry: {member.filename}")
        total_uncompressed += max(0, member.file_size)
        if total_uncompressed > max_total:
            raise ValueError("ZIP is too large after extraction")
        target = (destination / raw).resolve()
        if target != destination and destination not in target.parents:
            raise ValueError(f"Unsafe ZIP entry: {member.filename}")
        target.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(member, "r") as src, open(target, "wb") as dst:
            shutil.copyfileobj(src, dst)


def single_zip_root(zf: zipfile.ZipFile):
    names = [n.replace("\\", "/").lstrip("/") for n in zf.namelist() if n and not n.endswith("/")]
    if not names:
        return None
    roots = {n.split("/", 1)[0] for n in names if "/" in n}
    if len(roots) != 1:
        return None
    root = next(iter(roots))
    if all(n == root or n.startswith(root + "/") for n in names):
        return root
    return None


def looks_like_android_project(folder: Path) -> bool:
    markers = (
        "settings.gradle", "settings.gradle.kts",
        "build.gradle", "build.gradle.kts", "gradlew", "gradlew.bat", "app"
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
            root = single_zip_root(zf)
            safe_extract_zip(zf, temp_dir)
        source = temp_dir / root if root and (temp_dir / root).is_dir() else temp_dir
        if not looks_like_android_project(source):
            # Keep it anyway; the user may have a non-standard Android project.
            pass
        shutil.move(str(source), str(final_dir))
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        return final_dir
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise


def download_telegram_file(file_id):
    info = bot.get_file(file_id)
    return bot.download_file(info.file_path)


def save_data(data: bytes, folder: Path, name: str) -> Path:
    return_path = unique_path(folder / safe_name(name))
    return_path.parent.mkdir(parents=True, exist_ok=True)
    return_path.write_bytes(data)
    return return_path


def mode_folder():
    selected = current_mode()
    if selected == "android":
        return ANDROID_INCOMING
    if selected == "telegram":
        return TELEGRAM_DIR
    return NORMAL_DIR


@bot.message_handler(commands=["start", "menu", "help"])
def start(message):
    if not allowed(message):
        return
    bot.send_message(
        message.chat.id,
        "🖥️ <b>Windows RDP File Manager</b>\n\n"
        "اختار المكان اللي عايز ترفع فيه الملف:\n\n"
        "🤖 <b>Android Studio</b> → مشروع ZIP / APK / ملفات Android\n"
        "📁 <b>Telegram</b> → مجلد Telegram على سطح المكتب\n"
        "📂 <b>ملف عادي</b> → مجلد ملفات عادية على سطح المكتب\n\n"
        "📍 <b>حالة التخزين</b> تعرض المسارات الفعلية.",
        parse_mode="HTML",
        reply_markup=menu(),
    )


@bot.callback_query_handler(func=lambda call: call.data in {"mode:android", "mode:telegram", "mode:normal"})
def change_mode(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "غير مسموح")
        return
    selected = call.data.split(":", 1)[1]
    mode[ADMIN_ID] = selected
    labels = {
        "android": "🤖 Android Studio",
        "telegram": "📁 Telegram",
        "normal": "📂 ملفات عادية",
    }
    bot.answer_callback_query(call.id, "تم اختيار " + labels[selected])
    bot.send_message(
        call.message.chat.id,
        f"✅ تم اختيار: <b>{labels[selected]}</b>\n\nابعت الملف الآن، وهيتحفظ في المكان المحدد.",
        parse_mode="HTML",
        reply_markup=menu(),
    )


@bot.callback_query_handler(func=lambda call: call.data == "status")
def status(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "غير مسموح")
        return
    text = (
        "📍 <b>حالة التخزين</b>\n\n"
        f"🖥️ Desktop:\n<code>{DESKTOP}</code>\n\n"
        f"📁 Telegram:\n<code>{TELEGRAM_DIR}</code>\n\n"
        f"📂 ملفات عادية:\n<code>{NORMAL_DIR}</code>\n\n"
        f"🤖 Android Projects:\n<code>{ANDROID_PROJECTS}</code>\n\n"
        f"📱 APKs:\n<code>{ANDROID_APKS}</code>\n\n"
        f"📥 Android Incoming:\n<code>{ANDROID_INCOMING}</code>"
    )
    bot.answer_callback_query(call.id, "تم")
    bot.send_message(call.message.chat.id, text, parse_mode="HTML", reply_markup=menu())


@bot.message_handler(content_types=["document"])
def documents(message):
    if not allowed(message):
        return
    try:
        name = safe_name(message.document.file_name or "file")
        data = download_telegram_file(message.document.file_id)
        selected = current_mode()
        with lock:
            if selected == "android":
                if name.lower().endswith(".zip"):
                    incoming = save_data(data, ANDROID_INCOMING, name)
                    project = extract_android_project(incoming, Path(name).stem)
                    bot.reply_to(
                        message,
                        "✅ <b>تم رفع مشروع Android وتجهيزه</b>\n\n"
                        f"📦 ZIP: <code>{incoming}</code>\n"
                        f"📂 المشروع: <code>{project}</code>\n\n"
                        "افتح Android Studio ثم Open واختار مجلد المشروع.",
                        parse_mode="HTML",
                    )
                    return
                if name.lower().endswith(".apk"):
                    dest = save_data(data, ANDROID_APKS, name)
                    bot.reply_to(message, f"✅ تم رفع APK\n\n📱 {dest.name}\n📂 Desktop\\AndroidStudio\\APKs")
                    return
                dest = save_data(data, ANDROID_INCOMING, name)
                bot.reply_to(message, f"✅ تم رفع الملف\n\n📄 {dest.name}\n📂 Desktop\\AndroidStudio\\Incoming")
                return

            if selected == "telegram":
                dest = save_data(data, TELEGRAM_DIR, name)
                bot.reply_to(message, f"✅ تم رفع الملف\n\n📄 الاسم: {dest.name}\n📂 المكان: Desktop\\Telegram")
                return

            dest = save_data(data, NORMAL_DIR, name)
            bot.reply_to(message, f"✅ تم رفع الملف\n\n📄 الاسم: {dest.name}\n📂 المكان: Desktop\\ملفات عادية")
    except Exception as exc:
        bot.reply_to(message, f"❌ حصل خطأ أثناء حفظ الملف:\n{exc}")


@bot.message_handler(content_types=["photo", "video", "audio", "voice", "animation", "video_note"])
def media(message):
    if not allowed(message):
        return
    try:
        if message.content_type == "photo":
            file_id = message.photo[-1].file_id
            name = f"photo_{message.id}.jpg"
        elif message.content_type == "video":
            file_id = message.video.file_id
            name = message.video.file_name or f"video_{message.id}.mp4"
        elif message.content_type == "audio":
            file_id = message.audio.file_id
            name = message.audio.file_name or f"audio_{message.id}"
        elif message.content_type == "voice":
            file_id = message.voice.file_id
            name = f"voice_{message.id}.ogg"
        elif message.content_type == "animation":
            file_id = message.animation.file_id
            name = message.animation.file_name or f"animation_{message.id}.mp4"
        else:
            file_id = message.video_note.file_id
            name = f"video_note_{message.id}.mp4"
        data = download_telegram_file(file_id)
        with lock:
            dest = save_data(data, mode_folder(), name)
        bot.reply_to(message, f"✅ تم حفظ الملف\n\n📄 {dest.name}\n📂 <code>{dest.parent}</code>", parse_mode="HTML")
    except Exception as exc:
        bot.reply_to(message, f"❌ حصل خطأ أثناء حفظ الملف:\n{exc}")


@bot.message_handler(func=lambda m: bool(m.text) and not m.text.startswith("/"))
def links(message):
    if not allowed(message):
        return
    text = message.text.strip()
    if not re.match(r"^https?://", text, re.I):
        return
    dest = unique_path(mode_folder() / "رابط.url")
    dest.write_text("[InternetShortcut]\nURL=" + text + "\n", encoding="utf-8")
    bot.reply_to(message, f"🔗 تم حفظ اختصار الرابط\n\n📂 <code>{dest}</code>", parse_mode="HTML")


while True:
    try:
        bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=30)
    except Exception as exc:
        print(f"Telegram polling error: {exc!r}", flush=True)
        time.sleep(5)
