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
        "receipt_ok": "✅ *ការទូទាត់របស់អ្នកទទួលបានជោគជ័យ!*\n\n💰 ចំនួនទឹកប្រាក់បានទូទាត់: *${paid_amount:.2f}*\n\nសូមរង់ចាំអាហាររបស់អ្នកបន្តិច... 🛵 ប្រសិនបើមានចម្ងល់អាចទាក់ទងមកកាន់ Admin តាមរយៈប៊ូតុងខាងក្រោម។",
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
        "receipt_ok": "✅ *您的付款已成功！*\n\n💰 已付金额: *${paid_amount:.2f}*\n\n请稍候，您的食物马上就好... 🛵 如果您有任何疑问，请通过下面的按钮联系管理员。",
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
        "receipt_ok": "✅ *Your payment was successful!*\n\n💰 Amount paid: *${paid_amount:.2f}*\n\nPlease wait a moment for your food... 🛵 If you have any questions, you can contact Admin via the button below.",
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

def get_main_reply_markup(lang):
    """ មុខងារសម្រាប់ហៅប៊ូតុងទាំង ៣ មកវិញជានិច្ច (ការពារកុំឱ្យជាប់គាំង) """
    texts = LANG_DICT.get(lang, LANG_DICT["km"])
    app_url = f"{config.MINI_APP_URL}?lang={lang}"
    reply_markup = ReplyKeyboardMarkup(resize_keyboard=True, input_field_placeholder="👇 សូមចុចប៊ូតុងនៅទីនេះ...")
    btn_reply_app = KeyboardButton(texts["order_app"], web_app=WebAppInfo(url=app_url))
    phone_text = "📱 បញ្ជូនលេខទូរស័ព្ទ" if lang == "km" else "📱 发送电话" if lang == "zh" else "📱 Send Phone"
    reply_markup.row(btn_reply_app)
    reply_markup.row(
        KeyboardButton(phone_text, request_contact=True),
        KeyboardButton(texts.get("send_loc_btn", "📍 Location"), request_location=True)
    )
    return reply_markup

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
    
    # ១. បញ្ចូលកន្ទុយ ?lang= ទៅក្នុង URL វិញ ដើម្បីឱ្យ Mini App ចាប់ភាសាបានភ្លាមៗ (Smart Language V2)
    app_url = f"{config.MINI_APP_URL}?lang={lang}"
    
    # ២. ហៅមុខងារបង្កើតប៊ូតុងម៉ឺនុយធំនៅខាងក្រោមបាតអេក្រង់
    reply_markup = get_main_reply_markup(lang)
    
    # ៣. បង្កើតប៊ូតុងតូចភ្ជាប់នឹងសារ (Inline Keyboard ទុកជាជម្រើសទី២)
    inline_markup = InlineKeyboardMarkup(row_width=1)
    btn_inline_app = InlineKeyboardButton(texts["order_app"], web_app=WebAppInfo(url=app_url))
    btn_support = InlineKeyboardButton(texts["support"], url="https://t.me/XiaoYueXiaoChi")
    # បន្ថែមប៊ូតុងទី៣ (Link សុទ្ធ) ជាជំនួយបម្រុង ប្រសិនបើទូរស័ព្ទភ្ញៀវមិនគាំទ្រ WebAppInfo
    btn_fallback = InlineKeyboardButton("🔗 បើកតាម Browser (បើចុចខាងលើមិនដើរ)", url=app_url)
    inline_markup.add(btn_inline_app, btn_fallback, btn_support)
    
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

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_reply_'))
def handle_admin_reply_action(call):
    parts = call.data.split('_')
    if len(parts) >= 3:
        target_chat_id = parts[2]
        markup = telebot.types.ForceReply(selective=False)
        bot.send_message(call.message.chat.id, f"👉 សូម Reply ត្រឡប់មកកាន់សារនេះ ដើម្បីផ្ញើទៅភ្ញៀវ `{target_chat_id}`\n*(វាយសាររបស់អ្នករួចចុចបញ្ជូន)*", reply_markup=markup)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_status_'))
