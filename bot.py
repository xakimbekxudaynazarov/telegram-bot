import asyncio
import re

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

TOKEN = "85293055:AAjk-3n7VkklDliXrd63_RTdm5zvD8SxUvP"
ADMIN_ID = 56222156 # 👈 admin Telegram ID

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())


# 🔹 STATE
class OrderState(StatesGroup):
    name = State()
    phone = State()


# 🔹 START
@dp.message(CommandStart())
async def start_handler(message: Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📄 Xizmatlar")],
            [KeyboardButton(text="📞 Aloqa")]
        ],
        resize_keyboard=True
    )

    await message.answer(
        "Assalomu alaykum! 👋\n\nXizmat botiga xush kelibsiz!",
        reply_markup=kb
    )


# 🔹 XIZMATLAR MENYU
@dp.message(F.text == "📄 Xizmatlar")
async def xizmatlar(message: Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📑 Hujjat tayyorlash")],
            [KeyboardButton(text="🏢 Yagona darcha")],
            [KeyboardButton(text="✈️ Aviabiletlar")],
            [KeyboardButton(text="⬅️ Orqaga")]
        ],
        resize_keyboard=True
    )

    await message.answer("Xizmatni tanlang 👇", reply_markup=kb)


# 🔹 XIZMAT TANLASH
@dp.message(F.text.in_(["📑 Hujjat tayyorlash", "🏢 Yagona darcha", "✈️ Aviabiletlar"]))
async def choose_service(message: Message, state: FSMContext):
    await state.update_data(service=message.text)
    await message.answer("Ismingizni kiriting:")
    await state.set_state(OrderState.name)


# 🔹 ALOQA
@dp.message(F.text == "📞 Aloqa")
async def aloqa(message: Message):
    await message.answer("Bog‘lanish uchun:\n👉 @xakimbek0710")


# 🔹 ORQAGA
@dp.message(F.text == "⬅️ Orqaga")
async def back(message: Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📄 Xizmatlar")],
            [KeyboardButton(text="📞 Aloqa")]
        ],
        resize_keyboard=True
    )
    await message.answer("Bosh menyu", reply_markup=kb)


# 🔹 ISM
@dp.message(OrderState.name)
async def get_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Telefon raqamingizni kiriting:\n📌 Format: +998901234567")
    await state.set_state(OrderState.phone)


# 🔹 TELEFON
@dp.message(OrderState.phone)
async def get_phone(message: Message, state: FSMContext):
    phone = message.text.strip()

    # 🔍 FORMAT TEKSHIRISH
    pattern = r"^\+998\d{9}$"

    if not re.match(pattern, phone):
        await message.answer(
            "❌ Noto‘g‘ri format!\n\n"
            "📌 To‘g‘ri yozing:\n+998901234567"
        )
        return

    data = await state.get_data()

    text = (
        "📥 YANGI BUYURTMA:\n\n"
        f"🧾 Xizmat: {data['service']}\n"
        f"👤 Ism: {data['name']}\n"
        f"📞 Telefon: {phone}"
    )

    # 🔥 ADMIN GA YUBORISH
    await bot.send_message(chat_id=ADMIN_ID, text=text)

    # 👤 FOYDALANUVCHIGA
    await message.answer("✅ Buyurtmangiz qabul qilindi!\nTez orada bog‘lanamiz.")

    await state.clear()


# 🔹 RUN
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
