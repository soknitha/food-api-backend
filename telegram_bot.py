import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, ReplyKeyboardMarkup, KeyboardButton
import requests
import os
import io
import qrcode
from google import genai

# ដាក់ Token របស់ Bot អ្នកដែលបានពី BotFather នៅទីនេះ
BOT_TOKEN = "8704188082:AAEZmCT0yNJ9U3WNKte9E1SuJT0K4t4TOz0"

# ដាក់ Link ដែលអ្នកទទួលបានពី Railway (កុំភ្លេចថែម /api នៅខាងចុង)
API_BASE_URL = "https://web-production-88028.up.railway.app/api"

bot = telebot.TeleBot(BOT_TOKEN)

# ---------------- ការកំណត់ AI Gemini ---------------- #
# សូមទៅយក API Key ពី Google AI Studio មកជំនួសត្រង់នេះ
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "ដាក់_API_KEY_GEMINI_នៅទីនេះ")
client = genai.Client(api_key=GEMINI_API_KEY)

# Link ទៅកាន់ Mini App ដែលដំណើរការចេញពី Railway ផ្ទាល់
MINI_APP_URL = "https://web-production-88028.up.railway.app/miniapp"

# បង្កើតកន្ត្រកទំនិញសម្រាប់អតិថិជនម្នាក់ៗ (Shopping Cart)
user_carts = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    # រក្សាទុកព័ត៌មាន User ដោយស្វ័យប្រវត្តិ
    user_id = str(message.from_user.id)
    user_name = message.from_user.first_name or "N/A"
    
    try:
        requests.post(f"{API_BASE_URL}/users", json={"id": user_id, "name": user_name, "phone": "N/A", "location": ""})
    except Exception as e:
        print("Error saving initial user:", e)

    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    btn_phone = KeyboardButton("📱 ចែករំលែកលេខទូរស័ព្ទ", request_contact=True)
    btn_location = KeyboardButton("📍 ចែករំលែកទីតាំង", request_location=True)
    markup.add(btn_phone, btn_location)

    bot.send_message(message.chat.id, "👋 *សួស្តី!* ដើម្បីងាយស្រួលក្នុងការដឹកជញ្ជូន និងទទួលបាន Promotion ពិសេសៗ សូមលោកអ្នកមេត្តាចុចប៊ូតុងខាងក្រោម ដើម្បីចែករំលែកព័ត៌មានមកកាន់ហាងយើងខ្ញុំ។", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    if message.contact is not None:
        user_id = str(message.from_user.id)
        phone_number = message.contact.phone_number
        requests.post(f"{API_BASE_URL}/users", json={"id": user_id, "name": message.from_user.first_name, "phone": phone_number})
        bot.send_message(message.chat.id, "✅ អរគុណ! យើងបានទទួលលេខទូរស័ព្ទរបស់អ្នកហើយ។")
        show_main_menu(message.chat.id)

@bot.message_handler(content_types=['location'])
def handle_location(message):
    if message.location is not None:
        user_id = str(message.from_user.id)
        # អាចប្រើ Google Maps API ដើម្បីបំប្លែង lat/lon ទៅជា Plus Code ពិតប្រាកដ
        plus_code = f"{message.location.latitude},{message.location.longitude}" 
        requests.post(f"{API_BASE_URL}/users", json={"id": user_id, "name": message.from_user.first_name, "phone": "N/A", "location": plus_code})
        bot.send_message(message.chat.id, "✅ អរគុណ! យើងបានទទួលទីតាំងរបស់អ្នកហើយ។")
        show_main_menu(message.chat.id)

def show_main_menu(chat_id):
    welcome_text = "ឥឡូវនេះ លោកអ្នកអាចចាប់ផ្តើមកុម្ម៉ង់អាហារបាន! 👇"
    markup = InlineKeyboardMarkup()
    btn_mini_app = InlineKeyboardButton("📱 បើកកម្មវិធីកុម្ម៉ង់ (Mini App)", web_app=WebAppInfo(url=f"{MINI_APP_URL}"))
    btn_old_menu = InlineKeyboardButton("📜 មើលបញ្ជីមុខម្ហូបធម្មតា", callback_data="show_menu")
    markup.add(btn_mini_app)
    markup.add(btn_old_menu)
    bot.send_message(chat_id, welcome_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "show_menu")
def show_menu(call):
    try:
        # ទាញយកមុខម្ហូបពី FastAPI Backend
        response = requests.get(f"{API_BASE_URL}/menu")
        menu_items = response.json()
        
        if not menu_items:
            bot.send_message(call.message.chat.id, "សុំទោស ហាងរបស់យើងមិនទាន់មានមុខម្ហូបទេពេលនេះ។")
            return
        
        # បង្ហាញមុខម្ហូបនីមួយៗជាសារដាច់ដោយឡែក (មានរូបភាពបើមាន)
        for item in menu_items:
            markup = InlineKeyboardMarkup()
            btn_text = f"🛒 បន្ថែមចូលកន្ត្រក (${item.get('price', 0.0):.2f})"
            btn_data = f"order_{item['id']}"
            markup.add(InlineKeyboardButton(btn_text, callback_data=btn_data))
            
            caption = f"🍕 *{item['name']}*\n💰 តម្លៃ: *${item.get('price', 0.0):.2f}*"
            img_url = item.get('image_url')
            
            if img_url and img_url.strip() != "":
                try:
                    bot.send_photo(call.message.chat.id, photo=img_url, caption=caption, reply_markup=markup, parse_mode="Markdown")
                except Exception:
                    # បើ Link រូបខូច ផ្ញើតែអក្សរ
                    bot.send_message(call.message.chat.id, caption, reply_markup=markup, parse_mode="Markdown")
            else:
                bot.send_message(call.message.chat.id, caption, reply_markup=markup, parse_mode="Markdown")
        
        # ប៊ូតុងទៅមើលកន្ត្រក
        cart_markup = InlineKeyboardMarkup()
        cart_markup.add(InlineKeyboardButton("🛍 មើលកន្ត្រក និងគិតលុយ", callback_data="view_cart"))
        bot.send_message(call.message.chat.id, "👇 បន្ទាប់ពីជ្រើសរើសរួច សូមចុចប៊ូតុងខាងក្រោមដើម្បីទូទាត់ប្រាក់៖", reply_markup=cart_markup)
        
    except Exception as e:
        bot.send_message(call.message.chat.id, "ប្រព័ន្ធកំពុងមានបញ្ហា សូមព្យាយាមម្តងទៀតនៅពេលក្រោយ។")
        print("Error fetching menu:", e)

@bot.callback_query_handler(func=lambda call: call.data.startswith("order_"))
def add_to_cart(call):
    try:
        item_id = int(call.data.split("_")[1])
        response = requests.get(f"{API_BASE_URL}/menu")
        menu_items = response.json()
        
        # ស្វែងរកមុខម្ហូបដែលភ្ញៀវបានចុច
        item = next((x for x in menu_items if x['id'] == item_id), None)
        if item:
            chat_id = call.message.chat.id
            if chat_id not in user_carts:
                user_carts[chat_id] = []
            user_carts[chat_id].append(item)
            
            bot.answer_callback_query(call.id, f"✅ បានបន្ថែម {item['name']} ចូលកន្ត្រក!")
            
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🛍 មើលកន្ត្រក និងគិតលុយ", callback_data="view_cart"))
            markup.add(InlineKeyboardButton("🍕 បន្តកុម្ម៉ង់មុខម្ហូបផ្សេងទៀត", callback_data="show_menu"))
            bot.send_message(chat_id, f"🛒 បច្ចុប្បន្នអ្នកមាន *{len(user_carts[chat_id])}* មុខម្ហូបក្នុងកន្ត្រក។", reply_markup=markup, parse_mode="Markdown")
        else:
            bot.answer_callback_query(call.id, "❌ រកមិនឃើញមុខម្ហូបនេះទេ!")
    except Exception as e:
        print("Error adding to cart:", e)

@bot.callback_query_handler(func=lambda call: call.data == "view_cart")
def view_cart(call):
    chat_id = call.message.chat.id
    cart = user_carts.get(chat_id, [])
    if not cart:
        bot.answer_callback_query(call.id, "កន្ត្រករបស់អ្នកទទេស្អាត!", show_alert=True)
        return
        
    text = "🛒 *កន្ត្រកទំនិញរបស់អ្នក៖*\n\n"
    total = 0
    item_counts = {}
    for item in cart:
        item_counts[item['name']] = item_counts.get(item['name'], 0) + 1
        total += item.get('price', 0.0)
        
    for name, qty in item_counts.items():
        text += f"▪️ {name}  x{qty}\n"
        
    text += f"\n💰 *សរុប៖ ${total:.2f}*"
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✅ បញ្ជាក់ការកុម្ម៉ង់ (Checkout)", callback_data="checkout"))
    markup.add(InlineKeyboardButton("🗑 លុបកន្ត្រកចោល", callback_data="clear_cart"))
    markup.add(InlineKeyboardButton("🔙 ត្រឡប់ទៅម៉ឺនុយ", callback_data="show_menu"))
    
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "clear_cart")
def clear_cart(call):
    chat_id = call.message.chat.id
    user_carts[chat_id] = []
    bot.answer_callback_query(call.id, "🗑 កន្ត្រកត្រូវបានលុបជោគជ័យ!")
    bot.send_message(chat_id, "កន្ត្រករបស់អ្នកទទេស្អាតហើយ។ សូមចុច /start ដើម្បីកុម្ម៉ង់ម្តងទៀត។")

