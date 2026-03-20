from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager
import os
import io
import qrcode
import requests
from supabase import create_client, Client
import telebot
from telegram_bot import bot

# ---------------- ភ្ជាប់ Webhook របស់ Telegram Bot ---------------- #
WEBHOOK_URL = "https://web-production-88028.up.railway.app/webhook"

@asynccontextmanager
async def lifespan(app: FastAPI):
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    print(f"✅ Webhook ត្រូវបានភ្ជាប់ទៅកាន់: {WEBHOOK_URL}")
    yield

app = FastAPI(title="Food E-Commerce API", lifespan=lifespan)

# ដាក់ Token របស់ Bot សម្រាប់ផ្ញើសារចេញពី Server ត្រឡប់ទៅអតិថិជនវិញ
BOT_TOKEN = "8704188082:AAEZmCT0yNJ9U3WNKte9E1SuJT0K4t4TOz0"

# ---------------- ការកំណត់ Supabase Database ---------------- #
SUPABASE_URL = os.getenv("SUPABASE_URL", "ដាក់_URL_SUPABASE_របស់អ្នកទីនេះ")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "ដាក់_KEY_SUPABASE_របស់អ្នកទីនេះ")

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    USE_SUPABASE = True
except Exception as e:
    USE_SUPABASE = False

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

class AppConfig(BaseModel):
    banner_url: str
    is_open: bool
    aba_name: str
    aba_number: str
    kitchen_group_id: str
    reward_points: int = 50
    reward_discount: float = 5.0

@app.get("/")
def read_root():
    return {"message": "🎉 Server ដំណើរការយ៉ាងរលូន! នេះគឺជា Food E-Commerce API."}


@app.post("/webhook")
def handle_webhook(update_dict: dict):
    import json
    json_string = json.dumps(update_dict)
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return {"status": "ok"}

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
        response = supabase.table("orders").select("*").execute()
        return response.data
    return orders_db

@app.post("/api/orders")
def create_order(order: OrderCreate):
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
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": kitchen_id, "text": kitchen_msg, "parse_mode": "Markdown"})
        
    return new_order

# ---------------- Action-Triggered Notification (ពី Mini App) ---------------- #
@app.post("/api/miniapp/checkout")
def miniapp_checkout(order: OrderCreate):
    import random
    new_order = {
        "id": f"#{random.randint(1000, 9999)}",
        "customer": order.customer,
        "items": order.items,
        "total": order.total,
        "status": "ថ្មី (រង់ចាំការបញ្ជាក់)",
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

    # បាញ់សារទៅ Group ផ្ទះបាយ
    kitchen_id = app_config_db.get("kitchen_group_id")
    if kitchen_id:
        kitchen_msg = f"🧑‍🍳 *មានការកុម្ម៉ង់ថ្មី (ពី Mini App)*\n\n🧾 *វិក្កយបត្រ:* `{new_order['id']}`\n🛒 *មុខម្ហូប:*\n{new_order['items'].replace(', ', '%0A')}"
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": kitchen_id, "text": kitchen_msg, "parse_mode": "Markdown"})

    # ផ្ញើសារវិក្កយបត្រ រួមជាមួយ QR Code ទៅកាន់អតិថិជន
    if order.chat_id:
        payment_text = (
            f"🎉 *ការកុម្ម៉ង់ទទួលបានជោគជ័យ!*\n\n"
            f"🧾 *លេខវិក្កយបត្រ:* `{new_order['id']}`\n"
            f"👤 *អតិថិជន:* {new_order['customer']}\n"
            f"🛒 *មុខម្ហូប:*\n{new_order['items'].replace(', ', '%0A')}\n\n"
            f"💰 *សរុបប្រាក់ត្រូវបង់:* {new_order['total']}\n\n"
            f"💳 *សូមធ្វើការទូទាត់ប្រាក់មកកាន់គណនី ABA ខាងក្រោម៖*\n"
            f"• ឈ្មោះគណនី៖ *{app_config_db['aba_name']}*\n"
            f"• លេខគណនី៖ *{app_config_db['aba_number']}*\n\n"
            f"📸 ក្រោយពីបង់ប្រាក់រួច សូមផ្ញើរូបភាពវិក្កយបត្រ (Screenshot) មកទីនេះ ដើម្បីឱ្យយើងរៀបចំអាហារជូនអ្នកភ្លាមៗ។"
        )
        
        # បង្កើត Dynamic QR Code
        qr_data = f"Account: {app_config_db['aba_number']}\nName: {app_config_db['aba_name']}\nAmount: {new_order['total']}\nOrder ID: {new_order['id']}"
        qr = qrcode.make(qr_data)
        bio = io.BytesIO()
        qr.save(bio, format="PNG")
        bio.seek(0)
        
        files = {'photo': ('qr.png', bio, 'image/png')}
        data = {'chat_id': order.chat_id, 'caption': payment_text, 'parse_mode': 'Markdown'}
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data=data, files=files)

    return {"message": "Order placed and receipt sent", "order": new_order}

