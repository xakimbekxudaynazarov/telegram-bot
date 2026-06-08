import asyncio
import html
import logging
import os
import re
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

# ==================== LOGGING ====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ==================== ENV ====================
load_dotenv()

TOKEN = os.getenv("TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

if not TOKEN:
    raise ValueError("TOKEN topilmadi! .env faylni tekshiring.")
if not ADMIN_ID:
    raise ValueError("ADMIN_ID topilmadi! .env faylni tekshiring.")

try:
    ADMIN_ID = int(ADMIN_ID)
except ValueError:
    raise ValueError("ADMIN_ID butun son bo'lishi kerak!")

# ==================== BOT ====================
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ==================== FILES / GLOBALS ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ORDER_FILE = os.path.join(BASE_DIR, "order_counter.txt")
order_lock = asyncio.Lock()

# ==================== STATES ====================
class OrderState(StatesGroup):
    name = State()
    phone = State()
    confirm = State()

# ==================== KEYBOARDS ====================
class Keyboards:
    @staticmethod
    def main_menu() -> ReplyKeyboardMarkup:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📄 Xizmatlar"), KeyboardButton(text="📞 Aloqa")],
                [KeyboardButton(text="ℹ️ Biz haqimizda")]
            ],
            resize_keyboard=True,
            input_field_placeholder="Menyudan tanlang..."
        )

    @staticmethod
    def services_menu() -> ReplyKeyboardMarkup:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📑 Hujjat tayyorlash"), KeyboardButton(text="🏢 Yagona darcha")],
                [KeyboardButton(text="🚗 Avtoraqam"), KeyboardButton(text="🏦 Bank xizmatlari")],
                [KeyboardButton(text="🏷 Auksion xizmatlar")],
                [KeyboardButton(text="🏠 Bosh menyu")]
            ],
            resize_keyboard=True
        )

    @staticmethod
    def yagona_menu() -> ReplyKeyboardMarkup:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📜 Ishonchnoma"), KeyboardButton(text="📑 Ruxsatnoma")],
                [KeyboardButton(text="📄 Sudlanmaganlik"), KeyboardButton(text="🏥 Narkologiya ma'lumotnoma")],
                [KeyboardButton(text="💳 Qarzdorlik ma'lumotnoma"), KeyboardButton(text="👶 Bola puli ariza")],
                [KeyboardButton(text="💼 Ish haqi ma'lumotnoma")],
                [KeyboardButton(text="⬅️ Orqaga"), KeyboardButton(text="🏠 Bosh menyu")]
            ],
            resize_keyboard=True
        )

    @staticmethod
    def bank_menu() -> ReplyKeyboardMarkup:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="💳 Karta ochish"), KeyboardButton(text="💰 Kredit olish")],
                [KeyboardButton(text="🏠 Oila krediti"), KeyboardButton(text="🎓 Ta'lim krediti")],
                [KeyboardButton(text="🔓 Taqiqni ochish")],
                [KeyboardButton(text="⬅️ Orqaga"), KeyboardButton(text="🏠 Bosh menyu")]
            ],
            resize_keyboard=True
        )

    @staticmethod
    def auksion_menu() -> ReplyKeyboardMarkup:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🏠 Yer uchastkasi"), KeyboardButton(text="🚗 Avtomobil auksion")],
                [KeyboardButton(text="🏢 Noturar joy")],
                [KeyboardButton(text="⬅️ Orqaga"), KeyboardButton(text="🏠 Bosh menyu")]
            ],
            resize_keyboard=True
        )

    @staticmethod
    def phone_request() -> ReplyKeyboardMarkup:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📱 Raqam yuborish", request_contact=True)],
                [KeyboardButton(text="⬅️ Orqaga"), KeyboardButton(text="🏠 Bosh menyu")]
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )

    @staticmethod
    def navigation_only() -> ReplyKeyboardMarkup:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="⬅️ Orqaga"), KeyboardButton(text="🏠 Bosh menyu")]
            ],
            resize_keyboard=True
        )

    @staticmethod
    def confirm_keyboard() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="confirm")],
                [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")]
            ]
        )

