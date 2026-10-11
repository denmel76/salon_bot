import asyncio
import logging
import requests
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import TOKEN, YANDEX_KEY, YANDEX_FOLDER

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

USLUGI = {
    "manicure": "Маникюр — 1500 руб (1.5 ч)",
    "pedicure": "Педикюр — 2000 руб (2 ч)",
    "narashivanie": "Наращивание — 3000 руб (2.5 ч)",
    "korrekciya": "Коррекция — 1800 руб (1.5 ч)",
    "gel": "Гель-лак — 1000 руб (1 ч)",
    "strizhka": "Стрижка — 1200 руб (1 ч)",
    "okrashivanie": "Окрашивание — 3500 руб (2.5 ч)",
    "ukladka": "Укладка — 800 руб (40 мин)",
}

def menu_kb():
    kb = InlineKeyboardBuilder()
    for k, v in USLUGI.items():
        kb.button(text=v.split(" — ")[0], callback_data=f"us_{k}")
    kb.adjust(2)
    return kb.as_markup()

def ask_yandex(q):
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {"Authorization": f"Api-Key {YANDEX_KEY}", "Content-Type": "application/json"}
    data = {
        "modelUri": f"gpt://{YANDEX_FOLDER}/yandexgpt-lite",
        "completionOptions": {"temperature": 0.5, "maxTokens": 500},
        "messages": [
            {"role": "system", "text": "Ты — вежливый администратор салона «Красота»."},
            {"role": "user", "text": q}
        ]
    }
    r = requests.post(url, headers=headers, json=data, timeout=30)
    if r.status_code == 200:
        return r.json()["result"]["alternatives"][0]["message"]["text"]
    return None

@dp.message(Command("start"))
async def start(m: types.Message):
    await m.answer(
        f"Здравствуйте, {m.from_user.first_name}!\n\n"
        "Я бот салона «Красота».\nВыберите услугу:",
        reply_markup=menu_kb()
    )

@dp.message(Command("price"))
async def price(m: types.Message):
    text = "💅 Прайс:\n\n"
    for v in USLUGI.values():
        text += f"• {v}\n"
    await m.answer(text)

@dp.message(Command("contacts"))
async def contacts(m: types.Message):
    await m.answer("📍 ул. Ленина 15\n🕐 с 9 до 21\n📞 +7 999 123-45-67")

@dp.callback_query(F.data.startswith("us_"))
async def us(c: types.CallbackQuery):
    u = USLUGI.get(c.data[3:], "?")
    await c.message.answer(f"Выбрано: {u}")
    await c.answer()

@dp.message()
async def ai(m: types.Message):
    await m.answer("Думаю...")
    a = ask_yandex(m.text)
    await m.answer(a if a else "Уточню у администратора.")

async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
