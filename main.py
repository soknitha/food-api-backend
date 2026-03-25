import warnings
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, BackgroundTasks, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
import os
import sys
import requests
import asyncio
from supabase import create_client, Client
import telebot
from telegram_bot import bot
from google import genai
from google.genai import types
import time

# Import the centralized configuration
import config

# បិទរាល់សារព្រមាន (Warnings) ទាំងអស់កុំឱ្យលោតរំខាន
warnings.filterwarnings("ignore")

def download_fonts():
    """ ទាញយក Font ខ្មែរ និង ចិន ដោយស្វ័យប្រវត្តិដើម្បីឱ្យវិក្កយបត្រចេញអក្សរបាន ១០០% គ្រប់ភាសា """
    os.makedirs(os.path.dirname(config.KHMER_FONT_PATH), exist_ok=True)
    zh_font_path = config.KHMER_FONT_PATH.replace("Khmer", "SC")
    
    fonts_to_download = {
        config.KHMER_FONT_PATH: "https://github.com/google/fonts/raw/main/ofl/notosanskhmer/NotoSansKhmer-Regular.ttf",
        zh_font_path: "https://github.com/google/fonts/raw/main/ofl/notosanssc/NotoSansSC-Regular.ttf"
    }
    
    for path, url in fonts_to_download.items():
        if not os.path.exists(path):
            print(f"📥 កំពុងទាញយក Font សម្រាប់វិក្កយបត្រ: {os.path.basename(path)}...")
            try:
                res = requests.get(url, timeout=15)
                with open(path, "wb") as f:
                    f.write(res.content)
            except Exception as e:
                print(f"⚠️ មិនអាចទាញយក Font បានទេ: {e}")