# ==================== SERVICES ====================
SERVICES = {
    # Yagona darcha
    "📜 Ishonchnoma": "Yagona darcha",
    "📑 Ruxsatnoma": "Yagona darcha",
    "📄 Sudlanmaganlik": "Yagona darcha",
    "🏥 Narkologiya ma'lumotnoma": "Yagona darcha",
    "💳 Qarzdorlik ma'lumotnoma": "Yagona darcha",
    "👶 Bola puli ariza": "Yagona darcha",
    "💼 Ish haqi ma'lumotnoma": "Yagona darcha",

    # Bank
    "💳 Karta ochish": "Bank",
    "💰 Kredit olish": "Bank",
    "🏠 Oila krediti": "Bank",
    "🎓 Ta'lim krediti": "Bank",
    "🔓 Taqiqni ochish": "Bank",

    # Auksion
    "🏠 Yer uchastkasi": "Auksion",
    "🚗 Avtomobil auksion": "Auksion",
    "🏢 Noturar joy": "Auksion",

    # Avto
    "🚗 Avtoraqam": "Avto",

    # Hujjat
    "📑 Hujjat tayyorlash": "Hujjat"
}

# ==================== HELPERS ====================
async def get_order_number() -> int:
    """Buyurtma raqamini xavfsiz oshirib olish."""
    async with order_lock:
        try:
            with open(ORDER_FILE, "r", encoding="utf-8") as f:
                count = int(f.read().strip())
        except (FileNotFoundError, ValueError):
            count = 0

        count += 1

        with open(ORDER_FILE, "w", encoding="utf-8") as f:
            f.write(str(count))

        return count


def escape_text(value: object) -> str:
    """HTML parse mode uchun xavfsiz text."""
    return html.escape(str(value)) if value is not None else ""


def normalize_uzbek_phone(text: str) -> Optional[str]:
    """
    Telefon raqamni normallashtiradi.
    Qabul qiladi:
    +998901234567
    998901234567
    901234567
    90 123 45 67
    """
    cleaned = re.sub(r"[^\d+]", "", text.strip())

    if cleaned.startswith("+998") and len(cleaned) == 13:
        return cleaned

    if cleaned.startswith("998") and len(cleaned) == 12:
        return "+" + cleaned

    if cleaned.isdigit() and len(cleaned) == 9:
        return "+998" + cleaned

    return None


def is_valid_name(text: str) -> bool:
    """Ism validatsiyasi."""
    text = text.strip()

    if len(text) < 2 or len(text) > 50:
        return False

    allowed_extra = {" ", "'", "’", "‘", "-"}
    return all(ch.isalpha() or ch in allowed_extra for ch in text)


async def send_main_menu(message: Message, text: str = "🏠 <b>Bosh menyu</b>") -> None:
    await message.answer(text, reply_markup=Keyboards.main_menu(), parse_mode="HTML")


async def send_services_menu(message: Message) -> None:
    await message.answer(
        "📋 <b>Xizmatlar ro'yxati</b>\n\nKerakli bo'limni tanlang 👇",
        reply_markup=Keyboards.services_menu(),
        parse_mode="HTML"
    )


async def start_order_flow(message: Message, state: FSMContext) -> None:
    """Buyurtma jarayonini boshlash."""
    data = await state.get_data()
    service = escape_text(data.get("service", "Noma'lum"))

    text = (
        f"✅ <b>Tanlangan xizmat:</b> {service}\n\n"
        "📝 Iltimos, ismingizni kiriting:"
    )
    await message.answer(text, reply_markup=Keyboards.navigation_only(), parse_mode="HTML")
    await state.set_state(OrderState.name)


async def process_phone(message: Message, state: FSMContext, phone: str) -> None:
    """Telefonni saqlash va tasdiqlash oynasini chiqarish."""
    await state.update_data(phone=phone)
    data = await state.get_data()

    summary = (
        "📋 <b>Buyurtma ma'lumotlari:</b>\n\n"
        f"🧾 <b>Xizmat:</b> {escape_text(data.get('service'))}\n"
        f"📂 <b>Kategoriya:</b> {escape_text(data.get('category'))}\n"
        f"👤 <b>Ism:</b> {escape_text(data.get('name'))}\n"
        f"📞 <b>Telefon:</b> {escape_text(phone)}\n\n"
        "✅ Ma'lumotlar to'g'rimi?"
    )

    await message.answer(summary, reply_markup=Keyboards.confirm_keyboard(), parse_mode="HTML")
    await state.set_state(OrderState.confirm)

