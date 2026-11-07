import asyncio
import logging
import sqlite3
from flask import Flask
import threading
import os

# Создаем фейковый веб-сервер
app_web = Flask(__name__)

@app_web.route('/')
def health():
    return "Bot is running!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app_web.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

BOT_TOKEN = "9221569522:AAFp9XInJLAMOdJ-2_Q03fWQW7JPwoy9tcg"
ADMIN_ID = 6467020677 # <--- ВСТАВЬ СЮДА СВОЙ ID (ТОЛЬКО ЦИФРЫ)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- БАЗА ДАННЫХ ---
# Функция для подключения к базе
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    # Создаем таблицу, если ее нет (ID, Имя, Дата регистрации)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Функция для сохранения пользователя
def save_user(user_id, username, first_name):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    # INSERT OR IGNORE добавит только новых, старых не тронет
    cursor.execute('INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)', 
                   (user_id, username, first_name))
    conn.commit()
    conn.close()

# --- КЛАВИАТУРЫ ---
def main_menu():
    kb = [
        [KeyboardButton(text="🛒 Услуги и цены")],
        [KeyboardButton(text="💬 Задать вопрос"), KeyboardButton(text="📞 Связаться с нами")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def services_inline():
    builder = InlineKeyboardBuilder()
    builder.button(text="Разработка сайта", callback_data="service_site")
    builder.button(text="Дизайн логотипа", callback_data="service_logo")
    builder.button(text="Настройка рекламы", callback_data="service_ads")
    builder.adjust(1)
    return builder.as_markup()

# --- ОБРАБОТЧИКИ ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # СОХРАНЯЕМ ПОЛЬЗОВАТЕЛЯ В БАЗУ
    save_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    
    await message.answer(
        f"👋 Здравствуйте, {message.from_user.first_name}!\n"
        "Я — ваш виртуальный консультант. Чем я могу вам помочь сегодня?",
        reply_markup=main_menu()
    )

@dp.message(F.text == "🛒 Услуги и цены")
async def show_services(message: types.Message):
    await message.answer("Выберите интересующую вас услугу:", reply_markup=services_inline())

@dp.callback_query(F.data.startswith("service_"))
async def process_service(callback: types.CallbackQuery):
    service = callback.data.split("_")[1]
    if service == "site":
        text = "🌐 Разработка сайта: от 15 000 руб."
    elif service == "logo":
        text = "🎨 Дизайн логотипа: от 3 000 руб."
    elif service == "ads":
        text = "📈 Настройка рекламы: от 10 000 руб."
        
    await callback.answer()
    await callback.message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "📞 Связаться с нами")
async def contact(message: types.Message):
    await message.answer("📩 Напишите нашему менеджеру: @xuujs77838")

@dp.message(F.text == "💬 Задать вопрос")
async def ask_question(message: types.Message):
    await message.answer("Напишите ваш вопрос, и я передам его оператору.")

# Ловим любой текст и сохраняем (на будущее)
@dp.message(F.text)
async def echo_handler(message: types.Message):
    # Отправляем сообщение пользователю, что мы его приняли
    await message.answer(
        "Спасибо за ваш вопрос! Мы свяжемся с вами в ближайшее время.", 
        reply_markup=main_menu()
    )
    
    # А теперь пересылаем вопрос тебе в личку (Админу)
    try:
        admin_text = (
            f"🚨 НОВАЯ ЗАЯВКА!\n\n"
            f"👤 От: {message.from_user.first_name} (@{message.from_user.username})\n"
            f"🆔 ID: {message.from_user.id}\n\n"
            f"💬 Сообщение: {message.text}"
        )
        await bot.send_message(chat_id=ADMIN_ID, text=admin_text, parse_mode="Markdown")
    except Exception as e:
        print(f"Не удалось отправить сообщение админу: {e}")
# --- АДМИН-ПАНЕЛЬ ---
@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    # Проверяем, что команду ввел именно ты (Админ)
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У вас нет доступа к этой команде.")
        return

    # Подключаемся к базе и берем всех пользователей
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, first_name FROM users")
    users = cursor.fetchall()
    conn.close()

    # Формируем отчет
    total_users = len(users)
    report = f"📊 СТАТИСТИКА БОТА\n\n"
    report += f"👥 Всего пользователей: {total_users}\n\n"
    
    if total_users > 0:
        report += "📋 Список последних 10 пользователей:\n"
        # Берем последних 10 добавленных
        for user in users[-10:]:
            user_id, username, first_name = user
            # Если у человека нет юзернейма, пишем "нет"
            uname = f"@{username}" if username else "нет"
            report += f"• {first_name} ({uname}) | ID: {user_id}\n"
            
    await message.answer(report, parse_mode="Markdown")
async def main():
    if __name__ == "__main__":
    # Запускаем бота в фоновом потоке
        import threading
    threading.Thread(target=lambda: asyncio.run(main()), daemon=True).start()

    # Запускаем веб-сервер в главном потоке, чтобы Render видел порт
    port = int(os.environ.get("PORT", 10000))
    app_web.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    asyncio.run(main())