# ---------------- Lifespan Manager for Telegram Bot Webhook ---------------- #
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the Telegram webhook setup and removal during the application's lifespan.
    Ensures the webhook is correctly pointed to the public domain from config.
    """
    def startup_tasks():
        try:
            download_fonts()
            print("ℹ️  Setting up Telegram Webhook...")
            # Webhook គឺចាំបាច់បំផុតសម្រាប់ Railway ដើម្បីការពារកុំឱ្យ Server ដេកលក់ (Sleep) និងគាំង
            bot.remove_webhook()
            time.sleep(1) # សម្រាកបន្តិចដើម្បីឱ្យ Telegram ផ្តាច់ Webhook ចាស់ចេញសិន
            bot.set_webhook(url=config.WEBHOOK_URL)
            print(f"✅ Webhook is securely set to: {config.WEBHOOK_URL}")
        except Exception as e:
            print(f"⚠️ Webhook setup failed: {e}", file=sys.stderr)
            
    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, startup_tasks)
    
    yield
    
    print("ℹ️  Application shutting down...")

app = FastAPI(title="Food E-Commerce API", lifespan=lifespan)

# ---------------- CORS Middleware (ការពារការប្លុកទិន្នន័យពី Telegram Web App) ---------------- #
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------- Real-time WebSockets Manager (ល្បឿនផ្លេកបន្ទោរ) ---------------- #
class WSConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

ws_manager = WSConnectionManager()

async def broadcast_ws_event(event_type: str, data: dict):
    await ws_manager.broadcast({"type": event_type, "data": data})

# ---------------- កំណត់ទីតាំងរក្សាទុករូបភាព (Static Files) ---------------- #
UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# ---------------- Supabase Database Connection ---------------- #
try:
    supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    USE_SUPABASE = True
    print("✅ Successfully connected to Supabase! ធានាសុវត្ថិភាពទិន្នន័យ ១០០% មិនបាត់បង់។")
except Exception as e:
    print(f"❌ FATAL ERROR: មិនអាចភ្ជាប់ទៅកាន់មូលដ្ឋានទិន្នន័យបានទេ: {e}", file=sys.stderr)
    sys.exit("ប្រព័ន្ធទាមទារឱ្យមាន Database (Supabase) ដើម្បីដំណើរការ និងការពារការបាត់បង់ទិន្នន័យ។")


# ទិន្នន័យសាកល្បង (Mock Database ក្នុង Memory)
orders_db = [
    {"id": "#001", "customer": "សុខ សាន្ត", "items": "ភីហ្សា x1, កូកា x2", "total": "$15.50", "status": "កំពុងចម្អិន"},
    {"id": "#002", "customer": "ចាន់ ធី", "items": "បឺហ្គឺ x2", "total": "$8.00", "status": "កំពុងដឹកជញ្ជូន"}
]

menu_db = [
    {"id": 1, "name": "ភីហ្សា (Pizza)", "price": 8.50},
    {"id": 2, "name": "បឺហ្គឺ (Burger)", "price": 4.00}
]
menu_id_counter = 3

users_db = [
    {"id": 1, "name": "សុខ សាន្ត", "phone": "012345678", "points": 150},
    {"id": 2, "name": "ចាន់ ធី", "phone": "098765432", "points": 45}
]
user_id_counter = 3

# ទិន្នន័យថ្មីសម្រាប់ CRM និង Config
crm_messages_db = []
admin_active_chats = {} # ផ្ទុកពេលវេលាដែល Admin បានឆាតចុងក្រោយ
app_config_db = {
    "banner_url": "https://via.placeholder.com/600x200?text=Welcome+to+Xiao+Yue+Xiao+Chi",
    "is_open": True,
    "aba_name": "HEM SINATH",
    "aba_number": "086599789",
    "kitchen_group_id": "-1003740329904",
    "reward_points": 50,
    "reward_discount": 5.0
}

class MenuItem(BaseModel):
    name: str
    price: float
    image_url: str = ""

class UserItem(BaseModel):
    id: str = ""
    name: str
    phone: str = "N/A"
    location: str = ""
    language: str = ""

class OrderCreate(BaseModel):
    customer: str
    items: str
    total: str
    status: str = "ថ្មី (រង់ចាំការបញ្ជាក់)"
    chat_id: str = ""
    redeem_points: int = 0

class OrderStatusUpdate(BaseModel):
    order_id: str
    status: str

class OrderReceipt(BaseModel):
    chat_id: str
    image_url: str

class ChatMessage(BaseModel):
    chat_id: str
    user: str
    text: str
    is_admin: bool = False

class BroadcastRequest(BaseModel):
    target: str # 'all', 'pending'
    text: str

class FinalizeOrderData(BaseModel):
    order_id: str
    chat_id: str
    delivery_fee: float
    distance: float = 0.0

class ProcessLocationReq(BaseModel):
    chat_id: str
    lat: float
    lon: float

class AppConfig(BaseModel):
    banner_url: str
    is_open: bool
    aba_name: str
    aba_number: str
    kitchen_group_id: str
    reward_points: int = 50
    reward_discount: float = 5.0

class MenuReorderItem(BaseModel):
    id: int
    sort_order: int

# ---------------- វចនានុក្រមភាសាសម្រាប់រាល់សាររបស់ Bot (Bot Localization) ---------------- #
BOT_LANG_DICT = {
    "km": {
        "checkout_initial": "🎉 *ទទួលបានការកុម្ម៉ង់បឋម!*\n\n🧾 លេខវិក្កយបត្រ: `{order_id}`\n\nតើលោកអ្នកចង់មកយកផ្ទាល់ ឬឱ្យហាងដឹកជូន?",
        "pickup_btn": "🏪 មកយកផ្ទាល់នៅហាង (Pickup)",
        "delivery_btn": "🛵 ហាងដឹកជូនផ្ទាល់ (Delivery)",
        "payment_text": "🎉 *ការកុម្ម៉ង់ទទួលបានជោគជ័យ!*\n\n🧾 *លេខវិក្កយបត្រ:* `{order_id}`\n👤 *អតិថិជន:* {customer}\n📱 *គណនី Telegram:* {chat_id}\n📞 *លេខទូរស័ព្ទ:* {user_phone}\n📍 *ទីតាំង:* {user_loc}\n\n🛒 *មុខម្ហូបដែលបានកុម្ម៉ង់:*\n{formatted_items}\n💰 *សរុបប្រាក់ត្រូវបង់:* {total}\n\n💳 *សូមធ្វើការទូទាត់ប្រាក់មកកាន់គណនី ABA & ACLEDA ខាងក្រោម៖*\n• ឈ្មោះគណនី៖ {aba_name}\n• លេខគណនី៖ `{aba_number}`\n\n📸 ក្រោយពីបង់ប្រាក់រួច សូមផ្ញើរូបភាពវិក្កយបត្រ (Screenshot) មកទីនេះ ដើម្បីឱ្យយើងរៀបចំអាហារជូនអ្នកភ្លាមៗ។",
        "payment_success_user": "✅ *ការទូទាត់របស់អ្នកទទួលបានជោគជ័យ!*\n\n💰 ចំនួនទឹកប្រាក់បានទូទាត់: *${paid_amount:.2f}*\n\nសូមរង់ចាំអាហាររបស់អ្នកបន្តិច... 🛵 ប្រសិនបើមានចម្ងល់អាចទាក់ទងមកកាន់ Admin តាមរយៈប៊ូតុងខាងក្រោម។",
        "status_update": "🔔 *ជម្រាបសួរ {customer}*\nការកុម្ម៉ង់លេខ {order_id} របស់អ្នកត្រូវបានប្តូរស្ថានភាពទៅជា៖ *{status}*",
        "points_earned": "🎁 *អបអរសាទរ!* អ្នកទទួលបាន *{points} ពិន្ទុសន្សំ* ពីការទិញនេះ។\nបច្ចុប្បន្នអ្នកមានពិន្ទុសរុប៖ *{new_points} ពិន្ទុ* 🌟",
        "promo_50": "🎉 *កាដូពិសេសពីហាង 小月小吃!*\n\nអ្នកសន្សំបាន ៥០ ពិន្ទុហើយ! 🎁\nយើងខ្ញុំសូមជូន *ភេសជ្ជៈ ១ កែវ ឥតគិតថ្លៃ* សម្រាប់ការកុម្ម៉ង់លើកក្រោយ។\n*(សូម Screenshot សារនេះបង្ហាញទៅកាន់អ្នកលក់)*",
        "promo_100": "🎉 *កាដូពិសេសពីហាង 小月小吃!*\n\nអស្ចារ្យណាស់! អ្នកសន្សំបាន ១០០ ពិន្ទុ! 🎁\nយើងខ្ញុំសូមជូន *ការបញ្ចុះតម្លៃ $5.00* សម្រាប់ការកុម្ម៉ង់លើកក្រោយ។\n*(សូម Screenshot សារនេះបង្ហាញទៅកាន់អ្នកលក់)*",
        "receipt_shop": "ហាង 小月小吃",
        "receipt_title": "វិក្កយបត្រ / RECEIPT",
        "receipt_invoice": "លេខវិក្កយបត្រ:",
        "receipt_date": "កាលបរិច្ឆេទ:",
        "receipt_customer": "អតិថិជន:",
        "receipt_items": "មុខម្ហូប / Items",
        "receipt_total": "សរុប / Total Due:",
        "receipt_paid": "បានបង់ / Amount Paid:",
        "receipt_footer": "*** បង់ប្រាក់រួចរាល់ ***",
        "receipt_thanks": "សូមអរគុណដែលបានគាំទ្រ!",
        "ai_error": "មានបញ្ហាក្នុងការស្កេនវិក្កយបត្រ សូមសាកល្បងម្ដងទៀត។",
        "payment_reject_user": "⚠️ *ការទូទាត់ត្រូវបានបដិសេធ!*\n\nមូលហេតុ: {reason}\n\nសូមថតរូបវិក្កយបត្រឱ្យបានច្បាស់ រួចផ្ញើម្ដងទៀត ឬទាក់ទងមកកាន់ Admin។",
        "ai_error_scan": "ប្រព័ន្ធមិនអាចអានចំនួនទឹកប្រាក់ពីរូបភាពនេះបានទេ។ សូមថតឱ្យបានច្បាស់។",
        "ai_error_amount": "ចំនួនទឹកប្រាក់មិនគ្រប់គ្រាន់ (បានបង់: ${paid:.2f} / ត្រូវបង់: ${expected:.2f})។"
    },
    "zh": {
        "checkout_initial": "🎉 *收到初步订单！*\n\n🧾 订单编号: `{order_id}`\n\n您想自取还是让我们送货？",
        "pickup_btn": "🏪 到店自取 (Pickup)",
        "delivery_btn": "🛵 商店配送 (Delivery)",
        "payment_text": "🎉 *下单成功！*\n\n🧾 *订单编号:* `{order_id}`\n👤 *客户:* {customer}\n📱 *Telegram:* {chat_id}\n📞 *电话:* {user_phone}\n📍 *位置:* {user_loc}\n\n🛒 *已点菜品:*\n{formatted_items}\n💰 *总计:* {total}\n\n💳 *请向以下 ABA 或 ACLEDA 账户付款：*\n• 账户名称：{aba_name}\n• 账号：`{aba_number}`\n\n📸 付款后，请在此发送付款截图，以便我们立即为您准备食物。",
        "payment_success_user": "✅ *您的付款已成功！*\n\n💰 已付金额: *${paid_amount:.2f}*\n\n请稍候，您的食物马上就好... 🛵 如果您有任何疑问，请通过下面的按钮联系管理员。",
        "status_update": "🔔 *您好 {customer}*\n您的订单 {order_id} 状态已更新为：*{status}*",
        "points_earned": "🎁 *恭喜！* 您从此次购买中获得了 *{points} 积分*。\n您当前的总积分为：*{new_points} 分* 🌟",
        "promo_50": "🎉 *小月小吃的特别礼物！*\n\n您已累积 50 积分！🎁\n下次点餐我们将免费赠送 *1 杯饮料*。\n*(请截图此消息并出示给卖家)*",
        "promo_100": "🎉 *小月小吃的特别礼物！*\n\n太棒了！您已累积 100 积分！🎁\n下次点餐我们将提供 *$5.00 折扣*。\n*(请截图此消息并出示给卖家)*",
        "receipt_shop": "小月小吃",
        "receipt_title": "收据 / RECEIPT",
        "receipt_invoice": "订单编号:",
        "receipt_date": "日期:",
        "receipt_customer": "客户:",
        "receipt_items": "项目 / Items",
        "receipt_total": "总计 / Total Due:",
        "receipt_paid": "已付 / Amount Paid:",
        "receipt_footer": "*** 已付款 ***",
        "receipt_thanks": "感谢您的支持！",
        "ai_error": "扫描收据时出错。请重试。",
        "payment_reject_user": "⚠️ *付款被拒绝！*\n\n原因: {reason}\n\n请清晰拍照并重试，或联系管理员。",
        "ai_error_scan": "系统无法从此图像中读取金额。请重新拍摄清晰的照片。",
        "ai_error_amount": "付款金额不足（已付: ${paid:.2f} / 应付: ${expected:.2f}）。"
    },
    "en": {
        "checkout_initial": "🎉 *Preliminary Order Received!*\n\n🧾 Invoice No: `{order_id}`\n\nWould you like to pick it up or have it delivered?",
        "pickup_btn": "🏪 Store Pickup",
        "delivery_btn": "🛵 Store Delivery",
        "payment_text": "🎉 *Order Placed Successfully!*\n\n🧾 *Invoice No:* `{order_id}`\n👤 *Customer:* {customer}\n📱 *Telegram:* {chat_id}\n📞 *Phone:* {user_phone}\n📍 *Location:* {user_loc}\n\n🛒 *Ordered Items:*\n{formatted_items}\n💰 *Total Due:* {total}\n\n💳 *Please make a payment to the ABA & ACLEDA account below:*\n• Account Name: {aba_name}\n• Account Number: `{aba_number}`\n\n📸 After payment, please send the receipt screenshot here so we can prepare your food immediately.",
        "payment_success_user": "✅ *Your payment was successful!*\n\n💰 Amount paid: *${paid_amount:.2f}*\n\nPlease wait a moment for your food... 🛵 If you have any questions, you can contact Admin via the button below.",
        "status_update": "🔔 *Hello {customer}*\nYour order {order_id} status has been updated to: *{status}*",
        "points_earned": "🎁 *Congratulations!* You earned *{points} points* from this purchase.\nYour current total points: *{new_points} points* 🌟",
        "promo_50": "🎉 *Special Gift from Xiao Yue Xiao Chi!*\n\nYou've collected 50 points! 🎁\nWe offer *1 free drink* for your next order.\n*(Please screenshot this message and show it to the seller)*",
        "promo_100": "🎉 *Special Gift from Xiao Yue Xiao Chi!*\n\nAwesome! You've collected 100 points! 🎁\nWe offer a *$5.00 discount* for your next order.\n*(Please screenshot this message and show it to the seller)*",
        "receipt_shop": "Xiao Yue Xiao Chi",
        "receipt_title": "RECEIPT",
        "receipt_invoice": "Invoice No:",
        "receipt_date": "Date:",
        "receipt_customer": "Customer:",
        "receipt_items": "Items",
        "receipt_total": "Total Due:",
        "receipt_paid": "Amount Paid:",
        "receipt_footer": "*** PAID ***",
        "receipt_thanks": "Thank you for your support!",
        "ai_error": "Error scanning receipt. Please try again.",
        "payment_reject_user": "⚠️ *Payment Rejected!*\n\nReason: {reason}\n\nPlease take a clear photo and try again, or contact Admin.",
        "ai_error_scan": "The system could not read the amount from this image. Please take a clear photo.",
        "ai_error_amount": "Insufficient payment amount (Paid: ${paid:.2f} / Expected: ${expected:.2f})."
    }
}

def get_user_lang_from_db(chat_id):
    """ ទាញយកភាសាដែលអតិថិជនបានជ្រើសរើសពីមូលដ្ឋានទិន្នន័យ """
    if USE_SUPABASE:
        try:
            res = supabase.table("users").select("language").eq("chat_id", str(chat_id)).execute()
            if res.data and res.data[0].get("language"):
                return res.data[0]["language"]
        except Exception: pass
    for u in users_db:
        if str(u.get("chat_id")) == str(chat_id):
            return u.get("language", "km")
    return "km"

@app.get("/")
def read_root():
    return {"message": "🎉 Server ដំណើរការយ៉ាងរលូន! នេះគឺជា Food E-Commerce API."}

@app.get("/init", response_class=HTMLResponse)
def init_system(request: Request):
    return f"<div style='text-align:center; margin-top:50px; font-family:Arial;'><h2>✅ ប្រព័ន្ធ Bot កំពុងដំណើរការយ៉ាងរលូន!</h2><h3 style='color:green;'>Domain បច្ចុប្បន្ន៖ {config.DOMAIN}</h3><p>🔗 URL របស់ Mini App គឺ៖ <b>{config.MINI_APP_URL}</b></p><br><h3>👉 សូមចូលទៅកាន់ Telegram រួចចុច <b style='color:blue;'>/start</b> ម្តងទៀត ដើម្បីបើកមុខម្ហូប។</h3></div>"

@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

@app.post("/webhook")
async def handle_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handles incoming updates from the Telegram webhook."""
    try:
        json_str = await request.body()
        update = telebot.types.Update.de_json(json_str.decode('utf-8'))
        
        # ដំណើរការនៅក្នុង Background Task ដោយរលូន និងគ្មានការកកស្ទះ
        background_tasks.add_task(bot.process_new_updates, [update])
        
        return Response(status_code=200)
    except Exception as e:
        print(f"❌ Error in webhook handler: {e}", file=sys.stderr)
        return Response(status_code=500)


