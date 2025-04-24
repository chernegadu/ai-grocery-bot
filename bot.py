import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from openai import OpenAI

# === 🔐 Настройки ключей и доступа ===
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
OWNER_ID = int(os.environ.get("OWNER_ID", "178564204"))
ALLOWED_USERS = [OWNER_ID]

client = OpenAI(api_key=OPENAI_API_KEY)
shopping_list = []

# === 🌌 Команда /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        await update.message.reply_text("\u26d4\ufe0f Доступ запрещён.")
        return
    await update.message.reply_text("Привет! Напиши, что нужно купить — я запомню.")

# === 🔑 Команда /add_user <id> ===
async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("\u26d4\ufe0f Только владелец может добавлять пользователей.")
        return

    if not context.args:
        await update.message.reply_text("Используй команду так:\n`/add_user 987654321`", parse_mode="Markdown")
        return

    try:
        user_id = int(context.args[0])
        if user_id not in ALLOWED_USERS:
            ALLOWED_USERS.append(user_id)
            await update.message.reply_text(f"\u2705 Пользователь с ID {user_id} добавлен.")
        else:
            await update.message.reply_text("\u26a0\ufe0f Этот пользователь уже есть в списке.")
    except ValueError:
        await update.message.reply_text("\u274c Неверный формат ID. Введите число.")

# === 🧠 Обработка сообщений ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        await update.message.reply_text("\u26d4\ufe0f Доступ запрещён.")
        return

    user_text = update.message.text.lower()

    if user_text.startswith("удали ") or user_text.startswith("убери "):
        item = user_text.replace("удали ", "").replace("убери ", "").strip()
        if item in shopping_list:
            shopping_list.remove(item)
            await update.message.reply_text(f"\u274c Удалил: {item}")
        else:
            await update.message.reply_text("Такого продукта нет в списке.")
        return

    if "список" in user_text:
        if shopping_list:
            await update.message.reply_text("\ud83d\uded2 Твой список:\n" + "\n".join(f"• {item}" for item in shopping_list))
        else:
            await update.message.reply_text("Список пуст.")
        return

    if "очисти" in user_text or "удали всё" in user_text:
        shopping_list.clear()
        await update.message.reply_text("\ud83e\udea9 Список очищен.")
        return

    keywords = ["купи", "нужно", "добавь", "в список", "надо", "приобрести"]
    if any(word in user_text for word in keywords):
        prompt = f"Ты — помощник по покупкам. Пользователь написал: \"{user_text}\". Выдели список покупок через запятую, без пояснений."

        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100
            )
            items = response.choices[0].message.content.strip().split(",")
            items = [item.strip() for item in items if item.strip()]
            shopping_list.extend(items)
            await update.message.reply_text("\u2705 Добавлено:\n" + "\n".join(f"• {item}" for item in items))
        except Exception as e:
            await update.message.reply_text(f"\u26a0\ufe0f Ошибка от OpenAI:\n{e}")
    else:
        await update.message.reply_text("\ud83e\udde0 Не распознано как список покупок. Скажи, что нужно купить.")

# === 🚀 Запуск бота ===
app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("add_user", add_user))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.run_polling()