def handle_admin_status_update(call):
    parts = call.data.split('_', 3)
    if len(parts) == 4:
        _, _, action, order_id = parts
        status_map = {
            "cooking": "កំពុងចម្អិន",
            "delivering": "កំពុងដឹកជញ្ជូន",
            "done": "✅ រួចរាល់ (បានប្រគល់)"
        }
        new_status = status_map.get(action)
        if new_status:
            try:
                res = requests.put(f"{config.API_BASE_URL}/orders/status", json={"order_id": order_id, "status": new_status}, timeout=10)
                if res.status_code == 200:
                    bot.answer_callback_query(call.id, f"✅ បានប្តូរស្ថានភាពទៅជា: {new_status}")
                    new_caption = f"{call.message.caption or call.message.text}\n\n👉 *ស្ថានភាពបច្ចុប្បន្ន៖* {new_status}"
                    if call.message.content_type == 'photo':
                        bot.edit_message_caption(new_caption, chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=call.message.reply_markup)
                    else:
                        bot.edit_message_text(new_caption, chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=call.message.reply_markup)
                else:
                    bot.answer_callback_query(call.id, "❌ មានបញ្ហាក្នុងការប្តូរស្ថានភាព")
            except Exception as e:
                print(f"Admin status update error: {e}", file=sys.stderr)
                bot.answer_callback_query(call.id, "❌ មិនអាចភ្ជាប់ទៅកាន់ប្រព័ន្ធបានទេ")

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    lang = get_user_lang(str(message.chat.id))
    texts = LANG_DICT.get(lang, LANG_DICT["km"])
    try:
        requests.post(f"{config.API_BASE_URL}/users", json={"id": str(message.chat.id), "name": message.from_user.first_name, "phone": message.contact.phone_number}, timeout=15)
        bot.send_message(message.chat.id, texts["phone_saved"])
        
        # បញ្ជូនចូល Admin Group ភ្លាមៗ
        admin_msg = f"📱 *អតិថិជនបញ្ជូនលេខទូរស័ព្ទ*\n👤 ឈ្មោះ: {message.from_user.first_name}\n📞 លេខ: `{message.contact.phone_number}`\n🆔 ID: `{message.chat.id}`"
        bot.send_message("-1003740329904", admin_msg, parse_mode="Markdown")
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
        
        # បញ្ជូនទីតាំងចូល Admin Group ភ្លាមៗ
        admin_msg = f"📍 *អតិថិជនបញ្ជូនទីតាំង*\n👤 ឈ្មោះ: {message.from_user.first_name}\n🗺 ចុចមើលផែនទី (Google Maps)\n🆔 ID: `{chat_id}`"
        bot.send_message("-1003740329904", admin_msg, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception as e:
        print(f"⚠️ Location save error for {chat_id}: {e}", file=sys.stderr)
        
    try:
        res = requests.post(f"{config.API_BASE_URL}/orders/process_location", json={"chat_id": chat_id, "lat": lat, "lon": lon}, timeout=20)
        reply_markup = get_main_reply_markup(lang)
        if res.status_code == 200 and "ok" in res.json().get("status", ""):
            bot.send_message(chat_id, texts["loc_received"], reply_markup=reply_markup)
        else:
            bot.send_message(chat_id, texts["loc_saved"], reply_markup=reply_markup)
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
            paid_amount = response.json().get("paid_amount", 0.0)
            reply_text = texts["receipt_ok"].format(paid_amount=paid_amount)
            
            support_btn_text = "🎧 ផ្នែកបម្រើអតិថិជន (Support)"
            if lang == "zh":
                support_btn_text = "🎧 客服支持 (Support)"
            elif lang == "en":
                support_btn_text = "🎧 Customer Support"
                
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton(support_btn_text, url="https://t.me/XiaoYueXiaoChi"))
            bot.reply_to(message, reply_text, parse_mode="Markdown", reply_markup=markup)
            
            # បង្ហាញប៊ូតុងទាំង ៣ ឡើងវិញដោយប្រើសារណែនាំត្រឹមត្រូវជាជាង "✅"
            bot.send_message(message.chat.id, "👇 លោកអ្នកអាចបន្តការកុម្ម៉ង់ផ្សេងៗទៀតនៅខាងក្រោម៖", reply_markup=get_main_reply_markup(lang))
        else:
            reason = response.json().get("reason", texts["receipt_fail"])
            bot.reply_to(message, reason, parse_mode="Markdown")

    except Exception as e:
        bot.reply_to(message, texts["error"])
        print(f"Photo handling error for {message.chat.id}: {e}", file=sys.stderr)