# ==================== COMMAND HANDLERS ====================
@dp.message(CommandStart())
async def start_handler(message: Message):
    welcome_text = (
        f"👋 Assalomu alaykum, {escape_text(message.from_user.full_name)}!\n\n"
        "🤖 <b>Xizmatlar botiga</b> xush kelibsiz!\n"
        "📄 Kerakli xizmatni tanlash uchun quyidagi menyudan foydalaning."
    )
    await message.answer(welcome_text, reply_markup=Keyboards.main_menu(), parse_mode="HTML")


@dp.message(Command("help"))
async def help_handler(message: Message):
    help_text = (
        "🔹 <b>Bot buyruqlari:</b>\n"
        "/start - Botni ishga tushirish\n"
        "/help - Yordam olish\n"
        "/cancel - Joriy operatsiyani bekor qilish\n\n"
        "📞 Aloqa: @xakimbek0710"
    )
    await message.answer(help_text, parse_mode="HTML")


@dp.message(Command("cancel"))
async def cancel_handler(message: Message, state: FSMContext):
    current_state = await state.get_state()

    if current_state is None:
        await message.answer(
            "❌ Bekor qilish uchun faol operatsiya yo'q.",
            reply_markup=Keyboards.main_menu()
        )
        return

    await state.clear()
    await message.answer("✅ Operatsiya bekor qilindi.", reply_markup=Keyboards.main_menu())

# ==================== MENU HANDLERS ====================
@dp.message(F.text == "📄 Xizmatlar")
async def show_services(message: Message):
    await send_services_menu(message)


@dp.message(F.text == "🏢 Yagona darcha")
async def yagona_handler(message: Message):
    await message.answer(
        "🏢 <b>Yagona darcha xizmatlari</b>\n\nTanlang 👇",
        reply_markup=Keyboards.yagona_menu(),
        parse_mode="HTML"
    )


@dp.message(F.text == "🏦 Bank xizmatlari")
async def bank_handler(message: Message):
    await message.answer(
        "🏦 <b>Bank xizmatlari</b>\n\nTanlang 👇",
        reply_markup=Keyboards.bank_menu(),
        parse_mode="HTML"
    )


@dp.message(F.text == "🏷 Auksion xizmatlar")
async def auksion_handler(message: Message):
    await message.answer(
        "🏷 <b>Auksion xizmatlari</b>\n\nTanlang 👇",
        reply_markup=Keyboards.auksion_menu(),
        parse_mode="HTML"
    )

# ==================== SERVICE SELECT ====================
@dp.message(F.text == "📑 Hujjat tayyorlash")
async def hujjat_handler(message: Message, state: FSMContext):
    await state.update_data(service="📑 Hujjat tayyorlash", category="Hujjat")
    await start_order_flow(message, state)


@dp.message(F.text == "🚗 Avtoraqam")
async def avto_handler(message: Message, state: FSMContext):
    await state.update_data(service="🚗 Avtoraqam", category="Avto")
    await start_order_flow(message, state)


@dp.message(F.text.in_([
    "📜 Ishonchnoma", "📑 Ruxsatnoma", "📄 Sudlanmaganlik",
    "🏥 Narkologiya ma'lumotnoma", "💳 Qarzdorlik ma'lumotnoma",
    "👶 Bola puli ariza", "💼 Ish haqi ma'lumotnoma",
    "💳 Karta ochish", "💰 Kredit olish", "🏠 Oila krediti",
    "🎓 Ta'lim krediti", "🔓 Taqiqni ochish",
    "🏠 Yer uchastkasi", "🚗 Avtomobil auksion", "🏢 Noturar joy"
]))
async def service_selected(message: Message, state: FSMContext):
    service = message.text
    category = SERVICES.get(service, "Umumiy")

    await state.update_data(service=service, category=category)
    await start_order_flow(message, state)

