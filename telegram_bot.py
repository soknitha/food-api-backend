import warnings
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, ReplyKeyboardMarkup, KeyboardButton
import requests
import os
import sys
from google import genai

# Import the centralized configuration
import config

# Suppress all warnings
warnings.filterwarnings("ignore")

# ----------------
# Initialize Bot and AI Client from Central Config
# ----------------
try:
    bot = telebot.TeleBot(config.BOT_TOKEN, threaded=True) # Changed to True to prevent blocking in Polling mode
    # The Gemini client is now initialized in main.py, but we can also initialize it here if needed for direct use.
    # For now, the AI verification part in main.py handles it.
except Exception as e:
    print(f"❌ FATAL: Could not initialize bot client: {e}", file=sys.stderr)
    sys.exit("Exiting due to initialization failure.")


# ---------------- Language Settings ---------------- #
user_langs = {}
LANG_DICT = {
    "km": {
        "welcome": "🌟 *សូមស្វាគមន៍មកកាន់ 小月小吃!*\n\nយើងខ្ញុំផ្តល់ជូននូវបទពិសោធន៍ម្ហូបអាហារដ៏ឈ្ងុយឆ្ងាញ់ ប្រកបដោយអនាម័យ និងស្តង់ដារគុណភាពខ្ពស់បំផុត។ សូមរីករាយជាមួយសេវាកម្មកុម្ម៉ង់អាហារឌីជីថលរបស់យើងខ្ញុំ។",
        "choose": "👇 សូមជ្រើសរើសសេវាកម្មខាងក្រោម៖",
        "order_app": "📱 កុម្ម៉ង់អាហារ (Order Food)",
        "support": "🎧 ផ្នែកបម្រើអតិថិជន (Support)",
        "no_text": "⚠️ សូមអភ័យទោស ប្រព័ន្ធរបស់យើងប្រើប្រាស់តែប៊ូតុងបញ្ជាប៉ុណ្ណោះ។ សូមចុច /start ដើម្បីបើកម៉ឺនុយឡើងវិញ។",
        "receipt_ok": "✅ ទទួលបានជោគជ័យ!\nវិក្កយបត្ររបស់អ្នកត្រូវបានបញ្ជូនទៅកាន់អ្នកលក់។ សូមរង់ចាំបន្តិច អាហាររបស់អ្នកនឹងរៀបចំជូនភ្លាមៗ។ 🛵",
        "receipt_fail": "⚠️ អ្នកមិនមានការបញ្ជាទិញដែលកំពុងរង់ចាំការបង់ប្រាក់ទេ ឬអ្នកបានផ្ញើវិក្កយបត្ររួចហើយ។",
        "ask_location": "📍 *សូមផ្ញើទីតាំងរបស់អ្នក* ដើម្បីឱ្យប្រព័ន្ធគណនាថ្លៃដឹកជញ្ជូន។",
        "loc_received": "✅ ទទួលបានទីតាំង! ប្រព័ន្ធកំពុងរៀបចំវិក្កយបត្រ...",
        "phone_saved": "✅ លេខទូរស័ព្ទត្រូវបានរក្សាទុក!",
        "loc_saved": "✅ ទីតាំងត្រូវបានរក្សាទុក!",
        "processing": "⏳ កំពុងដំណើរការ...",
        "error": "❌ មានបញ្ហាក្នុងការដំណើរការរូបភាព។",
        "send_loc_btn": "📍 ផ្ញើទីតាំងរបស់ខ្ញុំ"
    },
    "zh": {
        "welcome": "🌟 *欢迎来到 小月小吃！*\n\n我们为您提供最卫生、高标准的美味佳肴。请享受我们便捷的数字化点餐服务。",
        "choose": "👇 请选择以下服务：",
        "order_app": "📱 小月小吃的菜单",
        "support": "🎧 客服支持 (Support)",
        "no_text": "⚠️ 抱歉，本系统仅支持按钮操作。请点击 /start 重新打开菜单。",
        "receipt_ok": "✅ 接收成功！\n您的付款截图已发送给商家。请稍候，您的食物马上就好。 🛵",
        "receipt_fail": "⚠️ 您当前没有待付款的订单，或您已经发送过凭证了。",
        "ask_location": "📍 *请发送您的位置* 以便系统计算运费。",
        "loc_received": "✅ 位置已收到！系统正在准备您的账单...",
        "phone_saved": "✅ 电话号码已保存！",
        "loc_saved": "✅ 位置已保存！",
        "processing": "⏳ 处理中...",
        "error": "❌ 处理图像时出错。",
        "send_loc_btn": "📍 发送我的位置"
    },
    "en": {
        "welcome": "🌟 *Welcome to Xiao Yue Xiao Chi!*\n\nWe provide a delicious culinary experience with the highest standards of hygiene and quality. Enjoy our seamless digital ordering service.",
        "choose": "👇 Please select a service below:",
        "order_app": "📱 Order Food",
        "support": "🎧 Customer Support",
        "no_text": "⚠️ Sorry, our system only accepts button interactions. Please click /start to reopen the menu.",
        "receipt_ok": "✅ Successfully Received!\nYour payment screenshot has been sent to the merchant. Please wait a moment, your food will be prepared shortly. 🛵",
        "receipt_fail": "⚠️ You have no pending orders awaiting payment, or you've already sent a receipt.",
        "ask_location": "📍 *Please send your location* for our system to calculate the delivery fee.",
        "loc_received": "✅ Location received! The system is preparing your bill...",
        "phone_saved": "✅ Phone number saved!",
        "loc_saved": "✅ Location saved!",
        "processing": "⏳ Processing...",
        "error": "❌ An error occurred while processing the image.",
        "send_loc_btn": "📍 Send My Location"
    }
}