@app.put("/api/orders/status")
def update_order_status(status_update: OrderStatusUpdate):
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
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": order["chat_id"], "text": msg_text, "parse_mode": "Markdown"})
            
        # ---------------- មុខងារ Loyalty Points ---------------- #
        if status_update.status == "✅ រួចរាល់ (បានប្រគល់)":
            try:
                total_amount = float(order['total'].replace('$', '').replace(',', ''))
                points_earned = int(total_amount) # ទិញ ១ ដុល្លារ បាន ១ ពិន្ទុ
                if points_earned > 0:
                    new_points = 0
                    if USE_SUPABASE:
                        res = supabase.table("users").select("*").eq("id", order["chat_id"]).execute()
                        if res.data:
                            user_id = res.data[0]['id']
                            new_points = res.data[0].get('points', 0) + points_earned
                            supabase.table("users").update({"points": new_points}).eq("id", user_id).execute()
                        else:
                            new_points = points_earned
                            supabase.table("users").insert({"id": order.get("chat_id", ""), "name": order["customer"], "phone": "N/A", "points": points_earned, "chat_id": order.get("chat_id", "")}).execute()
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
                        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": order["chat_id"], "text": pts_msg, "parse_mode": "Markdown"})
                        
                        # ---- ផ្ញើសារ Promotion ដោយស្វ័យប្រវត្តិ ---- #
                        old_points = new_points - points_earned
                        if new_points >= 50 and old_points < 50:
                            promo_msg = "🎉 *កាដូពិសេសពីហាង 小月小吃!*\n\nអ្នកសន្សំបាន ៥០ ពិន្ទុហើយ! 🎁\nយើងខ្ញុំសូមជូន *ភេសជ្ជៈ ១ កែវ ឥតគិតថ្លៃ* សម្រាប់ការកុម្ម៉ង់លើកក្រោយ។\n*(សូម Screenshot សារនេះបង្ហាញទៅកាន់អ្នកលក់)*"
                            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": order["chat_id"], "text": promo_msg, "parse_mode": "Markdown"})
                        elif new_points >= 100 and old_points < 100:
                            promo_msg = "🎉 *កាដូពិសេសពីហាង 小月小吃!*\n\nអស្ចារ្យណាស់! អ្នកសន្សំបាន ១០០ ពិន្ទុ! 🎁\nយើងខ្ញុំសូមជូន *ការបញ្ចុះតម្លៃ $5.00* សម្រាប់ការកុម្ម៉ង់លើកក្រោយ។\n*(សូម Screenshot សារនេះបង្ហាញទៅកាន់អ្នកលក់)*"
                            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": order["chat_id"], "text": promo_msg, "parse_mode": "Markdown"})
            except Exception as e:
                print("Error adding points:", e)
                
        return {"message": "Status updated successfully", "order": order}
    return {"error": "Order not found"}

@app.post("/api/orders/receipt")
def upload_receipt(data: OrderReceipt):
    if USE_SUPABASE:
        res = supabase.table("orders").select("*").eq("chat_id", data.chat_id).eq("status", "ថ្មី (រង់ចាំការបញ្ជាក់)").execute()
        if res.data:
            order_id = res.data[-1]['id'] # យករកការកុម្ម៉ង់ចុងក្រោយគេ
            supabase.table("orders").update({"receipt_url": data.image_url}).eq("id", order_id).execute()
            return {"message": "Receipt saved", "order_id": order_id}
        return {"error": "No pending order found"}
    else:
        for order in reversed(orders_db):
            if order.get("chat_id") == data.chat_id and order.get("status") == "ថ្មី (រង់ចាំការបញ្ជាក់)":
                order["receipt_url"] = data.image_url
                return {"message": "Receipt saved", "order_id": order["id"]}
        return {"error": "No pending order found"}

@app.get("/api/menu")
def get_menu():
    if USE_SUPABASE:
        response = supabase.table("menu").select("*").execute()
        return response.data
    return menu_db

