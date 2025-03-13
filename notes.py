import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import schedule
import time
import threading
from datetime import datetime

# Список разрешенных пользователей
ALLOWED_USERS = {123456789}  # Замени на свои ID

# Логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Функция для проверки доступа
def is_allowed(update: Update):
    return update.message.from_user.id in ALLOWED_USERS

# Создание клавиатуры с меню
def get_main_keyboard():
    return ReplyKeyboardMarkup([
        ['📝 Добавить заметку', '📋 Посмотреть заметки'],
        ['⏰ Установить напоминание', '🗑️ Удалить заметку'],
        ['✏️ Редактировать заметку', '❌ Удалить напоминание'],
        ['📅 Посмотреть напоминания']
    ], resize_keyboard=True)

# Креативное приветствие
async def start(update: Update, context: CallbackContext):
    if not is_allowed(update):
        await update.message.reply_text("🚫 Доступ запрещен.")
        return
    welcome_text = (
        "🌟 Привет! Я твой личный помощник. 🌟\n\n"
        "Я помогу тебе управлять заметками и напоминаниями. Вот что я умею:\n"
        "📝 Добавлять заметки\n"
        "📋 Показывать все заметки\n"
        "⏰ Устанавливать напоминания\n"
        "🗑️ Удалять заметки\n"
        "✏️ Редактировать заметки\n"
        "❌ Удалять напоминания\n"
        "📅 Показывать все напоминания\n\n"
        "Выбери действие:"
    )
    await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard())

# Обработка текстовых сообщений
async def handle_message(update: Update, context: CallbackContext):
    if not is_allowed(update):
        await update.message.reply_text("🚫 Доступ запрещен.")
        return

    text = update.message.text

    if text == '📝 Добавить заметку':
        await update.message.reply_text("Введите текст заметки:")
        context.user_data['awaiting_note'] = True
    elif text == '📋 Посмотреть заметки':
        await view_notes(update, context)
    elif text == '⏰ Установить напоминание':
        await update.message.reply_text("Введите дату, время и текст напоминания в формате: YYYY-MM-DD HH:MM текст")
        context.user_data['awaiting_reminder'] = True
    elif text == '🗑️ Удалить заметку':
        await update.message.reply_text("Введите номер заметки для удаления:")
        context.user_data['awaiting_note_delete'] = True
    elif text == '✏️ Редактировать заметку':
        await update.message.reply_text("Введите номер заметки и новый текст в формате: номер текст")
        context.user_data['awaiting_note_edit'] = True
    elif text == '❌ Удалить напоминание':
        await update.message.reply_text("Введите номер напоминания для удаления:")
        context.user_data['awaiting_reminder_delete'] = True
    elif text == '📅 Посмотреть напоминания':
        await view_reminders(update, context)
    elif context.user_data.get('awaiting_note'):
        await add_note(update, context)
        context.user_data['awaiting_note'] = False
    elif context.user_data.get('awaiting_reminder'):
        await set_reminder(update, context)
        context.user_data['awaiting_reminder'] = False
    elif context.user_data.get('awaiting_note_delete'):
        await delete_note(update, context)
        context.user_data['awaiting_note_delete'] = False
    elif context.user_data.get('awaiting_note_edit'):
        await edit_note(update, context)
        context.user_data['awaiting_note_edit'] = False
    elif context.user_data.get('awaiting_reminder_delete'):
        await delete_reminder(update, context)
        context.user_data['awaiting_reminder_delete'] = False
    else:
        await update.message.reply_text("Используйте кнопки для навигации.")