# ---------------- បម្រើ (Serve) គេហទំព័រ Mini App ដោយផ្ទាល់ ---------------- #
@app.get("/miniapp", response_class=HTMLResponse)
def serve_miniapp(response: Response):
    # បំពាក់ Cache-Control រក្សាគេហទំព័រទុក ១ថ្ងៃពេញ ធ្វើឱ្យ Mini App បើកលោតចេញភ្លាមៗ (0ms)
    response.headers["Cache-Control"] = "public, max-age=86400"
    # ប្រើប្រាស់ទីតាំងពិតប្រាកដ (Absolute Path) ដើម្បីប្រាកដថាវារកឃើញឯកសារ index.html ជានិច្ច
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>កំពុងរៀបចំប្រព័ន្ធ... រកមិនឃើញឯកសារ index.html ទេ</h1>"

@app.get("/api/orders")
def get_orders():
    if USE_SUPABASE:
        try:
            response = supabase.table("orders").select("*").order("created_at").execute()
            return response.data
        except Exception as e:
            print(f"⚠️ Column created_at missing, falling back to unsorted orders: {e}")
            try:
                response = supabase.table("orders").select("*").execute()
                return response.data
            except Exception as e2:
                pass # បើ Supabase គាំងទាំងស្រុង, បន្តទៅប្រើទិន្នន័យបម្រុងពី Memory
    return orders_db

@app.post("/api/orders")
def create_order(order: OrderCreate, background_tasks: BackgroundTasks):
    import random
    
    items_text = order.items
    if order.redeem_points > 0:
        items_text += f"\n🎁 (ប្រើប្រាស់ {order.redeem_points} ពិន្ទុ)"
        
    new_order = {
        "id": f"#{random.randint(1000, 9999)}",
        "customer": order.customer,
        "items": items_text,
        "total": order.total,
        "status": order.status,
        "chat_id": order.chat_id,
        "receipt_url": ""
    }
    if USE_SUPABASE:
        response = supabase.table("orders").insert(new_order).execute()
        new_order = response.data[0]
    else:
        orders_db.append(new_order)
        
    # បាញ់សារទៅ Group ផ្ទះបាយ
    kitchen_id = app_config_db.get("kitchen_group_id")
    if kitchen_id:
        kitchen_msg = f"🧑‍🍳 *មានការកុម្ម៉ង់ថ្មី (ពី Telegram Bot)*\n\n🧾 *វិក្កយបត្រ:* `{new_order['id']}`\n🛒 *មុខម្ហូប:*\n{new_order['items'].replace(', ', '%0A')}"
        requests.post(f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage", json={"chat_id": kitchen_id, "text": kitchen_msg, "parse_mode": "Markdown"})
        
    background_tasks.add_task(broadcast_ws_event, "NEW_ORDER", new_order)
    return new_order

# ---------------- Action-Triggered Notification (ពី Mini App) ---------------- #
@app.post("/api/miniapp/checkout")
def miniapp_checkout(order: OrderCreate, background_tasks: BackgroundTasks):
    import random
    new_order = {
        "id": f"#{random.randint(1000, 9999)}",
        "customer": order.customer,
        "items": order.items,
        "total": order.total,
        "status": "រង់ចាំជម្រើសដឹកជញ្ជូន",
        "chat_id": order.chat_id,
        "receipt_url": ""
    }
    if USE_SUPABASE:
        supabase.table("orders").insert(new_order).execute()
    else:
        orders_db.append(new_order)

    # កាត់ពិន្ទុអតិថិជនចេញ
    if order.redeem_points > 0 and order.chat_id:
        if USE_SUPABASE:
            res = supabase.table("users").select("points", "id").eq("chat_id", order.chat_id).execute()
            if res.data:
                u_id = res.data[0]['id']
                curr_pts = res.data[0].get('points', 0)
                if curr_pts >= order.redeem_points:
                    supabase.table("users").update({"points": curr_pts - order.redeem_points}).eq("id", u_id).execute()
        else:
            for u in users_db:
                if u.get("chat_id") == order.chat_id:
                    if u.get("points", 0) >= order.redeem_points:
                        u["points"] -= order.redeem_points

    if order.chat_id:
        lang = get_user_lang_from_db(order.chat_id)
        texts = BOT_LANG_DICT.get(lang, BOT_LANG_DICT["km"])
        markup = {
            "inline_keyboard": [
                [{"text": texts["pickup_btn"], "callback_data": f"pickup_{new_order['id']}"}],
                [{"text": texts["delivery_btn"], "callback_data": f"delivery_{new_order['id']}"}]
            ]
        }
        msg_text = texts["checkout_initial"].format(order_id=new_order['id'])
        requests.post(f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage", json={
            "chat_id": order.chat_id,
            "text": msg_text,
            "parse_mode": "Markdown",
            "reply_markup": markup
        })
        
    background_tasks.add_task(broadcast_ws_event, "NEW_ORDER", new_order)
    return {"message": "Order placed and receipt sent", "order": new_order}