@bot.callback_query_handler(func=lambda call: call.data == "checkout")
def checkout(call):
    chat_id = call.message.chat.id
    cart = user_carts.get(chat_id, [])
    if not cart:
        bot.answer_callback_query(call.id, "កន្ត្រករបស់អ្នកទទេស្អាត!", show_alert=True)
        return
        
    item_counts = {}
    total = 0
    for item in cart:
        item_counts[item['name']] = item_counts.get(item['name'], 0) + 1
        total += item.get('price', 0.0)
        
    items_str = ", ".join([f"{name} x{qty}" for name, qty in item_counts.items()])
    customer_name = call.from_user.first_name or f"អតិថិជន {chat_id}"
    
    order_data = {
        "customer": customer_name,
        "items": items_str,
        "total": f"${total:.2f}",
        "status": "ថ្មី (រង់ចាំការបញ្ជាក់)",
        "chat_id": str(chat_id)
    }
    
    try:
        response = requests.post(f"{API_BASE_URL}/orders", json=order_data)
        if response.status_code == 200:
            bot.answer_callback_query(call.id, "✅ ការបញ្ជាទិញជោគជ័យ!")
            
            # ទាញយកការកំណត់ ABA ពី Backend
            aba_name = "HEM SINATH"
            aba_number = "086599789"
            try:
                config_res = requests.get(f"{API_BASE_URL}/config").json()
                aba_name = config_res.get("aba_name", aba_name)
                aba_number = config_res.get("aba_number", aba_number)
            except:
                pass

            payment_text = (
                f"🎉 *អរគុណសម្រាប់ការកុម្ម៉ង់!*\n\n"
                f"📋 *វិក្កយបត្ររបស់អ្នក៖*\n{items_str}\n"
                f"💰 *សរុបប្រាក់ត្រូវបង់៖ ${total:.2f}*\n\n"
                f"💳 *សូមធ្វើការទូទាត់ប្រាក់មកកាន់គណនី ABA ខាងក្រោម៖*\n"
                f"• ឈ្មោះគណនី៖ *{aba_name}*\n"
                f"• លេខគណនី៖ *{aba_number}*\n\n"
                f"📸 ក្រោយពីបង់ប្រាក់រួច សូមផ្ញើរូបភាពវិក្កយបត្រ (Screenshot) មកទីនេះ ដើម្បីឱ្យយើងរៀបចំអាហារជូនអ្នកភ្លាមៗ។"
            )
            
            # បង្កើត Dynamic QR Code
            qr_data = f"Account: {aba_number}\nName: {aba_name}\nAmount: ${total:.2f}"
            qr = qrcode.make(qr_data)
            bio = io.BytesIO()
            qr.save(bio, format="PNG")
            bio.seek(0)
            bot.send_photo(chat_id, photo=bio, caption=payment_text, parse_mode="Markdown")
            
            user_carts[chat_id] = [] # សម្អាតកន្ត្រកក្រោយទិញរួច
        else:
            bot.send_message(chat_id, "❌ មានបញ្ហាក្នុងការបញ្ជូនការបញ្ជាទិញ។ សូមព្យាយាមម្តងទៀត។")
    except Exception as e:
        bot.send_message(chat_id, "❌ មិនអាចភ្ជាប់ទៅកាន់ប្រព័ន្ធបានទេពេលនេះ។")