# Добавление заметки
async def add_note(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    note = update.message.text.strip()
    if user_id not in context.user_data:
        context.user_data[user_id] = {'notes': [], 'reminders': []}
    context.user_data[user_id]['notes'].append(note)
    await update.message.reply_text("✅ Заметка добавлена!", reply_markup=get_main_keyboard())

# Просмотр заметок
async def view_notes(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id in context.user_data and context.user_data[user_id]['notes']:
        notes = "\n".join([f"{i+1}. {note}" for i, note in enumerate(context.user_data[user_id]['notes'])])
        await update.message.reply_text(f"📋 Ваши заметки:\n{notes}", reply_markup=get_main_keyboard())
    else:
        await update.message.reply_text("📭 У вас пока нет заметок.", reply_markup=get_main_keyboard())

# Удаление заметки
async def delete_note(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    try:
        note_index = int(update.message.text.strip()) - 1
        if user_id in context.user_data and 0 <= note_index < len(context.user_data[user_id]['notes']):
            deleted_note = context.user_data[user_id]['notes'].pop(note_index)
            await update.message.reply_text(f"🗑️ Заметка удалена: {deleted_note}", reply_markup=get_main_keyboard())
        else:
            await update.message.reply_text("❌ Неверный номер заметки.", reply_markup=get_main_keyboard())
    except ValueError:
        await update.message.reply_text("❌ Введите корректный номер заметки.", reply_markup=get_main_keyboard())

# Редактирование заметки
async def edit_note(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    try:
        parts = update.message.text.strip().split(maxsplit=1)
        note_index = int(parts[0]) - 1
        new_text = parts[1]
        if user_id in context.user_data and 0 <= note_index < len(context.user_data[user_id]['notes']):
            context.user_data[user_id]['notes'][note_index] = new_text
            await update.message.reply_text(f"✏️ Заметка изменена: {new_text}", reply_markup=get_main_keyboard())
        else:
            await update.message.reply_text("❌ Неверный номер заметки.", reply_markup=get_main_keyboard())
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Введите корректный номер и текст заметки.", reply_markup=get_main_keyboard())

# Установка напоминания
async def set_reminder(update: Update, context: CallbackContext):
    try:
        parts = update.message.text.strip().split(maxsplit=2)
        date_str, time_str, reminder_text = parts[0], parts[1], parts[2]
        reminder_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        now = datetime.now()

        if reminder_datetime < now:
            await update.message.reply_text("❌ Нельзя установить напоминание на прошедшее время.", reply_markup=get_main_keyboard())
            return

        delay = (reminder_datetime - now).total_seconds()
        threading.Timer(delay, lambda: context.bot.send_message(update.message.chat_id, f"⏰ Напоминание: {reminder_text}")).start()

        if 'reminders' not in context.user_data[update.message.from_user.id]:
            context.user_data[update.message.from_user.id]['reminders'] = []
        context.user_data[update.message.from_user.id]['reminders'].append(f"{date_str} {time_str}: {reminder_text}")

        await update.message.reply_text(f"✅ Напоминание установлено на {date_str} {time_str}.", reply_markup=get_main_keyboard())
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Используйте формат: YYYY-MM-DD HH:MM текст напоминания", reply_markup=get_main_keyboard())

# Просмотр напоминаний
async def view_reminders(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id in context.user_data and 'reminders' in context.user_data[user_id] and context.user_data[user_id]['reminders']:
        reminders = "\n".join([f"{i+1}. {reminder}" for i, reminder in enumerate(context.user_data[user_id]['reminders'])])
        await update.message.reply_text(f"📅 Ваши напоминания:\n{reminders}", reply_markup=get_main_keyboard())
    else:
        await update.message.reply_text("📭 У вас пока нет напоминаний.", reply_markup=get_main_keyboard())

# Удаление напоминания
async def delete_reminder(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    try:
        reminder_index = int(update.message.text.strip()) - 1
        if user_id in context.user_data and 'reminders' in context.user_data[user_id] and 0 <= reminder_index < len(context.user_data[user_id]['reminders']):
            deleted_reminder = context.user_data[user_id]['reminders'].pop(reminder_index)
            await update.message.reply_text(f"❌ Напоминание удалено: {deleted_reminder}", reply_markup=get_main_keyboard())
        else:
            await update.message.reply_text("❌ Неверный номер напоминания.", reply_markup=get_main_keyboard())
    except ValueError:
        await update.message.reply_text("❌ Введите корректный номер напоминания.", reply_markup=get_main_keyboard())

# Запуск планировщика напоминаний
def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

# Основная функция
def main():
    # Вставь сюда свой токен
    application = Application.builder().token("YOUR_TELEGRAM_BOT_TOKEN").build()

    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Запускаем планировщик в отдельном потоке
    threading.Thread(target=run_scheduler, daemon=True).start()

    # Запускаем бота
    application.run_polling()

if __name__ == '__main__':
    main()