import warnings
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, BackgroundTasks, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from contextlib import asynccontextmanager
import os
import sys
import requests
import asyncio
from supabase import create_client, Client
import telebot
from telegram_bot import bot
from google import genai
from google.genai import types

# Import the centralized configuration
import config

# បិទរាល់សារព្រមាន (Warnings) ទាំងអស់កុំឱ្យលោតរំខាន
warnings.filterwarnings("ignore")

def download_khmer_font():
    """ ទាញយក Font ខ្មែរដោយស្វ័យប្រវត្តិដើម្បីឱ្យវិក្កយបត្រចេញអក្សរខ្មែរបាន ១០០% """
    os.makedirs(os.path.dirname(config.KHMER_FONT_PATH), exist_ok=True)
    if not os.path.exists(config.KHMER_FONT_PATH):
        print("📥 កំពុងទាញយក Font ខ្មែរ Noto Sans Khmer ដ៏ស្រស់ស្អាត សម្រាប់វិក្កយបត្រ...")
        try:
            url = "https://github.com/google/fonts/raw/main/ofl/notosanskhmer/NotoSansKhmer-Regular.ttf"
            res = requests.get(url, timeout=10)
            with open(config.KHMER_FONT_PATH, "wb") as f:
                f.write(res.content)
            print("✅ ទាញយក Font ខ្មែរបានជោគជ័យ!")
        except Exception as e:
            print(f"⚠️ មិនអាចទាញយក Font ខ្មែរបានទេ: {e}")

