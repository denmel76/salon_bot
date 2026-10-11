import asyncio
import logging
import requests
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from supabase import create_client
from config import TOKEN, YANDEX_KEY, YANDEX_FOLDER, SUPABASE_URL, SUPABASE_KEY

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

USLUGI = {
    "manicure": "Маникюр — 1500 руб",
    "pedicure": "Педикюр — 2000 руб",
    "narashivanie": "Наращивание — 3000 руб",
    "korrekciya": "Коррекция — 1800 руб",
    "gel": "Гель-лак — 1000 руб",
    "strizhka": "Стрижка — 1200 руб",
    "okrashivanie": "Окрашивание — 3500 руб",
    "ukladka": "Укладка — 800 руб",
}

class Zap(StatesGroup):
    usluga = State()
    date = State()
    time = State()
    name = State()
    phone = State()

def menu_kb():
    kb = InlineKeyboardBuilder()
    for k, v in USLUGI.items():
        kb.button(text=v.split(" — ")[0], callback_data=f"us_{k}")
    kb.adjust(2)
    return kb.as_markup()

def date_kb():
    kb = InlineKeyboardBuilder()
    for i in range(1, 8):
        d = (datetime.now() + timedelta(days=i)).strftime("%d.%m")
        kb.button(text=d, callback_data=f"d_{d}")
    kb.adjust(3)
    return kb.as_markup()

def time_kb():
    kb = InlineKeyboardBuilder()
    for t in ["10:00", "12:00", "14:00", "16:00", "18:00", "20:00"]:
        kb.button(text=t, callback_data=f"t_{t}")
    kb.adjust(3)
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

@dp.message(Command("admin"))
async def admin(m: types.Message):
    try:
        r = supabase.table("zapisi").select("*").order("id", desc=True).limit(20).execute()
        rows = r.data
        if not rows:
            await m.answer("Записей нет.")
            return
        text = "📋 Записи:\n\n"
        for r in rows:
            text += f"{r['date']} {r['time']} — {r['usluga']}, {r['name']}, {r['phone']}\n"
        await m.answer(text)
    except Exception as e:
        await m.answer(f"Ошибка: {e}")

@dp.callback_query(F.data.startswith("us_"))
async def us(c: types.CallbackQuery, state: FSMContext):
    u = USLUGI.get(c.data[3:], "?")
    await state.update_data(usluga=u)
    await c.message.answer(f"Выбрано: {u}\nВыберите дату:", reply_markup=date_kb())
    await c.answer()

@dp.callback_query(F.data.startswith("d_"))
async def dt(c: types.CallbackQuery, state: FSMContext):
    await state.update_data(date=c.data[2:])
    await c.message.answer("Выберите время:", reply_markup=time_kb())
    await c.answer()

@dp.callback_query(F.data.startswith("t_"))
async def tm(c: types.CallbackQuery, state: FSMContext):
    await state.update_data(time=c.data[2:])
    await c.message.answer("Введите ваше имя:")
    await state.set_state(Zap.name)
    await c.answer()

@dp.message(Zap.name)
async def nm(m: types.Message, state: FSMContext):
    await state.update_data(name=m.text)
    await m.answer("Введите телефон:")
    await state.set_state(Zap.phone)

@dp.message(Zap.phone)
async def ph(m: types.Message, state: FSMContext):
    await state.update_data(phone=m.text)
    d = await state.get_data()
    try:
        supabase.table("zapisi").insert({
            "date": d["date"],
            "time": d["time"],
            "usluga": d["usluga"],
            "name": d["name"],
            "phone": d["phone"],
            "user_id": m.from_user.id
        }).execute()
        await m.answer(
            f"✅ Запись оформлена!\n\n"
            f"Услуга: {d['usluga']}\n"
            f"Дата: {d['date']}\n"
            f"Время: {d['time']}\n"
            f"Имя: {d['name']}\n"
            f"Телефон: {d['phone']}"
        )
    except Exception as e:
        await m.answer(f"Ошибка записи: {e}")
    await state.clear()

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