@app.post("/api/menu")
def add_menu(item: MenuItem):
    if USE_SUPABASE:
        try:
            response = supabase.table("menu").insert({"name": item.name, "price": item.price, "image_url": item.image_url}).execute()
            return response.data[0] if response.data else {"id": 0, "name": item.name, "price": item.price}
        except Exception as e:
                raise HTTPException(status_code=400, detail=f"Supabase Error: {str(e)}")
    global menu_id_counter
    new_item = {"id": menu_id_counter, "name": item.name, "price": item.price, "image_url": item.image_url}
    menu_db.append(new_item)
    menu_id_counter += 1
    return new_item

@app.delete("/api/menu/{item_id}")
def delete_menu(item_id: int):
    if USE_SUPABASE:
        supabase.table("menu").delete().eq("id", item_id).execute()
        return {"message": "Item deleted successfully"}
    global menu_db
    menu_db = [item for item in menu_db if item["id"] != item_id]
    return {"message": "Item deleted successfully"}

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
    user_id_str = str(user.id) if user.id else f"manual_{random.randint(10000, 99999)}"
    
    if USE_SUPABASE:
        res = supabase.table("users").select("*").eq("id", user_id_str).execute()
        if res.data:
            update_data = {"name": user.name}
            if user.phone and user.phone != "N/A": update_data["phone"] = user.phone
            if user.location: update_data["location"] = user.location
            response = supabase.table("users").update(update_data).eq("id", user_id_str).execute()
            return response.data[0] if response.data else None
        else:
            response = supabase.table("users").insert({"id": user_id_str, "name": user.name, "phone": user.phone, "points": 0, "chat_id": user_id_str, "location": getattr(user, "location", "")}).execute()
            return response.data[0] if response.data else None
            
    for u in users_db:
        if str(u.get("id")) == user_id_str or str(u.get("chat_id")) == user_id_str:
            u["name"] = user.name
            if user.phone and user.phone != "N/A": u["phone"] = user.phone
            if user.location: u["location"] = user.location
            return u
            
    new_user = {"id": user_id_str, "name": user.name, "phone": user.phone, "points": 0, "chat_id": user_id_str, "location": getattr(user, "location", "")}
    users_db.append(new_user)
    return new_user

@app.delete("/api/users/{user_id}")
def delete_user(user_id: int):
    if USE_SUPABASE:
        supabase.table("users").delete().eq("id", user_id).execute()
        return {"message": "User deleted successfully"}
    global users_db
    users_db = [user for user in users_db if user["id"] != user_id]
    return {"message": "User deleted successfully"}

# ---------------- ទាញយកពិន្ទុអតិថិជនតាម Chat ID ---------------- #
@app.get("/api/users/{chat_id}/points")
def get_user_points(chat_id: str):
    if USE_SUPABASE:
        res = supabase.table("users").select("points").eq("chat_id", chat_id).execute()
        if res.data:
            return {"points": res.data[0]["points"]}
    else:
        for u in users_db:
            if u.get("chat_id") == chat_id:
                return {"points": u.get("points", 0)}
    return {"points": 0}

# ---------------- Dynamic Mini App Config ---------------- #
@app.get("/api/config")
def get_config():
    return app_config_db

@app.post("/api/config")
def update_config(config: AppConfig):
    app_config_db.update(config.dict())
    return app_config_db

# ---------------- Live Chat CRM & Broadcast ---------------- #
@app.post("/api/crm/messages")
def add_crm_message(msg: ChatMessage):
    from datetime import datetime
    record = msg.dict()
    record["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    crm_messages_db.append(record)
    return {"status": "ok"}

@app.get("/api/crm/messages")
def get_crm_messages():
    return crm_messages_db[-100:] # យកត្រឹម 100 សារចុងក្រោយ

@app.post("/api/crm/reply")
def reply_crm_message(msg: ChatMessage):
    import time
    from datetime import datetime
    # ផ្ញើទៅកាន់ Telegram របស់អ្នកប្រើប្រាស់
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": msg.chat_id, "text": f"👨‍💼 *Admin:* {msg.text}", "parse_mode": "Markdown"})
    
    # កត់ត្រាទុកថា Admin ទើបតែបានឆាតជាមួយភ្ញៀវម្នាក់នេះ (ដើម្បីបិទ AI)
    admin_active_chats[msg.chat_id] = time.time()

    record = msg.dict()
    record["is_admin"] = True
    record["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    crm_messages_db.append(record)
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
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": cid, "text": f"📢 *សេចក្តីជូនដំណឹង:*\n{req.text}", "parse_mode": "Markdown"})
        count += 1
    return {"sent": count}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)