def finalize_order_internal(order_id, chat_id, fee, distance=0):
    order = None
    if USE_SUPABASE:
        res = supabase.table("orders").select("*").eq("id", order_id).execute()
        if res.data:
            order = res.data[0]
    else:
        for o in orders_db:
            if o["id"] == order_id:
                order = o
                break
    if not order:
        return
    
    new_items = order["items"]
    current_total_str = order["total"].replace("$", "").replace(",", "")
    try:
        current_total = float(current_total_str)
    except Exception:
        current_total = 0.0
    
    if fee > 0:
        new_items += f", 🛵 ថ្លៃដឹកជញ្ជូន ({distance:.1f}km) x1 (${fee:.2f})"
        current_total += fee
        
    new_total_str = f"${current_total:.2f}"
    
    if USE_SUPABASE:
        supabase.table("orders").update({"items": new_items, "total": new_total_str, "status": "ថ្មី (រង់ចាំការបញ្ជាក់)"}).eq("id", order_id).execute()
        order["items"] = new_items
        order["total"] = new_total_str
    else:
        order["items"] = new_items
        order["total"] = new_total_str
        order["status"] = "ថ្មី (រង់ចាំការបញ្ជាក់)"

    kitchen_id = app_config_db.get("kitchen_group_id")
    if kitchen_id:
        kitchen_msg = f"🧑‍🍳 *មានការកុម្ម៉ង់ថ្មី (ពី Mini App)*\n\n🧾 *វិក្កយបត្រ:* `{order['id']}`\n🛒 *មុខម្ហូប:*\n{order['items'].replace(', ', '%0A')}"
        requests.post(f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage", json={"chat_id": kitchen_id, "text": kitchen_msg, "parse_mode": "Markdown"})

    user_phone = "មិនមាន"
    user_loc = "មិនមាន"
    if USE_SUPABASE:
        res = supabase.table("users").select("*").eq("chat_id", chat_id).execute()
        if res.data:
            user_phone = res.data[0].get("phone", "មិនមាន")
            user_loc = res.data[0].get("location", "មិនមាន")
    else:
        for u in users_db:
            if str(u.get("chat_id")) == str(chat_id):
                user_phone = u.get("phone", "មិនមាន")
                user_loc = u.get("location", "មិនមាន")

    raw_items = order["items"].split(",")
    formatted_items = ""
    for idx, itm in enumerate(raw_items):
        if itm.strip():
            formatted_items += f"{idx + 1}. {itm.strip()}\n"

    lang = get_user_lang_from_db(chat_id)
    texts = BOT_LANG_DICT.get(lang, BOT_LANG_DICT["km"])
    aba_name = app_config_db.get("aba_name", "HEM SINATH")
    aba_number = app_config_db.get("aba_number", "086599789")
    
    payment_text = texts["payment_text"].format(
        order_id=order['id'],
        customer=order['customer'],
        chat_id=chat_id,
        user_phone=user_phone,
        user_loc=user_loc,
        formatted_items=formatted_items,
        total=order['total'],
        aba_name=aba_name,
        aba_number=aba_number
    )
    
    qr_path = os.path.join(os.path.dirname(__file__), "aba_qr.jpg")
    if os.path.exists(qr_path):
        with open(qr_path, "rb") as f:
            qr_bytes = f.read()
        
        # ធានាថារូបភាពត្រូវបានផ្ញើភ្ជាប់ជាមួយគ្នា ១០០%
        res_user = requests.post(f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendPhoto", data={'chat_id': chat_id, 'caption': payment_text, 'parse_mode': 'Markdown'}, files={'photo': ('aba_qr.jpg', qr_bytes, 'image/jpeg')})
        if res_user.status_code != 200:
            requests.post(f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage", json={'chat_id': chat_id, 'text': payment_text, 'parse_mode': 'Markdown'})
            
        requests.post(f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendPhoto", data={'chat_id': app_config_db.get("kitchen_group_id", "-1003740329904"), 'caption': f"🔔 *New Order Alert!*\n\n{payment_text}", 'parse_mode': 'Markdown'}, files={'photo': ('aba_qr.jpg', qr_bytes, 'image/jpeg')})
    else:
        # បម្រុងទុក (Fallback)៖ បើសិនជាបាត់រូប aba_qr.jpg ក៏វានៅតែបាញ់អត្ថបទវិក្កយបត្រទៅដែរ
        requests.post(f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage", json={'chat_id': chat_id, 'text': payment_text, 'parse_mode': 'Markdown'})
        requests.post(f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage", json={'chat_id': app_config_db.get("kitchen_group_id", "-1003740329904"), 'text': f"🔔 *New Order Alert!*\n\n{payment_text}", 'parse_mode': 'Markdown'})

@app.post("/api/orders/finalize")
def finalize_order_api(data: FinalizeOrderData):
    finalize_order_internal(data.order_id, data.chat_id, data.delivery_fee, data.distance)
    return {"status": "ok"}

@app.post("/api/orders/process_location")
def process_location_api(data: ProcessLocationReq):
    import math
    def calculate_distance(lat1, lon1, lat2, lon2):
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2) * math.sin(dlon/2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c
        
    # ទីតាំងហាងជាក់ស្តែងទំនើបបំផុត Xiao Yue Xiao Chi (HV46+M8V Phnom Penh / 11.556750, 104.860800)
    STORE_LAT = 11.556750
    STORE_LON = 104.860800
    dist = calculate_distance(STORE_LAT, STORE_LON, data.lat, data.lon)
    
    if dist <= 1:
        fee = 0.50
    elif dist <= 5:
        fee = 1.00
    elif dist <= 7:
        fee = 1.50
    elif dist <= 9:
        fee = 2.00
    elif dist <= 15:
        fee = 2.50
    elif dist <= 20:
        fee = 3.50
    else:
        fee = 4.00
    
    order_to_process = None
    if USE_SUPABASE:
        res = supabase.table("orders").select("*").eq("chat_id", data.chat_id).eq("status", "រង់ចាំទីតាំង").execute()
        if res.data:
            order_to_process = res.data[-1]
    else:
        for o in reversed(orders_db):
            if str(o.get("chat_id")) == data.chat_id and o.get("status") == "រង់ចាំទីតាំង":
                order_to_process = o
                break
                
    if order_to_process:
        finalize_order_internal(order_to_process["id"], data.chat_id, fee, dist)
        return {"status": "ok"}
    return {"error": "no order found"}

@app.put("/api/orders/status")
def update_order_status(status_update: OrderStatusUpdate, background_tasks: BackgroundTasks):
    order = None
    if USE_SUPABASE:
        response = supabase.table("orders").update({"status": status_update.status}).eq("id", status_update.order_id).execute()
        if response.data:
            order = response.data[0]
    else:
        for o in orders_db:
            if o["id"] == status_update.order_id:
                o["status"] = status_update.status
                order = o
                break
                
    if order:
        # បាញ់សារទៅប្រាប់អតិថិជនតាម Telegram ពេល Admin ប្តូរស្ថានភាព
        if order.get("chat_id"):
            lang = get_user_lang_from_db(order["chat_id"])
            texts = BOT_LANG_DICT.get(lang, BOT_LANG_DICT["km"])
            msg_text = texts["status_update"].format(customer=order['customer'], order_id=order['id'], status=status_update.status)
            requests.post(f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage", json={"chat_id": order["chat_id"], "text": msg_text, "parse_mode": "Markdown"})
            
        # ---------------- មុខងារ Loyalty Points ---------------- #
        if status_update.status == "✅ រួចរាល់ (បានប្រគល់)":
            try:
                total_amount = float(order['total'].replace('$', '').replace(',', ''))
                points_earned = int(total_amount) # ទិញ ១ ដុល្លារ បាន ១ ពិន្ទុ
                if points_earned > 0:
                    new_points = 0
                    if USE_SUPABASE:
                        user_chat_id = order.get("chat_id")
                        if not user_chat_id:
                            import random
                            user_chat_id = f"manual_{random.randint(10000, 99999)}"
                            user_chat_id = f"99{random.randint(1000000, 9999999)}"
                        res = supabase.table("users").select("*").eq("id", user_chat_id).execute()
                        if res.data:
                            user_id = res.data[0]['id']
                            new_points = res.data[0].get('points', 0) + points_earned
                            supabase.table("users").update({"points": new_points}).eq("id", user_id).execute()
                        else:
                            new_points = points_earned
                            supabase.table("users").insert({"id": user_chat_id, "name": order["customer"], "phone": "N/A", "points": points_earned, "chat_id": user_chat_id}).execute()
                    else:
                        user_found = False
                        for u in users_db:
                            if u["name"] == order["customer"]:
                                u["points"] = u.get("points", 0) + points_earned
                                u["chat_id"] = order.get("chat_id", "")
                                new_points = u["points"]
                                user_found = True
                                break
                        if not user_found:
                            global user_id_counter
                            new_points = points_earned
                            users_db.append({"id": order.get("chat_id", str(user_id_counter)), "name": order["customer"], "phone": "N/A", "points": points_earned, "chat_id": order.get("chat_id", "")})
                            user_id_counter += 1

                    if order.get("chat_id"):
                        pts_msg = texts["points_earned"].format(points=points_earned, new_points=new_points)
                        requests.post(f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage", json={"chat_id": order["chat_id"], "text": pts_msg, "parse_mode": "Markdown"})
                        
                        # ---- ផ្ញើសារ Promotion ដោយស្វ័យប្រវត្តិ ---- #
                        old_points = new_points - points_earned
                        if new_points >= 50 and old_points < 50:
                            promo_msg = texts["promo_50"]
                            requests.post(f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage", json={"chat_id": order["chat_id"], "text": promo_msg, "parse_mode": "Markdown"})
                        elif new_points >= 100 and old_points < 100:
                            promo_msg = texts["promo_100"]
                            requests.post(f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage", json={"chat_id": order["chat_id"], "text": promo_msg, "parse_mode": "Markdown"})
            except Exception as e:
                print("Error adding points:", e)
        background_tasks.add_task(broadcast_ws_event, "UPDATE_ORDER", order)
                
        return {"message": "Status updated successfully", "order": order}
    return {"error": "Order not found"}

def generate_receipt_image(order_data, amount_paid, lang="km"):
    """ Generates a highly professional POS-style PNG receipt image based on user's language. (High Definition - Retina Ready) """
    try:
        from PIL import Image, ImageDraw, ImageFont
        import io
        from datetime import datetime
        
        texts = BOT_LANG_DICT.get(lang, BOT_LANG_DICT["km"])
        items_list = [item.strip() for item in order_data["items"].split(",") if item.strip()]
        
        # បង្កើនគុណភាពរូបភាព ២ ដង (High Resolution - Retina Display)
        scale = 2
        width = 500 * scale
        base_height = 600 * scale
        height = base_height + (len(items_list) * 50 * scale)
        
        # ពណ៌ទូទៅ (Modern Colors Design)
        bg_color = (245, 247, 250)      # ពណ៌ផ្ទៃខាងក្រោយរាងប្រផេះស្រាល
        card_color = (255, 255, 255)    # ពណ៌សន្លឹកវិក្កយបត្រ
        text_main = (33, 37, 41)        # ពណ៌អក្សរគោល (ខ្មៅចាស់)
        text_muted = (108, 117, 125)    # ពណ៌អក្សរបន្ទាប់បន្សំ (ប្រផេះ)
        primary_color = (39, 174, 96)   # ពណ៌បៃតងបញ្ជាក់ការទូទាត់
        border_color = (226, 232, 240)  # ពណ៌បន្ទាត់ខណ្ឌ
        
        img = Image.new('RGB', (width, height), color=bg_color)
        d = ImageDraw.Draw(img)
        
        # គូសផ្ទៃកាតវិក្កយបត្រពណ៌សកណ្តាលមានកែងមូល (Modern Card Style)
        margin = 25 * scale
        d.rounded_rectangle([(margin, margin), (width - margin, height - margin)], radius=15*scale, fill=card_color, outline=border_color, width=2*scale)
        
        zh_font_path = config.KHMER_FONT_PATH.replace("Khmer", "SC")
        active_font_path = zh_font_path if lang == "zh" else config.KHMER_FONT_PATH
        if not os.path.exists(active_font_path):
            active_font_path = config.KHMER_FONT_PATH
        
        try:
            font_shop = ImageFont.truetype(active_font_path, 36 * scale)
            font_title = ImageFont.truetype(active_font_path, 28 * scale)
            font_bold = ImageFont.truetype(active_font_path, 22 * scale)
            font_text = ImageFont.truetype(active_font_path, 20 * scale)
            font_small = ImageFont.truetype(active_font_path, 16 * scale)
        except Exception as e:
            print(f"⚠️  Font Error: {e}. Falling back to default font.", file=sys.stderr)
            font_shop = font_title = font_text = font_bold = font_small = ImageFont.load_default()

        def draw_centered(y_pos, text_val, f_type, fill=text_main):
            try:
                bbox = d.textbbox((0, 0), text_val, font=f_type)
                w = bbox[2] - bbox[0]
            except AttributeError:
                w = d.textlength(text_val, font=f_type)
            d.text(((width - w) / 2, y_pos), text_val, fill=fill, font=f_type)
            
        def draw_divider(y_pos):
            d.line([(margin * 1.5, y_pos), (width - margin * 1.5, y_pos)], fill=border_color, width=2*scale)
            
        def draw_row(y_pos, left_text, right_text, f_type_left, f_type_right, fill_left=text_muted, fill_right=text_main):
            d.text((margin * 1.5, y_pos), left_text, fill=fill_left, font=f_type_left)
            try: w = d.textbbox((0, 0), right_text, font=f_type_right)[2]
            except AttributeError: w = d.textlength(right_text, font=f_type_right)
            d.text((width - margin * 1.5 - w, y_pos), right_text, fill=fill_right, font=f_type_right)

        # --- Header ---
        y = margin + 35 * scale
        draw_centered(y, texts["receipt_shop"], font_shop)
        y += 60 * scale
        
        # Badge "PAID" រចនាបែបទំនើប (Modern Dynamic Badge)
        paid_text = texts.get("receipt_footer", "*** PAID ***").replace("*", "").strip()
        try: bw = d.textbbox((0, 0), paid_text, font=font_small)[2]
        except AttributeError: bw = d.textlength(paid_text, font=font_small)
        badge_x1 = (width - bw - 40*scale) / 2
        badge_x2 = badge_x1 + bw + 40*scale
        d.rounded_rectangle([(badge_x1, y), (badge_x2, y + 35*scale)], radius=17*scale, fill=(233, 247, 239))
        draw_centered(y + 6*scale, paid_text, font_small, fill=primary_color)
        
        y += 70 * scale
        draw_divider(y)
        y += 30 * scale

        # --- Info ---
        draw_row(y, texts["receipt_invoice"], str(order_data['id']), font_text, font_bold)
        y += 40 * scale
        draw_row(y, texts["receipt_date"], datetime.now().strftime('%d/%m/%Y %H:%M'), font_text, font_bold)
        y += 40 * scale
        draw_row(y, texts["receipt_customer"], str(order_data['customer']), font_text, font_bold)
        y += 50 * scale
        
        draw_divider(y)
        y += 30 * scale
        
        # --- Items ---
        d.text((margin * 1.5, y), texts["receipt_items"], fill=text_main, font=font_bold)
        y += 50 * scale
        
        for idx, item in enumerate(items_list):
            max_chars = 45 # អនុញ្ញាតឱ្យឈ្មោះមុខម្ហូបចេញវែងជាងមុន
            display_item = item if len(item) <= max_chars else item[:max_chars-3] + "..."
            d.text((margin * 1.5, y), f"{idx+1}.  {display_item}", fill=text_main, font=font_text)
            y += 45 * scale
            
        y += 10 * scale
        draw_divider(y)
        y += 35 * scale
        
        # --- Totals ---
        tot_val = str(order_data['total'])
        draw_row(y, texts["receipt_total"], tot_val, font_bold, font_shop)
        y += 65 * scale

        paid_val = f"${float(amount_paid):.2f}"
        draw_row(y, texts["receipt_paid"], paid_val, font_text, font_bold, fill_right=primary_color)
        y += 65 * scale
        
        draw_divider(y)
        y += 40 * scale
        
        draw_centered(y, texts["receipt_thanks"], font_text, fill=text_muted)
        
        bio = io.BytesIO()
        img.save(bio, format="PNG", optimize=True)
        bio.seek(0)
        return bio.getvalue()
    except Exception as e:
        print(f"❌ Error generating receipt image: {e}", file=sys.stderr)
        return None

@app.post("/api/orders/receipt")
def upload_receipt(data: OrderReceipt, background_tasks: BackgroundTasks):
    # ស្វែងរកការកុម្ម៉ង់ដែលកំពុងរង់ចាំ (Pending Order)
    pending_order = None
    if USE_SUPABASE:
        res = supabase.table("orders").select("*").eq("chat_id", data.chat_id).eq("status", "ថ្មី (រង់ចាំការបញ្ជាក់)").execute()
        if res.data:
            pending_order = res.data[-1]
    else:
        for order in reversed(orders_db):
            if str(order.get("chat_id")) == str(data.chat_id) and order.get("status") == "ថ្មី (រង់ចាំការបញ្ជាក់)":
                pending_order = order
                break
                
    if not pending_order:
        return {"error": "No pending order found"}
        
    # ទាញយកទឹកប្រាក់ដែលត្រូវទូទាត់សរុប
    expected_total_str = pending_order["total"].replace("$", "").replace(",", "").strip()
    try:
        expected_total = float(expected_total_str)
    except Exception:
        expected_total = 0.0

    user_lang = get_user_lang_from_db(data.chat_id)
    lang_texts = BOT_LANG_DICT.get(user_lang, BOT_LANG_DICT["km"])

    # ---------------- មុខងារ AI Verification ---------------- #
    # ទាញយក GEMINI API KEY ពី telegram_bot ដោយផ្ទាល់ ដើម្បីធានាថាវាមិនទទេស្អាត
    import telegram_bot
    gemini_key = os.getenv("GEMINI_API_KEY", getattr(telegram_bot, "GEMINI_API_KEY", ""))
    is_valid = False
    ai_reason = lang_texts.get("ai_error_scan", "Cannot read amount.")
    extracted_amount = 0
    acc_name, trx_id = "N/A", "N/A"

    if gemini_key:
        try:
            client = genai.Client(api_key=gemini_key)
            img_data = requests.get(data.image_url).content
            
            prompt = f"""
            You are a highly precise payment verification AI. Analyze this ABA/ACLEDA bank receipt screenshot.
            Extract these exact values carefully: Total Amount Paid (number only), Account Name (string), Trx. ID or Reference Number (string).
            Return ONLY a valid JSON object in this format (no markdown):
            {{"extracted_amount": 15.50, "trx_id": "123456789", "account_name": "HEM SINATH"}}
            """
            
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[types.Part.from_bytes(data=img_data, mime_type='image/jpeg'), prompt],
                config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.1)
            )
            import json
            result = json.loads(response.text)
            
            # ប្រព័ន្ធការពារការគាំង (Robust Parsing): បំប្លែងទិន្នន័យ AI ទៅជាលេខសុទ្ធ
            raw_amount = str(result.get("extracted_amount", "0")).replace('$', '').replace(',', '').strip()
            try:
                extracted_amount = float(raw_amount)
            except ValueError:
                extracted_amount = 0.0
                
            acc_name = str(result.get("account_name", "N/A"))
            trx_id = str(result.get("trx_id", "N/A"))
            
            # ធ្វើការគណនាដោយកូដ Python ផ្ទាល់ដើម្បីធានាភាពជាក់លាក់ ១០០% ឥតខ្ចោះ
            if extracted_amount > 0 and extracted_amount >= expected_total:
                is_valid = True
            else:
                is_valid = False
                if extracted_amount == 0:
                    ai_reason = lang_texts.get("ai_error_scan", "Error scanning.")
                else:
                    ai_reason = lang_texts.get("ai_error_amount", "Mismatch").format(paid=extracted_amount, expected=expected_total)
                    
        except Exception as e:
            print(f"AI Verification Error: {e}")
            is_valid = False
            ai_reason = lang_texts.get("ai_error", "Error")

    if is_valid:
        if USE_SUPABASE:
            supabase.table("orders").update({"receipt_url": data.image_url, "status": "បានទូទាត់ប្រាក់ (Paid)"}).eq("id", pending_order["id"]).execute()
        else:
            pending_order.update({"receipt_url": data.image_url, "status": "បានទូទាត់ប្រាក់ (Paid)"})
        
        receipt_png = generate_receipt_image(pending_order, extracted_amount, lang=user_lang)
        admin_msg = f"✅ *អតិថិជនបានទូទាត់ប្រាក់ជោគជ័យ!*\n🧾 វិក្កយបត្រ: `{pending_order['id']}`\n💰 បានទូទាត់: `${extracted_amount}`\n🏦 គណនី: {acc_name}\n🆔 Trx ID: `{trx_id}`"
        
        admin_group = app_config_db.get("kitchen_group_id", "-1003740329904")
        markup_dict = {
            "inline_keyboard": [
                [{"text": "🧑‍🍳 កំពុងចម្អិន", "callback_data": f"admin_status_cooking_{pending_order['id']}"}, {"text": "🛵 កំពុងដឹកជញ្ជូន", "callback_data": f"admin_status_delivering_{pending_order['id']}"}],
                [{"text": "✅ ប្រគល់ជោគជ័យ (បញ្ចប់)", "callback_data": f"admin_status_done_{pending_order['id']}"}]
            ]
        }
        if receipt_png:
            import json
            requests.post(f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendPhoto", data={"chat_id": admin_group, "caption": admin_msg, "parse_mode": "Markdown", "reply_markup": json.dumps(markup_dict)}, files={"photo": ("receipt.png", receipt_png, "image/png")})
        else:
            requests.post(f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage", json={"chat_id": admin_group, "text": admin_msg, "parse_mode": "Markdown", "reply_markup": markup_dict})
            
        return {"message": "Receipt saved and verified", "order_id": pending_order["id"], "verified": True, "paid_amount": extracted_amount}
    else:
        admin_msg = f"⚠️ *ការព្រមានពីប្រព័ន្ធ AI (ការទូទាត់មានបញ្ហា)!*\n\nការកុម្ម៉ង់លេខ `{pending_order['id']}` របស់អតិថិជន {pending_order['customer']} ត្រូវបានរកឃើញភាពមិនប្រក្រតី។\n\n📉 តម្រូវការទឹកប្រាក់: `${expected_total}`\n🔍 មូលហេតុពី AI: {ai_reason}\n\nសូម Admin ពិនិត្យឡើងវិញជាបន្ទាន់ជាមួយភ្ញៀវ។"
        requests.post(f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage", json={"chat_id": app_config_db.get("kitchen_group_id", "-1003740329904"), "text": admin_msg, "parse_mode": "Markdown"})
        user_reject_reason = lang_texts["payment_reject_user"].format(reason=ai_reason)
        return {"error": "Payment verification failed", "reason": user_reject_reason, "verified": False}

menu_cache = []
last_menu_fetch = 0

@app.get("/api/menu")
def get_menu(response: Response):
    response.headers["Cache-Control"] = "public, max-age=15" # បង្ខំឱ្យទូរស័ព្ទ Save ទិន្នន័យនេះទុកក្នុង RAM ១៥វិនាទី
    global menu_cache, last_menu_fetch
    # កំណត់ Cache ៥ វិនាទី ដើម្បីឱ្យ Mini App ដើរលឿនដូចផ្លេកបន្ទោរ (Lightning Fast)
    if time.time() - last_menu_fetch < 5 and menu_cache:
        return menu_cache
    if USE_SUPABASE:
        try:
            res_db = supabase.table("menu").select("*").order("sort_order", nulls_first=False).order("id").execute()
            menu_cache = res_db.data
            last_menu_fetch = time.time()
            return menu_cache
        except Exception as e:
            print(f"⚠️ Column sort_order missing, falling back to id: {e}")
            try:
                res_db = supabase.table("menu").select("*").order("id").execute()
                menu_cache = res_db.data
                last_menu_fetch = time.time()
                return res_db.data
            except Exception as e2:
                try:
                    res_db = supabase.table("menu").select("*").execute()
                    menu_cache = res_db.data
                    last_menu_fetch = time.time()
                    return res_db.data
                except Exception as e3:
                    pass # បើ Supabase គាំងទាំងស្រុង, បន្តទៅប្រើទិន្នន័យបម្រុងពី Memory
    return sorted(menu_db, key=lambda x: (x.get("sort_order", 999), x["id"]))

@app.put("/api/menu/reorder")
def reorder_menu(items: list[MenuReorderItem], background_tasks: BackgroundTasks):
    if USE_SUPABASE:
        for item in items:
            try:
                supabase.table("menu").update({"sort_order": item.sort_order}).eq("id", item.id).execute()
            except Exception: pass
        background_tasks.add_task(broadcast_ws_event, "REORDER_MENU", [i.model_dump() for i in items])
        return {"status": "ok"}
    global menu_db
    for item in items:
        for m in menu_db:
            if m["id"] == item.id:
                m["sort_order"] = item.sort_order
    background_tasks.add_task(broadcast_ws_event, "REORDER_MENU", [i.model_dump() for i in items])
    return {"status": "ok"}

@app.post("/api/menu")
def add_menu(item: MenuItem, background_tasks: BackgroundTasks):
    if USE_SUPABASE:
        try:
            response = supabase.table("menu").insert({"name": item.name, "price": item.price, "image_url": item.image_url}).execute()
            if not response.data:
                raise HTTPException(status_code=403, detail="❌ ការបញ្ជូលត្រូវបានរារាំងដោយប្រព័ន្ធសុវត្ថិភាព។ សូមចូលទៅបិទ RLS (Disable RLS) លើ Table 'menu' ក្នុងគណនី Supabase របស់អ្នកជាបន្ទាន់។")
            background_tasks.add_task(broadcast_ws_event, "UPDATE_MENU", item.model_dump())
            return response.data[0]
        except Exception as e:
            if isinstance(e, HTTPException): raise e
            raise HTTPException(status_code=400, detail=f"Database Error: {str(e)}")
    global menu_id_counter
    new_item = {"id": menu_id_counter, "name": item.name, "price": item.price, "image_url": item.image_url}
    menu_db.append(new_item)
    menu_id_counter += 1
    return new_item

@app.put("/api/menu/{item_id}")
def update_menu(item_id: int, item: MenuItem, background_tasks: BackgroundTasks):
    if USE_SUPABASE:
        try:
            response = supabase.table("menu").update({"name": item.name, "price": item.price, "image_url": item.image_url}).eq("id", item_id).execute()
            if not response.data:
                raise HTTPException(status_code=403, detail="❌ ការកែប្រែត្រូវបានរារាំងដោយប្រព័ន្ធសុវត្ថិភាព។ សូមចូលទៅបិទ RLS (Disable RLS) លើ Table 'menu' ក្នុង Supabase។")
            background_tasks.add_task(broadcast_ws_event, "UPDATE_MENU", item.model_dump())
            return response.data[0]
        except Exception as e:
            if isinstance(e, HTTPException): raise e
            raise HTTPException(status_code=400, detail=f"Database Error: {str(e)}")
    global menu_db
    for m in menu_db:
        if m["id"] == item_id:
            m["name"] = item.name
            m["price"] = item.price
            m["image_url"] = item.image_url
            return m
    return {"error": "Item not found"}

@app.delete("/api/menu/{item_id}")
def delete_menu(item_id: int, background_tasks: BackgroundTasks):
    if USE_SUPABASE:
        supabase.table("menu").delete().eq("id", item_id).execute()
        background_tasks.add_task(broadcast_ws_event, "UPDATE_MENU", {"id": item_id, "deleted": True})
        return {"message": "Item deleted successfully"}
    global menu_db
    menu_db = [item for item in menu_db if item["id"] != item_id]
    background_tasks.add_task(broadcast_ws_event, "UPDATE_MENU", {"id": item_id, "deleted": True})
    return {"message": "Item deleted successfully"}

# ---------------- Upload រូបភាពមុខម្ហូប (JPG/PNG) ---------------- #
@app.post("/api/upload")
def upload_image(file: UploadFile = File(...)):
    import shutil
    try:
        file_bytes = file.file.read()
        file.file.seek(0)  # Reset file pointer after reading
        file_name = f"{file.filename}"
        
        # 1. ព្យាយាម Upload ទៅ Supabase Storage (ប្រភេទ Persistent - មិនបាត់ពេល Restart)
        if USE_SUPABASE:
            try:
                # Use upsert to avoid errors on duplicate files
                supabase.storage.from_("menu_images").upload(file_name, file_bytes, {"content-type": file.content_type, "upsert": "true"})
                image_url = supabase.storage.from_("menu_images").get_public_url(file_name)
                return {"image_url": image_url}
            except Exception as e:
                print(f"⚠️ Supabase Storage upload failed: {e}. Trying next method...")
                file.file.seek(0)

        # 2. ប្រព័ន្ធការពារកម្រិតទី ២: Upload ទៅកាន់ Cloud Storage Catbox.moe ជានិរន្តរ៍
        try:
            res = requests.post('https://catbox.moe/user/api.php', data={'reqtype': 'fileupload'}, files={'fileToUpload': (file.filename, file_bytes, file.content_type)}, timeout=30)
            if res.status_code == 200 and res.text.startswith("https"):
                return {"image_url": res.text}
            else:
                print(f"⚠️ Catbox upload failed with status {res.status_code}. Trying next method...")
        except Exception as e:
            print(f"⚠️ Catbox upload failed: {e}. Trying next method...")

        # 3. Local Storage (បម្រុងទុកចុងក្រោយ - បាត់ពេល Railway Restart)
        file.file.seek(0)
        file_location = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        local_image_url = f"https://{config.DOMAIN}/static/uploads/{file.filename}"
        return {"image_url": local_image_url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/users")
def get_users():
    if USE_SUPABASE:
        try:
            response = supabase.table("users").select("*").execute()
            return response.data
        except Exception as e:
            print(f"⚠️ Error fetching users: {e}")
            pass # បន្តទៅប្រើទិន្នន័យបម្រុងពី Memory
    return users_db

@app.post("/api/users")
def add_user(user: UserItem):
    import random
    # ប្រសិនបើជា Admin បន្ថែមដោយផ្ទាល់ពីកុំព្យូទ័រ (អត់មាន Telegram ID) វានឹងបង្កើត ID ថ្មី
    user_id_str = str(user.id) if user.id else f"99{random.randint(1000000, 9999999)}"
    
    if USE_SUPABASE:
        try:
            res = supabase.table("users").select("*").eq("id", user_id_str).execute()
            if res.data:
                update_data = {"name": user.name}
                if user.phone and user.phone != "N/A":
                    update_data["phone"] = user.phone
                if user.location:
                    update_data["location"] = user.location
                if user.language:
                    update_data["language"] = user.language
                try:
                    response = supabase.table("users").update(update_data).eq("id", user_id_str).execute()
                    return response.data[0] if response.data else None
                except Exception:
                    update_data.pop("location", None)
                    update_data.pop("language", None)
                    response = supabase.table("users").update(update_data).eq("id", user_id_str).execute()
                    return response.data[0] if response.data else None
            else:
                insert_data = {
                    "id": user_id_str,
                    "name": user.name,
                    "phone": user.phone,
                    "points": 0,
                    "chat_id": user_id_str
                }
                if user.location:
                    insert_data["location"] = user.location
                if user.language:
                    insert_data["language"] = user.language
                    
                try:
                    response = supabase.table("users").insert(insert_data).execute()
                    return response.data[0] if response.data else None
                except Exception as e1:
                    print(f"⚠️ Supabase Insert Error 1: {e1}")
                    try:
                        response = supabase.table("users").insert({"id": user_id_str, "name": user.name, "phone": user.phone, "points": 0, "chat_id": user_id_str}).execute()
                        return response.data[0] if response.data else None
                    except Exception as e2:
                        print(f"⚠️ Supabase Insert Error 2 (RLS): {e2}")
        except Exception as e:
            print(f"⚠️ Supabase Error: {str(e)}. Falling back to Memory DB.")
            
    for u in users_db:
        if str(u.get("id")) == user_id_str or str(u.get("chat_id")) == user_id_str:
            u["name"] = user.name
            if user.phone and user.phone != "N/A":
                u["phone"] = user.phone
            if user.location:
                u["location"] = user.location
            if user.language:
                u["language"] = user.language
            return u
            
    new_user = {"id": user_id_str, "name": user.name, "phone": user.phone, "points": 0, "chat_id": user_id_str, "location": getattr(user, "location", ""), "language": user.language or "km"}
    users_db.append(new_user)
    return new_user

@app.delete("/api/users/{user_id}")
def delete_user(user_id: str):
    if USE_SUPABASE:
        supabase.table("users").delete().eq("id", user_id).execute()
        return {"message": "User deleted successfully"}
    global users_db
    users_db = [user for user in users_db if str(user["id"]) != user_id]
    return {"message": "User deleted successfully"}

# ---------------- ទាញយកព័ត៌មាន User ម្នាក់ ---------------- #
@app.get("/api/users/{user_id}")
def get_user(user_id: str):
    if USE_SUPABASE:
        try:
            res = supabase.table("users").select("*").eq("id", user_id).execute()
            if res.data:
                return res.data[0]
        except Exception:
            pass
    else:
        for u in users_db:
            if str(u.get("id")) == user_id or str(u.get("chat_id")) == user_id:
                return u
    return {}

# ---------------- ទាញយកពិន្ទុអតិថិជនតាម Chat ID ---------------- #
@app.get("/api/users/{chat_id}/points")
def get_user_points(chat_id: str):
    if USE_SUPABASE:
        try:
            res = supabase.table("users").select("points").eq("chat_id", chat_id).execute()
            if res.data:
                return {"points": res.data[0]["points"]}
        except Exception:
            pass
    else:
        for u in users_db:
            if u.get("chat_id") == chat_id:
                return {"points": u.get("points", 0)}
    return {"points": 0}

# ---------------- Dynamic Mini App Config ---------------- #
config_cache = {}
last_config_fetch = 0

@app.get("/api/config")
def get_config(response: Response):
    response.headers["Cache-Control"] = "public, max-age=30" # បង្ខំឱ្យទូរស័ព្ទ Save ការកំណត់រយៈពេល ៣០វិនាទី
    global config_cache, last_config_fetch
    if time.time() - last_config_fetch < 10 and config_cache:
        return config_cache
    if USE_SUPABASE:
        try:
            res = supabase.table("config").select("*").eq("id", 1).execute()
            if res.data:
                config_cache = {**app_config_db, **res.data[0]}
                last_config_fetch = time.time()
                return config_cache # បញ្ចូលទិន្នន័យពី DB ទៅលើសភាពដើម
        except Exception as e:
            print("Error fetching config:", e)
    return app_config_db

@app.post("/api/config")
def update_config(config: AppConfig):
    app_config_db.update(config.model_dump())
    if USE_SUPABASE:
        try:
            res = supabase.table("config").select("id").eq("id", 1).execute()
            if res.data:
                supabase.table("config").update(config.model_dump()).eq("id", 1).execute()
            else:
                supabase.table("config").insert({"id": 1, **config.model_dump()}).execute()
        except Exception as e:
            print("Error saving config:", e)
    return app_config_db

# ---------------- Live Chat CRM & Broadcast ---------------- #
@app.post("/api/crm/messages")
def add_crm_message(msg: ChatMessage, background_tasks: BackgroundTasks):
    from datetime import datetime
    record = msg.model_dump()
    record["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    if USE_SUPABASE:
        try:
            supabase.table("crm_messages").insert(record).execute()
            background_tasks.add_task(broadcast_ws_event, "NEW_CRM_MSG", record)
        except Exception as e:
            print("Error saving CRM message:", e)
    else:
        crm_messages_db.append(record)
        background_tasks.add_task(broadcast_ws_event, "NEW_CRM_MSG", record)
    return {"status": "ok"}

@app.get("/api/crm/messages")
def get_crm_messages():
    if USE_SUPABASE:
        try:
            # ទាញយក 100 សារចុងក្រោយបំផុត
            res = supabase.table("crm_messages").select("*").order("id", desc=True).limit(100).execute()
            if res.data:
                return res.data[::-1] # ត្រឡប់បញ្ច្រាសមកវិញដើម្បីឱ្យសារចាស់នៅខាងលើ
        except Exception as e:
            print("Error fetching CRM messages:", e)
    return crm_messages_db[-100:]

@app.post("/api/crm/reply")
def reply_crm_message(msg: ChatMessage, background_tasks: BackgroundTasks):
    import time
    from datetime import datetime
    # ផ្ញើទៅកាន់ Telegram របស់អ្នកប្រើប្រាស់
    requests.post(f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage", json={"chat_id": msg.chat_id, "text": f"👨‍💼 *Admin:* {msg.text}", "parse_mode": "Markdown"})
    
    # កត់ត្រាទុកថា Admin ទើបតែបានឆាតជាមួយភ្ញៀវម្នាក់នេះ (ដើម្បីបិទ AI)
    admin_active_chats[msg.chat_id] = time.time()

    record = msg.model_dump()
    record["is_admin"] = True
    record["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    if USE_SUPABASE:
        try:
            supabase.table("crm_messages").insert(record).execute()
            background_tasks.add_task(broadcast_ws_event, "NEW_CRM_MSG", record)
        except Exception as e:
            print("Error saving CRM reply:", e)
    else:
        crm_messages_db.append(record)
        background_tasks.add_task(broadcast_ws_event, "NEW_CRM_MSG", record)
    return {"status": "ok"}

@app.get("/api/crm/ai_status/{chat_id}")
def get_ai_status(chat_id: str):
    import time
    last_admin_reply = admin_active_chats.get(chat_id, 0)
    # បិទ AI រយៈពេល ១ ម៉ោង (3600 វិនាទី) ក្រោយពី Admin ឆ្លើយតប
    if time.time() - last_admin_reply < 3600:
        return {"ai_active": False}
    return {"ai_active": True}

@app.post("/api/broadcast")
def broadcast_message(req: BroadcastRequest):
    # ប្រមូល chat_id ដែលធ្លាប់កុម្ម៉ង់
    chat_ids = set([str(o["chat_id"]) for o in orders_db if o.get("chat_id")])
    if USE_SUPABASE:
        res = supabase.table("orders").select("chat_id").execute()
        if res.data:
            chat_ids = set([str(o["chat_id"]) for o in res.data if o.get("chat_id")])
            
    count = 0
    for cid in chat_ids:
        requests.post(f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage", json={"chat_id": cid, "text": f"📢 *សេចក្តីជូនដំណឹង:*\n{req.text}", "parse_mode": "Markdown"})
        count += 1
    return {"sent": count}

if __name__ == "__main__":
    import uvicorn
    print(f"Starting server on http://0.0.0.0:{config.PORT}")
    uvicorn.run(app, host="0.0.0.0", port=config.PORT)