# ==================== FSM: NAME ====================
@dp.message(OrderState.name)
async def get_name(message: Message, state: FSMContext):
    text = (message.text or "").strip()

    if text == "⬅️ Orqaga":
        await state.clear()
        await send_services_menu(message)
        return

    if text == "🏠 Bosh menyu":
        await state.clear()
        await send_main_menu(message)
        return

    if not is_valid_name(text):
        await message.answer(
            "⚠️ Ism 2 dan 50 ta belgi orasida bo'lishi kerak.\n"
            "Faqat harflar, bo'sh joy, apostrof va defis ishlatish mumkin.\n\n"
            "Qayta kiriting:"
        )
        return

    await state.update_data(name=text)
    await message.answer(
        "📱 <b>Telefon raqamingizni yuboring:</b>\n\n"
        "Quyidagi tugma orqali raqamingizni yuboring yoki qo'lda kiriting (+998...):",
        reply_markup=Keyboards.phone_request(),
        parse_mode="HTML"
    )
    await state.set_state(OrderState.phone)

# ==================== FSM: PHONE ====================
@dp.message(OrderState.phone, F.contact)
async def get_phone_contact(message: Message, state: FSMContext):
    if not message.contact:
        await message.answer("⚠️ Kontaktni qaytadan yuboring.")
        return

    if message.contact.user_id != message.from_user.id:
        await message.answer("⚠️ Iltimos, o'zingizning telefon raqamingizni yuboring.")
        return

    phone = message.contact.phone_number
    if not phone.startswith("+"):
        phone = "+" + phone

    await process_phone(message, state, phone)


@dp.message(OrderState.phone)
async def get_phone_text(message: Message, state: FSMContext):
    text = (message.text or "").strip()

    if text == "⬅️ Orqaga":
        await state.set_state(OrderState.name)
        await message.answer("📝 Ismingizni kiriting:", reply_markup=Keyboards.navigation_only())
        return

    if text == "🏠 Bosh menyu":
        await state.clear()
        await send_main_menu(message)
        return

    phone = normalize_uzbek_phone(text)
    if not phone:
        await message.answer(
            "⚠️ <b>Noto'g'ri telefon formati!</b>\n\n"
            "Iltimos, quyidagi formatlardan birida kiriting:\n"
            "• +998901234567\n"
            "• 998901234567\n"
            "• 901234567\n\n"
            "Yoki <b>📱 Raqam yuborish</b> tugmasini bosing.",
            parse_mode="HTML"
        )
        return

    await process_phone(message, state, phone)

