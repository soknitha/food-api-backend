import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, ReplyKeyboardMarkup, KeyboardButton
import requests
import os
import io
import qrcode
from google import genai

# ដាក់ Token របស់ Bot អ្នកដែលបានពី BotFather នៅទីនេះ
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# ដាក់ Link ដែលអ្នកទទួលបានពី Railway (កុំភ្លេចថែម /api នៅខាងចុង)
API_BASE_URL = "https://web-production-88028.up.railway.app/api"

bot = telebot.TeleBot(BOT_TOKEN)

# ---------------- ការកំណត់ AI Gemini ---------------- #
# សូមទៅយក API Key ពី Google AI Studio មកជំនួសត្រង់នេះ
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "ដាក់_API_KEY_GEMINI_នៅទីនេះ")
client = genai.Client(api_key=GEMINI_API_KEY)

# Link ទៅកាន់ Mini App ដែលដំណើរការចេញពី Railway ផ្ទាល់
MINI_APP_URL = "https://web-production-88028.up.railway.app/miniapp"

# ---------------- ការកំណត់ភាសា (Language Settings) ---------------- #
user_langs = {}

LANG_DICT = {
    "km": {
        "welcome": "🌟 *សូមស្វាគមន៍មកកាន់ 小月小吃!*\n\nយើងខ្ញុំផ្តល់ជូននូវបទពិសោធន៍ម្ហូបអាហារដ៏ឈ្ងុយឆ្ងាញ់ ប្រកបដោយអនាម័យ និងស្តង់ដារគុណភាពខ្ពស់បំផុត។ សូមរីករាយជាមួយសេវាកម្មកុម្ម៉ង់អាហារឌីជីថលរបស់យើងខ្ញុំ។",
        "choose": "👇 សូមជ្រើសរើសសេវាកម្មខាងក្រោម៖",
        "order_app": "📱 កុម្ម៉ង់អាហារ (Order Food)",
        "support": "🎧 ផ្នែកបម្រើអតិថិជន (Support)",
        "no_text": "⚠️ សូមអភ័យទោស ប្រព័ន្ធរបស់យើងប្រើប្រាស់តែប៊ូតុងបញ្ជាប៉ុណ្ណោះ។ សូមចុច /start ដើម្បីបើកម៉ឺនុយឡើងវិញ។",
        "receipt_ok": "✅ Successfully Received!\nYour payment screenshot has been sent to the merchant. Please wait a moment, your food will be prepared shortly. 🛵",
        "receipt_fail": "⚠️ អ្នកមិនមានការបញ្ជាទិញដែលកំពុងរង់ចាំការបង់ប្រាក់ទេ ឬអ្នកបានផ្ញើវិក្កយបត្ររួចហើយ។"
    },
    "zh": {
        "welcome": "🌟 *欢迎来到 小月小吃！*\n\n我们为您提供最卫生、高标准的美味佳肴。请享受我们便捷的数字化点餐服务。",
        "choose": "👇 请选择以下服务：",
        "order_app": "📱 小月小吃的菜单",
        "support": "🎧 客服支持 (Support)",
        "no_text": "⚠️ 抱歉，本系统仅支持按钮操作。请点击 /start 重新打开菜单。",
        "receipt_ok": "✅ Successfully Received!\nYour payment screenshot has been sent to the merchant. Please wait a moment, your food will be prepared shortly. 🛵",
        "receipt_fail": "⚠️ 您当前没有待付款的订单，或您已经发送过凭证了。"
    },
    "en": {
        "welcome": "🌟 *Welcome to Xiao Yue Xiao Chi!*\n\nWe provide a delicious culinary experience with the highest standards of hygiene and quality. Enjoy our seamless digital ordering service.",
        "choose": "👇 Please select a service below:",
        "order_app": "📱 Order Food",
        "support": "🎧 Customer Support",
        "no_text": "⚠️ Sorry, our system only accepts button interactions. Please click /start to reopen the menu.",
        "receipt_ok": "✅ Successfully Received!\nYour payment screenshot has been sent to the merchant. Please wait a moment, your food will be prepared shortly. 🛵",
        "receipt_fail": "⚠️ You have no pending orders awaiting payment, or you've already sent a receipt."
    }
}

# អនុគមន៍ជំនួយក្នុងការទាញយកភាសាពី Database ជានិរន្តរ៍
def get_user_lang(chat_id):
    if chat_id in user_langs:
        return user_langs[chat_id]
    try:
        res = requests.get(f"{API_BASE_URL}/users/{chat_id}")
        if res.status_code == 200 and res.json():
            lang = res.json().get("language", "km")
            user_langs[chat_id] = lang
            return lang
    except: pass
    return "km"