@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_text_messages(message):
    chat_id = str(message.chat.id)
    
    # 1. ត្រួតពិនិត្យមើលថាតើជាសាររបស់ Admin ឆ្លើយតបទៅភ្ញៀវចេញពីក្នុង Group ដែរឬទេ
    if chat_id == "-1003740329904" or message.chat.id < 0:
        if message.reply_to_message and message.reply_to_message.text and "👉 សូម Reply ត្រឡប់មកកាន់សារនេះ" in message.reply_to_message.text:
            import re
            match = re.search(r"`(\d+)`", message.reply_to_message.text)
            if match:
                try:
                    # ប្រើ API ដើមដើម្បីបាញ់សារទៅភ្ញៀវ និងកត់ត្រាចូល CRM (ព្រមទាំងបិទ AI ១ម៉ោងពេល Admin ចាប់ផ្តើមឆាត)
                    requests.post(f"{config.API_BASE_URL}/crm/reply", json={"chat_id": match.group(1), "user": "Admin", "text": message.text}, timeout=5)
                    bot.send_message(chat_id, f"✅ បានបញ្ជូនសារទៅកាន់ភ្ញៀវសម្រេច!")
                except Exception as e:
                    bot.send_message(chat_id, f"❌ មានបញ្ហាក្នុងការបញ្ជូន: {e}")
        return

    # 2. បើជាសាររបស់ភ្ញៀវ -> បញ្ជូនទៅកាន់ Admin Group
    user_name = message.from_user.first_name or "ភ្ញៀវ"
    admin_group = "-1003740329904"
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("💬 ឆ្លើយតប (Reply)", callback_data=f"admin_reply_{chat_id}"))
    bot.send_message(admin_group, f"💬 *សារពីភ្ញៀវ:* {user_name}\n🆔 ID: `{chat_id}`\n\n{message.text}", parse_mode="Markdown", reply_markup=markup)

    try: requests.post(f"{config.API_BASE_URL}/crm/messages", json={"chat_id": chat_id, "user": user_name, "text": message.text}, timeout=5)
    except: pass

    # 3. ដំណើរការ AI Assistant
    try: res = requests.get(f"{config.API_BASE_URL}/crm/ai_status/{chat_id}", timeout=5); ai_active = res.json().get("ai_active", True) if res.status_code == 200 else True
    except: ai_active = True

    if ai_active:
        try:
            gemini_key = os.getenv("GEMINI_API_KEY", getattr(config, "GEMINI_API_KEY", ""))
            if gemini_key:
                client = genai.Client(api_key=gemini_key)
                response = client.models.generate_content(model='gemini-2.5-flash', contents=f"You are a polite customer service AI for Xiao Yue Xiao Chi. Keep answers brief. Always reply in the language the user writes. User message: {message.text}")
                bot.reply_to(message, response.text)
                bot.send_message(admin_group, f"🤖 *AI បានឆ្លើយតបទៅកាន់ {user_name}:*\n{response.text}", parse_mode="Markdown")
        except Exception as e: print(f"AI error: {e}", file=sys.stderr)

if __name__ == '__main__':
    print("🤖 This script is not meant to be run directly.", file=sys.stderr)
    print("Please run the main FastAPI application using: uvicorn main:app", file=sys.stderr)
    sys.exit(1)