# ==================== FSM: CONFIRM ====================
@dp.callback_query(F.data == "confirm", OrderState.confirm)
async def confirm_order(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    data = await state.get_data()
    order_num = await get_order_number()

    username = f"@{callback.from_user.username}" if callback.from_user.username else "yo'q"
    telegram_name = callback.from_user.full_name or "Noma'lum"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    admin_text = (
        f"🆕 <b>YANGI BUYURTMA #{order_num}</b>\n\n"
        f"🧾 <b>Xizmat:</b> {escape_text(data.get('service'))}\n"
        f"📂 <b>Kategoriya:</b> {escape_text(data.get('category'))}\n\n"
        f"👤 <b>Mijoz:</b> {escape_text(data.get('name'))}\n"
        f"📞 <b>Telefon:</b> {escape_text(data.get('phone'))}\n"
        f"🙍 <b>Telegram ism:</b> {escape_text(telegram_name)}\n"
        f"💬 <b>Username:</b> {escape_text(username)}\n"
        f"🆔 <b>ID:</b> <code>{callback.from_user.id}</code>\n"
        f"⏰ <b>Sana:</b> {escape_text(timestamp)}"
    )

    try:
        await bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML")

        if callback.message:
            await callback.message.edit_text(
                f"✅ <b>Buyurtma #{order_num} qabul qilindi!</b>\n\n"
                "Tez orada siz bilan bog'lanamiz.\n"
                "📞 Aloqa: @xakimbek0710",
                parse_mode="HTML"
            )
            await callback.message.answer(
                "🏠 <b>Bosh menyu</b>",
                reply_markup=Keyboards.main_menu(),
                parse_mode="HTML"
            )

        logger.info("Buyurtma #%s yuborildi. User: %s", order_num, callback.from_user.id)

    except TelegramAPIError:
        logger.exception("Admin ga xabar yuborishda xato")

        if callback.message:
            await callback.message.edit_text(
                "❌ <b>Xatolik yuz berdi!</b>\n\n"
                "Iltimos, keyinroq qayta urinib ko'ring yoki admin bilan bog'laning: @xakimbek0710",
                parse_mode="HTML"
            )

    await state.clear()


@dp.callback_query(F.data == "cancel", OrderState.confirm)
async def cancel_order(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    if callback.message:
        await callback.message.edit_text("❌ Buyurtma bekor qilindi.")
        await callback.message.answer(
            "🏠 <b>Bosh menyu</b>",
            reply_markup=Keyboards.main_menu(),
            parse_mode="HTML"
        )

    await state.clear()

# ==================== STATIC PAGES ====================
@dp.message(F.text == "📞 Aloqa")
async def contact_handler(message: Message):
    contact_text = (
        "📞 <b>Aloqa ma'lumotlari</b>\n\n"
        "👤 Admin: @xakimbek0710\n"
        "⏰ Ish vaqti: 09:00 - 18:00\n\n"
        "Savollaringiz bo'lsa, bemalol murojaat qiling!"
    )
    await message.answer(contact_text, parse_mode="HTML")


@dp.message(F.text == "ℹ️ Biz haqimizda")
async def about_handler(message: Message):
    about_text = (
        "ℹ️ <b>Biz haqimizda</b>\n\n"
        "🤖 Bu bot orqali siz turli xizmatlarga buyurtma berishingiz mumkin:\n"
        "• 📑 Hujjat tayyorlash\n"
        "• 🏢 Yagona darcha xizmatlari\n"
        "• 🏦 Bank xizmatlari\n"
        "• 🏷 Auksion xizmatlari\n"
        "• 🚗 Avtoraqam olish\n\n"
        "✅ Tez va sifatli xizmat!"
    )
    await message.answer(about_text, parse_mode="HTML")

# ==================== NAVIGATION ====================
@dp.message(F.text == "⬅️ Orqaga")
async def back_handler(message: Message, state: FSMContext):
    current_state = await state.get_state()

    if current_state == OrderState.name.state:
        await state.clear()
        await send_services_menu(message)
        return

    if current_state == OrderState.phone.state:
        await state.set_state(OrderState.name)
        await message.answer("📝 Ismingizni kiriting:", reply_markup=Keyboards.navigation_only())
        return

    await state.clear()
    await send_services_menu(message)


@dp.message(F.text == "🏠 Bosh menyu")
async def main_menu_handler(message: Message, state: FSMContext):
    await state.clear()
    await send_main_menu(message)

# ==================== FALLBACK ====================
@dp.message()
async def unknown_handler(message: Message, state: FSMContext):
    current_state = await state.get_state()

    if current_state:
        await message.answer("⚠️ Iltimos, talab qilingan ma'lumotni kiriting yoki menyudan tanlang.")
    else:
        await message.answer(
            "❓ Noma'lum buyruq. Iltimos, menyudan tanlang yoki /help yozing.",
            reply_markup=Keyboards.main_menu()
        )

# ==================== ERROR HANDLER ====================
@dp.errors()
async def error_handler(event):
    logger.exception("Kutilmagan xatolik yuz berdi: %s", event.exception)
    return True

# ==================== MAIN ====================
async def healthcheck(request):
    return web.Response(text="ONLINE XIZMAT BOT ishlayapti!")

async def main():
    logger.info("Bot ishga tushdi...")

    app = web.Application()
    app.router.add_get("/", healthcheck)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)

    await site.start()

    logger.info(f"Web server ishga tushdi. Port: {port}")

    await dp.start_polling(bot)