def get_user_lang(chat_id):
    """ Fetches user language from the backend, with a local cache. """
    if chat_id in user_langs:
        return user_langs[chat_id]
    try:
        res = requests.get(f"{config.API_BASE_URL}/users/{chat_id}", timeout=5)
        if res.status_code == 200 and res.json():
            lang = res.json().get("language", "km")
            user_langs[chat_id] = lang
            return lang
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Could not fetch user lang for {chat_id}: {e}", file=sys.stderr)
    return "km" # Default to Khmer

@bot.message_handler(commands=['start'])
@bot.message_handler(func=lambda message: message.text == '🔄 /start')
def send_welcome(message):
    print(f"📥 Received /start command from user: {message.chat.id}")
    try:
        # Register or update user info via API
        requests.post(f"{config.API_BASE_URL}/users", json={
            "id": str(message.from_user.id), "name": message.from_user.first_name or "N/A", "language": "km"
        }, timeout=15)
    except Exception as e:
        print(f"⚠️ Error saving initial user {message.chat.id}: {e}", file=sys.stderr)

    # Main reply keyboard
    reply_markup = ReplyKeyboardMarkup(resize_keyboard=True, input_field_placeholder="👇 Please use the buttons below...")
    reply_markup.add(
        KeyboardButton("🔄 /start"),
        KeyboardButton("📱 Send Phone", request_contact=True),
        KeyboardButton("📍 Send Location", request_location=True)
    )
    bot.send_message(message.chat.id, "Initializing...", reply_markup=reply_markup)

    # Language selection
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🇰🇭 ភាសាខ្មែរ", callback_data="lang_km"),
        InlineKeyboardButton("🇨🇳 中文", callback_data="lang_zh"),
        InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")
    )
    bot.send_message(message.chat.id, "🌐 Please select your language:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("lang_"))
def set_language(call):
    bot.answer_callback_query(call.id)
    lang = call.data.split("_")[1]
    chat_id = call.message.chat.id
    user_langs[chat_id] = lang
    
    try: # Save language preference persistently
        requests.post(f"{config.API_BASE_URL}/users", json={"id": str(chat_id), "name": call.from_user.first_name or "N/A", "language": lang}, timeout=15)
    except Exception as e:
        print(f"⚠️ Error saving language for {chat_id}: {e}", file=sys.stderr)

    try:
        bot.delete_message(chat_id, call.message.message_id)
    except Exception: pass
    show_main_menu(chat_id, lang)

def show_main_menu(chat_id, lang="km"):
    texts = LANG_DICT.get(lang, LANG_DICT["km"])
    
    # ១. ប្រើ Link សុទ្ធ (គ្មានកន្ទុយ ?lang=) ដើម្បីការពារ Telegram ប្លុកមិនឱ្យបើក (Telegram Security Bug)
    # ប្រព័ន្ធនឹងទាញយកភាសាដោយស្វ័យប្រវត្តិពី Database ជំនួសវិញ
    pure_url = config.MINI_APP_URL
    
    # ២. បង្កើតប៊ូតុងម៉ឺនុយធំនៅខាងក្រោមបាតអេក្រង់ (Reply Keyboard)
    # ជាទម្រង់ Native ធានាថាដំណើរការ ១០០% ការពារការគាំង និងបញ្ជូនភាសាបានត្រឹមត្រូវ
    reply_markup = ReplyKeyboardMarkup(resize_keyboard=True, input_field_placeholder="👇 សូមចុចប៊ូតុងនៅទីនេះ...")
    btn_reply_app = KeyboardButton(texts["order_app"], web_app=WebAppInfo(url=pure_url))
    
    phone_text = "📱 បញ្ជូនលេខទូរស័ព្ទ" if lang == "km" else "📱 发送电话" if lang == "zh" else "📱 Send Phone"
    reply_markup.row(btn_reply_app)
    reply_markup.row(
        KeyboardButton(phone_text, request_contact=True),
        KeyboardButton(texts.get("send_loc_btn", "📍 Location"), request_location=True)
    )
    
    # ៣. បង្កើតប៊ូតុងតូចភ្ជាប់នឹងសារ (Inline Keyboard ទុកជាជម្រើសទី២)
    inline_markup = InlineKeyboardMarkup(row_width=1)
    btn_inline_app = InlineKeyboardButton(texts["order_app"], web_app=WebAppInfo(url=pure_url))
    btn_support = InlineKeyboardButton(texts["support"], url="https://t.me/XiaoYueXiaoChi")
    inline_markup.add(btn_inline_app, btn_support)
    
    full_text = f"{texts['welcome']}\n\n{texts['choose']}"
    
    # ធ្វើបច្ចុប្បន្នភាពប៊ូតុងធំនៅបាតអេក្រង់មុន រួចទើបផ្ញើសារម៉ឺនុយ
    bot.send_message(chat_id, "✅ ប្រព័ន្ធត្រូវបានរៀបចំរួចរាល់ / System Ready", reply_markup=reply_markup)
    bot.send_message(chat_id, full_text, reply_markup=inline_markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('pickup_') or call.data.startswith('delivery_'))
def handle_delivery_choice(call):
    chat_id = str(call.message.chat.id)
    lang = get_user_lang(chat_id)
    texts = LANG_DICT.get(lang, LANG_DICT["km"])
    bot.answer_callback_query(call.id, text=texts["processing"])
    action, order_id = call.data.split('_', 1)
    
    try:
        if action == "pickup":
            requests.post(f"{config.API_BASE_URL}/orders/finalize", json={"order_id": order_id, "chat_id": chat_id, "delivery_fee": 0, "distance": 0}, timeout=20)
        elif action == "delivery":
            requests.put(f"{config.API_BASE_URL}/orders/status", json={"order_id": order_id, "status": "រង់ចាំទីតាំង"}, timeout=20)
            reply_markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            reply_markup.add(KeyboardButton(texts["send_loc_btn"], request_location=True))
            bot.send_message(chat_id, texts["ask_location"], reply_markup=reply_markup, parse_mode="Markdown")
        
        bot.delete_message(chat_id, call.message.message_id)
    except Exception as e:
        print(f"⚠️ Delivery choice error for order {order_id}: {e}", file=sys.stderr)

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    lang = get_user_lang(str(message.chat.id))
    texts = LANG_DICT.get(lang, LANG_DICT["km"])
    try:
        requests.post(f"{config.API_BASE_URL}/users", json={"id": str(message.chat.id), "name": message.from_user.first_name, "phone": message.contact.phone_number}, timeout=15)
        bot.send_message(message.chat.id, texts["phone_saved"])
    except Exception as e:
        print(f"⚠️ Contact save error for {message.chat.id}: {e}", file=sys.stderr)

@bot.message_handler(content_types=['location'])
def handle_location(message):
    chat_id = str(message.chat.id)
    lang = get_user_lang(chat_id)
    texts = LANG_DICT.get(lang, LANG_DICT["km"])
    lat, lon = message.location.latitude, message.location.longitude
    try:
        requests.post(f"{config.API_BASE_URL}/users", json={"id": chat_id, "name": message.from_user.first_name, "location": f"{lat},{lon}"}, timeout=15)
    except Exception as e:
        print(f"⚠️ Location save error for {chat_id}: {e}", file=sys.stderr)
        
    try:
        res = requests.post(f"{config.API_BASE_URL}/orders/process_location", json={"chat_id": chat_id, "lat": lat, "lon": lon}, timeout=20)
        if res.status_code == 200 and "ok" in res.json().get("status", ""):
            bot.send_message(chat_id, texts["loc_received"])
        else:
            bot.send_message(chat_id, texts["loc_saved"])
    except Exception as e:
        print(f"⚠️ Process location API error for {chat_id}: {e}", file=sys.stderr)

@bot.message_handler(content_types=['photo'])
def handle_payment_screenshot(message):
    lang = get_user_lang(message.chat.id)
    texts = LANG_DICT.get(lang, LANG_DICT["km"])
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        file_url = f"https://api.telegram.org/file/bot{config.BOT_TOKEN}/{file_info.file_path}"
        
        response = requests.post(f"{config.API_BASE_URL}/orders/receipt", json={"chat_id": str(message.chat.id), "image_url": file_url}, timeout=40)
        
        if response.status_code == 200 and not response.json().get("error"):
            bot.reply_to(message, texts["receipt_ok"], parse_mode="Markdown")
        else:
            reason = response.json().get("reason", texts["receipt_fail"])
            bot.reply_to(message, reason, parse_mode="Markdown")

    except Exception as e:
        bot.reply_to(message, texts["error"])
        print(f"Photo handling error for {message.chat.id}: {e}", file=sys.stderr)

@bot.message_handler(func=lambda message: True, content_types=['text'])
def block_text(message):
    lang = get_user_lang(message.chat.id)
    texts = LANG_DICT.get(lang, LANG_DICT["km"])
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception:
        pass
    bot.send_message(message.chat.id, texts["no_text"])

if __name__ == '__main__':
    print("🤖 This script is not meant to be run directly.", file=sys.stderr)
    print("Please run the main FastAPI application using: uvicorn main:app", file=sys.stderr)
    sys.exit(1)