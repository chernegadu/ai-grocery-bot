
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from openai import OpenAI
from fpdf import FPDF

# === 🔐 Настройки ключей и доступа ===
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
OWNER_ID = int(os.environ.get("OWNER_ID", "178564204"))
ALLOWED_USERS = [OWNER_ID]

client = OpenAI(api_key=OPENAI_API_KEY)
shopping_list = []

# === 📂 Команда /start с кнопками ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        await update.message.reply_text("⛔️ Доступ запрещён.")
        return

    keyboard = [
        [InlineKeyboardButton("🛒 Показать список", callback_data='show')],
        [InlineKeyboardButton("🧹 Очистить список", callback_data='clear')],
        [InlineKeyboardButton("📄 PDF-версия", callback_data='pdf')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Привет! Я твой бот-консьерж. Выбери действие:", reply_markup=reply_markup)

# === 🔑 Команда /add_user <id> ===
async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⛔️ Только владелец может добавлять пользователей.")
        return

    if not context.args:
        await update.message.reply_text("Используй команду так:\n`/add_user 987654321`", parse_mode="Markdown")
        return

    try:
        user_id = int(context.args[0])
        if user_id not in ALLOWED_USERS:
            ALLOWED_USERS.append(user_id)
            await update.message.reply_text(f"✅ Пользователь с ID {user_id} добавлен.")
        else:
            await update.message.reply_text("⚠️ Этот пользователь уже есть в списке.")
    except ValueError:
        await update.message.reply_text("❌ Неверный формат ID. Введите число.")

# === 🧠 Обработка текстовых сообщений ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        await update.message.reply_text("⛔️ Доступ запрещён.")
        return

    user_text = update.message.text.lower()

    if user_text.startswith("удали ") or user_text.startswith("убери "):
        item = user_text.replace("удали ", "").replace("убери ", "").strip()
        if item in shopping_list:
            shopping_list.remove(item)
            await update.message.reply_text(f"❌ Удалил: {item}")
        else:
            await update.message.reply_text("Такого продукта нет в списке.")
        return

    if "список" in user_text:
        if shopping_list:
            await update.message.reply_text("🛒 Твой список:\n" + "\n".join(f"• {item}" for item in shopping_list))
        else:
            await update.message.reply_text("Список пуст.")
        return

    if "очисти" in user_text or "удали всё" in user_text:
        shopping_list.clear()
        await update.message.reply_text("🧹 Список очищен.")
        return

    prompt keywords = ["купи", "нужно", "добавь", "в список", "надо", "приобрести"]

if any(word in user_text for word in keywords):
    prompt = f"""Ты — помощник по покупкам. Пользователь написал: \"{user_text}\". 
    Выдели список покупок через запятую, без пояснений."""

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100
        )
        items = response.choices[0].message.content.strip().split(",")
        items = [item.strip() for item in items if item.strip()]
        shopping_list.extend(items)

        await update.message.reply_text("✅ Добавлено:\n" + "\n".join(f"• {item}" for item in items))
    except Exception as e:
        await update.message.reply_text(f"⚠️ Ошибка от OpenAI:\n{e}")
else:
    await update.message.reply_text("🤖 Не распознано как список покупок. Скажи, что нужно купить.")

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100
        )
        items = response.choices[0].message.content.strip().split(",")
        items = [item.strip() for item in items if item.strip()]
        shopping_list.extend(items)
        await update.message.reply_text("✅ Добавлено:\n" + "\n".join(f"• {item}" for item in items))
    except Exception as e:
        await update.message.reply_text(f"⚠️ Ошибка от OpenAI:\n{e}")

# === 🛂 Обработка кнопок ===
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id not in ALLOWED_USERS:
        await query.edit_message_text("⛔️ Доступ запрещён.")
        return

    if query.data == 'show':
        text = "\n".join(f"• {item}" for item in shopping_list) or "Список пуст."
        await query.edit_message_text(f"🛒 Список:\n{text}")
    elif query.data == 'clear':
        shopping_list.clear()
        await query.edit_message_text("🧹 Список очищен.")
    elif query.data == 'pdf':
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, "\n".join(f"• {item}" for item in shopping_list) or "Список пуст.")
        pdf.output("shopping_list.pdf")
        await query.edit_message_text("📄 PDF сохранён как `shopping_list.pdf`.")

# === 🚀 Запуск бота ===
app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("add_user", add_user))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(button_handler))
app.run_polling()