# ---------------- ទទួលរូបភាព Screenshot ពីអតិថិជន ---------------- #
@bot.message_handler(content_types=['photo'])
def handle_payment_screenshot(message):
    try:
        chat_id = message.chat.id
        photo_id = message.photo[-1].file_id # យករូបភាពដែលមានគុណភាពច្បាស់ជាងគេ
        file_info = bot.get_file(photo_id)
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
        
        # បញ្ជូន URL រូបភាពទៅកាន់ Backend API
        response = requests.post(f"{API_BASE_URL}/orders/receipt", json={"chat_id": str(chat_id), "image_url": file_url})
        
        if response.status_code == 200:
            res_data = response.json()
            if "error" in res_data:
                bot.reply_to(message, "⚠️ អ្នកមិនមានការបញ្ជាទិញដែលកំពុងរង់ចាំការបង់ប្រាក់ទេ ឬអ្នកបានផ្ញើវិក្កយបត្ររួចហើយ។ សូមចុច /start ដើម្បីធ្វើការកុម្ម៉ង់ជាមុនសិន។")
            else:
                order_id = res_data.get("order_id", "Unknown")
                bot.reply_to(message, f"✅ *ទទួលបានជោគជ័យ!*\n\nរូបភាពបង់ប្រាក់សម្រាប់ការកុម្ម៉ង់លេខ *{order_id}* ត្រូវបានបញ្ជូនទៅកាន់អ្នកលក់រួចរាល់។\n\nសូមរង់ចាំបន្តិច អាហាររបស់អ្នកនឹងរៀបចំជូនក្នុងពេលឆាប់ៗនេះ។ 🛵", parse_mode="Markdown")
        else:
            bot.reply_to(message, "❌ សូមអភ័យទោស ប្រព័ន្ធមិនអាចភ្ជាប់ទៅកាន់ Admin បានទេពេលនេះ។")
    except Exception as e:
        bot.reply_to(message, "❌ មានកំហុសក្នុងការទទួលរូបភាព។")

