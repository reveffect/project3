import asyncio, logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from app import combine_cities

# Перед стартом необходимо запустить основное приложение!

# Инициализация бота
API_TOKEN = '7745898734:AAExhr_wpU2bATbGeZ_h9QJAZWGnDy6KvFo'
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


# Определение состояний для FSM
class Form(StatesGroup):
    start_point = State()
    end_point = State()
    days = State()
    inter = State()
    result = State()


# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    welcome_message = ("Привет! Я бот для проверки погоды по маршруту.\n\n"
        "Я могу:\n"
        "Получить прогноз погоды для точек маршрута.\n"
        "Предоставить прогноз на выбранный период и отобразить на графиках.\n"
        "Используй /help, чтобы узнать о доступных командах.")
    await message.reply(welcome_message)


# Команда /help
@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_message = (
        "Доступные команды:\n"
        "/start - Приветствие и описание возможностей бота\n"
        "/help - Список доступных команд и инструкция по использованию\n"
        "/weather - Запрос прогноза погоды по маршруту\n\n"
        "Использование команды /weather:\n"
        "1. Введи начальную точку маршрута.\n"
        "2. Введи конечную точку маршрута.\n"
        "3. Введи кол-во дней для прогноза (1 или 5).\n"
        "4. Добавь промежуточные точки (опционально)."
    )
    await message.reply(help_message)


# Команда /weather и первый город
@dp.message(Command("weather"))
async def cmd_weather(message: types.Message, state: FSMContext):
    await message.reply("Укажите первый город (например, Москва):")
    await state.set_state(Form.start_point)


# Последний город
@dp.message(Form.start_point)
async def process_start_point(message: types.Message, state: FSMContext):
    await state.update_data(start_point=message.text)
    await message.answer("Укажите последний город (например, Пенза):")
    await state.set_state(Form.end_point)


# Кол-во дней
@dp.message(Form.end_point)
async def process_end_point(message: types.Message, state: FSMContext):
    await state.update_data(end_point=message.text)
    await message.answer("Кол-во дней для прогноза (1 или 5):")
    await state.set_state(Form.days)


# Проверка на корректный ввод и запрос на промежуточные
@dp.message(Form.days)
async def process_days(message: types.Message, state: FSMContext):
    if message.text not in ['1', '5']:
        wrong_message = "Некорректный ввод! Число дней будет равно 5."
        await message.reply(wrong_message)
        await state.update_data(days='5')
    else:
        await state.update_data(days=message.text)

    answer_message = "Ввести промежуточные города?"
    await message.answer(answer_message, reply_markup=inter_keyboard())


# Выбор промежуточных
@dp.callback_query(Form.days)
async def process_callback(callback_query: types.CallbackQuery, state: FSMContext):
    data = callback_query.data
    if data == 'y':
        reply_text = "Введите промежуточные точки через пробел (например, Воронеж Рязань Тула):"
        await callback_query.message.answer(reply_text)
        await state.set_state(Form.inter)
    else:
        reply_text = "Промежуточные точки не добавлены."
        await callback_query.message.answer(reply_text)
        user_data = await state.get_data()
        start_point = user_data.get('start_point')
        end_point = user_data.get('end_point')
        days = user_data.get('days')

        try:
            weather_data_list, city_names = combine_cities(start_point, [], end_point, days)
            visualization_link = "http://127.0.0.1:5000/dashboard"
            response_message = (
                f"Первый город: {start_point}\n"
                f"Последний город: {end_point}\n"
                f"Кол-во дней: {days}\n"
                f"Ссылка на визуализацию: {visualization_link}"
            )
        except Exception:
            response_message = "Некорректный ввод"

        await callback_query.message.answer(response_message)
        await state.clear()

    await callback_query.answer()


# Обработка с промежуточными
@dp.message(Form.inter)
async def process_inter(message: types.Message, state: FSMContext):
    await state.update_data(inter=message.text)
    user_data = await state.get_data()
    start_point = user_data.get('start_point')
    end_point = user_data.get('end_point')
    days = user_data.get('days')
    inter = user_data.get('inter')

    try:
        weather_data_list, city_names = combine_cities(start_point, inter.split(), end_point, days)
        visualization_link = "http://127.0.0.1:5000/dashboard"
        response_message = (
            f"Первый город: {start_point}\n"
            f"Последний город: {end_point}\n"
            f"Кол-во дней: {days}\n"
            f"Промежуточные точки: {inter}\n"
            f"Ссылка на визуализацию: {visualization_link}"
        )
    except Exception:
        response_message = "Некорректный ввод"

    await message.answer(response_message)
    await state.clear()


def inter_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="Да", callback_data='y')],
        [InlineKeyboardButton(text="Нет", callback_data='n')]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def days_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="1 день", callback_data='1')],
        [InlineKeyboardButton(text="3 дня", callback_data='3')],
        [InlineKeyboardButton(text="5 дней", callback_data='5')]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# Старт бота
async def start_telegram_bot():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(start_telegram_bot())