# ---------------- Lifespan Manager for Telegram Bot Webhook ---------------- #
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the Telegram webhook setup and removal during the application's lifespan.
    Ensures the webhook is correctly pointed to the public domain from config.
    """
    def startup_tasks():
        try:
            download_khmer_font()
            print(f"ℹ️  Attempting to set webhook to: {config.WEBHOOK_URL}")
            bot.remove_webhook()
            bot.set_webhook(url=config.WEBHOOK_URL, drop_pending_updates=True)
            
            # Verify webhook is set correctly
            webhook_info = bot.get_webhook_info()
            if webhook_info.url == config.WEBHOOK_URL:
                print(f"✅ Webhook successfully set to: {config.WEBHOOK_URL}")
            else:
                print(f"⚠️ Webhook mismatch. Expected {config.WEBHOOK_URL}, but found {webhook_info.url}. Retrying...", file=sys.stderr)
                bot.set_webhook(url=config.WEBHOOK_URL, drop_pending_updates=True)
                if bot.get_webhook_info().url == config.WEBHOOK_URL:
                     print(f"✅ Webhook successfully reset to: {config.WEBHOOK_URL}")
                else:
                     print(f"❌ FATAL: Failed to set webhook. Found: {bot.get_webhook_info().url}", file=sys.stderr)
        except Exception as e:
            print(f"⚠️ Warning: Could not setup startup tasks: {e}", file=sys.stderr)
            
    # ប្រើប្រាស់ Background Thread ដើម្បីបើកផ្លូវឱ្យ Server (Uvicorn) ដំណើរការបានភ្លាមៗ ជៀសវាងការគាំង (Failed to respond) នៅលើ Railway
    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, startup_tasks)
    
    yield
    
    # Clean up and remove webhook on shutdown
    print("ℹ️  Application shutting down. Removing webhook...")
    try:
        bot.remove_webhook()
        print("✅ Webhook removed successfully.")
    except Exception as e:
        print(f"⚠️ Warning: Could not remove webhook on shutdown: {e}", file=sys.stderr)

app = FastAPI(title="Food E-Commerce API", lifespan=lifespan)

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
    "kitchen_group_id": "",
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

@app.get("/")
def read_root():
    return {"message": "🎉 Server ដំណើរការយ៉ាងរលូន! នេះគឺជា Food E-Commerce API."}

@app.get("/init", response_class=HTMLResponse)
def init_system(request: Request):
    """ ប្រើសម្រាប់បង្ខំឱ្យ Telegram ស្គាល់ Domain ថ្មីដោយស្វ័យប្រវត្តិ (Magic Fix) """
    host = request.headers.get("host")
    scheme = request.headers.get("x-forwarded-proto", "https")
    real_webhook_url = f"{scheme}://{host}/webhook"
    
    try:
        bot.remove_webhook()
        bot.set_webhook(url=real_webhook_url, drop_pending_updates=True)
        print(f"✅ Webhook Fixed: {real_webhook_url}")
        return f"<div style='text-align:center; margin-top:50px; font-family:Arial;'><h2>✅ ប្រព័ន្ធត្រូវបានជួសជុលជោគជ័យ!</h2><p>Webhook ថ្មីគឺ: <b>{real_webhook_url}</b></p><h3 style='color:green;'>សូមចូលទៅ Telegram រួចចុច /start ឥឡូវនេះ</h3></div>"
    except Exception as e:
        return f"<div style='text-align:center; color:red;'><h2>❌ មានកំហុស: {e}</h2></div>"

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
def serve_miniapp():
    # ប្រើប្រាស់ទីតាំងពិតប្រាកដ (Absolute Path) ដើម្បីប្រាកដថាវារកឃើញឯកសារ index.html ជានិច្ច
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>កំពុងរៀបចំប្រព័ន្ធ... រកមិនឃើញឯកសារ index.html ទេ</h1>"

@app.get("/api/orders")
def get_orders():
    if USE_SUPABASE:
        response = supabase.table("orders").select("*").order("created_at").execute()
        return response.data
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
        markup = {
            "inline_keyboard": [
                [{"text": "🏪 មកយកផ្ទាល់នៅហាង (Pickup)", "callback_data": f"pickup_{new_order['id']}"}],
                [{"text": "🛵 ហាងដឹកជូនផ្ទាល់ (Delivery)", "callback_data": f"delivery_{new_order['id']}"}]
            ]
        }
        msg_text = f"🎉 *ទទួលបានការកុម្ម៉ង់បឋម!*\n\n🧾 លេខវិក្កយបត្រ: `{new_order['id']}`\n\nតើលោកអ្នកចង់មកយកផ្ទាល់ ឬឱ្យហាងដឹកជូន?"
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

    payment_text = (
        f"🎉 *ការកុម្ម៉ង់ទទួលបានជោគជ័យ!*\n\n"
        f"🧾 *លេខវិក្កយបត្រ:* `{order['id']}`\n"
        f"👤 *អតិថិជន:* {order['customer']}\n"
        f"📱 *គណនី Telegram:* {chat_id}\n"
        f"📞 *លេខទូរស័ព្ទ:* {user_phone}\n"
        f"📍 *Location:* {user_loc}\n\n"
        f"🛒 *មុខម្ហូបដែលបានកុម្ម៉ង់:*\n"
        f"{formatted_items}\n"
        f"💰 *សរុបប្រាក់ត្រូវបង់:* {order['total']}\n\n"
        f"💳 *សូមធ្វើការទូទាត់ប្រាក់មកកាន់គណនី ABA & ACLEDA ខាងក្រោម៖*\n"
        f"• ឈ្មោះគណនី៖ HEM SINATH\n"
        f"• លេខគណនី៖ 086599789\n\n"
        f"📸 ក្រោយពីបង់ប្រាក់រួច សូមផ្ញើរូបភាពវិក្កយបត្រ (Screenshot) មកទីនេះ ដើម្បីឱ្យយើងរៀបចំអាហារជូនអ្នកភ្លាមៗ។"
    )
    
    qr_path = os.path.join(os.path.dirname(__file__), "aba_qr.jpg")
    if os.path.exists(qr_path):
        with open(qr_path, "rb") as f:
            qr_bytes = f.read()
        
        requests.post(f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendPhoto", data={'chat_id': chat_id, 'caption': payment_text, 'parse_mode': 'Markdown'}, files={'photo': ('aba_qr.jpg', qr_bytes, 'image/jpeg')})
        requests.post(f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendPhoto", data={'chat_id': "@XiaoYueXiaoChi", 'caption': f"🔔 *New Order Alert!*\n\n{payment_text}", 'parse_mode': 'Markdown'}, files={'photo': ('aba_qr.jpg', qr_bytes, 'image/jpeg')})
    else:
        # បម្រុងទុក (Fallback)៖ បើសិនជាបាត់រូប aba_qr.jpg ក៏វានៅតែបាញ់អត្ថបទវិក្កយបត្រទៅដែរ
        requests.post(f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage", json={'chat_id': chat_id, 'text': payment_text, 'parse_mode': 'Markdown'})
        requests.post(f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage", json={'chat_id': "@XiaoYueXiaoChi", 'text': f"🔔 *New Order Alert!*\n\n{payment_text}", 'parse_mode': 'Markdown'})

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
        
    # ទីតាំងហាងជាក់ស្តែង (HV46+P8 Phnom Penh) ប្រហែល 11.5564, 104.9282
    STORE_LAT = 11.5564
    STORE_LON = 104.9282
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
            msg_text = f"🔔 *ជម្រាបសួរ {order['customer']}*\nការកុម្ម៉ង់លេខ {order['id']} របស់អ្នកត្រូវបានប្តូរស្ថានភាពទៅជា៖ *{status_update.status}*"
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
                        pts_msg = f"🎁 *អបអរសាទរ!* អ្នកទទួលបាន *{points_earned} ពិន្ទុសន្សំ* ពីការទិញនេះ។\nបច្ចុប្បន្នអ្នកមានពិន្ទុសរុប៖ *{new_points} ពិន្ទុ* 🌟"
                        requests.post(f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage", json={"chat_id": order["chat_id"], "text": pts_msg, "parse_mode": "Markdown"})
                        
                        # ---- ផ្ញើសារ Promotion ដោយស្វ័យប្រវត្តិ ---- #
                        old_points = new_points - points_earned
                        if new_points >= 50 and old_points < 50:
                            promo_msg = "🎉 *កាដូពិសេសពីហាង 小月小吃!*\n\nអ្នកសន្សំបាន ៥០ ពិន្ទុហើយ! 🎁\nយើងខ្ញុំសូមជូន *ភេសជ្ជៈ ១ កែវ ឥតគិតថ្លៃ* សម្រាប់ការកុម្ម៉ង់លើកក្រោយ។\n*(សូម Screenshot សារនេះបង្ហាញទៅកាន់អ្នកលក់)*"
                            requests.post(f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage", json={"chat_id": order["chat_id"], "text": promo_msg, "parse_mode": "Markdown"})
                        elif new_points >= 100 and old_points < 100:
                            promo_msg = "🎉 *កាដូពិសេសពីហាង 小月小吃!*\n\nអស្ចារ្យណាស់! អ្នកសន្សំបាន ១០០ ពិន្ទុ! 🎁\nយើងខ្ញុំសូមជូន *ការបញ្ចុះតម្លៃ $5.00* សម្រាប់ការកុម្ម៉ង់លើកក្រោយ។\n*(សូម Screenshot សារនេះបង្ហាញទៅកាន់អ្នកលក់)*"
                            requests.post(f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage", json={"chat_id": order["chat_id"], "text": promo_msg, "parse_mode": "Markdown"})
            except Exception as e:
                print("Error adding points:", e)
        background_tasks.add_task(broadcast_ws_event, "UPDATE_ORDER", order)
                
        return {"message": "Status updated successfully", "order": order}
    return {"error": "Order not found"}

def generate_receipt_image(order_data, amount_paid):
    """ Generates a PNG receipt image with proper Khmer font support. """
    try:
        from PIL import Image, ImageDraw, ImageFont
        import io
        from datetime import datetime
        
        width, height = 450, 650
        img = Image.new('RGB', (width, height), color=(250, 250, 250))
        d = ImageDraw.Draw(img)
        
        # Load the beautiful Khmer font
        try:
            if not os.path.exists(config.KHMER_FONT_PATH):
                raise FileNotFoundError(f"Font file not found at {config.KHMER_FONT_PATH}")
            font_title = ImageFont.truetype(config.KHMER_FONT_PATH, 28)
            font_text = ImageFont.truetype(config.KHMER_FONT_PATH, 20)
            font_bold = ImageFont.truetype(config.KHMER_FONT_PATH, 22)
        except Exception as e:
            print(f"⚠️  Font Error: {e}. Falling back to default font.", file=sys.stderr)
            font_title = font_text = font_bold = ImageFont.load_default()

        # --- Drawing content ---
        y = 30
        d.text((width/2, y), "វិក្កយបត្រ / Receipt", fill=(0,0,0), font=font_title, anchor="mt")
        y += 50
        d.line([(20, y), (width-20, y)], fill=(50,50,50), width=1)
        y += 20

        d.text((30, y), f"លេខវិក្កយបត្រ: {order_data['id']}", fill=(0,0,0), font=font_text)
        d.text((width-30, y), f"{datetime.now().strftime('%d/%m/%Y')}", fill=(0,0,0), font=font_text, anchor="ra")
        y += 30
        d.text((30, y), f"អតិថិជន: {order_data['customer']}", fill=(0,0,0), font=font_text)
        y += 40
        
        d.text((30, y), "รายการ / Items", fill=(0,0,0), font=font_bold)
        y += 35
        items = order_data["items"].split(",")
        for item in items:
            if item.strip():
                d.text((30, y), item.strip()[:40], fill=(0,0,0), font=font_text)
                y += 30
        y += 10
        d.line([(20, y), (width-20, y)], fill=(150,150,150), width=1)
        y += 20
        
        d.text((30, y), "សរុប / Total Due:", fill=(0,0,0), font=font_bold)
        d.text((width-30, y), f"{order_data['total']}", fill=(0,0,0), font=font_bold, anchor="ra")
        y += 35
        d.text((30, y), "បានបង់ / Amount Paid:", fill=(0,0,0), font=font_bold)
        d.text((width-30, y), f"${float(amount_paid):.2f}", fill=(39, 174, 96), font=font_bold, anchor="ra")
        y += 60
        
        d.text((width/2, y), "*** បង់ប្រាក់រួចរាល់ ***", fill=(39, 174, 96), font=font_title, anchor="mt")
        y += 40
        d.text((width/2, y), "សូមអរគុណ!", fill=(0,0,0), font=font_text, anchor="mt")
        
        bio = io.BytesIO()
        img.save(bio, format="PNG")
        bio.seek(0)
        return bio.getvalue()
    except Exception as e:
        print(f"❌ Error generating receipt image: {e}", file=sys.stderr)
        return None

@app.post("/api/orders/receipt")
def upload_receipt(data: OrderReceipt):
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

    # ---------------- មុខងារ AI Verification ---------------- #
    # ទាញយក GEMINI API KEY ពី telegram_bot ដោយផ្ទាល់ ដើម្បីធានាថាវាមិនទទេស្អាត
    import telegram_bot
    gemini_key = os.getenv("GEMINI_API_KEY", getattr(telegram_bot, "GEMINI_API_KEY", ""))
    is_valid = False
    ai_reason = "ប្រព័ន្ធមិនអាចផ្ទៀងផ្ទាត់រូបភាពបានទេ"
    extracted_amount = 0
    acc_name, trx_id = "N/A", "N/A"

    if gemini_key:
        try:
            client = genai.Client(api_key=gemini_key)
            img_data = requests.get(data.image_url).content
            
            prompt = f"""
            You are a highly strictly payment verification system. Analyze this ABA/ACLEDA payment screenshot.
            Extract these exact values: Total Amount (number only), Account Name (string), Trx. ID or Reference Number (string).
            Compare the extracted amount with the expected total: {expected_total}.
            If the extracted amount is EXACTLY EQUAL OR GREATER than {expected_total}, set is_match to true, otherwise false.
            Return ONLY a valid JSON object in this format (no markdown):
            {{"extracted_amount": 15.50, "is_match": true, "trx_id": "123456789", "account_name": "HEM SINATH", "reason": "Amount verified."}}
            """
            
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[types.Part.from_bytes(data=img_data, mime_type='image/jpeg'), prompt],
                config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.0)
            )
            import json
            result = json.loads(response.text)
            is_valid = result.get("is_match", False)
            ai_reason = result.get("reason", "មិនអាចផ្ទៀងផ្ទាត់បាន")
            extracted_amount = result.get("extracted_amount", 0)
            acc_name = result.get("account_name", "N/A")
            trx_id = result.get("trx_id", "N/A")
        except Exception as e:
            print(f"AI Verification Error: {e}")
            is_valid = False
            ai_reason = "មានបញ្ហាភ្ជាប់ទៅកាន់ប្រព័ន្ធ AI ស្កេនរូបភាព"

    if is_valid:
        if USE_SUPABASE:
            supabase.table("orders").update({"receipt_url": data.image_url, "status": "បានទូទាត់ប្រាក់ (Paid)"}).eq("id", pending_order["id"]).execute()
        else:
            pending_order.update({"receipt_url": data.image_url, "status": "បានទូទាត់ប្រាក់ (Paid)"})
        
        receipt_png = generate_receipt_image(pending_order, extracted_amount)
        admin_msg = f"✅ *អតិថិជនបានទូទាត់ប្រាក់ជោគជ័យ!*\n🧾 វិក្កយបត្រ: `{pending_order['id']}`\n💰 បានទូទាត់: `${extracted_amount}`\n🏦 គណនី: {acc_name}\n🆔 Trx ID: `{trx_id}`"
        if receipt_png:
            requests.post(f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendPhoto", data={"chat_id": "@XiaoYueXiaoChi", "caption": admin_msg, "parse_mode": "Markdown"}, files={"photo": ("receipt.png", receipt_png, "image/png")})
            user_msg = "✅ *ការទូទាត់របស់អ្នកទទួលបានជោគជ័យ!* នេះជាវិក្កយបត្រផ្លូវការ។ សូមរង់ចាំអាហាររបស់អ្នកបន្តិច... 🛵"
            requests.post(f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendPhoto", data={"chat_id": data.chat_id, "caption": user_msg, "parse_mode": "Markdown"}, files={"photo": ("receipt.png", receipt_png, "image/png")})
        else:
            requests.post(f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage", json={"chat_id": "@XiaoYueXiaoChi", "text": admin_msg, "parse_mode": "Markdown"})
            requests.post(f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage", json={"chat_id": data.chat_id, "text": "✅ *ការទូទាត់ជោគជ័យ!* សូមរង់ចាំអាហាររបស់អ្នកបន្តិច... 🛵", "parse_mode": "Markdown"})
            
        return {"message": "Receipt saved and verified", "order_id": pending_order["id"], "verified": True}
    else:
        admin_msg = f"⚠️ *ការព្រមានពីប្រព័ន្ធ AI (ការទូទាត់មានបញ្ហា)!*\n\nការកុម្ម៉ង់លេខ `{pending_order['id']}` របស់អតិថិជន {pending_order['customer']} ត្រូវបានរកឃើញភាពមិនប្រក្រតី។\n\n📉 តម្រូវការទឹកប្រាក់: `${expected_total}`\n🔍 មូលហេតុពី AI: {ai_reason}\n\nសូម Admin ពិនិត្យឡើងវិញជាបន្ទាន់ជាមួយភ្ញៀវ។"
        requests.post(f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage", json={"chat_id": "@XiaoYueXiaoChi", "text": admin_msg, "parse_mode": "Markdown"})
        return {"error": "Payment verification failed", "reason": ai_reason, "verified": False}

@app.get("/api/menu")
def get_menu():
    if USE_SUPABASE:
        response = supabase.table("menu").select("*").order("sort_order", nulls_first=False).order("id").execute()
        return response.data
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
            background_tasks.add_task(broadcast_ws_event, "UPDATE_MENU", item.model_dump())
            return response.data[0] if response.data else {"id": 0, "name": item.name, "price": item.price, "image_url": item.image_url}
        except Exception as e:
                raise HTTPException(status_code=400, detail=f"Supabase Error: {str(e)}")
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
            background_tasks.add_task(broadcast_ws_event, "UPDATE_MENU", item.model_dump())
            return response.data[0] if response.data else {"id": item_id, "name": item.name, "price": item.price, "image_url": item.image_url}
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Supabase Error: {str(e)}")
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
        response = supabase.table("users").select("*").execute()
        return response.data
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
                try:
                    response = supabase.table("users").insert({"id": user_id_str, "name": user.name, "phone": user.phone, "points": 0, "chat_id": user_id_str, "location": getattr(user, "location", ""), "language": user.language or "km"}).execute()
                    return response.data[0] if response.data else None
                except Exception:
                    try:
                        response = supabase.table("users").insert({"id": user_id_str, "name": user.name, "phone": user.phone, "points": 0, "chat_id": user_id_str}).execute()
                        return response.data[0] if response.data else None
                    except Exception as e2:
                        raise HTTPException(status_code=400, detail=f"Database Error: {str(e2)}")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Supabase Error: {str(e)}")
            
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
@app.get("/api/config")
def get_config():
    if USE_SUPABASE:
        try:
            res = supabase.table("config").select("*").eq("id", 1).execute()
            if res.data:
                return {**app_config_db, **res.data[0]} # បញ្ចូលទិន្នន័យពី DB ទៅលើសភាពដើម
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