@bot.message_handler(commands=['start'])
@bot.message_handler(func=lambda message: message.text == '🔄 /start')
def send_welcome(message):
    # រក្សាទុកព័ត៌មាន User ដោយស្វ័យប្រវត្តិ
    user_id = str(message.from_user.id)
    user_name = message.from_user.first_name or "N/A"
    
    try:
        response = requests.post(f"{API_BASE_URL}/users", json={"id": user_id, "name": user_name, "phone": "N/A", "location": ""})
        if response.status_code == 200:
            user_data = response.json()
            if user_data and "language" in user_data:
                user_langs[message.chat.id] = user_data["language"]
    except Exception as e:
        print("Error saving initial user:", e)

    # បង្កើត Reply Keyboard (ជំនួសកន្លែងវាយអក្សរ)
    reply_markup = ReplyKeyboardMarkup(resize_keyboard=True, input_field_placeholder="👇 សូមប្រើប្រាស់ប៊ូតុងខាងក្រោម...")
    reply_markup.add(
        KeyboardButton("🔄 /start")
    )
    reply_markup.add(
        KeyboardButton("📱 ផ្ញើលេខទូរស័ព្ទ", request_contact=True),
        KeyboardButton("📍 ផ្ញើទីតាំង", request_location=True)
    )
    bot.send_message(message.chat.id, "កំពុងរៀបចំប្រព័ន្ធ... / System initializing...", reply_markup=reply_markup)

    # ជម្រើសភាសា (Language Selection)
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🇰🇭 ភាសាខ្មែរ", callback_data="lang_km"),
        InlineKeyboardButton("🇨🇳 中文", callback_data="lang_zh"),
        InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")
    )

    bot.send_message(message.chat.id, "🌐 សូមជ្រើសរើសភាសា\n🌐 请选择语言\n🌐 Please select your language:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ["lang_km", "lang_zh", "lang_en"])
def set_language(call):
    bot.answer_callback_query(call.id) # ប្រាប់ Telegram ថាទទួលបានការចុច
    lang = call.data.split("_")[1]
    chat_id = call.message.chat.id
    user_langs[chat_id] = lang
    
    # រក្សាទុកភាសាចូល Database តាមរយៈ API ដើម្បីឱ្យមាននិរន្តរភាព
    try:
        requests.post(f"{API_BASE_URL}/users", json={"id": str(chat_id), "name": call.from_user.first_name or "N/A", "language": lang})
    except Exception as e:
        print("Error saving language to API:", e)

    try:
        bot.delete_message(chat_id, call.message.message_id)     # លុបប៊ូតុង
    except:
        pass
        
    show_main_menu(chat_id, lang)

def show_main_menu(chat_id, lang="km"):
    texts = LANG_DICT.get(lang, LANG_DICT["km"])
    
    markup = InlineKeyboardMarkup(row_width=1)
    # បញ្ជូនជម្រើសភាសា (lang) ទៅកាន់ Mini App
    btn_mini_app = InlineKeyboardButton(texts["order_app"], web_app=WebAppInfo(url=f"{MINI_APP_URL}?v=new&lang={lang}"))
    btn_support = InlineKeyboardButton(texts["support"], url="https://t.me/XiaoYueXiaoChi")
    markup.add(btn_mini_app, btn_support)
    
    full_text = f"{texts['welcome']}\n\n{texts['choose']}"
    bot.send_message(chat_id, full_text, reply_markup=markup, parse_mode="Markdown")

# ---------------- ទទួលជម្រើសដឹកជញ្ជូន ---------------- #
@bot.callback_query_handler(func=lambda call: call.data.startswith('pickup_') or call.data.startswith('delivery_'))
def handle_delivery_choice(call):
    action, order_id = call.data.split('_', 1)
    chat_id = str(call.message.chat.id)
    
    if action == "pickup":
        requests.post(f"{API_BASE_URL}/orders/finalize", json={"order_id": order_id, "chat_id": chat_id, "delivery_fee": 0, "distance": 0})
        try: bot.delete_message(chat_id, call.message.message_id)
        except: pass
    elif action == "delivery":
        requests.put(f"{API_BASE_URL}/orders/status", json={"order_id": order_id, "status": "រង់ចាំទីតាំង"})
        reply_markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        reply_markup.add(KeyboardButton("📍 ផ្ញើទីតាំងរបស់ខ្ញុំ (Send Location)", request_location=True))
        bot.send_message(chat_id, "📍 *សូមផ្ញើទីតាំងរបស់អ្នក*\n\nសូមចុចប៊ូតុងខាងក្រោម ដើម្បីឱ្យប្រព័ន្ធវ័យឆ្លាតគណនាថ្លៃសេវាដឹកជញ្ជូនដោយស្វ័យប្រវត្តិ៖", reply_markup=reply_markup, parse_mode="Markdown")
        try: bot.delete_message(chat_id, call.message.message_id)
        except: pass

# ---------------- ទទួលព័ត៌មានពីការចុចប៊ូតុងផ្ញើទូរស័ព្ទ និង ទីតាំង ---------------- #
@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    chat_id = str(message.chat.id)
    phone = message.contact.phone_number
    try:
        requests.post(f"{API_BASE_URL}/users", json={"id": chat_id, "name": message.from_user.first_name, "phone": phone})
        lang = get_user_lang(chat_id)
        bot.send_message(chat_id, "✅ លេខទូរស័ព្ទរបស់អ្នកត្រូវបានរក្សាទុក!" if lang == "km" else "✅ Phone number saved!")
    except Exception as e:
        print("Contact Error:", e)

@bot.message_handler(content_types=['location'])
def handle_location(message):
    chat_id = str(message.chat.id)
    lat = message.location.latitude
    lon = message.location.longitude
    loc_str = f"{lat},{lon}"
    try:
        requests.post(f"{API_BASE_URL}/users", json={"id": chat_id, "name": message.from_user.first_name, "location": loc_str})
    except Exception as e:
        print("Location Error:", e)
        
    # ដំណើរការទីតាំងសម្រាប់ការកុម្ម៉ង់
    res = requests.post(f"{API_BASE_URL}/orders/process_location", json={"chat_id": chat_id, "lat": lat, "lon": lon})
    if res.status_code == 200 and "ok" in res.json().get("status", ""):
        bot.send_message("@XiaoYueXiaoChi", f"📍 *ទីតាំងដឹកជញ្ជូនរបស់អតិថិជន {message.from_user.first_name}* (ID: `{chat_id}`)", parse_mode="Markdown")
        bot.send_location("@XiaoYueXiaoChi", lat, lon)
        
        reply_markup = ReplyKeyboardMarkup(resize_keyboard=True, input_field_placeholder="👇 សូមប្រើប្រាស់ប៊ូតុងខាងក្រោម...")
        reply_markup.add(KeyboardButton("🔄 /start"))
        reply_markup.add(KeyboardButton("📱 ផ្ញើលេខទូរស័ព្ទ", request_contact=True), KeyboardButton("📍 ផ្ញើទីតាំង", request_location=True))
        bot.send_message(chat_id, "✅ ទទួលបានទីតាំងរួចរាល់! ប្រព័ន្ធកំពុងរៀបចំវិក្កយបត្រជូនអ្នក...", reply_markup=reply_markup)
    else:
        lang = get_user_lang(chat_id)
        bot.send_message(chat_id, "✅ ទីតាំងរបស់អ្នកត្រូវបានរក្សាទុក!" if lang == "km" else "✅ Location saved!")

# ---------------- ទទួលរូបភាព Screenshot ពីអតិថិជន ---------------- #
@bot.message_handler(content_types=['photo'])
def handle_payment_screenshot(message):
    try:
        chat_id = message.chat.id
        lang = get_user_lang(chat_id)
        texts = LANG_DICT.get(lang, LANG_DICT["km"])
        
        photo_id = message.photo[-1].file_id # យករូបភាពដែលមានគុណភាពច្បាស់ជាងគេ
        file_info = bot.get_file(photo_id)
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
        
        # បញ្ជូន URL រូបភាពទៅកាន់ Backend API
        response = requests.post(f"{API_BASE_URL}/orders/receipt", json={"chat_id": str(chat_id), "image_url": file_url})
        
        if response.status_code == 200:
            res_data = response.json()
            if "error" in res_data:
                if "verified" in res_data and not res_data["verified"]:
                    bot.reply_to(message, "⚠️ *ការទូទាត់របស់អ្នកមានបញ្ហា ឬទឹកប្រាក់មិនត្រូវគ្នា!* ❌\n\nសូមទាក់ទងមកកាន់ Admin ផ្ទាល់តាមរយៈប៊ូតុង 🎧 Support (@XiaoYueXiaoChi) ដើម្បីដោះស្រាយភ្លាមៗ។", parse_mode="Markdown")
                else:
                    bot.reply_to(message, texts["receipt_fail"])
            else:
                bot.reply_to(message, texts["receipt_ok"], parse_mode="Markdown")
        else:
            bot.reply_to(message, "❌ សូមអភ័យទោស ប្រព័ន្ធមិនអាចភ្ជាប់ទៅកាន់ Admin បានទេពេលនេះ។")
    except Exception as e:
        bot.reply_to(message, "❌ មានកំហុសក្នុងការទទួលរូបភាព។")

# បិទមុខងារវាយអក្សរបញ្ចូលក្នុង Bot (Block Text Messaging)
@bot.message_handler(func=lambda message: True, content_types=['text'])
def block_text(message):
    chat_id = message.chat.id
    lang = get_user_lang(chat_id)
    texts = LANG_DICT.get(lang, LANG_DICT["km"])
    
    try:
        bot.delete_message(chat_id, message.message_id) # លុបសារដែលភ្ញៀវវាយចូល
    except:
        pass
        
    # លោតប្រាប់ថាប្រព័ន្ធប្រើបានតែប៊ូតុង
    bot.send_message(chat_id, texts["no_text"])

if __name__ == '__main__':
    print("🤖 Telegram Bot កំពុងដំណើរការ... (ចុច Ctrl+C ដើម្បីបិទ)")
    # bot.infinity_polling(timeout=10, long_polling_timeout=5)
    print("សូមដំណើរការ bot នេះតាមរយៈ FastAPI Webhook នៅក្នុង main.py វិញ។")