# បន្ថែមមុខងារឆ្លើយតបពេលអតិថិជនវាយអក្សរធម្មតា (ក្រៅពីពាក្យបញ្ជា /start)
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    # បញ្ជូនសារទៅកាន់ Live Chat CRM របស់ Admin
    try:
        requests.post(f"{API_BASE_URL}/crm/messages", json={
            "chat_id": str(message.chat.id),
            "user": message.from_user.first_name or "អតិថិជន",
            "text": message.text
        })
    except:
        pass

    # ឆែកមើលថាតើ Admin កំពុងឆាតឬអត់ (បើកំពុងឆាត បិទ AI មិនឱ្យឆ្លើយតបទេ)
    try:
        status_res = requests.get(f"{API_BASE_URL}/crm/ai_status/{message.chat.id}")
        if status_res.status_code == 200 and not status_res.json().get("ai_active", True):
            return 
    except:
        pass

    # AI-Powered Chat (ជំនួយការ AI Gemini)
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        prompt = f"អ្នកគឺជាជំនួយការ AI ដ៏ឆ្លាតវៃរបស់ហាងអាហារ '小月小吃'។ សូមឆ្លើយតបយ៉ាងរាក់ទាក់ ជាភាសាខ្មែរ ទៅកាន់អតិថិជន។\n\nសំណួរអតិថិជន: {message.text}"
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt
        )
        
        bot.reply_to(message, response.text)
    except Exception as e:
        print("AI Error:", e)
        bot.reply_to(message, "សុំទោស ខ្ញុំពុំយល់ពាក្យបញ្ជានេះទេ។ សូមចុចពាក្យបញ្ជា /start ដើម្បីចាប់ផ្តើមការកុម្ម៉ង់។")

if __name__ == '__main__':
    print("🤖 Telegram Bot កំពុងដំណើរការ... (ចុច Ctrl+C ដើម្បីបិទ)")
    # bot.infinity_polling(timeout=10, long_polling_timeout=5)
    print("សូមដំណើរការ bot នេះតាមរយៈ FastAPI Webhook នៅក្នុង main.py វិញ។")