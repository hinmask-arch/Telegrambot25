import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import firebase_admin
from firebase_admin import credentials, firestore
import os
import json

# Логирование
logging.basicConfig(level=logging.INFO)

# --- Telegram Token ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# --- Firebase ---
firebase_key = json.loads(os.getenv("FIREBASE_CREDENTIALS"))  # ключ из переменной окружения
cred = credentials.Certificate(firebase_key)
firebase_admin.initialize_app(cred)
db = firestore.client()

# --- Состояния анкеты ---
QUESTION1, QUESTION2, QUESTION3, QUESTION4, PHOTO = range(5)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Используй /new для создания анкеты, /list для просмотра.")

async def new_form(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Вопрос 1: Введи свой ответ.")
    return QUESTION1

async def question1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["question1"] = update.message.text
    await update.message.reply_text("Вопрос 2:")
    return QUESTION2

async def question2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["question2"] = update.message.text
    await update.message.reply_text("Вопрос 3:")
    return QUESTION3

async def question3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["question3"] = update.message.text
    await update.message.reply_text("Вопрос 4:")
    return QUESTION4

async def question4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["question4"] = update.message.text
    await update.message.reply_text("Отправь фото (или /skip).")
    return PHOTO

async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_id = update.message.photo[-1].file_id
    context.user_data["photo"] = photo_id

    user_id = str(update.message.from_user.id)
    form_ref = db.collection("users").document(user_id).collection("forms").document()
    form_ref.set(context.user_data)

    await update.message.reply_text("Анкета сохранена!")
    return ConversationHandler.END

async def skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    form_ref = db.collection("users").document(user_id).collection("forms").document()
    form_ref.set(context.user_data)

    await update.message.reply_text("Анкета сохранена без фото!")
    return ConversationHandler.END

async def list_forms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    forms = db.collection("users").document(user_id).collection("forms").stream()
    text = "Ваши анкеты:\n"
    for f in forms:
        data = f.to_dict()
        text += f"- {data.get('question1', '')}, {data.get('question2', '')}\n"
    await update.message.reply_text(text)

# --- Application ---
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("new", new_form)],
    states={
        QUESTION1: [MessageHandler(filters.TEXT & ~filters.COMMAND, question1)],
        QUESTION2: [MessageHandler(filters.TEXT & ~filters.COMMAND, question2)],
        QUESTION3: [MessageHandler(filters.TEXT & ~filters.COMMAND, question3)],
        QUESTION4: [MessageHandler(filters.TEXT & ~filters.COMMAND, question4)],
        PHOTO: [
            MessageHandler(filters.PHOTO, photo),
            CommandHandler("skip", skip_photo)
        ],
    },
    fallbacks=[CommandHandler("cancel", skip_photo)]
)

app.add_handler(CommandHandler("start", start))
app.add_handler(conv_handler)
app.add_handler(CommandHandler("list", list_forms))

from flask import Flask, request

flask_app = Flask(__name__)

@flask_app.route("/", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), app.bot)
    app.update_queue.put(update)
    return "ok"

if __name__ == "__main__":
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
